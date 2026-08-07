"""Criterio de aceptación de T7.

Un test por fixture. Cada uno comprueba que se dispara exactamente la regla
sembrada y ninguna otra. El plan limpio no reporta nada: un falso positivo sobre
él invalida T7 igual que un falso negativo.
"""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from verificador import verificar  # noqa: E402

FIXTURES = RAIZ / "fixtures"
PEDIDO = (FIXTURES / "pedido.txt").read_text(encoding="utf-8")


def veredicto(nombre):
    plan = json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))
    return verificar(plan, PEDIDO)


def reglas_disparadas(resultado):
    return {i["regla"] for i in resultado["incumplimientos"]}


class PlanLimpio(unittest.TestCase):
    def test_plan_ok_no_reporta_nada(self):
        r = veredicto("plan-ok.json")
        self.assertEqual(r["incumplimientos"], [], "falso positivo sobre el plan limpio")
        self.assertTrue(r["valido"])


class DefectoSembrado(unittest.TestCase):
    def _comprobar(self, fixture, regla_esperada):
        r = veredicto(fixture)
        self.assertFalse(r["valido"])
        self.assertEqual(
            reglas_disparadas(r),
            {regla_esperada},
            "%s debía disparar solo la regla %d" % (fixture, regla_esperada),
        )
        return r

    def test_r1_unidad_sin_criterios(self):
        r = self._comprobar("plan-r1.json", 1)
        self.assertEqual([i["unidad"] for i in r["incumplimientos"]], ["U3"])

    def test_r2_criterio_sin_procedimiento(self):
        r = self._comprobar("plan-r2.json", 2)
        (fallo,) = r["incumplimientos"]
        self.assertEqual(fallo["unidad"], "U2")
        self.assertEqual(fallo["criterio"], 0)
        self.assertIn("procedimiento", fallo["detalle"])

    def test_r3_dependencia_inexistente(self):
        r = self._comprobar("plan-r3.json", 3)
        (fallo,) = r["incumplimientos"]
        self.assertEqual(fallo["unidad"], "U4")
        self.assertIn("U9", fallo["detalle"])

    def test_r5_alcance_excluido(self):
        r = self._comprobar("plan-r5.json", 5)
        self.assertEqual({i["unidad"] for i in r["incumplimientos"]}, {"U5"})
        for fallo in r["incumplimientos"]:
            self.assertIn("interfaz gráfica", fallo["detalle"])

    def test_r7_ciclo_de_dependencias(self):
        r = self._comprobar("plan-r7.json", 7)
        (fallo,) = r["incumplimientos"]
        self.assertIsNone(fallo["unidad"])
        # Solo las unidades del ciclo, no las que quedan aguas abajo.
        self.assertIn("U1, U2", fallo["detalle"])
        self.assertNotIn("U3", fallo["detalle"])
        self.assertNotIn("U4", fallo["detalle"])


class FormaDeLaSalida(unittest.TestCase):
    def test_todas_las_claves_declaradas(self):
        for fixture in ("plan-ok.json", "plan-r1.json", "plan-r5.json"):
            r = veredicto(fixture)
            self.assertEqual(set(r), {"valido", "incumplimientos"})
            self.assertIsInstance(r["valido"], bool)
            for fallo in r["incumplimientos"]:
                self.assertEqual(set(fallo), {"regla", "unidad", "criterio", "detalle"})
                self.assertIsInstance(fallo["regla"], int)
                self.assertIsInstance(fallo["detalle"], str)
                self.assertTrue(fallo["unidad"] is None or isinstance(fallo["unidad"], str))
                self.assertTrue(fallo["criterio"] is None or isinstance(fallo["criterio"], int))

    def test_esquema_invalido_devuelve_regla_0_y_no_evalua_el_resto(self):
        plan = json.loads((FIXTURES / "plan-r1.json").read_text(encoding="utf-8"))
        plan["campo_inventado"] = "x"
        r = verificar(plan, PEDIDO)
        self.assertFalse(r["valido"])
        self.assertEqual(reglas_disparadas(r), {0})

    def test_evalua_todas_las_reglas_sin_cortar_en_la_primera(self):
        plan = json.loads((FIXTURES / "plan-r1.json").read_text(encoding="utf-8"))
        plan["unidades"][3]["dependencias"] = ["U9"]
        r = verificar(plan, PEDIDO)
        self.assertEqual(reglas_disparadas(r), {1, 3})


if __name__ == "__main__":
    unittest.main(verbosity=2)
