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
import gates  # noqa: E402
import grafo  # noqa: E402
from grafo import UnidadAmbigua  # noqa: E402
import operational_state  # noqa: E402
import presupuesto  # noqa: E402
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
            raise UnidadAmbigua(motivo, costo=0.05)
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
        )
        gates.resolver(self.store, run, "entrada", "aprobado")
        estado = grafo.reanudar(
            run, self.store, self.checkpointer, productor_de(plan), None, costo,
            self.nodo(developer, costo), borrar,
        )
        return run, plan, estado

    def cerrar_con_gate(self, run, plan, developer=producir_entrega_stub,
                        costo=0.0, conservar=False):
        borrar = None if conservar else cadena.borrar_directorio
        gates.resolver(self.store, run, "salida", "aprobado")
        return grafo.reanudar(
            run, self.store, self.checkpointer, productor_de(plan), None, costo,
            self.nodo(developer, costo), borrar,
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
        primeros = {a["ruta"]: a["contenido"] for a in registro[1]["entrega_anterior"]["archivos"]}
        producidas = self.de_tipo(run_developer, "entrega_producida")
        segundos = {a["ruta"]: a["contenido"] for a in producidas[1]["payload"]["entrega"]["archivos"]}
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


# --- 8 — orden topológico ---------------------------------------------------


class OrdenTopologico(unittest.TestCase):
    def test_respeta_dependencias_y_es_determinista(self):
        plan = plan_de([("U3", ["U1"]), ("U1", []), ("U2", ["U1"]), ("U4", ["U2", "U3"])])
        self.assertEqual([u["id"] for u in cadena.orden_topologico(plan)], ["U1", "U2", "U3", "U4"])

    def test_un_ciclo_no_produce_orden(self):
        plan = plan_de([("U1", ["U2"]), ("U2", ["U1"])])
        with self.assertRaises(cadena.CicloDeDependencias):
            cadena.orden_topologico(plan)


if __name__ == "__main__":
    unittest.main(verbosity=2)
