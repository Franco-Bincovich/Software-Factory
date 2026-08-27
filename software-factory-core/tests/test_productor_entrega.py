"""Criterio de aceptación del productor real de Entregas.

Ningún test invoca al proveedor: se inyecta un cliente falso y se ejercita lo que
es nuestro —el prompt, el parseo, el costo y el tratamiento de fallos—. La
primera corrida contra el modelo real no se simula acá.
"""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import productor_entrega  # noqa: E402
import verificador_entrega  # noqa: E402
from grafo import FalloDeInfraestructura, UnidadAmbigua  # noqa: E402
from productor_entrega import (  # noqa: E402
    DeveloperSinContexto,
    EntregaNoParseable,
    ModeloSinPrecio,
    crear_productor,
    parsear_entrega,
)

UNIDAD = {
    "id": "U2",
    "enunciado": "Validar que un legajo tenga exactamente cuatro dígitos",
    "criterios": [
        {
            "condicion_observable": "Dado el valor \"4471\", `validarLegajo` devuelve válido",
            "resultado_esperado": "`valido` es true y `motivo` es null",
            "procedimiento": "Se abre pruebas.html y se cuenta la fila en verde",
        }
    ],
    "dependencias": ["U1"],
    "rastreo": "validar el legajo",
    "artefacto_esperado": "src/validar-legajo.js con sus pruebas",
}

UNIDAD_VECINA = {
    "id": "U7",
    "enunciado": "ENUNCIADO DE UNA UNIDAD QUE NO LE TOCA AL DEVELOPER",
    "criterios": [],
    "dependencias": [],
    "rastreo": "",
    "artefacto_esperado": "",
}

CONTEXTO_UNIDADES = [
    {
        "unidad": {
            "id": "U1",
            "enunciado": "Leer el archivo de altas",
            "criterios": [],
            "dependencias": [],
            "rastreo": "",
            "artefacto_esperado": "src/leer.js",
        },
        "entrega": {
            "unidad": "U1",
            "archivos": [
                {"ruta": "src/leer.js", "rol": "artefacto_esperado", "contenido": "function leer() {}"}
            ],
            "supuestos": [],
        },
    }
]

CONTEXTO_VAULT = {
    "03 - Agent Framework/Contrato de Entrega del Developer.md": "La entrega es inmutable.",
    "06 - Standards/Ruleset mecanico.md": "R1 — límites de tamaño.",
}

ENTREGA = {
    "unidad": "U2",
    "archivos": [
        {"ruta": "src/validar-legajo.js", "rol": "artefacto_esperado", "contenido": "function validarLegajo() {}"}
    ],
    "supuestos": [],
}

INCUMPLIMIENTOS = [
    {"regla": "C6", "archivo": None, "detalle": "Falta demo.html."},
    {"regla": "C7", "archivo": "demo.html", "detalle": "Reimplementa la lógica."},
]


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


class Flujo(object):
    """El contexto que devuelve `messages.stream`, con la superficie que se usa."""

    def __init__(self, respuesta):
        self._respuesta = respuesta

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get_final_message(self):
        return self._respuesta


class ClienteFalso(object):
    """Cliente mínimo con la superficie que el productor usa: `messages.stream`."""

    def __init__(self, respuesta=None, error=None):
        self.messages = self
        self._respuesta = respuesta
        self._error = error
        self.llamadas = []

    def stream(self, **kwargs):
        self.llamadas.append(kwargs)
        if self._error is not None:
            raise self._error
        return Flujo(self._respuesta)


def productor_con(respuesta=None, error=None, modelo="claude-sonnet-5"):
    cliente = ClienteFalso(respuesta=respuesta, error=error)
    return crear_productor("clave-de-prueba", modelo, None, cliente), cliente


def producir(cliente_kwargs=None, **kwargs):
    """Corre el productor con los argumentos por defecto de estos tests."""
    produccion, cliente = productor_con(**(cliente_kwargs or {}))
    resultado = produccion(
        kwargs.get("unidad", UNIDAD),
        kwargs.get("contexto_unidades", CONTEXTO_UNIDADES),
        kwargs.get("entrega_anterior"),
        kwargs.get("incumplimientos", []),
        kwargs.get("contexto_vault", CONTEXTO_VAULT),
    )
    return resultado, cliente


# --- 1 — el modelo tiene que tener precio -----------------------------------


class ModeloDesconocido(unittest.TestCase):
    def test_no_se_crea_un_productor_sin_precio_declarado(self):
        with self.assertRaises(ModeloSinPrecio) as capturado:
            crear_productor("clave", "modelo-inventado", None, ClienteFalso())
        self.assertIn("modelo-inventado", str(capturado.exception))


# --- 2 — costo ---------------------------------------------------------------


class CalculoDeCosto(unittest.TestCase):
    def test_sale_de_los_tokens_declarados_y_del_precio(self):
        respuesta = Respuesta(json.dumps(ENTREGA), entrada=20000, salida=6000)
        (entrega, costo), _ = producir({"respuesta": respuesta})
        # Sonnet 5 declarado a 3/15 por millón.
        esperado = (20000 * 3.00 + 6000 * 15.00) / 1_000_000
        self.assertAlmostEqual(costo, esperado)
        self.assertEqual(entrega["unidad"], "U2")


# --- 3 — prompt inicial ------------------------------------------------------


class PromptInicial(unittest.TestCase):
    def setUp(self):
        (self.entrega, _), self.cliente = producir(
            {"respuesta": Respuesta(json.dumps(ENTREGA))}
        )
        self.llamada = self.cliente.llamadas[0]
        self.sistema = self.llamada["system"][0]["text"]
        self.mensaje = self.llamada["messages"][0]["content"]

    def test_lleva_la_unidad_con_sus_criterios(self):
        self.assertIn("U2", self.mensaje)
        self.assertIn(UNIDAD["enunciado"], self.mensaje)
        self.assertIn("validarLegajo", self.mensaje)
        self.assertIn("Se abre pruebas.html", self.mensaje)

    def test_lleva_las_dependencias_como_contexto_de_lectura(self):
        self.assertIn("Unidad U1", self.mensaje)
        self.assertIn("function leer()", self.mensaje)
        self.assertIn("contexto de lectura", self.mensaje)
        self.assertIn("No las modifiques", self.mensaje)

    def test_nunca_lleva_el_plan_completo(self):
        """La unidad vecina no viaja: el Developer no ve el plan entero."""
        self.assertNotIn(UNIDAD_VECINA["enunciado"], self.mensaje)
        self.assertNotIn(UNIDAD_VECINA["enunciado"], self.sistema)
        self.assertNotIn("U7", self.mensaje)

    def test_el_sistema_lleva_vault_esquema_entregables_y_forma(self):
        for documento, contenido in CONTEXTO_VAULT.items():
            self.assertIn(documento, self.sistema)
            self.assertIn(contenido, self.sistema)
        self.assertIn("artefacto_esperado", self.sistema)
        self.assertIn("pruebas.html", self.sistema)
        self.assertIn("demo.html", self.sistema)
        self.assertIn("El primer carácter de", self.sistema)

    def test_el_sistema_dice_que_no_verifica_su_propio_trabajo(self):
        self.assertIn("no declarás si tus pruebas pasan", self.sistema)

    def test_el_sistema_explica_la_entrega_vacia(self):
        self.assertIn("No adivines", self.sistema)


# --- 4 — el prompt no se desvía del verificador ------------------------------


class AntiDeriva(unittest.TestCase):
    def test_el_prompt_nombra_cada_regla_que_el_verificador_puede_emitir(self):
        """Si el verificador gana una regla, el prompt tiene que nombrarla.

        Sin esto el prompt y el verificador se separan en silencio: el modelo
        produce contra reglas que ya no son las que lo rechazan.
        """
        texto = productor_entrega.REGLAS_DEL_VERIFICADOR
        faltantes = [regla for regla in verificador_entrega.REGLAS if regla not in texto]
        self.assertEqual(faltantes, [], "el prompt no nombra: %s" % faltantes)


# --- 5 — prompt de corrección ------------------------------------------------


class PromptDeCorreccion(unittest.TestCase):
    def test_lleva_la_entrega_anterior_y_cada_incumplimiento_con_su_id(self):
        (_, _), cliente = producir(
            {"respuesta": Respuesta(json.dumps(ENTREGA))},
            entrega_anterior=ENTREGA,
            incumplimientos=INCUMPLIMIENTOS,
        )
        mensaje = cliente.llamadas[0]["messages"][0]["content"]

        self.assertIn("fue rechazada por el verificador", mensaje)
        self.assertIn("C6", mensaje)
        self.assertIn("Falta demo.html.", mensaje)
        self.assertIn("C7", mensaje)
        self.assertIn("archivo demo.html", mensaje)
        self.assertIn("src/validar-legajo.js", mensaje)

    def test_pide_corregir_y_prohibe_regenerar(self):
        (_, _), cliente = producir(
            {"respuesta": Respuesta(json.dumps(ENTREGA))},
            entrega_anterior=ENTREGA,
            incumplimientos=INCUMPLIMIENTOS,
        )
        mensaje = cliente.llamadas[0]["messages"][0]["content"]
        self.assertIn("no toques nada más", mensaje)
        self.assertIn("vuelve **idéntico**", mensaje)
        self.assertIn("Regenerar la entrega desde cero", mensaje)

    def test_sin_entrega_previa_util_vuelve_a_producir_en_vez_de_corregir(self):
        """La entrega vacía que deja una iteración no parseable no es corregible."""
        (_, _), cliente = producir(
            {"respuesta": Respuesta(json.dumps(ENTREGA))},
            entrega_anterior={},
            incumplimientos=INCUMPLIMIENTOS,
        )
        mensaje = cliente.llamadas[0]["messages"][0]["content"]
        self.assertIn("Producí la Entrega para esta unidad", mensaje)
        self.assertNotIn("fue rechazada por el verificador", mensaje)


# --- 6 — la llamada ----------------------------------------------------------


class FormaDeLaLlamada(unittest.TestCase):
    def setUp(self):
        (_, _), self.cliente = producir({"respuesta": Respuesta(json.dumps(ENTREGA))})
        self.llamada = self.cliente.llamadas[0]

    def test_el_system_prompt_va_cacheado(self):
        """Es el prefijo estable de todas las llamadas de todas las unidades."""
        (bloque,) = self.llamada["system"]
        self.assertEqual(bloque["cache_control"], {"type": "ephemeral"})
        self.assertEqual(bloque["type"], "text")

    def test_el_techo_de_salida_alcanza_para_cuatro_archivos(self):
        self.assertEqual(self.llamada["max_tokens"], productor_entrega.MAX_TOKENS)
        self.assertGreaterEqual(productor_entrega.MAX_TOKENS, 32000)

    def test_se_invoca_por_streaming(self):
        """El SDK exige streaming para techos de salida altos."""
        self.assertFalse(hasattr(self.cliente, "_uso_create"))
        self.assertEqual(len(self.cliente.llamadas), 1)


# --- 7 — parseo --------------------------------------------------------------


class Parseo(unittest.TestCase):
    def test_acepta_json_pelado_y_json_entre_cercas(self):
        pelado = json.dumps(ENTREGA)
        self.assertEqual(parsear_entrega(pelado), ENTREGA)
        self.assertEqual(parsear_entrega("```json\n%s\n```" % pelado), ENTREGA)
        self.assertEqual(parsear_entrega("```\n%s\n```" % pelado), ENTREGA)

    def test_rechaza_lo_que_no_es_un_objeto_json(self):
        with self.assertRaises(EntregaNoParseable):
            parsear_entrega("no soy json")
        with self.assertRaises(EntregaNoParseable):
            parsear_entrega("[1, 2, 3]")


# --- 8 — respuesta inutilizable ---------------------------------------------


class RespuestaInutilizable(unittest.TestCase):
    def test_json_invalido_devuelve_entrega_vacia_con_su_costo(self):
        (entrega, costo), _ = producir({"respuesta": Respuesta("perdón, no puedo")})
        self.assertEqual(entrega, {})
        self.assertGreater(costo, 0)

    def test_respuesta_cortada_por_max_tokens_tambien(self):
        respuesta = Respuesta('{"unidad": "U2", "archi', stop_reason="max_tokens")
        (entrega, costo), _ = producir({"respuesta": respuesta})
        self.assertEqual(entrega, {})
        self.assertGreater(costo, 0)

    def test_la_entrega_vacia_de_una_iteracion_mala_la_rechaza_el_verificador(self):
        veredicto = verificador_entrega.verificar({}, {"unidades": [UNIDAD]})
        self.assertFalse(veredicto["valido"])
        self.assertEqual({i["regla"] for i in veredicto["incumplimientos"]}, {"C0"})


# --- 9 — fallos que escalan --------------------------------------------------


class FallosQueEscalan(unittest.TestCase):
    def test_un_error_de_la_api_escala_en_vez_de_reintentar(self):
        from anthropic import APIError

        error = APIError("cayó la red", request=None, body=None)
        with self.assertRaises(FalloDeInfraestructura) as capturado:
            producir({"error": error})
        self.assertIn("no respondió", str(capturado.exception))

    def test_un_rechazo_por_politicas_escala_llevando_el_costo_consumido(self):
        respuesta = Respuesta("", stop_reason="refusal")
        with self.assertRaises(FalloDeInfraestructura) as capturado:
            producir({"respuesta": respuesta})
        self.assertIn("políticas de contenido", str(capturado.exception))
        self.assertGreater(capturado.exception.costo, 0)


# --- 10 — la unidad ambigua no se corrige, escala ---------------------------


class EntregaVacia(unittest.TestCase):
    def test_una_entrega_sin_archivos_con_motivo_escala(self):
        vacia = {
            "unidad": "U2",
            "archivos": [],
            "supuestos": ["La unidad se contradice con U1: pide validar y no validar."],
        }
        with self.assertRaises(UnidadAmbigua) as capturado:
            producir({"respuesta": Respuesta(json.dumps(vacia))})
        self.assertIn("se contradice", capturado.exception.motivo)
        self.assertGreater(capturado.exception.costo, 0)

    def test_sin_motivo_declarado_escala_igual_y_lo_dice(self):
        vacia = {"unidad": "U2", "archivos": [], "supuestos": []}
        with self.assertRaises(UnidadAmbigua) as capturado:
            producir({"respuesta": Respuesta(json.dumps(vacia))})
        self.assertIn("sin motivo declarado", capturado.exception.motivo)


# --- 11 — sin contexto del Vault no se produce ------------------------------


class SinContextoDelVault(unittest.TestCase):
    def test_no_produce_a_ciegas(self):
        with self.assertRaises(DeveloperSinContexto) as capturado:
            producir({"respuesta": Respuesta(json.dumps(ENTREGA))}, contexto_vault={})
        self.assertIn("vault_lectura", str(capturado.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
