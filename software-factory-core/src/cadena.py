"""Coordinador de la cadena — V0.2.

Encadena las dos corridas: el Requirement produce el plan, el Developer ejecuta
sus unidades, y entre una cosa y la otra no hay ninguna persona.

**Dos corridas, no una.** El `run_id` del pedido es el de la cadena: lleva los
dos Gates, el directorio de trabajo y el registro de qué unidades corrieron. Cada
unidad abre su propia corrida de Developer, con identificador y presupuesto
propios, y declara de qué corrida de Requirement viene. Por eso se puede
reintentar al Developer sin volver a producir el plan.

**El Developer nunca decide qué sigue.** El orden sale del grafo de dependencias
del plan, que lee este módulo. El agente recibe una unidad y devuelve una
entrega.

**Si una unidad falla, se detiene el plan completo.** No siguen las unidades
independientes. En V0.2 la simplicidad vale más que el aprovechamiento: media
entrega repartida entre unidades que sí anduvieron y otras que no es más difícil
de explicar en un Gate que una detención limpia.

**Secuencial.** Una unidad por vez, aun las que no dependen entre sí. El
Operational State es de escritor único y la arquitectura declara un proyecto por
vez; paralelizar es V0.4.
"""

import shutil
from pathlib import Path

import deposito
import espacio
import grafo_developer
import operational_state
import presupuesto
from deposito import RutaFueraDelDirectorio, escribir_entrega, sha256_de
from grafo import (
    EVENTO_PEDIDO_HEREDADO,
    EVENTO_PLAN_HEREDADO,
    PLATAFORMA,
    _Techos,
    definicion_a_dict,
)
from operational_state import DIR_ESTADO, absoluta_desde, relativa_a

AGENTE = "developer-agent"

RAIZ_TRABAJO_POR_DEFECTO = DIR_ESTADO / "trabajo"


def _base():
    """El ancla contra la que se relativizan las rutas de los eventos.

    Se busca en el módulo y no se congela en un import, para que los tests
    puedan correr con un directorio de estado temporal —que es la única forma de
    comprobar de verdad que un evento no lleva rutas de la máquina—.
    """
    return operational_state.DIR_ESTADO


def raiz_entregas():
    """El área de entregas, hermana de `trabajo/` bajo el directorio de estado.

    No introduce configuración nueva: se deriva del mismo ancla que todo lo demás,
    y se calcula tarde por la misma razón que `_base()` —para que los tests puedan
    apuntarla a su tmpdir y comprobar de verdad dónde aterriza la evidencia—.

    Son dos áreas y no una a propósito. `trabajo/` es descartable y se borra;
    `entregas/` es evidencia y sobrevive. Mezclarlas obligaría a decidir archivo
    por archivo qué se conserva, que es exactamente lo que ADR-015 no quiere.
    """
    return _base() / "entregas"


class CicloDeDependencias(RuntimeError):
    """El plan tiene un ciclo y no hay orden posible.

    No debería llegar acá: es la regla 7 de T7 y el plan ya pasó por el
    verificador. Se comprueba igual porque el coordinador no da por buena la
    salida de otra pieza para decidir qué ejecuta.
    """


# --- orden de ejecución -----------------------------------------------------


def orden_topologico(plan):
    """Las unidades en un orden que respeta sus dependencias.

    Determinista: dentro de cada tanda habilitada se ordena por identificador.
    Dos corridas del mismo plan ejecutan en el mismo orden, y una cadena que no
    se puede repetir igual no se puede investigar.
    """
    unidades = {u["id"]: u for u in plan["unidades"]}
    pendientes = {
        uid: {d for d in u["dependencias"] if d in unidades} for uid, u in unidades.items()
    }
    ordenadas = []
    while pendientes:
        habilitadas = sorted(uid for uid, deps in pendientes.items() if not deps)
        if not habilitadas:
            raise CicloDeDependencias(
                "el plan tiene un ciclo entre las unidades: %s." % ", ".join(sorted(pendientes))
            )
        for uid in habilitadas:
            ordenadas.append(unidades[uid])
            del pendientes[uid]
        for deps in pendientes.values():
            deps.difference_update(habilitadas)
    return ordenadas


def contexto_de(unidad, unidades_por_id, entregas_por_unidad):
    """Las unidades de las que depende, como contexto de lectura.

    Enunciado, criterios y la entrega que produjeron. Contexto, no trabajo: el
    campo 3 de la Agent Definition dice que el Developer las lee y no las toca.
    """
    contexto = []
    for dep in unidad["dependencias"]:
        if dep not in unidades_por_id:
            continue
        contexto.append(
            {"unidad": unidades_por_id[dep], "entrega": entregas_por_unidad.get(dep)}
        )
    return contexto


# --- lo que la cadena ya hizo, leído del Operational State -------------------


def unidades_entregadas(store, run_pedido):
    """`{unidad: run_developer}` de las unidades que ya entregaron y verificaron.

    Sale del Operational State y no del checkpointer, que es lo que hace
    idempotente al nodo que ejecuta las unidades: al reanudar, lo ya hecho no se
    vuelve a hacer ni se vuelve a pagar. Es el punto 4 de ADR-006 — si los dos
    difieren, manda el Operational State.
    """
    hechas = {}
    for evento in store.leer_run(run_pedido):
        if evento["tipo"] == "unidad_entregada":
            hechas[evento["payload"]["unidad"]] = evento["payload"]["run_developer"]
    return hechas


def entrega_de(store, run_developer):
    """La última entrega producida por una corrida de Developer, con contenido.

    **Es el único lector del payload de `entrega_producida`**, y por eso es acá
    donde conviven las dos formas que ADR-017 punto 4 deja conviviendo. Un evento
    viejo trae el contenido adentro; uno nuevo trae el hash y el domicilio, y el
    contenido sale del depósito. Aguas abajo nadie distingue: `contexto_de`,
    `_resumen` y `materializar_evidencia` reciben lo mismo que recibían.

    Si el depósito no puede devolver lo que el evento afirma, esto **levanta**.
    Devolver una entrega a medias sería peor que fallar: el consumidor que la
    recibe es `productor_entrega`, que pega el código de las unidades de las que
    depende adentro del prompt del modelo. Una entrega incompleta ahí no rompe
    nada visible — produce una corrida cara contra un contexto mutilado.
    """
    entrega = None
    for evento in store.leer_run(run_developer):
        if evento["tipo"] == "entrega_producida":
            entrega = deposito.entrega_del_evento(evento["payload"], _base())
    return entrega


def directorio_registrado(store, run_pedido):
    """El directorio de la cadena, devuelto absoluto para poder escribir en él.

    En el evento está guardado relativo al directorio de estado —ADR-014 punto
    3—, así que acá se vuelve a expandir. La reanudación depende de esta función:
    si devolviera lo que el evento dice tal cual, la corrida reanudada
    escribiría contra una ruta relativa al proceso, que no es la misma carpeta.
    """
    for evento in store.leer_run(run_pedido):
        if evento["tipo"] == "directorio_trabajo":
            return str(absoluta_desde(evento["payload"]["ruta"], _base()))
    return None


# --- techo de la cadena -----------------------------------------------------
#
# Los dos techos de acá abajo se verifican **entre unidades**, antes de lanzar
# la que sigue, y no adentro de la subcorrida del Developer. Eso deja un exceso
# posible y conocido: la unidad ya empezada corre hasta su propio techo aunque
# la cadena cruce el del pedido en el medio. Con los parámetros de hoy
# —`Developer Agent.md`: 0,50 USD y 10 minutos por invocación— el exceso está
# acotado por **una** unidad empezada: el techo del pedido más 0,50 USD y más
# 10 minutos, no N veces eso.
#
# Cerrarlo se evaluó y se descartó (2026-08-30). Exigiría que el techo de la
# cadena cruce la frontera entre este módulo y `grafo_developer`, que hoy no
# sabe —ni tiene por qué saber— que hay una cadena arriba suyo. Acotado y
# conocido no es lo mismo que descontrolado, y la unidad en curso ya está
# gobernada por su propio techo. Queda escrito para que el que lea esto no lo
# tome por un olvido: mover la frontera pide una razón nueva, no la que ya se
# evaluó acá.


def costo_de_la_cadena(store, run_pedido, runs_developer):
    """Lo gastado por la cadena entera: el Requirement más todos los Developer."""
    total = presupuesto.consumo(store, run_pedido)["costo"]
    for run in runs_developer:
        total += presupuesto.consumo(store, run)["costo"]
    return total


def tiempo_de_la_cadena(store, run_pedido, ahora=None):
    """Los minutos que lleva viva la cadena, descontadas las esperas de Gate.

    **No suma las subcorridas, y no es un olvido**: los Developer corren adentro
    de la ventana de la corrida del pedido, así que sumarlas contaría dos veces
    el mismo reloj. El costo se suma porque cada corrida gasta plata aparte; el
    tiempo es uno solo y es el de la corrida que las contiene.

    El descuento de las ventanas de Gate lo hace `presupuesto.consumo`, que es
    de donde sale la medida: esperar a que una persona resuelva un Gate no puede
    matar la cadena, igual que no puede matar una corrida sola.

    El techo de tiempo es **por cadena y no por linaje**, al revés que el de
    costo, que se hereda descontado en `techo_heredado`. Sumar el tiempo de las
    corridas previas del linaje contaría los días que pasaron entre una y otra,
    que es precisamente lo que descontar las ventanas de Gate quiere evitar.
    """
    return presupuesto.consumo(store, run_pedido, ahora=ahora)["tiempo_min"]


# --- directorio de trabajo --------------------------------------------------


def crear_directorio(raiz, run_pedido):
    """Uno por corrida de plan, descartable, fuera del repositorio y del Vault.

    Y **versionado**: desde ADR-019 es un solo espacio para todas las unidades,
    así que la contención que antes daba el subdirectorio la da ahora el commit
    de cada parte aprobada. `espacio.iniciar` es idempotente y se llama también al
    reanudar; ver el encabezado de `espacio`.
    """
    return espacio.iniciar(Path(raiz) / run_pedido)


def inventario_del_espacio(entregas_por_unidad):
    """Qué hay en el espacio de trabajo, de quién es y con qué contenido.

    Una lista de `{ruta, rol, contenido, sha256, parte}`. Es el paquete que
    ADR-014 punto 1 exige —el domicilio no alcanza si el agente no sabe qué hay
    ahí— y desde ADR-019 es además lo que hace comprobable la regla C10: sin el
    hash no se puede distinguir duplicar de pisar.

    El `rol` viaja porque C7 lo necesita: un `.js` auxiliar no es lógica que los
    agregadores tengan que cargar, y sin el rol el verificador no puede saberlo.

    **Sin subdirectorio por unidad.** Las rutas son las de la entrega tal cual,
    porque todas las partes escriben en el mismo espacio.

    **En orden de entrega, y el último gana.** Si dos partes dejaron la misma
    ruta, la que vale es la última que se firmó: es el estado real del disco. El
    orden alfabético diría otra cosa el día que `U10` entregue antes que `U2`.

    **Sale del Operational State, no del disco.** ADR-003 manda que lo que un
    agente lee se declare, y ADR-014 descartó por eso la opción de mirar la
    carpeta. Además, leer del registro es lo que hace que una cadena reanudada
    reciba exactamente el mismo inventario que la original.

    Vacío para la primera parte, porque todavía no hay nada depositado.
    """
    por_ruta = {}
    for uid, entrega in entregas_por_unidad.items():
        for archivo in (entrega or {}).get("archivos", []):
            por_ruta[archivo["ruta"].replace("\\", "/")] = {
                "ruta": archivo["ruta"].replace("\\", "/"),
                "rol": archivo.get("rol"),
                "contenido": archivo["contenido"],
                "sha256": sha256_de(archivo["contenido"]),
                "parte": uid,
            }
    return list(por_ruta.values())


def ultima_parte_firmada(store, run_pedido):
    """El commit de la última parte que la plataforma firmó, o `None`.

    Sale del registro y no de `git log`: lo que vale es la parte que el
    Operational State reconoce como aprobada, no la que quedó en el disco.
    """
    commit = None
    for evento in store.leer_run(run_pedido):
        if evento["tipo"] == "parte_firmada":
            commit = evento["payload"]["commit"]
    return commit


def reconciliar(store, run_pedido, directorio, entregas_por_unidad):
    """Devuelve el espacio al estado que el registro dice que tiene.

    Es el punto de retorno de ADR-019 punto 2 puesto a andar, y la reanudación es
    su primer uso. Una corrida que se cortó pudo dejar el espacio en cualquiera de
    tres estados: a mitad de escribir una parte que nadie aprobó, con una parte
    escrita y sin firmar, o firmada sin que el registro se enterara. Los tres se
    resuelven igual:

    1. Volver al último commit que el registro reconoce como parte firmada.
       `volver` limpia también lo no versionado, que es lo que borra la parte
       escrita a medias.
    2. Reescribir encima lo que el registro dice que se entregó. Por el punto 4
       de ADR-006 el Operational State manda cuando difiere del checkpointer;
       acá manda también sobre el disco.

    Sin commits todavía no hay a dónde volver —la corrida se cortó antes de firmar
    nada—, así que alcanza con reescribir.
    """
    firmado = ultima_parte_firmada(store, run_pedido)
    if firmado is not None:
        espacio.volver(directorio, firmado)
    for entrega in entregas_por_unidad.values():
        if entrega is not None:
            escribir_entrega(directorio, entrega)


class EvidenciaIncompleta(RuntimeError):
    """Una unidad consta como entregada pero su entrega no está en el registro.

    No se materializa una entrega a medias ni se cierra la corrida: es la
    situación exacta en la que "entregado" sería una afirmación sin objeto.
    """


def materializar_evidencia(store, run_pedido, raiz=None):
    """Escribe la evidencia de una corrida aprobada. ADR-015 punto 1.

    **La fuente sigue sin ser el directorio de trabajo.** Lo que cambió con
    ADR-017 es de dónde sale el contenido: antes venía adentro del evento, ahora
    el evento da el hash y el domicilio y el contenido sale del depósito de la
    iteración. La diferencia la absorbe `entrega_de` y acá no se nota.

    Lo que sí cambia es el estatuto del resultado. ADR-015 punto 1 declaraba esta
    área **derivable** —si se perdía, se regeneraba desde los eventos—. Por
    ADR-017 punto 3 eso dejó de ser cierto: el contenido ya no está en el
    registro, así que el área de entregas es el único lugar donde existe y se
    respalda junto al `factory.db` o ninguno de los dos sirve.

    **Duplica el contenido de la iteración aceptada, a propósito.** El depósito
    de la iteración lo escribe el Developer antes de que exista un Gate, y esto
    corre recién cuando el Gate aprueba: no puede ser el mismo directorio porque
    todavía no se sabía que iba a haber aprobación. Uno respalda el evento y el
    otro es lo que se le entrega a un tercero.

    **Plano, sin subdirectorio por unidad.** Por ADR-019 las unidades son partes
    sucesivas sobre un mismo espacio, así que la evidencia se escribe como el
    espacio quedó: en el orden en que las partes entregaron, y si dos tocaron la
    misma ruta gana la última, igual que en el disco. Separarlas por carpeta
    entregaría algo que nunca existió y que no abre —`demo.html` de la parte 2
    carga la lógica de la 1, que estaría en otro directorio—.
    """
    destino = Path(raiz) if raiz is not None else raiz_entregas() / run_pedido
    materializadas = []
    for uid, run_developer in unidades_entregadas(store, run_pedido).items():
        entrega = entrega_de(store, run_developer)
        if entrega is None:
            raise EvidenciaIncompleta(
                "la unidad %s de la corrida %s consta entregada por la corrida %s, "
                "pero esa corrida no registró ninguna entrega."
                % (uid, run_pedido, run_developer)
            )
        escritos = escribir_entrega(destino, entrega)
        materializadas.append({"unidad": uid, "archivos": escritos})

    store.append(
        run_pedido,
        "evidencia_materializada",
        PLATAFORMA,
        {"ruta": relativa_a(destino, _base()), "unidades": materializadas},
    )
    return str(destino)


def borrar_directorio(store, run_pedido, ruta):
    """Se borra **después** de que el Gate de salida se resolvió, nunca antes.

    Y después de materializar la evidencia, por ADR-015 punto 3. Borrarlo no
    pierde nada, pero desde ADR-017 el motivo es otro: el evento ya no lleva el
    contenido, así que lo que respalda al borrado es el **área de entregas** —el
    depósito de cada iteración y la evidencia materializada—, no el registro. Lo
    que se descarta es la copia de trabajo. Queda registrado con su ruta, que es
    el ítem 8 de evidencia de la Agent Definition: sin eso, después nadie puede
    saber qué se descartó.
    """
    if ruta and Path(ruta).exists():
        shutil.rmtree(ruta)
    store.append(
        run_pedido,
        "directorio_borrado",
        PLATAFORMA,
        {"ruta": relativa_a(ruta, _base()) if ruta else ruta},
    )


# --- herencia de un plan ya verificado --------------------------------------


class PlanNoHeredable(RuntimeError):
    """La corrida nombrada no tiene un plan verificado que se pueda heredar."""


class PlanYaEjecutado(RuntimeError):
    """El plan ya produjo código en alguna corrida del linaje."""


class SinPresupuestoHeredado(RuntimeError):
    """Lo que el pedido autorizó ya se gastó: no queda techo para ejecutar."""


class QAIncompleto(RuntimeError):
    """Llegó el productor de QA sin su Agent Definition, o al revés."""


def pedido_de(store, run_id):
    """El pedido que originó la corrida, haya entrado por Intake o heredado."""
    for evento in store.leer_run(run_id):
        if evento["tipo"] in ("pedido_recibido", EVENTO_PEDIDO_HEREDADO):
            return evento["payload"]
    return None


def modo_de_produccion(store, run_id):
    """Con qué se produjo esa corrida. `None` si no consta."""
    for evento in store.leer_run(run_id):
        if evento["tipo"] == "modo_produccion_fijado":
            return evento["payload"]
    return None


def plan_verificado_de(store, run_id):
    """`(plan, iteracion, id del veredicto)` de la última verificación válida.

    El plan se identifica por la corrida que lo produjo, no por su `plan_id`: ese
    campo lo declara el agente y dos planes distintos pueden traer el mismo.

    Solo cuentan las verificaciones de plan. Las de entrega llevan `unidad` en su
    payload y viven en corridas de Developer, pero se filtran igual: confiar en
    que no aparezcan acá sería confiar en una separación que nadie comprueba.
    """
    planes, veredicto = {}, None
    for evento in store.leer_run(run_id):
        payload = evento["payload"]
        if evento["tipo"] == "iteracion_producida":
            planes[payload["iteracion"]] = payload["plan"]
        elif evento["tipo"] == "verificacion_ejecutada":
            if payload.get("valido") and "unidad" not in payload:
                veredicto = evento

    if veredicto is None:
        raise PlanNoHeredable(
            "la corrida %s no tiene ningún plan verificado. Un plan queda "
            "inmutable —y por lo tanto heredable— cuando pasa la verificación y "
            "el veredicto se registra; antes de eso es un borrador." % run_id
        )
    iteracion = veredicto["payload"]["iteracion"]
    if iteracion not in planes:
        raise PlanNoHeredable(
            "la corrida %s registró una verificación válida de la iteración %s y "
            "no el plan de esa iteración. El registro está incompleto."
            % (run_id, iteracion)
        )
    return planes[iteracion], iteracion, veredicto["id"]


def raiz_del_plan(store, run_id):
    """La corrida que produjo el plan, aunque se nombre a una que lo heredó."""
    for evento in store.leer_run(run_id):
        if evento["tipo"] == EVENTO_PLAN_HEREDADO:
            return evento["payload"]["origen"]
    return run_id


def herederas_de(store, raiz):
    return [
        evento["run_id"]
        for evento in store.eventos_de_tipo(EVENTO_PLAN_HEREDADO)
        if evento["payload"].get("origen") == raiz
    ]


def corridas_de_developer(store, run_pedido):
    return [
        evento["payload"]["run_developer"]
        for evento in store.leer_run(run_pedido)
        if evento["tipo"] == "unidad_lanzada"
    ]


def ejecuciones_del_plan(store, raiz):
    """Las corridas del linaje que ya entregaron alguna unidad de este plan."""
    return [
        run
        for run in [raiz] + herederas_de(store, raiz)
        if any(e["tipo"] == "unidad_entregada" for e in store.leer_run(run))
    ]


def gastado_en_el_linaje(store, raiz):
    """Todo lo que este plan consumió: sus corridas y las de sus Developers."""
    total = 0.0
    for run in [raiz] + herederas_de(store, raiz):
        total += costo_de_la_cadena(store, run, corridas_de_developer(store, run))
    return total


def techo_heredado(store, raiz, techo_pedido):
    """Lo que queda del techo del pedido después de lo ya gastado en el linaje.

    **El techo pertenece al trabajo, no a la corrida.** El pedido dijo que esto
    puede costar hasta cierto monto; producir el plan ya consumió parte. Si cada
    corrida arrancara con el techo entero, partir el trabajo en dos corridas
    sería la forma de evadirlo, y un techo evadible no es un techo.
    """
    gastado = gastado_en_el_linaje(store, raiz)
    resto = techo_pedido - gastado
    if resto <= 0:
        raise SinPresupuestoHeredado(
            "el pedido autorizó USD %s y el linaje del plan ya gastó USD %s. No "
            "queda techo para ejecutarlo: elevarlo es una decisión que dispara "
            "Gate por el criterio 4 del piso de ADR-004, no un ajuste."
            % (techo_pedido, round(gastado, 6))
        )
    return resto


def preparar_herencia(store, run_nombrado, reejecutar=False):
    """Lee el linaje y arma lo que hace falta para abrir la corrida heredera.

    Devuelve `{plan, pedido, origen, hecho}`. `hecho` es el payload de
    `plan_heredado`: de dónde viene el plan, cuál es, de qué veredicto nos
    fiamos, **con qué modo se produjo** y a qué ejecuciones sucede.

    El plan heredado **no se vuelve a verificar**. Es inmutable y su veredicto
    está registrado; reverificarlo sería aplicarle las reglas de hoy a algo
    juzgado bajo las de entonces, y además daría a entender que el registro puede
    estar mal. Lo que se anota es de qué verificación nos fiamos.
    """
    origen = raiz_del_plan(store, run_nombrado)
    plan, iteracion, veredicto = plan_verificado_de(store, origen)

    pedido = pedido_de(store, origen)
    if pedido is None:
        raise PlanNoHeredable(
            "la corrida %s no registró el pedido que la originó; sin él no hay "
            "techo que heredar." % origen
        )

    previas = ejecuciones_del_plan(store, origen)
    if previas and not reejecutar:
        raise PlanYaEjecutado(
            "el plan de la corrida %s ya produjo código en %s. Reejecutarlo deja "
            "el registro con dos respuestas a qué código satisface este plan: si "
            "es lo que querés, pedilo con --reejecutar y la corrida nueva declara "
            "a cuáles sucede." % (origen, ", ".join(previas))
        )

    hecho = {
        "de_corrida": run_nombrado,
        "origen": origen,
        "plan_id": plan.get("plan_id"),
        "iteracion": iteracion,
        "veredicto_evento": veredicto,
        # Con qué se produjo el plan original. Sin esto, leer una entrega
        # producida por un modelo sobre un plan producido por otro —o por el
        # stub— no se puede interpretar después.
        "modo_de_origen": modo_de_produccion(store, origen),
        "ejecuciones_previas": previas,
        "reejecuta": bool(previas),
    }
    return {"plan": plan, "pedido": pedido, "origen": origen, "hecho": hecho}


# --- el nodo que ejecuta las unidades ---------------------------------------


def nodo_ejecutar_unidades(
    store, definicion_developer, producir_entrega_fn, raiz_trabajo,
    ruta_vault=None, costo_iteracion=0.0, qa_fn=None, definicion_qa=None,
):
    """Fabrica el nodo del grafo externo que corre todas las unidades del plan.

    Desde el grafo del pedido es un solo nodo. Adentro, cada unidad es una
    corrida de verdad.

    **Idempotente por obligación**, igual que los nodos de Gate: al reanudar,
    LangGraph lo re-ejecuta desde su primera línea. Las unidades que ya
    entregaron se saltean leyendo el Operational State.

    `qa_fn` y `definicion_qa` van juntos o no van ninguno: sin la definición no
    hay `vault_lectura` que leer, y ADR-014 punto 4 ya dijo qué hace un agente
    ciego —no falla ruidosamente, inventa—. Sin los dos, la cadena corre como en
    V0.2 y ADR-018 no participa.
    """
    if (qa_fn is None) != (definicion_qa is None):
        raise QAIncompleto(
            "para correr la verificación sustantiva de ADR-018 hacen falta las "
            "dos cosas: el productor de casos y la Agent Definition del QA "
            "Agent, que es de donde sale qué documentos del Vault lee. Llegó "
            "sólo %s." % ("el productor" if qa_fn else "la definición")
        )

    techos_developer = {
        "costo": definicion_developer.techo_costo_usd,
        "tiempo_min": definicion_developer.techo_tiempo_min,
        "iteraciones": definicion_developer.techo_iteraciones,
    }
    definicion_dict = definicion_a_dict(definicion_developer)
    definicion_qa_dict = None if definicion_qa is None else definicion_a_dict(definicion_qa)

    def nodo(estado):
        run_pedido = estado["run_id"]
        plan = estado["plan"]
        techo_cadena = estado["techo_cadena"]
        techo_tiempo_cadena = estado["techo_tiempo_cadena"]

        directorio = directorio_registrado(store, run_pedido)
        reanuda = directorio is not None
        if not reanuda:
            directorio = crear_directorio(raiz_trabajo, run_pedido)
            store.append(
                run_pedido,
                "directorio_trabajo",
                PLATAFORMA,
                {"ruta": relativa_a(directorio, _base())},
            )
        else:
            espacio.iniciar(directorio)

        unidades_por_id = {u["id"]: u for u in plan["unidades"]}
        hechas = unidades_entregadas(store, run_pedido)
        entregas_por_unidad = {uid: entrega_de(store, run) for uid, run in hechas.items()}
        runs = list(hechas.values())

        if reanuda:
            reconciliar(store, run_pedido, directorio, entregas_por_unidad)

        for unidad in orden_topologico(plan):
            if unidad["id"] in hechas:
                continue

            gastado = costo_de_la_cadena(store, run_pedido, runs)
            if gastado >= techo_cadena:
                store.append(
                    run_pedido,
                    "techo_cadena_alcanzado",
                    PLATAFORMA,
                    {"costo": gastado, "limite": techo_cadena, "unidad": unidad["id"]},
                )
                return {
                    "directorio": directorio,
                    "entregas": _resumen(store, entregas_por_unidad, hechas),
                    "resultado": "escalado_por_techo_de_cadena",
                }

            minutos = tiempo_de_la_cadena(store, run_pedido)
            if minutos >= techo_tiempo_cadena:
                store.append(
                    run_pedido,
                    "techo_tiempo_cadena_alcanzado",
                    PLATAFORMA,
                    {
                        "tiempo_min": minutos,
                        "limite": techo_tiempo_cadena,
                        "unidad": unidad["id"],
                    },
                )
                return {
                    "directorio": directorio,
                    "entregas": _resumen(store, entregas_por_unidad, hechas),
                    "resultado": "escalado_por_techo_de_tiempo_de_cadena",
                }

            resultado = _correr_unidad(
                store, unidad, plan, unidades_por_id, entregas_por_unidad, run_pedido,
                definicion_developer, definicion_dict, techos_developer, directorio,
                inventario_del_espacio(entregas_por_unidad),
                producir_entrega_fn, ruta_vault, costo_iteracion,
                qa_fn, definicion_qa_dict,
            )
            runs.append(resultado["run_id"])

            if resultado["resultado"] != "entregado":
                store.append(
                    run_pedido,
                    "unidad_fallida",
                    PLATAFORMA,
                    {
                        "unidad": unidad["id"],
                        "run_developer": resultado["run_id"],
                        "motivo": resultado["resultado"],
                    },
                )
                pendientes = [
                    u["id"] for u in orden_topologico(plan)
                    if u["id"] not in hechas and u["id"] != unidad["id"]
                ]
                store.append(
                    run_pedido,
                    "plan_detenido",
                    PLATAFORMA,
                    {
                        "unidad": unidad["id"],
                        "motivo": resultado["resultado"],
                        "sin_ejecutar": pendientes,
                    },
                )
                return {
                    "directorio": directorio,
                    "entregas": _resumen(store, entregas_por_unidad, hechas),
                    "resultado": "escalado_por_unidad_fallida",
                }

            escribir_entrega(directorio, resultado["entrega"])
            commit = espacio.firmar(directorio, _asunto(unidad))
            hechas[unidad["id"]] = resultado["run_id"]
            entregas_por_unidad[unidad["id"]] = resultado["entrega"]
            # El SHA no es reproducible —lo determinan también la fecha y el
            # autor—, así que por el punto 1 de ADR-011 es un hecho y va al
            # registro: regenerar la corrida no lo recupera.
            store.append(
                run_pedido,
                "parte_firmada",
                PLATAFORMA,
                {
                    "unidad": unidad["id"],
                    "run_developer": resultado["run_id"],
                    "commit": commit,
                },
            )
            store.append(
                run_pedido,
                "unidad_entregada",
                PLATAFORMA,
                {"unidad": unidad["id"], "run_developer": resultado["run_id"]},
            )

        return {
            "directorio": directorio,
            "entregas": _resumen(store, entregas_por_unidad, hechas),
        }

    return nodo


def _asunto(unidad):
    """El mensaje del commit de una parte: su identificador y su enunciado.

    Una línea sola, porque `git log --oneline` sobre el espacio es la lista de
    partes firmadas y ahí es donde se lee. Un enunciado de varios renglones se
    corta en el primero por la misma razón.
    """
    enunciado = (unidad.get("enunciado") or "").strip().splitlines()
    return "%s — %s" % (unidad["id"], enunciado[0] if enunciado else "sin enunciado")


def _no_verificables(store, run_developer):
    """Cuántos criterios de la unidad no se pudieron comprobar ejecutando.

    Es la métrica del punto 5 de ADR-018, y se lee del último `qa_ejecutado` de
    la corrida: si el Developer reintentó, lo que vale es la verificación de la
    entrega que quedó. Devuelve `None` cuando QA no corrió, que no es lo mismo
    que cero — cero significa que se comprobó todo.
    """
    eventos = [e for e in store.leer_run(run_developer) if e["tipo"] == "qa_ejecutado"]
    if not eventos:
        return None
    return len(eventos[-1]["payload"]["no_verificables"])


def _resumen(store, entregas_por_unidad, hechas):
    """Lo que se somete en el Gate de salida: qué unidad, qué corrida, qué archivos.

    Cada archivo va con su **SHA-256**, por ADR-015 punto 2. El hash tiene que
    estar en lo que se somete y no sólo en lo que se resuelve: se firma sobre lo
    que se vio. Sin él, "aprobado" no identifica qué se aprobó y una modificación
    posterior del área de entregas sería indetectable.

    El contenido completo de cada archivo sigue sin ir acá: ya está en el
    Operational State, y el Gate se resuelve abriendo los dos HTML, no leyendo
    JSON en una terminal. El hash es corto y sirve para comprobar; el contenido
    volvería ilegible lo que una persona tiene que mirar.

    `no_verificables` es la métrica de ADR-018 punto 5, y va acá porque acá es
    donde la mira una persona. La cuenta habla del plan, no de la entrega: un
    criterio que nadie pudo comprobar ejecutando es un criterio mal escrito por
    el Requirement Agent, y el Gate de salida es donde eso se ve acumulado.
    """
    return [
        {
            "unidad": uid,
            "run_developer": hechas[uid],
            "archivos": [
                {"ruta": a["ruta"], "sha256": sha256_de(a["contenido"])}
                for a in (entregas_por_unidad.get(uid) or {}).get("archivos", [])
            ],
            "no_verificables": _no_verificables(store, hechas[uid]),
        }
        for uid in sorted(hechas)
    ]


def _correr_unidad(
    store, unidad, plan, unidades_por_id, entregas_por_unidad, run_pedido,
    definicion, definicion_dict, techos, directorio, inventario,
    producir_entrega_fn, ruta_vault, costo_iteracion,
    qa_fn=None, definicion_qa=None,
):
    """Abre una corrida de Developer para una unidad y la corre hasta el final."""
    run_id = store.nuevo_run_id()
    store.append(
        run_id,
        "run_iniciada",
        PLATAFORMA,
        {"agent_definition_id": definicion.agent_id, "version": str(definicion.version)},
    )
    # El encadenamiento es un hecho de la corrida del Developer: de qué corrida
    # de Requirement viene y qué unidad de qué plan ejecuta.
    store.append(
        run_id,
        "cadena_iniciada",
        PLATAFORMA,
        {"viene_de": run_pedido, "unidad": unidad["id"], "plan_id": plan["plan_id"]},
    )
    store.append(run_id, "techos_efectivos", PLATAFORMA, techos)
    store.append(
        run_pedido,
        "unidad_lanzada",
        PLATAFORMA,
        {"unidad": unidad["id"], "run_developer": run_id},
    )

    estado = grafo_developer.EstadoDeveloper(
        run_id=run_id,
        definicion=definicion_dict,
        plan=plan,
        unidad=unidad,
        contexto_unidades=contexto_de(unidad, unidades_por_id, entregas_por_unidad),
        directorio=directorio,
        # ADR-014 punto 1: el domicilio y el inventario. Desde ADR-019 el
        # domicilio es el mismo para todas las partes —`directorio`— y lo que
        # cambia entre una y otra es el inventario: qué hay ya en el espacio, de
        # quién es y con qué hash.
        inventario=inventario,
        entrega=None,
        incumplimientos=[],
        iteracion=0,
        resultado=None,
        techos_efectivos=techos,
        definicion_qa=definicion_qa,
        deposito=None,
    )
    compilado = grafo_developer.crear_grafo(
        producir_entrega_fn, store, ruta_vault, costo_iteracion, qa_fn=qa_fn
    )
    final = compilado.invoke(estado)
    return {
        "run_id": run_id,
        "resultado": final.get("resultado") or "entregado",
        "entrega": final.get("entrega"),
    }


__all__ = [
    "CicloDeDependencias",
    "EvidenciaIncompleta",
    "PlanNoHeredable",
    "PlanYaEjecutado",
    "QAIncompleto",
    "SinPresupuestoHeredado",
    "RutaFueraDelDirectorio",
    "RAIZ_TRABAJO_POR_DEFECTO",
    "borrar_directorio",
    "contexto_de",
    "costo_de_la_cadena",
    "crear_directorio",
    "directorio_registrado",
    "entrega_de",
    "escribir_entrega",
    "inventario_del_espacio",
    "materializar_evidencia",
    "nodo_ejecutar_unidades",
    "orden_topologico",
    "preparar_herencia",
    "raiz_entregas",
    "reconciliar",
    "sha256_de",
    "techo_heredado",
    "tiempo_de_la_cadena",
    "ultima_parte_firmada",
    "unidades_entregadas",
]
