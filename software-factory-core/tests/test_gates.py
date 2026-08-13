"""Criterio de aceptación de T11. Once tests, uno por fila de la tabla."""

import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import gates  # noqa: E402
from gates import GateInvalido, abrir, esta_bloqueada, resolucion, resolver  # noqa: E402
from operational_state import OperationalState  # noqa: E402

SOMETE = {"pedido": "un CSV de altas", "techos": {"costo": 2, "tiempo": 20, "iteraciones": 5}}


class BaseGates(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self._dir.name) / "estado" / "factory-test.db"
        self.store = OperationalState(self.ruta)
        self.run = self.store.nuevo_run_id()

    def tearDown(self):
        self.store.cerrar()
        self._dir.cleanup()

    def eventos_totales(self):
        return self.store._conexion.execute("SELECT COUNT(*) FROM evento").fetchone()[0]

    def aprobar_entrada(self, run_id=None):
        run_id = self.run if run_id is None else run_id
        abrir(self.store, run_id, "entrada", SOMETE)
        resolver(self.store, run_id, "entrada", "aprobado")


class AbrirYBloquear(BaseGates):
    def test_tras_abrir_la_corrida_queda_bloqueada(self):
        self.assertFalse(esta_bloqueada(self.store, self.run))
        abrir(self.store, self.run, "entrada", SOMETE)
        self.assertTrue(esta_bloqueada(self.store, self.run))
        evento = self.store.leer_run(self.run)[0]
        self.assertEqual(evento["tipo"], "gate_abierto")
        self.assertEqual(evento["payload"]["somete"], SOMETE)


class ResolverAprobando(BaseGates):
    def test_desbloquea_y_devuelve_la_decision(self):
        abrir(self.store, self.run, "entrada", SOMETE)
        resolver(self.store, self.run, "entrada", "aprobado", "el pedido es claro")
        self.assertFalse(esta_bloqueada(self.store, self.run))
        self.assertEqual(
            resolucion(self.store, self.run, "entrada"),
            {"decision": "aprobado", "motivo": "el pedido es claro"},
        )


class RechazoSinMotivo(BaseGates):
    def test_falla_y_no_escribe_evento(self):
        abrir(self.store, self.run, "entrada", SOMETE)
        antes = self.eventos_totales()
        for motivo in (None, "", "   "):
            with self.subTest(motivo=motivo):
                with self.assertRaises(GateInvalido) as capturado:
                    resolver(self.store, self.run, "entrada", "rechazado", motivo)
                self.assertIn("exige un motivo", str(capturado.exception))
        self.assertEqual(self.eventos_totales(), antes)
        self.assertTrue(esta_bloqueada(self.store, self.run))


class AprobacionSinMotivo(BaseGates):
    def test_se_acepta(self):
        abrir(self.store, self.run, "entrada", SOMETE)
        resolver(self.store, self.run, "entrada", "aprobado")
        self.assertEqual(
            resolucion(self.store, self.run, "entrada"), {"decision": "aprobado", "motivo": None}
        )


class ResolverGateNoAbierto(BaseGates):
    def test_falla_nombrando_la_corrida_y_el_gate(self):
        with self.assertRaises(GateInvalido) as capturado:
            resolver(self.store, self.run, "salida", "aprobado")
        mensaje = str(capturado.exception)
        self.assertIn(self.run, mensaje)
        self.assertIn("salida", mensaje)
        self.assertIn("no está abierto", mensaje)
        self.assertEqual(self.eventos_totales(), 0)


class ResolverDosVeces(BaseGates):
    def test_el_segundo_intento_falla(self):
        abrir(self.store, self.run, "entrada", SOMETE)
        resolver(self.store, self.run, "entrada", "aprobado")
        with self.assertRaises(GateInvalido) as capturado:
            resolver(self.store, self.run, "entrada", "rechazado", "me arrepentí")
        mensaje = str(capturado.exception)
        self.assertIn("ya fue resuelto", mensaje)
        self.assertIn(self.run, mensaje)
        self.assertEqual(resolucion(self.store, self.run, "entrada")["decision"], "aprobado")


class SalidaAntesDeEntrada(BaseGates):
    def test_abrir_salida_sin_entrada_aprobada_falla(self):
        with self.assertRaises(GateInvalido) as capturado:
            abrir(self.store, self.run, "salida", {"plan": "..."})
        self.assertIn("el de entrada no fue aprobado", str(capturado.exception))

        # Tampoco alcanza con haberlo abierto, ni con haberlo rechazado.
        abrir(self.store, self.run, "entrada", SOMETE)
        with self.assertRaises(GateInvalido):
            abrir(self.store, self.run, "salida", {"plan": "..."})
        resolver(self.store, self.run, "entrada", "rechazado", "ambiguo")
        with self.assertRaises(GateInvalido):
            abrir(self.store, self.run, "salida", {"plan": "..."})


class DuplicadoDelMismoTipo(BaseGates):
    def test_abrir_dos_gates_de_entrada_falla(self):
        abrir(self.store, self.run, "entrada", SOMETE)
        with self.assertRaises(GateInvalido) as capturado:
            abrir(self.store, self.run, "entrada", SOMETE)
        mensaje = str(capturado.exception)
        self.assertIn("ya abrió el Gate de entrada", mensaje)
        self.assertIn(self.run, mensaje)
        self.assertEqual(self.eventos_totales(), 1)


class ActorSiempreCEO(BaseGates):
    def test_el_evento_gate_resuelto_tiene_actor_ceo(self):
        self.aprobar_entrada()
        abrir(self.store, self.run, "salida", {"plan": "...", "veredicto": "valido"})
        resolver(self.store, self.run, "salida", "rechazado", "el plan tiene un hueco")
        resueltos = [e for e in self.store.leer_run(self.run) if e["tipo"] == "gate_resuelto"]
        self.assertEqual(len(resueltos), 2)
        for evento in resueltos:
            self.assertEqual(evento["actor"], "CEO")


class Listar(BaseGates):
    def test_muestra_los_abiertos_de_dos_corridas_sin_mezclarlos(self):
        otro = self.store.nuevo_run_id()
        abrir(self.store, self.run, "entrada", {"pedido": "corrida A"})
        abrir(self.store, otro, "entrada", {"pedido": "corrida B"})

        pendientes = gates.abiertos(self.store)
        self.assertEqual(
            sorted(g["run_id"] for g in pendientes), sorted([self.run, otro])
        )
        por_run = {g["run_id"]: g["payload"]["somete"]["pedido"] for g in pendientes}
        self.assertEqual(por_run[self.run], "corrida A")
        self.assertEqual(por_run[otro], "corrida B")

        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = gates.main(["--listar", "--db", str(self.ruta)])
        self.assertEqual(codigo, 0)
        texto = salida.getvalue()
        self.assertIn(self.run, texto)
        self.assertIn(otro, texto)
        self.assertIn("corrida A", texto)
        self.assertIn("corrida B", texto)


class SinAprobacionPorVencimiento(BaseGates):
    """La ausencia es deliberada y se verifica por inspección del módulo."""

    TOKENS = (
        "timeout", "vencimiento", "vence", "expir", "caduc", "deadline",
        "plazo", "autoaprob", "auto_aprob", "silencio", "default",
    )

    def test_el_modulo_no_contempla_aprobacion_por_vencimiento(self):
        fuente = (RAIZ / "src" / "gates.py").read_text(encoding="utf-8")
        for token in self.TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(
                    token, fuente.lower(),
                    "gates.py menciona '%s': no debe existir parámetro, constante, "
                    "rama ni comentario que contemple aprobación por vencimiento" % token,
                )

        # Ninguna firma acepta un parámetro de tiempo de espera.
        for nombre in ("abrir", "resolver", "esta_bloqueada", "resolucion", "abiertos"):
            firma = re.search(r"^def %s\((.*?)\):" % nombre, fuente, re.MULTILINE | re.DOTALL)
            self.assertIsNotNone(firma)
            self.assertNotIn("=", firma.group(1).replace("motivo=None", ""))

        # Un Gate abierto sigue bloqueando, se lo consulte cuantas veces se lo consulte.
        abrir(self.store, self.run, "entrada", SOMETE)
        for _ in range(5):
            self.assertTrue(esta_bloqueada(self.store, self.run))
        self.assertIsNone(resolucion(self.store, self.run, "entrada"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
