"""Verificador estructural de Entregas del Developer.

El par de T7 para código. Recibe una Entrega y el Plan de Trabajo que la
originó, y devuelve un veredicto binario más la lista de incumplimientos. No
corrige, no interpreta, no completa: comprueba y localiza. **No ejecuta nada de
lo que verifica.**

Evalúa todas las reglas siempre; no corta en el primer incumplimiento. Esa lista
completa es lo que alimenta el prompt de corrección del reintento, igual que en
T7. Si la entrega no valida contra el esquema, devuelve C0 y no evalúa el resto.

Los identificadores dicen de dónde sale cada regla: `C` las nueve reglas de
validez del Contrato de Entrega, `R` el Ruleset mecánico con su propio número,
`P` las prohibiciones del contrato, y `V` lo que este verificador comprueba y no
tiene número en ningún documento.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

import inspeccion_js as ins

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA_PATH = RAIZ / "schema" / "entrega.schema.json"

MARCADORES_FRAGMENTO = (
    "resto igual", "el resto igual", "resto del archivo", "sin cambios",
    "resto sin cambios", "idem", "omitido", "omitimos", "unchanged",
    "rest of file", "same as before", "etc.",
)
RE_LINEA_PUNTOS = re.compile(r"^\s*(?://\s*|/\*\s*|<!--\s*|#\s*)?(?:\.{3}|…)\s*(?:\*/|-->)?\s*$")
RE_RUTA_EN_TEXTO = re.compile(r"[\w.\-/]+\.[A-Za-z]{1,5}\b")
RE_BACKTICK = re.compile(r"`([^`]+)`")
RE_IDENTIFICADOR = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b|\b[a-z]+(?:[A-Z][a-z0-9]*)+\b")


def _incumplimiento(regla, detalle, archivo=None):
    return {"regla": regla, "archivo": archivo, "detalle": detalle}


def cargar_esquema(ruta=SCHEMA_PATH):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def _base(ruta):
    return ruta.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


# --- C0 — esquema -----------------------------------------------------------


def _c0(entrega, esquema):
    validador = Draft202012Validator(esquema)
    fallos = []
    for error in sorted(validador.iter_errors(entrega), key=lambda e: list(e.absolute_path)):
        ruta = "/".join(str(p) for p in error.absolute_path) or "(raíz)"
        fallos.append(_incumplimiento("C0", "%s: %s" % (ruta, error.message)))
    return fallos


# --- Identificación de los cuatro entregables -------------------------------


def _entregables(archivos):
    """Qué archivo cumple cada uno de los cuatro roles. `None` el que falte."""
    hallado = {"logica": None, "pruebas": None, "pruebas_html": None, "demo_html": None}
    for archivo in archivos:
        ruta = archivo["ruta"]
        base = _base(ruta).lower()
        if base == "pruebas.html":
            hallado["pruebas_html"] = hallado["pruebas_html"] or archivo
        elif base == "demo.html":
            hallado["demo_html"] = hallado["demo_html"] or archivo
        elif ins.es_js(ruta):
            es_prueba = "test" in base or "spec" in base or ruta.replace("\\", "/").startswith("tests/")
            clave = "pruebas" if es_prueba else "logica"
            hallado[clave] = hallado[clave] or archivo
    return hallado


NOMBRE_ENTREGABLE = {
    "logica": "el código de la lógica",
    "pruebas": "el archivo de pruebas",
    "pruebas_html": "pruebas.html",
    "demo_html": "demo.html",
}


# --- Reglas del Contrato de Entrega — C1 a C8 -------------------------------


def _c1(entrega, plan):
    ids = {u["id"] for u in plan["unidades"]}
    if entrega["unidad"] in ids:
        return []
    return [
        _incumplimiento(
            "C1",
            "La entrega declara la unidad '%s', que no existe en el plan. Unidades del plan: %s."
            % (entrega["unidad"], ", ".join(sorted(ids)) or "ninguna"),
        )
    ]


def _c2(entrega):
    """Ruta relativa, sin `..` y sin segmentos vacíos."""
    fallos = []
    for archivo in entrega["archivos"]:
        ruta = archivo["ruta"]
        normalizada = ruta.replace("\\", "/")
        if not ruta.strip():
            fallos.append(_incumplimiento("C2", "Hay un archivo con la ruta vacía.", archivo=ruta))
            continue
        if normalizada.startswith("/") or re.match(r"^[A-Za-z]:", ruta):
            fallos.append(
                _incumplimiento("C2", "La ruta es absoluta; tiene que ser relativa.", archivo=ruta)
            )
        if ".." in normalizada.split("/"):
            fallos.append(
                _incumplimiento(
                    "C2", "La ruta contiene '..', que es escribir fuera del directorio de trabajo.", archivo=ruta
                )
            )
    return fallos


def _c3(entrega):
    """Contenido completo: sin marcadores de fragmento."""
    fallos = []
    for archivo in entrega["archivos"]:
        for numero, linea in enumerate(archivo["contenido"].splitlines(), start=1):
            marcador = None
            if RE_LINEA_PUNTOS.match(linea):
                marcador = linea.strip()
            else:
                minuscula = linea.casefold()
                for frase in MARCADORES_FRAGMENTO:
                    if frase in minuscula:
                        marcador = frase
                        break
            if marcador:
                fallos.append(
                    _incumplimiento(
                        "C3",
                        "Línea %d: '%s' es un marcador de fragmento. El contenido "
                        "tiene que venir completo." % (numero, marcador),
                        archivo=archivo["ruta"],
                    )
                )
                break
    return fallos


def _c4(entrega, unidad):
    """El artefacto que la unidad declaró esperar está en la entrega."""
    if unidad is None:
        return []
    fallos = []
    if not any(a["rol"] == "artefacto_esperado" for a in entrega["archivos"]):
        fallos.append(
            _incumplimiento("C4", "Ningún archivo de la entrega está declarado como artefacto esperado.")
        )
    esperadas = [
        token for token in RE_RUTA_EN_TEXTO.findall(unidad["artefacto_esperado"])
        if "/" in token or ins.es_js(token) or ins.es_html(token)
    ]
    entregadas = {a["ruta"].replace("\\", "/") for a in entrega["archivos"]}
    bases = {_base(r) for r in entregadas}
    for esperada in esperadas:
        limpia = esperada.replace("\\", "/")
        if limpia in entregadas or _base(limpia) in bases:
            continue
        fallos.append(
            _incumplimiento(
                "C4",
                "La unidad %s declara el artefacto esperado '%s' y la entrega no lo trae."
                % (unidad["id"], esperada),
            )
        )
    return fallos


def _c5(entrega, entregables):
    """Lo que no es uno de los cuatro entregables se declara auxiliar y se justifica."""
    delos_cuatro = {a["ruta"] for a in entregables.values() if a is not None}
    fallos = []
    for archivo in entrega["archivos"]:
        if archivo["rol"] == "auxiliar":
            if not archivo.get("motivo", "").strip():
                fallos.append(
                    _incumplimiento(
                        "C5", "El archivo se declara auxiliar y no dice por qué.", archivo=archivo["ruta"]
                    )
                )
        elif archivo["ruta"] not in delos_cuatro:
            fallos.append(
                _incumplimiento(
                    "C5",
                    "El archivo no es ninguno de los cuatro entregables y no está "
                    "declarado auxiliar: ninguna unidad lo pidió.",
                    archivo=archivo["ruta"],
                )
            )
    return fallos


def _entrega_vacia(entrega):
    """La entrega vacía del contrato: unidad ambigua, motivo declarado, sin archivos.

    Corta como corta C0, y por la misma razón que aquella: no hay nada que
    corregir. El contrato la declara una entrega válida que dispara escalamiento,
    así que apilarle el resto de las reglas sería mandar a reintentar lo que no
    se reintenta.
    """
    motivo = "; ".join(entrega["supuestos"]) or "sin motivo declarado"
    return [
        _incumplimiento(
            "C6",
            "La entrega viene vacía (%s). Una entrega vacía no se corrige: "
            "corresponde escalamiento, no reintento." % motivo,
        )
    ]


def _c6(entrega, entregables):
    """Los cuatro entregables presentes y ninguno vacío."""
    fallos = []
    for clave, archivo in entregables.items():
        nombre = NOMBRE_ENTREGABLE[clave]
        if archivo is None:
            fallos.append(_incumplimiento("C6", "Falta %s." % nombre))
        elif not archivo["contenido"].strip():
            fallos.append(
                _incumplimiento("C6", "%s está vacío." % nombre.capitalize(), archivo=archivo["ruta"])
            )
    return fallos


def _c7(entregables, funciones):
    """Los dos HTML cargan el archivo de lógica y ninguno lo reimplementa."""
    logica = entregables["logica"]
    if logica is None:
        return []
    base_logica = _base(logica["ruta"])
    fallos = []
    for clave in ("pruebas_html", "demo_html"):
        archivo = entregables[clave]
        if archivo is None:
            continue
        contenido = archivo["contenido"]
        if base_logica not in {_base(src) for src in ins.scripts_externos(contenido)}:
            fallos.append(
                _incumplimiento(
                    "C7",
                    "No carga la lógica con <script src>: '%s' no aparece entre sus "
                    "scripts externos." % logica["ruta"],
                    archivo=archivo["ruta"],
                )
            )
        inline = "\n".join(ins.scripts_inline(contenido))
        repetidas = sorted(set(ins.funciones_declaradas(inline)) & set(funciones))
        if repetidas:
            fallos.append(
                _incumplimiento(
                    "C7",
                    "Reimplementa la lógica: declara %s, que ya está en '%s'."
                    % (", ".join(repetidas), logica["ruta"]),
                    archivo=archivo["ruta"],
                )
            )
    return fallos


def _c8(entrega):
    vistas, repetidas = set(), []
    for archivo in entrega["archivos"]:
        ruta = archivo["ruta"].replace("\\", "/")
        if ruta in vistas and ruta not in repetidas:
            repetidas.append(ruta)
        vistas.add(ruta)
    return [
        _incumplimiento("C8", "La entrega trae dos archivos con la misma ruta.", archivo=ruta)
        for ruta in repetidas
    ]


# --- V2 — los nombres de los criterios aparecen en el código ----------------


def _tokens_de_criterios(unidad):
    """Lo que en un criterio tiene forma de identificador: backticks, camelCase, snake_case.

    **Parcial y deliberadamente angosto.** Los criterios son prosa; exigir que
    cada palabra aparezca en el código produciría incumplimientos inventados. Si
    la unidad no nombra identificadores, esta regla no encuentra nada y pasa en
    vacío — está declarado en la spec.
    """
    tokens = set()
    for criterio in unidad["criterios"]:
        for parte in ("condicion_observable", "resultado_esperado", "procedimiento"):
            texto = criterio.get(parte) or ""
            for entre_comillas in RE_BACKTICK.findall(texto):
                candidato = entre_comillas.strip()
                if RE_IDENTIFICADOR.fullmatch(candidato):
                    tokens.add(candidato)
            tokens.update(RE_IDENTIFICADOR.findall(texto))
    return tokens


def _v2(entrega, unidad):
    if unidad is None:
        return []
    codigo = "\n".join(a["contenido"] for a in entrega["archivos"])
    faltantes = sorted(t for t in _tokens_de_criterios(unidad) if t not in codigo)
    return [
        _incumplimiento(
            "V2",
            "Los criterios de la unidad %s nombran '%s' y no aparece en el código entregado."
            % (unidad["id"], token),
        )
        for token in faltantes
    ]


# --- Orquestación -----------------------------------------------------------


def verificar(entrega, plan, esquema=None):
    """Devuelve el veredicto de la entrega. No ejecuta nada de lo que revisa."""
    esquema = cargar_esquema() if esquema is None else esquema

    fallos_esquema = _c0(entrega, esquema)
    if fallos_esquema:
        return {"valido": False, "incumplimientos": fallos_esquema}

    if not entrega["archivos"]:
        return {"valido": False, "incumplimientos": _entrega_vacia(entrega)}

    unidad = next((u for u in plan["unidades"] if u["id"] == entrega["unidad"]), None)
    entregables = _entregables(entrega["archivos"])
    logica = entregables["logica"]
    funciones = ins.funciones_declaradas(logica["contenido"]) if logica else []

    incumplimientos = []
    incumplimientos += _c1(entrega, plan)
    incumplimientos += _c2(entrega)
    incumplimientos += _c3(entrega)
    incumplimientos += _c4(entrega, unidad)
    incumplimientos += _c5(entrega, entregables)
    incumplimientos += _c6(entrega, entregables)
    incumplimientos += _c7(entregables, funciones)
    incumplimientos += _c8(entrega)
    incumplimientos += _v2(entrega, unidad)

    for archivo in entrega["archivos"]:
        ruta, contenido = archivo["ruta"], archivo["contenido"]
        incumplimientos += ins.v1_sintaxis(ruta, contenido)
        incumplimientos += ins.r1_tamano(ruta, contenido)
        incumplimientos += ins.r3_patrones_prohibidos(ruta, contenido)
        incumplimientos += ins.prohibiciones(ruta, contenido)

    if entregables["pruebas"] is not None:
        incumplimientos += ins.r8_tests(
            entregables["pruebas"]["ruta"], entregables["pruebas"]["contenido"], funciones
        )
    if entregables["pruebas_html"] is not None:
        pruebas_html = entregables["pruebas_html"]
        incumplimientos += ins.v3_invoca_la_funcion(
            pruebas_html["ruta"], pruebas_html["contenido"], funciones
        )
        incumplimientos += ins.v4_veredictos_fijos(pruebas_html["ruta"], pruebas_html["contenido"])

    incumplimientos.sort(key=lambda i: (i["regla"], i["archivo"] or "", i["detalle"]))
    return {"valido": not incumplimientos, "incumplimientos": incumplimientos}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verificador estructural de Entregas del Developer."
    )
    parser.add_argument("entrega", help="Ruta a la Entrega en JSON.")
    parser.add_argument(
        "--plan",
        required=True,
        help="Ruta al Plan de Trabajo que originó la entrega. Lo exigen C1, C4 y V2.",
    )
    args = parser.parse_args(argv)

    with open(args.entrega, encoding="utf-8") as fh:
        entrega = json.load(fh)
    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)

    veredicto = verificar(entrega, plan)
    print(json.dumps(veredicto, ensure_ascii=False, indent=2))
    return 0 if veredicto["valido"] else 1


if __name__ == "__main__":
    sys.exit(main())
