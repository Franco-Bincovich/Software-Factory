"""Contador de presupuesto — T12.

Mide el consumo de una corrida contra sus tres techos. Mide **durante**, no al
final: un techo que se verifica cuando la corrida terminó no es un techo, es una
estadística.

`verificar` devuelve el veredicto y no escribe ningún evento. Quien recibe
`TechoAlcanzado` detiene la corrida y emite `run_cortada`, para que la
responsabilidad de cortar quede en un solo lugar.

Elevar un techo no se implementa acá: es cambiar un parámetro de la Agent
Definition y relanzar. Modificarlo con la corrida viva permitiría que el límite
ceda bajo presión.
"""

from datetime import datetime, timezone

TECHOS = (
    ("costo", "techo_costo_usd"),
    ("tiempo_min", "techo_tiempo_min"),
    ("iteraciones", "techo_iteraciones"),
)


class TechoAlcanzado(object):
    """Uno o más techos alcanzados. Si se alcanzan juntos, los nombra a todos."""

    def __init__(self, alcanzados):
        self.techos = tuple(alcanzados)
        self.nombres = tuple(t["techo"] for t in self.techos)

    def __repr__(self):
        detalle = ", ".join(
            "%s %s/%s" % (t["techo"], t["valor"], t["limite"]) for t in self.techos
        )
        return "<TechoAlcanzado %s>" % detalle

    def __str__(self):
        return "techo alcanzado: " + ", ".join(
            "%s vale %s y el límite es %s" % (t["techo"], t["valor"], t["limite"])
            for t in self.techos
        )


def _parsear_ts(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def _ventanas_de_espera(eventos, ahora):
    """Segundos totales que la corrida pasó esperando a una persona.

    Cada par `gate_abierto` / `gate_resuelto` define una ventana. Un Gate abierto
    y todavía sin resolver descuenta desde que se abrió hasta ahora: esperar a un
    humano no puede matar una corrida.
    """
    pendientes = []
    total = 0.0
    for evento in eventos:
        gate = evento["payload"].get("gate")
        if evento["tipo"] == "gate_abierto":
            pendientes.append((gate, _parsear_ts(evento["ts"])))
        elif evento["tipo"] == "gate_resuelto":
            for i, (gate_abierto, desde) in enumerate(pendientes):
                if gate_abierto == gate:
                    total += (_parsear_ts(evento["ts"]) - desde).total_seconds()
                    del pendientes[i]
                    break
    # Los que siguen abiertos descuentan hasta ahora.
    for _, desde in pendientes:
        total += (ahora - desde).total_seconds()
    return total


def consumo(store, run_id, ahora=None):
    """Consumo vigente de una corrida: costo, tiempo neto en minutos, iteraciones.

    Devuelve ceros para una corrida recién iniciada; no falla.
    """
    ahora = datetime.now(timezone.utc) if ahora is None else ahora
    eventos = store.leer_run(run_id)

    costo = 0.0
    inicio = None
    iteraciones = 0
    for evento in eventos:
        if evento["tipo"] == "consumo_registrado":
            costo += evento["payload"].get("costo", 0)
        elif evento["tipo"] == "run_iniciada" and inicio is None:
            inicio = _parsear_ts(evento["ts"])
        elif evento["tipo"] == "verificacion_ejecutada":
            iteraciones += 1

    if inicio is None:
        tiempo_min = 0.0
    else:
        transcurrido = (ahora - inicio).total_seconds()
        neto = transcurrido - _ventanas_de_espera(eventos, ahora)
        tiempo_min = max(0.0, neto) / 60.0

    return {"costo": costo, "tiempo_min": tiempo_min, "iteraciones": iteraciones}


def verificar(store, run_id, definicion, ahora=None):
    """`None` si hay margen; `TechoAlcanzado` si algún techo se alcanzó.

    No escribe ningún evento: solo mide y responde.
    """
    actual = consumo(store, run_id, ahora=ahora)
    alcanzados = []
    for medida, campo_techo in TECHOS:
        limite = getattr(definicion, campo_techo)
        valor = actual[medida]
        if valor >= limite:
            alcanzados.append({"techo": medida, "valor": valor, "limite": limite})
    if not alcanzados:
        return None
    return TechoAlcanzado(alcanzados)


def registrar_consumo(store, run_id, costo):
    """Registra lo consumido en este momento. Es un delta, no el acumulado."""
    store.append(run_id, "consumo_registrado", "plataforma", {"costo": costo})
