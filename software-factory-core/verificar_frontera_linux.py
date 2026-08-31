#!/usr/bin/env python3
"""¿Existe la frontera de red en esta máquina? Una pasada, un veredicto.

Se corre en la mini PC el día que la Fábrica llegue a Linux, **antes** de
confiar en `ejecutor.py`:

    python3 verificar_frontera_linux.py

No necesita venv, ni `pip install`, ni la suite. Sólo Python 3.8+ de sistema y
`node`. Si le falta algo lo dice al arrancar, con el comando para conseguirlo,
en vez de morirse a mitad de camino.

## Por qué importa a quién le pregunta

Este script **importa `src/ejecutor.py` y le pide la frontera al mismo código
que la va a usar en producción**. No reimplementa `unshare` por su cuenta: una
reimplementación que anduviera probaría que anda la reimplementación, y de
`ejecutor.frontera_de_red` no diría nada. Si el que anda es el módulo, el que
tiene que contestar es el módulo.

## Por qué hay controles de mutación

Los tres tests de red afirman que el entregable **no pudo** salir. Un test así
pasa por dos motivos bien distintos: porque la frontera lo frenó, o porque no
había adónde ir. Una máquina sin internet los pone a los tres en verde con
frontera y sin frontera, y ahí "no pudo salir" no dice nada de la frontera.

Por eso cada test corre **dos veces**: con frontera y sin ella. La corrida sin
frontera es el control de mutación —si el test no cambia de resultado cuando le
sacás lo único que estaba probando, el test no está midiendo eso—. La frontera
se declara confirmada sólo si los tres frenan con ella y los tres salen sin
ella. Si los tres frenan siempre, el veredicto es INCONCLUSO, no PASA.
"""

import platform
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# --- Los tres tests, idénticos a los de `tests/test_ejecutor.py::SinRed` -----
#
# Idénticos a propósito: si acá se aflojaran, mañana la mini PC daría un verde
# que la suite no da. Cada uno imprime `CONECTO` si llegó a la red y `bloqueado`
# si no, que es el par de marcas que se mira más abajo.

JS_TCP = """const s = require("node:net").connect(53, "1.1.1.1");
s.setTimeout(4000);
s.on("connect", () => { console.log("CONECTO"); s.destroy(); });
s.on("error", (e) => console.log("bloqueado", e.code));
s.on("timeout", () => { console.log("timeout"); s.destroy(); });
"""

# La evasión que rompió el bloqueo en proceso: `import()` va por el cargador de
# ESM y no toca el parche de CommonJS. Es el test por el que existe la frontera
# de kernel, así que es el que menos se puede omitir.
JS_IMPORT = """import("node:net").then((net) => {
  const s = net.connect(53, "1.1.1.1");
  s.setTimeout(4000);
  s.on("connect", () => { console.log("CONECTO"); s.destroy(); });
  s.on("error", (e) => console.log("bloqueado", e.code));
  s.on("timeout", () => { console.log("timeout"); s.destroy(); });
});
"""

JS_FETCH = (
    'fetch("https://example.com", { signal: AbortSignal.timeout(4000) })'
    '.then(r => console.log("CONECTO", r.status))'
    '.catch(e => console.log("bloqueado", e.name));'
)

CASOS = (
    ("tcp", "conexión TCP con `node:net`", JS_TCP, "archivo"),
    ("import", "`import()` dinámico (la evasión del bloqueo en proceso)", JS_IMPORT, "archivo"),
    ("fetch", "`fetch` global", JS_FETCH, "expresion"),
)


def titulo(texto):
    print()
    print(texto)
    print("-" * len(texto))


# --- Precondiciones ---------------------------------------------------------


def precondiciones():
    """Todo lo que hace falta, comprobado antes de tocar nada.

    Se comprueba junto y se informa junto: que falten dos cosas y enterarse de a
    una es dos viajes a la máquina. Devuelve `(ejecutor, es_linux)` o corta.
    """
    titulo("Precondiciones")
    faltas = []

    print("  python3            %s" % platform.python_version())
    if sys.version_info < (3, 8):
        faltas.append(
            "Python 3.8 o mayor (hay %s). En Ubuntu: `apt install python3`."
            % platform.python_version()
        )

    sistema = platform.system()
    es_linux = sistema == "Linux"
    print("  sistema            %s (%s)" % (sistema, platform.release()))
    if not es_linux:
        print()
        print("  AVISO: esto no es Linux. El script corre igual y prueba la")
        print("  frontera que este sistema tenga, lo cual sirve para saber que el")
        print("  script no está roto — pero NO dice nada de la frontera de Linux.")

    modulo = RAIZ / "src" / "ejecutor.py"
    print("  src/ejecutor.py    %s" % ("está" if modulo.is_file() else "NO ESTÁ"))
    if not modulo.is_file():
        faltas.append(
            "`src/ejecutor.py` al lado de este script. Se esperaba en %s; "
            "correlo desde el repo, no desde una copia suelta." % modulo
        )

    node = _buscar_node()
    print("  node               %s" % (node or "NO ESTÁ EN EL PATH"))
    if node is None:
        faltas.append(
            "`node` en el PATH. La frontera de ADR-016 es JavaScript sobre Node. "
            "En Ubuntu: `apt install nodejs`."
        )

    if faltas:
        print()
        print("FALTA:")
        for f in faltas:
            print("  - %s" % f)
        print()
        print("VEREDICTO: no se pudo comprobar nada. Conseguí lo de arriba y volvé.")
        return None, es_linux

    sys.path.insert(0, str(RAIZ / "src"))
    import ejecutor  # noqa: E402

    print("  ejecutor           importado sin venv")
    return ejecutor, es_linux


def _buscar_node():
    """`shutil.which`, pero sin importar `ejecutor` todavía."""
    import shutil

    return shutil.which("node")


# --- Correr un caso, con frontera y sin ella --------------------------------


def _con_frontera(ejecutor, unidad, cuerpo, modo):
    if modo == "expresion":
        return ejecutor.ejecutar_expresion(unidad, cuerpo).salida
    (unidad / "caso.js").write_text(cuerpo, encoding="utf-8")
    return ejecutor.ejecutar_archivo(unidad, "caso.js").salida


def _sin_frontera(ejecutor, unidad, cuerpo, modo):
    """El mismo Node, los mismos permisos, **sin el prefijo de la frontera**.

    Es el control de mutación: le saca a la ejecución exactamente lo único que
    los tests dicen estar midiendo, y nada más. Si el resultado no cambia, los
    tests no estaban midiendo eso.
    """
    raiz = str(Path(unidad).resolve())
    argv = [
        ejecutor._binario_de_node(),
        "--permission",
        "--allow-fs-read=%s" % raiz,
        "--allow-fs-write=%s" % raiz,
    ]
    if modo == "expresion":
        argv += ["-e", cuerpo]
    else:
        # La ruta va resuelta, igual que la que arma `ejecutar_archivo`. Sin
        # esto, en macOS `/var/...` contra un permiso dado sobre
        # `/private/var/...` muere con `ERR_ACCESS_DENIED` y el control parece
        # una máquina sin red cuando es un error de ruta.
        destino = Path(raiz) / "caso.js"
        destino.write_text(cuerpo, encoding="utf-8")
        argv += [str(destino)]

    try:
        p = subprocess.run(
            argv,
            cwd=raiz,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=ejecutor.LIMITE_SEGUNDOS,
            env=dict(ejecutor.ENTORNO_MINIMO),
        )
    except subprocess.TimeoutExpired:
        return "(el control no terminó a tiempo)"
    return p.stdout or (p.stderr or "").strip()


def _resumen(salida):
    return " ".join((salida or "(sin salida)").split())[:90]


def _llego_a_correr(salida):
    """¿El caso llegó a intentar la red, o murió antes?

    Un control que no corrió y un control que corrió y no alcanzó la red se ven
    igual desde afuera —ninguno imprime `CONECTO`— y se arreglan distinto. Las
    marcas del propio caso son lo que los separa: si no está ninguna, el proceso
    no llegó a ejecutar el JavaScript.
    """
    texto = salida or ""
    return any(m in texto for m in ("CONECTO", "bloqueado", "timeout"))


# --- El veredicto -----------------------------------------------------------


def main():
    ejecutor, es_linux = precondiciones()
    if ejecutor is None:
        return 2

    titulo("Frontera")
    try:
        nombre, prefijo = ejecutor.frontera_de_red()
    except ejecutor.SinFrontera as e:
        print("  `frontera_de_red()` se negó. El módulo dice esto:")
        print()
        for linea in str(e).splitlines():
            print("    %s" % linea)
        print()
        print("VEREDICTO: NO HAY FRONTERA. El ejecutor no va a correr nada en esta")
        print("máquina, que es lo correcto. Arriba está qué mirar y en qué orden.")
        return 1

    print("  `frontera_de_red()` devolvió: %s" % nombre)
    print("  prefijo: %s" % " ".join(prefijo))
    if es_linux:
        print()
        print("  En Linux ese valor sale de la sonda, que ya vio que adentro no hay")
        print("  interfaces. Lo que sigue es la comprobación independiente, por los")
        print("  tres caminos reales.")
    else:
        print()
        print("  En este sistema no hay sonda: el prefijo salió de encontrar el")
        print("  binario, porque la frontera de macOS ya está medida.")

    titulo("Los tres tests, con frontera y sin ella")
    frenados = []
    controles = []
    rotos = []
    with tempfile.TemporaryDirectory() as tmp:
        unidad = Path(tmp) / "unidad"
        for clave, descripcion, cuerpo, modo in CASOS:
            unidad.mkdir(exist_ok=True)
            con = _con_frontera(ejecutor, unidad, cuerpo, modo)
            freno = "CONECTO" not in con
            frenados.append(freno)
            if not _llego_a_correr(con):
                rotos.append((clave, "con frontera"))

            for hijo in unidad.iterdir():
                hijo.unlink()
            sin = _sin_frontera(ejecutor, unidad, cuerpo, modo)
            salio = "CONECTO" in sin
            controles.append(salio)
            if not _llego_a_correr(sin):
                rotos.append((clave, "el control"))

            print("  %-8s %s" % (clave, descripcion))
            print("      con frontera  %-9s  %s" % (
                "FRENÓ" if freno else "SALIÓ", _resumen(con)))
            print("      control       %-9s  %s" % (
                "SALIÓ" if salio else "no salió", _resumen(sin)))
            for hijo in unidad.iterdir():
                hijo.unlink()

    titulo("Veredicto")
    if rotos:
        print("  INCONCLUSO. Estos ni siquiera llegaron a intentar la conexión:")
        for clave, cual in rotos:
            print("    - %s, %s" % (clave, cual))
        print()
        print("  No imprimieron ninguna de sus propias marcas, así que Node murió")
        print("  antes de ejecutar el JavaScript. Mirá la salida de arriba: no es un")
        print("  problema de red, es que el caso no corrió. Mientras siga así, el")
        print("  resto de esta pasada no mide la frontera.")
        return 3

    if not all(frenados):
        cuales = [c[0] for c, f in zip(CASOS, frenados) if not f]
        print("  LA FRONTERA NO EXISTE. Con `%s` puesto, estos salieron igual a la" % nombre)
        print("  red: %s." % ", ".join(cuales))
        print()
        print("  No usar este candidato. `ejecutor.py` lo aceptó porque la sonda no")
        print("  vio interfaces adentro, así que la sonda se está quedando corta:")
        print("  hay que endurecerla antes de tocar cualquier otra cosa.")
        return 1

    if not all(controles):
        cuales = [c[0] for c, s in zip(CASOS, controles) if not s]
        print("  INCONCLUSO. Los tres frenaron con frontera, pero sin frontera")
        print("  tampoco salieron: %s." % ", ".join(cuales))
        print()
        print("  Eso quiere decir que esta máquina no llega a la red ni sin la")
        print("  frontera puesta, así que los tests no pueden distinguir el")
        print("  aislamiento del cable desenchufado. El verde de arriba no prueba")
        print("  nada. Conseguí internet en esta máquina y volvé a correr esto.")
        return 3

    print("  FRONTERA CONFIRMADA con `%s`." % nombre)
    print("  Los tres caminos frenaron con ella y los tres salieron sin ella, así")
    print("  que lo que los frenó fue la frontera y no la falta de red.")
    if es_linux:
        print()
        print("  Esto es la primera medición de la rama de Linux, escrita el %s"
              % ejecutor.LINUX_ESCRITA_SIN_MEDIR)
        print("  sin poder correrse. Anotá la fecha de hoy y el candidato en el")
        print("  docstring de `src/ejecutor.py`: ya no es una rama que nadie vio")
        print("  funcionar, y el módulo tiene que dejar de decir que lo es.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
