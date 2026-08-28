"""Ningún test escribe en el directorio de estado real.

El estado operativo —`factory.db`, `trabajo/`, `entregas/`, `checkpointer/`—
es evidencia de producción. Una suite que escriba ahí contamina esa evidencia
con su propia salida, y un test que *lea* esa área termina validando en parte
lo que la propia suite acaba de producir.

Ya pasó: el 2026-08-28 `entregas/` venía creciendo dos corridas por cada
`unittest discover`. La causa no fue un descuido puntual sino una forma de
redirigir el estado que deja agujeros: `BaseCLI` mandaba `--db`,
`--checkpointer` y `--trabajo` a un temporal, pero `entregas/` es una cuarta
ruta que deriva de `DIR_ESTADO` y no tiene flag. `operational_state.py` ya
advierte por qué manda una sola variable y no tres; esto es esa advertencia
convertida en test.

**Qué comprueba y qué no.** Toma las clases base por las que pasan los tests
que ejercitan la cadena, corre su `setUp` y exige que todo lo que derive del
directorio de estado caiga en un temporal. No recorre la suite test por test:
si alguien escribe uno que se saltea las bases y va al área real por su
cuenta, esto no lo ve. Cubre la puerta por la que se entró la vez que pasó.
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))
sys.path.insert(0, str(RAIZ))

import cadena  # noqa: E402
import grafo  # noqa: E402
import operational_state  # noqa: E402

import test_cadena  # noqa: E402
import test_correr  # noqa: E402
import test_correr_cadena  # noqa: E402

# El directorio de estado tal como lo resolvería la fábrica en producción. Se
# lee del módulo al importar, antes de que ningún `setUp` lo redirija.
ESTADO_REAL = Path(operational_state.DIR_ESTADO).resolve()

BASES = (
    ("test_cadena.BaseCadena", test_cadena.BaseCadena),
    ("test_correr_cadena.BaseCLI", test_correr_cadena.BaseCLI),
    ("test_correr.BaseCLI", test_correr.BaseCLI),
)


def _cae_en_el_estado_real(ruta):
    try:
        Path(ruta).resolve().relative_to(ESTADO_REAL)
    except ValueError:
        return False
    return True


class ElEstadoRealNoSeToca(unittest.TestCase):
    def _sonda(self, base):
        """Una instancia mínima de la base, para poder correrle el `setUp`.

        `runTest` es el nombre que `TestCase` usa cuando se lo construye sin
        argumentos. Alcanza para que la instancia sea válida; no se ejecuta.
        """

        class Sonda(base):
            def runTest(self):
                pass

        return Sonda()

    @staticmethod
    def _desmontar(sonda):
        """Como la desmonta el runner: `tearDown` y después los `addCleanup`.

        Las dos cosas, y no sólo `tearDown`: unas bases restauran ahí y otras
        con `addCleanup`, que corre en `doCleanups`. Una sonda que llame a una
        sola inventa una fuga que en la suite real no existe.
        """
        sonda.tearDown()
        sonda.doCleanups()

    def test_las_bases_mandan_el_estado_a_un_temporal(self):
        for nombre, base in BASES:
            with self.subTest(base=nombre):
                sonda = self._sonda(base)
                sonda.setUp()
                try:
                    derivadas = {
                        "DIR_ESTADO": operational_state.DIR_ESTADO,
                        "entregas/": cadena.raiz_entregas(),
                    }
                    for que, ruta in derivadas.items():
                        self.assertFalse(
                            _cae_en_el_estado_real(ruta),
                            "%s deja %s dentro del estado real (%s)"
                            % (nombre, que, ruta),
                        )
                finally:
                    self._desmontar(sonda)

    def test_las_bases_devuelven_el_estado_al_terminar(self):
        """Redirigir sin restaurar contamina a los tests que vengan después.

        Un `setUp` que pisa `DIR_ESTADO` y no lo repone deja al resto de la
        suite apuntando a un temporal ya borrado, y el fallo aparece lejos de
        su causa.
        """
        for nombre, base in BASES:
            with self.subTest(base=nombre):
                antes = operational_state.DIR_ESTADO
                sonda = self._sonda(base)
                sonda.setUp()
                self._desmontar(sonda)
                self.assertEqual(operational_state.DIR_ESTADO, antes)

    def test_el_area_real_no_recibe_archivos_mientras_corren_las_bases(self):
        """La comprobación directa: mirar el disco, no las variables.

        Las dos de arriba miran a dónde apunta la configuración. Ésta mira si
        aparecieron archivos, que es el daño concreto que se quiere evitar.
        """
        if not ESTADO_REAL.is_dir():
            self.skipTest("no hay directorio de estado real en %s" % ESTADO_REAL)

        def foto():
            return {p for p in ESTADO_REAL.rglob("*") if p.is_file()}

        antes = foto()
        for _, base in BASES:
            sonda = self._sonda(base)
            sonda.setUp()
            self._desmontar(sonda)
        aparecidos = sorted(str(p.relative_to(ESTADO_REAL)) for p in foto() - antes)
        self.assertEqual(aparecidos, [], "la suite escribió en el estado real")


class ElAnclajeSigueSiendoUnaSolaVariable(unittest.TestCase):
    """`entregas/` se resuelve tarde, y de ahí que redirigirla funcione.

    Si alguna vez se congelara en una constante de módulo —como sí lo están
    `RAIZ_TRABAJO_POR_DEFECTO` y `RUTA_CHECKPOINTER_POR_DEFECTO`, que por eso
    necesitan flag— parchear `DIR_ESTADO` dejaría de alcanzar y las fugas
    volverían en silencio.
    """

    def test_raiz_entregas_se_calcula_tarde(self):
        original = operational_state.DIR_ESTADO
        operational_state.DIR_ESTADO = Path("/tmp/estado-inventado-para-el-test")
        try:
            self.assertEqual(
                cadena.raiz_entregas(),
                Path("/tmp/estado-inventado-para-el-test/entregas"),
            )
        finally:
            operational_state.DIR_ESTADO = original

    def test_las_rutas_congeladas_estan_declaradas(self):
        """Las que sí se congelan al importar, para que se sepa cuáles son.

        No es un defecto: tienen flag de CLI y los tests las redirigen por ahí.
        Está escrito para que quien agregue una cuarta sepa que le toca elegir
        entre calcularla tarde o darle flag.
        """
        for constante in (
            cadena.RAIZ_TRABAJO_POR_DEFECTO,
            grafo.RUTA_CHECKPOINTER_POR_DEFECTO,
            operational_state.RUTA_POR_DEFECTO,
        ):
            self.assertTrue(_cae_en_el_estado_real(constante), constante)


if __name__ == "__main__":
    unittest.main(verbosity=2)
