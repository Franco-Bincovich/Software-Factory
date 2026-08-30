"""Criterio de aceptación de la cadena de V0.2.

Cubre lo que la cadena agrega sobre T14: dos corridas encadenadas, una unidad por
corrida de Developer, el reintento tras rechazo, la detención cuando una unidad
falla, el techo de la cadena y el directorio de trabajo.

Todo corre contra un Operational State, un checkpointer y un directorio de
trabajo temporales. La base real nunca se abre y nada se escribe fuera del
temporal.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ))

import cadena  # noqa: E402
import deposito  # noqa: E402
import gates  # noqa: E402
import grafo  # noqa: E402
import grafo_developer  # noqa: E402
from grafo import UnidadAmbigua  # noqa: E402
import operational_state  # noqa: E402
import presupuesto  # noqa: E402
import verificacion_sustantiva  # noqa: E402
from agent_loader import cargar  # noqa: E402
from operational_state import OperationalState  # noqa: E402

from correr import producir_entrega_stub  # noqa: E402

PEDIDO = {
    "que_se_quiere": "Herramienta que valida los datos de alta antes de importarlos",
    "para_que": "Evitar revisar el archivo a mano antes de cada importación",
    "alcance_excluido": ["interfaz gráfica"],
    "techo_costo_usd": 2,
    "techo_tiempo_min": 20,
    "techo_iteraciones": 5,
}

RASTREO = "valida los datos de alta"


def definicion_texto(agent_id, costo, tiempo, iteraciones):
    """Una Agent Definition que T10 acepta: trece campos y techos coherentes."""
    return """---
titulo: {agent_id}
tipo: agent-definition
estado: aceptado
aprobado: 2026-08-26
version: 1.0
owner: CEO
agent_id: {agent_id}
techo_costo_usd: {costo}
techo_tiempo_min: {tiempo}
techo_iteraciones: {iteraciones}
herramientas: [leer_unidad, leer_vault, escribir_directorio_trabajo]
vault_lectura: []
vault_escritura: []
memory: none
---

# {agent_id} — Agent Definition

## 1. Identidad
Agente de prueba de la cadena. No corre fuera de los tests.
## 2. Propósito
Producir el artefacto que le corresponde en la cadena.
## 3. Entrada
Lo que la etapa anterior dejó verificado.
## 4. Salida
Un artefacto que valida contra su verificador.
## 5. Herramientas autorizadas
Las declaradas en el frontmatter, y ninguna más.
## 6. Alcance de decisión
Decide el método, no el objetivo ni la aceptación.
## 7. Criterio de terminación
El artefacto pasa su verificación estructural.
## 8. Presupuesto
**Costo:** USD {costo}. **Tiempo:** {tiempo} minutos. **Iteraciones:** {iteraciones}.
## 9. Comportamiento ante fallo
Corrige el artefacto anterior. Regenerarlo íntegro se trata como agotamiento.
## 10. Escalamiento
Alcanzar cualquier techo corta la corrida y escala al CEO.
## 11. Acceso al conocimiento
No escribe en el Vault.
## 12. Evidencia
Toda la corrida queda en el Operational State.
## 13. Dependencias
El contrato de su artefacto y su verificador.
""".format(agent_id=agent_id, costo=costo, tiempo=tiempo, iteraciones=iteraciones)


def _unidad(uid, dependencias):
    return {
        "id": uid,
        "enunciado": "Resolver la parte %s del trabajo." % uid,
        "criterios": [
            {
                "condicion_observable": "Corriendo la unidad %s sobre su entrada, qué devuelve." % uid,
                "resultado_esperado": "Devuelve lo que el pedido describe, sin error.",
                "procedimiento": "Abrir pruebas.html y contar las filas en verde.",
            }
        ],
        "dependencias": list(dependencias),
        "rastreo": RASTREO,
        "artefacto_esperado": "Entregable ejecutable con su prueba asociada.",
    }


def plan_de(unidades):
    return {
        "plan_id": "PLAN-CADENA-1",
        "run_id": "asignado-por-la-corrida",
        "pedido_id": "asignado-por-el-intake",
        "sucede_a": None,
        "restricciones": {
            "techo_costo": 2,
            "techo_tiempo_min": 20,
            "techo_iteraciones": 5,
            "alcance_excluido": ["interfaz gráfica"],
        },
        "unidades": [_unidad(uid, deps) for uid, deps in unidades],
        "supuestos": ["El archivo entra en memoria."],
        "fuera_de_alcance": ["Corregir las filas rechazadas."],
    }


UNA_UNIDAD = [("U1", [])]
# U1 y U3 no dependen de nadie; U2 depende de U1. El orden determinista es
# U1, U3, U2: dentro de cada tanda habilitada se ordena por identificador.
TRES_UNIDADES = [("U1", []), ("U2", ["U1"]), ("U3", [])]


def productor_de(plan):
    def producir(pedido, plan_anterior, incumplimientos, contexto_vault):
        return plan
    return producir


def developer_que_falla_en(unidad_id):
    """Entrega una entrega inválida —sin demo.html— solo para esa unidad."""

    def producir(unidad, contexto, entrega_anterior, incumplimientos, contexto_vault,
                 paquete=None):
        entrega = producir_entrega_stub(unidad, contexto, None, [], contexto_vault)
        if unidad["id"] == unidad_id:
            entrega["archivos"] = [
                a for a in entrega["archivos"] if a["ruta"] != "demo.html"
            ]
        return entrega

    return producir


def developer_que_corrige(registro):
    """Primero entrega sin demo.html; corrige recién con los incumplimientos."""

    def producir(unidad, contexto, entrega_anterior, incumplimientos, contexto_vault,
                 paquete=None):
        registro.append(
            {
                "unidad": unidad["id"],
                "entrega_anterior": entrega_anterior,
                "incumplimientos": list(incumplimientos),
            }
        )
        if entrega_anterior is None:
            entrega = producir_entrega_stub(unidad, contexto, None, [], contexto_vault)
            entrega["archivos"] = [
                a for a in entrega["archivos"] if a["ruta"] != "demo.html"
            ]
            return entrega
        return producir_entrega_stub(
            unidad, contexto, entrega_anterior, incumplimientos, contexto_vault
        )

    return producir


def developer_que_declara_ambigua(unidad_id, motivo):
    """Devuelve la entrega vacía del contrato para esa unidad."""

    def producir(unidad, contexto, entrega_anterior, incumplimientos, contexto_vault,
                 paquete=None):
        if unidad["id"] == unidad_id:
            raise UnidadAmbigua(motivo, consumo=0.05)
        return producir_entrega_stub(
            unidad, contexto, entrega_anterior, incumplimientos, contexto_vault
        )

    return producir


class BaseCadena(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        raiz = Path(self._dir.name)

        self.ruta_requirement = raiz / "requirement.md"
        self.ruta_requirement.write_text(
            definicion_texto("requirement-agente-de-prueba", 2, 20, 5), encoding="utf-8"
        )
        self.ruta_developer = raiz / "developer.md"
        self.ruta_developer.write_text(
            definicion_texto("developer-agente-de-prueba", 1, 10, 3), encoding="utf-8"
        )

        self.trabajo = raiz / "trabajo"
        self.store = OperationalState(raiz / "factory.db")
        self.checkpointer = grafo.abrir_checkpointer(raiz / "checkpoints.db")
        self.definicion_developer = cargar(str(self.ruta_developer))

        # El temporal es el directorio de estado durante el test, igual que en
        # producción: las rutas de los eventos se relativizan contra él, y si el
        # trabajo quedara afuera lo relativo sería una cadena de `..` seguida de
        # la ruta absoluta, o sea nada relativo.
        self._dir_estado = operational_state.DIR_ESTADO
        operational_state.DIR_ESTADO = raiz

    def tearDown(self):
        operational_state.DIR_ESTADO = self._dir_estado
        self.store.cerrar()
        self._dir.cleanup()

    # --- utilidades ---------------------------------------------------------

    def de_tipo(self, run_id, tipo):
        return [e for e in self.store.leer_run(run_id) if e["tipo"] == tipo]

    def ruta_de_trabajo(self, run_id):
        """El directorio de la corrida, absoluto, para poder mirar el disco.

        El evento lo guarda relativo al directorio de estado —ADR-014 punto 3—,
        así que un test que quiera abrir la carpeta tiene que expandirlo. Que la
        ruta guardada sea relativa lo comprueba `RutasRelativasEnLosEventos`;
        acá el punto es otro y la ruta es solo un medio.
        """
        return Path(cadena.directorio_registrado(self.store, run_id))

    def nodo(self, developer=producir_entrega_stub, costo=0.0):
        return cadena.nodo_ejecutar_unidades(
            self.store, self.definicion_developer, developer, str(self.trabajo),
            None, costo,
        )

    def correr_cadena(self, unidades=UNA_UNIDAD, developer=producir_entrega_stub,
                      costo=0.0, pedido=None, conservar=False):
        """Corre hasta que la cadena frena: en el Gate de salida o al escalar."""
        plan = plan_de(unidades)
        borrar = None if conservar else cadena.borrar_directorio
        run = grafo.ejecutar(
            str(self.ruta_requirement),
            dict(PEDIDO if pedido is None else pedido),
            productor_de(plan),
            self.store,
            self.checkpointer,
            None,
            costo,
            modo=grafo.MODO_STUB,
            ejecutar_unidades_fn=self.nodo(developer, costo),
            borrar_trabajo_fn=borrar,
            materializar_fn=cadena.materializar_evidencia,
        )
        gates.resolver(self.store, run, "entrada", "aprobado")
        estado = grafo.reanudar(
            run, self.store, self.checkpointer, productor_de(plan), None, costo,
            self.nodo(developer, costo), borrar, cadena.materializar_evidencia,
        )
        return run, plan, estado

    def cerrar_con_gate(self, run, plan, developer=producir_entrega_stub,
                        costo=0.0, conservar=False, decision="aprobado",
                        motivo=None, materializar=cadena.materializar_evidencia):
        borrar = None if conservar else cadena.borrar_directorio
        gates.resolver(self.store, run, "salida", decision, motivo)
        return grafo.reanudar(
            run, self.store, self.checkpointer, productor_de(plan), None, costo,
            self.nodo(developer, costo), borrar, materializar,
        )


# --- 1 — la cadena completa -------------------------------------------------


class CadenaCompleta(BaseCadena):
    def test_el_plan_se_ejecuta_sin_intervencion_en_el_medio(self):
        run, plan, estado = self.correr_cadena()

        # Dos corridas: la del pedido y la de la unidad.
        lanzadas = self.de_tipo(run, "unidad_lanzada")
        self.assertEqual([e["payload"]["unidad"] for e in lanzadas], ["U1"])
        run_developer = lanzadas[0]["payload"]["run_developer"]
        self.assertNotEqual(run_developer, run)

        # El encadenamiento es un hecho de la corrida del Developer.
        (encadenada,) = self.de_tipo(run_developer, "cadena_iniciada")
        self.assertEqual(encadenada["payload"]["viene_de"], run)
        self.assertEqual(encadenada["payload"]["unidad"], "U1")
        self.assertEqual(encadenada["payload"]["plan_id"], plan["plan_id"])

        # Dos Gates en toda la cadena, los dos en la corrida del pedido, y
        # ninguno en el medio.
        self.assertEqual(
            [e["payload"]["gate"] for e in self.de_tipo(run, "gate_abierto")],
            ["entrada", "salida"],
        )
        self.assertEqual(self.de_tipo(run_developer, "gate_abierto"), [])

        # El Gate de salida somete la entrega, no el plan.
        salida = self.de_tipo(run, "gate_abierto")[1]["payload"]["somete"]
        self.assertIn("directorio_trabajo", salida)
        self.assertEqual([u["unidad"] for u in salida["unidades"]], ["U1"])
        self.assertNotIn("plan", salida)

        self.assertTrue(gates.esta_bloqueada(self.store, run))
        estado = self.cerrar_con_gate(run, plan)
        self.assertEqual(estado["resultado"], "entregado")

    def test_cada_artefacto_fue_a_su_verificador(self):
        run, plan, _ = self.correr_cadena()
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]

        # El plan lo verificó el de planes: sus reglas son enteros.
        (del_plan,) = self.de_tipo(run, "verificacion_ejecutada")
        self.assertTrue(del_plan["payload"]["valido"])
        self.assertNotIn("unidad", del_plan["payload"])

        # La entrega, el de entregas: sus reglas llevan prefijo y nombran unidad.
        (de_entrega,) = self.de_tipo(run_developer, "verificacion_ejecutada")
        self.assertTrue(de_entrega["payload"]["valido"])
        self.assertEqual(de_entrega["payload"]["unidad"], "U1")

    def test_cada_agente_lleva_su_presupuesto_por_separado(self):
        run, _, _ = self.correr_cadena(costo=0.1)
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]

        self.assertAlmostEqual(presupuesto.consumo(self.store, run)["costo"], 0.1)
        self.assertAlmostEqual(
            presupuesto.consumo(self.store, run_developer)["costo"], 0.1
        )
        self.assertAlmostEqual(
            cadena.costo_de_la_cadena(self.store, run, [run_developer]), 0.2
        )


# --- 2 — el orden lo decide el plan, no el Developer ------------------------


class OrdenDeUnidades(BaseCadena):
    def test_primero_las_unidades_sin_dependencias(self):
        run, _, _ = self.correr_cadena(TRES_UNIDADES)
        lanzadas = [e["payload"]["unidad"] for e in self.de_tipo(run, "unidad_lanzada")]
        self.assertEqual(lanzadas, ["U1", "U3", "U2"])

    def test_la_unidad_recibe_las_entregas_de_las_que_depende(self):
        vistos = []

        def espia(unidad, contexto, entrega_anterior, incumplimientos, contexto_vault,
                  paquete=None):
            vistos.append((unidad["id"], [c["unidad"]["id"] for c in contexto]))
            return producir_entrega_stub(
                unidad, contexto, entrega_anterior, incumplimientos, contexto_vault
            )

        self.correr_cadena(TRES_UNIDADES, developer=espia)
        self.assertEqual(vistos, [("U1", []), ("U3", []), ("U2", ["U1"])])


# --- 3 — reintento tras rechazo ---------------------------------------------


class ReintentoTrasRechazo(BaseCadena):
    def test_corrige_la_entrega_anterior_sin_regenerarla(self):
        registro = []
        run, plan, _ = self.correr_cadena(developer=developer_que_corrige(registro))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]

        # Dos iteraciones: la primera rechazada, la segunda válida.
        veredictos = [
            e["payload"]["valido"] for e in self.de_tipo(run_developer, "verificacion_ejecutada")
        ]
        self.assertEqual(veredictos, [False, True])

        # La segunda llamada recibió la entrega anterior y los incumplimientos.
        self.assertEqual(len(registro), 2)
        self.assertIsNone(registro[0]["entrega_anterior"])
        self.assertEqual(registro[0]["incumplimientos"], [])
        self.assertIsNotNone(registro[1]["entrega_anterior"])
        self.assertIn("C6", {i["regla"] for i in registro[1]["incumplimientos"]})

        # Corrigió: los archivos que ya estaban llegaron intactos a la segunda.
        # El contenido de la segunda sale del depósito y no del evento, que desde
        # ADR-017 sólo lleva el hash. Se compara por contenido igual: lo que este
        # test cuida es que corrija en vez de regenerar.
        primeros = {a["ruta"]: a["contenido"] for a in registro[1]["entrega_anterior"]["archivos"]}
        producidas = self.de_tipo(run_developer, "entrega_producida")
        segunda = deposito.entrega_del_evento(
            producidas[1]["payload"], Path(operational_state.DIR_ESTADO)
        )
        segundos = {a["ruta"]: a["contenido"] for a in segunda["archivos"]}
        self.assertTrue(set(primeros).issubset(segundos))
        for ruta, contenido in primeros.items():
            self.assertEqual(segundos[ruta], contenido, "regeneró %s en vez de corregir" % ruta)

        # Y la unidad terminó entregando.
        self.assertEqual([e["payload"]["unidad"] for e in self.de_tipo(run, "unidad_entregada")], ["U1"])


# --- 4 — si una unidad falla, se detiene el plan completo -------------------


class DetencionDelPlan(BaseCadena):
    def test_no_siguen_las_unidades_independientes(self):
        run, plan, estado = self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_falla_en("U3")
        )

        # U1 entregó; U3 falló; U2 nunca se lanzó, aunque no dependía de U3.
        lanzadas = [e["payload"]["unidad"] for e in self.de_tipo(run, "unidad_lanzada")]
        self.assertEqual(lanzadas, ["U1", "U3"])
        self.assertEqual(
            [e["payload"]["unidad"] for e in self.de_tipo(run, "unidad_entregada")], ["U1"]
        )

        (fallida,) = self.de_tipo(run, "unidad_fallida")
        self.assertEqual(fallida["payload"]["unidad"], "U3")

        (detenido,) = self.de_tipo(run, "plan_detenido")
        self.assertEqual(detenido["payload"]["unidad"], "U3")
        self.assertEqual(detenido["payload"]["sin_ejecutar"], ["U2"])

        # La cadena escaló y no abrió el Gate de salida.
        self.assertEqual(estado["resultado"], "escalado_por_unidad_fallida")
        self.assertEqual(
            [e["payload"]["gate"] for e in self.de_tipo(run, "gate_abierto")], ["entrada"]
        )

    def test_el_directorio_no_se_borra_cuando_la_cadena_escala(self):
        run, _, _ = self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_falla_en("U3")
        )
        self.assertTrue(self.ruta_de_trabajo(run).exists())
        self.assertEqual(self.de_tipo(run, "directorio_borrado"), [])


# --- 4b — la unidad ambigua escala sin reintentar ---------------------------


class UnidadAmbiguaDetieneElPlan(BaseCadena):
    def test_no_se_reintenta_y_detiene_el_plan(self):
        motivo = "La unidad se contradice con U1: pide validar y no validar el mismo campo."
        run, plan, estado = self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_declara_ambigua("U3", motivo)
        )
        run_u3 = [
            e["payload"]["run_developer"]
            for e in self.de_tipo(run, "unidad_lanzada")
            if e["payload"]["unidad"] == "U3"
        ][0]

        # Se registró como hecho, con el motivo que dio el agente.
        (ambigua,) = self.de_tipo(run_u3, "unidad_ambigua")
        self.assertEqual(ambigua["payload"]["motivo"], motivo)
        self.assertEqual(ambigua["actor"], "developer-agent")

        # No fue al verificador y no se reintentó: una sola producción, cero
        # verificaciones. Reintentar sería mandar a adivinar lo que el contrato
        # prohíbe adivinar.
        self.assertEqual(self.de_tipo(run_u3, "verificacion_ejecutada"), [])
        self.assertEqual(self.de_tipo(run_u3, "entrega_producida"), [])

        # Pero el costo se cobró igual: la invocación se pagó.
        self.assertAlmostEqual(presupuesto.consumo(self.store, run_u3)["costo"], 0.05)

        # Y el plan se detuvo: U2 no se lanzó.
        (detenido,) = self.de_tipo(run, "plan_detenido")
        self.assertEqual(detenido["payload"]["motivo"], "escalado_por_unidad_ambigua")
        self.assertEqual(detenido["payload"]["sin_ejecutar"], ["U2"])
        self.assertEqual(estado["resultado"], "escalado_por_unidad_fallida")


# --- 5 — el techo de la cadena ----------------------------------------------


class TechoDeLaCadena(BaseCadena):
    def test_corta_antes_de_lanzar_la_unidad_que_lo_pasaria(self):
        pedido = dict(PEDIDO, techo_costo_usd=0.15)
        run, _, estado = self.correr_cadena(TRES_UNIDADES, costo=0.1, pedido=pedido)

        # El Requirement gastó 0.1 y la primera unidad otros 0.1: la segunda ya
        # no se lanza.
        lanzadas = [e["payload"]["unidad"] for e in self.de_tipo(run, "unidad_lanzada")]
        self.assertEqual(lanzadas, ["U1"])

        (techo,) = self.de_tipo(run, "techo_cadena_alcanzado")
        self.assertEqual(techo["payload"]["limite"], 0.15)
        self.assertEqual(techo["payload"]["unidad"], "U3")
        self.assertGreaterEqual(techo["payload"]["costo"], 0.15)

        self.assertEqual(estado["resultado"], "escalado_por_techo_de_cadena")


# --- 6 — el directorio de trabajo -------------------------------------------


class DirectorioDeTrabajo(BaseCadena):
    def test_uno_por_corrida_con_un_subdirectorio_por_unidad(self):
        run, plan, _ = self.correr_cadena(TRES_UNIDADES)

        ruta = self.ruta_de_trabajo(run)
        self.assertEqual(ruta.name, run)
        self.assertTrue(ruta.is_relative_to(self.trabajo))

        # Cada unidad en su subdirectorio: si no, se pisarían los dos HTML.
        for uid in ("U1", "U2", "U3"):
            self.assertTrue((ruta / uid / "pruebas.html").is_file())
            self.assertTrue((ruta / uid / "demo.html").is_file())
            self.assertTrue((ruta / uid / "src" / ("%s.js" % uid.lower())).is_file())

    def test_se_borra_recien_despues_de_aprobar_el_gate(self):
        run, plan, _ = self.correr_cadena()
        ruta = self.ruta_de_trabajo(run)
        registrada = self.de_tipo(run, "directorio_trabajo")[0]["payload"]["ruta"]

        # Con el Gate abierto y sin resolver, el directorio sigue estando.
        self.assertTrue(ruta.exists())
        self.assertEqual(self.de_tipo(run, "directorio_borrado"), [])

        self.cerrar_con_gate(run, plan)
        self.assertFalse(ruta.exists())
        (borrado,) = self.de_tipo(run, "directorio_borrado")
        # Se anota el mismo domicilio que se anotó al crearlo: sin eso, nadie
        # puede empatar el borrado con lo borrado.
        self.assertEqual(borrado["payload"]["ruta"], registrada)

    def test_conservar_trabajo_no_lo_borra(self):
        run, plan, _ = self.correr_cadena(conservar=True)
        ruta = self.ruta_de_trabajo(run)
        self.cerrar_con_gate(run, plan, conservar=True)
        self.assertTrue(ruta.exists())
        self.assertEqual(self.de_tipo(run, "directorio_borrado"), [])

    def test_una_ruta_que_escapa_del_directorio_no_se_escribe(self):
        entrega = {"unidad": "U1", "supuestos": [], "archivos": [
            {"ruta": "../afuera.js", "rol": "artefacto_esperado", "contenido": "x"}
        ]}
        with self.assertRaises(cadena.RutaFueraDelDirectorio):
            cadena.escribir_entrega(str(self.trabajo / "U1"), entrega)


# --- 7 — idempotencia -------------------------------------------------------


class Idempotencia(BaseCadena):
    def test_reentrar_no_vuelve_a_ejecutar_lo_ya_entregado(self):
        """El nodo se re-ejecuta al reanudar: lo hecho no se rehace ni se repaga."""
        run, plan, _ = self.correr_cadena(TRES_UNIDADES)
        lanzadas_antes = len(self.de_tipo(run, "unidad_lanzada"))
        entregadas_antes = [e["payload"]["run_developer"] for e in self.de_tipo(run, "unidad_entregada")]

        estado = {
            "run_id": run, "plan": plan, "pedido": dict(PEDIDO),
            "techo_cadena": PEDIDO["techo_costo_usd"],
        }
        resultado = self.nodo()(estado)

        self.assertEqual(len(self.de_tipo(run, "unidad_lanzada")), lanzadas_antes)
        entregadas_despues = [e["payload"]["run_developer"] for e in self.de_tipo(run, "unidad_entregada")]
        self.assertEqual(entregadas_despues, entregadas_antes)
        self.assertEqual([u["unidad"] for u in resultado["entregas"]], ["U1", "U2", "U3"])

    def test_reusa_el_directorio_ya_registrado(self):
        run, plan, _ = self.correr_cadena()
        ruta = str(self.ruta_de_trabajo(run))
        self.nodo()({
            "run_id": run, "plan": plan, "pedido": dict(PEDIDO),
            "techo_cadena": PEDIDO["techo_costo_usd"],
        })
        self.assertEqual(len(self.de_tipo(run, "directorio_trabajo")), 1)
        self.assertEqual(cadena.directorio_registrado(self.store, run), ruta)


# --- 7b — el paquete que recibe el Developer (ADR-014) -----------------------


def developer_que_anota_el_paquete(paquetes):
    """Entrega normal, pero deja registrado el paquete con el que la produjo."""

    def producir(unidad, contexto, entrega_anterior, incumplimientos, contexto_vault,
                 paquete=None):
        paquetes.append((unidad["id"], paquete))
        return producir_entrega_stub(
            unidad, contexto, entrega_anterior, incumplimientos, contexto_vault
        )

    return producir


class PaqueteSuficiente(BaseCadena):
    """ADR-014: el agente recibe dónde deposita y qué hay ya depositado.

    Sin estos dos datos el agente decide a ciegas si sus nombres pisan los de
    otra unidad, y decide mal: en la corrida real renombró sus entregables y
    pagó un rechazo por C5 y C6.
    """

    def test_la_unidad_recibe_su_domicilio_y_es_el_suyo_propio(self):
        paquetes = []
        run, _, _ = self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_anota_el_paquete(paquetes)
        )
        directorio = self.ruta_de_trabajo(run)

        self.assertEqual([uid for uid, _ in paquetes], ["U1", "U3", "U2"])
        for uid, paquete in paquetes:
            # El suyo, no el de la cadena: cada unidad tiene carpeta propia y por
            # eso los nombres fijos del contrato no chocan.
            self.assertEqual(Path(paquete["directorio_trabajo"]), directorio / uid)

    def test_el_inventario_arranca_vacio_y_crece_con_lo_ya_depositado(self):
        paquetes = []
        self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_anota_el_paquete(paquetes)
        )
        por_unidad = dict(paquetes)

        # La primera unidad no tiene nada que mirar.
        self.assertEqual(por_unidad["U1"]["ya_depositado"], [])

        # La segunda ve lo de la primera, prefijado por su subdirectorio, y
        # descubre ahí que `pruebas.html` y `demo.html` no son suyos.
        self.assertEqual(
            por_unidad["U3"]["ya_depositado"],
            ["U1/src/u1.js", "U1/tests/u1.test.js", "U1/pruebas.html", "U1/demo.html"],
        )

        # La tercera ve las dos anteriores.
        self.assertEqual(
            por_unidad["U2"]["ya_depositado"],
            [
                "U1/src/u1.js", "U1/tests/u1.test.js", "U1/pruebas.html", "U1/demo.html",
                "U3/src/u3.js", "U3/tests/u3.test.js", "U3/pruebas.html", "U3/demo.html",
            ],
        )

    def test_el_inventario_sale_del_registro_y_no_del_disco(self):
        """Lo que el agente lee se declara, no se descubre. ADR-003 y ADR-014 D."""
        entregas = {
            "U1": {"archivos": [{"ruta": "demo.html"}, {"ruta": "src/u1.js"}]},
            "U2": {"archivos": []},
        }
        self.assertEqual(
            cadena.ya_depositado(entregas), ["U1/demo.html", "U1/src/u1.js"]
        )
        self.assertEqual(cadena.ya_depositado({}), [])


# --- 7c — ningún evento nuevo escribe una ruta absoluta (ADR-014 punto 3) ----


class RutasRelativasEnLosEventos(BaseCadena):
    def test_el_directorio_se_registra_relativo_al_directorio_de_estado(self):
        run, plan, _ = self.correr_cadena()
        (registrado,) = self.de_tipo(run, "directorio_trabajo")
        ruta = registrado["payload"]["ruta"]

        self.assertFalse(Path(ruta).is_absolute())
        # Y sigue señalando la carpeta real: relativizar no puede perder el dato.
        self.assertTrue(
            Path(operational_state.absoluta_desde(ruta, operational_state.DIR_ESTADO))
            .is_relative_to(self.trabajo)
        )

    def test_el_borrado_registra_la_misma_ruta_relativa(self):
        run, plan, _ = self.correr_cadena()
        self.cerrar_con_gate(run, plan)
        (borrado,) = self.de_tipo(run, "directorio_borrado")
        self.assertFalse(Path(borrado["payload"]["ruta"]).is_absolute())

    def test_el_gate_de_salida_somete_una_ruta_relativa(self):
        run, _, _ = self.correr_cadena()
        salida = self.de_tipo(run, "gate_abierto")[1]["payload"]["somete"]
        self.assertFalse(Path(salida["directorio_trabajo"]).is_absolute())

    def test_ningun_evento_de_la_cadena_lleva_una_ruta_absoluta(self):
        """El barrido: se mira todo el registro, no los eventos que uno recuerda.

        Los cuatro sitios se arreglaron uno por uno; esta prueba es la que
        detecta el quinto que aparezca después.
        """
        run, plan, _ = self.correr_cadena(TRES_UNIDADES)
        self.cerrar_con_gate(run, plan)

        runs = [run] + [
            e["payload"]["run_developer"] for e in self.de_tipo(run, "unidad_lanzada")
        ]
        for run_id in runs:
            for evento in self.store.leer_run(run_id):
                texto = json.dumps(evento["payload"], ensure_ascii=False)
                self.assertNotIn(
                    str(self._dir.name), texto,
                    "el evento %s de %s lleva una ruta absoluta de esta máquina"
                    % (evento["tipo"], run_id),
                )


# --- 7d — reanudar una corrida con el directorio guardado en relativo --------


class ReanudarConDirectorioRelativo(BaseCadena):
    """El riesgo que introduce guardar relativo: que al reanudar no se expanda.

    `directorio_registrado` alimenta el directorio de toda la corrida. Si
    devolviera lo que el evento dice tal cual, la cadena reanudada escribiría
    contra una ruta relativa al proceso —otra carpeta— y las unidades que
    faltaban aterrizarían en cualquier lado sin que nada fallara ruidosamente.
    """

    def test_la_segunda_unidad_aterriza_en_el_directorio_de_la_primera(self):
        # La cadena se detiene con U3 fallada: quedan unidades sin ejecutar y el
        # directorio ya está registrado, en relativo.
        run, plan, _ = self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_falla_en("U3")
        )
        (registrado,) = self.de_tipo(run, "directorio_trabajo")
        self.assertFalse(Path(registrado["payload"]["ruta"]).is_absolute())
        directorio = self.ruta_de_trabajo(run)
        self.assertTrue((directorio / "U1" / "demo.html").is_file())

        # Se reanuda con un Developer que sí puede con U3.
        self.nodo()({
            "run_id": run, "plan": plan, "pedido": dict(PEDIDO),
            "techo_cadena": PEDIDO["techo_costo_usd"],
        })

        # No se creó un segundo directorio y lo nuevo cayó junto a lo viejo.
        self.assertEqual(len(self.de_tipo(run, "directorio_trabajo")), 1)
        for uid in ("U1", "U2", "U3"):
            self.assertTrue((directorio / uid / "demo.html").is_file())

    def test_el_inventario_de_la_corrida_reanudada_incluye_lo_ya_entregado(self):
        """Reanudar no le hace perder al agente lo que otras unidades dejaron."""
        run, plan, _ = self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_falla_en("U3")
        )
        paquetes = []
        self.nodo(developer_que_anota_el_paquete(paquetes))({
            "run_id": run, "plan": plan, "pedido": dict(PEDIDO),
            "techo_cadena": PEDIDO["techo_costo_usd"],
        })

        # U1 ya estaba entregada antes de reanudar y no se re-ejecutó, pero U3
        # —la primera que corre al reanudar— la ve igual: el inventario sale del
        # Operational State, así que sobrevive al corte.
        self.assertEqual(paquetes[0][0], "U3")
        self.assertEqual(
            paquetes[0][1]["ya_depositado"],
            ["U1/src/u1.js", "U1/tests/u1.test.js", "U1/pruebas.html", "U1/demo.html"],
        )


# --- 7e — la evidencia de entrega (ADR-015) ---------------------------------


class MaterializacionRota(RuntimeError):
    """Una falla cualquiera al escribir la evidencia. El motivo no importa acá."""


def materializar_que_falla(store, run_pedido):
    raise MaterializacionRota("no se pudo escribir la evidencia")


class EvidenciaDeEntrega(BaseCadena):
    """ADR-015: una corrida aprobada deja sus archivos abribles, no reconstruibles.

    La evidencia nunca se perdió —los eventos `entrega_producida` llevan el
    contenido completo—, pero recuperarla exigía correr un script. Lo que falta
    es la evidencia **materializada**: una carpeta que se abre y se le entrega a
    un tercero sin intermediar código.
    """

    def entregas_de(self, run):
        return cadena.raiz_entregas() / run

    def test_la_corrida_aprobada_deja_su_entrega_en_el_area_de_entregas(self):
        run, plan, _ = self.correr_cadena(TRES_UNIDADES)
        self.cerrar_con_gate(run, plan)

        area = self.entregas_de(run)
        self.assertTrue(area.is_dir())
        # Hermana de `trabajo/`, bajo el mismo directorio de estado.
        self.assertEqual(area.parent.parent, Path(operational_state.DIR_ESTADO))

        # Y lo escrito es exactamente lo que dice el evento, byte a byte. La
        # fuente es el registro y no el directorio de trabajo: por eso el área
        # es derivable, y por eso si alguna vez discrepara gana el evento.
        entregadas = self.de_tipo(run, "unidad_entregada")
        self.assertEqual([e["payload"]["unidad"] for e in entregadas], ["U1", "U3", "U2"])
        for evento in entregadas:
            uid = evento["payload"]["unidad"]
            entrega = cadena.entrega_de(self.store, evento["payload"]["run_developer"])
            for archivo in entrega["archivos"]:
                destino = area / uid / archivo["ruta"]
                self.assertTrue(destino.is_file(), "falta %s/%s" % (uid, archivo["ruta"]))
                self.assertEqual(
                    destino.read_text(encoding="utf-8"), archivo["contenido"]
                )

        # El subdirectorio por unidad se conserva: sin él los nombres fijos del
        # contrato se pisarían entre unidades, igual que en el área de trabajo.
        for uid in ("U1", "U2", "U3"):
            self.assertTrue((area / uid / "pruebas.html").is_file())
            self.assertTrue((area / uid / "demo.html").is_file())

        (materializada,) = self.de_tipo(run, "evidencia_materializada")
        self.assertFalse(Path(materializada["payload"]["ruta"]).is_absolute())
        self.assertEqual(
            [u["unidad"] for u in materializada["payload"]["unidades"]],
            ["U1", "U2", "U3"],
        )

    def test_el_gate_firma_los_hashes_que_se_le_sometieron(self):
        """Se firma sobre lo que se vio: los hashes salen del `gate_abierto`."""
        run, plan, _ = self.correr_cadena(TRES_UNIDADES)

        somete = self.de_tipo(run, "gate_abierto")[1]["payload"]["somete"]
        sometidos = [
            {"unidad": u["unidad"], "archivos": u["archivos"]} for u in somete["unidades"]
        ]
        # Lo sometido lleva hash por archivo. Sin eso se firma una lista de
        # nombres, y "aprobado" no identifica qué se aprobó.
        for unidad in somete["unidades"]:
            self.assertTrue(unidad["archivos"])
            for archivo in unidad["archivos"]:
                self.assertEqual(sorted(archivo), ["ruta", "sha256"])
                self.assertEqual(len(archivo["sha256"]), 64)

        self.cerrar_con_gate(run, plan)
        (resuelto,) = [
            e for e in self.de_tipo(run, "gate_resuelto")
            if e["payload"]["gate"] == "salida"
        ]
        self.assertEqual(resuelto["payload"]["firmado"], sometidos)

        # Y el hash firmado es el del archivo que quedó en el área de entregas.
        area = self.entregas_de(run)
        for unidad in somete["unidades"]:
            for archivo in unidad["archivos"]:
                contenido = (area / unidad["unidad"] / archivo["ruta"]).read_text(
                    encoding="utf-8"
                )
                self.assertEqual(cadena.sha256_de(contenido), archivo["sha256"])

    def test_el_gate_de_entrada_no_firma_nada_porque_no_somete_archivos(self):
        run, _, _ = self.correr_cadena()
        (entrada,) = [
            e for e in self.de_tipo(run, "gate_resuelto")
            if e["payload"]["gate"] == "entrada"
        ]
        self.assertNotIn("firmado", entrada["payload"])

    def test_se_borra_el_trabajo_y_no_la_evidencia(self):
        run, plan, _ = self.correr_cadena()
        trabajo = self.ruta_de_trabajo(run)
        self.cerrar_con_gate(run, plan)

        self.assertFalse(trabajo.exists())
        self.assertTrue(self.entregas_de(run).is_dir())
        # La separación es por estado, no por antigüedad: lo que se descarta es
        # la copia de trabajo, y la evidencia sobrevive en su propia área.
        self.assertEqual(len(self.de_tipo(run, "directorio_borrado")), 1)

    def test_conservar_el_trabajo_no_impide_materializar(self):
        """`--conservar-trabajo` decide si se descarta la copia, no si hay evidencia."""
        run, plan, _ = self.correr_cadena(conservar=True)
        trabajo = self.ruta_de_trabajo(run)
        self.cerrar_con_gate(run, plan, conservar=True)

        self.assertTrue(trabajo.exists())
        self.assertTrue(self.entregas_de(run).is_dir())

    def test_si_falla_la_materializacion_no_se_borra_nada_ni_cierra_la_corrida(self):
        """El orden de ADR-015 punto 3 tiene que ser comprobable, no confiable.

        Si se borrara primero y materializar fallara después, la corrida quedaría
        sin copia de trabajo y sin evidencia. Por eso materializar va antes y
        cualquier falla suya detiene el cierre.
        """
        run, plan, _ = self.correr_cadena()
        trabajo = self.ruta_de_trabajo(run)

        with self.assertRaises(MaterializacionRota):
            self.cerrar_con_gate(run, plan, materializar=materializar_que_falla)

        self.assertTrue(trabajo.exists())
        self.assertEqual(self.de_tipo(run, "directorio_borrado"), [])
        self.assertEqual(self.de_tipo(run, "evidencia_materializada"), [])
        # No cierra: un "entregado" sin evidencia sería una afirmación sin objeto.
        self.assertEqual(self.de_tipo(run, "run_cerrada"), [])

    def test_una_unidad_entregada_sin_entrega_registrada_no_materializa_a_medias(self):
        """La falla real que el caso anterior simula, con su causa concreta."""
        run, _, _ = self.correr_cadena()
        self.store.append(
            run, "unidad_entregada", "plataforma",
            {"unidad": "UX", "run_developer": self.store.nuevo_run_id()},
        )
        with self.assertRaises(cadena.EvidenciaIncompleta):
            cadena.materializar_evidencia(self.store, run)
        self.assertEqual(self.de_tipo(run, "evidencia_materializada"), [])

    def test_la_corrida_rechazada_no_materializa_nada(self):
        """No hubo entrega: no hay evidencia de entrega. Y el trabajo queda."""
        run, plan, _ = self.correr_cadena()
        trabajo = self.ruta_de_trabajo(run)
        self.cerrar_con_gate(run, plan, decision="rechazado", motivo="no sirve")

        self.assertFalse(self.entregas_de(run).exists())
        self.assertEqual(self.de_tipo(run, "evidencia_materializada"), [])
        # El directorio es justamente lo que hay que mirar tras un rechazo.
        self.assertTrue(trabajo.exists())
        self.assertEqual(self.de_tipo(run, "directorio_borrado"), [])

    def test_la_corrida_que_escala_no_materializa_nada(self):
        run, _, _ = self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_falla_en("U3")
        )
        self.assertFalse(self.entregas_de(run).exists())
        self.assertEqual(self.de_tipo(run, "evidencia_materializada"), [])


# --- 7f — el registro no lleva el contenido; el depósito sí (ADR-017) --------


class CorteAlRegistrar(RuntimeError):
    """El proceso muere entre depositar la entrega y appendear su evento."""


class StoreQueSeCortaAlRegistrarLaEntrega:
    """Delega todo en el store real menos el `append` que este test intercepta.

    Es la única forma de mirar el orden desde afuera: entre depositar y
    registrar no hay ningún punto de observación, así que el corte se simula.
    """

    def __init__(self, real):
        self._real = real

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)

    def append(self, run_id, tipo, actor, payload):
        if tipo == "entrega_producida":
            raise CorteAlRegistrar("corte entre depositar y registrar")
        return self._real.append(run_id, tipo, actor, payload)


class DepositoDeArtefactos(BaseCadena):
    """ADR-017: el evento registra ruta, rol y hash; el contenido vive aparte.

    Hasta acá el `entrega_producida` llevaba adentro cada archivo entero, y el
    registro crecía con el tamaño de lo producido en vez de con la cantidad de
    hechos. Lo que ata las dos mitades es el SHA-256: el evento sigue
    identificando sin ambigüedad qué se entregó aunque ya no lo contenga.
    """

    def deposito_de(self, run_developer, iteracion):
        return cadena.raiz_entregas() / run_developer / str(iteracion)

    def run_developer_de(self, run, unidad="U1"):
        (lanzada,) = [
            e for e in self.de_tipo(run, "unidad_lanzada")
            if e["payload"]["unidad"] == unidad
        ]
        return lanzada["payload"]["run_developer"]

    def test_el_evento_registra_el_hash_de_cada_archivo_y_no_su_contenido(self):
        run, _, _ = self.correr_cadena()
        run_developer = self.run_developer_de(run)

        (producida,) = self.de_tipo(run_developer, "entrega_producida")
        payload = producida["payload"]

        # El domicilio del depósito viaja en el evento y es relativo al
        # directorio de estado, como toda ruta desde ADR-014 punto 3.
        self.assertFalse(Path(payload["deposito"]).is_absolute())

        archivos = payload["entrega"]["archivos"]
        self.assertTrue(archivos)
        for archivo in archivos:
            self.assertNotIn("contenido", archivo)
            self.assertEqual(len(archivo["sha256"]), 64)
            # El rol se conserva: es parte de qué se entregó y pesa nada. Lo
            # único que se sacó es el contenido.
            self.assertIn("rol", archivo)

    def test_la_entrega_se_reconstruye_desde_el_area_de_entregas(self):
        run, _, _ = self.correr_cadena()
        run_developer = self.run_developer_de(run)
        (producida,) = self.de_tipo(run_developer, "entrega_producida")

        deposito_1 = self.deposito_de(run_developer, 1)
        self.assertTrue(deposito_1.is_dir())

        entrega = cadena.entrega_de(self.store, run_developer)
        self.assertEqual(
            [a["ruta"] for a in entrega["archivos"]],
            [a["ruta"] for a in producida["payload"]["entrega"]["archivos"]],
        )
        # Y lo reconstruido es byte a byte lo que está en el depósito, que desde
        # ADR-017 es el único lugar donde el contenido existe.
        for archivo in entrega["archivos"]:
            self.assertEqual(
                archivo["contenido"],
                (deposito_1 / archivo["ruta"]).read_text(encoding="utf-8"),
            )

    def test_cada_iteracion_deposita_la_suya_incluida_la_rechazada(self):
        """La iteración rechazada también se deposita, y es una decisión.

        Hasta ADR-017 existía sólo adentro de su evento: al área de trabajo se
        escribía recién cuando la unidad salía entregada, así que lo que el
        verificador rechazó nunca tocaba el disco. Si el evento pierde el
        contenido y sólo se deposita lo aceptado, ese código desaparece — y
        ADR-015 punto 3 lo conserva por diseño, porque es lo que permite
        entender por qué se rechazó.
        """
        registro = []
        run, _, _ = self.correr_cadena(developer=developer_que_corrige(registro))
        run_developer = self.run_developer_de(run)

        producidas = self.de_tipo(run_developer, "entrega_producida")
        self.assertEqual([e["payload"]["iteracion"] for e in producidas], [1, 2])

        # La primera no tenía demo.html: por eso la rechazaron. Y sigue en el
        # depósito, con su falta intacta.
        rechazada = self.deposito_de(run_developer, 1)
        self.assertTrue((rechazada / "pruebas.html").is_file())
        self.assertFalse((rechazada / "demo.html").exists())

        aceptada = self.deposito_de(run_developer, 2)
        self.assertTrue((aceptada / "demo.html").is_file())

    def test_un_evento_viejo_con_el_contenido_adentro_se_sigue_leyendo(self):
        """ADR-017 punto 4: no se migra nada y las dos formas conviven.

        Se distinguen **por presencia de campo**, no por fecha: el registro
        histórico no lleva marca de versión y el día de la implementación no es
        un dato que el evento tenga.
        """
        run_viejo = self.store.nuevo_run_id()
        self.store.append(
            run_viejo,
            "entrega_producida",
            "developer-agent",
            {
                "iteracion": 1,
                "unidad": "U1",
                "entrega": {
                    "unidad": "U1",
                    "archivos": [
                        {"ruta": "src/u1.js", "rol": "codigo", "contenido": "hola"}
                    ],
                },
            },
        )

        entrega = cadena.entrega_de(self.store, run_viejo)
        self.assertEqual(entrega["archivos"][0]["contenido"], "hola")

    def test_el_hash_del_evento_detecta_una_alteracion_del_deposito(self):
        """El registro es inmutable y el depósito no: manda el registro."""
        run, _, _ = self.correr_cadena()
        run_developer = self.run_developer_de(run)

        (self.deposito_de(run_developer, 1) / "demo.html").write_text(
            "otra cosa", encoding="utf-8"
        )

        with self.assertRaises(deposito.DepositoAlterado):
            cadena.entrega_de(self.store, run_developer)

    def test_si_falta_un_archivo_del_deposito_la_cadena_falla_ruidosamente(self):
        """El peor modo de falla: el que no tira excepción.

        La entrega de una unidad ya hecha entra al prompt de las que dependen de
        ella. Si el depósito no pudiera devolver el contenido y esto devolviera
        la entrega a medias, no rompería nada visible: produciría una corrida
        cara contra un contexto mutilado. Por eso levanta antes de armar nada.
        """
        run, plan, _ = self.correr_cadena(
            TRES_UNIDADES, developer=developer_que_falla_en("U3")
        )
        run_developer = self.run_developer_de(run, "U1")
        (self.deposito_de(run_developer, 1) / "demo.html").unlink()

        llamadas = []

        def espia(unidad, contexto, entrega_anterior, incumplimientos, contexto_vault,
                  paquete=None):
            llamadas.append(unidad["id"])
            return producir_entrega_stub(unidad, contexto, None, [], contexto_vault)

        with self.assertRaises(deposito.DepositoIncompleto):
            self.nodo(espia)({
                "run_id": run, "plan": plan, "pedido": dict(PEDIDO),
                "techo_cadena": PEDIDO["techo_costo_usd"],
            })

        # Y no llegó a producir nada: falla antes de armar el contexto, no
        # después de haberlo armado incompleto.
        self.assertEqual(llamadas, [])

    def test_el_corte_entre_depositar_y_registrar_deja_archivos_sin_evento(self):
        """El orden elegido, comprobado por su consecuencia.

        Se deposita, se relee para comprobar el hash, y recién entonces se
        appendea. El corte deja archivos sin evento y nunca evento sin archivos:
        el archivo huérfano es basura inerte que el reintento sobrescribe con lo
        mismo, y el evento huérfano afirmaría una entrega exhibiendo el hash de
        algo que no existe — y por ADR-011 punto 3 no se podría corregir.
        """
        plan = plan_de(UNA_UNIDAD)
        unidad = plan["unidades"][0]
        run_developer = self.store.nuevo_run_id()
        estado = grafo_developer.EstadoDeveloper(
            run_id=run_developer,
            definicion=grafo.definicion_a_dict(self.definicion_developer),
            plan=plan,
            unidad=unidad,
            contexto_unidades=[],
            directorio=str(self.trabajo),
            directorio_trabajo=cadena.directorio_de_unidad(str(self.trabajo), "U1"),
            ya_depositado=[],
            entrega=None,
            incumplimientos=[],
            iteracion=0,
            resultado=None,
            techos_efectivos={"costo": 1, "tiempo_min": 10, "iteraciones": 3},
        )

        cortado = StoreQueSeCortaAlRegistrarLaEntrega(self.store)
        with self.assertRaises(CorteAlRegistrar):
            grafo_developer.crear_grafo(producir_entrega_stub, cortado).invoke(estado)

        # Quedaron los archivos y no quedó el evento.
        deposito_1 = self.deposito_de(run_developer, 1)
        huerfanos = {
            p.relative_to(deposito_1): p.read_text(encoding="utf-8")
            for p in sorted(deposito_1.rglob("*")) if p.is_file()
        }
        self.assertTrue(huerfanos)
        self.assertEqual(self.de_tipo(run_developer, "entrega_producida"), [])

        # El reintento los sobrescribe con contenido idéntico en la misma ruta,
        # porque el hash de lo mismo es el mismo. La basura se limpia sola.
        grafo_developer.crear_grafo(producir_entrega_stub, self.store).invoke(estado)
        self.assertEqual(
            {
                p.relative_to(deposito_1): p.read_text(encoding="utf-8")
                for p in sorted(deposito_1.rglob("*")) if p.is_file()
            },
            huerfanos,
        )
        (producida,) = self.de_tipo(run_developer, "entrega_producida")
        self.assertEqual(producida["payload"]["iteracion"], 1)


# --- 8 — orden topológico ---------------------------------------------------


class OrdenTopologico(unittest.TestCase):
    def test_respeta_dependencias_y_es_determinista(self):
        plan = plan_de([("U3", ["U1"]), ("U1", []), ("U2", ["U1"]), ("U4", ["U2", "U3"])])
        self.assertEqual([u["id"] for u in cadena.orden_topologico(plan)], ["U1", "U2", "U3", "U4"])

    def test_un_ciclo_no_produce_orden(self):
        plan = plan_de([("U1", ["U2"]), ("U2", ["U1"])])
        with self.assertRaises(cadena.CicloDeDependencias):
            cadena.orden_topologico(plan)


# --- 9 — el enganche de QA en la cadena — ADR-018 ---------------------------


def qa_que_devuelve(casos, registro=None):
    """Una `qa_fn` que no invoca modelo y anota con qué la llamaron."""

    def producir(unidad, plan, entrega, deposito, contexto_vault):
        if registro is not None:
            registro.append(
                {
                    "unidad": unidad["id"],
                    "deposito": deposito,
                    "archivos_de_la_entrega": [a["ruta"] for a in entrega["archivos"]],
                    "contexto_vault": contexto_vault,
                }
            )
        return list(casos), 0.0

    return producir


class ResultadoFalso(object):
    def __init__(self, salida):
        self.salida = salida
        self.error = ""
        self.codigo = 0
        self.cortado_por_tiempo = False
        self.frontera = "ninguna"
        self.segundos = 0.0


#: El entregable que el stub del Developer siempre produce. Los casos de QA
#: tienen que nombrar un archivo real de la entrega desde el Control 1.
ENTREGABLE_DEL_STUB = "src/u1.js"


def caso_de_qa(criterio=1, expresion="correr()", espera="ok"):
    return {
        "criterio": criterio,
        "expresion": expresion,
        "espera": espera,
        "archivo": ENTREGABLE_DEL_STUB,
    }


def tiene_centinela(deposito):
    """Si el Control 4 reemplazó el entregable en esta copia del depósito."""
    for ruta in Path(deposito).rglob("*"):
        if not ruta.is_file():
            continue
        try:
            if verificacion_sustantiva.MARCA_CENTINELA in ruta.read_text(encoding="utf-8"):
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False


class EngancheDeQA(BaseCadena):
    """QA corre por unidad, después del verificador estructural.

    Los casos se inyectan y el ejecutor se reemplaza: acá se prueba dónde entra
    QA en el grafo y qué queda registrado, no la frontera —eso es
    `test_ejecutor`— ni el veredicto —eso es `test_verificacion_sustantiva`—.
    """

    def setUp(self):
        super().setUp()
        ruta_qa = Path(self._dir.name) / "qa.md"
        ruta_qa.write_text(definicion_texto("qa-agente-de-prueba", 1, 5, 1), encoding="utf-8")
        self.definicion_qa = cargar(str(ruta_qa))
        self._ejecutar = verificacion_sustantiva.ejecutor.ejecutar_expresion

    def tearDown(self):
        verificacion_sustantiva.ejecutor.ejecutar_expresion = self._ejecutar
        super().tearDown()

    def ejecutor_que_devuelve(self, salida, depende=True):
        """Reemplaza el ejecutor por uno que devuelve lo que se le dice.

        `depende` es la diferencia entre un caso que comprueba el entregable y
        uno vacuo: con el centinela plantado, el que depende devuelve otra cosa
        —y el Control 4 lo deja pasar como evidencia— y el que no, devuelve lo
        mismo y queda descartado. Un doble que ignorara el depósito *sería* el
        caso vacuo, así que la bandera no es un adorno.
        """

        def correr(deposito, expresion):
            if depende and tiene_centinela(deposito):
                return ResultadoFalso("sin el entregable no da lo mismo")
            return ResultadoFalso(salida)

        verificacion_sustantiva.ejecutor.ejecutar_expresion = correr

    def nodo_con_qa(self, qa_fn, developer=producir_entrega_stub):
        return cadena.nodo_ejecutar_unidades(
            self.store, self.definicion_developer, developer, str(self.trabajo),
            None, 0.0, qa_fn=qa_fn, definicion_qa=self.definicion_qa,
        )

    def correr_con_qa(self, qa_fn, unidades=UNA_UNIDAD, developer=producir_entrega_stub):
        plan = plan_de(unidades)
        run = grafo.ejecutar(
            str(self.ruta_requirement), dict(PEDIDO), productor_de(plan), self.store,
            self.checkpointer, None, 0.0, modo=grafo.MODO_STUB,
            ejecutar_unidades_fn=self.nodo_con_qa(qa_fn, developer),
            borrar_trabajo_fn=cadena.borrar_directorio,
            materializar_fn=cadena.materializar_evidencia,
        )
        gates.resolver(self.store, run, "entrada", "aprobado")
        estado = grafo.reanudar(
            run, self.store, self.checkpointer, productor_de(plan), None, 0.0,
            self.nodo_con_qa(qa_fn, developer), cadena.borrar_directorio,
            cadena.materializar_evidencia,
        )
        return run, plan, estado

    # --- las dos piezas van juntas -----------------------------------------

    def test_el_productor_sin_definicion_no_arma_el_nodo(self):
        with self.assertRaises(cadena.QAIncompleto) as capturado:
            cadena.nodo_ejecutar_unidades(
                self.store, self.definicion_developer, producir_entrega_stub,
                str(self.trabajo), None, 0.0, qa_fn=qa_que_devuelve([]),
            )
        self.assertIn("Llegó sólo el productor", str(capturado.exception))

    def test_la_definicion_sin_productor_tampoco(self):
        with self.assertRaises(cadena.QAIncompleto) as capturado:
            cadena.nodo_ejecutar_unidades(
                self.store, self.definicion_developer, producir_entrega_stub,
                str(self.trabajo), None, 0.0, definicion_qa=self.definicion_qa,
            )
        self.assertIn("Llegó sólo la definición", str(capturado.exception))

    def test_sin_ninguno_de_los_dos_la_cadena_corre_como_en_v02(self):
        run, _, _ = self.correr_cadena()
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        self.assertEqual(self.de_tipo(run_developer, "qa_ejecutado"), [])

    # --- dónde entra --------------------------------------------------------

    def test_qa_corre_una_vez_por_unidad_despues_de_la_verificacion_estructural(self):
        run, _, _ = self.correr_con_qa(qa_que_devuelve([]), TRES_UNIDADES)
        for lanzada in self.de_tipo(run, "unidad_lanzada"):
            run_developer = lanzada["payload"]["run_developer"]
            tipos = [
                e["tipo"] for e in self.store.leer_run(run_developer)
                if e["tipo"] in ("verificacion_ejecutada", "qa_ejecutado")
            ]
            self.assertEqual(tipos, ["verificacion_ejecutada", "qa_ejecutado"])

    def test_qa_corre_antes_del_gate_de_salida(self):
        run, _, _ = self.correr_con_qa(qa_que_devuelve([]))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        self.assertEqual(len(self.de_tipo(run_developer, "qa_ejecutado")), 1)
        # La cadena quedó frenada en el Gate de salida sin resolver: QA ya corrió.
        gates_abiertos = [e["payload"]["gate"] for e in self.de_tipo(run, "gate_abierto")]
        self.assertEqual(gates_abiertos, ["entrada", "salida"])

    def test_qa_recibe_el_deposito_de_la_entrega_producida(self):
        registro = []
        run, _, _ = self.correr_con_qa(qa_que_devuelve([], registro))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (producida,) = self.de_tipo(run_developer, "entrega_producida")
        self.assertEqual(len(registro), 1)
        # El mismo depósito que ADR-017 registró, no uno recalculado.
        self.assertEqual(
            operational_state.relativa_a(
                registro[0]["deposito"], operational_state.DIR_ESTADO
            ),
            producida["payload"]["deposito"],
        )
        self.assertTrue(Path(registro[0]["deposito"]).is_dir())

    def test_qa_recibe_la_unidad_que_se_esta_verificando(self):
        registro = []
        self.correr_con_qa(qa_que_devuelve([], registro), TRES_UNIDADES)
        self.assertEqual(
            sorted(r["unidad"] for r in registro), ["U1", "U2", "U3"]
        )

    # --- qué queda registrado ----------------------------------------------

    def test_el_evento_lleva_la_tabla_y_la_metrica(self):
        run, _, _ = self.correr_con_qa(qa_que_devuelve([]))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (evento,) = self.de_tipo(run_developer, "qa_ejecutado")
        self.assertEqual(evento["actor"], grafo_developer.AGENTE_QA)
        payload = evento["payload"]
        self.assertEqual(payload["unidad"], "U1")
        self.assertTrue(payload["cumple"])
        self.assertEqual([f["regla"] for f in payload["tabla"]], ["AC-U1-1"])
        # Sin casos, el único criterio no se pudo comprobar.
        self.assertEqual(payload["no_verificables"], ["AC-U1-1"])

    def test_el_evento_no_lleva_rutas_de_la_maquina(self):
        run, _, _ = self.correr_con_qa(qa_que_devuelve([]))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (evento,) = self.de_tipo(run_developer, "qa_ejecutado")
        self.assertFalse(Path(evento["payload"]["deposito"]).is_absolute())

    def test_los_casos_descartados_quedan_registrados(self):
        # Es la evidencia de que el límite del punto 3 operó. Sin ella, "QA no
        # exigió de más" no se puede comprobar.
        casos = [{"criterio": 99, "expresion": "x", "espera": "y"}]
        run, _, _ = self.correr_con_qa(qa_que_devuelve(casos))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (evento,) = self.de_tipo(run_developer, "qa_ejecutado")
        self.assertEqual(len(evento["payload"]["descartados"]), 1)
        self.assertTrue(evento["payload"]["cumple"])

    def test_la_metrica_va_en_lo_que_somete_el_gate_de_salida(self):
        run, _, _ = self.correr_con_qa(qa_que_devuelve([]), TRES_UNIDADES)
        somete = self.de_tipo(run, "gate_abierto")[1]["payload"]["somete"]
        self.assertEqual(
            [(u["unidad"], u["no_verificables"]) for u in somete["unidades"]],
            [("U1", 1), ("U2", 1), ("U3", 1)],
        )

    def test_sin_qa_la_metrica_es_none_y_no_cero(self):
        # Cero significa "se comprobó todo". Que QA no haya corrido es otra cosa
        # y el Gate tiene que poder distinguirlas.
        run, _, _ = self.correr_cadena()
        somete = self.de_tipo(run, "gate_abierto")[1]["payload"]["somete"]
        self.assertIsNone(somete["unidades"][0]["no_verificables"])

    # --- el bucle de corrección --------------------------------------------

    def test_un_incumplimiento_sustantivo_manda_a_reintentar_por_el_mismo_bucle(self):
        self.ejecutor_que_devuelve("lo que no se esperaba")
        casos = [caso_de_qa()]
        registro = []
        run, _, _ = self.correr_con_qa(
            qa_que_devuelve(casos), developer=developer_que_corrige(registro)
        )
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]

        # Dos vueltas de QA: la que rechazó y la de después de corregir.
        eventos = self.de_tipo(run_developer, "qa_ejecutado")
        self.assertEqual([e["payload"]["cumple"] for e in eventos], [False, False])
        # El Developer volvió a producir con los incumplimientos de QA en la mano,
        # en la misma forma que los estructurales.
        segundos = registro[-1]["incumplimientos"]
        self.assertEqual(set(segundos[0]), {"regla", "archivo", "detalle"})

    def test_agotar_el_techo_del_developer_escala_y_detiene_el_plan(self):
        self.ejecutor_que_devuelve("lo que no se esperaba")
        casos = [caso_de_qa()]
        run, _, _ = self.correr_con_qa(qa_que_devuelve(casos))
        (detenido,) = self.de_tipo(run, "plan_detenido")
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (escalado,) = self.de_tipo(run_developer, "escalamiento")
        self.assertEqual(escalado["payload"]["motivo"], "escalado_por_iteraciones")

    def test_qa_no_trae_techo_de_iteraciones_propio(self):
        """El que reintenta es el Developer; el techo que lo acota es el suyo."""
        self.ejecutor_que_devuelve("lo que no se esperaba")
        casos = [caso_de_qa()]
        run, _, _ = self.correr_con_qa(qa_que_devuelve(casos))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (techos,) = self.de_tipo(run_developer, "techos_efectivos")
        self.assertEqual(
            len(self.de_tipo(run_developer, "qa_ejecutado")),
            techos["payload"]["iteraciones"],
        )

    def test_qa_que_cumple_cierra_la_unidad(self):
        self.ejecutor_que_devuelve("ok")
        casos = [caso_de_qa()]
        run, _, _ = self.correr_con_qa(qa_que_devuelve(casos))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (evento,) = self.de_tipo(run_developer, "qa_ejecutado")
        self.assertTrue(evento["payload"]["cumple"])
        self.assertEqual(evento["payload"]["no_verificables"], [])
        self.assertEqual(self.de_tipo(run, "plan_detenido"), [])

    # --- lo que no se da por bueno -----------------------------------------

    def test_sin_frontera_escala_en_vez_de_aprobar(self):
        def sin_frontera(deposito, expresion):
            raise verificacion_sustantiva.ejecutor.SinFrontera("no hay sandbox acá")

        verificacion_sustantiva.ejecutor.ejecutar_expresion = sin_frontera
        casos = [caso_de_qa()]
        run, _, _ = self.correr_con_qa(qa_que_devuelve(casos))
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (escalado,) = self.de_tipo(run_developer, "escalamiento")
        self.assertEqual(escalado["payload"]["motivo"], "escalado_por_sin_frontera")
        # No quedó registrada ninguna verificación: nadie miró la unidad.
        self.assertEqual(self.de_tipo(run_developer, "qa_ejecutado"), [])
        self.assertEqual(len(self.de_tipo(run, "plan_detenido")), 1)

    def test_un_fallo_de_infraestructura_del_productor_escala(self):
        def se_cae(unidad, plan, entrega, deposito, contexto_vault):
            raise grafo.FalloDeInfraestructura("el proveedor no respondió", consumo=0.02)

        run, _, _ = self.correr_con_qa(se_cae)
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (fallo,) = self.de_tipo(run_developer, "fallo_infraestructura")
        self.assertEqual(fallo["payload"]["etapa"], "qa")
        (escalado,) = self.de_tipo(run_developer, "escalamiento")
        self.assertEqual(escalado["payload"]["motivo"], "escalado_por_infraestructura")

    def test_el_costo_de_qa_se_registra_contra_el_mismo_techo(self):
        def con_costo(unidad, plan, entrega, deposito, contexto_vault):
            return [], 0.07

        run, _, _ = self.correr_con_qa(con_costo)
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        consumos = [
            e["payload"]["costo"]
            for e in self.de_tipo(run_developer, "consumo_registrado")
        ]
        self.assertIn(0.07, consumos)

    def test_una_respuesta_ilegible_de_qa_escala_en_vez_de_aprobar(self):
        """Antes esto pasaba el Gate. Es el agujero que la rama cierra.

        Cero casos hace que todos los criterios salgan
        `no_verificable_mecanicamente`, y eso aprueba. Una respuesta que no se
        pudo leer firmaba la unidad con el mismo aspecto que un QA que miró.
        """

        def ilegible(unidad, plan, entrega, deposito, contexto_vault):
            raise grafo.RespuestaIlegible(
                "no_parseable", "Expecting value: line 1 column 1", consumo=0.12
            )

        run, _, _ = self.correr_con_qa(ilegible)
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        (evento,) = self.de_tipo(run_developer, "respuesta_ilegible")
        self.assertEqual(evento["payload"]["etapa"], "qa")
        self.assertEqual(evento["payload"]["motivo"], "no_parseable")
        self.assertIn("Expecting value", evento["payload"]["detalle"])
        (escalado,) = self.de_tipo(run_developer, "escalamiento")
        self.assertEqual(escalado["payload"]["motivo"], "escalado_por_qa_ilegible")
        # Nadie miró la unidad, y por eso no hay veredicto que la firme.
        self.assertEqual(self.de_tipo(run_developer, "qa_ejecutado"), [])
        self.assertEqual(len(self.de_tipo(run, "plan_detenido")), 1)

    def test_lo_que_qa_alcanzo_a_gastar_se_cobra_igual(self):
        def ilegible(unidad, plan, entrega, deposito, contexto_vault):
            raise grafo.RespuestaIlegible("truncada", "llegó al techo", consumo=0.12)

        run, _, _ = self.correr_con_qa(ilegible)
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        consumos = [
            e["payload"]["costo"]
            for e in self.de_tipo(run_developer, "consumo_registrado")
        ]
        self.assertIn(0.12, consumos)

    def test_qa_que_no_propone_nada_y_se_lo_pudo_leer_no_escala(self):
        """El silencio legítimo sigue pasando. La línea es si se entendió.

        Es el contraste que justifica el test de arriba: si los dos silencios
        terminaran igual, distinguirlos no serviría de nada.
        """

        def sin_casos(unidad, plan, entrega, deposito, contexto_vault):
            return [], 0.01

        run, _, _ = self.correr_con_qa(sin_casos)
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        self.assertEqual(self.de_tipo(run_developer, "respuesta_ilegible"), [])
        (evento,) = self.de_tipo(run_developer, "qa_ejecutado")
        self.assertTrue(evento["payload"]["cumple"])
        self.assertEqual(self.de_tipo(run, "plan_detenido"), [])

    def test_una_respuesta_ilegible_del_developer_se_anota_y_sigue_el_ciclo(self):
        """El otro lado de la asimetría: acá hay un verificador abajo.

        La entrega vacía la rechaza el verificador, el bucle de corrección
        reintenta, y si no alcanza escala por iteraciones —no por ilegible—.
        Gastó una iteración; no aprobó nada.
        """

        def ilegible(unidad, contexto, entrega, incumplimientos, contexto_vault,
                     paquete=None):
            raise grafo.RespuestaIlegible("truncada", "llegó al techo", consumo=0.01)

        run, _, _ = self.correr_cadena(developer=ilegible)
        run_developer = self.de_tipo(run, "unidad_lanzada")[0]["payload"]["run_developer"]
        eventos = self.de_tipo(run_developer, "respuesta_ilegible")
        self.assertTrue(eventos)
        self.assertEqual(eventos[0]["payload"]["etapa"], "entrega")
        self.assertTrue(self.de_tipo(run_developer, "verificacion_ejecutada"))
        (escalado,) = self.de_tipo(run_developer, "escalamiento")
        self.assertEqual(escalado["payload"]["motivo"], "escalado_por_iteraciones")


if __name__ == "__main__":
    unittest.main(verbosity=2)
