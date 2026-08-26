"""Armazón de ejecución — T14.

La pieza que conecta las seis anteriores y hace que exista una corrida. No
agrega lógica de negocio: T10 valida la definición, T8 valida el pedido, T12
mide y corta, T11 abre y registra Gates, T7 verifica, T13 persiste. Acá se
ordenan.

**Dos fases, no una.** El grafo no puede empezar antes de que exista el
`run_id`, porque el `run_id` es el `thread_id` con el que LangGraph indexa el
checkpoint y sin él no hay reanudación posible. Y ni T10 ni T8 pueden fallar
dentro del grafo, porque el criterio de aceptación exige cero eventos cuando la
definición o el pedido no valen. Por eso hay una fase previa —cargar, validar,
ingresar— y recién después un grafo.

**El estado del grafo es estado de ejecución, no evidencia.** Lo que importa se
escribe además en el Operational State. Si los dos difieren manda el Operational
State: es el punto 4 de ADR-006.

**Los nodos de Gate son idempotentes.** Al reanudar tras `interrupt()`, LangGraph
re-ejecuta el nodo interrumpido desde su primera línea. Un nodo de Gate que
volviera a llamar a `abrir` chocaría con la regla de T11 que prohíbe dos Gates
del mismo tipo en una corrida.

**El modo de producción es un hecho de la corrida, no un parámetro de la
invocación.** Se fija al abrirla y queda registrado antes de gastar un token.
Una corrida iniciada con el stub se reanuda con el stub aunque quien la reanude
no lo pida, porque el modo se lee del Operational State y no de los flags: si se
infiriera de los flags, olvidar `--stub` al reanudar gastaría dinero real sin
que nadie lo haya pedido.
"""

import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

import gates
import presupuesto
import verificador
from agent_loader import cargar
from intake import ingresar, texto_rastreable, validar

RUTA_CHECKPOINTER_POR_DEFECTO = Path(
    "/Users/franbincovich/Desktop/VSCode/software-factory-state/checkpointer/checkpoints.db"
)

# Valor que se le pasa a `interrupt()` al reanudar. El nodo no lo usa: la
# decisión se lee del Operational State, que es donde T11 la dejó. Existe
# porque LangGraph exige un valor de reanudación, no porque signifique algo.
REANUDAR = "reanudar"

AGENTE = "requirement-agent"
PLATAFORMA = "plataforma"

# El hecho que fija con qué se produce esta corrida. Se escribe una sola vez, al
# abrirla, y no se vuelve a tocar: el Operational State no admite update.
EVENTO_MODO = "modo_produccion_fijado"
MODO_STUB = "stub"
MODO_MODELO = "modelo"
MODOS = (MODO_STUB, MODO_MODELO)

TECHOS = (
    ("costo", "techo_costo_usd"),
    ("tiempo_min", "techo_tiempo_min"),
    ("iteraciones", "techo_iteraciones"),
)


class EstadoGrafo(TypedDict):
    """Estado de ejecución. Todo campo tiene que sobrevivir al checkpointer.

    `definicion` viaja como diccionario plano y no como `AgentDefinition`: el
    serializador del checkpointer no sabe empaquetar objetos arbitrarios. Los
    parámetros operativos son lo único que el runtime necesita, y el cuerpo de
    la Agent Definition nunca entra acá por decisión de T10.
    """

    run_id: str
    definicion: Dict[str, Any]
    pedido: Dict[str, Any]
    texto_rastreable: str
    plan: Optional[Dict[str, Any]]
    incumplimientos: List[Dict[str, Any]]
    iteracion: int
    resultado: Optional[str]
    techos_efectivos: Dict[str, Any]


class CorridaBloqueada(RuntimeError):
    """Se intentó reanudar una corrida cuyo Gate sigue sin resolver."""


class CorridaInexistente(RuntimeError):
    """No hay checkpoint para ese `run_id`."""


class ModoInvalido(ValueError):
    """Se quiso abrir una corrida con un modo de producción que no existe."""


class FalloDeInfraestructura(RuntimeError):
    """El productor no pudo trabajar por una causa ajena al plan.

    Red caída, credencial rechazada, límite de tasa, proveedor sobrecargado. No
    es una iteración mala —eso lo resuelve T7 y el ciclo de corrección— sino que
    la fábrica no pudo producir. Se registra y se escala.

    Lleva el costo ya consumido cuando lo hay: una invocación que se pagó y
    falló igual sigue siendo consumo, y omitirla le mentiría al techo de
    ADR-010.
    """

    def __init__(self, mensaje, costo=0.0):
        super().__init__(mensaje)
        self.costo = costo


class _Techos(object):
    """Portador de los tres techos con la forma que T12 espera de una definición.

    T12 los lee por atributo. Los techos efectivos no son los de la Agent
    Definition ni los del pedido sino el mínimo de ambos, así que no se le puede
    pasar ninguno de los dos objetos originales.
    """

    def __init__(self, efectivos):
        self.techo_costo_usd = efectivos["costo"]
        self.techo_tiempo_min = efectivos["tiempo_min"]
        self.techo_iteraciones = efectivos["iteraciones"]


# --- fase previa al grafo ---------------------------------------------------


def techos_efectivos(pedido, definicion):
    """El mínimo entre lo que pide el pedido y lo que autoriza la definición.

    La Agent Definition fija el máximo y el pedido solo puede bajarlo: un pedido
    no amplía el presupuesto de un agente por escribir un número más grande.
    """
    return {
        "costo": min(pedido["techo_costo_usd"], definicion.techo_costo_usd),
        "tiempo_min": min(pedido["techo_tiempo_min"], definicion.techo_tiempo_min),
        "iteraciones": min(pedido["techo_iteraciones"], definicion.techo_iteraciones),
    }


def definicion_a_dict(definicion):
    """Los parámetros operativos, en la forma que el checkpointer sabe guardar."""
    return {
        "agent_id": definicion.agent_id,
        "version": definicion.version,
        "techo_costo_usd": definicion.techo_costo_usd,
        "techo_tiempo_min": definicion.techo_tiempo_min,
        "techo_iteraciones": definicion.techo_iteraciones,
        "herramientas": list(definicion.herramientas),
        "vault_lectura": list(definicion.vault_lectura),
        "vault_escritura": list(definicion.vault_escritura),
        "memory": definicion.memory,
    }


def leer_contexto_vault(definicion_dict, ruta_vault):
    """Lee del Vault exactamente los documentos que declara `vault_lectura`.

    Ni uno más: ampliarlo exige Gate por el criterio 5 del piso de ADR-004. Solo
    lectura — ninguna corrida escribe en el Vault en V0.1.
    """
    if ruta_vault is None:
        return {}
    raiz = Path(ruta_vault)
    contexto = {}
    for relativa in definicion_dict["vault_lectura"]:
        archivo = raiz / relativa
        if not archivo.is_file():
            raise FileNotFoundError(
                "la Agent Definition declara leer '%s' y no existe bajo '%s'."
                % (relativa, raiz)
            )
        contexto[relativa] = archivo.read_text(encoding="utf-8")
    return contexto


# --- checkpointer -----------------------------------------------------------


def abrir_checkpointer(ruta=RUTA_CHECKPOINTER_POR_DEFECTO):
    """Checkpointer SQLite en archivo propio, separado de `factory.db`.

    Son dos archivos con naturalezas opuestas y no se fusionan: el Operational
    State es inmutable y autoritativo, el checkpointer es mutable por diseño y
    sin valor probatorio. Es el punto 4 de ADR-006.
    """
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(str(ruta), check_same_thread=False)
    return SqliteSaver(conexion)


# --- nodos ------------------------------------------------------------------


def _hubo_apertura(store, run_id, gate):
    return any(
        evento["tipo"] == "gate_abierto" and evento["payload"].get("gate") == gate
        for evento in store.leer_run(run_id)
    )


def _nodo_gate(store, gate, somete_de):
    """Fabrica el nodo de un Gate. Los dos Gates se comportan igual.

    Idempotente por obligación: al reanudar, LangGraph re-ejecuta este nodo
    desde el principio. Si el Gate ya está abierto no se vuelve a abrir, y si ya
    está resuelto no se vuelve a frenar.
    """

    def nodo(estado):
        run_id = estado["run_id"]
        if not _hubo_apertura(store, run_id, gate):
            gates.abrir(store, run_id, gate, somete_de(estado))

        decision = gates.resolucion(store, run_id, gate)
        if decision is None:
            interrupt({"gate": gate, "run_id": run_id})
            decision = gates.resolucion(store, run_id, gate)

        if decision is None:
            raise CorridaBloqueada(
                "la corrida %s se reanudó con el Gate de %s todavía sin resolver. "
                "El vencimiento nunca es aprobación." % (run_id, gate)
            )

        if decision["decision"] == "aprobado":
            return {}
        return {"resultado": "rechazado_en_%s" % gate}

    return nodo


def _nodo_verificar_techos(store):
    """Mide contra los tres techos antes de gastar. Nodo, no arista.

    Es nodo propio para que el corte quede registrado como hecho antes de
    escalar: una arista condicional decide en silencio y un techo que corta sin
    dejar evento es un corte que después nadie puede explicar.
    """

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
    """El único nodo que invoca al productor y el único que consume presupuesto.

    Corrige el plan anterior; no lo regenera. Regenerar íntegramente lo prohíbe
    el campo 9 de la Agent Definition, y por eso el productor recibe siempre el
    plan previo y la lista de incumplimientos.
    """

    def nodo(estado):
        run_id = estado["run_id"]
        contexto = leer_contexto_vault(estado["definicion"], ruta_vault)
        try:
            producido = producir_fn(
                estado["pedido"], estado["plan"], estado["incumplimientos"], contexto
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

        if isinstance(producido, tuple):
            plan, costo = producido
        else:
            plan, costo = producido, costo_iteracion

        presupuesto.registrar_consumo(store, run_id, costo)
        iteracion = estado["iteracion"] + 1
        store.append(
            run_id, "iteracion_producida", AGENTE, {"iteracion": iteracion, "plan": plan}
        )
        return {"plan": plan, "iteracion": iteracion, "incumplimientos": []}

    return nodo


def _nodo_verificar(store):
    """La verificación estructural de T7. La ejecuta la plataforma, no el agente."""

    def nodo(estado):
        run_id = estado["run_id"]
        veredicto = verificador.verificar(estado["plan"], estado["texto_rastreable"])
        store.append(
            run_id,
            "verificacion_ejecutada",
            PLATAFORMA,
            {
                "iteracion": estado["iteracion"],
                "valido": veredicto["valido"],
                "incumplimientos": veredicto["incumplimientos"],
            },
        )
        return {"incumplimientos": veredicto["incumplimientos"]}

    return nodo


def _nodo_escalar(store):
    """Registra el escalamiento y corta. Es el único lugar que emite `run_cortada`."""

    def nodo(estado):
        run_id = estado["run_id"]
        motivo = estado["resultado"] or "escalado_por_iteraciones"
        store.append(
            run_id,
            "escalamiento",
            AGENTE,
            {"motivo": motivo, "iteracion": estado["iteracion"]},
        )
        store.append(run_id, "run_cortada", PLATAFORMA, {"motivo": motivo})
        return {"resultado": motivo}

    return nodo


def _nodo_fin(store):
    """Cierra la corrida. Toda corrida termina acá, se haya entregado o no."""

    def nodo(estado):
        run_id = estado["run_id"]
        resultado = estado["resultado"] or "entregado"
        store.append(
            run_id,
            "run_cerrada",
            PLATAFORMA,
            {"resultado": resultado, "iteraciones": estado["iteracion"]},
        )
        return {"resultado": resultado}

    return nodo


# --- aristas condicionales --------------------------------------------------


def _tras_gate_entrada(estado):
    return "rechazado" if estado["resultado"] else "aprobado"


def _tras_verificar_techos(estado):
    return "techo" if estado["resultado"] else "ok"


def _tras_producir(estado):
    """Un fallo de infraestructura escala sin pasar por T7: no hay plan que verificar."""
    return "fallo" if estado["resultado"] else "verificar"


def _tras_verificar(estado):
    if not estado["incumplimientos"]:
        return "valido"
    if estado["iteracion"] >= estado["techos_efectivos"]["iteraciones"]:
        return "agotado"
    return "reintenta"


# --- construcción -----------------------------------------------------------


def crear_grafo(producir_fn, store, checkpointer, ruta_vault=None, costo_iteracion=0.0):
    """Devuelve el grafo compilado. Nodos y aristas declarados a mano.

    No se usan constructores de agentes preconstruidos: es el punto 6 de
    ADR-006.
    """
    grafo = StateGraph(EstadoGrafo)

    grafo.add_node(
        "gate_entrada",
        _nodo_gate(
            store,
            "entrada",
            lambda e: {"pedido": e["pedido"], "techos": e["techos_efectivos"]},
        ),
    )
    grafo.add_node("verificar_techos", _nodo_verificar_techos(store))
    grafo.add_node("producir", _nodo_producir(store, producir_fn, ruta_vault, costo_iteracion))
    grafo.add_node("verificar", _nodo_verificar(store))
    grafo.add_node(
        "gate_salida",
        _nodo_gate(
            store,
            "salida",
            lambda e: {"plan": e["plan"], "veredicto": "valido"},
        ),
    )
    grafo.add_node("escalar", _nodo_escalar(store))
    grafo.add_node("fin", _nodo_fin(store))

    grafo.add_edge(START, "gate_entrada")
    grafo.add_conditional_edges(
        "gate_entrada", _tras_gate_entrada, {"aprobado": "verificar_techos", "rechazado": "fin"}
    )
    grafo.add_conditional_edges(
        "verificar_techos", _tras_verificar_techos, {"ok": "producir", "techo": "escalar"}
    )
    grafo.add_conditional_edges(
        "producir", _tras_producir, {"verificar": "verificar", "fallo": "escalar"}
    )
    grafo.add_conditional_edges(
        "verificar",
        _tras_verificar,
        {"valido": "gate_salida", "reintenta": "verificar_techos", "agotado": "escalar"},
    )
    grafo.add_edge("gate_salida", "fin")
    grafo.add_edge("escalar", "fin")
    grafo.add_edge("fin", END)

    return grafo.compile(checkpointer=checkpointer)


# --- ejecución --------------------------------------------------------------


def _config(run_id):
    return {"configurable": {"thread_id": run_id}}


def ejecutar(
    ruta_definicion,
    pedido,
    producir_fn,
    store,
    checkpointer,
    ruta_vault=None,
    costo_iteracion=0.0,
    *,
    modo,
    modelo=None,
):
    """Corre la fase previa y lanza el grafo. Devuelve el `run_id`.

    Si la definición o el pedido no valen, levanta `CargaFallida` o
    `PedidoRechazado` **sin haber escrito un solo evento**: una corrida que no
    puede arrancar no deja rastro porque no ocurrió.

    Si el grafo frena en un Gate, devuelve igual: la corrida queda esperando y
    el proceso termina. Un proceso vivo esperando a una persona durante horas
    invita a ponerle un timeout, y ADR-004 lo prohíbe.

    `modo` es obligatorio y no tiene valor por defecto. Un default sería una
    etiqueta inventada sobre un hecho que después se lee para decidir si se
    gasta dinero: quien abre la corrida declara con qué la abre.

    `modelo` es evidencia y nada más. Queda registrado para poder saber después
    contra qué se produjo, pero la reanudación no lo usa para ejecutar: el
    nombre del modelo se sigue tomando del entorno.
    """
    if modo not in MODOS:
        raise ModoInvalido(
            "modo de producción '%s' no existe; los de V0.1 son: %s."
            % (modo, ", ".join(MODOS))
        )

    definicion = cargar(ruta_definicion)

    motivos = validar(pedido)
    if motivos:
        from intake import PedidoRechazado

        raise PedidoRechazado(motivos)

    efectivos = techos_efectivos(pedido, definicion)
    run_id = ingresar(pedido, store, definicion.agent_id, str(definicion.version))
    store.append(run_id, "techos_efectivos", PLATAFORMA, efectivos)

    hecho_modo = {"modo": modo}
    if modo == MODO_MODELO and modelo:
        hecho_modo["modelo"] = modelo
    store.append(run_id, EVENTO_MODO, PLATAFORMA, hecho_modo)

    estado = EstadoGrafo(
        run_id=run_id,
        definicion=definicion_a_dict(definicion),
        pedido=pedido,
        texto_rastreable=texto_rastreable(pedido),
        plan=None,
        incumplimientos=[],
        iteracion=0,
        resultado=None,
        techos_efectivos=efectivos,
    )

    grafo = crear_grafo(producir_fn, store, checkpointer, ruta_vault, costo_iteracion)
    grafo.invoke(estado, _config(run_id))
    return run_id


def modo_de(store, run_id):
    """Con qué se abrió la corrida, según el Operational State. `None` si no consta.

    Devuelve el primero de los eventos, no el último: el modo se fija una vez al
    abrir la corrida y no cambia. `None` significa que la corrida es anterior a
    este registro, y no es lo mismo que un modo por defecto: quien lea esto
    tiene que decidir qué hace con una corrida cuyo modo nadie anotó.
    """
    for evento in store.leer_run(run_id):
        if evento["tipo"] == EVENTO_MODO:
            return evento["payload"].get("modo")
    return None


def reanudar(run_id, store, checkpointer, producir_fn, ruta_vault=None, costo_iteracion=0.0):
    """Retoma una corrida. Devuelve el estado final del grafo.

    Distingue dos situaciones que LangGraph reanuda distinto: una corrida
    frenada en un Gate se retoma con `Command(resume=...)`; una que murió a
    mitad de un nodo se retoma sin entrada. En los dos casos los nodos ya
    completados no se repiten.
    """
    grafo = crear_grafo(producir_fn, store, checkpointer, ruta_vault, costo_iteracion)
    config = _config(run_id)

    instantanea = grafo.get_state(config)
    if not instantanea.created_at:
        raise CorridaInexistente("no hay corrida con id %s en el checkpointer." % run_id)

    if gates.esta_bloqueada(store, run_id):
        abiertos = [
            g["payload"].get("gate")
            for g in gates.abiertos(store)
            if g["run_id"] == run_id
        ]
        raise CorridaBloqueada(
            "la corrida %s tiene el Gate de %s sin resolver. Se resuelve con la CLI "
            "de T11 y recién después se reanuda." % (run_id, ", ".join(abiertos))
        )

    if not instantanea.next:
        return instantanea.values

    frenada_en_gate = any(tarea.interrupts for tarea in instantanea.tasks)
    entrada = Command(resume=REANUDAR) if frenada_en_gate else None
    return grafo.invoke(entrada, config)
