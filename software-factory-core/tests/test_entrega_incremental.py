"""Criterio de aceptación de la entrega incremental — ADR-019.

Cuatro cosas, que son las cuatro que el ADR pone a andar:

1. **La parte N ve lo que dejó la N-1 y no lo duplica.** Que lo vea lo cubre
   `PaqueteSuficiente` en `test_cadena.py`; acá se cubre lo otro, que es lo que
   ADR-019 midió cuatro veces sobre el registro: que copiarlo se rechace.
2. **La suite de las partes firmadas corre en cada paso y falla ruidosamente.**
3. **Corregir toca la parte nueva y no la aprobada.**
4. **El escalamiento del punto 6**: una parte que no se puede hacer sin reabrir
   lo firmado termina en una decisión de una persona, no en un pisado.

La parte mecánica de C10 —las dos ramas, la excepción de los agregadores— vive en
`test_verificador_entrega.py`, donde vive la regla. Acá se comprueba lo que sólo
se ve con la cadena andando: que el rechazo llegue al bucle de corrección, que el
espacio quede como el registro dice y que la corrida escale.

El grueso del andamiaje —Operational State temporal, checkpointer, Vault de
prueba— sale de `test_cadena.BaseCadena`. Repetirlo acá sería mantener dos copias
de la misma cama de pruebas.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ))
# `tests/` también, para reusar la cama de pruebas de `test_cadena`: al correr
# con `unittest discover -s tests` ya está, pero no al correr un módulo suelto.
sys.path.insert(0, str(RAIZ / "tests"))

import cadena  # noqa: E402
import ejecutor  # noqa: E402
import regresion  # noqa: E402
from ejecutor import SinFrontera  # noqa: E402

from correr import producir_entrega_stub  # noqa: E402
from test_cadena import BaseCadena, TRES_UNIDADES  # noqa: E402

AGREGADORES = ("pruebas.html", "demo.html")


def _hay_frontera():
    try:
        ejecutor.frontera_de_red()
        return shutil.which("node") is not None
    except SinFrontera:
        return False


HAY_FRONTERA = _hay_frontera()
MOTIVO = "sin frontera de kernel o sin Node: la regresión no se puede correr acá"


# --- 1 — la parte N no vuelve a depositar lo que ya está ---------------------


def _developer_que_entrega_ajeno(unidad_id, ajena, propia, cola=""):
    """Entrega el archivo de otra parte en lugar del suyo. Es la forma medida.

    Las cuatro cadenas del registro tienen a U2 entregando como propio un archivo
    de U1: en `957795bd…` el enunciado era escribir las pruebas y U2 entregó el
    archivo de pruebas de U1. Se reemplaza el propio en vez de sumar uno más para
    que la entrega siga teniendo exactamente los cuatro entregables — si no, el
    rechazo podría venir de C5 y el test no diría nada sobre C10.

    Con `cola` vacía es la rama «mismo hash» —duplicar—; con `cola` es la rama
    «hash distinto» —pisar lo firmado—.

    El contenido sale del contexto de las unidades de las que depende, que es de
    donde un Developer real lo sacaría: el inventario del paquete viaja sin
    contenido a propósito.
    """

    def producir(unidad, contexto, entrega_anterior, incumplimientos, contexto_vault,
                 paquete=None):
        entrega = producir_entrega_stub(
            unidad, contexto, entrega_anterior, incumplimientos, contexto_vault, paquete
        )
        if unidad["id"] != unidad_id:
            return entrega
        original = next(
            a for c in contexto for a in c["entrega"]["archivos"] if a["ruta"] == ajena
        )
        copia = dict(original, contenido=original["contenido"] + cola)
        entrega["archivos"] = [
            a for a in entrega["archivos"] if a["ruta"] not in (propia, ajena)
        ] + [copia]
        return entrega

    return producir


def developer_que_copia(unidad_id, ajena, propia):
    return _developer_que_entrega_ajeno(unidad_id, ajena, propia)


def developer_que_pisa(unidad_id, ajena, propia):
    return _developer_que_entrega_ajeno(
        unidad_id, ajena, propia, cola="\n// lo reescribe la parte %s\n" % unidad_id
    )


class NoSeVuelveADepositarLoQueYaEsta(BaseCadena):
    """El hallazgo 1 de ADR-019, convertido en una regla que corta.

    Las cuatro cadenas del registro tienen a U2 depositando una copia byte a byte
    de un artefacto de U1. Acá esa entrega se produce a propósito y se comprueba
    que la cadena la rechaza en vez de depositarla.
    """

    def incumplimientos_de(self, run, unidad):
        run_developer = next(
            e["payload"]["run_developer"] for e in self.de_tipo(run, "unidad_lanzada")
            if e["payload"]["unidad"] == unidad
        )
        return [
            i
            for e in self.de_tipo(run_developer, "verificacion_ejecutada")
            for i in e["payload"]["incumplimientos"]
        ]

    def test_copiar_el_archivo_de_la_parte_anterior_se_rechaza(self):
        run, _, _ = self.correr_cadena(
            TRES_UNIDADES,
            developer=developer_que_copia("U2", "tests/u1.test.js", "tests/u2.test.js"),
        )
        incumplimientos = self.incumplimientos_de(run, "U2")
        self.assertTrue(incumplimientos)
        self.assertEqual({i["regla"] for i in incumplimientos}, {"C10"})
        self.assertEqual({i["archivo"] for i in incumplimientos}, {"tests/u1.test.js"})
        # Y el detalle dice que el trabajo ya está hecho, no que se rehaga.
        self.assertIn("mismo contenido", incumplimientos[0]["detalle"])
        self.assertIn("U1", incumplimientos[0]["detalle"])

    def test_la_copia_no_llega_al_espacio_ni_al_registro(self):
        """Rechazar en el verificador no alcanza si el archivo igual se depositó."""
        run, _, _ = self.correr_cadena(
            TRES_UNIDADES,
            developer=developer_que_copia("U2", "tests/u1.test.js", "tests/u2.test.js"),
        )
        entregadas = [e["payload"]["unidad"] for e in self.de_tipo(run, "unidad_entregada")]
        self.assertNotIn("U2", entregadas)

        # El espacio quedó con lo de U1 tal cual, sin una segunda copia de nada.
        directorio = self.ruta_de_trabajo(run)
        self.assertTrue((directorio / "tests" / "u1.test.js").is_file())
        self.assertFalse((directorio / "src" / "u2.js").exists())

    def test_una_cadena_normal_no_deposita_dos_veces_la_misma_ruta(self):
        """La contracara: sin nadie copiando a propósito, no hay una sola ruta repetida.

        Es la métrica que ADR-019 deja habilitada —dos artefactos con la misma
        ruta en la misma cadena pasan a ser una anomalía— medida sobre la salida
        que la fábrica produce hoy.
        """
        run, _, _ = self.correr_cadena(TRES_UNIDADES)

        veces = {}
        for evento in self.de_tipo(run, "unidad_entregada"):
            entrega = cadena.entrega_de(self.store, evento["payload"]["run_developer"])
            for archivo in entrega["archivos"]:
                veces.setdefault(archivo["ruta"], []).append(evento["payload"]["unidad"])

        repetidas = {r: u for r, u in veces.items() if len(u) > 1}
        # Los agregadores sí se repiten, y por diseño: los reescribe cada parte.
        self.assertEqual(sorted(repetidas), sorted(AGREGADORES))
        self.assertEqual(
            sorted(r for r in veces if r not in AGREGADORES),
            ["src/u1.js", "src/u2.js", "src/u3.js",
             "tests/u1.test.js", "tests/u2.test.js", "tests/u3.test.js"],
        )


# --- 2 — la suite de las partes firmadas ------------------------------------


class EjecutorFalso:
    """Devuelve un `Resultado` fijo por archivo y anota sobre qué directorio corrió."""

    def __init__(self, por_archivo):
        self.por_archivo = por_archivo
        self.corridas = []

    def __call__(self, directorio, archivo):
        self.corridas.append((str(directorio), archivo))
        respuesta = self.por_archivo[archivo]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def resultado(codigo=0, error="", cortado=False, segundos=0.1):
    return ejecutor.Resultado(
        salida="", error=error, codigo=codigo,
        cortado_por_tiempo=cortado, frontera="ninguna", segundos=segundos,
    )


INVENTARIO = [
    {"ruta": "src/u1.js", "rol": "artefacto_esperado", "parte": "U1"},
    {"ruta": "tests/u1.test.js", "rol": "artefacto_esperado", "parte": "U1"},
    {"ruta": "pruebas.html", "rol": "artefacto_esperado", "parte": "U1"},
    {"ruta": "tests/u3.test.js", "rol": "artefacto_esperado", "parte": "U3"},
]


class SuiteDeLasPartesFirmadas(unittest.TestCase):
    """ADR-019 punto 4: lo firmado sigue andando, y comprobarlo no cuesta un token."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.deposito = Path(self._dir.name) / "deposito"
        (self.deposito / "tests").mkdir(parents=True)
        (self.deposito / "tests" / "u1.test.js").write_text("//\n", encoding="utf-8")
        (self.deposito / "tests" / "u3.test.js").write_text("//\n", encoding="utf-8")
        self.addCleanup(self._dir.cleanup)

    def test_se_corren_las_pruebas_del_inventario_y_no_los_html_ni_la_logica(self):
        self.assertEqual(
            regresion.archivos_de_prueba(INVENTARIO),
            [
                {"ruta": "tests/u1.test.js", "parte": "U1"},
                {"ruta": "tests/u3.test.js", "parte": "U3"},
            ],
        )

    def test_la_primera_parte_no_tiene_nada_que_correr(self):
        falso = EjecutorFalso({})
        self.assertEqual(regresion.correr(str(self.deposito), [], falso), [])
        self.assertEqual(falso.corridas, [])

    def test_una_suite_que_pasa_no_reporta_nada(self):
        falso = EjecutorFalso(
            {"tests/u1.test.js": resultado(), "tests/u3.test.js": resultado()}
        )
        pruebas = regresion.archivos_de_prueba(INVENTARIO)
        self.assertEqual(regresion.correr(str(self.deposito), pruebas, falso), [])
        self.assertEqual([a for _, a in falso.corridas],
                         ["tests/u1.test.js", "tests/u3.test.js"])

    def test_la_suite_que_falla_nombra_a_quien_se_la_rompieron(self):
        """`REG-<parte>` nombra al dueño del test, que es lo que el Developer no sabe."""
        falso = EjecutorFalso({
            "tests/u1.test.js": resultado(codigo=1, error="AssertionError: 3 !== 4\n"),
            "tests/u3.test.js": resultado(),
        })
        pruebas = regresion.archivos_de_prueba(INVENTARIO)
        fallos = regresion.correr(str(self.deposito), pruebas, falso)

        self.assertEqual(len(fallos), 1)
        self.assertEqual(fallos[0]["regla"], "REG-U1")
        self.assertEqual(fallos[0]["archivo"], "tests/u1.test.js")
        # Ruidoso quiere decir que dice qué hacer, y lo que hay que hacer es no
        # tocar lo aprobado.
        self.assertIn("corregí lo tuyo, no lo suyo", fallos[0]["detalle"])
        self.assertIn("AssertionError: 3 !== 4", fallos[0]["detalle"])

    def test_una_suite_colgada_no_se_confunde_con_una_que_pasa(self):
        falso = EjecutorFalso({
            "tests/u1.test.js": resultado(cortado=True, segundos=30),
            "tests/u3.test.js": resultado(),
        })
        pruebas = regresion.archivos_de_prueba(INVENTARIO)
        (fallo,) = regresion.correr(str(self.deposito), pruebas, falso)
        self.assertEqual(fallo["regla"], "REG-U1")
        self.assertIn("no terminó en 30 segundos", fallo["detalle"])

    def test_un_espacio_que_el_ejecutor_rechaza_no_pasa_por_defecto(self):
        falso = EjecutorFalso({
            "tests/u1.test.js": ejecutor.EntradaRechazada("hay un binario adentro"),
            "tests/u3.test.js": resultado(),
        })
        pruebas = regresion.archivos_de_prueba(INVENTARIO)
        (fallo,) = regresion.correr(str(self.deposito), pruebas, falso)
        self.assertEqual(fallo["regla"], "REG-U1")
        self.assertIn("hay un binario adentro", fallo["detalle"])

    def test_no_se_corre_sobre_el_deposito_sino_sobre_una_copia(self):
        """El depósito es el registro de auditoría de ADR-017 y tiene hash fijado."""
        def escribe(directorio, archivo):
            (Path(directorio) / "basura.txt").write_text("x", encoding="utf-8")
            return resultado()

        pruebas = regresion.archivos_de_prueba(INVENTARIO)
        self.assertEqual(regresion.correr(str(self.deposito), pruebas, escribe), [])
        self.assertFalse((self.deposito / "basura.txt").exists())


@unittest.skipUnless(HAY_FRONTERA, MOTIVO)
class SuiteFirmadaContraNodeDeVerdad(unittest.TestCase):
    """Lo mismo con Node, que es lo que decide si el mecanismo sirve.

    Los casos con ejecutor falso demuestran que la regresión reporta lo que se le
    dice; éste demuestra que un test que deja de pasar efectivamente se nota.
    """

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.espacio = Path(self._dir.name) / "espacio"
        (self.espacio / "src").mkdir(parents=True)
        (self.espacio / "tests").mkdir(parents=True)
        (self.espacio / "tests" / "u1.test.js").write_text(
            'const assert = require("node:assert");\n'
            'const { resolverU1 } = require("../src/u1.js");\n'
            'assert.strictEqual(resolverU1("dato").ok, true);\n',
            encoding="utf-8",
        )
        self.addCleanup(self._dir.cleanup)
        self.pruebas = [{"ruta": "tests/u1.test.js", "parte": "U1"}]

    def logica(self, cuerpo):
        (self.espacio / "src" / "u1.js").write_text(cuerpo, encoding="utf-8")

    def test_lo_firmado_que_sigue_andando_no_reporta_nada(self):
        self.logica(
            "function resolverU1(v) { return { ok: v.length > 0 }; }\n"
            "module.exports = { resolverU1 };\n"
        )
        self.assertEqual(regresion.correr(str(self.espacio), self.pruebas), [])

    def test_una_parte_que_rompe_lo_firmado_falla_ruidosamente(self):
        self.logica(
            "function resolverU1(v) { return { ok: false }; }\n"
            "module.exports = { resolverU1 };\n"
        )
        (fallo,) = regresion.correr(str(self.espacio), self.pruebas)
        self.assertEqual(fallo["regla"], "REG-U1")
        self.assertIn("estaba aprobada, falla con esta entrega", fallo["detalle"])


# --- 3 y 4 — corregir toca lo nuevo, y si no se puede, escala ---------------


class LoFirmadoNoSeReabre(BaseCadena):
    """ADR-019 puntos 5 y 6: el alcance de la corrección, y la salida cuando no alcanza."""

    def commit_de(self, run, unidad):
        return next(
            e["payload"]["commit"] for e in self.de_tipo(run, "parte_firmada")
            if e["payload"]["unidad"] == unidad
        )

    def contenido_firmado(self, run, unidad, ruta):
        run_developer = next(
            e["payload"]["run_developer"] for e in self.de_tipo(run, "unidad_entregada")
            if e["payload"]["unidad"] == unidad
        )
        entrega = cadena.entrega_de(self.store, run_developer)
        return next(a["contenido"] for a in entrega["archivos"] if a["ruta"] == ruta)

    def test_pisar_un_archivo_firmado_se_rechaza_y_dice_a_donde_ir(self):
        run, _, _ = self.correr_cadena(
            TRES_UNIDADES,
            developer=developer_que_pisa("U2", "tests/u1.test.js", "tests/u2.test.js"),
        )
        run_developer = next(
            e["payload"]["run_developer"] for e in self.de_tipo(run, "unidad_lanzada")
            if e["payload"]["unidad"] == "U2"
        )
        detalles = [
            i["detalle"]
            for e in self.de_tipo(run_developer, "verificacion_ejecutada")
            for i in e["payload"]["incumplimientos"]
        ]
        self.assertTrue(detalles)
        # No es "sacá el archivo": es "replanteá o escalá". Son correcciones
        # distintas y el detalle tiene que distinguirlas.
        self.assertIn("no se reabre", detalles[0])
        self.assertIn("escale", detalles[0])
        self.assertNotIn("mismo contenido", detalles[0])

    def test_el_espacio_queda_en_la_ultima_parte_firmada(self):
        """La parte rechazada no dejó nada: el punto de retorno sigue siendo un punto."""
        run, _, _ = self.correr_cadena(
            TRES_UNIDADES,
            developer=developer_que_pisa("U2", "tests/u1.test.js", "tests/u2.test.js"),
        )
        firmadas = [e["payload"]["unidad"] for e in self.de_tipo(run, "parte_firmada")]
        self.assertEqual(firmadas, ["U1", "U3"])
        self.assertEqual(
            cadena.ultima_parte_firmada(self.store, run), self.commit_de(run, "U3")
        )

        # Y el archivo que U2 quiso pisar quedó como U1 lo firmó, byte a byte.
        directorio = self.ruta_de_trabajo(run)
        self.assertEqual(
            (directorio / "tests" / "u1.test.js").read_text(encoding="utf-8"),
            self.contenido_firmado(run, "U1", "tests/u1.test.js"),
        )

    def test_el_commit_de_la_parte_anterior_sigue_teniendo_lo_que_tenia(self):
        """El punto de retorno de ADR-019 punto 2, comprobado donde vive."""
        run, _, _ = self.correr_cadena(TRES_UNIDADES)
        directorio = self.ruta_de_trabajo(run)
        commit = self.commit_de(run, "U1")

        guardado = subprocess.run(
            ["git", "-C", str(directorio), "show", "%s:src/u1.js" % commit],
            capture_output=True, text=True, check=True,
        ).stdout
        self.assertEqual(guardado, self.contenido_firmado(run, "U1", "src/u1.js"))

        # Y el commit de U1 lleva su identificador y su enunciado, que es lo que
        # hace legible `git log --oneline` sobre el espacio.
        asunto = subprocess.run(
            ["git", "-C", str(directorio), "log", "--format=%s", "-1", commit],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertTrue(asunto.startswith("U1 — "))

    def test_la_parte_que_no_se_puede_hacer_sin_reabrir_escala(self):
        """El punto 6: la decisión de reabrir lo firmado la toma una persona.

        Llega cara —agota las tres iteraciones antes de escalar— y eso está
        declarado en el propio ADR: la otra mitad del punto 6, declararlo en el
        plan de antemano, no se implementó.
        """
        run, _, _ = self.correr_cadena(
            TRES_UNIDADES,
            developer=developer_que_pisa("U2", "tests/u1.test.js", "tests/u2.test.js"),
        )
        run_developer = next(
            e["payload"]["run_developer"] for e in self.de_tipo(run, "unidad_lanzada")
            if e["payload"]["unidad"] == "U2"
        )

        (escalamiento,) = self.de_tipo(run_developer, "escalamiento")
        self.assertEqual(escalamiento["payload"]["motivo"], "escalado_por_iteraciones")
        self.assertEqual(
            {i["regla"] for i in escalamiento["payload"]["incumplimientos"]}, {"C10"}
        )

        (detenido,) = self.de_tipo(run, "plan_detenido")
        self.assertEqual(detenido["payload"]["unidad"], "U2")
        self.assertEqual(detenido["payload"]["motivo"], "escalado_por_iteraciones")


if __name__ == "__main__":
    unittest.main()
