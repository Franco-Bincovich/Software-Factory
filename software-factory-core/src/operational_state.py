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
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

# El anclaje se cuenta desde este archivo, src/operational_state.py: parents[0]
# es src, parents[1] es software-factory-core, parents[2] es la raiz del repo. La
# carpeta de estado es hermana del repo, no interna, porque el almacen vive fuera
# de todo git; si moves este modulo, el conteo deja de valer y hay que corregirlo
# o definir SOFTWARE_FACTORY_STATE_DIR.
RAIZ_REPO = Path(__file__).resolve().parents[2]

# Una sola variable gobierna todo el estado, y de ella derivan las tres rutas:
# factory.db, trabajo/ y checkpointer/checkpoints.db. ADR-006: el Estado
# Operativo es la unica fuente de verdad. Tres variables independientes
# permitirian partirlo en tres discos distintos sin aviso, y la configuracion no
# debe poder expresar un estado invalido.
DIR_ESTADO = Path(
    os.environ.get("SOFTWARE_FACTORY_STATE_DIR")
    or RAIZ_REPO.parent / "software-factory-state"
)

RUTA_POR_DEFECTO = DIR_ESTADO / "factory.db"


def relativa_a(ruta, base):
    """La ruta como se guarda en un evento: relativa a una base, y en posix.

    ADR-014 punto 3: una ruta absoluta en el registro convierte la evidencia en
    algo que solo se entiende en la maquina que la produjo. `os.path.relpath`
    —y no `Path.relative_to`— porque tiene que servir tambien cuando el destino
    cae fuera de la base: devuelve una cadena de `..` en vez de romper, y esa
    cadena tampoco lleva nombre de usuario adentro.

    Separadores posix siempre. Un evento escrito en Windows y leido en macOS
    tiene que decir lo mismo, que es todo el punto de guardar relativo.
    """
    return Path(os.path.relpath(str(ruta), str(base))).as_posix()


def absoluta_desde(relativa, base):
    """La ruta como se usa: la que salio de `relativa_a`, devuelta a absoluta.

    `normpath` y no `resolve`: resolver seguiria los symlinks y devolveria un
    domicilio distinto del que se guardo —en macOS `/tmp` es `/private/tmp`—.
    Lo que se reconstruye tiene que ser la misma ruta, no una equivalente.
    """
    return Path(os.path.normpath(os.path.join(str(base), str(relativa))))


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

    def eventos_de_tipo(self, tipo):
        """Todos los eventos de un tipo, de todas las corridas, ordenados por id.

        Lectura pura: no toca el esquema ni los triggers. Hace falta para seguir
        un linaje — qué corridas heredaron un plan no se puede saber leyendo una
        corrida sola, porque el hecho vive en la heredera y no en el origen.
        """
        filas = self._conexion.execute(
            "SELECT id, run_id, ts, tipo, actor, payload FROM evento "
            "WHERE tipo = ? ORDER BY id",
            (tipo,),
        ).fetchall()
        return [self._a_evento(f) for f in filas]

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
