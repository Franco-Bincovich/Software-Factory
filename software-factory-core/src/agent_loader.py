"""Cargador de Agent Definition — T10.

Lee una Agent Definition desde el Vault, verifica que cumpla los trece campos de
ADR-003 y **se niega a arrancar si falta alguno**. No es un validador opcional:
es la puerta por la que un agente pasa de documento a instancia ejecutable.

El frontmatter lleva los parámetros operativos; el cuerpo lleva la norma. El
cuerpo manda: si difieren, la carga falla y hay que corregir el documento. No se
resuelve el conflicto en favor de ninguno de los dos automáticamente.

No escribe nada: si el agente no se pudo cargar, no hay corrida que registrar.
Por eso este módulo no conoce al Operational State.
"""

import re

CAMPOS_ADR003 = (
    (1, "Identidad"),
    (2, "Propósito"),
    (3, "Entrada"),
    (4, "Salida"),
    (5, "Herramientas autorizadas"),
    (6, "Alcance de decisión"),
    (7, "Criterio de terminación"),
    (8, "Presupuesto"),
    (9, "Comportamiento ante fallo"),
    (10, "Escalamiento"),
    (11, "Acceso al conocimiento"),
    (12, "Evidencia"),
    (13, "Dependencias"),
)

CAMPOS_OPERATIVOS = (
    "agent_id",
    "techo_costo_usd",
    "techo_tiempo_min",
    "techo_iteraciones",
    "herramientas",
    "vault_lectura",
    "vault_escritura",
    "memory",
)

TECHOS = ("techo_costo_usd", "techo_tiempo_min", "techo_iteraciones")

# El techo del frontmatter tiene que reaparecer con el mismo valor en el cuerpo.
ETIQUETA_DE_TECHO = {
    "techo_costo_usd": "Costo",
    "techo_tiempo_min": "Tiempo",
    "techo_iteraciones": "Iteraciones",
}

# Los acrónimos se buscan respetando mayúsculas: en castellano "todo" es una
# palabra corriente y buscarla sin distinguir marcaría documentos correctos.
MARCADORES_SENSIBLES = ("TBD", "TODO", "XXX", "N/A")
MARCADORES_INSENSIBLES = ("por definir", "a definir", "placeholder")


class CargaFallida(ValueError):
    """La definición no se carga. Lleva la lista completa de motivos."""

    def __init__(self, motivos):
        self.motivos = list(motivos)
        super().__init__("; ".join(self.motivos))


class AgentDefinition(object):
    """Los parámetros operativos de un agente. No expone el texto del cuerpo.

    El cuerpo es la norma que una persona aprueba; el runtime opera sobre los
    parámetros. Exponerlo invitaría a que alguna pieza intente interpretarlo.
    """

    def __init__(self, datos):
        self.agent_id = datos["agent_id"]
        self.version = datos["version"]
        self.techo_costo_usd = datos["techo_costo_usd"]
        self.techo_tiempo_min = datos["techo_tiempo_min"]
        self.techo_iteraciones = datos["techo_iteraciones"]
        self.herramientas = tuple(datos["herramientas"])
        self.vault_lectura = tuple(datos["vault_lectura"])
        self.vault_escritura = tuple(datos["vault_escritura"])
        self.memory = datos["memory"]

    def __repr__(self):
        return "<AgentDefinition %s v%s>" % (self.agent_id, self.version)


# --- frontmatter ------------------------------------------------------------


def _partir_documento(texto):
    """Separa frontmatter y cuerpo. Devuelve (lineas_frontmatter, cuerpo)."""
    if not texto.startswith("---\n"):
        raise CargaFallida(["frontmatter: el documento no abre con un bloque '---'."])
    cierre = texto.find("\n---", 3)
    if cierre == -1:
        raise CargaFallida(["frontmatter: el bloque no cierra con '---'."])
    return texto[4:cierre].split("\n"), texto[cierre + 4 :]


def _partir_lista(crudo):
    """Parte una lista en línea respetando las comillas."""
    elementos, actual, comilla = [], "", None
    for caracter in crudo:
        if comilla:
            if caracter == comilla:
                comilla = None
            else:
                actual += caracter
        elif caracter in "\"'":
            comilla = caracter
        elif caracter == ",":
            elementos.append(actual.strip())
            actual = ""
        else:
            actual += caracter
    if actual.strip():
        elementos.append(actual.strip())
    return [e for e in elementos if e != ""]


def _valor_escalar(crudo):
    crudo = crudo.strip()
    if len(crudo) >= 2 and crudo[0] == crudo[-1] and crudo[0] in "\"'":
        return crudo[1:-1]
    try:
        return int(crudo)
    except ValueError:
        pass
    try:
        return float(crudo)
    except ValueError:
        pass
    return crudo


def parsear_frontmatter(lineas):
    """Parser mínimo para el frontmatter plano del vault.

    Cubre `clave: escalar` y `clave: [a, b]`. Alcanza para estos documentos y
    evita sumar una dependencia.
    """
    datos = {}
    for linea in lineas:
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        if ":" not in linea:
            continue
        clave, _, crudo = linea.partition(":")
        clave, crudo = clave.strip(), crudo.strip()
        if crudo.startswith("[") and crudo.endswith("]"):
            datos[clave] = _partir_lista(crudo[1:-1])
        else:
            datos[clave] = _valor_escalar(crudo)
    return datos


# --- cuerpo -----------------------------------------------------------------


def _secciones(cuerpo):
    """Devuelve [(numero, nombre, contenido)] de los encabezados '## N. Nombre'."""
    encontrados = []
    patron = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.MULTILINE)
    coincidencias = list(patron.finditer(cuerpo))
    for i, m in enumerate(coincidencias):
        fin = coincidencias[i + 1].start() if i + 1 < len(coincidencias) else len(cuerpo)
        encontrados.append((int(m.group(1)), m.group(2), cuerpo[m.end() : fin].strip()))
    return encontrados


def _marcadores_en(texto):
    hallados = []
    for marcador in MARCADORES_SENSIBLES:
        if re.search(r"(?<!\w)%s(?!\w)" % re.escape(marcador), texto):
            hallados.append(marcador)
    for marcador in MARCADORES_INSENSIBLES:
        if re.search(r"\b%s\b" % re.escape(marcador), texto, re.IGNORECASE):
            hallados.append(marcador)
    return hallados


def _primer_numero(texto):
    m = re.search(r"-?\d+(?:[.,]\d+)?", texto)
    if m is None:
        return None
    return float(m.group(0).replace(",", "."))


# --- validación -------------------------------------------------------------


def _validar_cuerpo(cuerpo, motivos):
    secciones = {numero: (nombre, contenido) for numero, nombre, contenido in _secciones(cuerpo)}
    for numero, nombre in CAMPOS_ADR003:
        if numero not in secciones:
            motivos.append(
                "cuerpo: falta el campo %d '%s' de los trece de ADR-003." % (numero, nombre)
            )
            continue
        nombre_real, contenido = secciones[numero]
        if nombre_real.strip() != nombre:
            motivos.append(
                "cuerpo: el campo %d se llama '%s'; ADR-003 lo nombra '%s'."
                % (numero, nombre_real, nombre)
            )
        if not contenido.strip():
            motivos.append("cuerpo: el campo %d '%s' no tiene contenido debajo." % (numero, nombre))
            continue
        for marcador in _marcadores_en(contenido):
            motivos.append(
                "cuerpo: el campo %d '%s' contiene el marcador de relleno '%s'."
                % (numero, nombre, marcador)
            )

    orden = [numero for numero, _, _ in _secciones(cuerpo)]
    esperado = [numero for numero, _ in CAMPOS_ADR003]
    if orden and orden != esperado and sorted(orden) == esperado:
        motivos.append("cuerpo: los trece campos no están en el orden de ADR-003.")
    return secciones


def _validar_frontmatter(frontmatter, motivos):
    for campo in CAMPOS_OPERATIVOS:
        if campo not in frontmatter:
            motivos.append("frontmatter: falta el campo operativo '%s'." % campo)

    for campo in TECHOS:
        if campo not in frontmatter:
            continue
        valor = frontmatter[campo]
        if not isinstance(valor, (int, float)) or isinstance(valor, bool):
            motivos.append("frontmatter: '%s' no es numérico; vale %r." % (campo, valor))
        elif valor <= 0:
            motivos.append(
                "frontmatter: '%s' debe ser mayor que cero; vale %r." % (campo, valor)
            )

    estado = frontmatter.get("estado")
    if estado != "aceptado":
        motivos.append(
            "frontmatter: 'estado' debe ser 'aceptado' para instanciar; vale %r." % estado
        )

    agent_id = frontmatter.get("agent_id")
    if "agent_id" in frontmatter and (not isinstance(agent_id, str) or not agent_id.strip()):
        motivos.append("frontmatter: 'agent_id' no puede estar vacío.")

    if "version" not in frontmatter:
        motivos.append("frontmatter: falta el campo 'version'.")


def _validar_coherencia(frontmatter, secciones, motivos):
    """Los techos del frontmatter tienen que reaparecer en el cuerpo del campo 8."""
    if 8 not in secciones:
        return
    _, contenido = secciones[8]
    for campo in TECHOS:
        if campo not in frontmatter:
            continue
        etiqueta = ETIQUETA_DE_TECHO[campo]
        m = re.search(r"\*\*%s:\*\*(.*)" % etiqueta, contenido)
        if m is None:
            motivos.append(
                "coherencia: el frontmatter declara '%s' = %r pero el cuerpo del campo 8 "
                "no declara '%s'." % (campo, frontmatter[campo], etiqueta)
            )
            continue
        en_cuerpo = _primer_numero(m.group(1))
        if en_cuerpo is None:
            motivos.append(
                "coherencia: el cuerpo del campo 8 declara '%s' sin un valor numérico; "
                "el frontmatter dice %r." % (etiqueta, frontmatter[campo])
            )
        elif float(frontmatter[campo]) != en_cuerpo:
            motivos.append(
                "coherencia: '%s' vale %r en el frontmatter y %s en el cuerpo del campo 8. "
                "El cuerpo manda: corregir el documento."
                % (campo, frontmatter[campo], _formatear(en_cuerpo))
            )


def _formatear(numero):
    return str(int(numero)) if float(numero).is_integer() else str(numero)


# --- interfaz ---------------------------------------------------------------


def cargar(ruta_agent_definition):
    """Carga una Agent Definition o levanta `CargaFallida`.

    No carga parcialmente, no usa valores por defecto y no advierte para seguir.
    """
    with open(ruta_agent_definition, encoding="utf-8") as fh:
        texto = fh.read()

    lineas, cuerpo = _partir_documento(texto)
    frontmatter = parsear_frontmatter(lineas)

    motivos = []
    secciones = _validar_cuerpo(cuerpo, motivos)
    _validar_frontmatter(frontmatter, motivos)
    _validar_coherencia(frontmatter, secciones, motivos)

    if motivos:
        raise CargaFallida(motivos)
    return AgentDefinition(frontmatter)
