"""QA contra defectos conocidos — ADR-018 medido, no declarado.

`test_verificacion_sustantiva` prueba que el mecanismo funciona: ancla, poda,
compara y emite. Lo hace con un ejecutor inyectado y con criterios inventados,
que es lo correcto para probar un invariante. **Lo que no prueba es que QA
detecte un defecto que un humano nombraría.** Eso es lo que se prueba acá.

Acá corre Node de verdad, sobre entregas de verdad, contra criterios que escribió
el Requirement Agent en corridas de verdad. Nada de lo que se juzga se escribió
para esta prueba: la procedencia de cada archivo está en
`fixtures/defectos-conocidos/PROCEDENCIA.md`, con el número de evento del
`factory.db`.

## Lo que el registro no tiene

**El `factory.db` real no contiene un solo defecto sustantivo.** Ocho corridas,
ocho verificaciones estructurales, y una sola con `valido: false`: la iteración 1
de la corrida `cc2b9cf8` (evento 49), sobre la unidad U2 del `PLAN-0001`.

Ese rechazo **no es un caso de QA, y agregarlo sería un error**. Sus cuatro
incumplimientos son C5 y C6 —"el archivo no es ninguno de los cuatro entregables",
"falta `demo.html`"— y la comparación archivo por archivo contra la iteración 2,
que sí fue aceptada, da esto:

    IDENTICO  src/es-email-valido.js               -> src/es-email-valido.js
    IDENTICO  tests/es-email-valido.casos.test.js  -> tests/es-email-valido.casos.test.js
    IDENTICO  pruebas-U2.html                      -> pruebas.html
    IDENTICO  demo-U2.html                         -> demo.html

**El contenido es byte a byte el mismo. Lo único que cambió entre el rechazo y la
aceptación son dos nombres de archivo.** Es forma pura, y la capa que corresponde
ya lo agarró: es exactamente el reparto del punto 7 de ADR-018 —el verificador
estructural aprueba la forma, QA aprueba el fondo, y una entrega necesita los
dos—. Un test donde QA rechazara esa iteración probaría que QA invade la capa de
abajo, no que verifica.

Por eso el control positivo de este archivo es fabricado, y por eso se fabrica
como se fabrica.

## Cómo se fabricó el defecto sin inventar el resultado

Tres reglas, y el orden importa:

1. **El defecto sale de la prosa del plan, no del código de la verificación.** Cada
   mutación rompe una promesa que el plan escribió con palabras, y el atributo
   `nombre_humano` de cada una es cómo la nombraría alguien que nunca vio
   `verificacion_sustantiva.py`. Una mutación diseñada mirando la implementación
   probaría que QA detecta lo que QA ya sabe detectar, que no prueba nada.
2. **El veredicto esperado se derivó del criterio y se midió con Node a mano,
   antes de escribir la aserción.** La verdad de fondo la fija el intérprete; este
   archivo sólo afirma que el veredicto de QA coincide con ella.
3. **Se afirma el motivo, y también su negativo.** El criterio que la mutación no
   toca tiene que salir `cumple`. Un rechazo que nombre el criterio equivocado es
   un falso positivo disfrazado de acierto, y `TestElMotivoEsElCorrecto` falla si
   pasa.

## Lo que estos tests no prueban, y falta

Los casos de prueba de acá están **transcriptos** del `procedimiento` de cada
criterio: el plan dice "ejecutar la función con el string `'usuario@dominio.com'`
y verificar que el retorno sea `true`", y eso es literalmente la expresión y el
`espera` del caso.

Entonces lo que se prueba es que **el mecanismo juzga bien cuando los casos ya
están escritos**. No se prueba que el prompt de `productor_qa` sepa *derivarlos*
leyendo la prosa, que es la otra mitad del agente. Esa medición necesita una
corrida con modelo, cuesta plata, y es una sesión propia. Está pendiente y
autorizada para después; hasta que se haga, el alcance de este archivo es el que
dice este párrafo.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import ejecutor  # noqa: E402
import verificacion_sustantiva as vs  # noqa: E402

FIXTURES = RAIZ / "fixtures" / "defectos-conocidos"


def _hay_frontera():
    try:
        ejecutor.frontera_de_red()
        return shutil.which("node") is not None
    except ejecutor.SinFrontera:
        return False


HAY_FRONTERA = _hay_frontera()
MOTIVO = "sin frontera de kernel o sin Node: no se puede ejecutar la entrega real"


def unidad(nombre):
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


#: Unidad U1 del PLAN-0001. Sus dos criterios son los **dos únicos ejecutables
#: tal como están escritos** de los once que ADR-018 midió: dicen la expresión y
#: el resultado sin que nadie tenga que interpretar nada.
U1_PLAN_0001 = unidad("plan-0001-u1.json")

#: Unidad U1 del PLAN-EMAILVALIDATOR-001. Un solo criterio, que enumera por
#: nombre cinco direcciones inválidas y dos válidas.
U1_EMAILVALIDATOR = unidad("plan-emailvalidator-u1.json")


def caso(indice, modulo, argumento, espera):
    """Un caso de QA, transcripto del `procedimiento` del criterio.

    No hay derivación acá: el criterio nombra la dirección y el retorno, y esto
    los pone en la forma que `verificacion_sustantiva` sabe correr.
    """
    return {
        "criterio": indice,
        "archivo": modulo.lstrip("./"),
        "procedimiento": "esEmailValido(%r) tiene que dar %s" % (argumento, espera),
        "expresion": (
            "const { esEmailValido } = require(%s); console.log(esEmailValido(%s));"
            % (json.dumps(modulo), json.dumps(argumento))
        ),
        "espera": espera,
    }


MODULO_0001 = "./src/es-email-valido.js"
MODULO_EMAILVALIDATOR = "./src/validar-email.js"

#: Los dos criterios del PLAN-0001, palabra por palabra:
#: 1. "Ejecutar la función con el string 'usuario@dominio.com' … el valor de retorno sea true."
#: 2. "Ejecutar la función con el string 'usuario@dominio' … el valor de retorno sea false."
CASOS_0001 = [
    caso(1, MODULO_0001, "usuario@dominio.com", "true"),
    caso(2, MODULO_0001, "usuario@dominio", "false"),
]

#: El criterio del PLAN-EMAILVALIDATOR-001 declara "5 cadenas válidas y 5
#: inválidas" pero **sólo nombra dos de las válidas**. Se transcriben las siete
#: que nombra y ninguna más: completar las tres que faltan sería inventar el
#: criterio, no ejecutarlo.
CASOS_EMAILVALIDATOR = [
    caso(1, MODULO_EMAILVALIDATOR, argumento, espera)
    for argumento, espera in [
        ("a@b.com", "true"),
        ("juan.perez@empresa.com.ar", "true"),
        ("texto-sin-arroba", "false"),
        ("@dominio.com", "false"),
        ("usuario@", "false"),
        ("usuario@dominio", "false"),
        ("usuario @dominio.com", "false"),
    ]
]


class Mutacion:
    """Un defecto sembrado en una entrega real, con su nombre en castellano.

    `nombre_humano` no es decoración: es la comprobación de la regla 1. Si un
    defecto no se puede nombrar sin hablar de la implementación de la
    verificación, no sirve como prueba de que la verificación detecta defectos.
    """

    def __init__(self, entrega, archivo, busca, reemplaza, nombre_humano, promesa_rota):
        self.entrega = entrega
        self.archivo = archivo
        self.busca = busca
        self.reemplaza = reemplaza
        self.nombre_humano = nombre_humano
        self.promesa_rota = promesa_rota


M1 = Mutacion(
    entrega="entrega-1a4fc044",
    archivo="src/es-email-valido.js",
    busca=r"@[^\s@]+\.[^\s@]+$/",
    reemplaza=r"@[^\s@]+$/",
    nombre_humano="acepta direcciones sin dominio de primer nivel",
    promesa_rota="La función retorna false para la dirección inválida 'usuario@dominio'.",
)

M2 = Mutacion(
    entrega="entrega-1a4fc044",
    archivo="src/es-email-valido.js",
    busca="  const patron =",
    reemplaza='  if (valor.includes(".com")) {\n    return false;\n  }\n  const patron =',
    nombre_humano="rechaza una dirección válida",
    promesa_rota="La función retorna true para la dirección válida 'usuario@dominio.com'.",
)

M3 = Mutacion(
    entrega="entrega-1a4fc044",
    archivo="src/es-email-valido.js",
    busca="return patron.test(valor);",
    reemplaza="return valor.match(patron);",
    nombre_humano="no devuelve un booleano, devuelve el resultado del match",
    promesa_rota="…determine si es una dirección de email sintácticamente válida, "
                 "devolviendo un valor booleano.",
)

M4 = Mutacion(
    entrega="entrega-6e131d4c",
    archivo="src/validar-email.js",
    busca=r"/^[^\s@]+@[^\s@]+\.[^\s@]+$/",
    reemplaza=r"/^[^@]+@[^@]+\.[^@]+$/",
    nombre_humano="acepta espacios en el medio de la dirección",
    promesa_rota="…5 cadenas que no lo son (ej: …, 'usuario @dominio.com').",
)


class BaseDeposito(unittest.TestCase):
    """Cada test arma su propio depósito a partir de la entrega real."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.armados = 0

    def deposito(self, entrega, mutacion=None):
        # Un directorio por armado: un test que compara dos mutaciones de la
        # misma entrega necesita las dos vivas al mismo tiempo.
        self.armados += 1
        destino = Path(self.tmp.name) / ("%d-%s" % (self.armados, entrega))
        shutil.copytree(FIXTURES / entrega, destino)
        if mutacion is not None:
            fuente = destino / mutacion.archivo
            texto = fuente.read_text(encoding="utf-8")
            self.assertIn(
                mutacion.busca, texto,
                "la mutación %r ya no encuentra qué mutar: la entrega cambió"
                % mutacion.nombre_humano,
            )
            fuente.write_text(
                texto.replace(mutacion.busca, mutacion.reemplaza, 1), encoding="utf-8"
            )
        return str(destino)

    def verificar(self, unidad_, casos, entrega, mutacion=None):
        return vs.verificar(unidad_, casos, self.deposito(entrega, mutacion))

    def fila(self, salida, regla):
        for fila in salida["tabla"]:
            if fila["regla"] == regla:
                return fila
        self.fail("la tabla no tiene fila para %s" % regla)

    def obtenido(self, salida, regla):
        return self.fila(salida, regla)["casos"][0]["obtenido"]

    def detalle(self, salida, regla):
        for incumplimiento in salida["incumplimientos"]:
            if incumplimiento["regla"] == regla:
                return incumplimiento["detalle"]
        self.fail("no hay incumplimiento para %s" % regla)


# --- control negativo — la entrega correcta se acepta -----------------------


@unittest.skipUnless(HAY_FRONTERA, MOTIVO)
class ControlNegativo(BaseDeposito):
    """Sin esto sólo se sabría que QA rechaza, no que discrimine.

    Las dos entregas fueron aceptadas por el verificador estructural y las dos
    hacen lo que su plan pidió. QA no tiene por dónde rechazarlas.
    """

    def test_la_entrega_real_del_plan_0001_cumple_sus_dos_criterios(self):
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, "entrega-1a4fc044")
        self.assertEqual(salida["incumplimientos"], [])
        self.assertEqual(
            [f["veredicto"] for f in salida["tabla"]], [vs.CUMPLE, vs.CUMPLE]
        )

    def test_la_entrega_real_del_emailvalidator_cumple_su_criterio(self):
        salida = self.verificar(
            U1_EMAILVALIDATOR, CASOS_EMAILVALIDATOR, "entrega-6e131d4c"
        )
        self.assertEqual(salida["incumplimientos"], [])
        self.assertEqual(self.fila(salida, "AC-U1-1")["veredicto"], vs.CUMPLE)

    def test_las_siete_direcciones_que_el_plan_nombra_dan_lo_que_el_plan_dice(self):
        """El control negativo, caso por caso y no agregado.

        Una fila `cumple` con un caso que falló no existe, pero afirmarlo sobre
        el agregado dejaría pasar una fila donde ningún caso corrió.
        """
        salida = self.verificar(
            U1_EMAILVALIDATOR, CASOS_EMAILVALIDATOR, "entrega-6e131d4c"
        )
        corridos = self.fila(salida, "AC-U1-1")["casos"]
        self.assertEqual(len(corridos), 7)
        for corrido in corridos:
            with self.subTest(expresion=corrido["expresion"]):
                self.assertTrue(corrido["cumple"])
                self.assertEqual(corrido["obtenido"], corrido["espera"])

    def test_la_entrega_correcta_no_deja_criterios_sin_verificar(self):
        """Los dos criterios del PLAN-0001 son ejecutables, y se ejecutan.

        Si esto empezara a dar `no_verificable`, el problema no sería la entrega:
        sería que el depósito o la frontera dejaron de dejar correr.
        """
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, "entrega-1a4fc044")
        self.assertEqual(salida["no_verificables"], [])
        self.assertEqual(salida["descartados"], [])


# --- control positivo — el defecto sembrado se rechaza ----------------------


@unittest.skipUnless(HAY_FRONTERA, MOTIVO)
class ElDefectoSeRechaza(BaseDeposito):
    """Cuatro defectos, cada uno rompiendo una promesa escrita en el plan."""

    def test_m1_sin_dominio_de_primer_nivel(self):
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, M1.entrega, M1)
        self.assertEqual(self.fila(salida, "AC-U1-2")["veredicto"], vs.NO_CUMPLE)
        self.assertEqual(
            self.obtenido(salida, "AC-U1-2"), "true",
            "'usuario@dominio' tenía que salir true con la mutación: %s"
            % M1.nombre_humano,
        )

    def test_m2_rechaza_una_direccion_valida(self):
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, M2.entrega, M2)
        self.assertEqual(self.fila(salida, "AC-U1-1")["veredicto"], vs.NO_CUMPLE)
        self.assertEqual(self.obtenido(salida, "AC-U1-1"), "false")

    def test_m3_no_devuelve_un_booleano(self):
        """El único que rompe los dos criterios, y por el mismo motivo.

        Es la forma del retorno, no el juicio sobre la dirección: la dirección
        válida da el match y la inválida da `null`, y ninguno de los dos es el
        booleano que el enunciado de la unidad promete.
        """
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, M3.entrega, M3)
        self.assertEqual(
            [f["veredicto"] for f in salida["tabla"]], [vs.NO_CUMPLE, vs.NO_CUMPLE]
        )
        self.assertNotIn(self.obtenido(salida, "AC-U1-1"), ("true", "false"))
        self.assertEqual(self.obtenido(salida, "AC-U1-2"), "null")

    def test_m4_acepta_espacios_en_el_medio(self):
        salida = self.verificar(
            U1_EMAILVALIDATOR, CASOS_EMAILVALIDATOR, M4.entrega, M4
        )
        self.assertEqual(self.fila(salida, "AC-U1-1")["veredicto"], vs.NO_CUMPLE)
        fallidos = [c for c in self.fila(salida, "AC-U1-1")["casos"] if not c["cumple"]]
        self.assertEqual(len(fallidos), 1, "el defecto no era ése solo")
        self.assertIn("usuario @dominio.com", fallidos[0]["expresion"])
        self.assertEqual(fallidos[0]["obtenido"], "true")


# --- el motivo del rechazo tiene que ser el motivo del defecto --------------


@unittest.skipUnless(HAY_FRONTERA, MOTIVO)
class ElMotivoEsElCorrecto(BaseDeposito):
    """Un rechazo por la razón equivocada es un falso positivo disfrazado.

    Que la tabla diga `no_cumple` no alcanza: hay que ver que nombre el criterio
    que el defecto rompió, que no nombre los otros, y que el detalle diga qué se
    esperaba y qué salió.
    """

    def test_m1_no_toca_el_criterio_de_la_direccion_valida(self):
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, M1.entrega, M1)
        self.assertEqual([i["regla"] for i in salida["incumplimientos"]], ["AC-U1-2"])
        self.assertEqual(self.fila(salida, "AC-U1-1")["veredicto"], vs.CUMPLE)

    def test_m2_no_toca_el_criterio_de_la_direccion_invalida(self):
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, M2.entrega, M2)
        self.assertEqual([i["regla"] for i in salida["incumplimientos"]], ["AC-U1-1"])
        self.assertEqual(self.fila(salida, "AC-U1-2")["veredicto"], vs.CUMPLE)

    def test_dos_defectos_distintos_no_dan_el_mismo_rechazo(self):
        """La comprobación que M1 y M2 existen para hacer.

        Si QA rechazara siempre por el mismo criterio, los dos tests de arriba
        pasarían de a uno y el conjunto seguiría sin discriminar. Los rechazos
        tienen que ser **disjuntos**, porque los defectos lo son.
        """
        uno = self.verificar(U1_PLAN_0001, CASOS_0001, M1.entrega, M1)
        otro = self.verificar(U1_PLAN_0001, CASOS_0001, M2.entrega, M2)
        reglas_uno = {i["regla"] for i in uno["incumplimientos"]}
        reglas_otro = {i["regla"] for i in otro["incumplimientos"]}
        # Los dos no vacíos primero: dos conjuntos vacíos también son disjuntos,
        # y sin esto el test pasaría con un QA que no rechaza nada.
        self.assertTrue(reglas_uno and reglas_otro)
        self.assertEqual(reglas_uno & reglas_otro, set())

    def test_el_detalle_cita_la_promesa_que_el_plan_escribio(self):
        """El detalle es lo que lee el Developer para corregir.

        Tiene que traer el `resultado_esperado` del criterio tal como el plan lo
        escribió, no una paráfrasis: es la diferencia entre "corregí esto" y
        "adiviná qué quise decir".
        """
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, M1.entrega, M1)
        esperado = U1_PLAN_0001["criterios"][1]["resultado_esperado"]
        self.assertIn(esperado, self.detalle(salida, "AC-U1-2"))
        self.assertEqual(esperado, M1.promesa_rota)

    def test_el_detalle_dice_que_se_esperaba_y_que_salio(self):
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, M2.entrega, M2)
        detalle = self.detalle(salida, "AC-U1-1")
        self.assertIn("Se esperaba 'true'", detalle)
        self.assertIn("se obtuvo 'false'", detalle)
        self.assertIn("usuario@dominio.com", detalle)

    def test_el_incumplimiento_nombra_el_archivo_del_defecto(self):
        salida = self.verificar(U1_PLAN_0001, CASOS_0001, M1.entrega, M1)
        self.assertEqual(
            salida["incumplimientos"][0]["archivo"], "src/es-email-valido.js"
        )
        self.assertEqual(salida["incumplimientos"][0]["archivo"], M1.archivo)


# --- la mutación es sobre la entrega real, no sobre una copia parecida ------


class LaMutacionEsSobreLaEntregaReal(BaseDeposito):
    """Sin frontera también corre: no ejecuta nada, sólo compara texto."""

    def test_cada_mutacion_cambia_exactamente_una_cosa(self):
        """Un defecto sembrado que además cambie otra cosa no prueba nada.

        Si la mutación tocara más de lo que dice, el rechazo podría venir de lo
        otro y la atribución del motivo sería mentira.
        """
        for mutacion in (M1, M2, M3, M4):
            with self.subTest(defecto=mutacion.nombre_humano):
                original = (FIXTURES / mutacion.entrega / mutacion.archivo).read_text(
                    encoding="utf-8"
                )
                self.assertEqual(original.count(mutacion.busca), 1)
                mutado = Path(
                    self.deposito(mutacion.entrega, mutacion), mutacion.archivo
                ).read_text(encoding="utf-8")
                self.assertNotEqual(mutado, original)
                self.assertEqual(mutado.replace(mutacion.reemplaza, mutacion.busca, 1),
                                 original)

    def test_el_deposito_sin_mutar_es_la_entrega_del_registro(self):
        """La copia no toca nada: lo que se juzga es lo que el Developer entregó."""
        for entrega in ("entrega-1a4fc044", "entrega-6e131d4c"):
            with self.subTest(entrega=entrega):
                copia = Path(self.deposito(entrega))
                for origen in sorted((FIXTURES / entrega).rglob("*")):
                    if origen.is_file():
                        relativa = origen.relative_to(FIXTURES / entrega)
                        self.assertEqual(
                            (copia / relativa).read_bytes(), origen.read_bytes()
                        )


if __name__ == "__main__":
    unittest.main()
