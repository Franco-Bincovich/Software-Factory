"""La costura entre la CLI y la cadena.

Es el hueco que dejó pasar una corrida que produjo el plan, no ejecutó ninguna
unidad y cerró en verde. `test_cadena.py` prueba que la cadena funciona **dada**
una cadena: inyecta el coordinador él mismo. `test_correr.py` prueba el modo de
producción. Ninguno de los dos ejercitaba la decisión de **tener** cadena, que es
donde estaba el defecto.

Estos tests entran por `correr.main`, como entra una persona.
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))
sys.path.insert(0, str(RAIZ))

import gates  # noqa: E402
import grafo  # noqa: E402
import operational_state  # noqa: E402
from operational_state import OperationalState  # noqa: E402

import correr  # noqa: E402
from test_cadena import definicion_texto  # noqa: E402

PEDIDO = {
    "que_se_quiere": "Una herramienta que valide los datos de alta antes de importarlos",
    "para_que": "Evitar revisar el archivo a mano antes de cada importación",
    "alcance_excluido": ["interfaz gráfica"],
    "techo_costo_usd": 2.0,
    "techo_tiempo_min": 20,
    "techo_iteraciones": 3,
}


class BaseCLI(unittest.TestCase):
    def setUp(self):
        import json

        self._dir = tempfile.TemporaryDirectory()
        raiz = Path(self._dir.name)

        self.ruta_pedido = raiz / "pedido.json"
        self.ruta_pedido.write_text(json.dumps(PEDIDO), encoding="utf-8")
        self.ruta_requirement = raiz / "requirement.md"
        self.ruta_requirement.write_text(
            definicion_texto("requirement-agente-de-prueba", 2, 20, 5), encoding="utf-8"
        )
        self.ruta_developer = raiz / "developer.md"
        self.ruta_developer.write_text(
            definicion_texto("developer-agente-de-prueba", 1, 10, 3), encoding="utf-8"
        )
        self.ruta_db = raiz / "factory.db"
        self.ruta_checkpointer = raiz / "checkpoints.db"
        self.trabajo = raiz / "trabajo"

        # El temporal es el directorio de estado durante el test, igual que en
        # `BaseCadena`. Los tres flags de arriba redirigen tres rutas, pero
        # `entregas/` es una cuarta que deriva de `DIR_ESTADO` y no tiene flag:
        # sin esto, materializar la evidencia escribía en el área real y la
        # suite contaminaba datos de producción con su propia salida.
        # `operational_state.py` ya lo advierte: una sola variable gobierna el
        # estado, y redirigir las derivadas una por una deja agujeros.
        self._dir_estado = operational_state.DIR_ESTADO
        operational_state.DIR_ESTADO = raiz

    def tearDown(self):
        operational_state.DIR_ESTADO = self._dir_estado
        self._dir.cleanup()

    # --- utilidades ---------------------------------------------------------

    def cli(self, *argv):
        salida, error = io.StringIO(), io.StringIO()
        completos = list(argv) + [
            "--db", str(self.ruta_db),
            "--checkpointer", str(self.ruta_checkpointer),
            "--trabajo", str(self.trabajo),
        ]
        with redirect_stdout(salida), redirect_stderr(error):
            codigo = correr.main(completos)
        return codigo, salida.getvalue().strip(), error.getvalue().strip()

    def nueva(self, *flags):
        return self.cli(
            "--pedido", str(self.ruta_pedido),
            "--definicion", str(self.ruta_requirement),
            "--stub",
            *flags,
        )

    def store(self):
        almacen = OperationalState(self.ruta_db)
        self.addCleanup(almacen.cerrar)
        return almacen

    def eventos(self, run_id):
        return self.store().leer_run(run_id)

    def tipos(self, run_id):
        return [e["tipo"] for e in self.eventos(run_id)]

    def de_tipo(self, run_id, tipo):
        return [e for e in self.eventos(run_id) if e["tipo"] == tipo]

    def aprobar(self, run_id, gate):
        almacen = OperationalState(self.ruta_db)
        try:
            gates.resolver(almacen, run_id, gate, "aprobado")
        finally:
            almacen.cerrar()

    def hasta_el_gate_de_salida(self):
        """Abre una corrida con cadena, aprueba la entrada y la reanuda."""
        codigo, run_id, error = self.nueva(
            "--definicion-developer", str(self.ruta_developer)
        )
        self.assertEqual(codigo, 0, error)
        self.aprobar(run_id, "entrada")
        codigo, _, error = self.cli("--reanudar", run_id, "--stub")
        self.assertEqual(codigo, 0, error)
        return run_id


# --- 1 — la ausencia deja de ser una decisión --------------------------------


class DeclararLaCadenaEsObligatorio(BaseCLI):
    def test_sin_ninguno_de_los_dos_flags_no_arranca(self):
        codigo, salida, error = self.nueva()
        self.assertEqual(codigo, 2)
        self.assertIn("--definicion-developer", error)
        self.assertIn("--solo-plan", error)
        self.assertIn("no un olvido", error)
        self.assertEqual(salida, "")

    def test_y_no_deja_corrida_abierta(self):
        """Rechazar antes de abrir: una corrida que no arranca no deja rastro."""
        self.nueva()
        self.assertFalse(self.ruta_db.exists() and self._hay_eventos())

    def _hay_eventos(self):
        almacen = OperationalState(self.ruta_db)
        try:
            return bool(
                almacen._conexion.execute("SELECT COUNT(*) FROM evento").fetchone()[0]
            )
        finally:
            almacen.cerrar()

    def test_los_dos_flags_juntos_es_error_de_uso(self):
        codigo, _, error = self.nueva(
            "--definicion-developer", str(self.ruta_developer), "--solo-plan"
        )
        self.assertEqual(codigo, 2)
        self.assertIn("cosas opuestas", error)


# --- 2 — con el flag, la cadena ejecuta las unidades ------------------------


class ConCadena(BaseCLI):
    def test_la_corrida_ejecuta_las_unidades_del_plan(self):
        """El test que faltaba: entrar por la CLI y comprobar que hubo Developer."""
        run_id = self.hasta_el_gate_de_salida()

        lanzadas = self.de_tipo(run_id, "unidad_lanzada")
        self.assertTrue(lanzadas, "la cadena no ejecutó ninguna unidad")
        self.assertEqual([e["payload"]["unidad"] for e in lanzadas], ["U1"])
        self.assertTrue(self.de_tipo(run_id, "unidad_entregada"))

        aperturas = [e["payload"]["gate"] for e in self.de_tipo(run_id, "gate_abierto")]
        self.assertEqual(aperturas, ["entrada", "salida"])

    def test_declara_el_regimen_de_dos_gates_y_lo_cumple(self):
        run_id = self.hasta_el_gate_de_salida()
        (regimen,) = self.de_tipo(run_id, grafo.EVENTO_GATES)
        self.assertEqual(regimen["payload"]["gates"], ["entrada", "salida"])

        self.aprobar(run_id, "salida")
        codigo, _, error = self.cli("--reanudar", run_id, "--stub")
        self.assertEqual(codigo, 0, error)
        self.assertEqual(self.de_tipo(run_id, grafo.EVENTO_REGIMEN_INCUMPLIDO), [])
        (cerrada,) = self.de_tipo(run_id, "run_cerrada")
        self.assertEqual(cerrada["payload"]["resultado"], "entregado")

    def test_registra_la_definicion_de_developer_como_hecho(self):
        run_id = self.hasta_el_gate_de_salida()
        (hecho,) = self.de_tipo(run_id, correr.EVENTO_CADENA)
        # Guardada relativa al repositorio —ADR-014 punto 3—, pero tiene que
        # seguir señalando la misma definición.
        self.assertEqual(
            Path(correr.absoluta_desde(hecho["payload"]["developer"], correr.RAIZ_REPO)),
            Path(self.ruta_developer),
        )

    def test_la_definicion_se_registra_en_relativo(self):
        """ADR-014 punto 3: ningún evento nuevo escribe una ruta absoluta."""
        run_id = self.hasta_el_gate_de_salida()
        (hecho,) = self.de_tipo(run_id, correr.EVENTO_CADENA)
        self.assertFalse(Path(hecho["payload"]["developer"]).is_absolute())

    def test_se_reanuda_sin_repetir_el_flag(self):
        """El hecho manda: la cadena se rearma sola al reanudar."""
        run_id = self.hasta_el_gate_de_salida()
        self.assertTrue(self.de_tipo(run_id, "unidad_lanzada"))


# --- 3 — solo-plan es explícito y queda registrado --------------------------


class SoloPlan(BaseCLI):
    def corrida_solo_plan(self):
        codigo, run_id, error = self.nueva("--solo-plan")
        self.assertEqual(codigo, 0, error)
        self.aprobar(run_id, "entrada")
        codigo, _, error = self.cli("--reanudar", run_id, "--stub")
        self.assertEqual(codigo, 0, error)
        return run_id

    def test_cierra_con_el_plan_verificado_y_sin_ejecutar_unidades(self):
        run_id = self.corrida_solo_plan()
        self.assertEqual(self.de_tipo(run_id, "unidad_lanzada"), [])
        (cerrada,) = self.de_tipo(run_id, "run_cerrada")
        self.assertEqual(cerrada["payload"]["resultado"], grafo.SIN_DEVELOPER)

    def test_declara_un_solo_gate_y_no_se_contradice(self):
        """Sin Developer no hay entrega que aprobar: el régimen lo dice."""
        run_id = self.corrida_solo_plan()
        (regimen,) = self.de_tipo(run_id, grafo.EVENTO_GATES)
        self.assertEqual(regimen["payload"]["gates"], ["entrada"])
        aperturas = [e["payload"]["gate"] for e in self.de_tipo(run_id, "gate_abierto")]
        self.assertEqual(aperturas, ["entrada"])
        self.assertEqual(self.de_tipo(run_id, grafo.EVENTO_REGIMEN_INCUMPLIDO), [])

    def test_la_ausencia_de_cadena_queda_registrada_con_su_motivo(self):
        """Leyendo los eventos se distingue 'nadie pidió cadena' de 'no se armó'."""
        run_id = self.corrida_solo_plan()
        (hecho,) = self.de_tipo(run_id, correr.EVENTO_CADENA)
        self.assertIsNone(hecho["payload"]["developer"])
        self.assertEqual(hecho["payload"]["motivo"], correr.MOTIVO_SOLO_PLAN)

    def test_no_se_reanuda_pidiendo_cadena(self):
        codigo, run_id, error = self.nueva("--solo-plan")
        self.assertEqual(codigo, 0, error)
        self.aprobar(run_id, "entrada")
        codigo, _, error = self.cli(
            "--reanudar", run_id, "--stub",
            "--definicion-developer", str(self.ruta_developer),
        )
        self.assertEqual(codigo, 2)
        self.assertIn("se abrió con --solo-plan", error)


# --- 4 — el cierre comprueba el régimen que la corrida declaró --------------


class RegimenDeclaradoYCumplido(BaseCLI):
    def test_declarar_dos_gates_y_cerrar_con_uno_falla_ruidoso(self):
        """La forma exacta del defecto: hay cadena declarada y nadie ejecutó nada.

        Se inyecta un coordinador que se comporta como si no hubiera Developer.
        El régimen queda declarado con dos Gates —porque hay coordinador— y el
        cierre tiene que negarse en vez de escribir `run_cerrada` en verde.
        """
        store = self.store()
        checkpointer = grafo.abrir_checkpointer(self.ruta_checkpointer)

        def coordinador_que_no_hace_nada(estado):
            return {"resultado": grafo.SIN_DEVELOPER}

        run_id = grafo.ejecutar(
            str(self.ruta_requirement), dict(PEDIDO), correr.producir_stub,
            store, checkpointer, None, 0.1, modo=grafo.MODO_STUB,
            ejecutar_unidades_fn=coordinador_que_no_hace_nada,
        )
        gates.resolver(store, run_id, "entrada", "aprobado")

        with self.assertRaises(grafo.RegimenIncumplido) as capturado:
            grafo.reanudar(
                run_id, store, checkpointer, correr.producir_stub, None, 0.1,
                coordinador_que_no_hace_nada,
            )

        mensaje = str(capturado.exception)
        self.assertIn("salida", mensaje)
        self.assertIn("se contradice", mensaje)

        # El hecho queda escrito y la corrida no cierra: mejor una corrida sin
        # cerrar que un `run_cerrada` que afirma algo falso.
        (incumplido,) = self.de_tipo(run_id, grafo.EVENTO_REGIMEN_INCUMPLIDO)
        self.assertEqual(incumplido["payload"]["faltan"], ["salida"])
        self.assertEqual(incumplido["payload"]["declarados"], ["entrada", "salida"])
        self.assertEqual(self.de_tipo(run_id, "run_cerrada"), [])


class VerificarRegimen(unittest.TestCase):
    """La comprobación, aislada. Vale para todo cierre, no solo para este caso."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.store = OperationalState(Path(self._dir.name) / "factory.db")
        self.addCleanup(self._dir.cleanup)
        self.addCleanup(self.store.cerrar)
        self.run = "corrida-de-prueba"

    def declarar(self, gates_):
        self.store.append(
            self.run, grafo.EVENTO_GATES, "plataforma",
            {"gates": list(gates_), "suprimido": "salida_de_plan", "motivo": "x"},
        )

    def aprobar(self, gate):
        self.store.append(self.run, "gate_abierto", "plataforma", {"gate": gate})
        self.store.append(
            self.run, "gate_resuelto", "CEO", {"gate": gate, "decision": "aprobado"}
        )

    def test_un_cierre_que_cumple_no_levanta(self):
        self.declarar(["entrada", "salida"])
        self.aprobar("entrada")
        self.aprobar("salida")
        grafo.verificar_regimen(self.store, self.run, "entregado")

    def test_un_gate_declarado_y_no_aprobado_levanta(self):
        self.declarar(["entrada", "salida"])
        self.aprobar("entrada")
        with self.assertRaises(grafo.RegimenIncumplido):
            grafo.verificar_regimen(self.store, self.run, "entregado")

    def test_un_gate_abierto_que_nadie_declaro_tambien_levanta(self):
        """La contradicción vale para los dos lados."""
        self.declarar(["entrada"])
        self.aprobar("entrada")
        self.aprobar("salida")
        with self.assertRaises(grafo.RegimenIncumplido):
            grafo.verificar_regimen(self.store, self.run, grafo.SIN_DEVELOPER)

    def test_un_rechazo_cierra_legitimamente_sin_cumplir_el_regimen(self):
        self.declarar(["entrada", "salida"])
        self.store.append(self.run, "gate_abierto", "plataforma", {"gate": "entrada"})
        self.store.append(
            self.run, "gate_resuelto", "CEO",
            {"gate": "entrada", "decision": "rechazado", "motivo": "no"},
        )
        grafo.verificar_regimen(self.store, self.run, "rechazado_en_entrada")

    def test_un_escalamiento_tampoco_prometio_cumplirlo(self):
        self.declarar(["entrada", "salida"])
        self.aprobar("entrada")
        grafo.verificar_regimen(self.store, self.run, "escalado_por_techo")

    def test_una_corrida_sin_regimen_declarado_no_se_comprueba(self):
        """No se puede comprobar lo que nadie declaró: son corridas anteriores."""
        self.aprobar("entrada")
        grafo.verificar_regimen(self.store, self.run, "entregado")


if __name__ == "__main__":
    unittest.main(verbosity=2)
