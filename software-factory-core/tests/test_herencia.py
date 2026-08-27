"""Ejecutar el Developer sobre un plan ya verificado en otra corrida.

Un plan que se produjo y se pagó no tiene por qué volver a producirse para poder
ejecutarse. Estos tests entran por `correr.main`, como entra una persona, y
cubren lo que la herencia tiene que garantizar: que el plan se identifique por la
corrida que lo produjo, que las dos corridas queden atadas en el registro, que el
techo no se pueda evadir partiendo el trabajo, y que reejecutar sea un acto
declarado y no un accidente.
"""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))
sys.path.insert(0, str(RAIZ))

import cadena  # noqa: E402
import grafo  # noqa: E402
import presupuesto  # noqa: E402

import correr  # noqa: E402
from test_correr_cadena import PEDIDO, BaseCLI  # noqa: E402


class BaseHerencia(BaseCLI):
    def plan_varado(self, pedido=None):
        """Una corrida `--solo-plan` que produce el plan y cierra sin ejecutarlo."""
        if pedido is not None:
            self.ruta_pedido.write_text(json.dumps(pedido), encoding="utf-8")
        codigo, run_id, error = self.nueva("--solo-plan")
        self.assertEqual(codigo, 0, error)
        self.aprobar(run_id, "entrada")
        codigo, _, error = self.cli("--reanudar", run_id, "--stub")
        self.assertEqual(codigo, 0, error)
        return run_id

    def heredar(self, de_corrida, *flags):
        return self.cli(
            "--desde-corrida", de_corrida,
            "--definicion-developer", str(self.ruta_developer),
            "--stub",
            *flags,
        )

    def heredar_y_ejecutar(self, de_corrida, *flags):
        codigo, run_id, error = self.heredar(de_corrida, *flags)
        self.assertEqual(codigo, 0, error)
        self.aprobar(run_id, "entrada")
        codigo, _, error = self.cli("--reanudar", run_id, "--stub")
        self.assertEqual(codigo, 0, error)
        return run_id

    def hecho_heredado(self, run_id):
        (evento,) = self.de_tipo(run_id, grafo.EVENTO_PLAN_HEREDADO)
        return evento["payload"]


# --- 1 — el plan varado se ejecuta sin volver a producirse ------------------


class HeredarUnPlanVerificado(BaseHerencia):
    def test_ejecuta_las_unidades_sin_producir_un_plan_nuevo(self):
        vieja = self.plan_varado()
        self.assertEqual(self.de_tipo(vieja, "unidad_lanzada"), [])

        nueva = self.heredar_y_ejecutar(vieja)

        self.assertTrue(self.de_tipo(nueva, "unidad_entregada"))
        # No hubo fase Requirement: no se produjo ningún plan en la heredera.
        self.assertEqual(self.de_tipo(nueva, "iteracion_producida"), [])
        self.assertEqual(self.de_tipo(nueva, "pedido_recibido"), [])

    def test_la_corrida_heredera_corre_bajo_la_definicion_del_developer(self):
        nueva = self.heredar_y_ejecutar(self.plan_varado())
        (iniciada,) = self.de_tipo(nueva, "run_iniciada")
        self.assertEqual(
            iniciada["payload"]["agent_definition_id"], "developer-agente-de-prueba"
        )


# --- 2 — las dos corridas quedan atadas en el registro ----------------------


class ElRegistroAtaLasDosCorridas(BaseHerencia):
    def test_declara_de_donde_vino_el_plan_y_de_que_veredicto_se_fia(self):
        vieja = self.plan_varado()
        nueva = self.heredar_y_ejecutar(vieja)
        hecho = self.hecho_heredado(nueva)

        self.assertEqual(hecho["de_corrida"], vieja)
        self.assertEqual(hecho["origen"], vieja)
        self.assertEqual(hecho["iteracion"], 1)

        # El veredicto del que nos fiamos existe y es el que dice válido.
        veredicto = [
            e for e in self.eventos(vieja) if e["id"] == hecho["veredicto_evento"]
        ]
        self.assertEqual(len(veredicto), 1)
        self.assertTrue(veredicto[0]["payload"]["valido"])

    def test_registra_con_que_modo_se_produjo_el_plan_original(self):
        """Sin esto no se puede leer después una entrega producida por otro modo."""
        nueva = self.heredar_y_ejecutar(self.plan_varado())
        hecho = self.hecho_heredado(nueva)
        self.assertEqual(hecho["modo_de_origen"], {"modo": "stub"})

        # Y el modo de la heredera es propio: son dos corridas, dos hechos.
        (modo,) = self.de_tipo(nueva, grafo.EVENTO_MODO)
        self.assertEqual(modo["payload"]["modo"], "stub")

    def test_el_pedido_viaja_copiado_para_que_la_corrida_se_lea_sola(self):
        nueva = self.heredar_y_ejecutar(self.plan_varado())
        (heredado,) = self.de_tipo(nueva, grafo.EVENTO_PEDIDO_HEREDADO)
        self.assertEqual(
            heredado["payload"]["que_se_quiere"], PEDIDO["que_se_quiere"]
        )
        self.assertEqual(
            heredado["payload"]["techo_costo_usd"], PEDIDO["techo_costo_usd"]
        )

    def test_declara_el_regimen_de_dos_gates_y_lo_cumple(self):
        vieja = self.plan_varado()
        nueva = self.heredar_y_ejecutar(vieja)
        (regimen,) = self.de_tipo(nueva, grafo.EVENTO_GATES)
        self.assertEqual(regimen["payload"]["gates"], ["entrada", "salida"])

        self.aprobar(nueva, "salida")
        codigo, _, error = self.cli("--reanudar", nueva, "--stub")
        self.assertEqual(codigo, 0, error)
        self.assertEqual(self.de_tipo(nueva, grafo.EVENTO_REGIMEN_INCUMPLIDO), [])
        (cerrada,) = self.de_tipo(nueva, "run_cerrada")
        self.assertEqual(cerrada["payload"]["resultado"], "entregado")


# --- 3 — el techo no se evade partiendo el trabajo --------------------------


class TechoHeredado(BaseHerencia):
    def test_se_descuenta_lo_que_el_plan_ya_gasto(self):
        vieja = self.plan_varado()
        gastado = presupuesto.consumo(self.store(), vieja)["costo"]
        self.assertGreater(gastado, 0)

        nueva = self.heredar_y_ejecutar(vieja)
        (efectivos,) = self.de_tipo(nueva, "techos_efectivos")
        self.assertAlmostEqual(
            efectivos["payload"]["costo"], PEDIDO["techo_costo_usd"] - gastado
        )

    def test_sin_techo_restante_se_niega_antes_de_gastar(self):
        """Si el techo se pudiera evadir partiendo el trabajo, no sería un techo."""
        vieja = self.plan_varado(dict(PEDIDO, techo_costo_usd=0.1))
        codigo, _, error = self.heredar(vieja)
        self.assertEqual(codigo, 1)
        self.assertIn("no queda techo", error.lower())
        self.assertEqual(self.store().eventos_de_tipo(grafo.EVENTO_PLAN_HEREDADO), [])

    def test_el_descuento_acumula_a_lo_largo_del_linaje(self):
        vieja = self.plan_varado()
        primera = self.heredar_y_ejecutar(vieja)
        segunda = self.heredar_y_ejecutar(vieja, "--reejecutar")

        gastado = cadena.gastado_en_el_linaje(self.store(), vieja)
        (efectivos,) = self.de_tipo(segunda, "techos_efectivos")
        # Lo de la segunda descuenta la producción del plan y la primera ejecución.
        self.assertLess(
            efectivos["payload"]["costo"], PEDIDO["techo_costo_usd"] - 0.1
        )
        self.assertGreater(gastado, 0.2)
        self.assertTrue(self.de_tipo(primera, "unidad_entregada"))


# --- 4 — reejecutar es un acto declarado ------------------------------------


class PlanYaEjecutado(BaseHerencia):
    def test_heredar_un_plan_que_ya_produjo_codigo_se_niega(self):
        vieja = self.plan_varado()
        primera = self.heredar_y_ejecutar(vieja)

        codigo, _, error = self.heredar(vieja)
        self.assertEqual(codigo, 1)
        self.assertIn("ya produjo código", error)
        self.assertIn(primera, error)

    def test_con_reejecutar_acepta_y_declara_a_cuales_sucede(self):
        vieja = self.plan_varado()
        primera = self.heredar_y_ejecutar(vieja)
        segunda = self.heredar_y_ejecutar(vieja, "--reejecutar")

        hecho = self.hecho_heredado(segunda)
        self.assertEqual(hecho["ejecuciones_previas"], [primera])
        self.assertTrue(hecho["reejecuta"])

    def test_heredar_de_una_heredera_resuelve_a_la_corrida_de_origen(self):
        vieja = self.plan_varado()
        primera = self.heredar_y_ejecutar(vieja)
        tercera = self.heredar_y_ejecutar(primera, "--reejecutar")

        hecho = self.hecho_heredado(tercera)
        self.assertEqual(hecho["de_corrida"], primera)
        self.assertEqual(hecho["origen"], vieja, "el linaje no resolvió a la raíz")


# --- 5 — lo que no se puede heredar -----------------------------------------


class NoHeredable(BaseHerencia):
    def test_una_corrida_sin_plan_verificado_se_niega(self):
        codigo, run_id, error = self.nueva("--solo-plan")
        self.assertEqual(codigo, 0, error)
        # Frenada en el Gate de entrada: todavía no produjo ni verificó nada.
        codigo, _, error = self.heredar(run_id)
        self.assertEqual(codigo, 1)
        self.assertIn("no tiene ningún plan verificado", error)

    def test_una_corrida_que_no_existe_se_niega(self):
        codigo, _, error = self.heredar("corrida-inventada")
        self.assertEqual(codigo, 1)
        self.assertIn("no tiene ningún plan verificado", error)


# --- 6 — la reanudación sabe que la corrida es heredera ---------------------


class ReanudarUnaHeredera(BaseHerencia):
    def test_no_vuelve_a_la_fase_requirement(self):
        """El grafo se rearma leyendo el registro, no los flags de la reanudación.

        Si se rearmara sin saberlo, aprobar el Gate de entrada mandaría a
        producir un plan sobre uno heredado.
        """
        vieja = self.plan_varado()
        codigo, nueva, error = self.heredar(vieja)
        self.assertEqual(codigo, 0, error)
        self.assertTrue(grafo.es_heredada(self.store(), nueva))

        self.aprobar(nueva, "entrada")
        codigo, _, error = self.cli("--reanudar", nueva, "--stub")
        self.assertEqual(codigo, 0, error)
        self.assertEqual(self.de_tipo(nueva, "iteracion_producida"), [])
        self.assertTrue(self.de_tipo(nueva, "unidad_entregada"))


# --- 7 — validaciones de uso -------------------------------------------------


class UsoDeLosFlags(BaseHerencia):
    def test_desde_corrida_exige_definicion_developer(self):
        codigo, _, error = self.cli("--desde-corrida", "x", "--stub")
        self.assertEqual(codigo, 2)
        self.assertIn("es para ejecutarlo", error)

    def test_no_se_combina_con_pedido_ni_con_solo_plan(self):
        for extra in (
            ("--pedido", "p.json"),
            ("--solo-plan",),
            ("--reanudar", "otra"),
        ):
            codigo, _, error = self.cli(
                "--desde-corrida", "x",
                "--definicion-developer", str(self.ruta_developer),
                "--stub", *extra,
            )
            self.assertEqual(codigo, 2, extra)
            self.assertIn("no se combina", error)

    def test_reejecutar_solo_tiene_sentido_heredando(self):
        codigo, _, error = self.nueva("--solo-plan", "--reejecutar")
        self.assertEqual(codigo, 2)
        self.assertIn("--desde-corrida", error)


if __name__ == "__main__":
    unittest.main(verbosity=2)
