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

**Desde V0.2 este grafo es el de la cadena, no el del Requirement solo.** La
corrida del pedido lleva los dos Gates —entrada y salida—, el directorio de
trabajo y el registro de qué unidades corrieron. El Gate de salida sobre el plan
se suprimió: aprobar el plan y después aprobar la entrega que sale de él es
aprobar dos veces lo mismo, y la defensa contra un plan malo pasa a ser el techo
de la cadena. Está justificado en la versión 1.1 del Requirement Agent.

**La ejecución de las unidades es un solo nodo acá y muchas corridas adentro.**
El coordinador se inyecta, con el mismo criterio con el que se inyecta el
productor: este módulo ordena y no sabe de Developers. Sin coordinador inyectado
la corrida termina cuando el plan queda verificado, que es el Requirement Agent
corriendo solo.

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
import operational_state
import presupuesto
import verificador
from agent_loader import cargar
from intake import ingresar, texto_rastreable, validar
from operational_state import DIR_ESTADO, relativa_a

RUTA_CHECKPOINTER_POR_DEFECTO = DIR_ESTADO / "checkpointer" / "checkpoints.db"

# Valor que se le pasa a `interrupt()` al reanudar. El nodo no lo usa: la
# decisión se lee del Operational State, que es donde T11 la dejó. Existe
# porque LangGraph exige un valor de reanudación, no porque signifique algo.
REANUDAR = "reanudar"

AGENTE = "requirement-agent"
PLATAFORMA = "plataforma"

# Resultado de una corrida sin coordinador de cadena: el plan quedó verificado y
# no hay quién lo ejecute. No es un fallo.
SIN_DEVELOPER = "plan_verificado"

# El régimen de Gates bajo el que corre la cadena, registrado como hecho de cada
# corrida. Que el cambio esté en la versión de una Agent Definition no alcanza:
# la corrida tiene que poder explicarse sola.
EVENTO_GATES = "gates_de_la_cadena"
EVENTO_REGIMEN_INCUMPLIDO = "regimen_incumplido"

MOTIVO_SUPRESION = (
    "aprobar el plan y despues aprobar la entrega que sale de el es aprobar dos "
    "veces lo mismo; la defensa contra un plan malo es el techo de la cadena. "
    "Requirement Agent 1.1."
)

# Los dos cierres en los que la corrida hizo lo que se propuso. Un rechazo humano
# o un escalamiento también cierran, pero no prometen haber cumplido el régimen.
RESULTADOS_COMPLETOS = ("entregado", SIN_DEVELOPER)


def regimen_de_gates(hay_cadena):
    """El régimen que esta corrida va a cumplir, según tenga cadena o no.

    **No es una constante, y eso es lo importante.** Una corrida sin Developer no
    abre Gate de salida porque no hay entrega que aprobar: declarar dos Gates y
    abrir uno hace que el registro se contradiga a sí mismo. El régimen se
    declara al abrir la corrida y se comprueba al cerrarla.
    """
    return {
        "gates": ["entrada", "salida"] if hay_cadena else ["entrada"],
        "suprimido": "salida_de_plan",
        "motivo": MOTIVO_SUPRESION,
    }

# El hecho que fija con qué se produce esta corrida. Se escribe una sola vez, al
# abrirla, y no se vuelve a tocar: el Operational State no admite update.
EVENTO_MODO = "modo_produccion_fijado"

# Los hechos de una corrida que hereda un plan ya verificado en vez de producirlo.
# Viven acá y no en `cadena` porque los escribe el que abre la corrida, y `cadena`
# los lee: `cadena` importa `grafo`, no al revés.
EVENTO_PLAN_HEREDADO = "plan_heredado"
EVENTO_PEDIDO_HEREDADO = "pedido_heredado"
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
    directorio: Optional[str]
    entregas: List[Dict[str, Any]]
    techo_cadena: float


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

    Lleva el consumo ya hecho cuando lo hay: una invocación que se pagó y falló
    igual sigue siendo consumo, y omitirla le mentiría al techo de ADR-010.
    """

    def __init__(self, mensaje, consumo=0.0):
        super().__init__(mensaje)
        self.consumo = consumo


class RegimenIncumplido(RuntimeError):
    """La corrida cerró sin cumplir el régimen de Gates que ella misma declaró.

    Es un fallo de la plataforma, no del agente ni del pedido: significa que el
    registro se contradice. Una corrida que declara dos Gates y cierra con uno no
    es una corrida a medias, es evidencia que miente sobre lo que ocurrió, y la
    evidencia es lo único que la fábrica tiene.

    Se levanta en vez de cerrar en verde. La corrida queda abierta y el hecho
    queda escrito: es preferible una corrida sin cerrar a un `run_cerrada` que
    afirma algo falso.
    """


class UnidadAmbigua(RuntimeError):
    """El productor devolvió la entrega vacía del contrato, con su motivo.

    No es un defecto a corregir y no es un fallo de infraestructura: el Contrato
    de Entrega declara esta salida válida cuando la unidad es ambigua o
    contradictoria, y dispara el criterio 6 del piso de ADR-004. Se escala.

    Vive acá y no en el productor por lo mismo que `FalloDeInfraestructura`: es
    vocabulario que el productor le habla al grafo, y el grafo no importa
    productores.

    Lleva el consumo ya hecho: la invocación se pagó igual.
    """

    def __init__(self, motivo, consumo=0.0):
        super().__init__(motivo)
        self.motivo = motivo
        self.consumo = consumo


class RespuestaIlegible(RuntimeError):
    """El modelo contestó y no se pudo leer lo que contestó.

    No es lo mismo que no decir nada, y ésa es toda la razón de que esta clase
    exista. Antes las dos causas de abajo devolvían el artefacto vacío —`{}` o
    `[]`— igual que un agente que contesta bien y no propone nada, y las tres
    situaciones quedaban indistinguibles en el registro.

    Las dos causas viajan nombradas en `motivo`:

    - `truncada`: el modelo llegó al techo de salida y la respuesta quedó
      cortada. `detalle` dice contra qué techo.
    - `no_parseable`: la respuesta terminó pero no es el JSON que se esperaba.
      `detalle` lleva lo que dijo el parser, que hasta ahora se descartaba.

    Vive acá por lo mismo que las dos de arriba: es vocabulario que el productor
    le habla al grafo.

    **El grafo no la trata igual en todos lados, y eso es deliberado.** Ver
    `grafo_developer._nodo_qa`, que la escala, contra los dos `_nodo_producir`,
    que siguen el ciclo de corrección. El porqué está escrito en cada uno.
    """

    def __init__(self, motivo, detalle, consumo=0.0):
        super().__init__("%s: %s" % (motivo, detalle))
        self.motivo = motivo
        self.detalle = detalle
        self.consumo = consumo


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


def regimen_declarado(store, run_id):
    """El régimen que la corrida declaró al abrirse. `None` si no consta.

    `None` significa que la corrida es anterior al registro del régimen, no que
    no tenga régimen: no se puede comprobar lo que nadie declaró.
    """
    for evento in store.leer_run(run_id):
        if evento["tipo"] == EVENTO_GATES:
            return evento["payload"]
    return None


def gates_de(store, run_id):
    """`(abiertos, aprobados)` de una corrida, en orden de aparición."""
    abiertos, aprobados = [], []
    for evento in store.leer_run(run_id):
        payload = evento["payload"]
        if evento["tipo"] == "gate_abierto":
            abiertos.append(payload.get("gate"))
        elif evento["tipo"] == "gate_resuelto" and payload.get("decision") == "aprobado":
            aprobados.append(payload.get("gate"))
    return abiertos, aprobados


def verificar_regimen(store, run_id, resultado):
    """Comprueba que la corrida cumplió el régimen que declaró. Levanta si no.

    Se aplica solo a los cierres que afirman haber completado el trabajo. Un
    rechazo en un Gate o un escalamiento cierran legítimamente sin haber abierto
    todos los Gates: no prometieron lo contrario.

    Comprueba las dos direcciones. Que no falte ninguno de los declarados, y que
    no se haya abierto ninguno que no se declaró: las dos son el registro
    contradiciéndose, y da igual para qué lado.
    """
    if resultado not in RESULTADOS_COMPLETOS:
        return

    declarado = regimen_declarado(store, run_id)
    if declarado is None:
        return

    esperados = list(declarado.get("gates") or [])
    abiertos, aprobados = gates_de(store, run_id)
    faltan = [g for g in esperados if g not in aprobados]
    de_mas = [g for g in abiertos if g not in esperados]
    if not faltan and not de_mas:
        return

    detalle = {
        "resultado": resultado,
        "declarados": esperados,
        "abiertos": abiertos,
        "aprobados": aprobados,
        "faltan": faltan,
        "de_mas": de_mas,
    }
    store.append(run_id, EVENTO_REGIMEN_INCUMPLIDO, PLATAFORMA, detalle)
    raise RegimenIncumplido(
        "la corrida %s declaró el régimen de Gates %s y cierra con resultado '%s' "
        "habiendo aprobado %s. Falta: %s. De más: %s. No se cierra en verde una "
        "corrida cuyo registro se contradice: revisá qué etapa no corrió."
        % (
            run_id,
            esperados,
            resultado,
            aprobados or "ninguno",
            faltan or "nada",
            de_mas or "nada",
        )
    )


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
            if fallo.consumo:
                presupuesto.registrar_consumo(store, run_id, fallo.consumo)
            store.append(
                run_id,
                "fallo_infraestructura",
                PLATAFORMA,
                {"detalle": str(fallo), "iteracion": estado["iteracion"]},
            )
            return {"resultado": "escalado_por_infraestructura"}
        except RespuestaIlegible as ilegible:
            # Se anota y se sigue. Abajo de este nodo está T7, que rechaza el plan
            # vacío por la regla 0 y devuelve incumplimientos: el bucle de
            # corrección reintenta y, si tres iteraciones no alcanzan, la corrida
            # escala igual. Una respuesta ilegible acá gasta una iteración, no
            # aprueba nada. Lo único que faltaba era decir por qué se gastó.
            #
            # `grafo_developer._nodo_qa` hace lo contrario con esta misma
            # excepción, y el porqué está escrito ahí: QA no tiene verificador
            # abajo, así que su silencio sí aprueba.
            store.append(
                run_id,
                "respuesta_ilegible",
                PLATAFORMA,
                {
                    "etapa": "plan",
                    "motivo": ilegible.motivo,
                    "detalle": ilegible.detalle,
                    "iteracion": estado["iteracion"],
                },
            )
            # El consumo sigue el camino normal de abajo: la invocación se pagó.
            producido = ({}, ilegible.consumo)

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


def _nodo_fin(store, borrar_trabajo_fn=None, materializar_fn=None):
    """Cierra la corrida. Toda corrida termina acá, se haya entregado o no.

    Es también donde se materializa la evidencia y se descarta el directorio de
    trabajo, y **solo si el Gate de salida se resolvió aprobando**. Nunca antes:
    mientras el Gate esté pendiente, o si la corrida escaló o fue rechazada, el
    directorio es justamente lo que la persona necesita mirar.

    El orden es fijo, por ADR-015 punto 3: primero se escribe la evidencia y
    después se borra el trabajo. Si materializar falla, levanta antes de borrar
    nada y la corrida no cierra: una corrida que quedó abierta se reanuda, pero
    un "entregado" sin evidencia materializada es una afirmación sin objeto.
    """

    def nodo(estado):
        run_id = estado["run_id"]
        resultado = estado["resultado"] or "entregado"

        # Antes que nada: que la corrida haya cumplido lo que declaró. Si no,
        # levanta y no cierra. El directorio tampoco se borra: si el registro se
        # contradice, lo último que hay que hacer es destruir lo que quedó.
        verificar_regimen(store, run_id, resultado)

        decision = gates.resolucion(store, run_id, "salida")
        if decision is not None and decision["decision"] == "aprobado":
            # Materializar no depende de que se borre. Con `--conservar-trabajo`
            # no hay `borrar_trabajo_fn` y la evidencia se escribe igual: son dos
            # áreas distintas y una corrida aprobada deja la suya en las dos.
            if materializar_fn is not None:
                materializar_fn(store, run_id)
            if borrar_trabajo_fn is not None and estado.get("directorio"):
                borrar_trabajo_fn(store, run_id, estado["directorio"])

        store.append(
            run_id,
            "run_cerrada",
            PLATAFORMA,
            {"resultado": resultado, "iteraciones": estado["iteracion"]},
        )
        return {"resultado": resultado}

    return nodo


def _nodo_sin_developer(estado):
    """Sin coordinador inyectado, la corrida termina con el plan verificado.

    Es el Requirement Agent corriendo solo. No es un fallo y no escala: produjo
    lo que su Agent Definition dice que produce.
    """
    return {"resultado": SIN_DEVELOPER}


def _somete_salida(estado):
    """Lo que se somete en el Gate de salida de la cadena.

    El contenido completo de los archivos no va acá: ya está en el Operational
    State, y el Gate se resuelve abriendo los dos HTML del directorio de trabajo,
    no leyendo JSON en una terminal.
    """
    directorio = estado.get("directorio")
    return {
        # Relativa al directorio de estado, ADR-014 punto 3. Quien resuelve el
        # Gate la abre desde ahí; quien lee el evento seis meses después ya no
        # está en la máquina que corrió, y una ruta absoluta no le dice nada.
        "directorio_trabajo": (
            relativa_a(directorio, operational_state.DIR_ESTADO) if directorio else directorio
        ),
        "unidades": estado.get("entregas") or [],
        "como_se_verifica": "abrir pruebas.html y demo.html de cada unidad en el navegador",
    }


def _somete_entrada_heredada(estado):
    """Lo que se aprueba al abrir una corrida que hereda un plan."""
    return {
        "plan": estado["plan"],
        "techo_cadena": estado["techo_cadena"],
        "techos": estado["techos_efectivos"],
    }


# --- aristas condicionales --------------------------------------------------


def _tras_gate_entrada(estado):
    return "rechazado" if estado["resultado"] else "aprobado"


def _tras_verificar_techos(estado):
    return "techo" if estado["resultado"] else "ok"


def _tras_producir(estado):
    """Un fallo de infraestructura escala sin pasar por T7: no hay plan que verificar."""
    return "fallo" if estado["resultado"] else "verificar"


def _tras_ejecutar_unidades(estado):
    resultado = estado["resultado"]
    if not resultado:
        return "entrega"
    if resultado == SIN_DEVELOPER:
        return "fin"
    return "escalar"


def _tras_verificar(estado):
    if not estado["incumplimientos"]:
        return "valido"
    if estado["iteracion"] >= estado["techos_efectivos"]["iteraciones"]:
        return "agotado"
    return "reintenta"


# --- construcción -----------------------------------------------------------


def crear_grafo(
    producir_fn, store, checkpointer, ruta_vault=None, costo_iteracion=0.0,
    ejecutar_unidades_fn=None, borrar_trabajo_fn=None, materializar_fn=None,
    heredado=False,
):
    """Devuelve el grafo compilado. Nodos y aristas declarados a mano.

    No se usan constructores de agentes preconstruidos: es el punto 6 de
    ADR-006.

    `ejecutar_unidades_fn` es el coordinador de la cadena. Se inyecta con el
    mismo criterio que `producir_fn`: este módulo ordena la corrida y no sabe qué
    es un Developer. Sin él, la corrida cierra con el plan verificado.

    `materializar_fn` se inyecta por lo mismo y además por una razón dura: quien
    sabe reconstruir la evidencia es el coordinador de la cadena, y ese módulo
    importa a éste. Inyectarla es lo que evita el import circular.

    `heredado` cambia **una sola arista**: la corrida que trae el plan de otra no
    pasa por la fase Requirement, va del Gate de entrada directo a ejecutar las
    unidades. Es un parámetro y no un grafo aparte para que no haya dos
    definiciones del mismo grafo separándose con el tiempo.
    """
    grafo = StateGraph(EstadoGrafo)

    somete_entrada = (
        _somete_entrada_heredada
        if heredado
        else (lambda e: {"pedido": e["pedido"], "techos": e["techos_efectivos"]})
    )
    grafo.add_node("gate_entrada", _nodo_gate(store, "entrada", somete_entrada))
    grafo.add_node("verificar_techos", _nodo_verificar_techos(store))
    grafo.add_node("producir", _nodo_producir(store, producir_fn, ruta_vault, costo_iteracion))
    grafo.add_node("verificar", _nodo_verificar(store))
    grafo.add_node(
        "ejecutar_unidades",
        _nodo_sin_developer if ejecutar_unidades_fn is None else ejecutar_unidades_fn,
    )
    grafo.add_node("gate_salida", _nodo_gate(store, "salida", _somete_salida))
    grafo.add_node("escalar", _nodo_escalar(store))
    grafo.add_node("fin", _nodo_fin(store, borrar_trabajo_fn, materializar_fn))

    grafo.add_edge(START, "gate_entrada")
    grafo.add_conditional_edges(
        "gate_entrada",
        _tras_gate_entrada,
        {
            "aprobado": "ejecutar_unidades" if heredado else "verificar_techos",
            "rechazado": "fin",
        },
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
        {"valido": "ejecutar_unidades", "reintenta": "verificar_techos", "agotado": "escalar"},
    )
    grafo.add_conditional_edges(
        "ejecutar_unidades",
        _tras_ejecutar_unidades,
        {"entrega": "gate_salida", "fin": "fin", "escalar": "escalar"},
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
    ejecutar_unidades_fn=None,
    borrar_trabajo_fn=None,
    materializar_fn=None,
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
    store.append(
        run_id, EVENTO_GATES, PLATAFORMA, regimen_de_gates(ejecutar_unidades_fn is not None)
    )

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
        directorio=None,
        entregas=[],
        techo_cadena=pedido["techo_costo_usd"],
    )

    grafo = crear_grafo(
        producir_fn, store, checkpointer, ruta_vault, costo_iteracion,
        ejecutar_unidades_fn, borrar_trabajo_fn, materializar_fn,
    )
    grafo.invoke(estado, _config(run_id))
    return run_id


def es_heredada(store, run_id):
    """Si la corrida trajo su plan de otra en vez de producirlo.

    Se lee del Operational State y no de los flags de la reanudación: si el grafo
    se rearmara sin saberlo, aprobar el Gate de entrada mandaría a la fase
    Requirement y la corrida produciría un plan sobre uno heredado.
    """
    return any(e["tipo"] == EVENTO_PLAN_HEREDADO for e in store.leer_run(run_id))


def ejecutar_heredado(
    store,
    checkpointer,
    herencia,
    techo_cadena,
    definicion_developer,
    ejecutar_unidades_fn,
    borrar_trabajo_fn=None,
    ruta_vault=None,
    *,
    modo,
    modelo=None,
    materializar_fn=None,
):
    """Abre una corrida que ejecuta un plan ya verificado en otra corrida.

    No produce plan: lo hereda. Por eso no pasa por la fase Requirement y por eso
    su Agent Definition es la del Developer, que es el único agente que corre.

    Lleva Gate de entrada igual que cualquier otra. No es una formalidad heredada
    del otro camino: comprometer el presupuesto del Developer sobre un plan que
    puede ser viejo es una decisión de recursos, que es para lo que ADR-004 pone
    ese Gate. Lo que somete es el plan y el techo con su descuento, no el pedido.

    `herencia` la arma `cadena`, que es quien sabe leer un linaje. Este módulo
    solo escribe los hechos y ordena la corrida.
    """
    run_id = store.nuevo_run_id()
    pedido = herencia["pedido"]

    store.append(
        run_id,
        "run_iniciada",
        PLATAFORMA,
        {
            "agent_definition_id": definicion_developer.agent_id,
            "version": str(definicion_developer.version),
        },
    )
    # El pedido viaja copiado, no referenciado, y con un tipo de evento propio:
    # `pedido_recibido` significa "entró por Intake" y esto no entró por ahí. Una
    # corrida tiene que poder leerse sola.
    store.append(run_id, EVENTO_PEDIDO_HEREDADO, PLATAFORMA, dict(pedido))
    store.append(run_id, EVENTO_PLAN_HEREDADO, PLATAFORMA, herencia["hecho"])

    efectivos = {
        "costo": techo_cadena,
        "tiempo_min": pedido["techo_tiempo_min"],
        "iteraciones": pedido["techo_iteraciones"],
    }
    store.append(run_id, "techos_efectivos", PLATAFORMA, efectivos)

    hecho_modo = {"modo": modo}
    if modo == MODO_MODELO and modelo:
        hecho_modo["modelo"] = modelo
    store.append(run_id, EVENTO_MODO, PLATAFORMA, hecho_modo)
    store.append(run_id, EVENTO_GATES, PLATAFORMA, regimen_de_gates(True))

    estado = EstadoGrafo(
        run_id=run_id,
        definicion=definicion_a_dict(definicion_developer),
        pedido=dict(pedido),
        texto_rastreable=texto_rastreable(pedido),
        plan=herencia["plan"],
        incumplimientos=[],
        iteracion=0,
        resultado=None,
        techos_efectivos=efectivos,
        directorio=None,
        entregas=[],
        techo_cadena=techo_cadena,
    )

    compilado = crear_grafo(
        None, store, checkpointer, ruta_vault, 0.0,
        ejecutar_unidades_fn, borrar_trabajo_fn, materializar_fn, heredado=True,
    )
    compilado.invoke(estado, _config(run_id))
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


def reanudar(
    run_id, store, checkpointer, producir_fn, ruta_vault=None, costo_iteracion=0.0,
    ejecutar_unidades_fn=None, borrar_trabajo_fn=None, materializar_fn=None,
):
    """Retoma una corrida. Devuelve el estado final del grafo.

    Distingue dos situaciones que LangGraph reanuda distinto: una corrida
    frenada en un Gate se retoma con `Command(resume=...)`; una que murió a
    mitad de un nodo se retoma sin entrada. En los dos casos los nodos ya
    completados no se repiten.
    """
    grafo = crear_grafo(
        producir_fn, store, checkpointer, ruta_vault, costo_iteracion,
        ejecutar_unidades_fn, borrar_trabajo_fn, materializar_fn,
        heredado=es_heredada(store, run_id),
    )
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
