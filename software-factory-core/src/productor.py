"""Productor real del Plan de Trabajo — la pieza que invoca al modelo.

Es lo que reemplaza al stub de T14. El armazón no sabe que existe un modelo:
recibe una función con la firma que declara T14 y la llama. Acá se construye esa
función.

**Este módulo no decide nada del proceso.** No abre Gates, no mide techos, no
verifica el plan y no escribe en el Operational State. Produce un plan y declara
cuánto costó producirlo; quien recibe eso decide qué hacer.

El costo se calcula acá y no se estima: sale de los tokens que la respuesta
declara, multiplicados por el precio del modelo. Un costo estimado convertiría
el techo de ADR-010 en una aproximación, y un techo aproximado no es un techo.
"""

import json
import re

from anthropic import Anthropic, APIError

from grafo import FalloDeInfraestructura, RespuestaIlegible
from intake import texto_rastreable
from verificador import LENGUAJE_DE_LA_FABRICA, TERMINOS_AJENOS, cargar_esquema

# Precios de lista en USD por millón de tokens, por modelo. Se actualizan a
# mano cuando cambian: un precio desactualizado no falla, miente, y el techo de
# costo deja de significar lo que dice.
#
# **Verificado el 2026-08-30** contra la tabla "Model pricing" de
# https://platform.claude.com/docs/en/about-claude/pricing —a donde redirige
# `docs.anthropic.com`—, las tres filas. Un precio sin fecha de verificación
# tiene el mismo defecto que un conteo escrito a mano: nadie sabe si sigue
# siendo cierto, y parece que sí.
#
# Acá había una nota que decía que Sonnet 5 se declaraba a 3/15 —el precio de
# lista— mientras regía un introductorio de 2/10, y que eso estaba bien porque
# "sobreestima, nunca subestima". **El razonamiento era falso, y la premisa
# también.** El aumento a 3/15 nunca ocurrió: el introductorio pasó a ser el
# precio estándar y la tabla quedó cobrando 1,5x de más sobre todo.
#
# Lo que hay que recordar de eso no es la fecha, es esto: una tabla
# desactualizada rompe el techo en **las dos** direcciones. La que subestima no
# corta cuando tiene que cortar; la que sobreestima corta corridas que podían
# seguir. Cuál de las dos domina depende de la mezcla de tokens de la corrida,
# así que no se sabe de antemano. No existe la dirección segura en la que
# equivocarse, y por eso no alcanza con que el error sea "conservador".
PRECIOS_USD_POR_MTOK = {
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},
    "claude-opus-5": {"input": 5.00, "output": 25.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}

#: Multiplicadores del caché sobre el precio de **entrada** base, de la misma
#: página y la misma fecha. La documentación los declara como la regla que
#: genera las columnas de caché de la tabla de precios, y las quince filas de
#: esa tabla la cumplen.
#:
#: Las claves son los nombres de los contadores tal como quedan en el desglose,
#: para que `costo_de` los recorra sin traducir nada.
#:
#: **Los dos TTL cuestan distinto y por eso se cobran distinto.** La API manda
#: los dos contadores por separado; hasta hoy los tirábamos y cobrábamos cero
#: por los tres.
MULTIPLICADORES_DE_CACHE = {
    "ephemeral_5m_input_tokens": 1.25,
    "ephemeral_1h_input_tokens": 2.0,
    "cache_read_input_tokens": 0.1,
}

MODELO_POR_DEFECTO = "claude-sonnet-5"

# Techo de salida por invocación. No es el techo de presupuesto de ADR-010 —ese
# lo mide T12 sobre la corrida entera— sino el límite de una sola respuesta.
MAX_TOKENS = 16000


class ModeloSinPrecio(ValueError):
    """El modelo configurado no tiene precio declarado.

    No se arranca sin precio: sin él, el consumo no se puede medir y el techo
    de costo de ADR-010 sería decorativo.
    """


class ProductorSinContexto(ValueError):
    """El productor no recibió los documentos que la Agent Definition declara leer."""


class PlanNoParseable(ValueError):
    """La respuesta del modelo no es JSON.

    No es un fallo de infraestructura: es una iteración mala. El plan vacío que
    devuelve el productor va igual a T7, que lo rechaza, y el ciclo normal de
    corrección se ocupa.
    """


# --- prompt -----------------------------------------------------------------

REGLAS_T7 = """\
El verificador estructural (T7) evalúa ocho reglas sobre el plan. Un plan que
incumple cualquiera de ellas se rechaza y hay que corregirlo.

Antes de las ocho comprueba el esquema JSON. Es una compuerta, no una de ellas:
si el plan no valida, el verificador devuelve `regla 0` y no evalúa nada más.

Regla 1 — Toda unidad de trabajo declara al menos un Acceptance Criterion.

Regla 2 — Todo Acceptance Criterion tiene sus tres partes presentes y no
vacías: `condicion_observable`, `resultado_esperado` y `procedimiento`.

Regla 3 — Toda dependencia declarada por una unidad corresponde al `id` de otra
unidad del mismo plan.

Regla 4 — El campo `rastreo` de cada unidad aparece **literal** en el texto del
pedido. Se comprueba por coincidencia exacta de subcadena: copiá un fragmento
del pedido tal cual está escrito, sin reformular, sin corregir tildes y sin
cambiar mayúsculas.

Regla 5 — Ningún término declarado en `alcance_excluido` aparece en el
`enunciado` ni en el `artefacto_esperado` de ninguna unidad. La comparación
ignora mayúsculas.

Regla 6 — El plan no supera diez unidades de trabajo. Si el problema necesita
más, el pedido es demasiado grande y hay que escalarlo, no partirlo en once.

Regla 7 — El grafo de dependencias no tiene ciclos.

Regla 8 — **El lenguaje no lo elegís vos.** La Fábrica produce {lenguaje} en
V0.2 y eso es un hecho del Contrato de Entrega del Developer, no algo que el
plan suponga: la lógica de cada unidad la tiene que poder cargar un navegador,
porque así es como se verifica. Un plan que pide otro lenguaje pide algo que el
Developer no puede entregar.

Por eso no nombres ningún otro lenguaje ni su herramienta de pruebas —{ajenos}
y sus extensiones de archivo— en `supuestos`, en el `enunciado`, en el
`artefacto_esperado`, en `ruta_artefacto` ni en ninguna de las tres partes de un
criterio. **No declares el lenguaje como supuesto**: si el pedido no lo dice, no
es que quede a criterio de nadie, es que ya está decidido.

`fuera_de_alcance` y `alcance_excluido` no se miran: ahí nombrar un lenguaje es
excluirlo, no comprometerse a él.\
""".format(
    lenguaje=LENGUAJE_DE_LA_FABRICA,
    ajenos=", ".join(TERMINOS_AJENOS),
)

FORMA_DE_RESPUESTA = """\
Respondé únicamente con el objeto JSON del plan. Sin texto antes, sin texto
después, sin explicación y sin bloque de código markdown. El primer carácter de
tu respuesta es `{` y el último es `}`.\
"""


def _system_prompt(esquema, contexto_vault):
    """Arma el prompt de sistema: contrato, esquema, reglas y forma de salida."""
    documentos = "\n\n".join(
        "--- %s ---\n%s" % (ruta, contenido)
        for ruta, contenido in sorted(contexto_vault.items())
    )

    return """\
Sos el Requirement Agent de una fábrica de software. Tu única salida es un Plan
de Trabajo en JSON: convertís un pedido estructurado en unidades de trabajo con
criterios de aceptación verificables. No escribís código, no ejecutás nada y no
producís ningún otro artefacto.

# Normas que te obligan

Estos son los documentos del Vault que tu Agent Definition declara leer. Son
norma, no sugerencia.

{documentos}

# Forma del plan

El plan valida contra este esquema JSON. `additionalProperties` es `false` en
todos los niveles: un campo de más invalida el plan igual que un campo de
menos.

```json
{esquema}
```

# Reglas de verificación

{reglas}

# Cómo se escribe un buen criterio de aceptación

`condicion_observable` describe qué se observa y bajo qué entrada; no es una
intención. `resultado_esperado` dice qué tiene que dar esa observación, en
términos comprobables. `procedimiento` dice cómo se hace la comprobación, con
el detalle suficiente para que otra persona la repita. Un criterio que no se
puede comprobar sin interpretar no cumple la regla 2 aunque tenga las tres
partes llenas.

# La ruta del artefacto es una decisión, no una ilustración

`artefacto_esperado` es prosa: dice **qué** produce la unidad. `ruta_artefacto`
es la ruta exacta, y el Developer está obligado a entregar ese archivo con ese
nombre. Son dos campos porque son dos cosas.

**No escribas rutas de ejemplo en la prosa.** Nada de "(ej. `src/algo.js`)". Si
la ruta importa, va en `ruta_artefacto` y es vinculante. Si no querés fijarla
—porque el Developer está en mejores condiciones de elegirla—, poné
`ruta_artefacto` en `null`. Las dos son decisiones legítimas; lo que no existe
es la ruta escrita al pasar, como quien da un ejemplo, que después alguien
tiene que cumplir al pie de la letra.

# Forma de la respuesta

{forma}\
""".format(
        documentos=documentos,
        esquema=json.dumps(esquema, ensure_ascii=False, indent=2),
        reglas=REGLAS_T7,
        forma=FORMA_DE_RESPUESTA,
    )


def _mensaje_inicial(pedido):
    return """\
Producí el Plan de Trabajo para este pedido.

# Pedido

**Qué se quiere:** {que_se_quiere}

**Para qué:** {para_que}

**Alcance excluido:** {excluido}

**Techos declarados:** costo USD {costo}, tiempo {tiempo} minutos, {iteraciones} iteraciones.

# Texto contra el que se evalúa la regla 4

Cada `rastreo` que escribas tiene que aparecer literal —subcadena exacta— en el
texto que sigue. Es lo único contra lo que se compara:

```
{rastreable}
```

{forma}\
""".format(
        que_se_quiere=pedido["que_se_quiere"],
        para_que=pedido["para_que"],
        excluido=", ".join(pedido["alcance_excluido"]) or "(nada declarado)",
        costo=pedido["techo_costo_usd"],
        tiempo=pedido["techo_tiempo_min"],
        iteraciones=pedido["techo_iteraciones"],
        rastreable=texto_rastreable(pedido),
        forma=FORMA_DE_RESPUESTA,
    )


def _mensaje_correccion(pedido, plan_anterior, incumplimientos):
    """Pide corregir el plan anterior. No pide uno nuevo.

    Regenerar íntegramente lo prohíbe el campo 9 de la Agent Definition: se
    trata como agotamiento. Por eso el plan previo va completo y la instrucción
    es explícita.
    """
    detalle = "\n".join(
        "- Regla {regla}{unidad}{criterio}: {detalle}".format(
            regla=i["regla"],
            unidad=" · unidad %s" % i["unidad"] if i.get("unidad") else "",
            criterio=" · criterio %s" % i["criterio"] if i.get("criterio") is not None else "",
            detalle=i["detalle"],
        )
        for i in incumplimientos
    )

    return """\
El plan que produjiste fue rechazado por el verificador estructural. Corregilo.

# Incumplimientos

{detalle}

# Plan a corregir

```json
{plan}
```

# Cómo corregir

Corregí exactamente los puntos listados y **no toques nada más**. Conservá los
`id` de las unidades, su orden, y todo campo que el verificador no señaló.
Regenerar el plan desde cero en vez de corregirlo se trata como agotamiento y
corta la corrida.

Actualizá `sucede_a` con el `plan_id` del plan que estás corrigiendo, y poné un
`plan_id` nuevo.

# Texto contra el que se evalúa la regla 4

```
{rastreable}
```

{forma}\
""".format(
        detalle=detalle,
        plan=json.dumps(plan_anterior, ensure_ascii=False, indent=2),
        rastreable=texto_rastreable(pedido),
        forma=FORMA_DE_RESPUESTA,
    )


# --- respuesta --------------------------------------------------------------

_CERCA_JSON = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")


def _texto_de(respuesta):
    return "".join(b.text for b in respuesta.content if b.type == "text")


def parsear_plan(texto):
    """Devuelve el plan. Levanta `PlanNoParseable` si la respuesta no es JSON.

    Tolera el bloque de código markdown que el prompt pide no usar: que el
    modelo lo agregue igual es previsible y no amerita gastar una iteración.
    """
    limpio = _CERCA_JSON.sub("", texto.strip())
    try:
        plan = json.loads(limpio)
    except ValueError as error:
        raise PlanNoParseable("la respuesta no es JSON: %s" % error)
    if not isinstance(plan, dict):
        raise PlanNoParseable("la respuesta es JSON pero no es un objeto.")
    return plan


#: Campos del `usage` que se guardan cuando la API los manda. Sólo éstos: cada
#: uno es un número que la respuesta declara, no una estimación nuestra. Los que
#: vuelven `None` —`output_tokens_details` sin extended thinking encendido,
#: `server_tool_use` sin herramientas de servidor— no se guardan: un campo en
#: cero y un campo ausente dicen cosas distintas, y confundirlos arruinaría la
#: medición el día que se enciendan.
CAMPOS_DE_USO = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)

#: Escritura de caché desglosada por TTL. La API la manda anidada bajo
#: `cache_creation`, aparte de la suma plana de arriba.
#:
#: Se guarda porque los dos TTL cuestan distinto —1,25x la entrada base a 5
#: minutos, 2x a una hora— y la suma sola no permite cobrar bien. Sin esto, el
#: día que alguien agregue `"ttl": "1h"` el costo se duplica en silencio: el
#: contador plano no cambia de nombre ni de forma, sólo pasa a valer el doble.
CAMPOS_DE_CACHE_POR_TTL = (
    "ephemeral_5m_input_tokens",
    "ephemeral_1h_input_tokens",
)


def _escritura_sin_ttl(contadores):
    """Escritura de caché que no viene desglosada por TTL, y hay que cobrar igual.

    `cache_creation_input_tokens` es la suma de los dos TTL. Cuando el desglose
    está, esta función devuelve cero y cada TTL se cobra a su precio. Cuando no
    está —eventos escritos antes de que empezáramos a guardarlo— queda la suma
    sola y hay que cobrarla a algún precio.

    Se cobra a 5 minutos, y **no es una estimación prudente: es un hecho sobre
    esas corridas.** Los dos `cache_control` de la fábrica son
    `{"type": "ephemeral"}` sin `ttl`, y sin `ttl` la API cachea a 5 minutos. Lo
    escrito en el registro hasta hoy es todo escritura de 5 minutos.

    El día que alguien ponga `"ttl": "1h"`, esa llamada va a traer el desglose y
    se va a cobrar al doble por la rama de arriba, no por ésta.
    """
    if any(campo in contadores for campo in CAMPOS_DE_CACHE_POR_TTL):
        return 0
    return contadores.get("cache_creation_input_tokens", 0)


def costo_de(contadores, modelo):
    """Costo real de una invocación, en dólares, según los tokens declarados.

    **Cobra los cuatro contadores.** Antes cobraba dos, y con el caching
    encendido en el Developer y en QA los tokens de caché no se cobraban: el
    techo medía sobre una corrida más barata que la real.

    Recibe el desglose de contadores —el mismo diccionario que después queda
    escrito en el evento—, no el `usage` de la API, y eso es deliberado. La única
    forma de saber qué habría costado una corrida vieja con la fórmula de hoy es
    correr esta misma función sobre lo que quedó registrado. Si acá se pidiera un
    objeto de la API, para recalcular habría que reescribir la fórmula, y una
    fórmula duplicada no sirve para verificar a la otra: verifica a sí misma.

    Los contadores que faltan valen cero. Eso es exactamente lo que corresponde a
    los eventos viejos, que no los tienen: declararon lo que declararon y no se
    reescriben.
    """
    precio = PRECIOS_USD_POR_MTOK[modelo]
    total = (
        contadores.get("input_tokens", 0) * precio["input"]
        + contadores.get("output_tokens", 0) * precio["output"]
    )
    for campo, multiplicador in MULTIPLICADORES_DE_CACHE.items():
        total += contadores.get(campo, 0) * precio["input"] * multiplicador
    total += (
        _escritura_sin_ttl(contadores)
        * precio["input"]
        * MULTIPLICADORES_DE_CACHE["ephemeral_5m_input_tokens"]
    )
    return total / 1_000_000


def consumo_de(uso, modelo, stop_reason=None):
    """Lo que costó una invocación **y en qué se fue**.

    `costo` es el mismo número de siempre y se sigue llamando igual: es el que
    suma el contador de techos y el que traen los eventos viejos.

    Lo demás es el desglose. Existe porque un costo sin desglose no se puede
    explicar: en la corrida `94cc2ae4` un paso de QA valió cuatro veces y media
    que otro y produjo cero casos, y no había cómo saber si la plata se fue en
    entrada o en salida. Con `output_tokens` al lado, eso se contesta leyendo el
    evento.

    `stop_reason` no sale del `usage` sino de la respuesta. Va igual, porque los
    dos datos solos no alcanzan: el desglose muestra que una respuesta fue
    enorme y `stop_reason` dice si además quedó cortada.

    La escritura de caché se guarda dos veces y no es redundancia: plana en
    `cache_creation_input_tokens`, que es la suma, y abierta por TTL bajo
    `cache_creation`. Se cobra por la abierta, porque los dos TTL valen distinto.
    La suma se guarda igual porque es lo que la API declara al mismo nivel que
    los otros contadores y porque es la única forma de comparar contra los
    eventos viejos, que sólo tienen ésa.

    Los contadores se arman **antes** de cobrar y se cobran desde el mismo
    diccionario que se guarda. Así el evento y el precio no pueden discrepar: lo
    que quedó escrito es exactamente lo que se facturó.
    """
    contadores = {}
    for campo in CAMPOS_DE_USO:
        valor = getattr(uso, campo, None)
        if valor is not None:
            contadores[campo] = valor
    creacion = getattr(uso, "cache_creation", None)
    for campo in CAMPOS_DE_CACHE_POR_TTL:
        valor = getattr(creacion, campo, None)
        if valor is not None:
            contadores[campo] = valor

    consumo = {"costo": costo_de(contadores, modelo), "modelo": modelo}
    consumo.update(contadores)
    razonamiento = getattr(
        getattr(uso, "output_tokens_details", None), "thinking_tokens", None
    )
    if razonamiento is not None:
        consumo["thinking_tokens"] = razonamiento
    if stop_reason is not None:
        consumo["stop_reason"] = stop_reason
    return consumo


# --- interfaz ---------------------------------------------------------------


def crear_productor(api_key, modelo=MODELO_POR_DEFECTO, ruta_vault=None, cliente=None):
    """Devuelve la `producir_fn` que espera T14, cableada contra el modelo real.

    La función devuelta cumple la firma del armazón —`(pedido, plan_anterior,
    incumplimientos, contexto_vault)`— y responde `(plan, costo)`.

    `ruta_vault` no se usa para leer: los documentos llegan en `contexto_vault`,
    que el armazón ya leyó respetando el `vault_lectura` de la Agent Definition.
    Se conserva para nombrarla en el error cuando ese contexto llega vacío.

    `cliente` existe para los tests: permite ejercitar el armado del prompt, el
    parseo y el cálculo de costo sin invocar al proveedor. En producción se deja
    en `None` y el cliente se construye acá.
    """
    if modelo not in PRECIOS_USD_POR_MTOK:
        raise ModeloSinPrecio(
            "el modelo '%s' no tiene precio declarado en PRECIOS_USD_POR_MTOK; "
            "sin precio el consumo no se puede medir y el techo de ADR-010 no "
            "se puede sostener. Modelos con precio: %s."
            % (modelo, ", ".join(sorted(PRECIOS_USD_POR_MTOK)))
        )

    cliente = Anthropic(api_key=api_key) if cliente is None else cliente
    esquema = cargar_esquema()

    def producir(pedido, plan_anterior, incumplimientos, contexto_vault):
        if not contexto_vault:
            raise ProductorSinContexto(
                "el productor no recibió ningún documento del Vault. La Agent "
                "Definition declara qué leer en `vault_lectura`; sin el Contrato "
                "del Plan de Trabajo el agente produce a ciegas. Indicá la raíz "
                "del Vault con --vault (valor actual: %r)." % (ruta_vault,)
            )

        # Sin plan previo —o con el plan vacío que deja una iteración cuya
        # respuesta no fue JSON— no hay nada que corregir: se produce de nuevo.
        if not plan_anterior:
            mensaje = _mensaje_inicial(pedido)
        else:
            mensaje = _mensaje_correccion(pedido, plan_anterior, incumplimientos)

        try:
            respuesta = cliente.messages.create(
                model=modelo,
                max_tokens=MAX_TOKENS,
                system=_system_prompt(esquema, contexto_vault),
                messages=[{"role": "user", "content": mensaje}],
            )
        except APIError as error:
            # Red, autenticación, límite de tasa, sobrecarga. No es una
            # iteración mala: es que la fábrica no pudo trabajar.
            raise FalloDeInfraestructura(
                "el proveedor del modelo no respondió: %s" % error
            )

        consumo = consumo_de(respuesta.usage, modelo, respuesta.stop_reason)

        if respuesta.stop_reason == "refusal":
            # No se autocorrige: un rechazo por políticas no cambia porque se
            # reintente. Escala, llevando el consumo que ya se pagó.
            raise FalloDeInfraestructura(
                "el modelo rechazó el pedido por políticas de contenido. La "
                "corrida se corta y el pedido se revisa a mano.",
                consumo=consumo,
            )

        # Una respuesta cortada o no parseable sigue siendo una iteración mala y
        # no un fallo de la fábrica: T7 rechaza el plan vacío por la regla 0 y el
        # ciclo de corrección hace su trabajo. Lo que cambia es que ahora se dice
        # cuál de las dos fue, en vez de devolver `{}` a secas y dejar que el
        # registro no distinga una respuesta cortada de una ilegible.
        if respuesta.stop_reason == "max_tokens":
            raise RespuestaIlegible(
                "truncada",
                "el modelo llegó al techo de %d tokens de salida y la respuesta "
                "quedó cortada." % MAX_TOKENS,
                consumo=consumo,
            )
        try:
            return parsear_plan(_texto_de(respuesta)), consumo
        except PlanNoParseable as error:
            raise RespuestaIlegible("no_parseable", str(error), consumo=consumo)

    return producir
