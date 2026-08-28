"""Inspección de los archivos de una Entrega — sin ejecutar nada.

No sabe qué es una Entrega. Recibe texto de archivos y devuelve hallazgos, cada
uno con el identificador de la regla que se incumple. Quien arma el veredicto es
`verificador_entrega`.

El único proceso externo que lanza es `node --check`, que **parsea y sale**: no
corre una sola línea del archivo que revisa. Es lo que hace que "que cada archivo
parsee" sea comprobable sin ejecutar la entrega.

Varias de estas comprobaciones son léxicas y por lo tanto parciales. Están
declaradas como tales una por una, con lo que cada una no puede ver.
"""

import posixpath
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


class NodeNoDisponible(RuntimeError):
    """No hay `node` en el PATH y no se puede comprobar si los archivos parsean.

    No se degrada a "pasa": un verificador que no pudo parsear y aun así aprueba
    miente sobre lo que verificó. Mismo criterio que `ModeloSinPrecio` en T15.
    """


# R1 del Ruleset mecánico, fila "cualquier otro".
LIMITE_LINEAS = 200

RE_SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)
RE_SRC = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""", re.I)
RE_FUNCION = re.compile(r"^[ \t]*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", re.M)
RE_FUNCION_ASIGNADA = re.compile(
    r"^[ \t]*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)", re.M
)


# --- Mecánica común ---------------------------------------------------------


def _hallazgo(regla, ruta, detalle):
    return {"regla": regla, "archivo": ruta, "detalle": detalle}


def es_html(ruta):
    return ruta.lower().endswith((".html", ".htm"))


def es_js(ruta):
    return ruta.lower().endswith((".js", ".mjs", ".cjs"))


def bloques_script(html):
    """(atributos, cuerpo) de cada `<script>` del HTML, en orden de aparición."""
    return [(m.group(1), m.group(2)) for m in RE_SCRIPT.finditer(html)]


def scripts_externos(html):
    """Los `src` de los `<script src=...>`, tal como están escritos."""
    return [RE_SRC.search(attr).group(1) for attr, _ in bloques_script(html) if RE_SRC.search(attr)]


def scripts_inline(html):
    return [cuerpo for attr, cuerpo in bloques_script(html) if not RE_SRC.search(attr)]


def sin_scripts(html):
    """El HTML con los `<script>` recortados: lo que el navegador pinta sin correr nada."""
    return RE_SCRIPT.sub(" ", html)


def funciones_declaradas(texto):
    return [m.group(1) for m in RE_FUNCION.finditer(texto)] + [
        m.group(1) for m in RE_FUNCION_ASIGNADA.finditer(texto)
    ]


def invoca(texto, nombre):
    return re.search(r"\b%s\s*\(" % re.escape(nombre), texto) is not None


# --- V1 — sintaxis ----------------------------------------------------------


def _node():
    ruta = shutil.which("node")
    if ruta is None:
        raise NodeNoDisponible(
            "no hay 'node' en el PATH y sin él no se puede comprobar que los "
            "archivos de la entrega parseen. El verificador no aprueba lo que no "
            "pudo revisar: instalá Node o corré el verificador donde esté."
        )
    return ruta


def error_de_sintaxis(codigo):
    """`None` si el texto parsea; la primera línea del error si no.

    `node --check` parsea el archivo y termina. No lo ejecuta.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
        fh.write(codigo)
        temporal = fh.name
    try:
        salida = subprocess.run(
            [_node(), "--check", temporal], capture_output=True, text=True, timeout=30
        )
    finally:
        Path(temporal).unlink(missing_ok=True)
    if salida.returncode == 0:
        return None
    for linea in salida.stderr.splitlines():
        limpia = linea.strip()
        if limpia.startswith("SyntaxError"):
            return limpia
    return "no parsea"


def v1_sintaxis(ruta, contenido):
    """Cada archivo de código parsea. Los HTML se revisan por bloque `<script>`."""
    if es_js(ruta):
        error = error_de_sintaxis(contenido)
        return [] if error is None else [_hallazgo("V1", ruta, "El archivo no parsea: %s." % error)]
    if not es_html(ruta):
        return []
    fallos = []
    for i, cuerpo in enumerate(scripts_inline(contenido)):
        error = error_de_sintaxis(cuerpo)
        if error is not None:
            fallos.append(
                _hallazgo("V1", ruta, "El bloque <script> número %d no parsea: %s." % (i + 1, error))
            )
    return fallos


# --- Ruleset mecánico — R1, R3, R8 ------------------------------------------


PATRONES_SECRETO = (
    (re.compile(r"""\b(?:api_?key|password|passwd|secret|token)\b\s*[:=]\s*["'][^"']{8,}["']""", re.I),
     "una asignación con forma de secreto literal"),
    (re.compile(r"""["'](?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{12,})["']"""),
     "una credencial con formato conocido"),
)


def r1_tamano(ruta, contenido):
    lineas = len(contenido.splitlines())
    if lineas <= LIMITE_LINEAS:
        return []
    return [
        _hallazgo(
            "R1", ruta, "El archivo tiene %d líneas; el límite es %d." % (lineas, LIMITE_LINEAS)
        )
    ]


def r3_patrones_prohibidos(ruta, contenido):
    """`console.log(` y secretos literales.

    La lectura del entorno también es R3 en el Ruleset, pero acá se reporta como
    P2: es prohibición del contrato y el identificador más específico manda.

    **Parcial.** La detección de secretos es léxica: reconoce formatos conocidos
    y nombres de variable sospechosos, no un secreto guardado con nombre inocente.
    """
    fallos = []
    if "console.log(" in contenido:
        fallos.append(_hallazgo("R3", ruta, "El archivo contiene 'console.log('."))
    for patron, que in PATRONES_SECRETO:
        if patron.search(contenido):
            fallos.append(_hallazgo("R3", ruta, "El archivo contiene %s." % que))
    return fallos


def r8_tests(ruta_pruebas, contenido_pruebas, funciones):
    """El archivo de pruebas existe, no está vacío y ejercita la lógica.

    **Parcial**, y el propio Ruleset lo dice: que el test exista y nombre la
    función es comprobable; que la pruebe bien, no.
    """
    if ruta_pruebas is None:
        return []
    if not any(invoca(contenido_pruebas, nombre) for nombre in funciones):
        nombres = ", ".join(funciones) if funciones else "ninguna función detectada en la lógica"
        return [
            _hallazgo(
                "R8",
                ruta_pruebas,
                "El archivo de pruebas no invoca la lógica entregada (%s)." % nombres,
            )
        ]
    return []


# --- Prohibiciones del contrato — P1, P2, P3 --------------------------------


PATRONES_RED = (
    (re.compile(r"\bfetch\s*\("), "fetch("),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\bWebSocket\b"), "WebSocket"),
    (re.compile(r"\bEventSource\b"), "EventSource"),
    (re.compile(r"\bnavigator\s*\.\s*sendBeacon\b"), "navigator.sendBeacon"),
    (re.compile(r"""\brequire\s*\(\s*["'](?:node:)?(?:http|https|net|dgram)["']"""), "require de un módulo de red"),
)

PATRONES_ENTORNO = (
    (re.compile(r"\bprocess\s*\.\s*env\b"), "process.env"),
    (re.compile(r"\bimport\s*\.\s*meta\s*\.\s*env\b"), "import.meta.env"),
    (re.compile(r"\bDeno\s*\.\s*env\b"), "Deno.env"),
)

PATRONES_ESCRITURA = (
    (re.compile(r"""\brequire\s*\(\s*["'](?:node:)?fs(?:/promises)?["']"""), "require de 'fs'"),
    (re.compile(r"\bfs\s*\.\s*(?:write|append|mkdir|rm|unlink)"), "una escritura con fs"),
    (re.compile(r"""\brequire\s*\(\s*["'](?:node:)?child_process["']"""), "require de 'child_process'"),
)


def _prohibicion(regla, patrones, ruta, contenido, leyenda):
    for patron, que in patrones:
        if patron.search(contenido):
            return [_hallazgo(regla, ruta, "%s: el archivo usa %s." % (leyenda, que))]
    return []


def prohibiciones(ruta, contenido):
    """P1 red, P2 entorno, P3 escritura fuera del directorio de trabajo.

    **Parcial.** Detecta las formas conocidas de hacer cada cosa, no cualquier
    forma: una llamada armada por indirección no se ve leyendo el texto.
    """
    return (
        _prohibicion("P1", PATRONES_RED, ruta, contenido, "El agente no abre conexiones de red")
        + _prohibicion("P2", PATRONES_ENTORNO, ruta, contenido, "El agente no lee variables de entorno")
        + _prohibicion("P3", PATRONES_ESCRITURA, ruta, contenido, "El agente no escribe fuera de su directorio de trabajo")
    )


# --- V3 y V4 — que pruebas.html no sea teatro -------------------------------


RE_VEREDICTO = re.compile(r"\b(?:PASA|FALLA|PASS|FAIL|OK|EXITO|ÉXITO)\b|[✓✔✗✘]")
RE_LITERAL = re.compile(r"""(["'])((?:(?!\1).)*)\1""")
# Un veredicto literal es legítimo si se elige: un ternario, un if o una
# comparación en la misma expresión. Si se asigna pelado, está escrito a mano.
MARCAS_DE_ELECCION = ("?", "if", "===", "!==", "==", "!=")


def v3_invoca_la_funcion(ruta, contenido, funciones):
    """`pruebas.html` invoca la función de la lógica por su nombre."""
    cuerpo = "\n".join(scripts_inline(contenido))
    if any(invoca(cuerpo, nombre) for nombre in funciones):
        return []
    nombres = ", ".join(funciones) if funciones else "ninguna función detectada en la lógica"
    return [
        _hallazgo(
            "V3", ruta, "pruebas.html no invoca la función de la lógica (%s)." % nombres
        )
    ]


def v4_veredictos_fijos(ruta, contenido):
    """Los resultados salen de ejecutar la función, no de texto escrito a mano.

    **Parcial, y es la comprobación más parcial de todas.** Ve un veredicto
    pintado en el HTML estático y ve un literal de veredicto asignado sin elegir.
    No ve un script que invoca la función, ignora lo que devuelve y escribe
    "PASA" igual. Eso queda para el Gate humano, que es el que abre el archivo.
    """
    fallos = []
    estatico = sin_scripts(contenido)
    encontrado = RE_VEREDICTO.search(estatico)
    if encontrado:
        fallos.append(
            _hallazgo(
                "V4",
                ruta,
                "El veredicto '%s' está escrito en el HTML estático, fuera de todo "
                "<script>: no puede salir de ejecutar la función." % encontrado.group(0),
            )
        )
    for cuerpo in scripts_inline(contenido):
        for linea in cuerpo.splitlines():
            if any(marca in linea for marca in MARCAS_DE_ELECCION):
                continue
            for _, literal in RE_LITERAL.findall(linea):
                if RE_VEREDICTO.search(literal):
                    fallos.append(
                        _hallazgo(
                            "V4",
                            ruta,
                            "El veredicto '%s' se asigna sin depender de lo que "
                            "devolvió la función: %s" % (literal, linea.strip()),
                        )
                    )
    return fallos


# --- V5 — autocontención ----------------------------------------------------

# Los módulos que Node trae puestos. Todo lo demás que se pida por nombre hay
# que instalarlo, y la frontera de ADR-016 no instala nada.
BUILTINS_NODE = frozenset(
    """
    assert async_hooks buffer child_process cluster console constants crypto
    dgram diagnostics_channel dns domain events fs http http2 https inspector
    module net os path perf_hooks process punycode querystring readline repl
    stream string_decoder sys timers tls trace_events tty url util v8 vm wasi
    worker_threads zlib
    """.split()
)

# Un manifiesto o un lockfile en la entrega es la declaración explícita de que
# hace falta instalar algo antes de correr.
ARCHIVOS_DE_DEPENDENCIAS = (
    "package.json", "package-lock.json", "npm-shrinkwrap.json",
    "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
)

RE_REQUIRE = re.compile(r"""\brequire\s*\(\s*["']([^"']*)["']\s*\)""")
RE_IMPORT_DINAMICO = re.compile(r"""\bimport\s*\(\s*["']([^"']*)["']\s*\)""")
RE_IMPORT_DESDE = re.compile(
    r"""^[ \t]*(?:import|export)\b[^\n;]*?\bfrom\s*["']([^"']*)["']""", re.M
)
RE_IMPORT_POR_EFECTO = re.compile(r"""^[ \t]*import\s+["']([^"']*)["']""", re.M)
RE_URL = re.compile(r"^(?:[a-z][a-z0-9+.\-]*:)?//", re.I)
RE_RUTA_ABSOLUTA = re.compile(r"^(?:/|[A-Za-z]:)")


def _sale_del_directorio(ruta, especificador):
    """Un especificador relativo que, resuelto desde su archivo, cae afuera.

    Las rutas de la entrega son relativas al directorio de la unidad y sin `..`
    —eso es C2—, así que el directorio de la unidad es la raíz de esas rutas.
    Un `require("../../otro/x.js")` desde `tests/` sale de ahí, y C2 no lo ve:
    C2 mira las rutas **declaradas**, no las que el código resuelve.
    """
    base = posixpath.dirname(ruta.replace("\\", "/"))
    destino = posixpath.normpath(posixpath.join(base, especificador))
    return destino == ".." or destino.startswith("../")


def _rompe_la_autocontencion(ruta, especificador, pelado_es_paquete=True):
    """Por qué el especificador rompe la autocontención, o `None` si no la rompe.

    `pelado_es_paquete` distingue los dos lenguajes que se mezclan en una
    entrega. Para `require` e `import`, un nombre sin `./` es un paquete que hay
    que instalar. Para el `src` de un `<script>` no: ahí `src/u1.js` es una URL
    relativa corriente y tratarla como paquete sería un falso positivo sobre
    entregas correctas.
    """
    if not especificador.strip():
        return None
    if RE_URL.match(especificador):
        return "'%s' se baja de la red al abrir el archivo" % especificador
    if RE_RUTA_ABSOLUTA.match(especificador):
        return "'%s' es una ruta absoluta: sale del directorio de la unidad" % especificador
    if pelado_es_paquete:
        if especificador.startswith("node:") or especificador.split("/")[0] in BUILTINS_NODE:
            return None
        if not especificador.startswith(("./", "../")):
            return (
                "'%s' es un paquete externo y habría que instalarlo antes de correr"
                % especificador
            )
    if _sale_del_directorio(ruta, especificador):
        return "'%s' apunta fuera del directorio de la unidad" % especificador
    return None


def _especificadores(texto):
    """Todo lo que el texto pide cargar, por `require` o por `import`."""
    return (
        RE_REQUIRE.findall(texto)
        + RE_IMPORT_DINAMICO.findall(texto)
        + RE_IMPORT_DESDE.findall(texto)
        + RE_IMPORT_POR_EFECTO.findall(texto)
    )


def v5_autocontencion(ruta, contenido):
    """El entregable se resuelve solo: nada que instalar, nada que bajar.

    Es la condición previa de ADR-016 punto 2 —"se rechaza por regla antes de
    ejecutarse"—, y la razón por la que existe está en el propio ADR: hoy la
    autocontención es **emergente**. Se sigue de que los HTML carguen con
    `<script src>` clásico, de que se abran sin servidor y de la prohibición de
    red, pero ninguna regla la comprueba. Una frontera que se apoya en que el
    contenido resulte inofensivo no es una frontera.

    **No repite lo que ya está cubierto.** Abrir la red desde el código es P1 y
    escribir con `fs` es P3; volver a reportarlos acá mandaría a corregir dos
    veces el mismo defecto, contra la regla del identificador más específico.
    V5 mira otra cosa: de dónde sale el código que el entregable necesita.

    **Parcial**, como las demás comprobaciones léxicas. Ve un especificador
    escrito literalmente entre comillas; no ve un nombre de módulo armado por
    concatenación en tiempo de ejecución.
    """
    normalizada = ruta.replace("\\", "/")
    if posixpath.basename(normalizada) in ARCHIVOS_DE_DEPENDENCIAS:
        return [
            _hallazgo("V5", ruta, "El archivo declara dependencias que habría que instalar.")
        ]
    if "node_modules" in normalizada.split("/"):
        return [_hallazgo("V5", ruta, "El archivo es una dependencia instalada.")]

    # (especificador, si un nombre pelado significa paquete)
    candidatos = []
    if es_js(ruta):
        candidatos = [(e, True) for e in _especificadores(contenido)]
    elif es_html(ruta):
        candidatos = [(src, False) for src in scripts_externos(contenido)]
        for cuerpo in scripts_inline(contenido):
            candidatos += [(e, True) for e in _especificadores(cuerpo)]

    fallos, vistos = [], set()
    for especificador, pelado_es_paquete in candidatos:
        motivo = _rompe_la_autocontencion(ruta, especificador, pelado_es_paquete)
        if motivo is not None and motivo not in vistos:
            vistos.add(motivo)
            fallos.append(
                _hallazgo("V5", ruta, "El entregable no se resuelve solo: %s." % motivo)
            )
    return fallos
