"""Productor real de Entregas — la pieza que invoca al modelo para el Developer.

Es lo que reemplaza al stub del Developer, y el equivalente de T15 para el otro
extremo de la cadena. El grafo no sabe que existe un modelo: recibe una función
con la firma que declara `grafo_developer` y la llama.

**Este módulo no decide nada del proceso.** No abre Gates, no mide techos, no
verifica la entrega y no escribe en el Operational State. Produce una entrega y
declara cuánto costó producirla.

Tres diferencias con `productor.py`, y las tres tienen motivo:

**Caché de prompt sobre el system prompt.** Los cuatro documentos que la Agent
Definition del Developer declara leer pesan unos 14.000 tokens, y viajan en cada
iteración de cada unidad. Un plan de diez unidades con tres iteraciones son hasta
treinta llamadas con el mismo prefijo. Sin caché, el contexto solo se come el
techo de USD 0.50 por unidad antes de generar una línea.

**Streaming con techo de salida más alto.** Una Entrega son cuatro archivos
completos escapados en JSON. Truncar cuesta una iteración pagada que devuelve
entrega vacía, y el SDK exige streaming para techos de salida altos.

**La entrega vacía con motivo escala, no se corrige.** El Contrato de Entrega la
declara una entrega válida ante una unidad ambigua. Reintentarla tres veces
quemaría el techo en una unidad que ya dijo que no se puede.
"""

import json

from anthropic import APIError

from grafo import FalloDeInfraestructura, RespuestaIlegible, UnidadAmbigua
from productor import (
    MODELO_POR_DEFECTO,
    PRECIOS_USD_POR_MTOK,
    ModeloSinPrecio,
    _CERCA_JSON,
    consumo_de,
)
from verificador_entrega import REGLAS, cargar_esquema

# Una Entrega son cuatro archivos completos. El techo de T15 —16.000— alcanza
# para una unidad chica y trunca en cuanto la unidad es real, y una respuesta
# truncada es una iteración pagada que no sirve.
MAX_TOKENS = 32000


class EntregaNoParseable(ValueError):
    """La respuesta del modelo no es JSON.

    No es un fallo de infraestructura: es una iteración mala. La entrega vacía
    que devuelve el productor va igual al verificador, que la rechaza, y el ciclo
    normal de corrección se ocupa.
    """


class DeveloperSinContexto(ValueError):
    """El productor no recibió los documentos que la Agent Definition declara leer."""


# --- prompt -----------------------------------------------------------------

REGLAS_DEL_VERIFICADOR = """\
El verificador estructural de entregas evalúa estas reglas. Una entrega que
incumpla cualquiera se rechaza y hay que corregirla. El identificador de cada
regla es el que vas a recibir si te la rechazan.

C0 — La entrega valida contra el esquema JSON. `additionalProperties` es `false`
en todos los niveles: un campo de más la invalida igual que uno de menos. Los
únicos campos de la entrega son `unidad`, `archivos` y `supuestos`.

C1 — `unidad` es el identificador exacto de la unidad que te pasaron. Una sola.

C2 — Toda `ruta` es relativa. Nunca absoluta, y ningún segmento es `..`.

C3 — Todo `contenido` viene completo. Están prohibidos los marcadores de
fragmento: `// resto igual`, `...`, `// sin cambios`, `resto del archivo` o
cualquier variante que delegue en el lector reconstruir el archivo.

C4 — Si la unidad declara un artefacto esperado con nombre de archivo, ese
archivo está en la entrega.

C5 — Todo archivo que no sea uno de los cuatro entregables va con
`rol: "auxiliar"` y un `motivo` que diga por qué existe. Los cuatro entregables
van con `rol: "artefacto_esperado"`.

C6 — Los cuatro entregables están **en el espacio de trabajo** y ninguno está
vacío. Cuentan los que trae tu entrega más los que ya dejaron las partes
anteriores: si la lógica ya está, no la vuelvas a traer.

C7 — `pruebas.html` y `demo.html` cargan con `<script src="...">` **todos** los
archivos de lógica que hay en el espacio, no sólo el tuyo, y **ninguno de los dos
reimplementa una función**. Dos copias de una función divergen en silencio.

C8 — No hay dos archivos con la misma ruta.

C10 — Ningún archivo tuyo repite una ruta que otra parte ya depositó. Con el
mismo contenido es duplicar y con contenido distinto es pisar algo aprobado; las
dos se rechazan. `pruebas.html` y `demo.html` son la única excepción: se
reescriben enteros por diseño.

R1 — Ningún archivo pasa de 200 líneas.

R3 — Sin `console.log(` en ninguna parte. Sin secretos literales.

R8 — El archivo de pruebas invoca la función de la lógica.

P1 — Nada de red: sin `fetch(`, `XMLHttpRequest`, `WebSocket`, `EventSource` ni
módulos de red.

P2 — Nada de variables de entorno: sin `process.env` ni equivalentes.

P3 — Nada de escribir fuera del directorio de trabajo: sin `fs`, sin
`child_process`.

V1 — Cada archivo parsea. Se comprueba con el parser real, sin ejecutar nada.

V2 — Los nombres que los criterios de aceptación mencionan aparecen en el código
entregado. Si el criterio nombra `validarLegajo`, la función se llama así.

V3 — `pruebas.html` invoca la función de la lógica por su nombre.

V4 — Los veredictos de `pruebas.html` salen de ejecutar la función, nunca de
texto fijo. Un veredicto escrito en el HTML estático se rechaza, y un literal
asignado sin depender del resultado también.

V5 — La entrega se resuelve sola: no hay nada que instalar ni que bajar. Sin
`package.json` ni lockfiles. Sin `node_modules`. Todo `require` es de un builtin
de Node —`node:test`, `node:assert`, `node:path`— o de una ruta relativa que
queda dentro del directorio de trabajo; un nombre de paquete se rechaza. Sin
`import` de paquete. Y el `src` de cada `<script>` es una ruta relativa dentro
del directorio: nunca una URL, nunca un CDN.\
"""

LOS_CUATRO_ENTREGABLES = """\
Son cuatro archivos. No tres, no cinco. **Son de la cadena, no tuyos**: lo que se
exige es que los cuatro estén en el espacio de trabajo cuando cierres, no que los
hayas producido todos vos.

1. **El código de la lógica**, en JavaScript. Declarado como `function` global
   para que los dos HTML lo carguen con un `<script>` clásico, y exportado con
   `module.exports` al final para que el archivo de pruebas lo consuma desde
   Node. Un archivo por parte, una sola definición de cada función.

2. **El archivo de pruebas**, con `node:test` y `node:assert`. Un test por cada
   Acceptance Criterion de la unidad.

3. **`pruebas.html`**, que se abre en cualquier navegador sin servidor y sin
   instalación. Carga la lógica con `<script src="...">` —**no** con `import` ni
   `type="module"`, que no cargan desde `file://`—, ejecuta las funciones reales
   contra los casos declarados en los criterios, y muestra cuáles pasaron. El
   veredicto sale de comparar lo que devolvió la función contra lo esperado.

4. **`demo.html`**, una interfaz operable por una persona: entrada, acción y
   resultado en pantalla, sin recargar. Carga los mismos archivos de lógica. El
   resultado se muestra en pantalla, no por consola: `console.log(` está
   prohibido por R3.

## Contenido y agregadores

Los dos primeros son **contenido** y el espacio crece por agregado: sumás
archivos propios y no tocás los de las partes anteriores.

Los dos HTML son **agregadores**: existen para mostrar todo lo que hay en el
espacio, así que los reescribís enteros incluyendo lo tuyo **y lo que ya estaba**.
Si el espacio ya tiene lógica de otra parte, tu `pruebas.html` y tu `demo.html`
la siguen cargando y siguen mostrando sus casos. Reescribirlos no es pisar trabajo
ajeno: es lo único que pueden hacer.\
"""

FORMA_DE_RESPUESTA = """\
Respondé únicamente con el objeto JSON de la entrega. Sin texto antes, sin texto
después, sin explicación y sin bloque de código markdown. El primer carácter de
tu respuesta es `{` y el último es `}`.\
"""

CUANDO_NO_PODES = """\
Si la unidad es ambigua o contradictoria —si no podés satisfacer sus criterios
sin interpretar la intención de quien escribió el plan, o si se contradicen entre
sí— **devolvé la entrega vacía con el motivo. No adivines.**

La entrega vacía es una entrega válida: `archivos` es una lista vacía y el motivo
va en `supuestos`. No es un fallo y no se reintenta: escala a una persona. Un
agente que completa huecos por su cuenta produce código que parece correcto y
responde a un requerimiento que nadie pidió.\
"""


def _system_prompt(esquema, contexto_vault):
    """Contrato, esquema, reglas y forma de salida.

    Es el prefijo estable de todas las llamadas de todas las unidades del plan, y
    por eso es lo que se cachea. Nada que varíe por unidad entra acá.
    """
    documentos = "\n\n".join(
        "--- %s ---\n%s" % (ruta, contenido)
        for ruta, contenido in sorted(contexto_vault.items())
    )

    return """\
Sos el Developer Agent de una fábrica de software. Tu única salida es una Entrega
en JSON: convertís **una** unidad de trabajo de un Plan de Trabajo en código que
cumple sus Acceptance Criteria. No verificás tu propio trabajo, no ejecutás nada
y no declarás si tus pruebas pasan: eso lo hace otro.

# Normas que te obligan

Estos son los documentos del Vault que tu Agent Definition declara leer. Son
norma, no sugerencia.

{documentos}

# Forma de la entrega

La entrega valida contra este esquema JSON.

```json
{esquema}
```

# Los cuatro entregables

{entregables}

# Reglas de verificación

{reglas}

# Cuando no podés

{no_podes}

# Forma de la respuesta

{forma}\
""".format(
        documentos=documentos,
        esquema=json.dumps(esquema, ensure_ascii=False, indent=2),
        entregables=LOS_CUATRO_ENTREGABLES,
        reglas=REGLAS_DEL_VERIFICADOR,
        no_podes=CUANDO_NO_PODES,
        forma=FORMA_DE_RESPUESTA,
    )


def _criterios_de(unidad):
    return "\n\n".join(
        "**Criterio {n}**\n- Condición observable: {c}\n- Resultado esperado: {r}\n"
        "- Procedimiento: {p}".format(
            n=i + 1,
            c=criterio.get("condicion_observable", ""),
            r=criterio.get("resultado_esperado", ""),
            p=criterio.get("procedimiento", ""),
        )
        for i, criterio in enumerate(unidad["criterios"])
    )


def _contexto_de_dependencias(contexto_unidades):
    """Las unidades de las que depende, con sus entregas. Contexto, no trabajo."""
    if not contexto_unidades:
        return "Esta unidad no depende de ninguna otra."

    partes = []
    for entrada in contexto_unidades:
        dependencia = entrada["unidad"]
        entrega = entrada.get("entrega") or {}
        archivos = "\n\n".join(
            "Archivo `%s`:\n```\n%s\n```" % (a["ruta"], a["contenido"])
            for a in entrega.get("archivos", [])
        )
        partes.append(
            "## Unidad {id} — {enunciado}\n\n{archivos}".format(
                id=dependencia["id"],
                enunciado=dependencia["enunciado"],
                archivos=archivos or "(sin entrega registrada)",
            )
        )
    return (
        "Son **contexto de lectura**. No las modifiques, no las re-entregues y no "
        "las corrijas: ya están hechas y verificadas.\n\n" + "\n\n".join(partes)
    )


def _inventario(depositado):
    """La tabla de qué hay en el espacio, de quién es y con qué hash.

    El hash va porque es lo que el agente necesita para entender el rechazo de
    C10 cuando llega: sin él, "ya depositaste este archivo" no le dice si lo que
    hizo fue copiar o pisar.
    """
    if not depositado:
        return (
            "El espacio está vacío: sos la primera parte. Todo lo que entregues "
            "queda firmado para las que vengan después."
        )
    filas = "\n".join(
        "| `%s` | %s | `%s` |" % (a["ruta"], a.get("parte", "?"), (a.get("sha256") or "")[:12])
        for a in depositado
    )
    return """\
Esto ya está en el espacio, firmado por las partes anteriores:

| Archivo | Parte | SHA-256 |
|---|---|---|
{filas}

**Lo firmado no se reabre.** No vuelvas a entregar ninguno de esos archivos: ni
con el mismo contenido —eso es duplicar trabajo que ya está hecho— ni con
contenido distinto —eso es pisar algo que ya se aprobó—. Las dos cosas las rechaza
C10.

Los dos únicos que sí reescribís son `pruebas.html` y `demo.html`, y los
reescribís **enteros**: con lo tuyo y con lo que ya mostraban.

Si tu unidad no se puede hacer sin modificar alguno de los otros, no la fuerces:
devolvé la entrega vacía diciendo cuál y por qué. Reabrir lo aprobado es una
decisión de una persona, no tuya.\
""".format(filas=filas)


def _donde_trabajas(paquete):
    """Dónde aterrizan sus archivos y qué hay ya en el espacio. ADR-014 punto 1.

    Va en el mensaje del turno y no en el system prompt: varía por parte, y el
    system prompt es el prefijo cacheado. Meter acá algo que cambia invalidaría
    el caché en cada unidad del plan.

    **Esta sección se dio vuelta con ADR-019.** Antes decía que el directorio era
    de la unidad y de ninguna otra, y que por eso los nombres del contrato no
    chocaban. Ahora el espacio es uno solo y compartido: lo que evita el choque no
    es una pared sino saber qué hay adentro y que lo firmado no se toca.
    """
    paquete = paquete or {}
    directorio = paquete.get("directorio_trabajo")
    if not directorio:
        return ""

    return """
# Dónde trabajás

Tus archivos se depositan en `{directorio}`, que es el espacio de trabajo de la
cadena entera. Las rutas que declarás en la entrega son relativas a ese
directorio, y **lo compartís con las demás partes del plan**: las que ya
entregaron dejaron sus archivos ahí y las que vengan después van a ver los tuyos.

Ese espacio es lo que hace que puedas usar lo anterior sin copiarlo. Si necesitás
la lógica de otra parte, `require` su archivo por su ruta relativa: está ahí, al
lado del tuyo.

Entregá los nombres fijos del contrato —`pruebas.html`, `demo.html`— tal como el
contrato manda. No los renombres, no les agregues el identificador de la unidad y
no inventes variantes: son los agregadores, y se reescriben.

{inventario}
""".format(directorio=directorio, inventario=_inventario(paquete.get("inventario")))


def _mensaje_inicial(unidad, contexto_unidades, paquete=None):
    """La unidad que le toca y sus dependencias. Nunca el plan completo."""
    return """\
Producí la Entrega para esta unidad de trabajo. Es la única unidad que te toca:
no ves el plan completo y no decidís qué se hace después.

# Unidad {id}

**Enunciado:** {enunciado}

**Artefacto esperado:** {artefacto}

# Acceptance Criteria

Son lo que tu entrega tiene que cumplir, y los casos de `pruebas.html` salen de
acá.

{criterios}

# Unidades de las que depende

{dependencias}
{donde}
{forma}\
""".format(
        id=unidad["id"],
        enunciado=unidad["enunciado"],
        artefacto=unidad["artefacto_esperado"],
        criterios=_criterios_de(unidad),
        dependencias=_contexto_de_dependencias(contexto_unidades),
        donde=_donde_trabajas(paquete),
        forma=FORMA_DE_RESPUESTA,
    )


def _mensaje_correccion(unidad, entrega_anterior, incumplimientos, paquete=None):
    """Pide corregir la entrega anterior. No pide una nueva.

    Regenerar íntegramente lo prohíbe el campo 9 de la Agent Definition: se trata
    como agotamiento. Por eso la entrega previa va completa y la instrucción es
    explícita.
    """
    detalle = "\n".join(
        "- {regla}{archivo}: {detalle}".format(
            regla=i["regla"],
            archivo=" · archivo %s" % i["archivo"] if i.get("archivo") else "",
            detalle=i["detalle"],
        )
        for i in incumplimientos
    )

    return """\
La entrega que produjiste fue rechazada por el verificador estructural. Corregila.

# Incumplimientos

{detalle}

# Entrega a corregir

```json
{entrega}
```

# Cómo corregir

Corregí exactamente los puntos listados y **no toques nada más**. Todo archivo
que el verificador no señaló vuelve **idéntico**, carácter por carácter: misma
ruta, mismo contenido. Regenerar la entrega desde cero en vez de corregirla se
trata como agotamiento y corta la corrida.

# Unidad {id}

**Enunciado:** {enunciado}

{criterios}
{donde}
{forma}\
""".format(
        detalle=detalle,
        entrega=json.dumps(entrega_anterior, ensure_ascii=False, indent=2),
        id=unidad["id"],
        enunciado=unidad["enunciado"],
        criterios=_criterios_de(unidad),
        donde=_donde_trabajas(paquete),
        forma=FORMA_DE_RESPUESTA,
    )


# --- respuesta --------------------------------------------------------------


def _texto_de(mensaje):
    return "".join(b.text for b in mensaje.content if b.type == "text")


def parsear_entrega(texto):
    """Devuelve la entrega. Levanta `EntregaNoParseable` si no es JSON.

    Tolera el bloque de código markdown que el prompt pide no usar: que el modelo
    lo agregue igual es previsible y no amerita gastar una iteración.
    """
    limpio = _CERCA_JSON.sub("", texto.strip())
    try:
        entrega = json.loads(limpio)
    except ValueError as error:
        raise EntregaNoParseable("la respuesta no es JSON: %s" % error)
    if not isinstance(entrega, dict):
        raise EntregaNoParseable("la respuesta es JSON pero no es un objeto.")
    return entrega


def es_entrega_vacia(entrega):
    """La entrega vacía del contrato: sin archivos, con el motivo en los supuestos."""
    return isinstance(entrega.get("archivos"), list) and not entrega["archivos"]


def motivo_de(entrega):
    supuestos = entrega.get("supuestos") or []
    return "; ".join(str(s) for s in supuestos) or "sin motivo declarado"


# --- interfaz ---------------------------------------------------------------


def crear_productor(api_key, modelo=MODELO_POR_DEFECTO, ruta_vault=None, cliente=None):
    """Devuelve la `producir_fn` que espera `grafo_developer`.

    La función devuelta cumple la firma del grafo del Developer —`(unidad,
    contexto_unidades, entrega_anterior, incumplimientos, contexto_vault,
    paquete)`— y responde `(entrega, costo)`.

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

    if cliente is None:
        from anthropic import Anthropic

        cliente = Anthropic(api_key=api_key)
    esquema = cargar_esquema()

    def producir(unidad, contexto_unidades, entrega_anterior, incumplimientos,
                 contexto_vault, paquete=None):
        if not contexto_vault:
            raise DeveloperSinContexto(
                "el productor de entregas no recibió ningún documento del Vault. "
                "La Agent Definition del Developer declara qué leer en "
                "`vault_lectura`; sin el Contrato de Entrega y el Ruleset "
                "mecánico el agente produce a ciegas. Indicá la raíz del Vault "
                "con --vault (valor actual: %r)." % (ruta_vault,)
            )

        # Sin entrega previa —o con la entrega vacía que deja una iteración cuya
        # respuesta no fue JSON— no hay nada que corregir: se produce de nuevo.
        if not entrega_anterior:
            mensaje = _mensaje_inicial(unidad, contexto_unidades, paquete)
        else:
            mensaje = _mensaje_correccion(unidad, entrega_anterior, incumplimientos, paquete)

        # El system prompt es el prefijo estable de todas las llamadas de todas
        # las unidades del plan: se cachea. Sin esto el contexto del Vault
        # —unos 14.000 tokens— se cobra entero en cada iteración de cada unidad.
        sistema = [
            {
                "type": "text",
                "text": _system_prompt(esquema, contexto_vault),
                "cache_control": {"type": "ephemeral"},
            }
        ]

        try:
            with cliente.messages.stream(
                model=modelo,
                max_tokens=MAX_TOKENS,
                system=sistema,
                messages=[{"role": "user", "content": mensaje}],
            ) as flujo:
                respuesta = flujo.get_final_message()
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
                "el modelo rechazó la unidad por políticas de contenido. La "
                "corrida se corta y la unidad se revisa a mano.",
                consumo=consumo,
            )

        # Una respuesta cortada o no parseable sigue siendo una iteración mala y
        # no un fallo de la fábrica: el verificador rechaza la entrega vacía y el
        # ciclo de corrección hace su trabajo. Lo que cambia es que ahora queda
        # escrito cuál de las dos fue.
        #
        # Ojo con la vecindad: la entrega vacía **deliberada** está unas líneas
        # más abajo y sale por `UnidadAmbigua`. Ésa parseó bien y dice un motivo;
        # ésta no se pudo leer. Que las dos terminen sin entrega no las iguala.
        if respuesta.stop_reason == "max_tokens":
            raise RespuestaIlegible(
                "truncada",
                "el modelo llegó al techo de %d tokens de salida y la respuesta "
                "quedó cortada." % MAX_TOKENS,
                consumo=consumo,
            )
        try:
            entrega = parsear_entrega(_texto_de(respuesta))
        except EntregaNoParseable as error:
            raise RespuestaIlegible("no_parseable", str(error), consumo=consumo)

        if es_entrega_vacia(entrega):
            # El contrato la declara válida y dispara escalamiento. No es un
            # defecto a corregir: reintentarla sería mandar a adivinar
            # exactamente lo que el contrato prohíbe adivinar.
            raise UnidadAmbigua(motivo_de(entrega), consumo=consumo)

        return entrega, consumo

    return producir
