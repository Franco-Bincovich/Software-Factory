# software-factory-core

Piezas de runtime de V0.1. Seis tareas del Bloque B de PLAN-V0.1:

| Tarea | Pieza | Módulo |
|---|---|---|
| T7 | Verificador estructural | `src/verificador.py` |
| T8 | Formulario de Intake | `src/intake.py` |
| T10 | Cargador de Agent Definition | `src/agent_loader.py` |
| T11 | Motor de Gates | `src/gates.py` |
| T12 | Contador de presupuesto | `src/presupuesto.py` |
| T13 | Operational State | `src/operational_state.py` |

Las piezas no están cableadas entre sí: encadenarlas es T14.

```
schema/     esquema JSON del Plan de Trabajo
src/        las seis piezas
templates/  la plantilla de pedido
fixtures/   el pedido base y los seis planes de prueba
tests/      un archivo por pieza
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

## Formulario de Intake (T8)

Punto único de ingreso de pedidos. Es un mecanismo, no una Agent Definition: no
interpreta, no completa, no infiere. Valida y registra. La interpretación de
pedidos difusos llega en V0.2 como Intake Agent.

La especificación completa está en [`docs/T8-spec.md`](docs/T8-spec.md).

Se parte de [`templates/pedido.template.json`](templates/pedido.template.json),
que trae los seis campos vacíos: qué se quiere, para qué, qué no entra, y los
tres techos. Los términos de `alcance_excluido` conviene escribirlos como uno
espera verlos en un plan —`"interfaz gráfica"`, no `"nada visual"`—, porque es
contra esa lista que T7 evalúa su regla 5.

```
./.venv/bin/python src/intake.py --pedido mi-pedido.json
```

Imprime el `run_id` y termina en 0 si el pedido entra. Si no, imprime cada
rechazo con su campo y su motivo, y termina en 1.

**El rechazo ocurre antes de generar el `run_id`.** Un pedido inválido no
consume nada y no deja corrida abierta: cero eventos escritos. No abre el Gate
de entrada, que es T11.

## Cargador de Agent Definition (T10)

Lee una Agent Definition desde el Vault, verifica que cumpla los trece campos de
ADR-003 y se niega a arrancar si falta alguno. No es un validador opcional: es
la puerta por la que un agente pasa de documento a instancia ejecutable.

La especificación completa está en [`docs/T10-spec.md`](docs/T10-spec.md).

El frontmatter lleva los parámetros operativos y el cuerpo lleva la norma. **El
cuerpo manda:** si los techos del frontmatter y los del campo 8 no coinciden, la
carga falla nombrando ambos valores y no elige ninguno.

```python
from agent_loader import cargar

d = cargar(".../03 - Agent Framework/Requirement Agent.md")
d.agent_id, d.techo_costo_usd, d.herramientas, d.vault_escritura
```

No expone el texto del cuerpo: el cuerpo es la norma que una persona aprueba y
el runtime opera sobre los parámetros. No escribe ningún evento — el módulo ni
siquiera conoce al Operational State.

## Motor de Gates (T11)

Frena una corrida y espera una decisión humana. No decide nada: abre, bloquea,
registra la resolución y devuelve el control.

La especificación completa está en [`docs/T11-spec.md`](docs/T11-spec.md).

```
./.venv/bin/python src/gates.py --listar
./.venv/bin/python src/gates.py --resolver <run_id> --gate entrada --decision aprobado
```

Cuatro restricciones, cada una con error explícito: no se resuelve un Gate que
no está abierto, no se resuelve dos veces, no se abre el de salida sin el de
entrada aprobado, y no se abren dos del mismo tipo en una corrida. Rechazar
exige motivo; aprobar no. El actor de `gate_resuelto` es siempre `CEO`.

**Un Gate abierto bloquea la corrida hasta que una persona lo resuelva.** No hay
aprobación automática por el paso del tiempo, y esa ausencia es deliberada: no
existe parámetro, constante, rama ni comentario que la contemple, y un test lo
verifica por inspección del módulo. Si alguna vez se decide lo contrario, será
por un ADR que reemplace a ADR-004 — no "por si acaso".

## Contador de presupuesto (T12)

Mide el consumo de una corrida contra sus tres techos. Mide durante, no al
final: un techo que se verifica cuando la corrida terminó no es un techo, es una
estadística.

La especificación completa está en [`docs/T12-spec.md`](docs/T12-spec.md).

```python
from presupuesto import consumo, registrar_consumo, verificar

registrar_consumo(store, run, 0.5)      # un delta, no el acumulado
consumo(store, run)                     # {costo, tiempo_min, iteraciones}
verificar(store, run, definicion)       # None | TechoAlcanzado
```

El costo es la suma de los deltas. Las iteraciones son la cantidad de eventos
`verificacion_ejecutada`. El tiempo es el de reloj desde `run_iniciada`
**menos** las ventanas de espera de Gates: esperar a un humano no consume
presupuesto, y un Gate todavía sin resolver descuenta desde que se abrió hasta
ahora. Si dos techos se alcanzan juntos, `TechoAlcanzado` los nombra a ambos.

`verificar` no escribe ningún evento y no corta: devuelve el veredicto y quien
lo recibe detiene la corrida y emite `run_cortada`, para que la responsabilidad
de cortar quede en un solo lugar. **Elevar un techo no está implementado**:
es cambiar un parámetro de la Agent Definition y relanzar. Modificarlo con la
corrida viva permitiría que el límite ceda bajo presión.

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

Sesenta tests, uno por cada fila de los criterios de aceptación de las seis
tareas:

| Archivo | Tests | Cubre |
|---|---|---|
| `test_verificador.py` | 9 | los seis fixtures de T7 y tres sobre la forma de la salida |
| `test_intake.py` | 9 | el criterio de aceptación de T8 |
| `test_agent_loader.py` | 10 | el criterio de aceptación de T10 |
| `test_gates.py` | 11 | el criterio de aceptación de T11 |
| `test_presupuesto.py` | 12 | el criterio de aceptación de T12 |
| `test_operational_state.py` | 9 | el criterio de aceptación de T13 |

Todo lo que toca el Operational State corre contra una base temporal que se
destruye al terminar. La base real nunca se abre desde los tests.
