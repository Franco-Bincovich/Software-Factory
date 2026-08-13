"""Verificador estructural de Planes de Trabajo — T7.

Recibe un Plan de Trabajo y el texto del pedido que lo originó, y devuelve un
veredicto binario más la lista de incumplimientos. No corrige, no interpreta, no
completa: solo comprueba y localiza.

Evalúa las siete reglas siempre; no corta en el primer incumplimiento. Si el
plan no valida contra el esquema, devuelve regla 0 y no evalúa el resto.
"""

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA_PATH = RAIZ / "schema" / "plan-de-trabajo.schema.json"

PARTES_CRITERIO = ("condicion_observable", "resultado_esperado", "procedimiento")


def _incumplimiento(regla, detalle, unidad=None, criterio=None):
    return {"regla": regla, "unidad": unidad, "criterio": criterio, "detalle": detalle}


def cargar_esquema(ruta=SCHEMA_PATH):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


# --- Regla 0 — esquema ------------------------------------------------------


def _regla_0(plan, esquema):
    validador = Draft202012Validator(esquema)
    fallos = []
    for error in sorted(validador.iter_errors(plan), key=lambda e: list(e.absolute_path)):
        ruta = "/".join(str(p) for p in error.absolute_path) or "(raíz)"
        fallos.append(_incumplimiento(0, "%s: %s" % (ruta, error.message)))
    return fallos


# --- Reglas 1 a 7 -----------------------------------------------------------


def _regla_1(plan):
    """Toda unidad tiene al menos un criterio."""
    return [
        _incumplimiento(1, "La unidad no declara ningún Acceptance Criterion.", unidad=u["id"])
        for u in plan["unidades"]
        if not u["criterios"]
    ]


def _regla_2(plan):
    """Todo criterio tiene las tres partes, presentes y no vacías."""
    fallos = []
    for u in plan["unidades"]:
        for i, criterio in enumerate(u["criterios"]):
            for parte in PARTES_CRITERIO:
                valor = criterio.get(parte)
                if valor is None:
                    detalle = "Falta la parte '%s' del criterio." % parte
                elif not str(valor).strip():
                    detalle = "La parte '%s' del criterio está vacía." % parte
                else:
                    continue
                fallos.append(_incumplimiento(2, detalle, unidad=u["id"], criterio=i))
    return fallos


def _regla_3(plan):
    """Cada id de dependencias está en unidades."""
    existentes = {u["id"] for u in plan["unidades"]}
    fallos = []
    for u in plan["unidades"]:
        for dep in u["dependencias"]:
            if dep not in existentes:
                fallos.append(
                    _incumplimiento(
                        3,
                        "La dependencia '%s' no corresponde a ninguna unidad del plan." % dep,
                        unidad=u["id"],
                    )
                )
    return fallos


def _regla_4(plan, pedido):
    """El texto de rastreo aparece literal en el pedido."""
    return [
        _incumplimiento(
            4,
            "El rastreo '%s' no aparece literal en el pedido." % u["rastreo"],
            unidad=u["id"],
        )
        for u in plan["unidades"]
        if u["rastreo"] not in pedido
    ]


def _regla_5(plan):
    """Ningún término de alcance_excluido aparece en enunciado ni artefacto_esperado."""
    excluidos = plan["restricciones"]["alcance_excluido"]
    fallos = []
    for u in plan["unidades"]:
        for campo in ("enunciado", "artefacto_esperado"):
            texto = u[campo].casefold()
            for termino in excluidos:
                if termino.casefold() in texto:
                    fallos.append(
                        _incumplimiento(
                            5,
                            "El término excluido '%s' aparece en '%s'." % (termino, campo),
                            unidad=u["id"],
                        )
                    )
    return fallos


def _regla_6(plan):
    """El plan no supera diez unidades."""
    cantidad = len(plan["unidades"])
    if cantidad <= 10:
        return []
    return [_incumplimiento(6, "El plan declara %d unidades de trabajo; el máximo es 10." % cantidad)]


def _regla_7(plan):
    """Sin ciclos: el grafo de dependencias admite orden topológico.

    Solo se consideran las aristas entre unidades que existen. Una dependencia
    hacia una unidad inexistente es materia de la regla 3, no de ésta.
    """
    existentes = {u["id"] for u in plan["unidades"]}
    aristas = {
        u["id"]: [d for d in u["dependencias"] if d in existentes] for u in plan["unidades"]
    }

    def alcanza_a_si_misma(inicio):
        pila = list(aristas[inicio])
        visto = set()
        while pila:
            actual = pila.pop()
            if actual == inicio:
                return True
            if actual in visto:
                continue
            visto.add(actual)
            pila.extend(aristas.get(actual, []))
        return False

    # Solo las unidades que participan del ciclo, no las que quedan aguas abajo:
    # nombrar a estas ultimas mandaria a corregir unidades que no estan mal.
    en_ciclo = {uid for uid in aristas if alcanza_a_si_misma(uid)}
    if not en_ciclo:
        return []
    implicadas = ", ".join(sorted(en_ciclo))
    return [
        _incumplimiento(
            7, "El grafo de dependencias tiene un ciclo entre las unidades: %s." % implicadas
        )
    ]


# --- Orquestación -----------------------------------------------------------


def verificar(plan, pedido, esquema=None):
    """Devuelve el veredicto del plan en el formato declarado por la spec."""
    esquema = cargar_esquema() if esquema is None else esquema

    fallos_esquema = _regla_0(plan, esquema)
    if fallos_esquema:
        return {"valido": False, "incumplimientos": fallos_esquema}

    incumplimientos = []
    incumplimientos += _regla_1(plan)
    incumplimientos += _regla_2(plan)
    incumplimientos += _regla_3(plan)
    incumplimientos += _regla_4(plan, pedido)
    incumplimientos += _regla_5(plan)
    incumplimientos += _regla_6(plan)
    incumplimientos += _regla_7(plan)

    incumplimientos.sort(
        key=lambda i: (i["regla"], i["unidad"] or "", -1 if i["criterio"] is None else i["criterio"])
    )
    return {"valido": not incumplimientos, "incumplimientos": incumplimientos}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verificador estructural de Planes de Trabajo (T7)."
    )
    parser.add_argument("plan", help="Ruta al Plan de Trabajo en JSON.")
    parser.add_argument(
        "--pedido",
        required=True,
        help="Ruta al texto del pedido original. Lo exige la regla 4.",
    )
    args = parser.parse_args(argv)

    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    with open(args.pedido, encoding="utf-8") as fh:
        pedido = fh.read()

    veredicto = verificar(plan, pedido)
    print(json.dumps(veredicto, ensure_ascii=False, indent=2))
    return 0 if veredicto["valido"] else 1


if __name__ == "__main__":
    sys.exit(main())
