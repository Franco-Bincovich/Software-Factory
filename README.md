# software-factory-core

Piezas de runtime de V0.1: el verificador estructural de Planes de Trabajo (T7)
y el Operational State (T13).

```
schema/     esquema JSON del Plan de Trabajo
src/        el verificador y el almacén de eventos
fixtures/   el pedido base y los seis planes de prueba
tests/      los tests de ambas piezas
docs/       las especificaciones
```

## Verificador estructural (T7)

Recibe un Plan de Trabajo en JSON y el texto del pedido que lo originó, y
devuelve un veredicto binario más la lista de incumplimientos. No corrige, no
interpreta y no completa planes: solo comprueba y localiza. Lo ejecuta la
plataforma, nunca el agente que produjo el plan.

La especificación completa está en [`docs/T7-spec.md`](docs/T7-spec.md).

## Requisitos

Python 3.9 o superior y `jsonschema`. Es la única dependencia fuera de la
librería estándar.

```
python3 -m venv .venv
./.venv/bin/pip install jsonschema
```

## Cómo se corre

```
./.venv/bin/python src/verificador.py <plan.json> --pedido <pedido.txt>
```

El pedido es obligatorio: la regla 4 comprueba que el `rastreo` de cada unidad
aparezca literal en él.

```
./.venv/bin/python src/verificador.py fixtures/plan-ok.json --pedido fixtures/pedido.txt
```

Imprime el veredicto en JSON por salida estándar. Termina en 0 si el plan es
válido y en 1 si no lo es.

```json
{
  "valido": false,
  "incumplimientos": [
    {
      "regla": 3,
      "unidad": "U4",
      "criterio": null,
      "detalle": "La dependencia 'U9' no corresponde a ninguna unidad del plan."
    }
  ]
}
```

Evalúa las siete reglas siempre y devuelve la lista completa; no corta en el
primer incumplimiento. Si el plan no valida contra el esquema devuelve regla `0`
y no evalúa el resto.

## Operational State (T13)

El almacén de hechos de la fábrica. Todo lo que ocurrió durante una corrida se
escribe acá: qué pedido entró, qué produjo el agente, qué verificó la
plataforma, quién aprobó qué, cuánto se consumió. Es la única fuente de verdad
de los hechos; el Vault, que lo es de las normas, no participa.

Una sola tabla autoritativa, `evento`. No hay tablas mutables y no existe
función de update ni de delete: la inmutabilidad la fuerzan dos triggers de la
propia base, no la ausencia de código que la viole. El estado actual de
cualquier cosa se deriva leyendo sus eventos.

La especificación completa está en [`docs/T13-spec.md`](docs/T13-spec.md).

```python
from operational_state import OperationalState

store = OperationalState()              # o OperationalState("/otra/ruta.db")
run = store.nuevo_run_id()
store.append(run, "run_iniciada", "plataforma", {"agent_definition_id": "requirement-agent"})

store.leer_run(run)         # eventos de la corrida, ordenados por id
store.gates_pendientes()    # gates abiertos sin resolución posterior
store.consumo(run)          # {costo, tiempo, iteraciones}
```

`append` rechaza el evento si el actor está vacío o dice `sistema`, y si alguna
clave del payload —a cualquier nivel de anidamiento, incluidas las de objetos
dentro de arrays— es un nombre de secreto conocido. Ese control es léxico y por
lo tanto parcial: no detecta un secreto guardado bajo un nombre inocente.

### Dónde vive el archivo

```
/Users/franbincovich/Desktop/VSCode/software-factory-state/factory.db
```

Directorio hermano del vault y de este repo. Si no existe, se crea al abrir el
almacén. La ruta es configurable por constructor; los tests siempre usan una
base temporal.

### Advertencia — R8

**El almacén no está versionado ni respaldado.** Vive fuera de todo repositorio
git a propósito: un hecho no tiene versiones, tiene ocurrencia. La contrapartida
es que **si ese directorio se pierde, se pierde toda la evidencia de todo lo que
la fábrica hizo, sin reconstrucción posible desde el Vault.**

Es el riesgo R8 del registro del Project Master Plan, hoy abierto. El
procedimiento de respaldo se declara en Infrastructure, documento todavía
bloqueado. Hasta entonces **el respaldo es manual y es responsabilidad del
CEO.**

## Cómo se corren los tests

```
./.venv/bin/python -m unittest discover -s tests -v
```

Dieciocho tests. Nueve de T7: uno por cada uno de los seis fixtures y tres sobre
la forma de la salida. Cada test de fixture comprueba que se dispara exactamente
la regla sembrada y ninguna otra; el del plan limpio comprueba cero
incumplimientos. Nueve de T13, uno por cada fila de su criterio de aceptación,
todos contra una base temporal que se destruye al terminar.
