"""Verificación sustantiva — la plataforma que juzga lo que QA propuso.

Es la contraparte de `verificador_entrega` para ADR-018. Aquél mira la forma de
la Entrega sin ejecutar nada; éste ejecuta el entregable bajo la frontera de
ADR-016 y compara resultados contra los Acceptance Criteria del plan.

**Acá no hay modelo.** Los casos de prueba los produce el QA Agent
(`productor_qa`); este módulo los ancla, los corre con el ejecutor y emite el
veredicto. Es el punto 3 de ADR-005 otra vez: el productor nunca es el
verificador, y por eso el que decide si un criterio se cumple no es el mismo que
escribió el caso.

El veredicto es binario por criterio: cumple, no cumple, o no verificable
mecánicamente. **Sin porcentajes.** "El 80% de los criterios pasa" no es un
veredicto: es una forma de entregar sin cumplir.

## Los cuatro controles del límite, y por qué son código y no prompt

ADR-018 punto 3 prohíbe que QA exija capacidades que el plan no incluyó. Un
rechazo por algo que nadie pidió mete al Developer en un bucle que no se cierra
corrigiendo, porque el blanco se mueve: se paga el techo entero contra un
requerimiento que nunca se escribió.

Una instrucción en el prompt no alcanza para eso. Sería una garantía que la
máquina no da, exactamente como el bloqueo de red en proceso que `ejecutor`
documenta y rechaza. Lo que sí se puede construir es esto:

**Control 1 — anclaje obligatorio, y la poda es previa a ejecutar.** Cada caso
declara de qué criterio de *su* unidad deriva, por índice. El índice se resuelve
contra `unidad["criterios"]` **antes** de correr nada: ausente, fuera de rango o
mal tipado, y el caso se descarta sin ejecutarse. Es la misma disciplina que
`ejecutor.revisar_entrada` — se rechaza antes, no se interpreta después.

**Control 2 — el veredicto lo emite el criterio, no el caso.** Es la decisión de
diseño de este módulo y la que sostiene todo lo demás, así que va escrita acá y
no sólo en la Agent Definition.

`veredicto` recorre **`unidad["criterios"]`**, no la lista de casos. Por cada
criterio junta los casos que se le anclaron y emite una fila; el `regla` del
incumplimiento es el identificador del criterio. No existe un camino de código
que fabrique un incumplimiento a partir de un caso: un caso no se puede nombrar
a sí mismo en el veredicto, sólo puede aportar evidencia sobre un criterio que
el plan ya escribió.

La consecuencia es la que importa: **la superficie de rechazo es, por
construcción, la lista de criterios del plan.** Un caso inventado sobre una
capacidad ausente no tiene criterio al que colgarse, y por lo tanto no tiene
dónde aterrizar el "no cumple". No hace falta detectar la intención de QA —cosa
que no se puede hacer mecánicamente— porque no hace falta: no tiene cómo
expresarse.

**Y hasta acá llega. Léase crudo, porque el párrafo de arriba se lee como si
dijera más de lo que dice.** El Control 2 garantiza el *rango* del rechazo: no se
puede nombrar un criterio que el plan no escribió. **No garantiza la validez del
ancla dentro de ese rango**: nada impide que un caso se cuelgue del criterio
equivocado *del mismo plan*, y si falla, el incumplimiento se le imputa a un
criterio que no hablaba de eso.

Eso no es un pendiente: **no se puede acotar mecánicamente.** El argumento es
corto. Estos dos casos son idénticos en toda propiedad que una máquina pueda
mirar —misma función, misma aridad, mismo literal esperado, mismo archivo, mismo
criterio declarado—:

    fn('usuario-arroba-dominio.com')  espera 'false'   <- deriva del criterio
    fn('usuario@dominio')             espera 'false'   <- no deriva del criterio

Lo único que los separa es el significado de las dos cadenas: a una le falta el
`@`, que es lo que el criterio pide, y a la otra le falta el dominio de primer
nivel, que el criterio nunca mencionó. Un control que los distinga tiene que
comparar la prosa del criterio con un string arbitrario, o sea solapamiento de
palabras clave: el heurístico que este mismo módulo rechaza más abajo para
`fuera_de_alcance`, y por el mismo motivo.

El reductio, que es lo que cierra la discusión: **un control que compruebe "este
caso prueba este criterio" equivale a tener una especificación ejecutable y total
del criterio, y si la tuvieras no harían falta ni QA ni el Developer** —ya
tendrías el programa—. La imposibilidad es estructural, no de ingeniería.

Así que la validez del ancla vive en el prompt de `productor_qa`, y ahí se queda.
Quien venga a "endurecer" esto que lea este párrafo antes de escribir un control
que no controla.

Si alguien viene a simplificar esto invirtiendo el bucle —recorrer los casos y
tomar el nombre de regla de cada caso, que sale más corto—, la garantía
desaparece sin que nada se rompa a la vista. El invariante está cubierto por un
test property-style que corre contra salidas fabricadas hostiles, y hay una
verificación por mutación registrada que confirma que ese test lo detecta.

**Por qué no se coteja contra `fuera_de_alcance`.** `fuera_de_alcance` y
`restricciones.alcance_excluido` son arrays de prosa libre. Cotejar un caso de
prueba contra una frase en castellano sería solapamiento de palabras clave: un
heurístico que falla en los dos sentidos y que daría confianza falsa justo en el
borde que se quiere cuidar. Y no hace falta: si todo rechazo tiene que nombrar un
criterio de la unidad, QA no puede rechazar por algo fuera de alcance, porque no
habría criterio que nombrar. El caso donde el plan se contradice —un criterio que
pide lo que el mismo plan excluyó— es un defecto del plan, y le corresponde al
verificador estructural y al Requirement Agent, no a este módulo.

**Control 3 — el ejecutor ya está.** "Exigir una capacidad ausente" se
materializa casi siempre como "además tendría que existir el módulo X". Un caso
así no corre: `ejecutor.revisar_entrada` rechaza lo que V5 rechazaría, y se
ejecuta sobre el depósito de la entrega, que contiene sólo lo entregado.

**Control 4 — la evidencia tiene que depender del artefacto.** Los tres controles
de arriba cuidan que QA no rechace de más. Ninguno cuidaba lo contrario: que QA
**acepte** sin haber comprobado nada. Un caso así:

    {"criterio": 2, "archivo": "src/validar-email.js",
     "expresion": "console.log('false');", "espera": "false"}

pasaba, y si era el único anclado a ese criterio el criterio salía `cumple` con
cero evidencia sobre la entrega. El Control 1 lo dejaba pasar porque el ancla era
válida; el 2 porque el criterio tenía un caso que "cumplía"; el 3 porque no toca
el filesystem. Y una aceptación falsa es peor que un rechazo injusto: **el
rechazo injusto se descubre en el bucle de corrección, la aceptación falsa se
firma en el Gate.**

Contra eso van tres cosas, todas mecánicas y ninguna semántica:

1. **Copia limpia por ejecución.** El ejecutor le da permiso de escritura sobre
   la raíz del depósito, así que un caso puede dejar un archivo que haga pasar a
   otro. Repetir la tanda en el mismo orden no lo ve —la contaminación se
   reproduce igual—; una copia limpia por ejecución sí.
2. **Doble corrida.** Dos ejecuciones del mismo caso tienen que dar la misma
   salida. Lo que depende del reloj o del azar no es evidencia en ninguna de las
   dos direcciones: pasar por suerte firma de más y fallar por suerte manda al
   Developer a corregir un fantasma.
3. **El centinela.** El caso que pasó se corre una vez más con el archivo que
   nombra reemplazado por un módulo que se deja usar y no hace nada. Si **igual
   pasa**, su salida no dependía del entregable. El centinela se sortea por tanda
   (`centinela_nuevo`) para que no pueda coincidir con ningún `espera`, lo que le
   da al control una propiedad que conviene tener escrita: **se equivoca en una
   sola dirección —puede dejar pasar un caso vacuo, no puede condenar uno real—.**

**Qué pasa cuando dispara: el caso se descarta como evidencia, no se convierte en
falla.** Contarlo como `no_cumple` sería fabricar el rechazo injusto para tapar
la aceptación falsa, cambiando un problema por el otro y culpando al Developer de
un defecto de QA. Si era el único caso del criterio, el criterio cae solo a
`no_verificable_mecanicamente` y escala a una persona, que es exactamente la
verdad: QA no produjo evidencia ejecutable para ese criterio.

**El techo del Control 4, que no es un borde sino su límite.** Prueba que la
salida del caso **depende del artefacto**. No prueba que el caso **pruebe el
criterio**: eso es el hueco del ancla de más arriba, y sigue abierto porque no se
puede cerrar. Es el piso, no el techo. Y cuando se lo midió contra la única
corrida real con QA, los diez casos eran evidencia genuina: **es una guardia
sobre un hueco abierto, no la reparación de algo que ya se pudrió.**

## El corolario: la métrica sale del mismo anclaje

Un criterio al que no quedó anclado ningún caso —porque QA no supo derivarlo, o
porque su procedimiento cae fuera de la frontera de ADR-016— queda marcado
`no_verificable_mecanicamente` **por construcción del anclaje**, no por un juicio
aparte. La métrica del punto 5 de ADR-018 es un conteo sobre esa tabla. Nada que
opinar.
"""

import os
import shutil
import tempfile
import uuid

import ejecutor

CUMPLE = "cumple"
NO_CUMPLE = "no_cumple"
NO_VERIFICABLE = "no_verificable_mecanicamente"

#: Prefijo del centinela del Control 4. El valor completo se sortea por corrida
#: —ver `centinela_nuevo`— y la marca sirve para reconocerlo.
MARCA_CENTINELA = "CENTINELA-QA-"

#: Por qué un caso ejecutado no cuenta como evidencia. Son las dos formas de
#: pasar sin probar nada, y las dos terminan en el mismo lugar: el criterio
#: queda no verificable, nunca no cumplido.
NO_DEPENDE = "no_depende_del_artefacto"
NO_DETERMINISTA = "no_determinista"


def identificador_de_criterio(unidad_id, indice):
    """El nombre con el que un criterio aparece en el veredicto.

    Lleva la unidad adentro a propósito: los criterios se numeran desde 1 en
    cada unidad, y un `AC-2` suelto no dice de cuál. El identificador es lo que
    el Developer recibe en el bucle de corrección, así que tiene que resolver
    solo.
    """
    return "AC-%s-%d" % (unidad_id, indice)


def criterios_de(unidad):
    return list(unidad.get("criterios") or [])


# --- Control 1 — el anclaje -------------------------------------------------


def ruta_en_deposito(deposito, archivo):
    """La ruta absoluta de `archivo` dentro del depósito, o `None`.

    Normaliza antes de decidir: un `archivo` con `..` que apunte afuera no es un
    archivo de la entrega, y que exista en el disco no lo convierte en uno. Es
    la misma disciplina de `ejecutor.revisar_entrada`, acá sobre el campo que el
    Control 4 usa para saber qué reemplazar.
    """
    if not isinstance(archivo, str) or not archivo.strip():
        return None
    raiz = os.path.realpath(deposito)
    destino = os.path.realpath(os.path.join(raiz, archivo))
    if destino != raiz and not destino.startswith(raiz + os.sep):
        return None
    return destino if os.path.isfile(destino) else None


def _motivo_de_descarte(caso, cantidad, deposito):
    """Por qué este caso no se ejecuta, o `None` si se ejecuta.

    Devuelve el motivo en vez de un booleano porque el descarte se registra: un
    caso podado sin explicación manda a alguien a leer código, y son los casos
    podados los que dicen si el productor está derivando mal.
    """
    if not isinstance(caso, dict):
        return "el caso no es un objeto; es %r." % (caso,)

    indice = caso.get("criterio")
    if isinstance(indice, bool) or not isinstance(indice, int):
        return (
            "no ancla en ningún criterio: `criterio` vale %r y tiene que ser el "
            "número de un criterio de esta unidad." % (indice,)
        )
    if not 1 <= indice <= cantidad:
        return (
            "ancla en el criterio %d y la unidad tiene %d. Un caso que no deriva "
            "de un criterio del plan no se ejecuta." % (indice, cantidad)
        )

    if not str(caso.get("expresion") or "").strip():
        return "no trae expresión para ejecutar."
    if "espera" not in caso:
        return "no declara qué espera obtener."

    # `archivo` dejó de ser decorativo cuando el Control 4 empezó a reemplazarlo
    # por el centinela: un caso que no dice sobre qué entregable habla no se
    # puede auditar, porque no hay qué sacarle para ver si la salida cambia.
    if ruta_en_deposito(deposito, caso.get("archivo")) is None:
        return (
            "no nombra un archivo de la entrega: `archivo` vale %r y tiene que "
            "ser la ruta, dentro del depósito, del entregable que el caso pone "
            "a prueba." % (caso.get("archivo"),)
        )
    return None


def anclar(casos, unidad, deposito):
    """Parte los casos en los que derivan de un criterio y los que no.

    **Previo a ejecutar**, que es la mitad del control: un caso sin ancla válida
    no llega al ejecutor. Devuelve `(anclados, descartados)`; cada descartado va
    con su motivo.
    """
    cantidad = len(criterios_de(unidad))
    anclados, descartados = [], []
    for caso in casos or []:
        motivo = _motivo_de_descarte(caso, cantidad, deposito)
        if motivo is None:
            anclados.append(caso)
        else:
            descartados.append({"caso": caso, "motivo": motivo})
    return anclados, descartados


# --- la ejecución -----------------------------------------------------------


def _obtenido(resultado):
    if resultado.cortado_por_tiempo:
        return "cortado por tiempo a los %ss" % resultado.segundos
    if resultado.codigo != 0:
        return "terminó con código %s: %s" % (resultado.codigo, (resultado.error or "").strip())
    return (resultado.salida or "").strip()


def centinela_nuevo():
    """Un centinela irrepetible, sorteado por tanda.

    Tiene que ser imposible que coincida con el `espera` de un caso: si
    coincidiera, un caso legítimo sobreviviría al reemplazo y lo declararíamos
    vacuo siendo real. QA nunca vio este valor —se sortea después de que produjo
    los casos—, así que no puede haberlo escrito.
    """
    return MARCA_CENTINELA + uuid.uuid4().hex


def modulo_centinela(centinela):
    """El reemplazo del entregable: un módulo que se deja usar y no hace nada.

    Es un Proxy y no un `throw` a propósito. Un módulo que explota sólo delata al
    caso que **nunca cargó** el archivo; éste delata además al que lo carga y no
    lo usa —`require(...)` seguido de imprimir una constante—, que es la forma
    más común de aceptación falsa y la que se midió antes de elegir.

    Cualquier propiedad devuelve el mismo Proxy y cualquier llamada devuelve el
    centinela, así que la expresión corre entera y la salida sólo cambia si
    dependía del comportamiento del entregable.
    """
    return (
        "// Reemplazo del Control 4 de `verificacion_sustantiva`. No es de la entrega.\n"
        "const centinela = %s;\n"
        "const trampa = new Proxy(function () {}, {\n"
        "  get: () => trampa,\n"
        "  apply: () => centinela,\n"
        "  construct: () => trampa,\n"
        "});\n"
        "module.exports = trampa;\n" % _literal(centinela)
    )


def _literal(texto):
    return '"%s"' % texto.replace("\\", "\\\\").replace('"', '\\"')


_CODIGO = (".js", ".cjs", ".mjs")


def _plantar_centinela(copia, archivo, centinela):
    destino = os.path.join(copia, archivo)
    contenido = (
        modulo_centinela(centinela)
        if destino.endswith(_CODIGO)
        else centinela
    )
    with open(destino, "w", encoding="utf-8") as salida:
        salida.write(contenido)


def _en_copia_limpia(deposito, expresion, ejecutar_fn, centinela_en=None, centinela=None):
    """Ejecuta sobre una copia intacta del depósito, opcionalmente adulterada.

    **Copia por ejecución, no por tanda.** El ejecutor le da al caso permiso de
    escritura sobre la raíz, así que un caso puede dejar un archivo que haga
    pasar a otro. Repetir la tanda en el mismo orden no lo detecta: la
    contaminación se reproduce igual. Sólo una copia limpia por ejecución lo
    corta.

    El depósito real nunca se toca. Es el registro de auditoría de ADR-017 y
    tiene un SHA-256 fijado; adulterarlo y restaurarlo dejaría el hash mintiendo
    si algo se corta a la mitad.
    """
    with tempfile.TemporaryDirectory() as tmp:
        copia = os.path.join(tmp, "deposito")
        shutil.copytree(deposito, copia)
        if centinela_en is not None:
            _plantar_centinela(copia, centinela_en, centinela)
        return ejecutar_fn(copia, expresion)


def _una_corrida(caso, deposito, ejecutar_fn, centinela_en=None, centinela=None):
    """Un `{cumple, obtenido}` para una ejecución.

    `ejecutor.SinFrontera` **no se atrapa**. Que la máquina no tenga frontera de
    kernel no es un incumplimiento del entregable: es que la Fábrica no puede
    verificar. Sube y el grafo lo escala.
    """
    try:
        resultado = _en_copia_limpia(
            deposito, caso["expresion"], ejecutar_fn, centinela_en, centinela
        )
    except ejecutor.EntradaRechazada as rechazo:
        # El depósito trae algo que V5 habría rechazado. Es del entregable,
        # no de la máquina: cuenta como no cumplido y se dice por qué.
        return {"cumple": False, "obtenido": "el ejecutor rechazó el depósito: %s" % rechazo}
    obtenido = _obtenido(resultado)
    return {
        "cumple": (
            not resultado.cortado_por_tiempo
            and resultado.codigo == 0
            and obtenido == str(caso["espera"]).strip()
        ),
        "obtenido": obtenido,
    }


def correr(casos, deposito, ejecutar_fn=None):
    """Corre cada caso anclado bajo la frontera de ADR-016 y filtra lo que no es
    evidencia. Devuelve `(corridas, sin_evidencia)`.

    La comparación es de igualdad exacta sobre la salida estándar, sin espacios
    a los costados. Nada de coincidencia parcial: un criterio que "casi" da lo
    esperado no se cumple, y aflojar acá convertiría el veredicto binario en una
    escala sin decirlo.

    Cada caso se corre **dos veces sobre copias limpias**, y el que pasó se corre
    **una tercera con el entregable reemplazado por el centinela**. Ver el
    Control 4 en el encabezado. El reemplazo es sólo para los que pasaron: un
    caso que ya falló deja su criterio en `no_cumple` sea vacuo o no, así que
    medirlo no cambiaría nada y costaría una ejecución.
    """
    ejecutar_fn = ejecutor.ejecutar_expresion if ejecutar_fn is None else ejecutar_fn
    centinela = centinela_nuevo()
    corridas, sin_evidencia = [], []

    for caso in casos:
        primera = _una_corrida(caso, deposito, ejecutar_fn)
        repetida = _una_corrida(caso, deposito, ejecutar_fn)

        if primera["obtenido"] != repetida["obtenido"]:
            sin_evidencia.append(
                {
                    "caso": caso,
                    "motivo": NO_DETERMINISTA,
                    "detalle": (
                        "dos corridas del mismo caso sobre copias limpias dieron "
                        "%r y %r. Lo que depende del reloj, del azar o de lo que "
                        "dejó otro caso no comprueba nada."
                        % (primera["obtenido"], repetida["obtenido"])
                    ),
                }
            )
            continue

        if primera["cumple"]:
            con_centinela = _una_corrida(
                caso, deposito, ejecutar_fn, caso["archivo"], centinela
            )
            if con_centinela["cumple"]:
                sin_evidencia.append(
                    {
                        "caso": caso,
                        "motivo": NO_DEPENDE,
                        "detalle": (
                            "el caso sigue dando %r con `%s` reemplazado por un "
                            "módulo que no hace nada. Su salida no depende del "
                            "entregable, así que no comprueba que el entregable "
                            "cumpla." % (con_centinela["obtenido"], caso["archivo"])
                        ),
                    }
                )
                continue

        corridas.append(dict(primera, caso=caso))

    return corridas, sin_evidencia


# --- Control 2 — la emisión por criterio ------------------------------------


def veredicto(unidad, corridas):
    """La tabla y los incumplimientos. **El bucle es sobre los criterios.**

    Ver el Control 2 en el encabezado del módulo antes de tocar esta función. El
    recorrido va sobre `unidad["criterios"]` y no sobre `corridas`, y ese detalle
    es la garantía entera: es lo que hace que un incumplimiento sólo pueda
    nombrar un criterio que el plan escribió para esta unidad. Invertir el bucle
    para acortar el código elimina el control sin romper nada visible.

    Los incumplimientos salen en `{regla, archivo, detalle}`, la misma forma que
    `verificador_entrega`, para que `_mensaje_correccion` del Developer los
    reciba sin distinguir de dónde vienen y el bucle de reintento sea uno solo.
    """
    por_criterio = {}
    for corrida in corridas:
        caso = corrida["caso"]
        indice = caso.get("criterio") if isinstance(caso, dict) else None
        por_criterio.setdefault(indice, []).append(corrida)

    tabla, incumplimientos = [], []
    for indice, criterio in enumerate(criterios_de(unidad), start=1):
        regla = identificador_de_criterio(unidad["id"], indice)
        de_este = por_criterio.get(indice, [])

        if not de_este:
            # Sin caso anclado no hay procedimiento ejecutable: se declara, no
            # se juzga. Punto 5 de ADR-018.
            tabla.append(
                {
                    "regla": regla,
                    "criterio": criterio.get("condicion_observable", ""),
                    "procedimiento": None,
                    "veredicto": NO_VERIFICABLE,
                    "casos": [],
                }
            )
            continue

        fallidas = [c for c in de_este if not c["cumple"]]
        tabla.append(
            {
                "regla": regla,
                "criterio": criterio.get("condicion_observable", ""),
                "procedimiento": "; ".join(
                    str(c["caso"].get("procedimiento") or c["caso"]["expresion"])
                    for c in de_este
                ),
                "veredicto": NO_CUMPLE if fallidas else CUMPLE,
                "casos": [
                    {
                        # `archivo` va al registro porque el Control 4 lo usa:
                        # sin él no se puede auditar después sobre qué
                        # entregable se midió que la salida dependía.
                        "archivo": c["caso"].get("archivo"),
                        "expresion": c["caso"]["expresion"],
                        "espera": c["caso"]["espera"],
                        "obtenido": c["obtenido"],
                        "cumple": c["cumple"],
                    }
                    for c in de_este
                ],
            }
        )

        if fallidas:
            primera = fallidas[0]
            incumplimientos.append(
                {
                    "regla": regla,
                    "archivo": primera["caso"].get("archivo"),
                    "detalle": (
                        "el criterio dice: %s. Se esperaba %r y se obtuvo %r "
                        "ejecutando `%s`."
                        % (
                            criterio.get("resultado_esperado", "")
                            or criterio.get("condicion_observable", ""),
                            str(primera["caso"]["espera"]).strip(),
                            primera["obtenido"],
                            primera["caso"]["expresion"],
                        )
                    ),
                }
            )

    return tabla, incumplimientos


# --- interfaz ---------------------------------------------------------------


def verificar(unidad, casos, deposito, ejecutar_fn=None):
    """Ancla, corre y juzga. Es lo que llama el nodo de QA del grafo.

    `descartados` y `sin_evidencia` van en claves distintas y no se suman. Los
    primeros no se ejecutaron —es la poda previa del Control 1— y los segundos
    se ejecutaron y no probaron nada. "QA no derivó un caso" y "QA derivó un caso
    que no comprobaba el entregable" son dos fallas distintas del productor, y
    contarlas juntas volvería ilegible la métrica del punto 5 de ADR-018.
    """
    anclados, descartados = anclar(casos, unidad, deposito)
    corridas, sin_evidencia = correr(anclados, deposito, ejecutar_fn)
    tabla, incumplimientos = veredicto(unidad, corridas)
    return {
        "tabla": tabla,
        "incumplimientos": incumplimientos,
        "no_verificables": [f["regla"] for f in tabla if f["veredicto"] == NO_VERIFICABLE],
        "descartados": descartados,
        "sin_evidencia": sin_evidencia,
    }
