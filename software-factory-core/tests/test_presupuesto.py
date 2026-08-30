"""Criterio de aceptación de T12. Quince tests, uno por fila de la tabla.

Los tres últimos no son de T12: cubren que el desglose del consumo y el evento
viejo de sólo `costo` se lean igual, que es lo que permite no migrar nada.
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from operational_state import OperationalState  # noqa: E402
from presupuesto import TechoAlcanzado, consumo, registrar_consumo, verificar  # noqa: E402

AHORA = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)


class Definicion(object):
    """Los tres techos, con la forma que expone el AgentDefinition de T10."""

    def __init__(self, costo=2, tiempo=20, iteraciones=5):
        self.techo_costo_usd = costo
        self.techo_tiempo_min = tiempo
        self.techo_iteraciones = iteraciones


class BasePresupuesto(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self._dir.name) / "estado" / "factory-test.db"
        self.store = OperationalState(self.ruta)
        self.run = self.store.nuevo_run_id()
        self.definicion = Definicion()

    def tearDown(self):
        self.store.cerrar()
        self._dir.cleanup()

    def en(self, minutos, tipo, actor="plataforma", payload=None):
        """Inserta un evento con marca de tiempo controlada.

        Escribe por SQL porque `append` sella el `ts` con el reloj real y estos
        tests necesitan reconstruir una línea de tiempo. Insertar está permitido:
        los triggers solo impiden modificar y borrar.
        """
        ts = (AHORA - timedelta(minutes=minutos)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        con = sqlite3.connect(str(self.ruta))
        with con:
            con.execute(
                "INSERT INTO evento (run_id, ts, tipo, actor, payload) VALUES (?,?,?,?,?)",
                (self.run, ts, tipo, actor, json.dumps(payload or {}, ensure_ascii=False)),
            )
        con.close()


class SumaDeDeltas(BasePresupuesto):
    def test_tres_consumos_de_medio_dan_uno_y_medio(self):
        for _ in range(3):
            registrar_consumo(self.store, self.run, 0.5)
        self.assertEqual(consumo(self.store, self.run, ahora=AHORA)["costo"], 1.5)


class ConsumoConDesglose(BasePresupuesto):
    """Los dos formatos conviven. No se migra nada."""

    def test_el_evento_nuevo_guarda_el_desglose_entero(self):
        registrar_consumo(
            self.store,
            self.run,
            {"costo": 0.5, "input_tokens": 8000, "output_tokens": 7000,
             "stop_reason": "max_tokens", "modelo": "claude-sonnet-5"},
        )
        (evento,) = [
            e for e in self.store.leer_run(self.run) if e["tipo"] == "consumo_registrado"
        ]
        self.assertEqual(evento["payload"]["output_tokens"], 7000)
        self.assertEqual(evento["payload"]["stop_reason"], "max_tokens")

    def test_el_evento_viejo_de_solo_costo_se_sigue_leyendo(self):
        self.en(1, "consumo_registrado", payload={"costo": 0.5})
        self.assertEqual(consumo(self.store, self.run, ahora=AHORA)["costo"], 0.5)

    def test_el_techo_suma_el_costo_total_sin_mirar_el_desglose(self):
        """Los dos formatos mezclados suman igual: el contador lee `costo`."""
        self.en(1, "consumo_registrado", payload={"costo": 1.0})
        registrar_consumo(self.store, self.run, {"costo": 0.6, "output_tokens": 900})
        registrar_consumo(self.store, self.run, 0.5)
        resultado = verificar(self.store, self.run, self.definicion, ahora=AHORA)
        self.assertIsInstance(resultado, TechoAlcanzado)
        self.assertAlmostEqual(resultado.techos[0]["valor"], 2.1)


class CostoBajoElTecho(BasePresupuesto):
    def test_devuelve_none(self):
        for _ in range(3):
            registrar_consumo(self.store, self.run, 0.5)
        self.assertIsNone(verificar(self.store, self.run, self.definicion, ahora=AHORA))


class CostoEnElTecho(BasePresupuesto):
    def test_devuelve_techo_alcanzado_nombrando_costo(self):
        for _ in range(4):
            registrar_consumo(self.store, self.run, 0.5)
        resultado = verificar(self.store, self.run, self.definicion, ahora=AHORA)
        self.assertIsInstance(resultado, TechoAlcanzado)
        self.assertIn("costo", resultado.nombres)
        self.assertEqual(resultado.techos[0]["valor"], 2.0)
        self.assertEqual(resultado.techos[0]["limite"], 2)


class CostoSobreElTecho(BasePresupuesto):
    def test_devuelve_techo_alcanzado(self):
        for _ in range(5):
            registrar_consumo(self.store, self.run, 0.5)
        resultado = verificar(self.store, self.run, self.definicion, ahora=AHORA)
        self.assertIsInstance(resultado, TechoAlcanzado)
        self.assertEqual(resultado.nombres, ("costo",))


class Iteraciones(BasePresupuesto):
    def test_cinco_verificaciones_con_techo_cinco_alcanzan(self):
        self.en(10, "run_iniciada")
        for _ in range(4):
            self.en(5, "verificacion_ejecutada")
        self.assertIsNone(verificar(self.store, self.run, Definicion(tiempo=60), ahora=AHORA))
        self.en(5, "verificacion_ejecutada")
        resultado = verificar(self.store, self.run, Definicion(tiempo=60), ahora=AHORA)
        self.assertIsInstance(resultado, TechoAlcanzado)
        self.assertIn("iteraciones", resultado.nombres)


class TiempoNeto(BasePresupuesto):
    def test_treinta_minutos_menos_una_ventana_de_quince_dan_quince(self):
        self.en(30, "run_iniciada")
        self.en(25, "gate_abierto", payload={"gate": "entrada"})
        self.en(10, "gate_resuelto", actor="CEO", payload={"gate": "entrada", "decision": "aprobado"})
        self.assertAlmostEqual(
            consumo(self.store, self.run, ahora=AHORA)["tiempo_min"], 15.0, places=6
        )


class GateAbiertoSinResolver(BasePresupuesto):
    def test_la_ventana_descuenta_desde_que_se_abrio_hasta_ahora(self):
        self.en(30, "run_iniciada")
        self.en(20, "gate_abierto", payload={"gate": "entrada"})
        # 30 de reloj, 20 esperando todavía: cuentan 10.
        self.assertAlmostEqual(
            consumo(self.store, self.run, ahora=AHORA)["tiempo_min"], 10.0, places=6
        )


class DosVentanas(BasePresupuesto):
    def test_se_descuentan_ambas(self):
        self.en(60, "run_iniciada")
        self.en(55, "gate_abierto", payload={"gate": "entrada"})
        self.en(45, "gate_resuelto", actor="CEO", payload={"gate": "entrada", "decision": "aprobado"})
        self.en(30, "gate_abierto", payload={"gate": "salida"})
        self.en(10, "gate_resuelto", actor="CEO", payload={"gate": "salida", "decision": "aprobado"})
        # 60 de reloj menos 10 y menos 20 de espera: 30.
        self.assertAlmostEqual(
            consumo(self.store, self.run, ahora=AHORA)["tiempo_min"], 30.0, places=6
        )


class TiempoBajoElTechoPorElDescuento(BasePresupuesto):
    def test_treinta_y_cinco_de_reloj_con_veinte_de_espera_devuelve_none(self):
        self.en(35, "run_iniciada")
        self.en(30, "gate_abierto", payload={"gate": "entrada"})
        self.en(10, "gate_resuelto", actor="CEO", payload={"gate": "entrada", "decision": "aprobado"})
        actual = consumo(self.store, self.run, ahora=AHORA)
        self.assertAlmostEqual(actual["tiempo_min"], 15.0, places=6)
        self.assertIsNone(verificar(self.store, self.run, self.definicion, ahora=AHORA))


class Prioridad(BasePresupuesto):
    def test_si_dos_techos_se_alcanzan_juntos_los_nombra_a_ambos(self):
        self.en(30, "run_iniciada")
        for _ in range(4):
            registrar_consumo(self.store, self.run, 0.5)
        resultado = verificar(self.store, self.run, self.definicion, ahora=AHORA)
        self.assertIsInstance(resultado, TechoAlcanzado)
        self.assertEqual(set(resultado.nombres), {"costo", "tiempo_min"})
        self.assertIn("costo", str(resultado))
        self.assertIn("tiempo_min", str(resultado))


class SinEfectos(BasePresupuesto):
    def test_verificar_no_escribe_ningun_evento(self):
        self.en(30, "run_iniciada")
        registrar_consumo(self.store, self.run, 0.5)
        antes = self.store._conexion.execute("SELECT COUNT(*) FROM evento").fetchone()[0]
        for _ in range(5):
            verificar(self.store, self.run, self.definicion, ahora=AHORA)
            verificar(self.store, self.run, Definicion(costo=0.1), ahora=AHORA)
        despues = self.store._conexion.execute("SELECT COUNT(*) FROM evento").fetchone()[0]
        self.assertEqual(antes, despues)
        # Tampoco emite run_cortada: cortar es responsabilidad de quien recibe el veredicto.
        tipos = [e["tipo"] for e in self.store.leer_run(self.run)]
        self.assertNotIn("run_cortada", tipos)


class CorridaSinConsumo(BasePresupuesto):
    def test_devuelve_ceros_y_no_falla(self):
        self.assertEqual(
            consumo(self.store, self.run, ahora=AHORA),
            {"costo": 0.0, "tiempo_min": 0.0, "iteraciones": 0},
        )
        self.en(0, "run_iniciada")
        actual = consumo(self.store, self.run, ahora=AHORA)
        self.assertEqual(actual["costo"], 0.0)
        self.assertEqual(actual["iteraciones"], 0)
        self.assertAlmostEqual(actual["tiempo_min"], 0.0, places=6)
        self.assertIsNone(verificar(self.store, self.run, self.definicion, ahora=AHORA))


if __name__ == "__main__":
    unittest.main(verbosity=2)
