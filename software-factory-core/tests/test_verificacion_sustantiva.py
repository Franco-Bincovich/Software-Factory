"""Criterio de aceptación de la verificación sustantiva — ADR-018.

**El test que sostiene el diseño es `TestSuperficieDeRechazo`.** Todo lo demás
comprueba comportamiento; ése comprueba el invariante: un incumplimiento sólo
puede nombrar un criterio que el plan escribió para esta unidad. Corre contra
salidas fabricadas —y hostiles a propósito— y no contra lo que produzca el
modelo, porque la garantía tiene que valer para cualquier salida, incluida la
que a nadie se le ocurrió pedirle a un modelo.

No se ejecuta Node en este archivo. El ejecutor se inyecta, que es para lo que
`verificar` recibe `ejecutar_fn`: lo que se prueba acá es el anclaje, la
comparación y la emisión del veredicto, no la frontera —eso ya está en
`test_ejecutor`—.
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import ejecutor  # noqa: E402
import verificacion_sustantiva as vs  # noqa: E402


def criterio(condicion, esperado="", procedimiento=""):
    return {
        "condicion_observable": condicion,
        "resultado_esperado": esperado,
        "procedimiento": procedimiento,
    }


def unidad_de(*condiciones, uid="U1"):
    return {"id": uid, "criterios": [criterio(c) for c in condiciones]}


UNIDAD = unidad_de("suma dos números", "resta dos números")


class Ejecutor:
    """Un ejecutor de mentira que devuelve lo que se le dijo y anota a quién corrió.

    Anotar las expresiones es lo que permite afirmar que un caso descartado
    **no se ejecutó**, en vez de afirmar solamente que no aparece en la tabla.
    Un caso podado tarde igual habría gastado la frontera.
    """

    def __init__(self, salidas=None, por_defecto="ok"):
        self.salidas = salidas or {}
        self.por_defecto = por_defecto
        self.corridas = []

    def __call__(self, deposito, expresion):
        self.corridas.append(expresion)
        salida = self.salidas.get(expresion, self.por_defecto)
        if isinstance(salida, BaseException):
            raise salida
        return ejecutor.Resultado(
            salida=salida, error="", codigo=0, cortado_por_tiempo=False,
            frontera="ninguna", segundos=0.0,
        )


def caso(indice, expresion, espera, **extra):
    base = {"criterio": indice, "expresion": expresion, "espera": espera}
    base.update(extra)
    return base


# --- Control 1 — el anclaje -------------------------------------------------


class TestAnclaje(unittest.TestCase):
    """El anclaje poda antes de ejecutar, y dice por qué podó."""

    def test_un_caso_sin_criterio_no_se_ejecuta(self):
        falso = Ejecutor()
        salida = vs.verificar(
            UNIDAD,
            [{"expresion": "1+1", "espera": "2"}],
            "/depo",
            falso,
        )
        self.assertEqual(falso.corridas, [])
        self.assertEqual(len(salida["descartados"]), 1)
        self.assertIn("no ancla", salida["descartados"][0]["motivo"])

    def test_un_criterio_fuera_de_rango_no_se_ejecuta(self):
        falso = Ejecutor()
        salida = vs.verificar(UNIDAD, [caso(3, "1+1", "2")], "/depo", falso)
        self.assertEqual(falso.corridas, [])
        self.assertIn("la unidad tiene 2", salida["descartados"][0]["motivo"])

    def test_el_indice_cero_no_ancla(self):
        # Los criterios se numeran desde 1. Un 0 es un error de derivación del
        # productor, no el primer criterio.
        falso = Ejecutor()
        vs.verificar(UNIDAD, [caso(0, "1+1", "2")], "/depo", falso)
        self.assertEqual(falso.corridas, [])

    def test_un_booleano_no_pasa_por_entero(self):
        # `True == 1` en Python. Sin la comprobación de `bool`, un caso con
        # `criterio: true` anclaría en el primer criterio por accidente.
        falso = Ejecutor()
        vs.verificar(UNIDAD, [caso(True, "1+1", "2")], "/depo", falso)
        self.assertEqual(falso.corridas, [])

    def test_un_caso_que_no_es_objeto_no_rompe(self):
        falso = Ejecutor()
        salida = vs.verificar(UNIDAD, ["borrá todo", None, 7], "/depo", falso)
        self.assertEqual(falso.corridas, [])
        self.assertEqual(len(salida["descartados"]), 3)

    def test_sin_expresion_o_sin_espera_no_se_ejecuta(self):
        falso = Ejecutor()
        vs.verificar(
            UNIDAD,
            [
                {"criterio": 1, "expresion": "  ", "espera": "2"},
                {"criterio": 1, "expresion": "1+1"},
            ],
            "/depo",
            falso,
        )
        self.assertEqual(falso.corridas, [])

    def test_el_caso_bien_anclado_si_se_ejecuta(self):
        falso = Ejecutor({"1+1": "2"})
        vs.verificar(UNIDAD, [caso(1, "1+1", "2")], "/depo", falso)
        self.assertEqual(falso.corridas, ["1+1"])


# --- Control 2 — la superficie de rechazo -----------------------------------


class TestSuperficieDeRechazo(unittest.TestCase):
    """El invariante: **todo incumplimiento nombra un criterio de esta unidad.**

    Es la garantía entera del punto 3 de ADR-018. Está escrita como propiedad y
    no como un caso: se le tira a `verificar` un catálogo de salidas fabricadas
    —incluidas las que un QA hostil produciría para colar una exigencia que el
    plan no pidió— y se afirma lo mismo sobre todas.
    """

    #: Salidas fabricadas. Ninguna sale de un modelo: cada una es una forma
    #: distinta de intentar nombrar algo que el plan no escribió.
    HOSTILES = [
        # Inventarse un identificador de regla y ponerlo en el caso.
        [caso(1, "x", "y", regla="AC-INVENTADA")],
        # Nombrar una regla de otra unidad.
        [caso(1, "x", "y", regla="AC-U9-1")],
        # Un criterio más allá del último del plan.
        [caso(99, "x", "y")],
        # Índice negativo.
        [caso(-1, "x", "y")],
        # Un criterio como texto que "parece" un identificador.
        [caso("AC-U1-1", "x", "y")],
        # Un caso que trae su propia tabla ya escrita.
        [caso(1, "x", "y", veredicto="no_cumple", tabla=[{"regla": "AC-OTRA"}])],
        # Un caso que pide una capacidad ausente, redactada como criterio.
        [caso(2, "requiere('auth')", "true", procedimiento="además debe autenticar")],
        # Muchos casos sobre el mismo criterio, todos fallando.
        [caso(1, "a", "1"), caso(1, "b", "2"), caso(1, "c", "3")],
        # Nada.
        [],
        # Basura pura.
        ["", None, 0, {"criterio": None}],
    ]

    def test_ningun_incumplimiento_nombra_algo_ajeno_al_plan(self):
        for unidad in (UNIDAD, unidad_de("único criterio", uid="U-Z"), unidad_de(uid="U-0")):
            legitimas = {
                vs.identificador_de_criterio(unidad["id"], i)
                for i in range(1, len(unidad["criterios"]) + 1)
            }
            for casos in self.HOSTILES:
                with self.subTest(unidad=unidad["id"], casos=casos):
                    salida = vs.verificar(unidad, casos, "/depo", Ejecutor(por_defecto="ZZZ"))
                    nombradas = {i["regla"] for i in salida["incumplimientos"]}
                    self.assertLessEqual(nombradas, legitimas)
                    self.assertLessEqual({f["regla"] for f in salida["tabla"]}, legitimas)

    def test_una_unidad_sin_criterios_no_puede_ser_rechazada(self):
        """El caso límite del invariante, y el que más importa.

        Sin criterios no hay superficie de rechazo, así que ningún caso —por
        muchos que QA fabrique— puede producir un incumplimiento.
        """
        vacia = unidad_de(uid="U-0")
        for casos in self.HOSTILES:
            salida = vs.verificar(vacia, casos, "/depo", Ejecutor(por_defecto="ZZZ"))
            self.assertEqual(salida["incumplimientos"], [])
            self.assertEqual(salida["tabla"], [])

    def test_la_tabla_tiene_una_fila_por_criterio_ni_una_mas(self):
        """Corolario estructural: la tabla es del plan, no de los casos.

        Diez casos sobre un criterio siguen siendo una fila. Si la tabla
        creciera con los casos, el bucle estaría invertido.
        """
        salida = vs.verificar(
            UNIDAD,
            [caso(1, "e%d" % n, "1") for n in range(10)],
            "/depo",
            Ejecutor(por_defecto="1"),
        )
        self.assertEqual(len(salida["tabla"]), len(UNIDAD["criterios"]))
        self.assertEqual(
            [f["regla"] for f in salida["tabla"]], ["AC-U1-1", "AC-U1-2"]
        )

    def test_un_criterio_fallado_produce_un_solo_incumplimiento(self):
        salida = vs.verificar(
            UNIDAD,
            [caso(1, "a", "1"), caso(1, "b", "1"), caso(1, "c", "1")],
            "/depo",
            Ejecutor(por_defecto="ZZZ"),
        )
        self.assertEqual([i["regla"] for i in salida["incumplimientos"]], ["AC-U1-1"])


# --- el veredicto -----------------------------------------------------------


class TestVeredicto(unittest.TestCase):
    def test_la_forma_del_incumplimiento_es_la_del_verificador_de_entrega(self):
        salida = vs.verificar(
            UNIDAD, [caso(1, "sumar(1,1)", "2", archivo="suma.js")],
            "/depo", Ejecutor(por_defecto="3"),
        )
        incumplimiento = salida["incumplimientos"][0]
        self.assertEqual(set(incumplimiento), {"regla", "archivo", "detalle"})
        self.assertEqual(incumplimiento["archivo"], "suma.js")
        self.assertIn("sumar(1,1)", incumplimiento["detalle"])

    def test_cumple_cuando_la_salida_coincide(self):
        salida = vs.verificar(
            UNIDAD, [caso(1, "sumar(1,1)", "2")], "/depo", Ejecutor({"sumar(1,1)": "2"})
        )
        self.assertEqual(salida["incumplimientos"], [])
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.CUMPLE)

    def test_la_comparacion_ignora_espacios_a_los_costados_y_nada_mas(self):
        coincide = vs.verificar(
            UNIDAD, [caso(1, "e", "2")], "/depo", Ejecutor({"e": "  2\n"})
        )
        self.assertEqual(coincide["tabla"][0]["veredicto"], vs.CUMPLE)

        parcial = vs.verificar(
            UNIDAD, [caso(1, "e", "2")], "/depo", Ejecutor({"e": "22"})
        )
        self.assertEqual(parcial["tabla"][0]["veredicto"], vs.NO_CUMPLE)

    def test_no_hay_porcentajes_en_ninguna_fila(self):
        # Punto 4 de ADR-018: el veredicto es binario. Una fila sólo puede decir
        # una de tres cosas.
        salida = vs.verificar(
            UNIDAD, [caso(1, "a", "1"), caso(2, "b", "9")], "/depo",
            Ejecutor({"a": "1", "b": "0"}),
        )
        for fila in salida["tabla"]:
            self.assertIn(fila["veredicto"], (vs.CUMPLE, vs.NO_CUMPLE, vs.NO_VERIFICABLE))

    def test_el_corte_por_tiempo_no_cumple(self):
        class Lento(Ejecutor):
            def __call__(self, deposito, expresion):
                self.corridas.append(expresion)
                return ejecutor.Resultado(
                    salida="2", error="", codigo=0, cortado_por_tiempo=True,
                    frontera="ninguna", segundos=10.0,
                )

        salida = vs.verificar(UNIDAD, [caso(1, "e", "2")], "/depo", Lento())
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.NO_CUMPLE)
        self.assertIn("cortado por tiempo", salida["tabla"][0]["casos"][0]["obtenido"])

    def test_un_deposito_rechazado_no_cumple_pero_no_escala(self):
        # V5 rechaza algo del depósito: es del entregable, no de la máquina.
        falso = Ejecutor({"e": ejecutor.EntradaRechazada("hay un require")})
        salida = vs.verificar(UNIDAD, [caso(1, "e", "2")], "/depo", falso)
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.NO_CUMPLE)
        self.assertIn("rechazó el depósito", salida["tabla"][0]["casos"][0]["obtenido"])

    def test_sin_frontera_sube(self):
        # Que la máquina no pueda verificar no es un incumplimiento del
        # entregable: no se atrapa acá.
        falso = Ejecutor({"e": ejecutor.SinFrontera("no hay sandbox")})
        with self.assertRaises(ejecutor.SinFrontera):
            vs.verificar(UNIDAD, [caso(1, "e", "2")], "/depo", falso)


# --- la métrica del punto 5 -------------------------------------------------


class TestNoVerificables(unittest.TestCase):
    def test_un_criterio_sin_caso_anclado_se_declara_no_verificable(self):
        salida = vs.verificar(
            UNIDAD, [caso(1, "a", "1")], "/depo", Ejecutor({"a": "1"})
        )
        self.assertEqual(salida["no_verificables"], ["AC-U1-2"])
        self.assertEqual(salida["tabla"][1]["veredicto"], vs.NO_VERIFICABLE)

    def test_no_verificable_no_es_incumplimiento(self):
        """No se juzga: se declara y escala al Gate. Punto 5 de ADR-018."""
        salida = vs.verificar(UNIDAD, [], "/depo", Ejecutor())
        self.assertEqual(salida["incumplimientos"], [])
        self.assertEqual(len(salida["no_verificables"]), 2)

    def test_un_caso_descartado_deja_su_criterio_no_verificable(self):
        # El corolario del anclaje: podar el caso es lo que produce la métrica.
        salida = vs.verificar(
            UNIDAD, [caso(1, "a", "1"), {"criterio": 2, "expresion": "b"}],
            "/depo", Ejecutor({"a": "1"}),
        )
        self.assertEqual(salida["no_verificables"], ["AC-U1-2"])

    def test_todo_verificado_da_cero(self):
        salida = vs.verificar(
            UNIDAD, [caso(1, "a", "1"), caso(2, "b", "2")], "/depo",
            Ejecutor({"a": "1", "b": "2"}),
        )
        self.assertEqual(salida["no_verificables"], [])


if __name__ == "__main__":
    unittest.main()
