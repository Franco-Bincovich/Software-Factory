"""Grafo de una corrida del Developer Agent — una unidad.

**Una unidad por corrida.** Identificador propio, techos propios, presupuesto
propio. Eso es lo que permite reintentar al Developer sin volver a producir el
plan: la corrida que se reintenta es la de la unidad, no la del pedido.

**Sin Gates adentro.** Los dos Gates de la cadena viven en la corrida del pedido.
Entre la verificación del plan y la última unidad no hay intervención humana, que
es exactamente la capacidad que V0.2 agrega.

Por eso este grafo se compila **sin checkpointer**: no hay `interrupt`, y sin
interrupción no hay nada que reanudar a mitad. Si la corrida muere, el
coordinador reintenta la unidad entera — sabe cuáles ya entregaron porque lo lee
del Operational State, no de un checkpoint.

El productor es inyectable con la misma forma que en T14, y por la misma razón:
los tests ponen entregas predecibles y el modelo real entra sin tocar el grafo.
"""

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

import presupuesto
import verificador_entrega
from grafo import FalloDeInfraestructura, UnidadAmbigua, _Techos, leer_contexto_vault

AGENTE = "developer-agent"
PLATAFORMA = "plataforma"


class EstadoDeveloper(TypedDict):
    """Estado de ejecución de una unidad. Mismo criterio que `EstadoGrafo`.

    `plan` viaja entero porque el verificador de entregas lo exige: sus reglas
    C1, C4 y V2 se comprueban contra la unidad tal como el plan la declara, no
    contra una copia que el Developer pudiera haber tocado.

    `directorio` es el de la cadena entera; `directorio_trabajo` es el de esta
    unidad. Son dos cosas distintas y la que le importa al agente es la segunda:
    es el domicilio que ADR-014 exige que reciba.
    """

    run_id: str
    definicion: Dict[str, Any]
    plan: Dict[str, Any]
    unidad: Dict[str, Any]
    contexto_unidades: List[Dict[str, Any]]
    directorio: str
    directorio_trabajo: str
    ya_depositado: List[str]
    entrega: Optional[Dict[str, Any]]
    incumplimientos: List[Dict[str, Any]]
    iteracion: int
    resultado: Optional[str]
    techos_efectivos: Dict[str, Any]


def _nodo_verificar_techos(store):
    """Los techos de esta corrida, que son los del Developer y no los del plan."""

    def nodo(estado):
        run_id = estado["run_id"]
        veredicto = presupuesto.verificar(store, run_id, _Techos(estado["techos_efectivos"]))
        if veredicto is None:
            return {}
        for techo in veredicto.techos:
            store.append(
                run_id,
                "techo_alcanzado",
                AGENTE,
                {"techo": techo["techo"], "valor": techo["valor"], "limite": techo["limite"]},
            )
        return {"resultado": "escalado_por_techo"}

    return nodo


def _nodo_producir(store, producir_fn, ruta_vault, costo_iteracion):
    """Produce la entrega. Corrige la anterior; no la regenera.

    Recibe siempre la entrega previa y la lista de incumplimientos, que es lo que
    el campo 9 de la Agent Definition exige para que reintentar sea corregir.

    El sexto argumento es el paquete de ADR-014: dónde deposita y qué hay ya
    depositado. Va como diccionario y no como dos posicionales más para que el
    día que el paquete tenga que crecer, crezca sin cambiarle la firma a todo
    productor existente. Que el paquete sea suficiente es el punto del ADR; que
    sea ampliable es lo que hace que se pueda cumplir la próxima vez.
    """

    def nodo(estado):
        run_id = estado["run_id"]
        contexto = leer_contexto_vault(estado["definicion"], ruta_vault)
        try:
            producido = producir_fn(
                estado["unidad"],
                estado["contexto_unidades"],
                estado["entrega"],
                estado["incumplimientos"],
                contexto,
                {
                    "directorio_trabajo": estado["directorio_trabajo"],
                    "ya_depositado": estado["ya_depositado"],
                },
            )
        except FalloDeInfraestructura as fallo:
            if fallo.costo:
                presupuesto.registrar_consumo(store, run_id, fallo.costo)
            store.append(
                run_id,
                "fallo_infraestructura",
                PLATAFORMA,
                {"detalle": str(fallo), "iteracion": estado["iteracion"]},
            )
            return {"resultado": "escalado_por_infraestructura"}
        except UnidadAmbigua as ambigua:
            # No va al verificador y no cuenta como iteración mala. El contrato
            # declara válida la entrega vacía ante una unidad ambigua, y el
            # criterio 6 del piso de ADR-004 manda escalar. Reintentarla tres
            # veces quemaría el techo en una unidad que ya dijo que no se puede.
            if ambigua.costo:
                presupuesto.registrar_consumo(store, run_id, ambigua.costo)
            store.append(
                run_id,
                "unidad_ambigua",
                AGENTE,
                {
                    "unidad": estado["unidad"]["id"],
                    "motivo": ambigua.motivo,
                    "iteracion": estado["iteracion"],
                },
            )
            return {"resultado": "escalado_por_unidad_ambigua"}

        if isinstance(producido, tuple):
            entrega, costo = producido
        else:
            entrega, costo = producido, costo_iteracion

        presupuesto.registrar_consumo(store, run_id, costo)
        iteracion = estado["iteracion"] + 1
        store.append(
            run_id,
            "entrega_producida",
            AGENTE,
            {"iteracion": iteracion, "unidad": estado["unidad"]["id"], "entrega": entrega},
        )
        return {"entrega": entrega, "iteracion": iteracion, "incumplimientos": []}

    return nodo


def _nodo_verificar(store):
    """El verificador de entregas. Lo ejecuta la plataforma, nunca el agente.

    El artefacto elige su verificador: acá salió una entrega, así que va al de
    entregas. El de planes verifica planes y no sabe leer esto.
    """

    def nodo(estado):
        run_id = estado["run_id"]
        veredicto = verificador_entrega.verificar(estado["entrega"], estado["plan"])
        store.append(
            run_id,
            "verificacion_ejecutada",
            PLATAFORMA,
            {
                "iteracion": estado["iteracion"],
                "unidad": estado["unidad"]["id"],
                "valido": veredicto["valido"],
                "incumplimientos": veredicto["incumplimientos"],
            },
        )
        return {"incumplimientos": veredicto["incumplimientos"]}

    return nodo


def _nodo_escalar(store):
    def nodo(estado):
        run_id = estado["run_id"]
        motivo = estado["resultado"] or "escalado_por_iteraciones"
        store.append(
            run_id,
            "escalamiento",
            AGENTE,
            {
                "motivo": motivo,
                "unidad": estado["unidad"]["id"],
                "iteracion": estado["iteracion"],
                "incumplimientos": estado["incumplimientos"],
            },
        )
        store.append(run_id, "run_cortada", PLATAFORMA, {"motivo": motivo})
        return {"resultado": motivo}

    return nodo


def _nodo_fin(store):
    def nodo(estado):
        run_id = estado["run_id"]
        resultado = estado["resultado"] or "entregado"
        store.append(
            run_id,
            "run_cerrada",
            PLATAFORMA,
            {
                "resultado": resultado,
                "unidad": estado["unidad"]["id"],
                "iteraciones": estado["iteracion"],
            },
        )
        return {"resultado": resultado}

    return nodo


def _tras_verificar_techos(estado):
    return "techo" if estado["resultado"] else "ok"


def _tras_producir(estado):
    return "fallo" if estado["resultado"] else "verificar"


def _tras_verificar(estado):
    if not estado["incumplimientos"]:
        return "valido"
    if estado["iteracion"] >= estado["techos_efectivos"]["iteraciones"]:
        return "agotado"
    return "reintenta"


def crear_grafo(producir_fn, store, ruta_vault=None, costo_iteracion=0.0):
    """El grafo de una unidad. Nodos y aristas a mano, como exige ADR-006."""
    grafo = StateGraph(EstadoDeveloper)

    grafo.add_node("verificar_techos", _nodo_verificar_techos(store))
    grafo.add_node("producir", _nodo_producir(store, producir_fn, ruta_vault, costo_iteracion))
    grafo.add_node("verificar", _nodo_verificar(store))
    grafo.add_node("escalar", _nodo_escalar(store))
    grafo.add_node("fin", _nodo_fin(store))

    grafo.add_edge(START, "verificar_techos")
    grafo.add_conditional_edges(
        "verificar_techos", _tras_verificar_techos, {"ok": "producir", "techo": "escalar"}
    )
    grafo.add_conditional_edges(
        "producir", _tras_producir, {"verificar": "verificar", "fallo": "escalar"}
    )
    grafo.add_conditional_edges(
        "verificar",
        _tras_verificar,
        {"valido": "fin", "reintenta": "verificar_techos", "agotado": "escalar"},
    )
    grafo.add_edge("escalar", "fin")
    grafo.add_edge("fin", END)

    # Sin checkpointer: este grafo no interrumpe, así que no hay nada que
    # reanudar a mitad. La reanudación de la cadena es del coordinador.
    return grafo.compile()
