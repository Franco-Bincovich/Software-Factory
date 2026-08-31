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


class CreacionDeCache(object):
    """El objeto anidado bajo `usage.cache_creation`, abierto por TTL."""

    def __init__(self, cinco_min=0, una_hora=0):
        self.ephemeral_5m_input_tokens = cinco_min
        self.ephemeral_1h_input_tokens = una_hora


class Uso(object):
    def __init__(self, entrada, salida, cache_creation=None):
        self.input_tokens = entrada
        self.output_tokens = salida
        if cache_creation is not None:
            self.cache_creation = cache_creation


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


class TablaDePrecios(unittest.TestCase):
    """Los precios son dato externo; lo que se puede fijar acá es lo verificado.

    Copiada a mano el 2026-08-30 de la tabla "Model pricing" de
    https://platform.claude.com/docs/en/about-claude/pricing. **Los números están
    escritos a mano a propósito.** Si se derivaran de las constantes del módulo,
    el test se verificaría a sí mismo y pasaría con cualquier precio.
    """

    #: modelo -> (entrada, escritura 5m, escritura 1h, lectura, salida), USD/MTok
    TABLA = {
        "claude-sonnet-5": (2.00, 2.50, 4.00, 0.20, 10.00),
        "claude-opus-5": (5.00, 6.25, 10.00, 0.50, 25.00),
        "claude-haiku-4-5": (1.00, 1.25, 2.00, 0.10, 5.00),
    }

    #: Qué contador del desglose corresponde a cada columna de la tabla.
    COLUMNAS = (
        ("input_tokens", 0),
        ("ephemeral_5m_input_tokens", 1),
        ("ephemeral_1h_input_tokens", 2),
        ("cache_read_input_tokens", 3),
        ("output_tokens", 4),
    )

    def test_se_declaran_los_mismos_modelos_que_se_verificaron(self):
        """Media tabla verificada es peor que ninguna: nadie sabe cuál mitad."""
        self.assertEqual(set(productor.PRECIOS_USD_POR_MTOK), set(self.TABLA))

    def test_un_millon_de_cada_contador_cuesta_lo_que_dice_la_tabla(self):
        """Cobra un contador por vez, no la suma de los cinco.

        La suma admite que dos errores se cancelen. Columna por columna, no.

        Es además el único test que ata los multiplicadores de caché al precio
        base: si alguien actualiza `PRECIOS_USD_POR_MTOK` y no toca
        `MULTIPLICADORES_DE_CACHE` —o al revés—, las tres columnas de caché
        dejan de dar y esto cae.
        """
        for modelo, fila in self.TABLA.items():
            for contador, columna in self.COLUMNAS:
                with self.subTest(modelo=modelo, contador=contador):
                    self.assertAlmostEqual(
                        costo_de({contador: 1_000_000}, modelo), fila[columna]
                    )


class CalculoDeCosto(unittest.TestCase):
    def test_sale_de_los_tokens_declarados_y_el_precio_del_modelo(self):
        # 1M de entrada a USD 2 y 1M de salida a USD 10 dan USD 12.
        self.assertAlmostEqual(
            costo_de({"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                     "claude-sonnet-5"),
            12.0,
        )
        # Los tres precios declarados son coherentes entre sí.
        for modelo, precio in productor.PRECIOS_USD_POR_MTOK.items():
            with self.subTest(modelo=modelo):
                self.assertGreater(precio["output"], precio["input"])

    def test_el_productor_devuelve_el_costo_medido(self):
        producir, _ = productor_con(Respuesta(json.dumps(PLAN), 30_000, 4_000))
        plan, consumo = producir(PEDIDO, None, [], CONTEXTO)
        self.assertEqual(plan, PLAN)
        # 30k * 2/1M + 4k * 10/1M = 0.06 + 0.04
        self.assertAlmostEqual(consumo["costo"], 0.10)


class CobroDelCache(unittest.TestCase):
    """Los cuatro contadores se cobran. Antes se cobraban dos y el techo mentía."""

    SIN_CACHE = {"input_tokens": 1_000, "output_tokens": 500}

    def costo(self, **extra):
        return costo_de(dict(self.SIN_CACHE, **extra), "claude-sonnet-5")

    def test_la_misma_llamada_con_cache_cuesta_mas_que_sin_cache(self):
        sin_cache = self.costo()
        # 1k * 2/1M + 500 * 10/1M
        self.assertAlmostEqual(sin_cache, 0.007)

        escritura = self.costo(
            cache_creation_input_tokens=20_000,
            ephemeral_5m_input_tokens=20_000,
        )
        # 20k a 1,25x sobre USD 2 = USD 0,05 más.
        self.assertAlmostEqual(escritura, sin_cache + 0.05)

        lectura = self.costo(cache_read_input_tokens=20_000)
        # 20k a 0,1x sobre USD 2 = USD 0,004 más.
        self.assertAlmostEqual(lectura, sin_cache + 0.004)

        self.assertGreater(escritura, lectura)
        self.assertGreater(lectura, sin_cache)

    def test_la_escritura_de_una_hora_cuesta_mas_que_la_de_cinco_minutos(self):
        """La tabla distingue los dos TTL, así que la fórmula también.

        Los mismos tokens, el mismo modelo, la misma llamada: sólo cambia cuánto
        dura el caché. Cobrarlos igual sería cobrar la mitad la mitad de las
        veces.
        """
        cinco_min = self.costo(
            cache_creation_input_tokens=20_000, ephemeral_5m_input_tokens=20_000
        )
        una_hora = self.costo(
            cache_creation_input_tokens=20_000, ephemeral_1h_input_tokens=20_000
        )
        # 1,25x contra 2x sobre los mismos 20k: USD 0,05 contra USD 0,08.
        self.assertAlmostEqual(una_hora - cinco_min, 0.03)

    def test_la_escritura_desglosada_no_se_cobra_dos_veces(self):
        """El campo plano es la suma de los dos TTL, no un tercer contador."""
        contadores = {
            "cache_creation_input_tokens": 20_000,
            "ephemeral_5m_input_tokens": 12_000,
            "ephemeral_1h_input_tokens": 8_000,
        }
        self.assertAlmostEqual(
            costo_de(contadores, "claude-sonnet-5"),
            (12_000 * 2 * 1.25 + 8_000 * 2 * 2) / 1_000_000,
        )

    def test_la_escritura_sin_desglose_se_cobra_a_cinco_minutos(self):
        """Los eventos viejos traen la suma sola. No es un supuesto prudente.

        Los `cache_control` de la fábrica no declaran `ttl`, y sin `ttl` la API
        cachea a 5 minutos: todo lo que está escrito en el registro es escritura
        de 5 minutos.
        """
        self.assertAlmostEqual(
            costo_de({"cache_creation_input_tokens": 20_000}, "claude-sonnet-5"),
            0.05,
        )


class EventosViejos(unittest.TestCase):
    """La fórmula nueva lee lo que escribió la vieja. No se migra nada."""

    def test_un_desglose_sin_los_campos_de_cache_se_cobra_sin_cache(self):
        # Es el payload exacto que dejaba la fórmula anterior: dos contadores.
        viejo = {"costo": 0.15, "modelo": "claude-sonnet-5",
                 "input_tokens": 30_000, "output_tokens": 4_000}
        self.assertAlmostEqual(costo_de(viejo, "claude-sonnet-5"), 0.10)

    def test_un_evento_sin_ningun_contador_no_cuesta_nada_y_no_falla(self):
        """Los stubs registran un número pelado, sin desglose que cobrar."""
        self.assertEqual(costo_de({}, "claude-sonnet-5"), 0.0)


class DesgloseDelConsumo(unittest.TestCase):
    """El desglose existe para poder explicar un costo, no sólo sumarlo."""

    def test_lleva_los_tokens_que_la_api_declaro_y_el_stop_reason(self):
        consumo = consumo_de(Uso(30_000, 4_000), "claude-sonnet-5", "end_turn")
        self.assertAlmostEqual(consumo["costo"], 0.10)
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

    def test_la_escritura_de_cache_queda_abierta_por_ttl(self):
        """Sin esto la fórmula no puede cobrar bien, porque los TTL valen distinto."""
        uso = Uso(1_000, 500, CreacionDeCache(cinco_min=12_000, una_hora=8_000))
        uso.cache_creation_input_tokens = 20_000
        consumo = consumo_de(uso, "claude-sonnet-5")

        self.assertEqual(consumo["ephemeral_5m_input_tokens"], 12_000)
        self.assertEqual(consumo["ephemeral_1h_input_tokens"], 8_000)
        # La suma plana se guarda igual: es lo que declara la API y lo único
        # comparable contra los eventos viejos.
        self.assertEqual(consumo["cache_creation_input_tokens"], 20_000)

    def test_el_costo_guardado_es_el_de_los_contadores_guardados(self):
        """El evento y el precio no pueden discrepar: se cobra el mismo dict."""
        uso = Uso(1_000, 500, CreacionDeCache(cinco_min=20_000))
        uso.cache_creation_input_tokens = 20_000
        consumo = consumo_de(uso, "claude-sonnet-5")

        contadores = {c: consumo[c] for c in consumo if c.endswith("_tokens")}
        self.assertAlmostEqual(consumo["costo"], costo_de(contadores, "claude-sonnet-5"))
        self.assertAlmostEqual(consumo["costo"], 0.057)

    def test_sin_cache_creation_no_se_inventan_los_ttl(self):
        consumo = consumo_de(Uso(10, 10), "claude-sonnet-5")
        self.assertNotIn("ephemeral_5m_input_tokens", consumo)
        self.assertNotIn("ephemeral_1h_input_tokens", consumo)


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
        # Las nueve reglas más la compuerta del esquema: el prompt nombra cada
        # identificador que el verificador puede devolver. La 0 aparece en
        # minúscula porque el prompt la presenta como compuerta, no como regla.
        for regla in range(10):
            self.assertIn("regla %d" % regla, sistema.lower())

        usuario = llamada["messages"][0]["content"]
        self.assertEqual(llamada["messages"][0]["role"], "user")
        self.assertIn(PEDIDO["que_se_quiere"], usuario)
        self.assertIn(PEDIDO["para_que"], usuario)
        self.assertIn("interfaz gráfica", usuario)
        # El texto contra el que T7 evalúa la regla 4 va literal.
        self.assertIn(PEDIDO["que_se_quiere"] + "\n" + PEDIDO["para_que"], usuario)


class FormaDelProcedimiento(unittest.TestCase):
    """Lo que el prompt enseña sobre `procedimiento`, que es la mitad no mecánica
    de ADR-021.

    La regla 9 sola sería un portón cerrado: siete de los ocho planes del
    registro tenían al menos un criterio que delega, así que sin esta enseñanza
    cada corrida entraría en un ciclo de rebotes. Y la regla rebota el plan
    entero, no el criterio.

    El texto del prompt está cortado a mano a 78 columnas en el fuente, así que
    las frases se buscan contra la versión de un solo renglón. Sin esto, una
    aserción sobre una frase que cruza un salto de línea falla estando el texto.
    """

    def setUp(self):
        producir, cliente = productor_con(Respuesta(json.dumps(PLAN)))
        producir(PEDIDO, None, [], CONTEXTO)
        self.corrido = " ".join(cliente.llamadas[0]["system"].split())

    def test_dice_la_forma_correcta_antes_que_la_prohibicion(self):
        forma = self.corrido.index("dice qué se invoca, con qué entrada")
        contra = self.corrido.index("Correr el comando de ejecución de pruebas")
        self.assertLess(forma, contra)

    def test_lleva_el_contraejemplo_de_la_delegacion(self):
        self.assertIn("Correr el comando de ejecución de pruebas del proyecto", self.corrido)
        self.assertIn("Ejecutar la suite y confirmar que termina sin fallos", self.corrido)

    def test_cierra_la_salida_por_perifrasis(self):
        """Prohibir el nombre no prohíbe la conducta: es lo que pasó con la 8."""
        self.assertIn("no alcanza con sacarle el nombre a la herramienta", self.corrido)
        self.assertIn("se ejecuta el archivo de verificación del proyecto", self.corrido)

    def test_no_le_prohibe_a_la_unidad_producir_pruebas(self):
        self.assertIn("Podés pedir un archivo de pruebas en `artefacto_esperado`", self.corrido)

    def test_la_regla_9_declara_que_mira_un_solo_campo(self):
        self.assertIn("Se mira **sólo** el `procedimiento`", self.corrido)


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
        self.assertEqual(
            capturado.exception.texto, "acá va el plan: enseguida lo escribo"
        )

    def test_respuesta_cortada_por_max_tokens_dice_que_quedo_cortada(self):
        producir, _ = productor_con(
            Respuesta('{"plan_id": "PLAN', stop_reason="max_tokens")
        )
        with self.assertRaises(RespuestaIlegible) as capturado:
            producir(PEDIDO, None, [], CONTEXTO)
        self.assertEqual(capturado.exception.motivo, "truncada")
        self.assertIn(str(productor.MAX_TOKENS), capturado.exception.detalle)
        # Y se lleva lo que alcanzó a escribir: es lo único que después permite
        # decir por qué no se pudo leer, y se descartaba en este mismo `raise`.
        self.assertEqual(capturado.exception.texto, '{"plan_id": "PLAN')

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
        self.assertAlmostEqual(capturado.exception.consumo["costo"], 0.02)


class SinContextoDelVault(unittest.TestCase):
    def test_no_produce_a_ciegas(self):
        producir, cliente = productor_con(Respuesta(json.dumps(PLAN)))
        with self.assertRaises(ProductorSinContexto) as capturado:
            producir(PEDIDO, None, [], {})
        self.assertIn("--vault", str(capturado.exception))
        self.assertEqual(cliente.llamadas, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
