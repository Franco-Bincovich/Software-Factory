"""Criterio de aceptación del ejecutor aislado.

**Cada garantía se prueba intentando violarla.** Un test que ejecuta código
inofensivo y ve que no pasa nada no prueba que haya una frontera: prueba que
nadie la empujó. Así que el archivo que se ejecuta acá abre conexiones, escribe
afuera y no termina nunca, y lo que se afirma es que no lo consigue.

Los tests que ejecutan Node de verdad se saltean donde no hay frontera de kernel,
y **el salteo dice por qué**. No se degradan a una versión más floja: si en un
sistema no se puede comprobar la garantía, acá no queda un test verde que dé a
entender que sí.
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import ejecutor  # noqa: E402
from ejecutor import EntradaRechazada, SinFrontera  # noqa: E402


def _hay_frontera():
    try:
        ejecutor.frontera_de_red()
        return shutil.which("node") is not None
    except SinFrontera:
        return False


HAY_FRONTERA = _hay_frontera()
MOTIVO = "sin frontera de kernel o sin Node: la garantía no se puede comprobar acá"


class BaseEjecutor(unittest.TestCase):
    """Un directorio de unidad por test, y nada afuera que no sea nuestro."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name).resolve()
        self.unidad = self.raiz / "unidad"
        self.unidad.mkdir()
        self.afuera = self.raiz / "afuera"
        self.afuera.mkdir()
        self.ajeno = self.afuera / "ajeno.txt"
        self.ajeno.write_text("secreto de afuera\n", encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)

    def archivo(self, nombre, cuerpo):
        destino = self.unidad / nombre
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(textwrap.dedent(cuerpo), encoding="utf-8")
        return nombre


# --- 1 — sin red ------------------------------------------------------------


@unittest.skipUnless(HAY_FRONTERA, MOTIVO)
class SinRed(BaseEjecutor):
    """Probado por los tres caminos, incluido el que evadió el bloqueo en proceso."""

    def test_no_puede_abrir_una_conexion_tcp(self):
        self.archivo("u1.js", """
            const s = require("node:net").connect(53, "1.1.1.1");
            s.setTimeout(4000);
            s.on("connect", () => { console.log("CONECTO"); s.destroy(); });
            s.on("error", (e) => console.log("bloqueado", e.code));
            s.on("timeout", () => { console.log("timeout"); s.destroy(); });
        """)
        r = ejecutor.ejecutar_archivo(self.unidad, "u1.js")
        self.assertNotIn("CONECTO", r.salida)
        self.assertIn("bloqueado", r.salida)

    def test_no_puede_salir_por_import_dinamico(self):
        """La evasión que apareció en el primer intento del bloqueo en proceso.

        `import()` va por el cargador de ESM y no toca el parche de CommonJS. Es
        exactamente el test que un bloqueo en proceso no pasaría, y por el que
        este ejecutor exige una frontera de kernel.
        """
        self.archivo("u1.js", """
            import("node:net").then((net) => {
              const s = net.connect(53, "1.1.1.1");
              s.setTimeout(4000);
              s.on("connect", () => { console.log("CONECTO"); s.destroy(); });
              s.on("error", (e) => console.log("bloqueado", e.code));
              s.on("timeout", () => { console.log("timeout"); s.destroy(); });
            });
        """)
        r = ejecutor.ejecutar_archivo(self.unidad, "u1.js")
        self.assertNotIn("CONECTO", r.salida)
        self.assertIn("bloqueado", r.salida)

    def test_no_puede_usar_fetch(self):
        r = ejecutor.ejecutar_expresion(
            self.unidad,
            'fetch("https://example.com", { signal: AbortSignal.timeout(4000) })'
            '.then(r => console.log("SALIO", r.status))'
            '.catch(e => console.log("bloqueado"));',
        )
        self.assertNotIn("SALIO", r.salida)
        self.assertIn("bloqueado", r.salida)


# --- 2 — sin filesystem fuera del directorio de la unidad -------------------


@unittest.skipUnless(HAY_FRONTERA, MOTIVO)
class SinFilesystemAfuera(BaseEjecutor):

    def test_no_puede_leer_fuera_del_directorio(self):
        r = ejecutor.ejecutar_expresion(
            self.unidad,
            'const fs=require("node:fs");'
            'try{console.log("LEIDO",fs.readFileSync(%s,"utf8"))}'
            'catch(e){console.log("bloqueado",e.code)}' % repr(str(self.ajeno)),
        )
        self.assertNotIn("LEIDO", r.salida)
        self.assertIn("ERR_ACCESS_DENIED", r.salida)

    def test_no_puede_escribir_fuera_del_directorio(self):
        plantado = self.afuera / "plantado.txt"
        r = ejecutor.ejecutar_expresion(
            self.unidad,
            'const fs=require("node:fs");'
            'try{fs.writeFileSync(%s,"x");console.log("ESCRIBIO")}'
            'catch(e){console.log("bloqueado",e.code)}' % repr(str(plantado)),
        )
        self.assertNotIn("ESCRIBIO", r.salida)
        self.assertIn("ERR_ACCESS_DENIED", r.salida)
        self.assertFalse(plantado.exists(), "el archivo de afuera se creó igual")

    def test_no_puede_salir_por_puntos_puntos(self):
        r = ejecutor.ejecutar_expresion(
            self.unidad,
            'const fs=require("node:fs");'
            'try{console.log("LEIDO",fs.readFileSync("../afuera/ajeno.txt","utf8"))}'
            'catch(e){console.log("bloqueado",e.code)}',
        )
        self.assertNotIn("LEIDO", r.salida)
        self.assertIn("ERR_ACCESS_DENIED", r.salida)

    def test_no_puede_fabricarse_un_symlink_para_salir(self):
        """El agujero del symlink, cerrado del lado de adentro.

        `revisar_entrada` cubre el symlink que ya está en el depósito. Éste cubre
        el otro extremo: que el código no pueda crearse uno mientras corre.
        """
        atajo = self.unidad / "atajo"
        r = ejecutor.ejecutar_expresion(
            self.unidad,
            'const fs=require("node:fs");'
            'try{fs.symlinkSync(%s,%s);console.log("CREO EL SYMLINK")}'
            'catch(e){console.log("bloqueado",e.code)}'
            % (repr(str(self.afuera)), repr(str(atajo))),
        )
        self.assertNotIn("CREO EL SYMLINK", r.salida)
        self.assertIn("ERR_ACCESS_DENIED", r.salida)
        self.assertFalse(atajo.exists())

    def test_si_puede_leer_y_escribir_dentro_de_su_directorio(self):
        """La frontera tiene que dejar trabajar: si no, el falso negativo es total."""
        self.archivo("dato.txt", "propio\n")
        r = ejecutor.ejecutar_expresion(
            self.unidad,
            'const fs=require("node:fs");'
            'console.log("leyo:",fs.readFileSync("dato.txt","utf8").trim());'
            'fs.writeFileSync("salida.txt","ok");'
            'console.log("escribio");',
        )
        self.assertEqual(r.codigo, 0, r.error)
        self.assertIn("leyo: propio", r.salida)
        self.assertIn("escribio", r.salida)
        self.assertEqual((self.unidad / "salida.txt").read_text(encoding="utf-8"), "ok")


# --- 3 — no se cuelga indefinidamente ---------------------------------------


@unittest.skipUnless(HAY_FRONTERA, MOTIVO)
class CortePorTiempo(BaseEjecutor):

    def test_el_que_no_termina_nunca_se_corta(self):
        self.archivo("u1.js", """
            console.log("arranque");
            setInterval(() => {}, 1000);
        """)
        inicio = time.monotonic()
        r = ejecutor.ejecutar_archivo(self.unidad, "u1.js", limite=1.5)
        self.assertTrue(r.cortado_por_tiempo)
        self.assertNotEqual(r.codigo, 0)
        self.assertLess(time.monotonic() - inicio, 12)

    def test_el_que_ignora_sigterm_se_corta_igual(self):
        """`SIGTERM` es una sugerencia; medido contra código que lo ignora."""
        self.archivo("u1.js", """
            process.on("SIGTERM", () => {});
            console.log("no me voy con SIGTERM");
            setInterval(() => {}, 1000);
        """)
        r = ejecutor.ejecutar_archivo(self.unidad, "u1.js", limite=1.0)
        self.assertTrue(r.cortado_por_tiempo)
        self.assertEqual(r.codigo, -9, "no terminó en SIGKILL")

    def test_el_corte_no_deja_procesos_huerfanos(self):
        marca = "huerfano-%d" % os.getpid()
        self.archivo("%s.js" % marca, """
            process.on("SIGTERM", () => {});
            setInterval(() => {}, 1000);
        """)
        ejecutor.ejecutar_archivo(self.unidad, "%s.js" % marca, limite=1.0)
        time.sleep(0.5)
        vivos = subprocess.run(
            ["pgrep", "-f", marca], capture_output=True, text=True
        ).stdout.split()
        self.assertEqual(vivos, [], "quedaron procesos vivos tras el corte")

    def test_el_que_termina_a_tiempo_no_se_marca_como_cortado(self):
        r = ejecutor.ejecutar_expresion(self.unidad, 'console.log("rapido")', limite=10)
        self.assertFalse(r.cortado_por_tiempo)
        self.assertEqual(r.codigo, 0)


# --- 4 — lo que devuelve ----------------------------------------------------


@unittest.skipUnless(HAY_FRONTERA, MOTIVO)
class LoQueDevuelve(BaseEjecutor):

    def test_devuelve_salida_error_y_codigo_de_retorno(self):
        self.archivo("u1.js", """
            console.log("por stdout");
            console.error("por stderr");
            process.exit(3);
        """)
        r = ejecutor.ejecutar_archivo(self.unidad, "u1.js")
        self.assertIn("por stdout", r.salida)
        self.assertIn("por stderr", r.error)
        self.assertEqual(r.codigo, 3)
        self.assertFalse(r.cortado_por_tiempo)

    def test_registra_bajo_que_frontera_corrio(self):
        """Dos corridas bajo fronteras distintas no son comparables."""
        r = ejecutor.ejecutar_expresion(self.unidad, 'console.log("x")')
        self.assertEqual(r.frontera, "sandbox-exec" if platform.system() == "Darwin" else r.frontera)
        self.assertTrue(r.frontera)

    def test_no_le_pasa_el_entorno_del_proceso_padre(self):
        """Ni el modelo de permisos ni el sandbox tapan `process.env`.

        El padre tiene la `ANTHROPIC_API_KEY` cargada por `load_dotenv`, así que
        heredar el entorno sería entregársela al código que se está verificando.
        """
        os.environ["SECRETO_DE_PRUEBA"] = "no-se-tiene-que-ver"
        self.addCleanup(os.environ.pop, "SECRETO_DE_PRUEBA", None)
        r = ejecutor.ejecutar_expresion(
            self.unidad, 'console.log("visto:", process.env.SECRETO_DE_PRUEBA)'
        )
        self.assertIn("visto: undefined", r.salida)
        self.assertNotIn("no-se-tiene-que-ver", r.salida)


# --- 5 — la entrada que no debería haber llegado ----------------------------


class EntradaQueNoDeberiaHaberLlegado(BaseEjecutor):
    """El depósito ya pasó por V5. El ejecutor no lo asume: comprueba otra vez.

    No necesitan frontera de kernel: rechazan **antes** de ejecutar, que es
    precisamente lo que se está probando.
    """

    def test_rechaza_un_symlink_en_el_directorio(self):
        """El único agujero medido del modelo de permisos de Node.

        No es de V5 y no puede serlo: V5 corre sobre la Entrega, que es texto, y
        un symlink no tiene cómo escribirse ahí.
        """
        self.archivo("u1.js", 'console.log("hola");')
        (self.unidad / "atajo").symlink_to(self.afuera)
        with self.assertRaises(EntradaRechazada) as caso:
            ejecutor.revisar_entrada(self.unidad, "u1.js")
        self.assertIn("atajo", str(caso.exception))
        self.assertIn("enlace simbólico", str(caso.exception))

    def test_rechaza_un_manifiesto_de_dependencias(self):
        self.archivo("u1.js", 'console.log("hola");')
        self.archivo("package.json", '{"dependencies":{"left-pad":"1.0.0"}}')
        with self.assertRaises(EntradaRechazada) as caso:
            ejecutor.revisar_entrada(self.unidad, "u1.js")
        self.assertIn("package.json", str(caso.exception))

    def test_rechaza_un_paquete_externo_pedido_por_require(self):
        self.archivo("u1.js", 'const x = require("left-pad"); console.log(x);')
        with self.assertRaises(EntradaRechazada) as caso:
            ejecutor.revisar_entrada(self.unidad, "u1.js")
        self.assertIn("left-pad", str(caso.exception))

    def test_rechaza_una_dependencia_ya_instalada(self):
        self.archivo("u1.js", 'console.log("hola");')
        self.archivo("node_modules/left-pad/index.js", "module.exports = 1;")
        with self.assertRaises(EntradaRechazada) as caso:
            ejecutor.revisar_entrada(self.unidad, "u1.js")
        self.assertIn("node_modules", str(caso.exception))

    def test_rechaza_un_binario(self):
        self.archivo("u1.js", 'console.log("hola");')
        (self.unidad / "addon.node").write_bytes(b"\x7fELF\x00\xff binario")
        with self.assertRaises(EntradaRechazada) as caso:
            ejecutor.revisar_entrada(self.unidad, "u1.js")
        self.assertIn("addon.node", str(caso.exception))

    def test_rechaza_un_archivo_de_fuera_del_directorio(self):
        self.archivo("u1.js", 'console.log("hola");')
        with self.assertRaises(EntradaRechazada) as caso:
            ejecutor.revisar_entrada(self.unidad, "../afuera/ajeno.txt")
        self.assertIn("fuera del directorio", str(caso.exception))

    def test_no_ejecuta_nada_de_lo_que_rechaza(self):
        """El rechazo es previo, como manda ADR-016 punto 2.

        Si el archivo llegara a correr, dejaría su rastro en disco. Que no esté
        es lo que prueba que no se intentó y se vio qué pasaba.
        """
        self.archivo("u1.js", """
            require("node:fs").writeFileSync("corri.txt", "corri");
        """)
        self.archivo("package.json", "{}")
        with self.assertRaises(EntradaRechazada):
            ejecutor.ejecutar_archivo(self.unidad, "u1.js")
        self.assertFalse((self.unidad / "corri.txt").exists())

    def test_la_entrega_limpia_no_se_rechaza(self):
        """Un falso positivo acá invalida el ejecutor igual que un falso negativo."""
        self.archivo("src/u1.js", 'module.exports = () => 1;')
        self.archivo("tests/u1.test.js", """
            const test = require("node:test");
            const assert = require("node:assert");
            const u1 = require("../src/u1.js");
            test("anda", () => assert.equal(u1(), 1));
        """)
        self.archivo("pruebas.html", '<script src="src/u1.js"></script>')
        destino = ejecutor.revisar_entrada(self.unidad, "src/u1.js")
        self.assertEqual(destino, self.unidad / "src" / "u1.js")


# --- 6 — la negativa a ejecutar sin frontera --------------------------------


class NegativaSinFrontera(unittest.TestCase):
    """Sin frontera de kernel no se ejecuta, y el mensaje dice qué faltó."""

    def test_en_macos_sin_sandbox_exec_se_niega_y_lo_nombra(self):
        with self.assertRaises(SinFrontera) as caso:
            ejecutor.frontera_de_red(sistema="Darwin", buscar=lambda _: None)
        mensaje = str(caso.exception)
        self.assertIn("sandbox-exec", mensaje)
        self.assertIn("no hay `sandbox-exec` en el PATH", mensaje)

    def test_en_un_sistema_sin_frontera_escrita_se_niega(self):
        with self.assertRaises(SinFrontera) as caso:
            ejecutor.frontera_de_red(sistema="Windows")
        mensaje = str(caso.exception)
        self.assertIn("Frontera buscada", mensaje)
        self.assertIn("Por qué no se consiguió", mensaje)
        self.assertIn("Windows", mensaje)

    def test_el_mensaje_dice_por_que_no_se_degrada_al_bloqueo_en_proceso(self):
        """Sin esto, el siguiente que lo lea lo "arregla" bloqueando en proceso."""
        for sistema in ("Linux", "Windows"):
            with self.assertRaises(SinFrontera) as caso:
                ejecutor.frontera_de_red(sistema=sistema, buscar=lambda _: None)
            self.assertIn("evadible", str(caso.exception))

    def test_en_macos_con_sandbox_exec_devuelve_el_prefijo_con_el_perfil(self):
        nombre, prefijo = ejecutor.frontera_de_red(
            sistema="Darwin", buscar=lambda _: "/usr/bin/sandbox-exec"
        )
        self.assertEqual(nombre, "sandbox-exec")
        self.assertEqual(prefijo, ["/usr/bin/sandbox-exec", "-p", ejecutor.PERFIL_SIN_RED])
        self.assertIn("deny network*", ejecutor.PERFIL_SIN_RED)

    def test_sin_node_no_hay_nada_que_ejecutar(self):
        with self.assertRaises(SinFrontera) as caso:
            ejecutor._binario_de_node(buscar=lambda _: None)
        self.assertIn("node", str(caso.exception))


# --- 7 — la sonda de Linux --------------------------------------------------


#: Las tres observaciones que la sonda puede devolver, como las devuelve
#: `observar_red`: `(interfaces, salida, crudo)`.
AFUERA = (2, "TIMEOUT", "INTERFACES=2 SALIDA=TIMEOUT")
AISLADO = (0, "ERROR:ENETUNREACH", "INTERFACES=0 SALIDA=ERROR:ENETUNREACH")
#: El caso contradictorio: adentro no hay interfaces y la conexión sale igual.
#: No debería poder pasar, y por eso mismo se comprueba: si pasa, lo que falla
#: es la sonda, y aceptarla sería tomar por frontera algo que no lo es.
SIN_AISLAR = (0, "CONECTO", "INTERFACES=0 SALIDA=CONECTO")
NO_CORRIO = (None, None, "código 1 — unshare: unshare failed: Operation not permitted")


def buscar_solo(*disponibles):
    """Un `shutil.which` de mentira: sólo encuentra lo que se le nombra."""
    return lambda nombre: "/usr/bin/%s" % nombre if nombre in disponibles else None


def sonda(control, *respuestas):
    """Un `observar_red` de mentira.

    Sin prefijo devuelve `control`; con prefijo va devolviendo `respuestas` en
    el orden en que se prueban los candidatos.
    """
    pendientes = list(respuestas)
    return lambda prefijo: control if not prefijo else pendientes.pop(0)


class SondaDeLinux(unittest.TestCase):
    """En Linux la frontera se comprueba, no se deduce de encontrar el binario.

    Esta rama se escribió sin poder correr Linux ni una vez, así que lo único
    honesto que se puede afirmar hoy es cómo decide el módulo, no que el
    espacio de nombres se cree. Lo segundo lo mide
    `verificar_frontera_linux.py` en la máquina real.
    """

    def test_encontrar_unshare_no_alcanza_si_la_sonda_no_lo_confirma(self):
        """El corazón de la rama: `which` no es prueba de nada en Linux."""
        with self.assertRaises(SinFrontera):
            ejecutor.frontera_de_red(
                sistema="Linux",
                buscar=buscar_solo("unshare"),
                observar=sonda(AFUERA, NO_CORRIO, NO_CORRIO),
            )

    def test_cuando_la_sonda_confirma_devuelve_el_prefijo(self):
        nombre, prefijo = ejecutor.frontera_de_red(
            sistema="Linux",
            buscar=buscar_solo("unshare"),
            observar=sonda(AFUERA, AISLADO),
        )
        self.assertEqual(nombre, "unshare-netns")
        self.assertEqual(prefijo, ["/usr/bin/unshare", "--user", "--map-current-user", "--net", "--"])

    def test_si_el_primer_candidato_falla_prueba_el_siguiente(self):
        """`--map-current-user` es de util-linux 2.38; en 22.04 hay que caer al otro."""
        nombre, _ = ejecutor.frontera_de_red(
            sistema="Linux",
            buscar=buscar_solo("unshare"),
            observar=sonda(AFUERA, NO_CORRIO, AISLADO),
        )
        self.assertEqual(nombre, "unshare-netns-root")

    def test_no_acepta_una_frontera_que_igual_deja_conectar(self):
        with self.assertRaises(SinFrontera) as caso:
            ejecutor.frontera_de_red(
                sistema="Linux",
                buscar=buscar_solo("bwrap"),
                observar=sonda(AFUERA, SIN_AISLAR),
            )
        self.assertIn("la conexión saliente igual se estableció", str(caso.exception))

    def test_no_acepta_una_frontera_donde_siguen_viendose_interfaces(self):
        with self.assertRaises(SinFrontera) as caso:
            ejecutor.frontera_de_red(
                sistema="Linux",
                buscar=buscar_solo("bwrap"),
                observar=sonda(AFUERA, (2, "TIMEOUT", "INTERFACES=2 SALIDA=TIMEOUT")),
            )
        self.assertIn("No aisló nada", str(caso.exception))

    def test_en_una_maquina_sin_red_no_afirma_la_frontera(self):
        """El control de la sonda, que es el que evita el falso verde.

        Sin él, una máquina con el cable desenchufado haría pasar cualquier
        frontera —incluso una que no existe—, porque adentro y afuera se verían
        igual.
        """
        desconectada = (0, "ERROR:ENETUNREACH", "INTERFACES=0 SALIDA=ERROR:ENETUNREACH")
        with self.assertRaises(SinFrontera) as caso:
            ejecutor.frontera_de_red(
                sistema="Linux",
                buscar=buscar_solo("unshare"),
                observar=sonda(desconectada, AISLADO, AISLADO),
            )
        self.assertIn("máquina desconectada", str(caso.exception))

    def test_si_el_control_no_corre_tampoco_afirma_nada(self):
        with self.assertRaises(SinFrontera) as caso:
            ejecutor.frontera_de_red(
                sistema="Linux",
                buscar=buscar_solo("unshare"),
                observar=sonda(NO_CORRIO, AISLADO, AISLADO),
            )
        self.assertIn("no hay contra qué comparar", str(caso.exception))

    def test_sin_candidatos_no_corre_ninguna_sonda(self):
        """Ni la de control: no hay nada contra qué compararla."""
        def explotar(_):
            self.fail("corrió una sonda sin tener ningún candidato que probar")

        with self.assertRaises(SinFrontera) as caso:
            ejecutor.frontera_de_red(
                sistema="Linux", buscar=lambda _: None, observar=explotar
            )
        mensaje = str(caso.exception)
        self.assertIn("no está `unshare` en el PATH", mensaje)
        self.assertIn("no está `bwrap` en el PATH", mensaje)


class ElMensajeDeLinuxAlcanzaParaArreglarlo(unittest.TestCase):
    """Mañana en la mini PC, el mensaje tiene que bastar sin releer el módulo.

    Que la sonda corrió, con qué candidato, y con qué murió. Un "no hay
    frontera" a secas manda a reconstruir desde cero lo que la máquina ya
    contestó.
    """

    def mensaje(self):
        with self.assertRaises(SinFrontera) as caso:
            ejecutor.frontera_de_red(
                sistema="Linux",
                buscar=buscar_solo("unshare"),
                observar=sonda(AFUERA, NO_CORRIO, NO_CORRIO),
            )
        return str(caso.exception)

    def test_dice_que_se_probo_y_con_que_murio(self):
        mensaje = self.mensaje()
        self.assertIn("Se probó cada candidato con una sonda real", mensaje)
        self.assertIn("unshare-netns", mensaje, "no dice qué candidato se probó")
        self.assertIn("Operation not permitted", mensaje, "no dice con qué murió")

    def test_nombra_el_sysctl_de_apparmor_que_es_la_causa_mas_probable(self):
        """Es el motivo número uno en un Ubuntu 24.04 de fábrica."""
        self.assertIn("kernel.apparmor_restrict_unprivileged_userns", self.mensaje())

    def test_deja_la_observacion_de_control_a_la_vista(self):
        self.assertIn("INTERFACES=2", self.mensaje())

    def test_avisa_que_nadie_vio_funcionar_esta_rama(self):
        mensaje = self.mensaje()
        self.assertIn(ejecutor.LINUX_ESCRITA_SIN_MEDIR, mensaje)
        self.assertIn("nadie la vio funcionar", mensaje)

    def test_manda_a_leer_por_que_seccomp_no_es_la_salida_obvia(self):
        """Sin esto, el que lo lea mañana lo ve como lo que alguien no hizo."""
        self.assertIn("seccomp", self.mensaje())
        self.assertIn("descartado con motivo", self.mensaje())


if __name__ == "__main__":
    unittest.main()
