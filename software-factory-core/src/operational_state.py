"""Operational State — T13.

El almacén de hechos de la fábrica. Única fuente de verdad de lo que ocurrió:
qué pedido entró, qué produjo el agente, qué verificó la plataforma, quién
aprobó qué, cuánto se consumió. El Vault no participa.

Una sola tabla autoritativa, `evento`. No hay tablas mutables y no existe
función de update ni de delete: la inmutabilidad la fuerza la propia base con
dos triggers, no la ausencia de código que la viole.

El archivo vive fuera de todo repositorio git. Si se pierde, se pierde toda la
evidencia de la fábrica sin reconstrucción posible. Es R8 y está asumido.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

RUTA_POR_DEFECTO = Path(
    "/Users/franbincovich/Desktop/VSCode/software-factory-state/factory.db"
)

# ADR-009 punto 8: toda accion registrada nombra a su actor.
ACTORES_V01 = ("requirement-agent", "plataforma", "CEO")
ACTORES_PROHIBIDOS = ("sistema",)

# ADR-009 punto 4. Control lexico y por lo tanto parcial: no detecta un secreto
# guardado bajo un nombre inocente.
CLAVES_PROHIBIDAS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "credential",
    "authorization",
    "private_key",
)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS evento (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id   TEXT    NOT NULL,
  ts       TEXT    NOT NULL,
  tipo     TEXT    NOT NULL,
  actor    TEXT    NOT NULL,
  payload  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evento_run  ON evento(run_id);
CREATE INDEX IF NOT EXISTS idx_evento_tipo ON evento(tipo);

CREATE TRIGGER IF NOT EXISTS evento_no_update BEFORE UPDATE ON evento
BEGIN SELECT RAISE(ABORT, 'evento es inmutable'); END;

CREATE TRIGGER IF NOT EXISTS evento_no_delete BEFORE DELETE ON evento
BEGIN SELECT RAISE(ABORT, 'evento es inmutable'); END;
"""


class RegistroRechazado(ValueError):
    """El evento no se escribe. Como nada se borra, se rechaza antes de entrar."""


def _claves_prohibidas_en(valor, camino=""):
    """Devuelve los caminos de toda clave prohibida, a cualquier nivel.

    Recorre diccionarios y listas, con lo que alcanza tambien a las claves de
    objetos anidados dentro de arrays.
    """
    hallazgos = []
    if isinstance(valor, dict):
        for clave, contenido in valor.items():
            camino_hijo = "%s.%s" % (camino, clave) if camino else str(clave)
            if str(clave).casefold() in CLAVES_PROHIBIDAS:
                hallazgos.append(camino_hijo)
            hallazgos.extend(_claves_prohibidas_en(contenido, camino_hijo))
    elif isinstance(valor, list):
        for i, elemento in enumerate(valor):
            hallazgos.extend(_claves_prohibidas_en(elemento, "%s[%d]" % (camino, i)))
    return hallazgos


class OperationalState:
    """Almacen de eventos. Escritor unico, archivo unico."""

    def __init__(self, ruta=RUTA_POR_DEFECTO):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._conexion = sqlite3.connect(str(self.ruta))
        self._conexion.row_factory = sqlite3.Row
        self._conexion.executescript(ESQUEMA)
        self._conexion.commit()

    # --- escritura --------------------------------------------------------

    def append(self, run_id, tipo, actor, payload):
        """Registra un hecho y devuelve su id. Es la unica forma de escribir."""
        if not isinstance(run_id, str) or not run_id.strip():
            raise RegistroRechazado("run_id es obligatorio.")
        if not isinstance(tipo, str) or not tipo.strip():
            raise RegistroRechazado("tipo es obligatorio.")

        if not isinstance(actor, str) or not actor.strip():
            raise RegistroRechazado(
                "actor es obligatorio: toda accion registrada nombra a su actor."
            )
        if actor.strip().casefold() in ACTORES_PROHIBIDOS:
            raise RegistroRechazado(
                "actor '%s' no nombra a nadie. Actores de V0.1: %s."
                % (actor, ", ".join(ACTORES_V01))
            )

        if not isinstance(payload, dict):
            raise RegistroRechazado("payload debe ser un objeto JSON.")
        prohibidas = _claves_prohibidas_en(payload)
        if prohibidas:
            raise RegistroRechazado(
                "el payload contiene claves prohibidas: %s. Ningun secreto entra "
                "al Operational State, y como nada se borra, entraria para siempre."
                % ", ".join(sorted(prohibidas))
            )

        try:
            serializado = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as error:
            raise RegistroRechazado("payload no es serializable a JSON: %s" % error)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        with self._conexion:
            cursor = self._conexion.execute(
                "INSERT INTO evento (run_id, ts, tipo, actor, payload) VALUES (?, ?, ?, ?, ?)",
                (run_id, ts, tipo, actor, serializado),
            )
        return cursor.lastrowid

    # --- lectura ----------------------------------------------------------

    def leer_run(self, run_id):
        """Devuelve los eventos de una corrida, ordenados por id."""
        filas = self._conexion.execute(
            "SELECT id, run_id, ts, tipo, actor, payload FROM evento "
            "WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [self._a_evento(f) for f in filas]

    def gates_pendientes(self):
        """Gates abiertos que no tienen un `gate_resuelto` posterior.

        Aparea cada resolucion con el gate abierto mas antiguo aun sin resolver
        de la misma corrida y del mismo tipo de gate.
        """
        filas = self._conexion.execute(
            "SELECT id, run_id, ts, tipo, actor, payload FROM evento "
            "WHERE tipo IN ('gate_abierto', 'gate_resuelto') ORDER BY id",
        ).fetchall()

        abiertos = []
        for fila in filas:
            evento = self._a_evento(fila)
            clave = (evento["run_id"], evento["payload"].get("gate"))
            if evento["tipo"] == "gate_abierto":
                abiertos.append((clave, evento))
                continue
            for i, (clave_abierto, _) in enumerate(abiertos):
                if clave_abierto == clave:
                    del abiertos[i]
                    break
        return [evento for _, evento in abiertos]

    def consumo(self, run_id):
        """Consumo acumulado de una corrida.

        Cada evento `consumo_registrado` lleva lo consumido en ese momento, no
        el acumulado: el acumulado es estado derivado y no se guarda como hecho.
        Por eso se suman los deltas de todos los eventos de la corrida.
        """
        filas = self._conexion.execute(
            "SELECT payload FROM evento WHERE run_id = ? AND tipo = 'consumo_registrado' "
            "ORDER BY id",
            (run_id,),
        ).fetchall()
        total = {"costo": 0, "tiempo": 0, "iteraciones": 0}
        for fila in filas:
            payload = json.loads(fila["payload"])
            for clave in total:
                total[clave] += payload.get(clave, 0)
        return total

    # --- identidad --------------------------------------------------------

    @staticmethod
    def nuevo_run_id():
        """Identificador unico y opaco. Se llama antes de consumir un token."""
        return uuid.uuid4().hex

    # --- interno ----------------------------------------------------------

    @staticmethod
    def _a_evento(fila):
        return {
            "id": fila["id"],
            "run_id": fila["run_id"],
            "ts": fila["ts"],
            "tipo": fila["tipo"],
            "actor": fila["actor"],
            "payload": json.loads(fila["payload"]),
        }

    def cerrar(self):
        self._conexion.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()


def nuevo_run_id():
    """Atajo de modulo, por si no hace falta abrir el almacen todavia."""
    return OperationalState.nuevo_run_id()
