"""Criterio de aceptación del productor de casos de prueba del QA Agent.

Ningún test invoca al proveedor: se inyecta un cliente falso y se ejercita lo que
es nuestro —el prompt, el parseo, el costo y el tratamiento de fallos—.

Lo que **no** se prueba acá es el límite del punto 3 de ADR-018. Ese límite no
vive en este módulo: el prompt lo explica para no gastar tokens en casos que se
van a descartar, pero la garantía está en `verificacion_sustantiva` y se prueba
en `test_verificacion_sustantiva`. Afirmar acá que el prompt contiene la
instrucción es afirmar que se le pidió, no que se cumpla.

Vale igual para la derivación y para los supuestos. Un test que busca una frase
en el prompt comprueba que el pedido llegó, nada más: si el modelo enuncia la
promesa y después instancia otra cosa, esto pasa en verde. Se prueban porque
**el pedido puede desaparecer sin que nada se rompa** —una reescritura del prompt
que se lleve puesta la instrucción no la ve nadie— y porque los supuestos sí son
plomería: que el campo de la entrega llegue al mensaje es un hecho verificable y
es lo que faltaba.
"""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import productor_qa  # noqa: E402
from grafo import FalloDeInfraestructura, RespuestaIlegible  # noqa: E402
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
    "artefacto_esperado": "Módulo con la validación del legajo",
    "ruta_artefacto": "src/validar-legajo.js",
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
    # Con la forma del supuesto que la corrida real produjo y QA nunca vio: una
    # decisión sobre entradas que el plan no menciona. Sin esto en el mensaje, el
    # caso `validarLegajo(null)` no se le ocurre a nadie.
    "supuestos": ["El plan no dice qué hacer con entradas que no son string. "
                  "Una entrada que no es string devuelve inválido."],
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
        (casos, consumo), _ = producir({"respuesta": respuesta})
        esperado = (20000 * 2.00 + 6000 * 10.00) / 1_000_000
        self.assertAlmostEqual(consumo["costo"], esperado)
        self.assertEqual(len(casos), 1)

    def test_el_desglose_explica_el_costo_de_un_paso_de_qa(self):
        """El caso que motivó todo esto: 0,125 para producir cero casos."""
        respuesta = Respuesta(json.dumps({"casos": CASOS}), entrada=8000, salida=7000)
        (_, consumo), _ = producir({"respuesta": respuesta})
        self.assertEqual(consumo["input_tokens"], 8000)
        self.assertEqual(consumo["output_tokens"], 7000)
        self.assertEqual(consumo["stop_reason"], "end_turn")


# --- 4 — el prompt -----------------------------------------------------------


class ConPrompt(unittest.TestCase):
    """Arma una llamada y expone sus dos mitades. No trae tests propios.

    Es una base y no una superclase con tests para que heredarla no los vuelva a
    correr: `test_conteos_declarados` cuenta métodos y una herencia que duplica
    tests declara un número que no se corresponde con lo que se comprueba.
    """

    def setUp(self):
        (self.casos, _), self.cliente = producir(
            {"respuesta": Respuesta(json.dumps({"casos": CASOS}))}
        )
        self.llamada = self.cliente.llamadas[0]
        self.sistema = self.llamada["system"][0]["text"]
        self.mensaje = self.llamada["messages"][0]["content"]


class Prompt(ConPrompt):
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


# --- 4b — la derivación ------------------------------------------------------


class Derivacion(ConPrompt):
    """Que se le pida enunciar la promesa antes de instanciarla.

    Es auditabilidad, no control: ver el encabezado de `productor_qa`. Lo que
    estos tests custodian es que **el pedido no desaparezca**, porque una
    reescritura del prompt que se lo lleve puesto no rompe nada más.
    """

    def test_pide_enunciar_la_promesa_antes_de_instanciar(self):
        self.assertIn("Derivar son dos pasos", self.sistema)
        self.assertIn("promete", self.sistema)

    def test_la_pregunta_que_ancla_esta_escrita(self):
        # Es la única prueba que el agente tiene para decidir si un caso deriva
        # del criterio que cita. Si se cae, la derivación vuelve a ser un reflejo.
        self.assertIn(
            "¿queda desmentido lo que **este** criterio promete?", self.sistema
        )

    def test_ya_no_ensena_a_derivar_variando_entradas(self):
        """El texto que produjo el sesgo, y la licencia que lo cerraba.

        El prompt viejo daba cuatro entradas parecidas como ejemplo de derivación
        y remataba con "todos esos derivan del mismo criterio". El modelo copió el
        método: el caso vacío no derivó del criterio, derivó del párrafo.
        """
        self.assertNotIn("Todos esos derivan del mismo criterio", self.sistema)
        self.assertIn("Variar la entrada no es derivar", self.sistema)

    def test_el_procedimiento_pide_la_derivacion_y_no_la_mecanica(self):
        self.assertIn("la derivación escrita", self.sistema)
        self.assertNotIn("una frase que diga qué comprueba", self.sistema)


# --- 4c — la custodia del quedarse corto -------------------------------------


class QuedarseCorto(ConPrompt):
    """El eje que faltaba.

    `EL_LIMITE` custodiaba cinco veces que QA no exigiera de más y ninguna que un
    caso probara el criterio del que cuelga. El modelo optimizó el único eje que
    le dieron.
    """

    def test_el_limite_custodia_los_dos_lados(self):
        self.assertIn("El límite corre para los dos lados", self.sistema)

    def test_nombra_las_dos_formas_de_quedarse_corto(self):
        self.assertIn("prueba menos de lo que el criterio promete", self.sistema)
        self.assertIn("se cuelga del criterio más parecido", self.sistema)

    def test_dice_que_ninguna_maquina_lo_va_a_atrapar(self):
        # Sin esto el agente puede suponer que hay una red abajo, como la hay
        # para el ancla fuera de rango y para la evidencia vacua.
        self.assertIn("no lo puede comprobar ninguna máquina", self.sistema)

    def test_prefiere_el_criterio_sin_caso_al_caso_falso(self):
        self.assertIn("dejalo sin caso", self.sistema)


# --- 4d — los supuestos de la entrega ----------------------------------------


class SupuestosDeLaEntrega(ConPrompt):
    """La única de las tres que es plomería y no prosa.

    Que el campo de la entrega llegue al mensaje es un hecho verificable, y es
    lo que faltaba: el Developer prometió algo y el que verifica no se enteró.
    """

    def test_los_supuestos_van_en_el_mensaje(self):
        self.assertIn("no son string", self.mensaje)

    def test_una_entrega_sin_supuestos_lo_dice(self):
        # Ausencia declarada, no sección vacía: "no declaró" y "no le llegó" son
        # cosas distintas y el agente tiene que poder distinguirlas.
        (_, _), cliente = producir(
            {"respuesta": Respuesta(json.dumps({"casos": CASOS}))},
            entrega=dict(ENTREGA, supuestos=[]),
        )
        self.assertIn(
            "no declaró supuestos", cliente.llamadas[0]["messages"][0]["content"]
        )

    def test_no_se_presentan_como_criterios(self):
        self.assertIn("**No son criterios.**", self.mensaje)
        self.assertIn("ninguna por supuesto", self.mensaje)

    def test_ante_contradiccion_manda_el_criterio(self):
        self.assertIn("manda el criterio", self.mensaje)

    def test_un_caso_que_solo_comprueba_el_supuesto_no_prueba_el_plan(self):
        # El riesgo de pasarle los supuestos: que QA verifique que el Developer
        # hizo lo que dijo, en vez de que la unidad haga lo que el plan pidió.
        self.assertIn("evaluándose a sí mismo con tu firma", self.mensaje)


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
    """Nunca casos inventados. Y nunca cero casos por una falla en silencio.

    Rellenar sería lo que ADR-018 prohíbe: convertir una pregunta abierta en un
    veredicto. Pero devolver la lista vacía cuando la respuesta no se pudo leer
    era peor, porque cero casos hace que todos los criterios salgan
    `no_verificable_mecanicamente` y la unidad **pase**: una falla que firmaba
    trabajo sin verificar, con el mismo aspecto que un QA que decidió bien.

    La línea no es cuántos casos hay: es si se entendió lo que el modelo dijo.
    """

    def test_una_respuesta_cortada_dice_que_quedo_cortada(self):
        respuesta = Respuesta("{\"casos\": [{\"crit", stop_reason="max_tokens")
        with self.assertRaises(RespuestaIlegible) as capturado:
            producir({"respuesta": respuesta})
        self.assertEqual(capturado.exception.motivo, "truncada")
        self.assertIn(str(productor_qa.MAX_TOKENS), capturado.exception.detalle)
        self.assertGreater(capturado.exception.consumo["costo"], 0)

    def test_una_respuesta_no_parseable_dice_que_no_se_pudo_parsear(self):
        with self.assertRaises(RespuestaIlegible) as capturado:
            producir({"respuesta": Respuesta("no sé qué probar")})
        self.assertEqual(capturado.exception.motivo, "no_parseable")
        self.assertGreater(capturado.exception.consumo["costo"], 0)

    def test_la_lista_vacia_que_se_pudo_leer_sigue_siendo_una_respuesta(self):
        """El silencio legítimo: QA contestó, y contestó que no hay nada que probar."""
        (casos, consumo), _ = producir(
            {"respuesta": Respuesta(json.dumps({"casos": []}))}
        )
        self.assertEqual(casos, [])
        self.assertGreater(consumo["costo"], 0)


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
        self.assertGreater(capturado.exception.consumo["costo"], 0)


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
