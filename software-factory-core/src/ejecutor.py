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
leer antes de tocar este módulo. En macOS está medida; en Linux está escrita y
**nadie la vio funcionar**, así que se prueba sola antes de usarse.

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

## Por qué en Linux la frontera se prueba en vez de darse por buena

En macOS alcanza con encontrar `sandbox-exec` en el PATH **porque la frontera se
midió**: los tres tests de red corrieron contra ella y fallaron en abrir la
conexión. Encontrar el binario es entonces un proxy legítimo de una garantía ya
comprobada.

En Linux no hay tal medición. La rama se escribió el **2026-08-31** en una
máquina macOS sin Docker ni VM, donde Linux no se puede correr **ni una vez**.
Encontrar `unshare` en el PATH no probaría nada: `unshare --user` falla con
`EPERM` en cualquier Ubuntu 24.04 de fábrica, porque
`kernel.apparmor_restrict_unprivileged_userns` viene en 1. Un `which` que
devolviera el prefijo dejaría al ejecutor afirmando una garantía que la máquina
probablemente no da — el defecto exacto que este módulo existe para no cometer.

Por eso el camino de Linux **corre una sonda y sólo devuelve el prefijo si la
sonda demuestra que la red no está**. La demostración es de la máquina real, en
el momento de usarse, y no de quien escribió esto. Si mañana AppArmor bloquea el
espacio de nombres, `SinFrontera` lo dice con el error del kernel adentro.

La sonda lleva su propio control, y eso no es exceso: **una máquina sin red haría
pasar cualquier frontera, incluso una que no existe.** Así que se observa dos
veces —con el prefijo y sin él— y sólo se acepta la frontera si la diferencia
entre las dos observaciones es la frontera. Sin control, un cable desenchufado se
leería como aislamiento conseguido.

## El plan de contingencia, y por qué no es la opción obvia

Si en la máquina real ni `unshare` ni `bwrap` consiguen el espacio de nombres,
queda un tercer camino: **un filtro `seccomp` que deniegue `socket(AF_INET, …)`**,
instalado con `PR_SET_NO_NEW_PRIVS` entre el `fork` y el `exec`. No necesita
privilegios ni espacios de nombres, así que es inmune a lo que rompe a los otros
dos.

**Está descartado a propósito, y el motivo no es la pereza.** Un espacio de
nombres de red vacío corta el acceso **por ausencia**: adentro no hay interfaz ni
ruta, así que no hay adónde salir y nadie tuvo que enumerar por dónde no. Un
filtro de syscalls corta **por lista**, y esa lista la escribe una persona:
`socket`, `socketcall` en 32 bits, y después la decisión sobre `AF_NETLINK` y
`AF_PACKET`, y después lo que no se nos ocurrió.

Eso lo pone en **la misma familia que el bloqueo en proceso** que este módulo
rechaza más arriba. Es mejor —lo hace cumplir el kernel y `NO_NEW_PRIVS` lo
vuelve irrevocable, así que el código contenido no puede desarmarlo—, pero
comparte la propiedad que importa: su alcance sigue siendo "todos los caminos que
quien lo escribió supo enumerar". El namespace no tiene alcance, tiene vacío.

Se agrega **sólo** si los dos primeros fallan en la máquina real, y con esa
diferencia anotada donde se lo agregue. Lo que no corresponde es adoptarlo por
comodidad: hoy no ahorra nada, y cambia una frontera sin lista por una con lista.
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

#: El día que se escribió la rama de Linux sin poder correrla. Va en el mensaje
#: de `SinFrontera` para que quien lo lea sepa cuán vieja es la suposición.
LINUX_ESCRITA_SIN_MEDIR = "2026-08-31"

#: Los candidatos de Linux, en orden de preferencia. Cada uno es
#: `(nombre, binario, argumentos)`.
#:
#: `unshare` va primero porque es de util-linux, paquete esencial: es el único
#: que no puede faltar en un Ubuntu recién instalado. `bwrap` va después porque
#: hay que instalarlo, no porque sea peor.
#:
#: Las dos variantes de `unshare` son la misma frontera con distinto mapeo de
#: usuario. `--map-current-user` es de util-linux 2.38; Ubuntu 24.04 trae 2.39 y
#: le sirve, Ubuntu 22.04 trae 2.37 y no. **Sin ninguno de los dos mapeos el UID
#: de adentro cae a `nobody` y Node no puede leer el directorio de la unidad**:
#: la frontera andaría y la ejecución fallaría por otra cosa, que es peor que
#: fallar limpio. Por eso no existe la variante pelada.
CANDIDATOS_LINUX = (
    ("unshare-netns", "unshare", ["--user", "--map-current-user", "--net", "--"]),
    ("unshare-netns-root", "unshare", ["--user", "--map-root-user", "--net", "--"]),
    ("bwrap-netns", "bwrap", ["--unshare-net", "--dev-bind", "/", "/", "--"]),
)

#: Lo que la sonda observa, y por qué son dos cosas y no una.
#:
#: `INTERFACES` cuenta las interfaces que no son loopback. Adentro de un espacio
#: de nombres de red recién creado hay una sola, `lo`, y arranca caída: la cuenta
#: da 0. Es la señal principal porque es **instantánea y no depende de que la
#: máquina tenga internet**.
#:
#: `SALIDA` intenta una conexión a TEST-NET-1 (RFC 5737), que no se rutea a
#: ninguna parte. Sin frontera el intento queda colgado hasta el `timeout`; con
#: frontera el kernel contesta `ENETUNREACH` de inmediato, porque no hay ruta.
#: La diferencia entre "tardó" y "no hay por dónde" es la que interesa.
SONDA_JS = (
    'const os=require("node:os");'
    'const n=Object.values(os.networkInterfaces())'
    '.filter(v=>(v||[]).some(a=>!a.internal)).length;'
    'const fin=(r)=>{process.stdout.write("INTERFACES="+n+" SALIDA="+r);'
    "process.exit(0);};"
    'let s;try{s=require("node:net").connect(53,"192.0.2.1");}'
    'catch(e){return fin("ERROR:"+(e.code||e.message));}'
    "s.setTimeout(1500);"
    's.on("connect",()=>{s.destroy();fin("CONECTO");});'
    's.on("error",(e)=>{s.destroy();fin("ERROR:"+(e.code||e.message));});'
    's.on("timeout",()=>{s.destroy();fin("TIMEOUT");});'
)

#: Techo de la sonda. Generoso contra el `setTimeout` de 1500 ms de adentro: si
#: se alcanza, el candidato no arrancó o se colgó, y las dos cosas son "no
#: sirve".
SONDA_LIMITE_SEGUNDOS = 8.0


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


def observar_red(prefijo, limite=SONDA_LIMITE_SEGUNDOS):
    """Corre `SONDA_JS` bajo `prefijo` y devuelve qué vio de la red.

    Devuelve `(interfaces, salida, crudo)`, donde `interfaces` es la cantidad de
    interfaces que no son loopback y `salida` es el síntoma del intento de
    conexión. Si la sonda no llegó a correr —el candidato no arrancó, o se
    colgó—, `interfaces` es `None` y `crudo` trae por qué.

    No juzga: informa. Quien decide si eso es una frontera es `_probar_frontera`,
    que compara esta observación contra la de afuera.
    """
    argv = list(prefijo) + [_binario_de_node(), "-e", SONDA_JS]
    try:
        proceso = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=limite,
            env=dict(ENTORNO_MINIMO),
        )
    except subprocess.TimeoutExpired:
        return None, None, "la sonda no terminó en %.0f s" % limite
    except OSError as e:
        return None, None, "no se pudo lanzar la sonda: %s" % e

    texto = (proceso.stdout or "").strip()
    marcas = dict(
        parte.split("=", 1) for parte in texto.split(" ") if "=" in parte
    )
    if "INTERFACES" not in marcas or "SALIDA" not in marcas:
        detalle = (proceso.stderr or "").strip() or texto or "sin salida"
        return None, None, "código %s — %s" % (proceso.returncode, detalle)
    return int(marcas["INTERFACES"]), marcas["SALIDA"], texto


def _probar_frontera(prefijo, control, observar):
    """¿El prefijo aísla la red? Devuelve `(aisla, detalle)`.

    `control` es la observación de afuera, sin prefijo. **Se compara contra ella
    y no contra una expectativa fija**, porque una máquina sin red haría pasar
    cualquier frontera: si afuera tampoco hay interfaces, la sonda no puede
    distinguir el aislamiento del cable desenchufado, y eso se informa como
    inconcluso en vez de como éxito.
    """
    interfaces_afuera, salida_afuera, crudo_afuera = control
    if interfaces_afuera is None:
        return False, (
            "la sonda de control no corrió ni siquiera sin frontera (%s), así que "
            "no hay contra qué comparar" % crudo_afuera
        )
    if interfaces_afuera == 0:
        return False, (
            "sin frontera esta máquina ya no ve ninguna interfaz de red "
            "(control: %s). La sonda no puede distinguir el aislamiento de una "
            "máquina desconectada, así que no afirma nada" % crudo_afuera
        )

    interfaces, salida, crudo = observar(prefijo)
    if interfaces is None:
        return False, "el candidato no llegó a correr: %s" % crudo
    if interfaces > 0:
        return False, (
            "corrió, pero adentro siguen viéndose %d interfaces de red que no son "
            "loopback (%s). No aisló nada" % (interfaces, crudo)
        )
    if salida == "CONECTO":
        return False, (
            "corrió y no hay interfaces, pero la conexión saliente igual se "
            "estableció (%s). Eso no es una frontera" % crudo
        )
    return True, "adentro %s / afuera %s" % (crudo, crudo_afuera)


def _frontera_linux(buscar, observar):
    """El primer candidato que la sonda apruebe, o `SinFrontera` con el detalle.

    El detalle es todo el punto: si mañana AppArmor bloquea el espacio de
    nombres, el mensaje tiene que alcanzar para saber qué tocar sin volver a
    leer este módulo entero.
    """
    presentes = []
    intentos = []
    for nombre, binario, argumentos in CANDIDATOS_LINUX:
        ruta = buscar(binario)
        if ruta is None:
            intentos.append((nombre, "no está `%s` en el PATH" % binario))
            continue
        presentes.append((nombre, [ruta] + list(argumentos)))

    if not presentes:
        return _sin_frontera_linux(intentos, control=None)

    # El control se observa una sola vez y recién cuando hay algo que comparar.
    control = observar([])
    for nombre, prefijo in presentes:
        aisla, detalle = _probar_frontera(prefijo, control, observar)
        if aisla:
            return nombre, prefijo
        intentos.append((nombre, detalle))
    return _sin_frontera_linux(intentos, control=control)


def _sin_frontera_linux(intentos, control):
    """El mensaje que se lee mañana en la mini PC.

    Dice **que se probó**, no sólo que no hay: qué candidato, con qué argumentos
    y con qué murió. Un "no hay frontera" a secas manda a alguien a reconstruir
    desde cero lo que la máquina ya contestó.
    """
    lineas = [
        "Frontera buscada: un espacio de nombres de red vacío, que en Linux "
        "deniega la red en el kernel por ausencia de interfaz y de ruta.",
        "",
        "Se probó cada candidato con una sonda real; ninguno pasó:",
    ]
    for nombre, detalle in intentos:
        lineas.append("  - %s: %s" % (nombre, detalle))
    if control is not None:
        lineas.append("")
        lineas.append("Observación de control, sin frontera: %s" % (control[2],))
    lineas += [
        "",
        "Qué mirar primero, por probabilidad:",
        "  1. `sysctl kernel.apparmor_restrict_unprivileged_userns` — Ubuntu "
        "24.04 lo trae en 1 de fábrica y eso hace fallar `unshare --user` con "
        "EPERM. Es el motivo más probable de todos.",
        "  2. `unshare --version` — `--map-current-user` es de util-linux 2.38. "
        "Con 2.37 sólo sirve la variante `--map-root-user`.",
        "  3. `sysctl user.max_user_namespaces` — si está en 0, no hay espacios "
        "de nombres de usuario para nadie.",
        "  4. `bwrap` no viene instalado en Ubuntu Server; se instala con "
        "`apt install bubblewrap`.",
        "",
        "Esta rama se escribió el %s en una máquina donde Linux no se podía "
        "correr ni una vez, así que **nadie la vio funcionar**. La sonda existe "
        "por eso: no se da por buena, se comprueba." % LINUX_ESCRITA_SIN_MEDIR,
        "",
        "Antes de reemplazarla por un filtro `seccomp`, leer el docstring de "
        "este módulo: está descartado con motivo, no por olvido.",
        "",
        "Sin frontera de kernel no se ejecuta: el bloqueo de red dentro del "
        "proceso es evadible y está documentado arriba en este módulo.",
    ]
    raise SinFrontera("\n".join(lineas))


def frontera_de_red(sistema=None, buscar=shutil.which, observar=None):
    """El prefijo de comando que le saca la red al proceso, o `SinFrontera`.

    Devuelve `(nombre, argv_prefijo)`. El nombre viaja en el `Resultado` para que
    quede registrado bajo qué frontera corrió cada ejecución: dos corridas con
    fronteras distintas no son comparables, y el dato no se puede reconstruir
    después.

    **Los dos sistemas se resuelven distinto a propósito.** En macOS alcanza con
    encontrar el binario, porque la frontera está medida. En Linux no lo está, así
    que se corre una sonda: encontrar `unshare` no prueba que el espacio de
    nombres se pueda crear.
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

    if sistema == "Linux":
        return _frontera_linux(buscar, observar or observar_red)

    raise SinFrontera(
        "Frontera buscada: una que deniegue la red en el kernel para el sistema "
        "'%s'.\n"
        "Por qué no se consiguió: este ejecutor tiene escrita la de macOS "
        "(`sandbox-exec`, medida) y la de Linux (espacio de nombres de red, "
        "probada con sonda en cada uso). Para '%s' no hay ninguna, y darla por "
        "buena sin medirla sería exactamente lo que este módulo evita.\n"
        "Sin frontera de kernel no se ejecuta: el bloqueo de red dentro del "
        "proceso es evadible y está documentado arriba en este módulo."
        % (sistema, sistema)
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
