"""Motor de Gates — T11.

El mecanismo que frena una corrida y espera una decisión humana. No decide
nada: abre, bloquea, registra la resolución y devuelve el control.

Un Gate abierto bloquea la corrida hasta que una persona lo resuelva. La única
forma de que un Gate deje de bloquear es `resolver`, y solo el CEO resuelve:
ninguna pieza puede resolver un Gate en nombre de una persona.

No calcula el descuento de las ventanas de espera — solo deja los eventos con
sus marcas de tiempo para que T12 lo haga.
"""

import argparse
import json
import sys

from operational_state import OperationalState

GATES = ("entrada", "salida")
DECISIONES = ("aprobado", "rechazado")
ACTOR = "CEO"


class GateInvalido(ValueError):
    """La operación sobre el Gate no procede. Nombra la corrida y el Gate."""


def _validar_nombre(gate):
    if gate not in GATES:
        raise GateInvalido("gate '%s' no existe; los de V0.1 son: %s." % (gate, ", ".join(GATES)))


def _abiertos_de(store, run_id):
    return [g for g in store.gates_pendientes() if g["run_id"] == run_id]


def _hubo_apertura(store, run_id, gate):
    return any(
        e["tipo"] == "gate_abierto" and e["payload"].get("gate") == gate
        for e in store.leer_run(run_id)
    )


def abrir(store, run_id, gate, somete):
    """Abre un Gate y bloquea la corrida.

    `somete` es el artefacto sometido íntegro: el pedido con sus techos, o el
    plan con el veredicto de T7.
    """
    _validar_nombre(gate)

    if _hubo_apertura(store, run_id, gate):
        raise GateInvalido(
            "la corrida %s ya abrió el Gate de %s; no se abre un segundo Gate del "
            "mismo tipo." % (run_id, gate)
        )

    if gate == "salida":
        previa = resolucion(store, run_id, "entrada")
        if previa is None or previa["decision"] != "aprobado":
            raise GateInvalido(
                "la corrida %s no puede abrir el Gate de salida: el de entrada no "
                "fue aprobado." % run_id
            )

    store.append(run_id, "gate_abierto", "plataforma", {"gate": gate, "somete": somete})


def _firmado_de(somete):
    """Los hashes de lo sometido, para repetirlos en la resolución. ADR-015 punto 2.

    **Se leen del `gate_abierto`, no se recalculan.** Es la diferencia entre
    firmar lo que se vio y firmar lo que hay ahora: si se recalcularan, un cambio
    entre la apertura y la resolución quedaría firmado sin que nadie lo note, que
    es exactamente lo que el hash existe para impedir.

    Devuelve una lista vacía cuando lo sometido no lleva archivos —el Gate de
    entrada somete el pedido, no una entrega—, y `resolver` la omite del payload.
    """
    if not isinstance(somete, dict):
        return []
    firmado = []
    for unidad in somete.get("unidades") or []:
        archivos = [
            {"ruta": a["ruta"], "sha256": a["sha256"]}
            for a in unidad.get("archivos") or []
            if isinstance(a, dict) and "sha256" in a
        ]
        if archivos:
            firmado.append({"unidad": unidad.get("unidad"), "archivos": archivos})
    return firmado


def resolver(store, run_id, gate, decision, motivo=None):
    """Registra la decisión humana sobre un Gate abierto.

    El actor es siempre el CEO. `motivo` es obligatorio si rechaza: un rechazo
    sin motivo no le sirve a nadie.

    Si lo sometido llevaba hashes, la resolución los repite: una aprobación que
    no nombra un objeto no es evidencia de nada. Se copian del evento de apertura
    porque `resolver` corre desde el CLI, en otro proceso que el grafo, y no tiene
    el estado a mano —y porque el evento es la única fuente que no puede diverger
    de lo que la persona miró—.
    """
    _validar_nombre(gate)

    if decision not in DECISIONES:
        raise GateInvalido(
            "decisión '%s' no válida para el Gate de %s de la corrida %s; las "
            "opciones son: %s." % (decision, gate, run_id, ", ".join(DECISIONES))
        )

    if decision == "rechazado" and (not isinstance(motivo, str) or not motivo.strip()):
        raise GateInvalido(
            "rechazar el Gate de %s de la corrida %s exige un motivo." % (gate, run_id)
        )

    abiertos = [g for g in _abiertos_de(store, run_id) if g["payload"].get("gate") == gate]
    if not abiertos:
        if _hubo_apertura(store, run_id, gate):
            raise GateInvalido(
                "el Gate de %s de la corrida %s ya fue resuelto; no se resuelve dos "
                "veces." % (gate, run_id)
            )
        raise GateInvalido(
            "el Gate de %s de la corrida %s no está abierto." % (gate, run_id)
        )

    payload = {"gate": gate, "decision": decision}
    if isinstance(motivo, str) and motivo.strip():
        payload["motivo"] = motivo
    firmado = _firmado_de(abiertos[-1]["payload"].get("somete"))
    if firmado:
        payload["firmado"] = firmado
    store.append(run_id, "gate_resuelto", ACTOR, payload)


def esta_bloqueada(store, run_id):
    """Verdadero mientras la corrida tenga algún Gate abierto sin resolver."""
    return bool(_abiertos_de(store, run_id))


def resolucion(store, run_id, gate):
    """La decisión registrada sobre un Gate, o None si todavía no la hay."""
    _validar_nombre(gate)
    encontrada = None
    for evento in store.leer_run(run_id):
        if evento["tipo"] != "gate_resuelto":
            continue
        if evento["payload"].get("gate") != gate:
            continue
        encontrada = {
            "decision": evento["payload"].get("decision"),
            "motivo": evento["payload"].get("motivo"),
        }
    return encontrada


def abiertos(store):
    """Todos los Gates abiertos sin resolver, de todas las corridas."""
    return store.gates_pendientes()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Motor de Gates (T11).")
    parser.add_argument("--listar", action="store_true", help="Muestra los Gates abiertos.")
    parser.add_argument("--resolver", metavar="RUN_ID", help="Corrida a resolver.")
    parser.add_argument("--gate", choices=list(GATES))
    parser.add_argument("--decision", choices=list(DECISIONES))
    parser.add_argument("--motivo")
    parser.add_argument("--db", help="Ruta del Operational State.")
    args = parser.parse_args(argv)

    store = OperationalState() if args.db is None else OperationalState(args.db)
    try:
        if args.listar:
            pendientes = abiertos(store)
            if not pendientes:
                print("No hay Gates abiertos.")
            for gate in pendientes:
                print(
                    "%s  corrida %s  Gate de %s  abierto desde %s"
                    % (gate["id"], gate["run_id"], gate["payload"].get("gate"), gate["ts"])
                )
                print("    somete: %s" % json.dumps(gate["payload"].get("somete"), ensure_ascii=False))
            return 0

        if args.resolver:
            if not args.gate or not args.decision:
                print("resolver exige --gate y --decision.", file=sys.stderr)
                return 2
            resolver(store, args.resolver, args.gate, args.decision, args.motivo)
            print("Gate de %s de la corrida %s: %s" % (args.gate, args.resolver, args.decision))
            return 0

        parser.print_help()
        return 2
    except GateInvalido as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    finally:
        store.cerrar()


if __name__ == "__main__":
    sys.exit(main())
