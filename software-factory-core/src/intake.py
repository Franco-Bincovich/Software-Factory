"""Formulario de Intake — T8.

Punto único de ingreso de pedidos a la fábrica. Es un mecanismo, no una Agent
Definition: no interpreta, no completa, no infiere. Valida y registra.

Un pedido inválido se rechaza **antes** de generar el `run_id`, así que no
consume nada y no deja corrida abierta. La interpretación de pedidos difusos
llega en V0.2 como Intake Agent.
"""

import argparse
import json
import sys

from operational_state import OperationalState

CAMPOS = (
    "que_se_quiere",
    "para_que",
    "alcance_excluido",
    "techo_costo_usd",
    "techo_tiempo_min",
    "techo_iteraciones",
)

TECHOS = ("techo_costo_usd", "techo_tiempo_min", "techo_iteraciones")


class PedidoRechazado(ValueError):
    """El pedido no entra. Lleva la lista completa de motivos."""

    def __init__(self, motivos):
        self.motivos = list(motivos)
        super().__init__("; ".join(self.motivos))


def _es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def validar(pedido):
    """Devuelve la lista de motivos de rechazo. Vacía si el pedido es válido.

    No corrige y no completa por defecto: solo dice qué campo y por qué.
    """
    motivos = []

    if not isinstance(pedido, dict):
        return ["el pedido debe ser un objeto JSON con los seis campos."]

    for campo in CAMPOS:
        if campo not in pedido:
            motivos.append("falta el campo '%s'." % campo)

    for campo in ("que_se_quiere", "para_que"):
        if campo in pedido:
            valor = pedido[campo]
            if not isinstance(valor, str) or not valor.strip():
                motivos.append("'%s' está vacío o es solo espacios." % campo)

    if "alcance_excluido" in pedido:
        valor = pedido["alcance_excluido"]
        if not isinstance(valor, list):
            motivos.append("'alcance_excluido' debe ser una lista.")
        else:
            for i, elemento in enumerate(valor):
                if not isinstance(elemento, str) or not elemento.strip():
                    motivos.append(
                        "'alcance_excluido[%d]' está vacío: un término excluido "
                        "vacío no excluye nada." % i
                    )

    for campo in TECHOS:
        if campo not in pedido:
            continue
        valor = pedido[campo]
        if not _es_numero(valor):
            motivos.append("'%s' no es numérico: %r." % (campo, valor))
        elif valor <= 0:
            motivos.append("'%s' debe ser mayor que cero; vale %r." % (campo, valor))

    if "techo_iteraciones" in pedido:
        valor = pedido["techo_iteraciones"]
        if _es_numero(valor) and not isinstance(valor, int):
            motivos.append("'techo_iteraciones' debe ser entero; vale %r." % valor)

    return motivos


def texto_rastreable(pedido):
    """El texto contra el que T7 evalúa su regla 4. Ni más ni menos.

    `alcance_excluido` y los techos no forman parte del texto rastreable.
    """
    return pedido["que_se_quiere"] + "\n" + pedido["para_que"]


def ingresar(pedido, store, agent_definition_id="requirement-agent", version="1.0"):
    """Valida el pedido y, si entra, abre la corrida. Devuelve el `run_id`.

    Si el pedido no valida levanta `PedidoRechazado` sin haber generado ningún
    `run_id` ni escrito ningún evento. No abre el Gate de entrada: eso es T11.
    """
    motivos = validar(pedido)
    if motivos:
        raise PedidoRechazado(motivos)

    run_id = store.nuevo_run_id()
    store.append(
        run_id,
        "run_iniciada",
        "plataforma",
        {"agent_definition_id": agent_definition_id, "version": version},
    )
    # Íntegro y sin normalizar: si el CEO escribió algo raro, queda como lo escribió.
    store.append(run_id, "pedido_recibido", "plataforma", pedido)
    store.append(
        run_id,
        "techos_declarados",
        "plataforma",
        {
            "costo": pedido["techo_costo_usd"],
            "tiempo": pedido["techo_tiempo_min"],
            "iteraciones": pedido["techo_iteraciones"],
        },
    )
    return run_id


def main(argv=None):
    parser = argparse.ArgumentParser(description="Formulario de Intake (T8).")
    parser.add_argument("--pedido", required=True, help="Ruta al pedido en JSON.")
    parser.add_argument("--db", default=None, help="Ruta del Operational State.")
    args = parser.parse_args(argv)

    with open(args.pedido, encoding="utf-8") as fh:
        pedido = json.load(fh)

    motivos = validar(pedido)
    if motivos:
        for motivo in motivos:
            print("rechazado: %s" % motivo, file=sys.stderr)
        return 1

    store = OperationalState() if args.db is None else OperationalState(args.db)
    try:
        print(ingresar(pedido, store))
    finally:
        store.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
