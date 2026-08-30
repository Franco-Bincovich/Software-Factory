"""Criterio de aceptación del productor real.

Ningún test invoca al proveedor: se inyecta un cliente falso y se ejercita lo
que es nuestro —el prompt, el parseo, el costo y el tratamiento de fallos—. La
primera corrida contra el modelo real es T15 y no se simula acá.
"""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import productor  # noqa: E402
from grafo import FalloDeInfraestructura, RespuestaIlegible  # noqa: E402
from productor import (  # noqa: E402
    ModeloSinPrecio,
    PlanNoParseable,
    ProductorSinContexto,
    consumo_de,
    costo_de,
    crear_productor,
    parsear_plan,
)

PEDIDO = {
    "que_se_quiere": "Herramienta que lee un CSV de altas y reporta filas no importables",
    "para_que": "Evitar revisar el archivo a mano antes de cada importación",
    "alcance_excluido": ["interfaz gráfica"],
    "techo_costo_usd": 2,
    "techo_tiempo_min": 20,
    "techo_iteraciones": 5,
}

CONTEXTO = {
    "03 - Agent Framework/Contrato del Plan de Trabajo.md": "El plan es inmutable.",
    "08 - ADR/ADR-001 - Glosario canonico.md": "Plan de Trabajo — la salida del agente.",
}

PLAN = {"plan_id": "PLAN-1", "unidades": []}


# --- dobles de la API -------------------------------------------------------


class Uso(object):
    def __init__(self, entrada, salida):
        self.input_tokens = entrada
        self.output_tokens = salida


class Bloque(object):
    def __init__(self, texto):
        self.type = "text"
        self.text = texto


class Respuesta(object):
    def __init__(self, texto, entrada=1000, salida=2000, stop_reason="end_turn"):
        self.content = [Bloque(texto)]
        self.usage = Uso(entrada, salida)
        self.stop_reason = stop_reason


class ClienteFalso(object):
    """Cliente mínimo con la superficie que el productor usa: `messages.create`."""

    def __init__(self, respuesta=None, error=None):
        self.messages = self
        self._respuesta = respuesta
        self._error = error
        self.llamadas = []

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._respuesta


def productor_con(respuesta=None, error=None, modelo="claude-sonnet-5"):
    cliente = ClienteFalso(respuesta, error)
    return crear_productor("clave-de-prueba", modelo, "/vault", cliente), cliente


# --- precio -----------------------------------------------------------------


class ModeloDesconocido(unittest.TestCase):
    def test_no_se_crea_un_productor_sin_precio_declarado(self):
        with self.assertRaises(ModeloSinPrecio) as capturado:
            crear_productor("clave", "modelo-inventado", "/vault", ClienteFalso())
        self.assertIn("no tiene precio declarado", str(capturado.exception))


class CalculoDeCosto(unittest.TestCase):
    def test_sale_de_los_tokens_declarados_y_el_precio_del_modelo(self):
        # 1M de entrada a USD 3 y 1M de salida a USD 15 dan USD 18.
        self.assertAlmostEqual(
            costo_de(Uso(1_000_000, 1_000_000), "claude-sonnet-5"), 18.0
        )
        # Los tres precios declarados son coherentes entre sí.
        for modelo, precio in productor.PRECIOS_USD_POR_MTOK.items():
            with self.subTest(modelo=modelo):
                self.assertGreater(precio["output"], precio["input"])

    def test_el_productor_devuelve_el_costo_medido(self):
        producir, _ = productor_con(Respuesta(json.dumps(PLAN), 30_000, 4_000))
        plan, consumo = producir(PEDIDO, None, [], CONTEXTO)
        self.assertEqual(plan, PLAN)
        # 30k * 3/1M + 4k * 15/1M = 0.09 + 0.06
        self.assertAlmostEqual(consumo["costo"], 0.15)


class DesgloseDelConsumo(unittest.TestCase):
    """El desglose existe para poder explicar un costo, no sólo sumarlo."""

    def test_lleva_los_tokens_que_la_api_declaro_y_el_stop_reason(self):
        consumo = consumo_de(Uso(30_000, 4_000), "claude-sonnet-5", "end_turn")
        self.assertAlmostEqual(consumo["costo"], 0.15)
        self.assertEqual(consumo["modelo"], "claude-sonnet-5")
        self.assertEqual(consumo["input_tokens"], 30_000)
        self.assertEqual(consumo["output_tokens"], 4_000)
        self.assertEqual(consumo["stop_reason"], "end_turn")

    def test_lo_que_la_api_no_manda_no_se_inventa(self):
        """Un campo ausente y un campo en cero dicen cosas distintas."""
        consumo = consumo_de(Uso(10, 10), "claude-sonnet-5")
        self.assertNotIn("thinking_tokens", consumo)
        self.assertNotIn("cache_read_input_tokens", consumo)
        self.assertNotIn("stop_reason", consumo)

    def test_el_cero_declarado_si_se_guarda(self):
        uso = Uso(10, 10)
        uso.cache_read_input_tokens = 0
        self.assertEqual(consumo_de(uso, "claude-sonnet-5")["cache_read_input_tokens"], 0)


# --- prompt -----------------------------------------------------------------


class PromptInicial(unittest.TestCase):
    def test_lleva_contrato_esquema_reglas_y_texto_rastreable(self):
        producir, cliente = productor_con(Respuesta(json.dumps(PLAN)))
        producir(PEDIDO, None, [], CONTEXTO)

        llamada = cliente.llamadas[0]
        self.assertEqual(llamada["model"], "claude-sonnet-5")
        self.assertEqual(llamada["max_tokens"], productor.MAX_TOKENS)
        # Sin parámetros de muestreo: Sonnet 5 los rechaza.
        for prohibido in ("temperature", "top_p", "top_k"):
            self.assertNotIn(prohibido, llamada)

        sistema = llamada["system"]
        for ruta, contenido in CONTEXTO.items():
            self.assertIn(ruta, sistema)
            self.assertIn(contenido, sistema)
        self.assertIn("plan-de-trabajo", json.dumps(productor.cargar_esquema()))
        self.assertIn("alcance_excluido", sistema)
        # Las siete reglas más la compuerta del esquema: el prompt nombra cada
        # identificador que el verificador puede devolver. La 0 aparece en
        # minúscula porque el prompt la presenta como compuerta, no como regla.
        for regla in range(8):
            self.assertIn("regla %d" % regla, sistema.lower())

        usuario = llamada["messages"][0]["content"]
        self.assertEqual(llamada["messages"][0]["role"], "user")
        self.assertIn(PEDIDO["que_se_quiere"], usuario)
        self.assertIn(PEDIDO["para_que"], usuario)
        self.assertIn("interfaz gráfica", usuario)
        # El texto contra el que T7 evalúa la regla 4 va literal.
        self.assertIn(PEDIDO["que_se_quiere"] + "\n" + PEDIDO["para_que"], usuario)


class PromptDeCorreccion(unittest.TestCase):
    def test_lleva_el_plan_anterior_y_cada_incumplimiento(self):
        incumplimientos = [
            {"regla": 1, "unidad": "U1", "criterio": None, "detalle": "sin criterios."},
            {"regla": 2, "unidad": "U2", "criterio": 0, "detalle": "falta procedimiento."},
        ]
        producir, cliente = productor_con(Respuesta(json.dumps(PLAN)))
        producir(PEDIDO, {"plan_id": "PLAN-0"}, incumplimientos, CONTEXTO)

        usuario = cliente.llamadas[0]["messages"][0]["content"]
        self.assertIn("PLAN-0", usuario)
        self.assertIn("Regla 1", usuario)
        self.assertIn("unidad U1", usuario)
        self.assertIn("sin criterios.", usuario)
        self.assertIn("Regla 2", usuario)
        self.assertIn("criterio 0", usuario)
        self.assertIn("falta procedimiento.", usuario)
        # Corregir, no regenerar: lo exige el campo 9 de la Agent Definition.
        self.assertIn("no toques nada más", usuario)
        self.assertIn("agotamiento", usuario)

    def test_sin_plan_previo_util_vuelve_a_producir_en_vez_de_corregir(self):
        producir, cliente = productor_con(Respuesta(json.dumps(PLAN)))
        producir(PEDIDO, {}, [{"regla": 0, "detalle": "x", "unidad": None, "criterio": None}], CONTEXTO)
        usuario = cliente.llamadas[0]["messages"][0]["content"]
        self.assertIn("Producí el Plan de Trabajo", usuario)
        self.assertNotIn("fue rechazado", usuario)


# --- respuesta --------------------------------------------------------------


class Parseo(unittest.TestCase):
    def test_acepta_json_pelado_y_json_entre_cercas(self):
        self.assertEqual(parsear_plan('{"a": 1}'), {"a": 1})
        self.assertEqual(parsear_plan('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(parsear_plan('```\n{"a": 1}\n```'), {"a": 1})

    def test_rechaza_lo_que_no_es_un_objeto_json(self):
        for crudo in ("no soy json", "[1, 2]", ""):
            with self.subTest(crudo=crudo):
                with self.assertRaises(PlanNoParseable):
                    parsear_plan(crudo)


class RespuestaInutilizable(unittest.TestCase):
    """No es un fallo de la fábrica: es una iteración mala, y se cobra.

    Antes devolvía el plan vacío y el registro no distinguía por qué. Ahora la
    causa viaja en `motivo`, y el consumo ya pagado viaja con ella.
    """

    def test_json_invalido_dice_que_no_se_pudo_parsear(self):
        producir, _ = productor_con(Respuesta("acá va el plan: enseguida lo escribo"))
        with self.assertRaises(RespuestaIlegible) as capturado:
            producir(PEDIDO, None, [], CONTEXTO)
        self.assertEqual(capturado.exception.motivo, "no_parseable")
        self.assertGreater(capturado.exception.consumo["costo"], 0)

    def test_respuesta_cortada_por_max_tokens_dice_que_quedo_cortada(self):
        producir, _ = productor_con(
            Respuesta('{"plan_id": "PLAN', stop_reason="max_tokens")
        )
        with self.assertRaises(RespuestaIlegible) as capturado:
            producir(PEDIDO, None, [], CONTEXTO)
        self.assertEqual(capturado.exception.motivo, "truncada")
        self.assertIn(str(productor.MAX_TOKENS), capturado.exception.detalle)

    def test_las_dos_causas_no_se_confunden(self):
        """Truncada y no parseable son fallas distintas y se cuentan distinto."""
        cortada, _ = productor_con(Respuesta("{", stop_reason="max_tokens"))
        ilegible, _ = productor_con(Respuesta("{"))
        motivos = []
        for producir in (cortada, ilegible):
            with self.assertRaises(RespuestaIlegible) as capturado:
                producir(PEDIDO, None, [], CONTEXTO)
            motivos.append(capturado.exception.motivo)
        self.assertEqual(motivos, ["truncada", "no_parseable"])

    def test_el_plan_vacio_lo_rechaza_t7_por_la_regla_0(self):
        from verificador import verificar

        veredicto = verificar({}, "cualquier pedido")
        self.assertFalse(veredicto["valido"])
        self.assertTrue(all(i["regla"] == 0 for i in veredicto["incumplimientos"]))


# --- fallos -----------------------------------------------------------------


class FallosDeInfraestructura(unittest.TestCase):
    def test_un_error_de_la_api_escala_en_vez_de_reintentar(self):
        from anthropic import APIError

        error = APIError("se cayó la red", request=None, body=None)
        producir, _ = productor_con(error=error)
        with self.assertRaises(FalloDeInfraestructura) as capturado:
            producir(PEDIDO, None, [], CONTEXTO)
        self.assertIn("no respondió", str(capturado.exception))

    def test_un_rechazo_por_politicas_escala_llevando_el_costo_consumido(self):
        producir, _ = productor_con(Respuesta("", 10_000, 0, stop_reason="refusal"))
        with self.assertRaises(FalloDeInfraestructura) as capturado:
            producir(PEDIDO, None, [], CONTEXTO)
        self.assertIn("políticas de contenido", str(capturado.exception))
        self.assertAlmostEqual(capturado.exception.consumo["costo"], 0.03)


class SinContextoDelVault(unittest.TestCase):
    def test_no_produce_a_ciegas(self):
        producir, cliente = productor_con(Respuesta(json.dumps(PLAN)))
        with self.assertRaises(ProductorSinContexto) as capturado:
            producir(PEDIDO, None, [], {})
        self.assertIn("--vault", str(capturado.exception))
        self.assertEqual(cliente.llamadas, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
