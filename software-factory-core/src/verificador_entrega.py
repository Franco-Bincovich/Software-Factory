"""Verificador estructural de Entregas del Developer.

El par de T7 para código. Recibe una Entrega y el Plan de Trabajo que la
originó, y devuelve un veredicto binario más la lista de incumplimientos. No
corrige, no interpreta, no completa: comprueba y localiza. **No ejecuta nada de
lo que verifica.**

Evalúa todas las reglas siempre; no corta en el primer incumplimiento. Esa lista
completa es lo que alimenta el prompt de corrección del reintento, igual que en
T7. Si la entrega no valida contra el esquema, devuelve C0 y no evalúa el resto.

Los identificadores dicen de dónde sale cada regla: `C` las diez reglas de
validez del Contrato de Entrega, `R` el Ruleset mecánico con su propio número,
`P` las prohibiciones del contrato, y `V` lo que este verificador comprueba y no
tiene número en ningún documento.

## El inventario del espacio — ADR-019

Desde ADR-019 las unidades de un plan son partes sucesivas sobre un mismo espacio
de trabajo que crece, así que verificar una entrega mirándola sola dejó de
alcanzar. El parámetro `inventario` trae lo que las partes anteriores ya
depositaron —ruta, contenido, hash y parte firmante— y tres reglas lo consultan:

- **C6** exige los cuatro entregables **en el espacio**, no en la entrega. Una
  parte cuyo trabajo es agregar pruebas cumple con la lógica que dejó la anterior.
- **C7** exige que los agregadores carguen **toda** la lógica del espacio, no sólo
  la de esta parte. Es lo que paga la excepción que C10 les da.
- **C10** rechaza volver a escribir un archivo de contenido que ya está.

Sin inventario —el verificador corrido a mano, o la primera parte de una cadena—
las tres se comportan como antes de ADR-019, que es el caso de una parte única.
"""

import argparse
import hashlib
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
RE_BACKTICK = re.compile(r"`([^`]+)`")
RE_IDENTIFICADOR = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b|\b[a-z]+(?:[A-Z][a-z0-9]*)+\b")


# Los identificadores que este verificador puede emitir. C9 no está: la cumple el
# esquema con `additionalProperties: false`, así que un campo de más sale como C0.
#
# Existe para que el prompt del productor de entregas no se desvíe de lo que acá
# se comprueba de verdad: hay un test que exige que el prompt nombre cada uno.
REGLAS = (
    "C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C10",
    "R1", "R3", "R8",
    "P1", "P2", "P3",
    "V1", "V2", "V3", "V4", "V5",
)

# Los dos agregadores del Contrato de Entrega. Existen para mostrar todo lo que
# hay en el espacio, así que la parte que agrega lógica los reescribe enteros o
# dejan de mostrar lo nuevo: son la única excepción a C10.
#
# **La distinción es por nombre y la declara el contrato**, no la decide este
# código mirando el archivo. Una heurística que adivinara qué es un agregador se
# equivoca el día que alguien llame `index.html` a la lógica.
AGREGADORES = ("pruebas.html", "demo.html")


def _incumplimiento(regla, detalle, archivo=None):
    return {"regla": regla, "archivo": archivo, "detalle": detalle}


def cargar_esquema(ruta=SCHEMA_PATH):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def _base(ruta):
    return ruta.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _normal(ruta):
    return ruta.replace("\\", "/")


def _sha256(contenido):
    """El mismo hash que `deposito.sha256_de`, calculado sin importar el depósito.

    Este módulo es un verificador que no toca disco ni Operational State, y se
    corre a mano por línea de comandos. Traerse `deposito` para una línea de
    `hashlib` le colgaría esa cadena de imports encima.
    """
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def _es_agregador(ruta):
    return _base(ruta).lower() in AGREGADORES


def es_prueba(ruta):
    normalizada = _normal(ruta)
    base = _base(normalizada).lower()
    return "test" in base or "spec" in base or normalizada.startswith("tests/")


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
            clave = "pruebas" if es_prueba(ruta) else "logica"
            hallado[clave] = hallado[clave] or archivo
    return hallado


def _logicas(archivos):
    """**Todos** los archivos de lógica, no el primero.

    `_entregables` devuelve uno solo porque describe los cuatro roles del
    contrato, y hasta ADR-019 no había más que uno por unidad aislada. En un
    espacio que acumula, la parte 2 deja su lógica al lado de la de la parte 1 y
    los agregadores tienen que cargar las dos.

    Los auxiliares quedan afuera. Un `.js` declarado auxiliar existe por el
    motivo que C5 le exige declarar y no es uno de los cuatro entregables:
    exigirle a los agregadores que lo carguen sería inventar un incumplimiento
    de C7 cada vez que una entrega trae un archivo de apoyo.
    """
    return [
        a for a in archivos
        if ins.es_js(a["ruta"])
        and not es_prueba(a["ruta"])
        and a.get("rol") != "auxiliar"
    ]


def _archivos_del_espacio(entrega, inventario):
    """Cómo queda el espacio si esta entrega se deposita.

    Los archivos de la entrega van primero y ganan la ruta: son lo que esta parte
    produjo, y C10 ya rechazó los casos en que pisar lo anterior no es legítimo.
    """
    propias = {_normal(a["ruta"]) for a in entrega["archivos"]}
    return list(entrega["archivos"]) + [
        a for a in inventario if _normal(a["ruta"]) not in propias
    ]


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
    """El artefacto que la unidad declaró esperar está en la entrega.

    **La ruta se lee de `ruta_artefacto`, no de la prosa.** Hasta ADR-020 esta
    regla sacaba rutas del texto de `artefacto_esperado` con una expresión
    regular, y erraba en las dos direcciones a la vez: exigía
    `src/validate_email.py` porque el plan lo había escrito precedido de "ej.",
    y descartaba `validador.py` —que sí era la ruta que el plan quería— porque
    no tenía barra. La información para distinguir un ejemplo de una decisión no
    está en el texto, así que ninguna expresión regular mejor la iba a sacar.

    `ruta_artefacto` en `null` es una decisión del plan: no fija la ruta. Sólo
    queda en pie la primera mitad de la regla —que algo venga declarado como
    artefacto esperado—, que es la que no depende de saber cuál.

    **La ruta se compara entera, sin caer al nombre de archivo.** Antes
    `src/a.js` satisfacía a `lib/a.js`, y eso tenía sentido cuando cada unidad
    trabajaba en su propio subdirectorio y el prefijo era ruido. Con el espacio
    único de ADR-019 el prefijo es parte de la decisión, y aceptar otro sería
    volver a convertir la ruta declarada en una sugerencia.
    """
    if unidad is None:
        return []
    fallos = []
    if not any(a["rol"] == "artefacto_esperado" for a in entrega["archivos"]):
        fallos.append(
            _incumplimiento("C4", "Ningún archivo de la entrega está declarado como artefacto esperado.")
        )
    esperada = unidad.get("ruta_artefacto")
    if not esperada:
        return fallos
    entregadas = {_normal(a["ruta"]) for a in entrega["archivos"]}
    if _normal(esperada) not in entregadas:
        fallos.append(
            _incumplimiento(
                "C4",
                "La unidad %s declara la ruta '%s' para su artefacto y la entrega "
                "no la trae." % (unidad["id"], esperada),
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


def _c6(en_el_espacio):
    """Los cuatro entregables presentes en el espacio y ninguno vacío.

    **En el espacio, no en la entrega.** Por ADR-019 los cuatro son de la cadena:
    una parte cuyo trabajo es agregar pruebas cumple con la lógica que dejó la
    anterior, y exigirle que la vuelva a traer sería exigirle que viole C10.
    """
    fallos = []
    for clave, archivo in en_el_espacio.items():
        nombre = NOMBRE_ENTREGABLE[clave]
        if archivo is None:
            fallos.append(_incumplimiento("C6", "Falta %s en el espacio de trabajo." % nombre))
        elif not archivo["contenido"].strip():
            fallos.append(
                _incumplimiento("C6", "%s está vacío." % nombre.capitalize(), archivo=archivo["ruta"])
            )
    return fallos


def _c7(entregables, logicas, funciones):
    """Los agregadores cargan toda la lógica del espacio y ninguno la reimplementa.

    **Toda, no la de esta parte.** Es lo que paga la excepción que C10 les da:
    si se los exceptúa de no reescribir porque agregan, entonces tienen que
    agregar. Un `pruebas.html` de la parte 2 que sólo cargue la lógica de la
    parte 2 no reescribió el resumen, lo achicó.
    """
    if not logicas:
        return []
    fallos = []
    for clave in ("pruebas_html", "demo_html"):
        archivo = entregables[clave]
        if archivo is None:
            continue
        contenido = archivo["contenido"]
        cargados = {_base(src) for src in ins.scripts_externos(contenido)}
        for logica in logicas:
            if _base(logica["ruta"]) in cargados:
                continue
            fallos.append(
                _incumplimiento(
                    "C7",
                    "No carga la lógica con <script src>: '%s' no aparece entre sus "
                    "scripts externos." % logica["ruta"],
                    archivo=archivo["ruta"],
                )
            )
        inline = "\n".join(ins.scripts_inline(contenido))
        for nombre in sorted(set(ins.funciones_declaradas(inline)) & set(funciones)):
            fallos.append(
                _incumplimiento(
                    "C7",
                    "Reimplementa la lógica: declara %s, que ya está en '%s'."
                    % (nombre, funciones[nombre]),
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


def _c10(entrega, inventario):
    """Ningún archivo de contenido repite una ruta que otra parte ya depositó.

    Las dos ramas son fallas distintas y el detalle las distingue, porque lo que
    el Developer tiene que hacer también es distinto:

    - **Mismo hash: duplicar.** El trabajo ya estaba hecho. Se saca el archivo de
      la entrega y listo; el archivo sigue estando en el espacio.
    - **Hash distinto: modificar lo firmado.** No se corrige sacando nada: o la
      parte se replantea para agregar en vez de pisar, o —si la unidad no se
      puede hacer sin reabrir lo aprobado— escala, que es el punto 6 de ADR-019.

    Los dos agregadores quedan exceptuados **por nombre**, ver `AGREGADORES`.
    """
    ya_esta = {_normal(a["ruta"]): a for a in inventario}
    fallos = []
    for archivo in entrega["archivos"]:
        ruta = _normal(archivo["ruta"])
        anterior = ya_esta.get(ruta)
        if anterior is None or _es_agregador(ruta):
            continue
        if anterior["sha256"] == _sha256(archivo["contenido"]):
            fallos.append(
                _incumplimiento(
                    "C10",
                    "La parte %s ya depositó este archivo con el mismo contenido. "
                    "No lo entregues de nuevo: ya está en el espacio de trabajo y "
                    "podés usarlo tal como está." % anterior["parte"],
                    archivo=ruta,
                )
            )
        else:
            fallos.append(
                _incumplimiento(
                    "C10",
                    "La parte %s ya depositó este archivo y esta entrega lo "
                    "reescribe con otro contenido. Lo aprobado no se reabre: "
                    "agregá archivos propios en vez de modificarlo, y si la unidad "
                    "no se puede hacer sin reabrirlo, entregá vacío declarando ese "
                    "motivo para que la decisión escale." % anterior["parte"],
                    archivo=ruta,
                )
            )
    return fallos


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


def verificar(entrega, plan, esquema=None, inventario=None):
    """Devuelve el veredicto de la entrega. No ejecuta nada de lo que revisa.

    `inventario` es lo que las partes anteriores dejaron en el espacio de trabajo:
    una lista de `{ruta, contenido, sha256, parte}`. Ver el encabezado del módulo.
    """
    esquema = cargar_esquema() if esquema is None else esquema
    inventario = inventario or []

    fallos_esquema = _c0(entrega, esquema)
    if fallos_esquema:
        return {"valido": False, "incumplimientos": fallos_esquema}

    if not entrega["archivos"]:
        return {"valido": False, "incumplimientos": _entrega_vacia(entrega)}

    unidad = next((u for u in plan["unidades"] if u["id"] == entrega["unidad"]), None)
    entregables = _entregables(entrega["archivos"])
    espacio = _archivos_del_espacio(entrega, inventario)
    en_el_espacio = _entregables(espacio)
    logicas = _logicas(espacio)
    # Nombre de función -> archivo del espacio que la declara. C7 lo necesita
    # para decir en cuál está la que el agregador reimplementó; R8 y V3 sólo
    # miran los nombres, y les alcanza con que la lógica sea la del espacio.
    funciones = {
        nombre: logica["ruta"]
        for logica in logicas
        for nombre in ins.funciones_declaradas(logica["contenido"])
    }
    nombres = list(funciones)

    incumplimientos = []
    incumplimientos += _c1(entrega, plan)
    incumplimientos += _c2(entrega)
    incumplimientos += _c3(entrega)
    incumplimientos += _c4(entrega, unidad)
    incumplimientos += _c5(entrega, entregables)
    incumplimientos += _c6(en_el_espacio)
    incumplimientos += _c7(entregables, logicas, funciones)
    incumplimientos += _c8(entrega)
    incumplimientos += _c10(entrega, inventario)
    incumplimientos += _v2(entrega, unidad)

    for archivo in entrega["archivos"]:
        ruta, contenido = archivo["ruta"], archivo["contenido"]
        incumplimientos += ins.v1_sintaxis(ruta, contenido)
        incumplimientos += ins.r1_tamano(ruta, contenido)
        incumplimientos += ins.r3_patrones_prohibidos(ruta, contenido)
        incumplimientos += ins.prohibiciones(ruta, contenido)
        incumplimientos += ins.v5_autocontencion(ruta, contenido)

    if entregables["pruebas"] is not None:
        incumplimientos += ins.r8_tests(
            entregables["pruebas"]["ruta"], entregables["pruebas"]["contenido"], nombres
        )
    if entregables["pruebas_html"] is not None:
        pruebas_html = entregables["pruebas_html"]
        incumplimientos += ins.v3_invoca_la_funcion(
            pruebas_html["ruta"], pruebas_html["contenido"], nombres
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
