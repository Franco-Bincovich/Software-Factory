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

import grafo_developer
import presupuesto
from grafo import (
    EVENTO_PEDIDO_HEREDADO,
    EVENTO_PLAN_HEREDADO,
    PLATAFORMA,
    _Techos,
    definicion_a_dict,
)

AGENTE = "developer-agent"

RAIZ_TRABAJO_POR_DEFECTO = Path(
    "/Users/franbincovich/Desktop/VSCode/software-factory-state/trabajo"
)


class CicloDeDependencias(RuntimeError):
    """El plan tiene un ciclo y no hay orden posible.

    No debería llegar acá: es la regla 7 de T7 y el plan ya pasó por el
    verificador. Se comprueba igual porque el coordinador no da por buena la
    salida de otra pieza para decidir qué ejecuta.
    """


class RutaFueraDelDirectorio(RuntimeError):
    """Una ruta de la entrega escaparía del directorio de trabajo.

    Es la regla C2 del verificador de entregas, comprobada otra vez acá y a
    propósito. Escribir es irreversible: lo que verifica un módulo y ejecuta otro
    se comprueba en los dos.
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
    """La última entrega producida por una corrida de Developer."""
    entrega = None
    for evento in store.leer_run(run_developer):
        if evento["tipo"] == "entrega_producida":
            entrega = evento["payload"]["entrega"]
    return entrega


def directorio_registrado(store, run_pedido):
    for evento in store.leer_run(run_pedido):
        if evento["tipo"] == "directorio_trabajo":
            return evento["payload"]["ruta"]
    return None


# --- techo de la cadena -----------------------------------------------------


def costo_de_la_cadena(store, run_pedido, runs_developer):
    """Lo gastado por la cadena entera: el Requirement más todos los Developer."""
    total = presupuesto.consumo(store, run_pedido)["costo"]
    for run in runs_developer:
        total += presupuesto.consumo(store, run)["costo"]
    return total


# --- directorio de trabajo --------------------------------------------------


def crear_directorio(raiz, run_pedido):
    """Uno por corrida de plan, descartable, fuera del repositorio y del Vault."""
    ruta = Path(raiz) / run_pedido
    ruta.mkdir(parents=True, exist_ok=True)
    return str(ruta)


def directorio_de_unidad(directorio, unidad_id):
    """Cada unidad escribe en su propio subdirectorio, y no es un detalle.

    El Contrato de Entrega fija los nombres `pruebas.html` y `demo.html`, iguales
    para toda unidad. Dos unidades escribiendo en la misma carpeta se pisarían
    los dos archivos que existen justamente para que una persona verifique. Las
    rutas de la entrega siguen siendo relativas a su unidad; el prefijo lo pone
    la plataforma al depositarla.
    """
    return str(Path(directorio) / unidad_id)


def escribir_entrega(directorio, entrega):
    """Materializa los archivos de una entrega ya verificada.

    Escribe la plataforma, no el agente: el agente declara qué archivos produjo y
    la plataforma los deposita donde corresponde. Es la misma separación por la
    que el agente no ejecuta su propia verificación.

    Solo se llama con una entrega que pasó el verificador. Aun así se comprueba
    que ninguna ruta escape del directorio, porque escribir no se deshace.
    """
    raiz = Path(directorio).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    escritos = []
    for archivo in entrega["archivos"]:
        destino = (raiz / archivo["ruta"]).resolve()
        if raiz not in destino.parents and destino != raiz:
            raise RutaFueraDelDirectorio(
                "la ruta '%s' de la entrega quedaría fuera del directorio de "
                "trabajo '%s'." % (archivo["ruta"], raiz)
            )
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(archivo["contenido"], encoding="utf-8")
        escritos.append(archivo["ruta"])
    return escritos


def borrar_directorio(store, run_pedido, ruta):
    """Se borra **después** de que el Gate de salida se resolvió, nunca antes.

    Borrarlo no pierde nada: la entrega registrada en el Operational State lleva
    el contenido completo de cada archivo. Lo que se descarta es la copia de
    trabajo. Queda registrado con su ruta, que es el ítem 8 de evidencia de la
    Agent Definition: sin eso, después nadie puede saber qué se descartó.
    """
    if ruta and Path(ruta).exists():
        shutil.rmtree(ruta)
    store.append(run_pedido, "directorio_borrado", PLATAFORMA, {"ruta": ruta})


# --- herencia de un plan ya verificado --------------------------------------


class PlanNoHeredable(RuntimeError):
    """La corrida nombrada no tiene un plan verificado que se pueda heredar."""


class PlanYaEjecutado(RuntimeError):
    """El plan ya produjo código en alguna corrida del linaje."""


class SinPresupuestoHeredado(RuntimeError):
    """Lo que el pedido autorizó ya se gastó: no queda techo para ejecutar."""


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
    ruta_vault=None, costo_iteracion=0.0,
):
    """Fabrica el nodo del grafo externo que corre todas las unidades del plan.

    Desde el grafo del pedido es un solo nodo. Adentro, cada unidad es una
    corrida de verdad.

    **Idempotente por obligación**, igual que los nodos de Gate: al reanudar,
    LangGraph lo re-ejecuta desde su primera línea. Las unidades que ya
    entregaron se saltean leyendo el Operational State.
    """
    techos_developer = {
        "costo": definicion_developer.techo_costo_usd,
        "tiempo_min": definicion_developer.techo_tiempo_min,
        "iteraciones": definicion_developer.techo_iteraciones,
    }
    definicion_dict = definicion_a_dict(definicion_developer)

    def nodo(estado):
        run_pedido = estado["run_id"]
        plan = estado["plan"]
        techo_cadena = estado["techo_cadena"]

        directorio = directorio_registrado(store, run_pedido)
        if directorio is None:
            directorio = crear_directorio(raiz_trabajo, run_pedido)
            store.append(run_pedido, "directorio_trabajo", PLATAFORMA, {"ruta": directorio})

        unidades_por_id = {u["id"]: u for u in plan["unidades"]}
        hechas = unidades_entregadas(store, run_pedido)
        entregas_por_unidad = {uid: entrega_de(store, run) for uid, run in hechas.items()}
        runs = list(hechas.values())

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
                    "entregas": _resumen(entregas_por_unidad, hechas),
                    "resultado": "escalado_por_techo_de_cadena",
                }

            resultado = _correr_unidad(
                store, unidad, plan, unidades_por_id, entregas_por_unidad, run_pedido,
                definicion_developer, definicion_dict, techos_developer, directorio,
                producir_entrega_fn, ruta_vault, costo_iteracion,
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
                    "entregas": _resumen(entregas_por_unidad, hechas),
                    "resultado": "escalado_por_unidad_fallida",
                }

            escribir_entrega(
                directorio_de_unidad(directorio, unidad["id"]), resultado["entrega"]
            )
            hechas[unidad["id"]] = resultado["run_id"]
            entregas_por_unidad[unidad["id"]] = resultado["entrega"]
            store.append(
                run_pedido,
                "unidad_entregada",
                PLATAFORMA,
                {"unidad": unidad["id"], "run_developer": resultado["run_id"]},
            )

        return {"directorio": directorio, "entregas": _resumen(entregas_por_unidad, hechas)}

    return nodo


def _resumen(entregas_por_unidad, hechas):
    """Lo que se somete en el Gate de salida: qué unidad, qué corrida, qué archivos.

    El contenido completo de cada archivo no va acá: ya está en el Operational
    State, y el Gate se resuelve abriendo los dos HTML del directorio de trabajo,
    no leyendo JSON en una terminal.
    """
    return [
        {
            "unidad": uid,
            "run_developer": hechas[uid],
            "subdirectorio": uid,
            "archivos": [a["ruta"] for a in (entregas_por_unidad.get(uid) or {}).get("archivos", [])],
        }
        for uid in sorted(hechas)
    ]


def _correr_unidad(
    store, unidad, plan, unidades_por_id, entregas_por_unidad, run_pedido,
    definicion, definicion_dict, techos, directorio, producir_entrega_fn,
    ruta_vault, costo_iteracion,
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
        entrega=None,
        incumplimientos=[],
        iteracion=0,
        resultado=None,
        techos_efectivos=techos,
    )
    compilado = grafo_developer.crear_grafo(
        producir_entrega_fn, store, ruta_vault, costo_iteracion
    )
    final = compilado.invoke(estado)
    return {
        "run_id": run_id,
        "resultado": final.get("resultado") or "entregado",
        "entrega": final.get("entrega"),
    }


__all__ = [
    "CicloDeDependencias",
    "PlanNoHeredable",
    "PlanYaEjecutado",
    "SinPresupuestoHeredado",
    "RutaFueraDelDirectorio",
    "RAIZ_TRABAJO_POR_DEFECTO",
    "borrar_directorio",
    "contexto_de",
    "costo_de_la_cadena",
    "crear_directorio",
    "directorio_de_unidad",
    "directorio_registrado",
    "entrega_de",
    "escribir_entrega",
    "nodo_ejecutar_unidades",
    "orden_topologico",
    "preparar_herencia",
    "techo_heredado",
    "unidades_entregadas",
]
