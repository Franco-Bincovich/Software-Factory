"""Verificador estructural de Planes de Trabajo — T7.

Recibe un Plan de Trabajo y el texto del pedido que lo originó, y devuelve un
veredicto binario más la lista de incumplimientos. No corrige, no interpreta, no
completa: solo comprueba y localiza.

Evalúa las nueve reglas siempre; no corta en el primer incumplimiento. Si el
plan no valida contra el esquema, devuelve regla 0 y no evalúa el resto.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA_PATH = RAIZ / "schema" / "plan-de-trabajo.schema.json"

PARTES_CRITERIO = ("condicion_observable", "resultado_esperado", "procedimiento")

#: El lenguaje que el Developer Agent sabe producir. Es un hecho de la Fábrica,
#: no una decisión de cada corrida: el [[Contrato de Entrega del Developer]] lo
#: cierra a favor de JavaScript en V0.2 porque `pruebas.html` ejecuta la lógica
#: real sin servidor, y eso obliga a que un navegador la pueda cargar.
#:
#: Está acá y no se lee del contrato a propósito. Que el verificador de planes
#: importe el contrato del Developer es acoplamiento nuevo por diez palabras;
#: la desincronización la vigila un test que compara los dos sin que ninguno
#: dependa del otro, el mismo patrón de `test_conteos_declarados.py`.
LENGUAJE_DE_LA_FABRICA = "JavaScript"

#: Vocabulario cerrado de lo que la Fábrica **no** puede producir mientras
#: V0.2 esté cerrada a JavaScript. Lenguajes y sus herramientas de prueba.
#:
#: Es una lista declarada, no una detección. No se intenta inferir el lenguaje
#: de un plan —eso es adivinar, y una regla que adivina se equivoca en silencio—:
#: se prohíben términos nombrados uno por uno, y el día que V0.3 abra otro
#: lenguaje se saca de acá deliberadamente.
#:
#: **Lo que quedó afuera y por qué.** `cargo` es "a cargo de" en castellano.
#: `go` y `gem` son palabras corrientes. `py` es demasiado corto para tener
#: sentido solo. Un falso positivo acá cuesta un plan rechazado y una iteración
#: pagada, así que un término ambiguo se deja pasar antes que arriesgarlo.
TERMINOS_AJENOS = (
    "python", "pytest", "unittest", "pip", "django", "flask",
    "java", "junit", "maven", "gradle", "kotlin",
    "ruby", "rspec", "rails",
    "rust",
    "golang",
    "php", "phpunit", "laravel",
    "swift", "xctest",
    "csharp", "dotnet", "nunit",
)

#: Extensiones de archivo de esos mismos lenguajes. Van aparte porque se
#: comparan distinto: un término se busca entre bordes de palabra, y una
#: extensión no tiene borde a la izquierda —el punto viene pegado al nombre—.
EXTENSIONES_AJENAS = (
    ".py", ".java", ".rb", ".rs", ".go", ".php", ".swift", ".cs",
)

#: `\b` en los dos extremos para el término. Es la diferencia con la regla 5,
#: que compara por subcadena porque sus términos los escribió el CEO en el
#: pedido: acá la lista es nuestra y la subcadena mentiría —`java` está dentro
#: de `javascript`, que es justo el lenguaje permitido—.
_RE_AJENOS = re.compile(
    "|".join(
        [r"\b%s\b" % re.escape(t) for t in TERMINOS_AJENOS]
        + [r"%s\b" % re.escape(e) for e in EXTENSIONES_AJENAS]
    ),
    re.IGNORECASE,
)

#: Cómo un procedimiento delega la comprobación en un ejecutor que no existe del
#: lado de acá de la frontera. Van como perífrasis y no como lista de comandos
#: **porque así es como aparece en el registro**: de los siete criterios que la
#: regla 9 corta, cinco no nombran ninguna herramienta. Dicen "correr el comando
#: de ejecución de pruebas del proyecto".
#:
#: No es casualidad. La regla 8 ya castiga nombrar `pytest`, así que el nombre
#: propio desaparece y queda la perífrasis, que dice exactamente lo mismo y no la
#: cortaba nadie. Una lista de comandos —`npm test`, `jest`, `npx`— medida contra
#: los ocho planes del registro corta dos criterios, y los dos ya los cortaba la
#: regla 8 por decir `pytest` en el mismo renglón: aporte neto cero.
DELEGACION_EN_EJECUTOR = (
    r"\brunners?\b",
    r"\bcomando\s+de\s+(la\s+)?(ejecuci[oó]n\s+de\s+)?(las\s+)?(pruebas|tests?)\b",
    r"\bsuite\s+de\s+(pruebas|tests?)\b",
)

#: Las herramientas del propio JavaScript. La regla 8 no las ve —y hace bien: son
#: del lenguaje que la Fábrica sí produce—, pero la frontera de ADR-016 no las
#: da igual, porque no hay red y no se instala nada.
HERRAMIENTAS_SIN_FRONTERA = (
    "npm test", "npm run", "npm install", "npm ci",
    "yarn", "pnpm", "npx",
    "jest", "mocha", "vitest", "jasmine", "karma", "cypress",
    "playwright", "puppeteer", "selenium",
    "eslint", "prettier", "webpack", "rollup", "babel", "tsc",
)

#: `\s+` en lugar del espacio literal: "npm  test" partido por un salto de línea
#: es el mismo comando y esquivarla por un espacio de más sería un agujero.
_RE_SIN_EJECUTOR = re.compile(
    "|".join(
        list(DELEGACION_EN_EJECUTOR)
        + [
            r"\b%s\b" % re.escape(h).replace(r"\ ", r"\s+")
            for h in HERRAMIENTAS_SIN_FRONTERA
        ]
    ),
    re.IGNORECASE,
)


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


def _regla_8(plan):
    """El plan no compromete un lenguaje que la Fábrica no sabe producir.

    Un plan que pide Python es un plan que el Developer no puede cumplir, y no
    porque le falte capacidad: el Contrato de Entrega le exige entregar lógica
    que un navegador cargue. Antes de esta regla la contradicción no la
    comprobaba nadie y salía de dos maneras, las dos malas. Ruidosa: el plan
    fija una ruta `.py`, C4 la exige, C6 exige la lógica ejecutable, y el
    Developer oscila entre las dos hasta agotar el techo. Silenciosa: el plan
    dice Python, el Developer entrega JavaScript porque es lo único que sabe
    hacer, nada lo compara, y el Gate de salida firma una entrega que
    contradice al plan que la originó. La segunda ya pasó y nadie la vio.

    **Se miran los campos donde nombrar un lenguaje es comprometerse a él.** No
    `fuera_de_alcance`, donde "no se implementa en Python" es una aclaración
    legítima y prohibirla obligaría a escribir peor. No `alcance_excluido`, que
    se copia literal del pedido: si el CEO escribió ahí la palabra, rechazar el
    plan sería castigar al agente por obedecer.

    Los criterios sí se miran, y no es exceso de celo: el criterio es lo que QA
    ejecuta. Un plan que dice JavaScript en la unidad y `pytest` en el
    procedimiento le pasa la contradicción entera al paso siguiente.
    """
    fallos = []

    for i, supuesto in enumerate(plan["supuestos"]):
        for termino in sorted(set(m.group(0).lower() for m in _RE_AJENOS.finditer(supuesto))):
            fallos.append(
                _incumplimiento(
                    8,
                    "El supuesto %d nombra '%s'. La Fábrica produce %s en V0.2 y el "
                    "lenguaje no es un supuesto del plan: es un hecho del Contrato de "
                    "Entrega del Developer." % (i + 1, termino, LENGUAJE_DE_LA_FABRICA),
                )
            )

    for u in plan["unidades"]:
        textos = [(campo, u[campo], None) for campo in ("enunciado", "artefacto_esperado")]
        if u.get("ruta_artefacto"):
            textos.append(("ruta_artefacto", u["ruta_artefacto"], None))
        for j, criterio in enumerate(u["criterios"]):
            for parte in PARTES_CRITERIO:
                textos.append((parte, criterio.get(parte) or "", j))
        for campo, texto, j in textos:
            for termino in sorted(set(m.group(0).lower() for m in _RE_AJENOS.finditer(texto))):
                fallos.append(
                    _incumplimiento(
                        8,
                        "'%s' nombra '%s'. La Fábrica produce %s en V0.2."
                        % (campo, termino, LENGUAJE_DE_LA_FABRICA),
                        unidad=u["id"],
                        criterio=j,
                    )
                )
    return fallos


def _regla_9(plan):
    """El procedimiento no delega la comprobación en un ejecutor que no existe.

    QA corre cada caso con `node -e` sin red y sin instalar nada (ADR-016). Un
    criterio cuyo procedimiento dice "correr el comando de ejecución de pruebas
    del proyecto y verificar que el reporte indique cero fallos" no tiene ningún
    caso posible: del lado de acá de la frontera no hay comando que correr ni
    reporte que leer.

    Lo que pasa cuando no se corta está medido. Contra los ocho planes del
    registro, siete llevan un criterio así, y de las tres corridas que llegaron a
    ejecutarlo con QA encendido, dos murieron con el techo de salida quemado y
    sin producir un solo caso. Es el defecto que ADR-018 punto 5 anotó como
    "2 de 11 criterios ejecutables".

    **Se mira `procedimiento` y ningún otro campo.** Ésta es la distinción que
    hace correcta a la regla, y la primera que alguien va a querer "completar"
    extendiéndola a `artefacto_esperado`. No se extiende, y el motivo es que los
    dos campos dicen cosas distintas:

    - `artefacto_esperado` describe **qué se produce**. Una unidad puede tener
      que entregar legítimamente un archivo de pruebas, o un `package.json` con
      su script de test. Prohibir ahí la palabra sería prohibirle a la Fábrica
      producir tests, que es lo contrario de lo que se quiere.
    - `procedimiento` describe **cómo se comprueba**, y el que comprueba es QA,
      atado a la frontera. Es el único campo donde nombrar una herramienta es
      comprometer a alguien a usarla.

    La diferencia se ve en una unidad sola: "entregar `pruebas.js` con al menos
    dos casos" es un artefacto impecable, y "correr la suite y ver que dé cero
    fallos" es un procedimiento imposible. La misma unidad, y sólo el segundo
    campo está mal. Una regla que mirara los dos rechazaría la unidad entera por
    la mitad que estaba bien.

    Es también la diferencia con la regla 8, que sí mira varios campos: allá el
    lenguaje ajeno contamina donde aparezca, porque el Developer no lo sabe
    producir en ninguna parte. Acá el problema no es la herramienta, es *quién
    tendría que correrla*.
    """
    fallos = []
    for u in plan["unidades"]:
        for j, criterio in enumerate(u["criterios"]):
            texto = criterio.get("procedimiento") or ""
            for termino in sorted(
                set(m.group(0).lower() for m in _RE_SIN_EJECUTOR.finditer(texto))
            ):
                fallos.append(
                    _incumplimiento(
                        9,
                        "El procedimiento delega la comprobación en '%s'. La "
                        "verificación corre con `node -e` sin red y sin instalar "
                        "nada, así que no hay runner ni reporte que leer: el "
                        "procedimiento tiene que decir qué se invoca y qué valor "
                        "se espera." % termino,
                        unidad=u["id"],
                        criterio=j,
                    )
                )
    return fallos


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
    incumplimientos += _regla_8(plan)
    incumplimientos += _regla_9(plan)

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
