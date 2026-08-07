"""Criterio de aceptación de T13.

Un test por cada fila de la tabla: son nueve. Todos operan sobre una base
temporal que se crea y se destruye con cada test. La base real nunca se toca.
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from operational_state import OperationalState, RegistroRechazado  # noqa: E402


class BaseTemporal(unittest.TestCase):
    """Cada test corre contra su propio archivo, nunca contra el almacén real."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self._dir.name) / "estado" / "factory-test.db"
        self.store = OperationalState(self.ruta)
        self.run = self.store.nuevo_run_id()

    def tearDown(self):
        self.store.cerrar()
        self._dir.cleanup()

    def assertNoEsLaBaseReal(self):
        self.assertNotIn("software-factory-state", str(self.ruta))


class EscribirYLeer(BaseTemporal):
    def test_cinco_eventos_se_leen_en_orden(self):
        self.assertNoEsLaBaseReal()
        tipos = [
            "run_iniciada",
            "pedido_recibido",
            "techos_declarados",
            "iteracion_producida",
            "run_finalizada",
        ]
        ids = [self.store.append(self.run, t, "plataforma", {"n": i}) for i, t in enumerate(tipos)]

        eventos = self.store.leer_run(self.run)
        self.assertEqual(len(eventos), 5)
        self.assertEqual([e["tipo"] for e in eventos], tipos)
        self.assertEqual([e["id"] for e in eventos], sorted(ids))
        self.assertEqual([e["payload"]["n"] for e in eventos], [0, 1, 2, 3, 4])


class InmutabilidadUpdate(BaseTemporal):
    def test_update_falla_con_error_de_la_base(self):
        self.store.append(self.run, "run_iniciada", "plataforma", {"v": "1.0"})
        con = sqlite3.connect(str(self.ruta))
        with self.assertRaises(sqlite3.DatabaseError) as capturado:
            con.execute("UPDATE evento SET actor = 'otro'")
        self.assertIn("inmutable", str(capturado.exception))
        con.close()
        # El evento sigue como se escribió.
        self.assertEqual(self.store.leer_run(self.run)[0]["actor"], "plataforma")


class InmutabilidadDelete(BaseTemporal):
    def test_delete_falla_con_error_de_la_base(self):
        self.store.append(self.run, "run_iniciada", "plataforma", {"v": "1.0"})
        con = sqlite3.connect(str(self.ruta))
        with self.assertRaises(sqlite3.DatabaseError) as capturado:
            con.execute("DELETE FROM evento")
        self.assertIn("inmutable", str(capturado.exception))
        con.close()
        self.assertEqual(len(self.store.leer_run(self.run)), 1)


class Reconstruccion(BaseTemporal):
    def test_una_corrida_se_reconstruye_solo_con_sus_eventos(self):
        self.store.append(
            self.run, "run_iniciada", "plataforma",
            {"agent_definition_id": "requirement-agent", "version": "1.0"},
        )
        self.store.append(
            self.run, "pedido_recibido", "plataforma",
            {"pedido": "Herramienta que lee un CSV de altas de empleados."},
        )
        self.store.append(
            self.run, "techos_declarados", "plataforma",
            {"costo": 2, "tiempo": 20, "iteraciones": 5},
        )
        self.store.append(
            self.run, "gate_abierto", "plataforma", {"gate": "entrada", "somete": "pedido y techos"}
        )
        self.store.append(
            self.run, "gate_resuelto", "CEO", {"gate": "entrada", "decision": "aprobado"}
        )
        self.store.append(
            self.run, "iteracion_producida", "requirement-agent", {"iteracion": 1, "unidades": 4},
        )
        self.store.append(
            self.run, "verificacion_ejecutada", "plataforma",
            {"valido": True, "incumplimientos": []},
        )
        self.store.append(
            self.run, "consumo_registrado", "plataforma",
            {"costo": 0.4, "tiempo": 3, "iteraciones": 1},
        )
        self.store.append(self.run, "run_finalizada", "plataforma", {"resultado": "completado"})

        # Todo lo que sigue sale exclusivamente de leer_run: ninguna otra fuente.
        eventos = self.store.leer_run(self.run)
        por_tipo = {e["tipo"]: e for e in eventos}

        self.assertEqual(por_tipo["run_iniciada"]["payload"]["agent_definition_id"], "requirement-agent")
        self.assertIn("CSV de altas de empleados", por_tipo["pedido_recibido"]["payload"]["pedido"])
        self.assertEqual(por_tipo["techos_declarados"]["payload"]["costo"], 2)
        self.assertEqual(por_tipo["gate_resuelto"]["payload"]["decision"], "aprobado")
        self.assertEqual(por_tipo["gate_resuelto"]["actor"], "CEO")
        self.assertTrue(por_tipo["verificacion_ejecutada"]["payload"]["valido"])
        self.assertEqual(por_tipo["run_finalizada"]["payload"]["resultado"], "completado")
        # Quién hizo cada cosa queda registrado en cada evento.
        self.assertEqual(por_tipo["iteracion_producida"]["actor"], "requirement-agent")
        # El orden de lo ocurrido es reconstruible.
        self.assertEqual(
            [e["tipo"] for e in eventos][:3],
            ["run_iniciada", "pedido_recibido", "techos_declarados"],
        )


class ActorObligatorio(BaseTemporal):
    def test_actor_vacio_o_sistema_es_rechazado(self):
        for actor in ("", "   ", "sistema", "SISTEMA", "Sistema"):
            with self.subTest(actor=actor):
                with self.assertRaises(RegistroRechazado):
                    self.store.append(self.run, "run_iniciada", actor, {"v": 1})
        self.assertEqual(self.store.leer_run(self.run), [])
        # Los actores válidos de V0.1 sí entran.
        for actor in ("requirement-agent", "plataforma", "CEO"):
            self.store.append(self.run, "run_iniciada", actor, {"v": 1})
        self.assertEqual(len(self.store.leer_run(self.run)), 3)


class Secretos(BaseTemporal):
    def test_clave_prohibida_en_cualquier_nivel_es_rechazada(self):
        payloads = [
            {"api_key": "abc"},
            {"credenciales": {"api_key": "abc"}},
            {"a": {"b": {"c": {"API_KEY": "abc"}}}},
            {"conexiones": [{"nombre": "x", "api_key": "abc"}]},
            {"a": [[{"token": "abc"}]]},
            {"cfg": {"lista": [{"ok": 1}, {"private_key": "abc"}]}},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(RegistroRechazado) as capturado:
                    self.store.append(self.run, "pedido_recibido", "plataforma", payload)
                self.assertIn("claves prohibidas", str(capturado.exception))

        # Las nueve claves de la spec, cada una a un nivel anidado.
        for clave in (
            "password", "passwd", "secret", "token", "api_key",
            "apikey", "credential", "authorization", "private_key",
        ):
            with self.subTest(clave=clave):
                with self.assertRaises(RegistroRechazado):
                    self.store.append(
                        self.run, "pedido_recibido", "plataforma", {"n": [{clave.upper(): "x"}]}
                    )

        # Nada de lo rechazado quedó escrito.
        self.assertEqual(self.store.leer_run(self.run), [])
        # Una clave de nombre parecido pero distinta sí entra: el control es léxico.
        self.store.append(self.run, "pedido_recibido", "plataforma", {"api_key_id": "publico"})
        self.assertEqual(len(self.store.leer_run(self.run)), 1)


class Consumo(BaseTemporal):
    def test_devuelve_el_acumulado_tras_varios_consumo_registrado(self):
        self.assertEqual(
            self.store.consumo(self.run), {"costo": 0, "tiempo": 0, "iteraciones": 0}
        )
        for costo, tiempo, iteraciones in ((0.4, 3, 1), (0.9, 7, 2), (1.5, 12, 3)):
            self.store.append(
                self.run, "consumo_registrado", "plataforma",
                {"costo": costo, "tiempo": tiempo, "iteraciones": iteraciones},
            )
        self.assertEqual(
            self.store.consumo(self.run), {"costo": 1.5, "tiempo": 12, "iteraciones": 3}
        )
        # El consumo es por corrida.
        otro = self.store.nuevo_run_id()
        self.assertEqual(self.store.consumo(otro), {"costo": 0, "tiempo": 0, "iteraciones": 0})


class Gates(BaseTemporal):
    def test_solo_devuelve_los_abiertos_sin_resolucion_posterior(self):
        self.assertEqual(self.store.gates_pendientes(), [])

        self.store.append(self.run, "gate_abierto", "plataforma", {"gate": "entrada"})
        self.assertEqual([g["payload"]["gate"] for g in self.store.gates_pendientes()], ["entrada"])

        self.store.append(self.run, "gate_resuelto", "CEO", {"gate": "entrada", "decision": "aprobado"})
        self.assertEqual(self.store.gates_pendientes(), [])

        # Dos gates abiertos, uno resuelto: queda el otro.
        self.store.append(self.run, "gate_abierto", "plataforma", {"gate": "salida"})
        otro = self.store.nuevo_run_id()
        self.store.append(otro, "gate_abierto", "plataforma", {"gate": "entrada"})
        pendientes = self.store.gates_pendientes()
        self.assertEqual(
            sorted((g["run_id"], g["payload"]["gate"]) for g in pendientes),
            sorted([(self.run, "salida"), (otro, "entrada")]),
        )

        # Resolver el de una corrida no cierra el de la otra.
        self.store.append(otro, "gate_resuelto", "CEO", {"gate": "entrada", "decision": "rechazado"})
        pendientes = self.store.gates_pendientes()
        self.assertEqual([(g["run_id"], g["payload"]["gate"]) for g in pendientes], [(self.run, "salida")])


class AislamientoEntreCorridas(BaseTemporal):
    def test_dos_run_id_distintos_no_se_mezclan(self):
        run_a = self.store.nuevo_run_id()
        run_b = self.store.nuevo_run_id()
        self.assertNotEqual(run_a, run_b)

        for i in range(3):
            self.store.append(run_a, "iteracion_producida", "requirement-agent", {"n": i, "de": "A"})
        for i in range(2):
            self.store.append(run_b, "iteracion_producida", "requirement-agent", {"n": i, "de": "B"})

        eventos_a = self.store.leer_run(run_a)
        eventos_b = self.store.leer_run(run_b)
        self.assertEqual(len(eventos_a), 3)
        self.assertEqual(len(eventos_b), 2)
        self.assertTrue(all(e["payload"]["de"] == "A" for e in eventos_a))
        self.assertTrue(all(e["payload"]["de"] == "B" for e in eventos_b))
        self.assertTrue(all(e["run_id"] == run_a for e in eventos_a))
        self.assertEqual(self.store.leer_run("run-que-no-existe"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
