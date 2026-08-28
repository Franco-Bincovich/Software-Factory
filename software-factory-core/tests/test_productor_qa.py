"""Criterio de aceptación del productor de casos de prueba del QA Agent.

Ningún test invoca al proveedor: se inyecta un cliente falso y se ejercita lo que
es nuestro —el prompt, el parseo, el costo y el tratamiento de fallos—.

Lo que **no** se prueba acá es el límite del punto 3 de ADR-018. Ese límite no
vive en este módulo: el prompt lo explica para no gastar tokens en casos que se
van a descartar, pero la garantía está en `verificacion_sustantiva` y se prueba
en `test_verificacion_sustantiva`. Afirmar acá que el prompt contiene la
instrucción es afirmar que se le pidió, no que se cumpla.
"""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import productor_qa  # noqa: E402
from grafo import FalloDeInfraestructura  # noqa: E402
from productor_qa import (  # noqa: E402
    CasosNoParseables,
    ModeloSinPrecio,
    QASinContexto,
    crear_productor,
    parsear_casos,
)

UNIDAD = {
    "id": "U2",
    "enunciado": "Validar que un legajo tenga exactamente cuatro dígitos",
    "criterios": [
        {
            "condicion_observable": 'Dado "4471", `validarLegajo` devuelve válido',
            "resultado_esperado": "`valido` es true y `motivo` es null",
            "procedimiento": "Se ejecuta la función y se mira el objeto devuelto",
        },
        {
            "condicion_observable": 'Dado "44", `validarLegajo` devuelve inválido',
            "resultado_esperado": "`valido` es false",
            "procedimiento": "Se abre pruebas.html y se cuenta la fila en verde",
        },
    ],
    "dependencias": [],
    "rastreo": "validar el legajo",
    "artefacto_esperado": "src/validar-legajo.js",
}

PLAN = {
    "plan_id": "P1",
    "unidades": [UNIDAD],
    "fuera_de_alcance": ["Autenticación de usuarios"],
    "restricciones": {"alcance_excluido": ["Persistencia en base de datos"]},
}

ENTREGA = {
    "unidad": "U2",
    "archivos": [
        {
            "ruta": "src/validar-legajo.js",
            "rol": "artefacto_esperado",
            "contenido": "function validarLegajo() {}",
        }
    ],
    "supuestos": [],
}

DEPOSITO = "/estado/trabajo/abc123/U2/iteracion-1"

CONTEXTO_VAULT = {
    "03 - Agent Framework/Contrato de Entrega del Developer.md": "La entrega es inmutable.",
    "08 - ADR/ADR-016 - Frontera de ejecucion.md": "Sin red, sin filesystem afuera.",
}

CASOS = [
    {
        "criterio": 1,
        "archivo": "src/validar-legajo.js",
        "procedimiento": "Legajo válido de cuatro dígitos",
        "expresion": 'console.log(require("./src/validar-legajo.js")("4471").valido)',
        "espera": "true",
    }
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
    def __init__(self, respuesta):
        self._respuesta = respuesta

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get_final_message(self):
        return self._respuesta


class ClienteFalso(object):
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


def producir(cliente_kwargs=None, **kwargs):
    cliente = ClienteFalso(**(cliente_kwargs or {}))
    produccion = crear_productor("clave-de-prueba", "claude-sonnet-5", None, cliente)
    resultado = produccion(
        kwargs.get("unidad", UNIDAD),
        kwargs.get("plan", PLAN),
        kwargs.get("entrega", ENTREGA),
        kwargs.get("deposito", DEPOSITO),
        kwargs.get("contexto_vault", CONTEXTO_VAULT),
    )
    return resultado, cliente


# --- 1 — el modelo tiene que tener precio -----------------------------------


class ModeloDesconocido(unittest.TestCase):
    def test_no_se_crea_un_productor_sin_precio_declarado(self):
        with self.assertRaises(ModeloSinPrecio) as capturado:
            crear_productor("clave", "modelo-inventado", None, ClienteFalso())
        self.assertIn("modelo-inventado", str(capturado.exception))


# --- 2 — el contexto del Vault es obligatorio -------------------------------


class SinContexto(unittest.TestCase):
    """ADR-014 punto 4: un agente sin lo que necesita no falla, inventa."""

    def test_sin_documentos_del_vault_no_produce(self):
        with self.assertRaises(QASinContexto):
            producir(contexto_vault={})

    def test_el_error_dice_como_arreglarlo(self):
        with self.assertRaises(QASinContexto) as capturado:
            producir(contexto_vault=None)
        self.assertIn("--vault", str(capturado.exception))

    def test_no_se_llama_al_modelo(self):
        cliente = ClienteFalso(respuesta=Respuesta(json.dumps({"casos": CASOS})))
        produccion = crear_productor("clave", "claude-sonnet-5", None, cliente)
        with self.assertRaises(QASinContexto):
            produccion(UNIDAD, PLAN, ENTREGA, DEPOSITO, {})
        self.assertEqual(cliente.llamadas, [])


# --- 3 — costo ---------------------------------------------------------------


class CalculoDeCosto(unittest.TestCase):
    def test_sale_de_los_tokens_declarados_y_del_precio(self):
        respuesta = Respuesta(json.dumps({"casos": CASOS}), entrada=20000, salida=6000)
        (casos, costo), _ = producir({"respuesta": respuesta})
        esperado = (20000 * 3.00 + 6000 * 15.00) / 1_000_000
        self.assertAlmostEqual(costo, esperado)
        self.assertEqual(len(casos), 1)


# --- 4 — el prompt -----------------------------------------------------------


class Prompt(unittest.TestCase):
    def setUp(self):
        (self.casos, _), self.cliente = producir(
            {"respuesta": Respuesta(json.dumps({"casos": CASOS}))}
        )
        self.llamada = self.cliente.llamadas[0]
        self.sistema = self.llamada["system"][0]["text"]
        self.mensaje = self.llamada["messages"][0]["content"]

    def test_el_prefijo_estable_se_cachea(self):
        self.assertEqual(
            self.llamada["system"][0]["cache_control"], {"type": "ephemeral"}
        )

    def test_el_sistema_lleva_los_documentos_del_vault(self):
        for ruta, contenido in CONTEXTO_VAULT.items():
            self.assertIn(ruta, self.sistema)
            self.assertIn(contenido, self.sistema)

    def test_el_sistema_declara_la_frontera_de_adr_016(self):
        self.assertIn("Sin red", self.sistema)
        self.assertIn("Sin instalar nada", self.sistema)

    def test_los_criterios_van_numerados_desde_uno(self):
        # El número es lo que el caso cita en `criterio`. Si el mensaje no los
        # numera, el anclaje no tiene contra qué resolverse.
        self.assertIn("**Criterio 1**", self.mensaje)
        self.assertIn("**Criterio 2**", self.mensaje)
        self.assertNotIn("**Criterio 3**", self.mensaje)

    def test_lo_excluido_del_plan_va_en_el_mensaje(self):
        self.assertIn("Autenticación de usuarios", self.mensaje)
        self.assertIn("Persistencia en base de datos", self.mensaje)

    def test_el_deposito_y_sus_archivos_van_en_el_mensaje(self):
        self.assertIn(DEPOSITO, self.mensaje)
        self.assertIn("src/validar-legajo.js", self.mensaje)

    def test_el_mensaje_no_lleva_unidades_ajenas(self):
        otra = dict(PLAN, unidades=[UNIDAD, {"id": "U9", "enunciado": "AJENA"}])
        (_, _), cliente = producir(
            {"respuesta": Respuesta(json.dumps({"casos": CASOS}))}, plan=otra
        )
        self.assertNotIn("AJENA", cliente.llamadas[0]["messages"][0]["content"])

    def test_el_plan_sin_exclusiones_lo_dice(self):
        (_, _), cliente = producir(
            {"respuesta": Respuesta(json.dumps({"casos": CASOS}))},
            plan={"plan_id": "P1", "unidades": [UNIDAD]},
        )
        self.assertIn(
            "no declara exclusiones", cliente.llamadas[0]["messages"][0]["content"]
        )


# --- 5 — parseo --------------------------------------------------------------


class Parseo(unittest.TestCase):
    def test_acepta_el_objeto_con_clave_casos(self):
        self.assertEqual(parsear_casos(json.dumps({"casos": CASOS})), CASOS)

    def test_acepta_la_lista_pelada(self):
        self.assertEqual(parsear_casos(json.dumps(CASOS)), CASOS)

    def test_tolera_el_bloque_markdown(self):
        texto = "```json\n%s\n```" % json.dumps({"casos": CASOS})
        self.assertEqual(parsear_casos(texto), CASOS)

    def test_lo_que_no_es_json_levanta(self):
        with self.assertRaises(CasosNoParseables):
            parsear_casos("acá van los casos: probá la suma")

    def test_un_json_sin_casos_levanta(self):
        with self.assertRaises(CasosNoParseables):
            parsear_casos(json.dumps({"pruebas": CASOS}))


# --- 6 — respuestas degradadas ----------------------------------------------


class RespuestaDegradada(unittest.TestCase):
    """Cero casos, nunca casos inventados.

    Una tanda que no se pudo leer deja todos los criterios sin comprobar, y la
    tabla lo dice. Rellenar sería exactamente lo que ADR-018 prohíbe: convertir
    una pregunta abierta en un veredicto.
    """

    def test_una_respuesta_cortada_da_cero_casos_y_cobra(self):
        respuesta = Respuesta("{\"casos\": [{\"crit", stop_reason="max_tokens")
        (casos, costo), _ = producir({"respuesta": respuesta})
        self.assertEqual(casos, [])
        self.assertGreater(costo, 0)

    def test_una_respuesta_no_parseable_da_cero_casos_y_cobra(self):
        (casos, costo), _ = producir({"respuesta": Respuesta("no sé qué probar")})
        self.assertEqual(casos, [])
        self.assertGreater(costo, 0)


# --- 7 — fallos --------------------------------------------------------------


class Fallos(unittest.TestCase):
    def test_un_error_del_proveedor_es_fallo_de_infraestructura(self):
        from anthropic import APIError

        error = APIError("se cayó", request=None, body=None)
        with self.assertRaises(FalloDeInfraestructura):
            producir({"error": error})

    def test_un_rechazo_por_politicas_escala_con_su_costo(self):
        respuesta = Respuesta("", stop_reason="refusal")
        with self.assertRaises(FalloDeInfraestructura) as capturado:
            producir({"respuesta": respuesta})
        self.assertGreater(capturado.exception.costo, 0)


# --- 8 — el techo de tokens --------------------------------------------------


class TechoDeTokens(unittest.TestCase):
    def test_el_max_tokens_es_el_del_modulo(self):
        (_, _), cliente = producir(
            {"respuesta": Respuesta(json.dumps({"casos": CASOS}))}
        )
        self.assertEqual(cliente.llamadas[0]["max_tokens"], productor_qa.MAX_TOKENS)


# --- 9 — la Agent Definition del Vault --------------------------------------


class DefinicionDelVault(unittest.TestCase):
    """La definición real del QA Agent, la que se pasa por `--definicion-qa`.

    Se prueba acá y no en `test_agent_loader` porque lo que importa no es que
    cargue: es que lo que declara leer exista. Una `vault_lectura` que apunta a
    un archivo inexistente hace fallar la corrida recién cuando alguien la
    lanza, y con eso ya se pagó el Gate de entrada.
    """

    def setUp(self):
        from agent_loader import cargar

        self.ruta = RAIZ.parent / "03 - Agent Framework" / "QA Agent.md"
        self.assertTrue(self.ruta.exists(), "falta la definición del QA Agent")
        self.definicion = cargar(self.ruta)

    def test_carga_con_los_trece_campos_y_sus_techos(self):
        self.assertEqual(self.definicion.agent_id, "qa-agent")
        self.assertEqual(self.definicion.techo_costo_usd, 0.25)
        self.assertEqual(self.definicion.techo_tiempo_min, 5)
        self.assertEqual(self.definicion.techo_iteraciones, 1)

    def test_no_escribe_en_el_vault_ni_recuerda(self):
        # QA no acumula criterio entre corridas: cada unidad se verifica contra
        # su plan y nada más. ADR-011.
        self.assertEqual(self.definicion.vault_escritura, ())
        self.assertEqual(self.definicion.memory, "none")

    def test_todo_lo_que_declara_leer_existe(self):
        faltantes = [
            relativa for relativa in self.definicion.vault_lectura
            if not (RAIZ.parent / relativa).is_file()
        ]
        self.assertEqual(faltantes, [])

    def test_lee_el_adr_de_la_frontera_y_el_contrato_de_entrega(self):
        # Sin ADR-016 no sabe bajo qué restricciones se ejecuta lo que escribe;
        # sin el Contrato de Entrega no sabe qué forma tiene lo que va a probar.
        declarado = " ".join(self.definicion.vault_lectura)
        self.assertIn("ADR-016", declarado)
        self.assertIn("Contrato de Entrega del Developer", declarado)


if __name__ == "__main__":
    unittest.main()
