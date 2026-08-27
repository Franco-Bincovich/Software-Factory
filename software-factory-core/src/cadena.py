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
from grafo import PLATAFORMA, _Techos, definicion_a_dict

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
        techo_cadena = estado["pedido"]["techo_costo_usd"]

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
    "unidades_entregadas",
]
