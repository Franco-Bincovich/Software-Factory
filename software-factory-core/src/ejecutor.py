"""Ejecutor aislado — la frontera de ADR-016 puesta a correr.

Maquinaria de gobierno, no un agente. Corre un archivo de JavaScript o una
expresión bajo las cuatro restricciones del punto 1 de ADR-016 y devuelve el
resultado. Sin modelo, sin prompt y sin decisiones: acá no se juzga si el
entregable está bien, se lo ejecuta y se informa qué pasó. Quien juzga es el QA
Agent de ADR-018, que es otra cosa y va aparte.

Al terminar una ejecución tiene que ser cierto que el entregable **no pudo**
alcanzar la red, escribir fuera del directorio de la unidad ni colgarse
indefinidamente. "No pudo", no "no lo intentó".

## De dónde sale cada garantía, medido en Node v22.23.1

**Filesystem, procesos y addons — modelo de permisos de Node.** Con
`--permission` y las dos listas de `--allow-fs-*` acotadas al directorio de la
unidad, lo demás queda denegado por defecto, que es la postura de ADR-009.
Medido: leer y escribir afuera dan `ERR_ACCESS_DENIED`; salir por `../` también,
porque normaliza antes de comprobar; `child_process`, `worker_threads` y
`process.binding` dan `ERR_ACCESS_DENIED`; `process.dlopen` da
`ERR_DLOPEN_DISABLED`; y fabricarse un symlink en tiempo de ejecución da
`ERR_ACCESS_DENIED` porque el destino cae fuera de lo permitido.

De ahí sale un beneficio que no era el buscado: **el código ejecutado no puede
engendrar procesos**, así que no hay nietos que puedan quedar huérfanos.

**Tiempo — `SIGKILL` sobre el grupo.** `SIGTERM` es ignorable y el código
ejecutado puede ignorarlo; está medido y hay un test que lo prueba. Un corte por
tiempo que termine en `SIGTERM` es una sugerencia, no un límite.

**Red — frontera del kernel, o no se ejecuta.** Ver abajo, que es lo que hay que
leer antes de tocar este módulo.

## Por qué la red no se bloquea dentro del proceso

El modelo de permisos de Node 22 **no cubre red**: no existe `--allow-net`. Con
`--permission` activo y el filesystem cerrado, `node:net`, `node:dgram` y
`fetch` salieron a internet sin que nada se quejara.

El camino evidente es bloquearla dentro del proceso —parchear `Module._load`,
congelar `fetch` y `WebSocket` desde un `--require`—. **Se intentó y se midió.**
Frenó `require("node:net")`, frenó `fetch` y frenó `process.binding("tcp_wrap")`,
y en el primer intento apareció la evasión: `import("node:net")` dinámico va por
el cargador de ESM, no toca el parche de CommonJS, y abrió una conexión TCP.

Ese hueco puntual se tapa con hooks de ESM. **Eso no cambia la naturaleza de la
cosa, y es lo que importa acá:** un bloqueo escrito en el mismo espacio de
memoria que aquello que intenta contener es una convención, no una frontera.
Comparte el intérprete, los prototipos y el cargador con el código del que se
defiende, así que su alcance es "todos los caminos que quien lo escribió supo
enumerar" — y ADR-016 punto 2 ya nombró a eso por lo que es: "una frontera que
depende de que el contenido resulte inofensivo no es una frontera: es una
expectativa".

Por eso este módulo **exige una frontera de kernel y se niega a ejecutar si no la
consigue**. Degradar al bloqueo en proceso dejaría el código afirmando una
garantía que la máquina no da, en el borde de seguridad y sin que se note.

Si alguien viene a simplificar esto: la simplificación ya se probó, el agujero
tiene nombre, y está cubierto por un test.
"""

import os
import platform
import shutil
import signal
import subprocess
import time
from pathlib import Path

import inspeccion_js as ins

# Node no impone ninguno de los dos por su cuenta: son de este ejecutor.
LIMITE_SEGUNDOS = 10.0
GRACIA_SEGUNDOS = 2.0

# `allow default` y una sola denegación. No es un sandbox general —eso es V0.4 y
# sigue siéndolo—: es la restricción angosta que ADR-016 pide, sobre lo único que
# el modelo de permisos de Node no cubre.
PERFIL_SIN_RED = "(version 1)(allow default)(deny network*)"

# Lo que el proceso ejecutado ve de entorno. Ni el modelo de permisos ni el
# sandbox del sistema protegen las variables de entorno: medido, un `-e` bajo
# las dos capas leyó `process.env.ANTHROPIC_API_KEY` del padre. Y el padre la
# tiene cargada, porque `correr.py` hace `load_dotenv`. Se pasa un entorno mínimo
# en vez de heredar.
ENTORNO_MINIMO = {"PATH": "/usr/bin:/bin", "NODE_ENV": "test"}


class SinFrontera(RuntimeError):
    """No hay frontera de kernel en este sistema, así que no se ejecuta nada.

    Es la negativa deliberada del módulo. El mensaje dice qué se buscó y por qué
    no apareció: un "no puedo ejecutar" a secas manda a alguien a leer código.
    """


class EntradaRechazada(RuntimeError):
    """Llegó algo que la regla V5 habría rechazado, o un symlink.

    El depósito ya pasó por el verificador estructural, así que esto no debería
    ocurrir nunca. Se comprueba igual: ejecutar es irreversible, y un ejecutor
    que confía en que aguas arriba se hizo el control es un ejecutor cuya
    frontera depende de otro módulo.
    """


class Resultado:
    """Qué pasó al correr. Hechos, sin veredicto."""

    def __init__(self, salida, error, codigo, cortado_por_tiempo, frontera, segundos):
        self.salida = salida
        self.error = error
        self.codigo = codigo
        self.cortado_por_tiempo = cortado_por_tiempo
        self.frontera = frontera
        self.segundos = segundos

    def __repr__(self):
        return "Resultado(codigo=%r, cortado_por_tiempo=%r, frontera=%r)" % (
            self.codigo, self.cortado_por_tiempo, self.frontera,
        )


# --- La frontera de red -----------------------------------------------------


def frontera_de_red(sistema=None, buscar=shutil.which):
    """El prefijo de comando que le saca la red al proceso, o `SinFrontera`.

    Devuelve `(nombre, argv_prefijo)`. El nombre viaja en el `Resultado` para que
    quede registrado bajo qué frontera corrió cada ejecución: dos corridas con
    fronteras distintas no son comparables, y el dato no se puede reconstruir
    después.
    """
    sistema = platform.system() if sistema is None else sistema

    if sistema == "Darwin":
        ruta = buscar("sandbox-exec")
        if ruta is None:
            raise SinFrontera(
                "Frontera buscada: `sandbox-exec` con el perfil %s, que en macOS "
                "deniega la red en el kernel.\n"
                "Por qué no se consiguió: no hay `sandbox-exec` en el PATH.\n"
                "Sin frontera de kernel no se ejecuta: el bloqueo de red dentro "
                "del proceso es evadible y está documentado arriba en este "
                "módulo." % PERFIL_SIN_RED
            )
        return "sandbox-exec", [ruta, "-p", PERFIL_SIN_RED]

    raise SinFrontera(
        "Frontera buscada: una que deniegue la red en el kernel para el sistema "
        "'%s'.\n"
        "Por qué no se consiguió: este ejecutor sólo tiene escrita y medida la de "
        "macOS (`sandbox-exec`). En Linux la equivalente es un espacio de nombres "
        "de red —`unshare --net`—, que no está escrita acá y sobre la que no se "
        "midió nada; darla por buena sin medirla sería exactamente lo que este "
        "módulo evita.\n"
        "Sin frontera de kernel no se ejecuta: el bloqueo de red dentro del "
        "proceso es evadible y está documentado arriba en este módulo."
        % sistema
    )


# --- Lo que no debería haber llegado ----------------------------------------


def revisar_entrada(directorio, archivo=None):
    """Rechaza lo que V5 habría rechazado, y los symlinks, que V5 no puede ver.

    **El symlink no es de V5 y no puede serlo.** V5 corre sobre la Entrega, que
    es una lista de `{ruta, rol, contenido}` de texto; un symlink no tiene cómo
    escribirse ahí. Es una propiedad del directorio en disco, y el único módulo
    que mira el directorio es éste. Por eso el control vive acá y no se duplica.

    Importa porque es el único agujero medido del modelo de permisos de Node: un
    symlink que **ya esté** en el directorio cuando arranca el proceso se
    atraviesa sin que el modelo diga nada —se leyó un archivo de afuera a través
    de uno—. Fabricarse uno en tiempo de ejecución sí está bloqueado.

    Lo demás es V5 tal cual, llamada sobre lo que hay en disco: el mismo código
    que corrió sobre la Entrega, corrido otra vez sobre lo que se va a ejecutar.
    """
    raiz = Path(directorio).resolve()
    if not raiz.is_dir():
        raise EntradaRechazada("el directorio de la unidad '%s' no existe." % raiz)

    for ruta in sorted(raiz.rglob("*")):
        relativa = ruta.relative_to(raiz).as_posix()
        if ruta.is_symlink():
            raise EntradaRechazada(
                "'%s' es un enlace simbólico. El modelo de permisos de Node lo "
                "atraviesa sin comprobar adónde apunta, así que un symlink en el "
                "directorio de la unidad es una salida del directorio de la "
                "unidad." % relativa
            )
        if not ruta.is_file():
            continue
        try:
            contenido = ruta.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise EntradaRechazada(
                "'%s' no es texto UTF-8. La frontera de ADR-016 es JavaScript "
                "autocontenido; un binario en el directorio de la unidad queda "
                "fuera de lo que este ejecutor sabe contener." % relativa
            )
        fallos = ins.v5_autocontencion(relativa, contenido)
        if fallos:
            raise EntradaRechazada(
                "'%s' no habría pasado V5: %s" % (relativa, fallos[0]["detalle"])
            )

    if archivo is None:
        return None

    destino = (raiz / archivo).resolve()
    if raiz not in destino.parents and destino != raiz:
        raise EntradaRechazada(
            "'%s' cae fuera del directorio de la unidad '%s'." % (archivo, raiz)
        )
    if not destino.is_file():
        raise EntradaRechazada("'%s' no es un archivo del directorio de la unidad." % archivo)
    return destino


# --- Correr -----------------------------------------------------------------


def _matar(proceso):
    """Al grupo, y terminando en `SIGKILL`.

    Al grupo porque el prefijo de la frontera es otro proceso y no siempre se
    reemplaza a sí mismo; medido en macOS `sandbox-exec` hace `exec` y el pid es
    el mismo, pero la construcción no depende de eso.

    Terminando en `SIGKILL` porque `SIGTERM` se puede ignorar y hay un test que
    lo prueba con código que lo ignora. La gracia intermedia existe para que un
    proceso que sí atiende la señal alcance a cerrar y devolver su salida.
    """
    grupo = os.getpgid(proceso.pid)
    for señal, espera in ((signal.SIGTERM, GRACIA_SEGUNDOS), (signal.SIGKILL, GRACIA_SEGUNDOS)):
        try:
            os.killpg(grupo, señal)
        except ProcessLookupError:
            return
        try:
            proceso.wait(timeout=espera)
            return
        except subprocess.TimeoutExpired:
            continue


def _binario_de_node(buscar=shutil.which):
    """Node por ruta absoluta, resuelta con el `PATH` de quien invoca.

    Absoluta porque el proceso hijo recibe `ENTORNO_MINIMO`, y ahí el `PATH` no
    incluye el Node de un gestor de versiones. Buscarlo con el `PATH` heredado y
    pasarlo resuelto es lo que permite tener las dos cosas: entorno limpio adentro
    y el Node que la máquina usa de verdad.
    """
    ruta = buscar("node")
    if ruta is None:
        raise SinFrontera(
            "No hay `node` en el PATH. La frontera de ADR-016 es JavaScript sobre "
            "Node, así que sin Node no hay nada que ejecutar."
        )
    return ruta


def _correr(argumentos_node, directorio, limite):
    """Lanza Node bajo las dos capas y devuelve el `Resultado`."""
    nombre, prefijo = frontera_de_red()
    raiz = str(Path(directorio).resolve())
    argv = prefijo + [
        _binario_de_node(),
        "--permission",
        "--allow-fs-read=%s" % raiz,
        "--allow-fs-write=%s" % raiz,
    ] + argumentos_node

    inicio = time.monotonic()
    proceso = subprocess.Popen(
        argv,
        cwd=raiz,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(ENTORNO_MINIMO),
        # Grupo propio: sin esto el `killpg` alcanzaría al proceso que llama.
        start_new_session=True,
    )
    try:
        salida, error = proceso.communicate(timeout=limite)
        cortado = False
    except subprocess.TimeoutExpired:
        cortado = True
        _matar(proceso)
        salida, error = proceso.communicate()

    return Resultado(
        salida=salida,
        error=error,
        codigo=proceso.returncode,
        cortado_por_tiempo=cortado,
        frontera=nombre,
        segundos=round(time.monotonic() - inicio, 3),
    )


def ejecutar_archivo(directorio, archivo, limite=LIMITE_SEGUNDOS):
    """Corre un archivo del directorio de la unidad."""
    destino = revisar_entrada(directorio, archivo)
    return _correr([str(destino)], directorio, limite)


def ejecutar_expresion(directorio, expresion, limite=LIMITE_SEGUNDOS):
    """Corre una expresión con el directorio de la unidad como raíz.

    La expresión la escribe QA, no el Developer, así que no pasa por V5. El
    directorio sí: es lo que la expresión va a poder tocar.
    """
    revisar_entrada(directorio)
    return _correr(["-e", expresion], directorio, limite)
