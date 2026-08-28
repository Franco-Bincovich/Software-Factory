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

## Los tres controles del límite, y por qué son código y no prompt

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

## El corolario: la métrica sale del mismo anclaje

Un criterio al que no quedó anclado ningún caso —porque QA no supo derivarlo, o
porque su procedimiento cae fuera de la frontera de ADR-016— queda marcado
`no_verificable_mecanicamente` **por construcción del anclaje**, no por un juicio
aparte. La métrica del punto 5 de ADR-018 es un conteo sobre esa tabla. Nada que
opinar.
"""

import ejecutor

CUMPLE = "cumple"
NO_CUMPLE = "no_cumple"
NO_VERIFICABLE = "no_verificable_mecanicamente"


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


def _motivo_de_descarte(caso, cantidad):
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
    return None


def anclar(casos, unidad):
    """Parte los casos en los que derivan de un criterio y los que no.

    **Previo a ejecutar**, que es la mitad del control: un caso sin ancla válida
    no llega al ejecutor. Devuelve `(anclados, descartados)`; cada descartado va
    con su motivo.
    """
    cantidad = len(criterios_de(unidad))
    anclados, descartados = [], []
    for caso in casos or []:
        motivo = _motivo_de_descarte(caso, cantidad)
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


def correr(casos, deposito, ejecutar_fn=None):
    """Corre cada caso anclado bajo la frontera de ADR-016.

    La comparación es de igualdad exacta sobre la salida estándar, sin espacios
    a los costados. Nada de coincidencia parcial: un criterio que "casi" da lo
    esperado no se cumple, y aflojar acá convertiría el veredicto binario en una
    escala sin decirlo.

    `ejecutor.SinFrontera` **no se atrapa**. Que la máquina no tenga frontera de
    kernel no es un incumplimiento del entregable: es que la Fábrica no puede
    verificar. Sube y el grafo lo escala.
    """
    ejecutar_fn = ejecutor.ejecutar_expresion if ejecutar_fn is None else ejecutar_fn
    corridas = []
    for caso in casos:
        try:
            resultado = ejecutar_fn(deposito, caso["expresion"])
        except ejecutor.EntradaRechazada as rechazo:
            # El depósito trae algo que V5 habría rechazado. Es del entregable,
            # no de la máquina: cuenta como no cumplido y se dice por qué.
            corridas.append(
                {
                    "caso": caso,
                    "cumple": False,
                    "obtenido": "el ejecutor rechazó el depósito: %s" % rechazo,
                }
            )
            continue
        obtenido = _obtenido(resultado)
        corridas.append(
            {
                "caso": caso,
                "cumple": (
                    not resultado.cortado_por_tiempo
                    and resultado.codigo == 0
                    and obtenido == str(caso["espera"]).strip()
                ),
                "obtenido": obtenido,
            }
        )
    return corridas


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
    """Ancla, corre y juzga. Es lo que llama el nodo de QA del grafo."""
    anclados, descartados = anclar(casos, unidad)
    corridas = correr(anclados, deposito, ejecutar_fn)
    tabla, incumplimientos = veredicto(unidad, corridas)
    return {
        "tabla": tabla,
        "incumplimientos": incumplimientos,
        "no_verificables": [f["regla"] for f in tabla if f["veredicto"] == NO_VERIFICABLE],
        "descartados": descartados,
    }
