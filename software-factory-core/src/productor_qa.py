"""Productor de casos de prueba — la pieza que invoca al modelo para QA.

El equivalente de `productor_entrega` del otro lado de ADR-005 punto 3. El grafo
no sabe que existe un modelo: recibe una función con la firma que declara
`grafo_developer` y la llama.

**Este módulo no verifica nada.** No ejecuta, no compara, no emite veredictos y
no escribe en el Operational State. Produce casos de prueba y declara cuánto
costó producirlos. Quien los ancla, los corre y los juzga es
`verificacion_sustantiva`, y esa separación es la razón de ser del agente: si el
mismo que escribe el caso decidiera si pasó, QA sería el productor evaluándose a
sí mismo con otro nombre.

## Por qué el límite se le explica al modelo aunque no dependa de él

El prompt le dice que un caso sin ancla válida se descarta antes de ejecutarse.
No es ahí donde vive la garantía —vive en `verificacion_sustantiva.anclar`, y el
encabezado de ese módulo explica por qué—, pero decirlo evita gastar tokens y una
iteración en casos que van a la basura. El prompt sirve para que el agente sea
eficiente; el código sirve para que no pueda pasarse de la raya. Son dos cosas
distintas y ninguna reemplaza a la otra.

## Por qué la derivación se escribe: auditabilidad, no control

`LA_DERIVACION` le pide a QA que enuncie la promesa del criterio antes de
instanciarla, y `procedimiento` pasa a llevar esa derivación escrita en vez de
una glosa de la expresión.

**Eso no agrega ningún control, y conviene no confundirse.** Que este caso pruebe
este criterio y no otro no es acotable en código: el encabezado de
`verificacion_sustantiva` tiene el argumento entero, y termina en que un control
así equivaldría a una especificación ejecutable y total del criterio —y con ésa
en la mano no harían falta ni QA ni el Developer—. Nada de lo que se escriba en
un prompt convierte eso en una garantía: el modelo puede declarar una promesa y
después instanciar otra cosa, y nadie lo va a frenar.

Lo que cambia es que la derivación pase de implícita a escrita. Hoy un mal
anclaje es indistinguible de uno bueno mirando el caso: dos expresiones que
comparten función, aridad, archivo, literal esperado y número de criterio, y sólo
se diferencian en lo que las cadenas significan. Con la promesa declarada al
lado, la persona que abre la tabla lee "el criterio promete X" junto a un caso
que prueba Y, y **el mal anclaje se puede leer como mal anclaje**. No se impide:
se hace visible, que es todo lo que se puede hacer en esta capa.

## Los supuestos de la entrega, y por qué no son criterios

El Developer declara en `supuestos` lo que decidió donde el plan no decía. Son
promesas hechas —escribió el código que las cumple— y no le llegaban a QA. En la
primera corrida real el productor declaró que una entrada que no es string
devuelve `false` y escribió la guarda; el caso que lo comprueba no apareció,
porque QA no tenía cómo saber que la función aceptaba algo que no fuera un
string. Una promesa hecha que no le llegó al que verifica.

Viajan en el mensaje como contexto y no como criterios. La superficie de rechazo
no crece: la tabla del veredicto tiene una fila por criterio del plan y ninguna
por supuesto, así que un supuesto incumplido no tiene dónde aparecer. Lo que dan
es dónde mirar dentro de un criterio que ya existe.
"""

import json

from anthropic import APIError

from grafo import FalloDeInfraestructura, RespuestaIlegible
from productor import (
    MODELO_POR_DEFECTO,
    PRECIOS_USD_POR_MTOK,
    ModeloSinPrecio,
    _CERCA_JSON,
    consumo_de,
)

# Una tanda de casos son expresiones cortas, no archivos completos. El techo del
# Developer —32.000— sobra por un orden de magnitud.
MAX_TOKENS = 8000


class CasosNoParseables(ValueError):
    """La respuesta del modelo no es JSON.

    La levanta `parsear_casos` y la traduce `crear_productor` a
    `RespuestaIlegible`, que es la que entiende el grafo.

    **No devuelve la lista vacía, y antes sí.** Devolverla dejaba a QA con cero
    casos, y cero casos hace que todos los criterios salgan
    `no_verificable_mecanicamente` y la unidad pase. Una respuesta que no se
    pudo leer terminaba firmando trabajo que nadie verificó, con el mismo
    aspecto que un QA que había decidido bien.
    """


class QASinContexto(ValueError):
    """El productor no recibió los documentos que la Agent Definition declara leer."""


# --- prompt -----------------------------------------------------------------

LA_FRONTERA = """\
Cada caso se ejecuta con `node -e <expresion>` bajo estas restricciones, que las
impone el sistema y no se negocian:

- **Sin red.** Denegada en el kernel. Una expresión que abra una conexión falla.
- **Sin filesystem fuera del depósito.** Sólo se leen y escriben archivos de la
  carpeta de la entrega.
- **Con límite de tiempo.** Una expresión que no termina se corta y el caso
  cuenta como no cumplido.
- **Sin instalar nada.** Sólo builtins de Node —`node:assert`, `node:path`— y
  rutas relativas dentro del depósito. Un nombre de paquete hace fallar el caso.

El directorio de trabajo de la expresión es el depósito, así que
`require("./logica.js")` resuelve contra los archivos de la entrega.\
"""

FORMA_DEL_CASO = """\
Cada caso es un objeto con estos campos, todos obligatorios:

- `criterio`: **el número del criterio del que deriva**, contando desde 1 en el
  orden en que aparecen abajo. Es lo que ata el caso a lo que el plan pidió.
- `archivo`: el archivo de la entrega que el caso pone a prueba. Tiene que ser
  uno de los archivos de la entrega, listados más abajo: la plataforma lo
  reemplaza por un módulo vacío y vuelve a correr el caso, y si la salida no
  cambia el caso no comprobaba nada y no cuenta como evidencia.
- `procedimiento`: **la derivación escrita, en dos partes**: qué promete el
  criterio y cómo este caso instancia esa promesa. No la mecánica del caso —lo
  que hace la expresión ya se lee en `expresion` y repetirlo en prosa no agrega
  nada—. Así se ve: "el criterio promete que ninguna dirección sin arroba se
  acepta; este caso instancia esa promesa con una dirección que escribe la
  arroba como palabra".
- `expresion`: JavaScript de una sola expresión o secuencia, que **imprime en
  salida estándar** lo que hay que observar. Usá `process.stdout.write(...)` o
  `console.log(...)`; la salida se compara con `espera` recortando los espacios
  de los costados.
- `espera`: la salida exacta que se espera. Comparación por igualdad, no por
  coincidencia parcial.\
"""

LA_DERIVACION = """\
**Derivar son dos pasos, y el primero se escribe.** Antes de pensar entradas,
enunciá qué **promete** el criterio: la propiedad general que la unidad afirma
que vale. Recién después instanciá esa promesa en un caso concreto.

    Criterio    "Dado un legajo con el formato equivocado, `validarLegajo`
                devuelve inválido."
    Promete     que ningún valor que no tenga el formato del legajo sea aceptado.
    Instancia   `validarLegajo("44a1")` da inválido, porque una letra donde va un
                dígito es exactamente no tener ese formato.

**Variar la entrada no es derivar.** "El legajo válido, el vacío, el del largo
equivocado y el del formato equivocado" son cuatro entradas parecidas salidas del
mismo reflejo, y parecerse no las ancla: el del largo equivocado instancia la
promesa del criterio que habla del largo, y colgado del que habla del formato, un
fallo suyo cae sobre un criterio que nunca prometió eso.

La pregunta que separa una cosa de la otra es una sola:

> Si este caso falla, ¿queda desmentido lo que **este** criterio promete?

Contestala antes de escribir la expresión, no después. Si la respuesta es no, el
caso está anclado al criterio equivocado, y no hay entrada que lo arregle: lo que
hay que cambiar es de qué criterio cuelga, o no escribirlo.

Un criterio puede llevar varios casos —instancias distintas de la misma promesa,
y ahí sí conviene ir a los bordes—. Lo que no puede llevar es casos que
instancien otra cosa.\
"""

EL_LIMITE = """\
**Sólo podés derivar casos de los Acceptance Criteria de esta unidad.** No de lo
que te parezca que el código debería hacer, no de buenas prácticas, no de
capacidades que la unidad no pidió.

Un caso cuyo `criterio` no sea el número de un criterio de esta unidad **se
descarta antes de ejecutarse**: no aporta nada y no puede rechazar nada. La
plataforma emite el veredicto recorriendo los criterios del plan, así que un caso
sobre algo que nadie pidió no tiene dónde aterrizar.

El motivo no es de forma. Un rechazo por una capacidad ausente mete al Developer
en un bucle que no se cierra corrigiendo, porque el blanco se mueve: se quema el
techo entero contra un requerimiento que nunca se escribió.

**El límite corre para los dos lados, y con el mismo peso.** Todo lo de arriba
custodia que no exijas de más. Quedarse corto no sale más barato: sale más caro
de encontrar, porque un caso mal anclado pasa todos los filtros —el número de
criterio existe, la expresión corre, la salida se compara— y produce un veredicto
lo mismo.

Las dos formas de quedarse corto:

- **Un caso que prueba menos de lo que el criterio promete.** El criterio sale
  "cumple" con la promesa comprobada a medias, y el Gate lo lee como verificado.
  Es una firma en falso, y las firmas en falso no vuelven: se descubren cuando
  alguien usa el software.
- **Un caso que prueba otra cosa y se cuelga del criterio más parecido.** Si
  falla, el incumplimiento se le imputa a un criterio que no prometía eso, y el
  Developer termina corrigiendo contra un blanco que el plan nunca le puso.

Esto no lo atrapa nadie más. La plataforma comprueba que el número de criterio
exista y que la salida de tu caso dependa del entregable; **que el caso pruebe
*ese* criterio no lo puede comprobar ninguna máquina**, y por eso te lo estamos
pidiendo a vos en vez de programarlo. Si un criterio te queda sin ningún caso que
lo instancie de verdad, dejalo sin caso: "no verificable mecánicamente" es un
resultado, y un veredicto falso no.

**Si un criterio no se puede comprobar ejecutando** —porque su procedimiento
nombra abrir un HTML y mirarlo, o un intérprete que no es Node, o algo que no
tiene salida observable— **no le pongas ningún caso.** No lo aproximes y no lo
des por cumplido: la plataforma lo declara "no verificable mecánicamente" y
escala a una persona, que es lo correcto. Inventar un caso que "más o menos"
lo cubre convierte una pregunta abierta en un veredicto falso.

**No cuentes los tests que entregó el Developer como evidencia.** Podés
ejecutarlos, pero que pasen no comprueba nada: es el productor declarando que su
producto está bien. Tus casos son tuyos.\
"""

FORMA_DE_RESPUESTA = """\
Respondé únicamente con un objeto JSON con una sola clave, `casos`, cuyo valor es
la lista de casos. Sin texto antes, sin texto después, sin explicación y sin
bloque de código markdown. El primer carácter de tu respuesta es `{` y el último
es `}`.\
"""


def _system_prompt(contexto_vault):
    """Contrato, frontera, límite y forma de salida.

    Es el prefijo estable de todas las llamadas de todas las unidades del plan, y
    por eso es lo que se cachea. Nada que varíe por unidad entra acá.
    """
    documentos = "\n\n".join(
        "--- %s ---\n%s" % (ruta, contenido)
        for ruta, contenido in sorted(contexto_vault.items())
    )

    return """\
Sos el QA Agent de una fábrica de software. Verificás **resultados**, no código:
no leés el código para opinar si está bien escrito, ejecutás el entregable y
comprobás qué devuelve contra lo que el plan pidió.

Tu única salida son casos de prueba en JSON. **No decidís si la unidad cumple.**
Otro corre tus casos y arma el veredicto; vos no vas a saber cómo salieron.

# Normas que te obligan

Estos son los documentos del Vault que tu Agent Definition declara leer. Son
norma, no sugerencia.

{documentos}

# Dónde y cómo se ejecuta

{frontera}

# Cómo se deriva un caso de un criterio

{derivacion}

# Forma de cada caso

{forma_caso}

# El límite de lo que podés exigir

{limite}

# Forma de la respuesta

{forma}\
""".format(
        documentos=documentos,
        frontera=LA_FRONTERA,
        derivacion=LA_DERIVACION,
        forma_caso=FORMA_DEL_CASO,
        limite=EL_LIMITE,
        forma=FORMA_DE_RESPUESTA,
    )


def _criterios_numerados(unidad):
    """Los criterios con el número que el caso tiene que citar en `criterio`."""
    return "\n\n".join(
        "**Criterio {n}**\n- Condición observable: {c}\n- Resultado esperado: {r}\n"
        "- Procedimiento que declara el plan: {p}".format(
            n=i + 1,
            c=criterio.get("condicion_observable", ""),
            r=criterio.get("resultado_esperado", ""),
            p=criterio.get("procedimiento", ""),
        )
        for i, criterio in enumerate(unidad.get("criterios") or [])
    )


def _lo_excluido(plan):
    """Lo que el plan dejó afuera. Vinculante para QA igual que para el Developer.

    Va en el mensaje aunque el control mecánico no lo use: el control acota la
    superficie de rechazo a los criterios, y esto le dice al agente por qué no
    tiene sentido intentar. Lo que no se hace es *cotejar* un caso contra estas
    frases —es prosa libre y cotejarla sería un heurístico disfrazado de regla—.
    """
    fuera = list(plan.get("fuera_de_alcance") or [])
    excluido = list((plan.get("restricciones") or {}).get("alcance_excluido") or [])
    todo = fuera + excluido
    if not todo:
        return "El plan no declara exclusiones."
    return (
        "El plan declara esto fuera de alcance. **No es un defecto que la entrega "
        "no lo tenga**, y no podés derivar ningún caso de acá:\n\n%s"
        % "\n".join("- %s" % item for item in todo)
    )


def _archivos_del_deposito(entrega):
    archivos = (entrega or {}).get("archivos") or []
    if not archivos:
        return "(la entrega no declara archivos)"
    return "\n".join(
        "- `%s`%s" % (a["ruta"], " — %s" % a["rol"] if a.get("rol") else "")
        for a in archivos
    )


def _supuestos_de(entrega):
    """Lo que el Developer decidió donde el plan no decía.

    Son promesas hechas: el productor las escribió y escribió el código que las
    cumple. Hasta que empezaron a viajar acá, QA instanciaba los criterios a
    ciegas sobre ese margen —ver el encabezado del módulo—.

    Se pasan como contexto, nunca como criterios. La distinción es sustantiva y
    el prompt la dice: la tabla del veredicto tiene una fila por criterio del
    plan y ninguna por supuesto, así que un supuesto incumplido no tiene dónde
    aparecer. Lo que dan es dónde mirar dentro de un criterio que ya existe.
    """
    supuestos = list((entrega or {}).get("supuestos") or [])
    if not supuestos:
        return "El Developer no declaró supuestos."
    return "\n".join("- %s" % str(s) for s in supuestos)


def _mensaje(unidad, plan, entrega, deposito):
    return """\
Produjeron una entrega para esta unidad y ya pasó la verificación estructural:
los archivos están, parsean y corresponden con el plan. Lo que falta comprobar es
si **hace lo que la unidad pide**, y eso es lo tuyo.

# Unidad {id}

**Enunciado:** {enunciado}

**Artefacto esperado:** {artefacto}

# Acceptance Criteria

Numerados. El campo `criterio` de cada caso cita uno de estos números.

{criterios}

# Fuera de alcance

{excluido}

# Lo que el Developer decidió por su cuenta

El plan deja cosas sin decir y el productor tuvo que decidirlas para poder
escribir el código. Esto es lo que declaró haber decidido:

{supuestos}

Está acá porque son promesas hechas y no tenías cómo saberlas. Un supuesto te
dice qué entradas el productor esperaba recibir, y ahí es donde una promesa del
plan se puede estar cumpliendo a medias sin que se note.

**No son criterios.** No podés derivar un caso de un supuesto ni rechazar porque
un supuesto no se cumpla: la tabla del veredicto tiene una fila por Acceptance
Criterion y ninguna por supuesto, así que eso no tiene dónde aparecer. Y un caso
que sólo comprueba que la decisión del productor sea la que él dijo no prueba
nada del plan: es el productor evaluándose a sí mismo con tu firma.

Lo que sí: usalos para instanciar mejor un criterio que ya existe. Si el
criterio promete rechazar lo inválido y el supuesto dice qué entradas la función
acepta, ahí tenés instancias de esa promesa que sin el supuesto no se te habrían
ocurrido.

Si un supuesto contradice un criterio, manda el criterio. Que el productor haya
decidido otra cosa no cambia lo que el plan pidió.

# El depósito

Los archivos de la entrega están en `{deposito}`, que es el directorio de trabajo
de tus expresiones. Estos son:

{archivos}

{forma}\
""".format(
        id=unidad["id"],
        enunciado=unidad["enunciado"],
        artefacto=unidad.get("artefacto_esperado", ""),
        criterios=_criterios_numerados(unidad),
        excluido=_lo_excluido(plan),
        supuestos=_supuestos_de(entrega),
        deposito=deposito,
        archivos=_archivos_del_deposito(entrega),
        forma=FORMA_DE_RESPUESTA,
    )


# --- respuesta --------------------------------------------------------------


def _texto_de(mensaje):
    return "".join(b.text for b in mensaje.content if b.type == "text")


def parsear_casos(texto):
    """Devuelve la lista de casos. Levanta `CasosNoParseables` si no es JSON.

    Tolera el bloque de código markdown que el prompt pide no usar: que el modelo
    lo agregue igual es previsible y no amerita gastar una iteración.
    """
    limpio = _CERCA_JSON.sub("", texto.strip())
    try:
        datos = json.loads(limpio)
    except ValueError as error:
        raise CasosNoParseables("la respuesta no es JSON: %s" % error)
    if isinstance(datos, list):
        return datos
    if not isinstance(datos, dict) or not isinstance(datos.get("casos"), list):
        raise CasosNoParseables("la respuesta no trae una lista en `casos`.")
    return datos["casos"]


# --- interfaz ---------------------------------------------------------------


def crear_productor(api_key, modelo=MODELO_POR_DEFECTO, ruta_vault=None, cliente=None):
    """Devuelve la `qa_fn` que espera `grafo_developer`.

    La función devuelta cumple la firma `(unidad, plan, entrega, deposito,
    contexto_vault)` y responde `(casos, costo)`.

    `cliente` existe para los tests: permite ejercitar el armado del prompt, el
    parseo y el cálculo de costo sin invocar al proveedor.
    """
    if modelo not in PRECIOS_USD_POR_MTOK:
        raise ModeloSinPrecio(
            "el modelo '%s' no tiene precio declarado en PRECIOS_USD_POR_MTOK; "
            "sin precio el consumo no se puede medir y el techo de ADR-010 no "
            "se puede sostener. Modelos con precio: %s."
            % (modelo, ", ".join(sorted(PRECIOS_USD_POR_MTOK)))
        )

    if cliente is None:
        from anthropic import Anthropic

        cliente = Anthropic(api_key=api_key)

    def producir(unidad, plan, entrega, deposito, contexto_vault):
        if not contexto_vault:
            raise QASinContexto(
                "el productor de QA no recibió ningún documento del Vault. La "
                "Agent Definition del QA Agent declara qué leer en "
                "`vault_lectura`; sin el Contrato de Entrega y ADR-016 el agente "
                "no sabe qué forma tiene lo que va a ejecutar ni bajo qué "
                "restricciones. Indicá la raíz del Vault con --vault (valor "
                "actual: %r)." % (ruta_vault,)
            )

        sistema = [
            {
                "type": "text",
                "text": _system_prompt(contexto_vault),
                "cache_control": {"type": "ephemeral"},
            }
        ]

        try:
            with cliente.messages.stream(
                model=modelo,
                max_tokens=MAX_TOKENS,
                system=sistema,
                messages=[
                    {"role": "user", "content": _mensaje(unidad, plan, entrega, deposito)}
                ],
            ) as flujo:
                respuesta = flujo.get_final_message()
        except APIError as error:
            raise FalloDeInfraestructura(
                "el proveedor del modelo no respondió: %s" % error
            )

        consumo = consumo_de(respuesta.usage, modelo, respuesta.stop_reason)

        if respuesta.stop_reason == "refusal":
            raise FalloDeInfraestructura(
                "el modelo rechazó la unidad por políticas de contenido. La "
                "corrida se corta y la unidad se revisa a mano.",
                consumo=consumo,
            )

        # Acá había un `return [], costo` para los dos casos de abajo, y era el
        # agujero más caro de la fábrica: cero casos hace que todos los criterios
        # salgan `no_verificable_mecanicamente`, y eso **pasa**. Una respuesta que
        # no se pudo leer firmaba la unidad con el mismo aspecto que un QA que
        # había mirado y decidido. Ahora se distingue.
        #
        # La lista vacía sigue siendo una respuesta legítima —la da el stub, y la
        # da el modelo cuando ningún criterio es verificable mecánicamente—, pero
        # sólo cuando **se pudo leer** que era vacía: `{"casos": []}` parsea y
        # llega abajo intacta. La línea no es cuántos casos hay, es si se entendió
        # lo que el modelo contestó.
        #
        # Las dos llevan el texto que el modelo alcanzó a escribir. Es lo único
        # que permite después decir *por qué* no se pudo leer, y se descartaba
        # acá mismo. Quién lo guarda es el grafo, contra el área de artefactos.
        texto = _texto_de(respuesta)
        if respuesta.stop_reason == "max_tokens":
            raise RespuestaIlegible(
                "truncada",
                "el modelo llegó al techo de %d tokens de salida y la respuesta "
                "quedó cortada." % MAX_TOKENS,
                consumo=consumo,
                texto=texto,
            )
        try:
            return parsear_casos(texto), consumo
        except CasosNoParseables as error:
            raise RespuestaIlegible(
                "no_parseable", str(error), consumo=consumo, texto=texto
            )

    return producir
