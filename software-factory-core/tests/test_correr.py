"""El modo de producción sobrevive a la reanudación — pruebas de la CLI.

Una corrida decide con qué produce **una sola vez**, cuando se abre, y ese modo
queda registrado como hecho suyo en el Operational State. `--reanudar` lo lee de
ahí. El bug que estas pruebas cierran es concreto: antes el modo se deducía de
los flags de cada invocación, así que una corrida iniciada con `--stub` se
reanudaba contra el modelo real en cuanto alguien olvidaba repetir el flag, y
gastaba dinero que nadie pidió gastar.

Ninguna prueba toca la red, la base real ni el Vault real: el productor del
modelo se sustituye por un espía y el almacén vive en un directorio temporal.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))
# Para reutilizar los fixtures de T14 sin duplicarlos, corra el discover desde
# donde corra.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import correr  # noqa: E402
import gates  # noqa: E402
import grafo  # noqa: E402
import operational_state  # noqa: E402
import presupuesto  # noqa: E402
import productor  # noqa: E402
from operational_state import OperationalState  # noqa: E402
from test_grafo import PEDIDO, definicion_texto, productor_valido  # noqa: E402

LECTURA = ("normas/contrato-plan.md", "normas/glosario.md")


class BaseCLI(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.tmp = Path(self._dir.name)

        self.vault = self.tmp / "vault"
        (self.vault / "normas").mkdir(parents=True)
        for relativa in LECTURA:
            (self.vault / relativa).write_text("Documento de prueba.\n", encoding="utf-8")
        self.ruta_definicion = self.vault / "Agente de prueba.md"
        self.ruta_definicion.write_text(definicion_texto(), encoding="utf-8")

        self.ruta_pedido = self.tmp / "pedido.json"
        self.ruta_pedido.write_text(json.dumps(PEDIDO), encoding="utf-8")

        self.ruta_db = self.tmp / "estado" / "factory-test.db"
        self.ruta_checkpointer = self.tmp / "estado" / "checkpointer" / "checkpoints.db"

        # El directorio de estado, también al temporal. Estos tests hoy no
        # llegan a materializar evidencia —van con `--solo-plan`—, así que no
        # fugan; pero el agujero es el mismo que tenía el `BaseCLI` de
        # `test_correr_cadena.py` y está a un test de distancia de abrirse.
        estado = mock.patch.object(operational_state, "DIR_ESTADO", self.tmp / "estado")
        estado.start()
        self.addCleanup(estado.stop)

        # El entorno queda aislado y se restaura solo. Sin credencial: que una
        # corrida en modo stub no la exija es parte de lo que se comprueba.
        entorno = mock.patch.dict(os.environ, {})
        entorno.start()
        self.addCleanup(entorno.stop)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("ANTHROPIC_MODEL", None)

        # `.env` del repo fuera de juego: si se leyera, la credencial real
        # entraría al entorno del test y "sin credencial" dejaría de significar
        # nada. Lo que el test declara en `os.environ` es todo lo que hay.
        sin_env = mock.patch.object(correr, "load_dotenv", lambda *a, **k: None)
        sin_env.start()
        self.addCleanup(sin_env.stop)

        # El productor del modelo nunca se construye de verdad. El espía cuenta
        # con qué lo llamaron y devuelve un plan predecible.
        self.construcciones = []

        def crear_espia(api_key, modelo=productor.MODELO_POR_DEFECTO, ruta_vault=None, cliente=None):
            self.construcciones.append({"modelo": modelo, "ruta_vault": ruta_vault})
            return productor_valido

        espia = mock.patch.object(productor, "crear_productor", crear_espia)
        espia.start()
        self.addCleanup(espia.stop)

    # --- utilidades ---------------------------------------------------------

    def cli(self, *argv):
        """Corre `correr.main` y devuelve `(codigo, stdout, stderr)`."""
        salida, error = io.StringIO(), io.StringIO()
        completos = list(argv) + [
            "--db",
            str(self.ruta_db),
            "--checkpointer",
            str(self.ruta_checkpointer),
        ]
        with redirect_stdout(salida), redirect_stderr(error):
            codigo = correr.main(completos)
        return codigo, salida.getvalue().strip(), error.getvalue().strip()

    def abrir_corrida(self, *flags):
        """Abre una corrida nueva y devuelve su `run_id`. Frena en el Gate.

        Va con `--solo-plan` porque estos tests son sobre el modo de producción,
        no sobre la cadena. Declararlo es obligatorio: una corrida nueva tiene
        que decir si ejecuta las unidades del plan o solo lo produce.
        """
        codigo, run_id, error = self.cli(
            "--pedido",
            str(self.ruta_pedido),
            "--definicion",
            str(self.ruta_definicion),
            "--vault",
            str(self.vault),
            "--solo-plan",
            *flags,
        )
        self.assertEqual(codigo, 0, error)
        return run_id

    def credencial_disponible(self):
        """Lo que hace falta para que el modo modelo pueda construir productor."""
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        os.environ["ANTHROPIC_MODEL"] = "modelo-de-prueba"

    def store(self):
        almacen = OperationalState(self.ruta_db)
        self.addCleanup(almacen.cerrar)
        return almacen

    def aprobar(self, run_id, gate):
        almacen = OperationalState(self.ruta_db)
        try:
            gates.resolver(almacen, run_id, gate, "aprobado")
        finally:
            almacen.cerrar()

    def tipos(self, run_id):
        almacen = OperationalState(self.ruta_db)
        try:
            return [e["tipo"] for e in almacen.leer_run(run_id)]
        finally:
            almacen.cerrar()


# --- reanudación en modo stub -----------------------------------------------


class ReanudarEnModoStub(BaseCLI):
    def test_se_reanuda_con_el_stub_aunque_no_se_repita_el_flag(self):
        run_id = self.abrir_corrida("--stub")
        self.assertEqual(grafo.modo_de(self.store(), run_id), "stub")

        self.aprobar(run_id, "entrada")
        codigo, salida, error = self.cli("--reanudar", run_id)

        self.assertEqual(codigo, 0, error)
        self.assertIn(run_id, salida)

        # Lo decisivo: nadie construyó el productor del modelo. La corrida
        # avanzó, produjo y verificó, y no invocó a nadie ni pidió credencial.
        self.assertEqual(self.construcciones, [])
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)

        tipos = self.tipos(run_id)
        self.assertIn("iteracion_producida", tipos)
        self.assertIn("verificacion_ejecutada", tipos)

        # El costo por defecto también salió del modo: el nominal del stub.
        consumo = presupuesto.consumo(self.store(), run_id)
        self.assertAlmostEqual(consumo["costo"], correr.COSTO_STUB)

    def test_repetir_el_flag_no_cambia_nada(self):
        run_id = self.abrir_corrida("--stub")
        self.aprobar(run_id, "entrada")

        codigo, _, error = self.cli("--reanudar", run_id, "--stub")

        self.assertEqual(codigo, 0, error)
        self.assertEqual(self.construcciones, [])


# --- reanudación en modo modelo ---------------------------------------------


class ReanudarEnModoModelo(BaseCLI):
    def test_se_reanuda_con_el_modelo_y_el_nombre_queda_como_evidencia(self):
        self.credencial_disponible()

        run_id = self.abrir_corrida()
        self.assertEqual(grafo.modo_de(self.store(), run_id), "modelo")

        registrado = [
            e for e in self.store().leer_run(run_id) if e["tipo"] == grafo.EVENTO_MODO
        ][0]
        self.assertEqual(registrado["payload"]["modelo"], "modelo-de-prueba")

        self.aprobar(run_id, "entrada")
        codigo, _, error = self.cli("--reanudar", run_id)

        self.assertEqual(codigo, 0, error)
        # Una construcción al abrir y otra al reanudar, las dos contra el modelo
        # que el entorno declara: el nombre se toma del entorno, no del evento.
        self.assertEqual([c["modelo"] for c in self.construcciones], ["modelo-de-prueba"] * 2)
        self.assertIn("iteracion_producida", self.tipos(run_id))

    def test_sin_credencial_la_reanudacion_lo_dice_en_vez_de_caerse(self):
        self.credencial_disponible()
        run_id = self.abrir_corrida()
        self.aprobar(run_id, "entrada")

        del os.environ["ANTHROPIC_API_KEY"]
        codigo, _, error = self.cli("--reanudar", run_id)

        self.assertEqual(codigo, 1)
        self.assertIn("ANTHROPIC_API_KEY", error)


# --- la contradicción no se resuelve sola -----------------------------------


class ModoContradictorio(BaseCLI):
    """Pedir un modo distinto del registrado falla en los dos sentidos.

    Elegir uno de los dos sería elegir por alguien que cree algo falso: quien
    reanuda cree que corre con un productor y la corrida se abrió con el otro.
    """

    def test_reanudar_con_stub_una_corrida_del_modelo(self):
        self.credencial_disponible()
        run_id = self.abrir_corrida()
        self.aprobar(run_id, "entrada")
        self.construcciones.clear()

        codigo, _, error = self.cli("--reanudar", run_id, "--stub")

        self.assertEqual(codigo, 2)
        self.assertIn("modelo", error)
        self.assertIn(run_id, error)
        # Falló antes de construir nada y sin producir una sola iteración.
        self.assertEqual(self.construcciones, [])
        self.assertNotIn("iteracion_producida", self.tipos(run_id))

    def test_reanudar_con_modelo_una_corrida_del_stub(self):
        self.credencial_disponible()
        run_id = self.abrir_corrida("--stub")
        self.aprobar(run_id, "entrada")

        codigo, _, error = self.cli("--reanudar", run_id, "--modelo")

        self.assertEqual(codigo, 2)
        self.assertIn("stub", error)
        self.assertIn(run_id, error)
        self.assertEqual(self.construcciones, [])
        self.assertNotIn("iteracion_producida", self.tipos(run_id))

    def test_el_mensaje_nombra_siempre_el_modo_registrado(self):
        self.credencial_disponible()
        del_modelo = self.abrir_corrida()
        del_stub = self.abrir_corrida("--stub")

        _, _, error_modelo = self.cli("--reanudar", del_modelo, "--stub")
        _, _, error_stub = self.cli("--reanudar", del_stub, "--modelo")

        self.assertIn("se inició en modo 'modelo'", error_modelo)
        self.assertIn("se inició en modo 'stub'", error_stub)

    def test_los_dos_flags_juntos_es_error_de_uso(self):
        codigo, _, error = self.cli(
            "--pedido",
            str(self.ruta_pedido),
            "--definicion",
            str(self.ruta_definicion),
            "--stub",
            "--modelo",
        )

        self.assertEqual(codigo, 2)
        self.assertIn("dos modos distintos", error)


# --- corridas anteriores al registro ----------------------------------------


class CorridaSinModoRegistrado(BaseCLI):
    def test_no_se_reanuda_y_el_mensaje_dice_que_es_previa_al_registro(self):
        # Una corrida como las que quedaron en `factory.db` antes de este
        # cambio: tiene eventos, no tiene el hecho del modo.
        almacen = self.store()
        almacen.append("corrida-vieja", "run_iniciada", "plataforma", {"version": "1.0"})

        codigo, _, error = self.cli("--reanudar", "corrida-vieja")

        self.assertEqual(codigo, 1)
        self.assertIn("corrida-vieja", error)
        self.assertIn("anterior", error)
        self.assertEqual(self.construcciones, [])

    def test_una_corrida_que_no_existe_se_distingue_de_una_sin_modo(self):
        codigo, _, error = self.cli("--reanudar", "corrida-que-no-existe")

        self.assertEqual(codigo, 1)
        self.assertIn("no hay corrida", error)


class PrecedenciaDelEntornoSobreDotenv(unittest.TestCase):
    """De dónde sale la credencial cuando el entorno y el `.env` no coinciden.

    `load_dotenv` comprueba **presencia**, no contenido: una variable definida
    pero vacía está presente, así que le gana al `.env`. Pasó en una sesión
    real con `ANTHROPIC_API_KEY=""` exportada en el shell — la Fábrica moría
    diciendo "no configurada" con la key escrita en el `.env`, a un palmo, y
    el mensaje no daba ninguna pista de por qué.

    La regla que se comprueba acá es la que `_credencial_y_modelo` ya declara
    dos veces con sus `.strip()`: **una variable vacía es una variable no
    configurada**. Lo único que faltaba era aplicarla antes de leer el `.env`
    y no después.

    No hereda de `BaseCLI` a propósito: esa base neutraliza `load_dotenv` con
    un no-op para que la suite no lea la credencial real, y con eso puesto
    estos tests no comprobarían nada. Acá se ejerce el `load_dotenv` de verdad
    contra un `.env` de mentira en un temporal, nunca el del repo.
    """

    CLAVE_DEL_DOTENV = "clave-escrita-en-el-dotenv"

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.tmp = Path(self._dir.name)
        (self.tmp / ".env").write_text(
            "ANTHROPIC_API_KEY=%s\nANTHROPIC_MODEL=modelo-del-dotenv\n"
            % self.CLAVE_DEL_DOTENV,
            encoding="utf-8",
        )

        # `RAIZ` es lo que decide qué `.env` se lee. Apuntada al temporal, el
        # del repo queda fuera de alcance por construcción y no por disciplina.
        raiz = mock.patch.object(correr, "RAIZ", self.tmp)
        raiz.start()
        self.addCleanup(raiz.stop)

        entorno = mock.patch.dict(os.environ, {})
        entorno.start()
        self.addCleanup(entorno.stop)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("ANTHROPIC_MODEL", None)

    def test_una_variable_vacia_no_le_gana_al_dotenv(self):
        """El caso que rompió: definida y vacía es un hueco, no una decisión."""
        os.environ["ANTHROPIC_API_KEY"] = ""

        api_key, modelo = correr._credencial_y_modelo()

        self.assertEqual(api_key, self.CLAVE_DEL_DOTENV)
        self.assertEqual(modelo, "modelo-del-dotenv")

    def test_una_variable_con_solo_espacios_tambien_es_vacia(self):
        """El borde que el `.strip()` de la función ya contemplaba."""
        os.environ["ANTHROPIC_API_KEY"] = "   "

        api_key, _ = correr._credencial_y_modelo()

        self.assertEqual(api_key, self.CLAVE_DEL_DOTENV)

    def test_una_variable_con_valor_real_le_gana_al_dotenv(self):
        """La precedencia no se invierte, y este test es lo que lo impide.

        En producción y en CI no hay `.env`: el entorno *es* la configuración.
        Si alguien "arregla" esto con `override=True`, un `.env` local pasaría
        a ganarle a la credencial inyectada y acá se rompería.
        """
        os.environ["ANTHROPIC_API_KEY"] = "clave-inyectada-por-el-entorno"
        os.environ["ANTHROPIC_MODEL"] = "modelo-inyectado-por-el-entorno"

        api_key, modelo = correr._credencial_y_modelo()

        self.assertEqual(api_key, "clave-inyectada-por-el-entorno")
        self.assertEqual(modelo, "modelo-inyectado-por-el-entorno")

    def test_una_variable_ausente_se_toma_del_dotenv(self):
        """El caso normal en una máquina de desarrollo."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)

        api_key, modelo = correr._credencial_y_modelo()

        self.assertEqual(api_key, self.CLAVE_DEL_DOTENV)
        self.assertEqual(modelo, "modelo-del-dotenv")


if __name__ == "__main__":
    unittest.main(verbosity=2)
