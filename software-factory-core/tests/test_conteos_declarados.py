"""Guardián de los conteos declarados, y de un hecho que no es un conteo.

Una afirmación como "los trece campos" o "las ocho reglas" es una norma que un
agente lee en tiempo de ejecución: el Vault entra textual en el system prompt. Si
la máquina tiene otro número, el agente aplica una norma que no existe. Este
archivo hace que esa desincronización rompa la suite en vez de quedarse escrita.

Lo mismo vale para el lenguaje de la Fábrica, que no es un número pero es el
mismo problema: el Contrato de Entrega del Developer lo fija en prosa y
`verificador.LENGUAJE_DE_LA_FABRICA` lo repite en código. Ver `LenguajeDeLaFabrica`
al final, y ADR-020 para por qué está repetido en vez de importado.

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

La exclusión es sobre las **afirmaciones** que un ADR hace, no sobre el
directorio. `08 - ADR/` sí se lee como **inventario**: cuántos ADRs aceptados hay
es un dato que sale de contar archivos y leer un campo del frontmatter, y es lo
que declara `Project Master Plan:31`. Contar no es interpretar; lo que el
guardián no hace es corregir la prosa de adentro de un ADR.

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
DIR_ADR = VAULT / "08 - ADR"

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
    "veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintidós": 22,
    "veintitres": 23,
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


RE_ARCHIVO_ADR = re.compile(r"^ADR-(\d+)\b")
RE_ESTADO = re.compile(r"^estado:[ \t]*(\S+)", re.M)


def _adrs_aceptados():
    """Los números de ADR aceptados, según el directorio y el frontmatter.

    Se cuenta `aceptado` y no archivos, porque la línea que esto guarda dice
    "ADRs **aprobados**". Contar archivos mediría una cosa y afirmaría otra: un
    ADR propuesto está en el directorio y no aprueba nada.

    `estado` se toma de la primera aparición, que es la del frontmatter por
    estar arriba de todo. Devuelve el conjunto de números, no la cantidad: el
    rango declarado necesita saber *cuáles*, no cuántos.
    """
    numeros = set()
    for archivo in DIR_ADR.glob("ADR-*.md"):
        m = RE_ARCHIVO_ADR.match(archivo.name)
        estado = RE_ESTADO.search(archivo.read_text(encoding="utf-8"))
        if m and estado and estado.group(1) == "aceptado":
            numeros.add(int(m.group(1)))
    return numeros


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
    "adrs_aprobados": (
        lambda: len(_adrs_aceptados()),
        "los `ADR-NNN*.md` de `08 - ADR/` con `estado: aceptado`",
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
    # --- las ocho reglas de T7 --------------------------------------------
    ("reglas_t7", "03 - Agent Framework/Verification.md",
     r"sus <N> reglas de validez"),
    ("reglas_t7", "03 - Agent Framework/Requirement Agent.md",
     r"las <N> reglas de validez del Contrato"),
    ("reglas_t7", "03 - Agent Framework/Requirement Agent.md",
     r"Las <N> reglas las evalúa"),
    # Esta no estaba registrada y ADR-020 la encontró desfasada a mano. El
    # `\s+` es porque la frase cruza el corte de línea.
    ("reglas_t7", "03 - Agent Framework/Requirement Agent.md",
     r"alguna de las <N>\s+reglas de validez"),
    ("reglas_t7", "software-factory-core/docs/verificador-entrega-spec.md",
     r"porque las <N> salen de un solo documento"),
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

    # --- los ADRs aprobados -----------------------------------------------
    ("adrs_aprobados", "01 - Master Plan/Project Master Plan.md",
     r"ADRs aprobados: <N> \("),
)


# El rango que acompaña al número en `Project Master Plan:31`. Se guarda aparte
# porque no es un conteo: es el conjunto de ADRs, y se verifica por igualdad
# contra los números que hay en el directorio.
RANGO_ADRS = ("01 - Master Plan/Project Master Plan.md",
              r"ADRs aprobados: \d+ \(([^)]*)\)")

# Gramática cerrada de un tramo: `ADR-NNN` o `ADR-NNN a ADR-MMM`. No hay nada
# que interpretar —o la frase tiene esta forma o no la tiene—, y si no la tiene
# el guardián lo dice en vez de adivinar.
RE_TRAMO_ADR = re.compile(r"ADR-(\d+)(?: a ADR-(\d+))?")


def _expandir_rango(expresion):
    """Los números que el rango declara, o None si no respeta la gramática."""
    numeros = set()
    for tramo in expresion.split(","):
        m = RE_TRAMO_ADR.fullmatch(tramo.strip())
        if not m:
            return None
        desde = int(m.group(1))
        hasta = int(m.group(2)) if m.group(2) else desde
        numeros.update(range(desde, hasta + 1))
    return numeros


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

    def test_el_rango_de_adrs_nombra_los_que_estan_en_el_directorio(self):
        """El número puede coincidir y el rango estar mal igual.

        `ADRs aprobados: 17` sigue siendo cierto si se acepta ADR-018 y se
        rechaza ADR-013: cambian cuáles, no cuántos. El rango es lo que dice
        cuáles, así que se verifica contra el conjunto y no contra el total.
        """
        ruta, patron = RANGO_ADRS
        texto = (VAULT / ruta).read_text(encoding="utf-8")
        m = re.search(patron, texto)
        self.assertIsNotNone(
            m, f"{ruta} — no se encontró el rango de ADRs /{patron}/")

        linea = texto.count("\n", 0, m.start()) + 1
        declarados = _expandir_rango(m.group(1))
        self.assertIsNotNone(
            declarados,
            f"{ruta}:{linea} — el rango {m.group(1)!r} no respeta la forma "
            f"`ADR-NNN` o `ADR-NNN a ADR-MMM` separados por comas. Si la "
            f"redacción cambió a propósito, volvé a registrarla acá.")

        reales = _adrs_aceptados()
        def _fmt(ns):
            return ", ".join("ADR-%03d" % n for n in sorted(ns)) or "ninguno"
        self.assertEqual(
            declarados, reales,
            f"\n{ruta}:{linea} declara un rango que no coincide con "
            f"`08 - ADR/`\n"
            f"    dice: {m.group(0).strip()!r}\n"
            f"    declarados y no aceptados: {_fmt(declarados - reales)}\n"
            f"    aceptados y no declarados: {_fmt(reales - declarados)}")

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


CONTRATO_DEVELOPER = "03 - Agent Framework/Contrato de Entrega del Developer.md"

#: La frase del Contrato que cierra el lenguaje. `<L>` es el hueco donde va el
#: lenguaje, igual que `<N>` en las afirmaciones de conteo.
CIERRE_DEL_LENGUAJE = r"En V0\.2 eso se cierra a favor de <L>\."


class LenguajeDeLaFabrica(unittest.TestCase):
    """La constante del verificador y el Contrato no se pueden contradecir.

    La regla 8 de T7 rechaza un plan que compromete un lenguaje que el Developer
    no sabe producir, y para eso `verificador.py` guarda el nombre del lenguaje
    en una constante. La norma, sin embargo, vive en el Contrato de Entrega del
    Developer, que es lo que el agente lee.

    **El verificador de planes no importa el contrato del Developer, y es a
    propósito.** Acoplar los dos módulos por diez palabras es caro y no hace
    falta: alcanza con que este test falle el día que uno de los dos cambie sin
    el otro. Es el mismo patrón que las afirmaciones de conteo de este archivo.
    """

    def test_la_constante_dice_lo_que_dice_el_contrato(self):
        texto = (VAULT / CONTRATO_DEVELOPER).read_text(encoding="utf-8")
        m = re.search(CIERRE_DEL_LENGUAJE.replace("<L>", r"(\w+)"), texto)
        self.assertIsNotNone(
            m,
            f"{CONTRATO_DEVELOPER} — no se encontró el cierre del lenguaje "
            f"/{CIERRE_DEL_LENGUAJE}/. Si la redacción cambió a propósito, "
            f"volvé a registrarla acá.")
        linea = texto.count("\n", 0, m.start()) + 1
        self.assertEqual(
            m.group(1), verificador.LENGUAJE_DE_LA_FABRICA,
            f"\n{CONTRATO_DEVELOPER}:{linea} cierra V0.2 a favor de "
            f"{m.group(1)!r} y `verificador.LENGUAJE_DE_LA_FABRICA` dice "
            f"{verificador.LENGUAJE_DE_LA_FABRICA!r}.\n"
            f"    La regla 8 estaría rechazando planes en nombre de un lenguaje "
            f"que el Contrato ya no manda.")

    def test_el_lenguaje_de_la_fabrica_no_esta_en_el_vocabulario_prohibido(self):
        """Prohibir lo único que se puede producir haría inviable todo plan."""
        self.assertNotIn(
            verificador.LENGUAJE_DE_LA_FABRICA.lower(),
            verificador.TERMINOS_AJENOS,
        )


if __name__ == "__main__":
    unittest.main()
