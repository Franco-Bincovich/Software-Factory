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

from verificador import (  # noqa: E402
    EXTENSIONES_AJENAS,
    LENGUAJE_DE_LA_FABRICA,
    TERMINOS_AJENOS,
    verificar,
)

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

    def test_r8_lenguaje_ajeno(self):
        r = self._comprobar("plan-r8.json", 8)
        detalles = [i["detalle"] for i in r["incumplimientos"]]
        # Los tres lugares sembrados: el supuesto, la ruta y el procedimiento.
        self.assertTrue(any("supuesto 2" in d and "python" in d for d in detalles))
        self.assertTrue(any("ruta_artefacto" in d and "'.py'" in d for d in detalles))
        self.assertTrue(any("procedimiento" in d and "pytest" in d for d in detalles))
        # Y localiza: la ruta es de U1, el procedimiento es del criterio 0 de U2.
        (ruta,) = [i for i in r["incumplimientos"] if "ruta_artefacto" in i["detalle"]]
        self.assertEqual((ruta["unidad"], ruta["criterio"]), ("U1", None))
        (proc,) = [i for i in r["incumplimientos"] if "pytest" in i["detalle"] and i["unidad"]]
        self.assertEqual((proc["unidad"], proc["criterio"]), ("U2", 0))


class Regla8(unittest.TestCase):
    """El vocabulario es cerrado y declarado, y dos campos quedan afuera."""

    def _plan(self):
        return json.loads((FIXTURES / "plan-ok.json").read_text(encoding="utf-8"))

    def _reglas(self, plan):
        return reglas_disparadas(verificar(plan, PEDIDO))

    def test_nombrar_un_lenguaje_para_excluirlo_no_es_comprometerse(self):
        """`fuera_de_alcance` y `alcance_excluido` no se miran, y es a propósito."""
        plan = self._plan()
        plan["fuera_de_alcance"].append("Implementar nada de esto en Python.")
        plan["restricciones"]["alcance_excluido"].append("django")
        self.assertNotIn(8, self._reglas(plan))

    def test_el_lenguaje_de_la_fabrica_no_se_marca_a_si_mismo(self):
        """`java` está prohibido y vive adentro de `javascript`, que no lo está."""
        plan = self._plan()
        plan["unidades"][0]["enunciado"] = "Escribir la lógica en JavaScript, sin frameworks."
        plan["unidades"][0]["ruta_artefacto"] = "src/lector.js"
        self.assertNotIn(8, self._reglas(plan))

    def test_la_extension_de_un_csv_no_es_la_de_csharp(self):
        """`.csv` no puede leerse como `.cs`: la frontera de palabra lo impide."""
        plan = self._plan()
        plan["unidades"][0]["artefacto_esperado"] = "Módulo que lee altas.csv y devuelve registros."
        self.assertNotIn(8, self._reglas(plan))

    def test_el_detalle_nombra_el_lenguaje_de_la_fabrica(self):
        """Un rechazo que no dice qué sí se puede producir obliga a adivinar."""
        plan = self._plan()
        plan["supuestos"].append("Se usa Ruby con rspec.")
        fallos = [i for i in verificar(plan, PEDIDO)["incumplimientos"] if i["regla"] == 8]
        self.assertTrue(fallos)
        for fallo in fallos:
            self.assertIn(LENGUAJE_DE_LA_FABRICA, fallo["detalle"])

    def test_el_vocabulario_no_incluye_palabras_del_castellano(self):
        """Un falso positivo cuesta un plan rechazado y una iteración pagada."""
        for palabra in ("cargo", "go", "gem", "py", "ir", "as"):
            self.assertNotIn(palabra, TERMINOS_AJENOS)
        for ext in EXTENSIONES_AJENAS:
            self.assertTrue(ext.startswith("."), ext)


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
