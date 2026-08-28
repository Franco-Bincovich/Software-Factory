"""Guardián de los conteos declarados.

Una afirmación como "los trece campos" o "las siete reglas" es una norma que un
agente lee en tiempo de ejecución: el Vault entra textual en el system prompt. Si
la máquina tiene otro número, el agente aplica una norma que no existe. Este
archivo hace que esa desincronización rompa la suite en vez de quedarse escrita.

Cada conteo guardado se **deriva de la máquina por introspección** —el largo de
una tupla, las funciones de un módulo, los `def test_` del árbol—. De la prosa se
lee **solamente el número**, y sólo en las líneas registradas en `AFIRMACIONES`.
Un test que interpreta prosa es un test que miente.

Los conteos del Vault que no tienen contraparte en el código —"los doce
principios", "los dieciocho documentos"— quedan fuera por eso mismo: no hay nada
que introspeccionar y contarlos exigiría interpretar.

## Qué no guarda, y cuánto cuesta

**`08 - ADR/`, `99 - Archive/` y `07 - Projects/_reference/`.** Un ADR es un
registro fechado. `ADR-016:19` dice "diecinueve reglas" y el día que se escribió
era verdad; hoy son veinte porque V5 agregó una. Corregirlo sería reescribir la
historia, así que el guardián no mira ahí. **El precio de esa exclusión es
concreto: si mañana un ADR vuelve a citar uno de estos números, el guardián no lo
ve.** Queda a cargo de quien escriba el ADR. La exclusión es deliberada; no la
levantes para hacer pasar un test.

**Las nueve reglas de validez del Contrato de Entrega.** Viven numeradas en un
documento del Vault y no tienen contraparte fiel en el código: el verificador
emite `C0`–`C8` porque la regla 9 la cubre el esquema, así que los nueve
identificadores coinciden con las nueve reglas por casualidad, no por
construcción. Contarlos sería medir una cosa y afirmar otra.

**Las afirmaciones que nadie registró.** Esto no descubre afirmaciones nuevas:
revisa las de `AFIRMACIONES`. Si alguien escribe "las once reglas" en un
documento nuevo, el guardián no se entera. A cambio, si alguien **reescribe** una
afirmación registrada, falla pidiendo que se la vuelva a registrar, que es
exactamente el momento en que corresponde volver a mirarla.
"""

import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# RAIZ es software-factory-core; el Vault cuelga de RAIZ.parent, igual que en
# test_agent_loader.py. El guardián lee el Vault real: es donde están las
# afirmaciones que un agente carga como norma.
VAULT = RAIZ.parent
TESTS = RAIZ / "tests"

import agent_loader
import verificador
import verificador_entrega

# ---------------------------------------------------------------- numerales

# Vocabulario cerrado. Alcanza para leer un número escrito en palabras sin
# interpretar nada: se suman los tokens. "doscientos cincuenta y seis" -> 256.
# `un`/`uno`/`una` quedan afuera a propósito: son artículos disfrazados de
# número y ningún conteo guardado vale uno.
_PALABRAS = {
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
    "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13,
    "catorce": 14, "quince": 15, "dieciseis": 16, "dieciséis": 16,
    "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiuno": 21, "veintidos": 22, "veintidós": 22, "veintitres": 23,
    "veintitrés": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
    "veintiséis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100, "ciento": 100,
    "doscientos": 200, "trescientos": 300, "cuatrocientos": 400,
    "quinientos": 500, "seiscientos": 600, "setecientos": 700,
    "ochocientos": 800, "novecientos": 900,
}

_ALT = "|".join(sorted(_PALABRAS, key=len, reverse=True))
# Un numeral es un entero en dígitos o hasta tres palabras encadenadas.
NUMERAL = rf"(?:\d+|\b(?:{_ALT})\b(?:\s+(?:y\s+)?\b(?:{_ALT})\b){{0,2}})"


def a_entero(texto):
    """El número que el texto declara. Suma aditiva sobre el vocabulario."""
    if texto.isdigit():
        return int(texto)
    return sum(_PALABRAS[p] for p in texto.lower().split() if p != "y")


# ------------------------------------------------- conteos que sabe la máquina

RE_DEF_TEST = re.compile(r"^\s*def (test_\w+)", re.M)


def _archivos_de_test():
    return sorted(TESTS.glob("test_*.py"))


def _tests_en(archivo):
    return len(RE_DEF_TEST.findall(archivo.read_text(encoding="utf-8")))


def _reglas_de_t7():
    """Las `_regla_N` de verificador.py con N >= 1.

    `_regla_0` no cuenta: es la compuerta del esquema, no una de las reglas.
    Es la convención que ya fijan T7-spec, el README y el propio verificador.
    """
    return sum(1 for n in vars(verificador) if re.fullmatch(r"_regla_[1-9]\d*", n))


CONTEOS = {
    "reglas_t7": (
        _reglas_de_t7,
        "las funciones `_regla_N` de `src/verificador.py` con N >= 1",
    ),
    "campos_adr003": (
        lambda: len(agent_loader.CAMPOS_ADR003),
        "`agent_loader.CAMPOS_ADR003`",
    ),
    "campos_operativos": (
        lambda: len(agent_loader.CAMPOS_OPERATIVOS),
        "`agent_loader.CAMPOS_OPERATIVOS`",
    ),
    "identificadores_entrega": (
        lambda: len(verificador_entrega.REGLAS),
        "`verificador_entrega.REGLAS`",
    ),
    "tests": (
        lambda: sum(_tests_en(a) for a in _archivos_de_test()),
        "los `def test_` bajo `tests/`",
    ),
}


def _valor_y_origen(clave):
    """Resuelve una clave de conteo. `tests:archivo.py` cuenta ese archivo."""
    if clave.startswith("tests:"):
        archivo = TESTS / clave.split(":", 1)[1]
        return _tests_en(archivo), f"los `def test_` de `tests/{archivo.name}`"
    fn, origen = CONTEOS[clave]
    return fn(), origen


# ------------------------------------------------------- afirmaciones guardadas

# (clave de conteo, ruta desde la raíz del repo, patrón con `<N>` donde va el
# número). El patrón tiene que identificar la afirmación sin ambigüedad dentro
# de su archivo; si deja de encontrarse, el guardián lo dice.
AFIRMACIONES = (
    # --- las siete reglas de T7 -------------------------------------------
    ("reglas_t7", "03 - Agent Framework/Verification.md",
     r"sus <N> reglas de validez"),
    ("reglas_t7", "03 - Agent Framework/Requirement Agent.md",
     r"las <N> reglas de validez del Contrato"),
    ("reglas_t7", "03 - Agent Framework/Requirement Agent.md",
     r"Las <N> reglas las evalúa"),
    ("reglas_t7", "06 - Standards/Ruleset mecanico.md",
     r"las <N> reglas del Contrato del Plan"),
    ("reglas_t7", "06 - Standards/Ruleset mecanico.md",
     r"las <N> reglas del Plan"),
    ("reglas_t7", "01 - Master Plan/Runbook V0.1.md",
     r"las <N> reglas, corrige"),
    ("reglas_t7", "software-factory-core/src/verificador.py",
     r"las <N> reglas siempre; no corta"),
    ("reglas_t7", "software-factory-core/src/productor.py",
     r"evalúa <N> reglas sobre el plan"),
    ("reglas_t7", "software-factory-core/docs/T7-spec.md",
     r"## Las <N> reglas"),
    ("reglas_t7", "software-factory-core/docs/T14-spec.md",
     r"las <N> reglas \| T7"),
    ("reglas_t7", "software-factory-core/schema/plan-de-trabajo.schema.json",
     r"las <N> reglas no se declaran"),
    ("reglas_t7", "software-factory-core/README.md",
     r"las <N> reglas siempre y devuelve"),
    ("reglas_t7", "software-factory-core/tests/test_agent_loader.py",
     r"pasa las <N> reglas y su Gate"),

    # --- los trece campos de ADR-003 --------------------------------------
    ("campos_adr003", "00 - Home/Home.md",
     r"los <N> campos de ADR-003"),
    ("campos_adr003", "01 - Master Plan/PLAN-V0.1 - Requirement Agent.md",
     r"Los <N> campos obligatorios de ADR-003"),
    ("campos_adr003", "01 - Master Plan/PLAN-V0.1 - Requirement Agent.md",
     r"contrato de <N> campos"),
    ("campos_adr003", "02 - Architecture/Architecture.md",
     r"contrato de <N> campos"),
    ("campos_adr003", "02 - Architecture/Architecture.md",
     r"definido por <N> campos obligatorios"),
    ("campos_adr003", "03 - Agent Framework/Requirement Agent.md",
     r"<N> campos completos, ninguno vacío"),
    ("campos_adr003", "03 - Agent Framework/Agent Framework.md",
     r"los <N> campos completos\. Un campo"),
    ("campos_adr003", "03 - Agent Framework/Agent Framework.md",
     r"los <N> campos del cuerpo"),
    ("campos_adr003", "software-factory-core/src/agent_loader.py",
     r"cumpla los <N> campos de"),
    ("campos_adr003", "software-factory-core/src/agent_loader.py",
     r"los <N> campos no están en el orden"),
    ("campos_adr003", "software-factory-core/README.md",
     r"cumpla los <N> campos de"),
    ("campos_adr003", "software-factory-core/docs/T10-spec.md",
     r"cumpla los <N> campos, y"),
    ("campos_adr003", "software-factory-core/docs/T10-spec.md",
     r"sin los <N> campos completos"),
    ("campos_adr003", "software-factory-core/docs/T10-spec.md",
     r"Los <N> encabezados de ADR-003"),
    ("campos_adr003", "software-factory-core/tests/test_cadena.py",
     r"<N> campos y techos"),
    ("campos_adr003", "software-factory-core/tests/test_grafo.py",
     r"<N> campos y techos"),

    # --- los ocho campos operativos del frontmatter ------------------------
    ("campos_operativos", "software-factory-core/docs/T10-spec.md",
     r"Los <N> campos operativos"),

    # --- los veinte identificadores del verificador de Entregas ------------
    ("identificadores_entrega", "software-factory-core/tests/test_verificador_entrega.py",
     r"y <N> copias casi\s+idénticas"),
    ("identificadores_entrega", "software-factory-core/docs/verificador-entrega-spec.md",
     r"y <N> copias casi\s+idénticas"),

    # --- el tamaño de la suite --------------------------------------------
    ("tests", "software-factory-core/README.md",
     r"<N> tests, uno por cada fila"),
    ("tests:test_agent_loader.py", "software-factory-core/tests/test_agent_loader.py",
     r"<N> tests, uno por fila"),
    ("tests:test_gates.py", "software-factory-core/tests/test_gates.py",
     r"<N> tests, uno por fila"),
    ("tests:test_grafo.py", "software-factory-core/tests/test_grafo.py",
     r"<N> tests, uno por fila"),
    ("tests:test_intake.py", "software-factory-core/tests/test_intake.py",
     r"<N> tests, uno por fila"),
    ("tests:test_presupuesto.py", "software-factory-core/tests/test_presupuesto.py",
     r"<N> tests, uno por fila"),
    ("tests:test_operational_state.py", "software-factory-core/tests/test_operational_state.py",
     r"de la tabla: son <N>"),
    ("tests:test_cadena.py", "software-factory-core/docs/cadena-spec.md",
     r"<N> tests contra un Operational State"),
)


def _compilar(patron):
    return re.compile(patron.replace("<N>", f"({NUMERAL})"), re.IGNORECASE)


def _hallazgos(clave, ruta, patron):
    """Cada aparición de la afirmación: (linea, numero declarado, texto)."""
    texto = (VAULT / ruta).read_text(encoding="utf-8")
    salida = []
    for m in _compilar(patron).finditer(texto):
        linea = texto.count("\n", 0, m.start()) + 1
        salida.append((linea, a_entero(m.group(1)), m.group(0)))
    return salida


class ConteosDeclarados(unittest.TestCase):

    def test_toda_afirmacion_registrada_sigue_en_su_archivo(self):
        """Si una afirmación se reescribió, hay que volver a registrarla.

        El guardián no puede avisar de una desincronización en una frase que ya
        no reconoce. Prefiere fallar a callarse.
        """
        perdidas = [
            f"{ruta} — no se encontró la afirmación /{patron}/"
            for clave, ruta, patron in AFIRMACIONES
            if not _hallazgos(clave, ruta, patron)
        ]
        self.assertEqual(perdidas, [], "\n" + "\n".join(perdidas))

    def test_ninguna_afirmacion_declara_un_numero_distinto_al_de_la_maquina(self):
        desfasadas = []
        for clave, ruta, patron in AFIRMACIONES:
            real, origen = _valor_y_origen(clave)
            for linea, declarado, texto in _hallazgos(clave, ruta, patron):
                if declarado != real:
                    desfasadas.append(
                        f"{ruta}:{linea} declara {declarado} y la máquina tiene "
                        f"{real}\n    dice: {texto.strip()!r}\n"
                        f"    el número sale de: {origen}"
                    )
        self.assertEqual(desfasadas, [], "\n" + "\n".join(desfasadas))

    def test_la_tabla_de_tests_del_readme_coincide_archivo_por_archivo(self):
        readme = RAIZ / "README.md"
        texto = readme.read_text(encoding="utf-8")
        declarado = {
            m.group(1): int(m.group(2))
            for m in re.finditer(r"^\| `(test_\w+\.py)` \| (\d+) \|", texto, re.M)
        }
        real = {a.name: _tests_en(a) for a in _archivos_de_test()}

        faltan = sorted(set(real) - set(declarado))
        sobran = sorted(set(declarado) - set(real))
        distintos = [
            f"README.md — `{n}` declara {declarado[n]} y tiene {real[n]}"
            for n in sorted(set(real) & set(declarado))
            if declarado[n] != real[n]
        ]
        problemas = (
            [f"README.md — falta la fila de `{n}`" for n in faltan]
            + [f"README.md — sobra la fila de `{n}`" for n in sobran]
            + distintos
        )
        self.assertEqual(problemas, [], "\n" + "\n".join(problemas))


if __name__ == "__main__":
    unittest.main()
