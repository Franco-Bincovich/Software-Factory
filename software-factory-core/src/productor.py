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
from verificador import cargar_esquema

# Precios de lista en USD por millón de tokens, por modelo. Se actualizan a
# mano cuando cambian: un precio desactualizado no falla, miente, y el techo de
# costo deja de significar lo que dice.
#
# Nota: Sonnet 5 tiene precio introductorio de USD 2 / USD 10 hasta el
# 2026-08-31. Se declara el precio de lista, que es el que rige después y el
# que sobreestima —nunca subestima— el consumo real.
#
# **Reverificar el 2026-08-31.** Ese día vence el introductorio y hay que
# comprobar qué precio queda vigente. Si el de lista bajara a 2/10, esta tabla
# pasaría a sobreestimar un 50% de forma permanente, y un techo medido con
# precios inflados corta corridas que podían seguir.
PRECIOS_USD_POR_MTOK = {
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-opus-5": {"input": 5.00, "output": 25.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
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
El verificador estructural (T7) evalúa siete reglas sobre el plan. Un plan que
incumple cualquiera de ellas se rechaza y hay que corregirlo.

Antes de las siete comprueba el esquema JSON. Es una compuerta, no una de ellas:
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

Regla 7 — El grafo de dependencias no tiene ciclos.\
"""

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


def costo_de(uso, modelo):
    """Costo real de una invocación, en dólares, según los tokens declarados."""
    precio = PRECIOS_USD_POR_MTOK[modelo]
    return (
        uso.input_tokens * precio["input"] + uso.output_tokens * precio["output"]
    ) / 1_000_000


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

    Los tokens de caché se guardan aunque hoy sean cero. `costo_de` no los cobra
    —y no podría cobrarlos con la fórmula que tiene: un token leído de caché se
    factura a una décima parte y no viene dentro de `input_tokens`—, así que el
    día que se encienda el caching el registro va a tener el dato desde antes de
    que la fórmula lo use.
    """
    consumo = {"costo": costo_de(uso, modelo), "modelo": modelo}
    for campo in CAMPOS_DE_USO:
        valor = getattr(uso, campo, None)
        if valor is not None:
            consumo[campo] = valor
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
