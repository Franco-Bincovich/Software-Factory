"""Criterio de aceptación de T14. Veinte tests, uno por fila de la tabla.

Cada test corre contra un Operational State y un checkpointer temporales, y
contra un Vault temporal. La base real y el Vault real nunca se abren.
"""

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import gates  # noqa: E402
import grafo  # noqa: E402
import presupuesto  # noqa: E402
from agent_loader import CargaFallida  # noqa: E402
from intake import PedidoRechazado  # noqa: E402
from operational_state import OperationalState  # noqa: E402

PEDIDO = {
    "que_se_quiere": "Herramienta que lee un CSV de altas y reporta filas no importables",
    "para_que": "Evitar revisar el archivo a mano antes de cada importación",
    "alcance_excluido": ["interfaz gráfica"],
    "techo_costo_usd": 2,
    "techo_tiempo_min": 20,
    "techo_iteraciones": 5,
}

RASTREO = "lee un CSV de altas"

LECTURA = ("normas/contrato-plan.md", "normas/glosario.md")


class Techos(object):
    """Los tres techos con la forma que T12 espera. Igual que en test_presupuesto."""

    def __init__(self, costo=2, tiempo=20, iteraciones=5):
        self.techo_costo_usd = costo
        self.techo_tiempo_min = tiempo
        self.techo_iteraciones = iteraciones


def definicion_texto(costo=2, tiempo=20, iteraciones=5):
    """Una Agent Definition que T10 acepta: trece campos y techos coherentes."""
    lectura = ", ".join('"%s"' % ruta for ruta in LECTURA)
    return """---
titulo: Agente de prueba
tipo: agent-definition
estado: aceptado
aprobado: 2026-08-11
version: 1.0
owner: CEO
agent_id: agente-de-prueba
techo_costo_usd: {costo}
techo_tiempo_min: {tiempo}
techo_iteraciones: {iteraciones}
herramientas: [leer_pedido, leer_vault, escribir_salida]
vault_lectura: [{lectura}]
vault_escritura: []
memory: none
---

# Agente de prueba — Agent Definition

## 1. Identidad

Agente de prueba del armazón de ejecución. No corre fuera de los tests.

## 2. Propósito

Convertir un pedido estructurado en un Plan de Trabajo verificable.

## 3. Entrada

Un pedido que pasó por el formulario de Intake.

## 4. Salida

Un Plan de Trabajo que cumple el contrato y valida contra el verificador.

## 5. Herramientas autorizadas

Leer el pedido, leer los documentos declarados del Vault, escribir su salida.

## 6. Alcance de decisión

Decide la descomposición en unidades y sus criterios de aceptación.

## 7. Criterio de terminación

El plan valida contra el verificador estructural y el Gate de salida se aprueba.

## 8. Presupuesto

Los tres techos son obligatorios según ADR-010.

**Costo:** USD {costo} por Agent Run.
**Tiempo:** {tiempo} minutos de reloj, descontando la espera de Gates.
**Iteraciones:** {iteraciones} ciclos completos de producción y evaluación.

## 9. Comportamiento ante fallo

Corrige el plan anterior. Regenerarlo íntegro se trata como agotamiento.

## 10. Escalamiento

Alcanzar cualquier techo corta la corrida y escala al CEO.

## 11. Acceso al conocimiento

Lee los dos documentos que declara el frontmatter. No escribe en el Vault.

## 12. Evidencia

Toda la corrida queda en el Operational State.

## 13. Dependencias

El contrato del Plan de Trabajo y el verificador estructural.
""".format(costo=costo, tiempo=tiempo, iteraciones=iteraciones, lectura=lectura)


# --- productores inyectables ------------------------------------------------


def _plan(sucede_a=None, con_criterios=True):
    criterios = []
    if con_criterios:
        criterios = [
            {
                "condicion_observable": "Corriendo el lector sobre un CSV de cincuenta filas, "
                "cuántos registros devuelve.",
                "resultado_esperado": "Cincuenta registros, sin contar el encabezado.",
                "procedimiento": "Ejecutar el lector sobre el archivo de prueba y contar.",
            }
        ]
    return {
        "plan_id": "PLAN-2" if sucede_a else "PLAN-1",
        "run_id": "asignado-por-la-corrida",
        "pedido_id": "asignado-por-el-intake",
        "sucede_a": sucede_a,
        "restricciones": {
            "techo_costo": 2,
            "techo_tiempo_min": 20,
            "techo_iteraciones": 5,
            "alcance_excluido": ["interfaz gráfica"],
        },
        "unidades": [
            {
                "id": "U1",
                "enunciado": "Leer el archivo de entrada y separar las filas importables.",
                "criterios": criterios,
                "dependencias": [],
                "rastreo": RASTREO,
                "artefacto_esperado": "Módulo lector con su prueba asociada.",
                "ruta_artefacto": None,
            }
        ],
        "supuestos": ["El archivo entra en memoria."],
        "fuera_de_alcance": ["Corregir las filas rechazadas."],
    }


def productor_valido(pedido, plan_anterior, incumplimientos, contexto_vault):
    return _plan()


def productor_invalido(pedido, plan_anterior, incumplimientos, contexto_vault):
    """Devuelve siempre una unidad sin criterios: incumple la regla 1 de T7."""
    return _plan(con_criterios=False)


def productor_que_corrige(registro):
    """Falla la primera vez y corrige después, sobre el plan que recibe.

    `registro` acumula lo que recibió en cada llamada, para poder comprobar que
    corrige en vez de regenerar.
    """

    def producir(pedido, plan_anterior, incumplimientos, contexto_vault):
        registro.append(
            {
                "plan_anterior": plan_anterior,
                "incumplimientos": list(incumplimientos),
                "contexto_vault": dict(contexto_vault),
            }
        )
        if plan_anterior is None:
            return _plan(con_criterios=False)
        return _plan(sucede_a=plan_anterior["plan_id"], con_criterios=True)

    return producir


def productor_sin_proveedor(costo=0.0):
    """Simula que el proveedor del modelo no respondió."""

    def producir(pedido, plan_anterior, incumplimientos, contexto_vault):
        raise grafo.FalloDeInfraestructura("el proveedor no respondió", consumo=costo)

    return producir


def productor_que_explota(veces):
    """Explota las primeras `veces` llamadas. Simula que el proceso murió."""
    estado = {"restantes": veces}

    def producir(pedido, plan_anterior, incumplimientos, contexto_vault):
        if estado["restantes"] > 0:
            estado["restantes"] -= 1
            raise RuntimeError("el proceso murió a mitad de producir")
        return _plan()

    return producir


# --- base -------------------------------------------------------------------


class BaseGrafo(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._dir.name)

        self.vault = self.tmp / "vault"
        (self.vault / "normas").mkdir(parents=True)
        for relativa in LECTURA:
            (self.vault / relativa).write_text(
                "Documento normativo de prueba: %s\n" % relativa, encoding="utf-8"
            )
        self.ruta_definicion = self.vault / "Agente de prueba.md"
        self.ruta_definicion.write_text(definicion_texto(), encoding="utf-8")

        self.ruta_db = self.tmp / "estado" / "factory-test.db"
        self.store = OperationalState(self.ruta_db)
        self.checkpointer = grafo.abrir_checkpointer(
            self.tmp / "estado" / "checkpointer" / "checkpoints.db"
        )

    def tearDown(self):
        self.checkpointer.conn.close()
        self.store.cerrar()
        self._dir.cleanup()

    # --- utilidades ---------------------------------------------------------

    def eventos_totales(self):
        return self.store._conexion.execute("SELECT COUNT(*) FROM evento").fetchone()[0]

    def tipos(self, run_id):
        return [e["tipo"] for e in self.store.leer_run(run_id)]

    def de_tipo(self, run_id, tipo):
        return [e for e in self.store.leer_run(run_id) if e["tipo"] == tipo]

    def correr(
        self,
        productor=productor_valido,
        pedido=None,
        costo=0.0,
        vault=None,
        modo=grafo.MODO_STUB,
        modelo=None,
    ):
        return grafo.ejecutar(
            str(self.ruta_definicion),
            dict(PEDIDO if pedido is None else pedido),
            productor,
            self.store,
            self.checkpointer,
            vault,
            costo,
            modo=modo,
            modelo=modelo,
        )

    def retomar(self, run_id, productor=productor_valido, costo=0.0, vault=None):
        return grafo.reanudar(
            run_id, self.store, self.checkpointer, productor, vault, costo
        )

    def hasta_el_final(self, productor=productor_valido, pedido=None, costo=0.0, vault=None):
        """Corrida completa del Requirement solo, sin coordinador de cadena.

        Sin Developer inyectado la corrida cierra con el plan verificado y no
        abre Gate de salida: el de salida es de la cadena y se resuelve sobre la
        entrega. El Gate de salida sobre el plan se suprimió en la versión 1.1 de
        la Agent Definition. La rama de abajo queda porque el helper también
        sirve para corridas con cadena.
        """
        run = self.correr(productor, pedido, costo, vault)
        gates.resolver(self.store, run, "entrada", "aprobado")
        estado = self.retomar(run, productor, costo, vault)
        if gates.esta_bloqueada(self.store, run):
            gates.resolver(self.store, run, "salida", "aprobado")
            estado = self.retomar(run, productor, costo, vault)
        return run, estado


# --- 1 ----------------------------------------------------------------------


class DefinicionInvalida(BaseGrafo):
    def test_no_arranca_y_no_escribe_un_solo_evento(self):
        roto = definicion_texto().replace("agent_id: agente-de-prueba\n", "")
        self.ruta_definicion.write_text(roto, encoding="utf-8")

        with self.assertRaises(CargaFallida) as capturado:
            self.correr()

        self.assertTrue(
            any("agent_id" in motivo for motivo in capturado.exception.motivos),
            capturado.exception.motivos,
        )
        self.assertEqual(self.eventos_totales(), 0)


# --- 2 ----------------------------------------------------------------------


class PedidoInvalido(BaseGrafo):
    def test_no_arranca_y_no_escribe_un_solo_evento(self):
        pedido = dict(PEDIDO)
        del pedido["techo_costo_usd"]

        with self.assertRaises(PedidoRechazado) as capturado:
            self.correr(pedido=pedido)

        self.assertTrue(
            any("techo_costo_usd" in motivo for motivo in capturado.exception.motivos)
        )
        self.assertEqual(self.eventos_totales(), 0)


# --- 3 ----------------------------------------------------------------------


class FrenaEnElGateDeEntrada(BaseGrafo):
    def test_la_corrida_se_detiene_el_evento_queda_y_el_proceso_termina(self):
        run = self.correr()

        self.assertTrue(gates.esta_bloqueada(self.store, run))
        abiertos = self.de_tipo(run, "gate_abierto")
        self.assertEqual(len(abiertos), 1)
        self.assertEqual(abiertos[0]["payload"]["gate"], "entrada")
        self.assertEqual(
            abiertos[0]["payload"]["somete"]["techos"],
            {"costo": 2, "tiempo_min": 20, "iteraciones": 5},
        )

        # Nada se produjo todavía: el Gate frena antes de gastar.
        self.assertEqual(self.de_tipo(run, "iteracion_producida"), [])
        self.assertEqual(self.de_tipo(run, "consumo_registrado"), [])

        # El grafo queda con el nodo pendiente, no terminado.
        instantanea = grafo.crear_grafo(
            productor_valido, self.store, self.checkpointer
        ).get_state({"configurable": {"thread_id": run}})
        self.assertEqual(instantanea.next, ("gate_entrada",))


# --- 4 ----------------------------------------------------------------------


class RechazoEnEntrada(BaseGrafo):
    def test_la_corrida_termina_sin_producir_nada(self):
        run = self.correr()
        gates.resolver(self.store, run, "entrada", "rechazado", "el pedido es ambiguo")
        estado = self.retomar(run)

        self.assertEqual(estado["resultado"], "rechazado_en_entrada")
        self.assertEqual(self.de_tipo(run, "iteracion_producida"), [])
        self.assertEqual(self.de_tipo(run, "consumo_registrado"), [])
        self.assertEqual(self.de_tipo(run, "verificacion_ejecutada"), [])

        cerradas = self.de_tipo(run, "run_cerrada")
        self.assertEqual(len(cerradas), 1)
        self.assertEqual(cerradas[0]["payload"]["resultado"], "rechazado_en_entrada")
        # No se abrió el Gate de salida.
        self.assertEqual(
            [e["payload"]["gate"] for e in self.de_tipo(run, "gate_abierto")], ["entrada"]
        )


# --- 5 ----------------------------------------------------------------------


class CorridaCompleta(BaseGrafo):
    def test_gate_de_entrada_aprobado_y_plan_valido(self):
        run, estado = self.hasta_el_final(costo=0.1)

        # Sin cadena, la corrida termina con el plan verificado. No hay Gate de
        # salida sobre el plan: se suprimió al encadenar el Developer.
        self.assertEqual(estado["resultado"], grafo.SIN_DEVELOPER)
        self.assertEqual(estado["incumplimientos"], [])
        self.assertEqual(estado["iteracion"], 1)

        self.assertEqual(
            self.tipos(run),
            [
                "run_iniciada",
                "pedido_recibido",
                "techos_declarados",
                "techos_efectivos",
                "modo_produccion_fijado",
                "gates_de_la_cadena",
                "gate_abierto",
                "gate_resuelto",
                "consumo_registrado",
                "iteracion_producida",
                "verificacion_ejecutada",
                "run_cerrada",
            ],
        )
        verificaciones = self.de_tipo(run, "verificacion_ejecutada")
        self.assertTrue(verificaciones[0]["payload"]["valido"])
        self.assertEqual(self.de_tipo(run, "escalamiento"), [])


# --- 6 ----------------------------------------------------------------------


class Correccion(BaseGrafo):
    def test_corrige_el_plan_anterior_en_la_segunda_iteracion_sin_regenerar(self):
        registro = []
        productor = productor_que_corrige(registro)
        run, estado = self.hasta_el_final(productor)

        self.assertEqual(estado["resultado"], grafo.SIN_DEVELOPER)
        self.assertEqual(len(self.de_tipo(run, "iteracion_producida")), 2)
        self.assertEqual(len(self.de_tipo(run, "verificacion_ejecutada")), 2)

        self.assertEqual(len(registro), 2)
        # Primera llamada: sin plan previo y sin incumplimientos.
        self.assertIsNone(registro[0]["plan_anterior"])
        self.assertEqual(registro[0]["incumplimientos"], [])
        # Segunda: recibe el plan anterior y lo que le faltó. No regenera.
        self.assertIsNotNone(registro[1]["plan_anterior"])
        self.assertEqual(registro[1]["plan_anterior"]["plan_id"], "PLAN-1")
        self.assertTrue(registro[1]["incumplimientos"])
        self.assertEqual(registro[1]["incumplimientos"][0]["regla"], 1)
        self.assertEqual(estado["plan"]["sucede_a"], "PLAN-1")

        veredictos = [e["payload"]["valido"] for e in self.de_tipo(run, "verificacion_ejecutada")]
        self.assertEqual(veredictos, [False, True])


# --- 7 ----------------------------------------------------------------------


class TechoDeIteraciones(BaseGrafo):
    def test_con_techo_dos_escala_tras_la_segunda(self):
        pedido = dict(PEDIDO, techo_iteraciones=2)
        run = self.correr(productor_invalido, pedido)
        gates.resolver(self.store, run, "entrada", "aprobado")
        estado = self.retomar(run, productor_invalido)

        self.assertEqual(estado["resultado"], "escalado_por_iteraciones")
        self.assertEqual(len(self.de_tipo(run, "iteracion_producida")), 2)

        escalamientos = self.de_tipo(run, "escalamiento")
        self.assertEqual(len(escalamientos), 1)
        self.assertEqual(escalamientos[0]["payload"]["motivo"], "escalado_por_iteraciones")
        self.assertEqual(escalamientos[0]["actor"], "requirement-agent")
        self.assertEqual(len(self.de_tipo(run, "run_cortada")), 1)
        # Escalar no entrega: nunca se abre el Gate de salida.
        self.assertEqual(
            [e["payload"]["gate"] for e in self.de_tipo(run, "gate_abierto")], ["entrada"]
        )


# --- 8 ----------------------------------------------------------------------


class TechoDeCosto(BaseGrafo):
    def test_corta_y_registra_cual_techo_se_alcanzo(self):
        pedido = dict(PEDIDO, techo_costo_usd=0.15)
        run = self.correr(productor_invalido, pedido, costo=0.1)
        gates.resolver(self.store, run, "entrada", "aprobado")
        estado = self.retomar(run, productor_invalido, costo=0.1)

        self.assertEqual(estado["resultado"], "escalado_por_techo")

        alcanzados = self.de_tipo(run, "techo_alcanzado")
        self.assertEqual(len(alcanzados), 1)
        self.assertEqual(alcanzados[0]["payload"]["techo"], "costo")
        self.assertAlmostEqual(alcanzados[0]["payload"]["valor"], 0.2)
        self.assertEqual(alcanzados[0]["payload"]["limite"], 0.15)

        self.assertEqual(len(self.de_tipo(run, "run_cortada")), 1)
        self.assertEqual(
            self.de_tipo(run, "run_cerrada")[0]["payload"]["resultado"], "escalado_por_techo"
        )


# --- 9 ----------------------------------------------------------------------


class ElRelojSeDetiene(BaseGrafo):
    def test_la_espera_del_gate_no_agota_el_techo_de_tiempo(self):
        run = self.correr()
        techos = Techos(tiempo=1)
        dentro_de_una_hora = datetime.now(timezone.utc) + timedelta(minutes=60)

        # Con el Gate abierto, una hora de espera no consume tiempo.
        while_abierto = presupuesto.consumo(self.store, run, ahora=dentro_de_una_hora)
        self.assertLess(while_abierto["tiempo_min"], 1)
        self.assertIsNone(
            presupuesto.verificar(self.store, run, techos, ahora=dentro_de_una_hora)
        )

        # Resuelto el Gate, la ventana se cierra y el reloj vuelve a correr.
        gates.resolver(self.store, run, "entrada", "aprobado")
        despues = presupuesto.consumo(self.store, run, ahora=dentro_de_una_hora)
        self.assertGreater(despues["tiempo_min"], 59)

        veredicto = presupuesto.verificar(
            self.store, run, techos, ahora=dentro_de_una_hora
        )
        self.assertIsNotNone(veredicto)
        self.assertIn("tiempo_min", veredicto.nombres)


# --- 10 ---------------------------------------------------------------------


class ReanudacionTrasFallo(BaseGrafo):
    def test_retoma_sin_repetir_los_nodos_completados(self):
        explota = productor_que_explota(1)
        run = self.correr(explota)
        gates.resolver(self.store, run, "entrada", "aprobado")

        # Que muera el productor, no que el Gate siga bloqueando: `CorridaBloqueada`
        # también es un RuntimeError y pasaría por el motivo equivocado.
        with self.assertRaises(RuntimeError) as capturado:
            self.retomar(run, explota)
        self.assertNotIsInstance(capturado.exception, grafo.CorridaBloqueada)
        self.assertIn("murió a mitad de producir", str(capturado.exception))

        # El proceso murió antes de producir nada.
        self.assertEqual(self.de_tipo(run, "iteracion_producida"), [])
        eventos_antes = self.eventos_totales()

        estado = self.retomar(run, explota)

        self.assertEqual(estado["resultado"], grafo.SIN_DEVELOPER)
        self.assertGreater(self.eventos_totales(), eventos_antes)

        # El Gate de entrada no se repitió: una apertura y una resolución. Y no
        # hay Gate de salida, porque sin cadena no hay entrega que aprobar.
        aperturas = [e["payload"]["gate"] for e in self.de_tipo(run, "gate_abierto")]
        self.assertEqual(aperturas, ["entrada"])
        resoluciones = [e["payload"]["gate"] for e in self.de_tipo(run, "gate_resuelto")]
        self.assertEqual(resoluciones, ["entrada"])
        # Y se produjo una sola vez, pese a las dos reanudaciones.
        self.assertEqual(len(self.de_tipo(run, "iteracion_producida")), 1)


# --- 11 ---------------------------------------------------------------------


class Trazabilidad(BaseGrafo):
    def test_la_corrida_se_reconstruye_leyendo_solo_el_operational_state(self):
        run, _ = self.hasta_el_final(costo=0.1)

        eventos = self.store.leer_run(run)

        # Todo hecho nombra a su actor, y ninguno es anónimo.
        for evento in eventos:
            self.assertTrue(evento["actor"].strip())
            self.assertIn(evento["actor"], ("plataforma", "CEO", "requirement-agent"))

        por_tipo = {e["tipo"]: e for e in eventos}

        # Qué se pidió, con qué techos, y con cuáles se corrió.
        self.assertEqual(por_tipo["pedido_recibido"]["payload"]["que_se_quiere"], PEDIDO["que_se_quiere"])
        self.assertEqual(por_tipo["techos_declarados"]["payload"]["costo"], 2)
        self.assertEqual(por_tipo["techos_efectivos"]["payload"]["iteraciones"], 5)

        # Quién aprobó qué.
        resueltos = self.de_tipo(run, "gate_resuelto")
        self.assertEqual([e["payload"]["gate"] for e in resueltos], ["entrada"])
        for evento in resueltos:
            self.assertEqual(evento["actor"], "CEO")
            self.assertEqual(evento["payload"]["decision"], "aprobado")

        # Qué produjo y qué se verificó, sin mirar el checkpointer.
        producidas = self.de_tipo(run, "iteracion_producida")
        self.assertEqual(producidas[-1]["payload"]["plan"]["unidades"][0]["rastreo"], RASTREO)
        self.assertTrue(self.de_tipo(run, "verificacion_ejecutada")[-1]["payload"]["valido"])

        # Cuánto consumió y cómo terminó.
        self.assertAlmostEqual(presupuesto.consumo(self.store, run)["costo"], 0.1)
        self.assertEqual(
            por_tipo["run_cerrada"]["payload"]["resultado"], grafo.SIN_DEVELOPER
        )

        # La corrida declara bajo qué régimen de Gates corrió, sin que haya que
        # deducirlo de la versión del código que la ejecutó. Ésta no tiene
        # cadena, así que declara un solo Gate: sin Developer no hay entrega que
        # aprobar, y declarar dos abriendo uno sería el registro mintiendo.
        regimen = por_tipo[grafo.EVENTO_GATES]["payload"]
        self.assertEqual(regimen["gates"], ["entrada"])
        self.assertEqual(regimen["suprimido"], "salida_de_plan")
        self.assertTrue(regimen["motivo"].strip())

        # Y el cierre comprobó que ese régimen se cumplió.
        self.assertEqual(self.de_tipo(run, grafo.EVENTO_REGIMEN_INCUMPLIDO), [])

        # La secuencia está ordenada y es la única fuente consultada.
        self.assertEqual([e["id"] for e in eventos], sorted(e["id"] for e in eventos))


# --- 12 ---------------------------------------------------------------------


class SinEscrituraEnElVault(BaseGrafo):
    def test_ninguna_corrida_modifica_un_archivo_del_vault(self):
        def instantanea():
            return {
                str(ruta.relative_to(self.vault)): ruta.read_bytes()
                for ruta in sorted(self.vault.rglob("*"))
                if ruta.is_file()
            }

        antes = instantanea()
        self.assertIn("normas/contrato-plan.md", antes)

        registro = []
        run, estado = self.hasta_el_final(
            productor_que_corrige(registro), costo=0.1, vault=str(self.vault)
        )
        self.assertEqual(estado["resultado"], grafo.SIN_DEVELOPER)

        # El agente sí leyó lo que declara `vault_lectura`, ni más ni menos.
        self.assertEqual(sorted(registro[0]["contexto_vault"]), sorted(LECTURA))

        self.assertEqual(instantanea(), antes)


# --- 13 ---------------------------------------------------------------------


class FalloDelProveedor(BaseGrafo):
    """No es una iteración mala: la fábrica no pudo producir. Se registra y escala."""

    def test_escala_registrando_el_fallo_y_el_consumo_ya_pagado(self):
        productor = productor_sin_proveedor(costo=0.04)
        run = self.correr(productor)
        gates.resolver(self.store, run, "entrada", "aprobado")
        estado = self.retomar(run, productor)

        self.assertEqual(estado["resultado"], "escalado_por_infraestructura")

        fallos = self.de_tipo(run, "fallo_infraestructura")
        self.assertEqual(len(fallos), 1)
        self.assertIn("el proveedor no respondió", fallos[0]["payload"]["detalle"])
        self.assertEqual(fallos[0]["actor"], "plataforma")

        # El plan nunca se verificó: no hay plan.
        self.assertEqual(self.de_tipo(run, "verificacion_ejecutada"), [])
        self.assertEqual(self.de_tipo(run, "iteracion_producida"), [])
        # Pero lo que se pagó se registró: el techo no se alimenta de ficciones.
        self.assertAlmostEqual(presupuesto.consumo(self.store, run)["costo"], 0.04)

        self.assertEqual(len(self.de_tipo(run, "escalamiento")), 1)
        self.assertEqual(len(self.de_tipo(run, "run_cortada")), 1)
        self.assertEqual(
            self.de_tipo(run, "run_cerrada")[0]["payload"]["resultado"],
            "escalado_por_infraestructura",
        )


# --- 14 ---------------------------------------------------------------------


class ModoDeProduccionRegistrado(BaseGrafo):
    """El modo con el que se abre una corrida es un hecho suyo, no un flag.

    Queda en el Operational State antes de producir nada, y se lee de ahí para
    reanudar. Sin este hecho, una corrida iniciada con el stub se reanudaría
    contra el modelo real por el solo hecho de que quien la reanuda no repitió
    `--stub`, y gastaría dinero que nadie pidió gastar.
    """

    def test_el_hecho_queda_registrado_al_abrir_la_corrida(self):
        run = self.correr(modo=grafo.MODO_STUB)

        registrados = self.de_tipo(run, grafo.EVENTO_MODO)
        self.assertEqual(len(registrados), 1)
        self.assertEqual(registrados[0]["payload"]["modo"], "stub")
        self.assertEqual(registrados[0]["actor"], "plataforma")

    def test_se_registra_antes_de_producir_nada(self):
        run = self.correr(modo=grafo.MODO_STUB)
        tipos = self.tipos(run)

        # Antes del Gate de entrada, y por lo tanto antes de cualquier
        # `iteracion_producida` o `consumo_registrado`.
        self.assertLess(tipos.index(grafo.EVENTO_MODO), tipos.index("gate_abierto"))
        self.assertNotIn("consumo_registrado", tipos)

    def test_el_nombre_del_modelo_queda_como_evidencia(self):
        run = self.correr(modo=grafo.MODO_MODELO, modelo="claude-sonnet-5")

        payload = self.de_tipo(run, grafo.EVENTO_MODO)[0]["payload"]
        self.assertEqual(payload["modo"], "modelo")
        self.assertEqual(payload["modelo"], "claude-sonnet-5")

    def test_en_modo_stub_no_se_anota_ningun_modelo(self):
        run = self.correr(modo=grafo.MODO_STUB, modelo="claude-sonnet-5")

        self.assertNotIn("modelo", self.de_tipo(run, grafo.EVENTO_MODO)[0]["payload"])

    def test_modo_de_lee_el_hecho_de_la_corrida(self):
        run = self.correr(modo=grafo.MODO_STUB)

        self.assertEqual(grafo.modo_de(self.store, run), "stub")

    def test_modo_de_devuelve_none_cuando_la_corrida_no_lo_anoto(self):
        # Una corrida anterior a este registro: existe, pero el hecho no está.
        self.store.append("corrida-vieja", "run_iniciada", "plataforma", {"version": "1.0"})

        self.assertIsNone(grafo.modo_de(self.store, "corrida-vieja"))

    def test_no_se_abre_una_corrida_con_un_modo_que_no_existe(self):
        with self.assertRaises(grafo.ModoInvalido) as capturado:
            self.correr(modo="turbo")

        self.assertIn("turbo", str(capturado.exception))
        # Un modo inválido no deja rastro, igual que un pedido inválido.
        self.assertEqual(self.eventos_totales(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
