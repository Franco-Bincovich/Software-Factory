# software-factory-core

Piezas de runtime de V0.1. Ocho tareas del Bloque B de PLAN-V0.1:

| Tarea | Pieza | Módulo |
|---|---|---|
| T7 | Verificador estructural | `src/verificador.py` |
| T8 | Formulario de Intake | `src/intake.py` |
| T10 | Cargador de Agent Definition | `src/agent_loader.py` |
| T11 | Motor de Gates | `src/gates.py` |
| T12 | Contador de presupuesto | `src/presupuesto.py` |
| T13 | Operational State | `src/operational_state.py` |
| T14 | Armazón de ejecución | `src/grafo.py` · `correr.py` |
| T15 | Productor real | `src/productor.py` |

T14 las encadena: es lo que hace que exista una corrida. T15 es lo que hace que
esa corrida produzca algo — y lo que hace que cueste plata.

Más las piezas de V0.2, sin número de tarea y fuera del Bloque B:

| Pieza | Módulos |
|---|---|
| Verificador de Entregas del Developer | `src/verificador_entrega.py` · `src/inspeccion_js.py` |
| La cadena: Requirement → Developer | `src/cadena.py` · `src/grafo_developer.py` |
| Productor real de Entregas | `src/productor_entrega.py` |

```
schema/     los esquemas JSON del Plan de Trabajo y de la Entrega
src/        las piezas
templates/  la plantilla de pedido
examples/   un pedido de ejemplo, válido y listo para correr
fixtures/   el pedido base, los seis planes de prueba y la entrega limpia
tests/      un archivo por pieza
docs/       las especificaciones
correr.py   la CLI de una corrida
```

## Verificador estructural (T7)

Recibe un Plan de Trabajo en JSON y el texto del pedido que lo originó, y
devuelve un veredicto binario más la lista de incumplimientos. No corrige, no
interpreta y no completa planes: solo comprueba y localiza. Lo ejecuta la
plataforma, nunca el agente que produjo el plan.

La especificación completa está en [`docs/T7-spec.md`](docs/T7-spec.md).

## Requisitos

**Python 3.12 y Node.** Python corre la fábrica; Node solo se usa para
comprobar que los archivos de una Entrega parseen, con `node --check`, que
parsea y termina sin ejecutar nada. **Sin Node el verificador de entregas no
verifica entregas**: falla nombrando qué falta, en vez de aprobar lo que no pudo
revisar. Todo lo demás —las ocho piezas de V0.1, incluida la verificación de
planes— corre sin Node.

Cinco dependencias directas de Python, declaradas con versión exacta en
`requirements.txt`: `jsonschema` para los esquemas del Plan de Trabajo y de la Entrega;
`langgraph` más `langgraph-checkpoint-sqlite` para el armazón de ejecución de
T14 —LangGraph es el coordinador que fija ADR-006, y la versión se fija exacta
por su punto 7—; y `anthropic` más `python-dotenv` para el productor real de
T15, que invoca al modelo con la credencial que lee de `.env`.

```
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements.lock
```

**Para instalar se usa el lock; para agregar una dependencia se edita
`requirements.txt`.** Los dos archivos no son intercambiables:

| Archivo | Qué tiene | Cuándo se toca |
|---|---|---|
| `requirements.txt` | las cinco dependencias directas | al agregar o subir una dependencia |
| `requirements.lock` | las 47 del árbol completo, con versión exacta | nunca a mano; se regenera |

Después de tocar `requirements.txt`, el lock se regenera instalando desde él y
congelando el resultado, y se le vuelve a poner el encabezado de dos líneas:

```
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip freeze > requirements.lock
```

Instalar desde `requirements.txt` también funciona, pero resuelve las
transitivas al día y el árbol queda distinto del que se probó.

LangGraph arrastra `langchain-core` como dependencia transitiva. Está en el
árbol y no se usa: ADR-006 punto 8 prohíbe programar contra LangChain, no
tenerlo instalado.

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

Evalúa las ocho reglas siempre y devuelve la lista completa; no corta en el
primer incumplimiento. Si el plan no valida contra el esquema devuelve regla `0`
y no evalúa el resto.

## Verificador de Entregas del Developer

El par del anterior para código. Recibe una Entrega del Developer y el Plan de
Trabajo que la originó, y devuelve la misma forma de veredicto. **No ejecuta
nada de lo que verifica**: el único proceso externo que lanza es `node --check`,
que parsea el archivo y termina sin correr una sola línea.

La especificación completa está en
[`docs/verificador-entrega-spec.md`](docs/verificador-entrega-spec.md).

```
./.venv/bin/python src/verificador_entrega.py fixtures/entrega-ok.json \
    --plan fixtures/plan-entrega.json
```

Son dos módulos: `verificador_entrega.py` sabe qué es una Entrega —el esquema,
las reglas del contrato, la orquestación y la CLI— e `inspeccion_js.py` sabe de
texto de código y no sabe qué es una Entrega.

**Los identificadores de regla llevan prefijo** porque salen de tres documentos
distintos: `C` el Contrato de Entrega del Developer, `R` el Ruleset mecánico con
su propio número, `P` las prohibiciones del contrato, y `V` lo que este
verificador comprueba y no tiene número en ningún lado. Un incumplimiento que no
se puede rastrear al documento que lo exige no se puede discutir.

```json
{
  "valido": false,
  "incumplimientos": [
    {
      "regla": "C7",
      "archivo": "demo.html",
      "detalle": "Reimplementa la lógica: declara validarLegajo, que ya está en 'src/validar-legajo.js'."
    }
  ]
}
```

**Varias reglas son parciales y están declaradas como tales**, una por una, con
lo que cada una no puede ver. La más parcial es `V4` —que `pruebas.html` no sea
teatro—: ve un veredicto escrito a mano, no ve un script que invoca la función,
ignora lo que devuelve y escribe "PASA" igual. Eso queda para el Gate humano.

**Sin `node` en el PATH falla nombrando qué falta**, en vez de aprobar lo que no
pudo parsear.

## La cadena de V0.2

Un pedido se convierte en plan y en código **sin ninguna persona en el medio**.
La especificación completa está en [`docs/cadena-spec.md`](docs/cadena-spec.md).

```
./.venv/bin/python correr.py --pedido pedido.json \
    --definicion "…/Requirement Agent.md" \
    --definicion-developer "…/Developer Agent.md" --stub
./.venv/bin/python src/gates.py --resolver <run_id> --gate entrada --decision aprobado
./.venv/bin/python correr.py --reanudar <run_id>      # plan, T7, y todas las unidades
./.venv/bin/python src/gates.py --resolver <run_id> --gate salida --decision aprobado
./.venv/bin/python correr.py --reanudar <run_id>      # cierra y borra el directorio
```

**Dos corridas encadenadas, no una.** El `run_id` del pedido es el de la cadena.
Cada unidad del plan abre su propia corrida de Developer, con techos y
presupuesto propios, y declara de qué corrida de Requirement viene. Por eso se
puede reintentar al Developer sin volver a producir el plan.

**Declarar si hay cadena es obligatorio.** Una corrida nueva exige
`--definicion-developer` para ejecutar las unidades del plan, o `--solo-plan`
para producir el plan y cerrar sin ejecutarlas. No hay valor por defecto: correr
media cadena tiene que ser un acto, no un olvido. La decisión queda registrada
como `cadena_fijada` — con la ruta, o con `null` y el motivo—, haya cadena o no.

**El cierre comprueba el régimen que la corrida declaró.** `gates_de_la_cadena`
dice bajo qué régimen corre —dos Gates con cadena, uno sin ella— y `fin` no
escribe `run_cerrada` sin verificar que se cumplió. Una corrida que declara dos
Gates y cierra habiendo aprobado uno levanta `RegimenIncumplido` en vez de cerrar
en verde. El registro es lo único que la fábrica tiene: una corrida cuyo registro
se contradice es peor que una que falla, porque la que falla se ve.

**Dos Gates en toda la cadena**, los dos en la corrida del pedido: entrada sobre
el pedido, salida sobre la entrega. **El Gate de salida sobre el plan se
suprimió** —aprobar el plan y después aprobar la entrega que sale de él es
aprobar dos veces lo mismo—, y la defensa contra un plan malo pasa a ser **el
techo de la cadena**: el techo de costo del pedido acota la suma de todas las
corridas y se comprueba antes de lanzar cada unidad.

**El Developer nunca decide qué sigue.** El orden sale del grafo de dependencias
del plan, es determinista, y va de a una unidad por vez. **Si una unidad falla se
detiene el plan completo**, incluidas las unidades independientes: en V0.2 la
simplicidad vale más que el aprovechamiento.

**El directorio de trabajo** es descartable, uno por corrida, fuera del
repositorio y del Vault, con un subdirectorio por unidad —si no, dos unidades se
pisarían `pruebas.html`—. Se borra **recién después** de aprobar el Gate de
salida; `--conservar-trabajo` no lo borra.

**Con `--solo-plan` la corrida cierra con el plan verificado**, que es el
Requirement Agent corriendo solo. Esa corrida declara un solo Gate, porque sin
Developer no hay entrega que aprobar.

**Un solo modo para toda la cadena.** `--stub` usa los productores de relleno; el
modo modelo usa los reales. Una corrida no produce el plan contra el modelo y el
código con el stub, ni al revés — y lo mismo vale para los casos de prueba de QA.

## Verificación sustantiva — el QA Agent

Implementa ADR-018. El verificador de entregas mira la **forma** de lo entregado
sin ejecutarlo; QA mira el **resultado**: corre los criterios de aceptación del
plan sobre el depósito de la entrega, bajo la frontera de kernel de ADR-016.

```
./.venv/bin/python correr.py --pedido pedido.json \
    --definicion "…/Requirement Agent.md" \
    --definicion-developer "…/Developer Agent.md" \
    --definicion-qa "…/QA Agent.md" --stub
```

**Se enciende con el flag; no viene por defecto.** No es una concesión: la
medición de ADR-018 sobre el plan actual da **2 criterios ejecutables de 11**, así
que hoy una corrida con QA escala casi todo. Poder correr sin QA es lo que permite
corregir al Requirement Agent sin quedarse sin fábrica mientras tanto. Además QA
depende de que la máquina tenga frontera de kernel, y encenderlo por defecto
rompería corridas que hoy funcionan por un motivo del entorno y no del entregable.

**Encenderlo es un hecho de la corrida**, igual que el modo y que la definición
del Developer. Queda en `cadena_fijada` bajo la clave `qa` —en `null` cuando no la
hubo— y `--reanudar` lo lee de ahí en vez de deducirlo de los flags. Encender QA a
mitad de una corrida dejaría unas unidades verificadas contra los criterios del
plan y otras no, sin nada en el registro que diga cuáles.

**Entra por unidad, después del verificador estructural y antes del Gate de
salida**, y reusa el bucle de reintento que ya existía: los incumplimientos
sustantivos vuelven al Developer en la misma forma `{regla, archivo, detalle}` que
los estructurales, acotados por el mismo techo de iteraciones. Ni un segundo bucle
ni un techo nuevo.

**El límite —QA no puede exigir lo que el plan no incluyó— es mecánico.** Cada
caso de prueba declara de qué criterio de su unidad deriva, y el índice se
resuelve **antes** de ejecutar nada. El veredicto lo emite el criterio, no el
caso: `veredicto` recorre `unidad["criterios"]`, así que la superficie de rechazo
es por construcción la lista de criterios del plan y un caso inventado sobre una
capacidad ausente no tiene dónde colgarse. No se coteja contra `fuera_de_alcance`:
son strings en prosa libre, y cualquier cotejo sería solapamiento de palabras
clave — un heurístico que falla en los dos sentidos justo en el borde que se
quiere cuidar.

**Los criterios que no se pudieron comprobar ejecutando se declaran, no se
juzgan.** Un criterio sin ningún caso anclado sale `no_verificable_mecanicamente`,
y el conteo viaja hasta lo que somete el Gate de salida. **Es una métrica sobre el
Requirement Agent, no sobre el Developer**: dice cuánto de lo que el plan prometió
no era comprobable.

**Sin frontera de kernel no se aprueba: se escala.** Que la máquina no pueda
verificar no dice nada sobre el entregable, y registrar como verificado algo que
nadie miró es la única salida que no está disponible.

**El stub de QA no propone ningún caso, a propósito.** Los otros dos stubs
fabrican un artefacto de relleno porque su forma está fijada por un contrato;
derivar un caso de prueba exige leer prosa y traducirla a una expresión
ejecutable, que es justo lo que sin modelo no se puede hacer. Fabricar casos que
pasen contra el entregable del stub del Developer daría verde sin haber mirado
nada. Con la lista vacía, todos los criterios salen `no_verificable_mecanicamente`
y la corrida queda diciendo exactamente eso — y, de paso, `--stub` no necesita
frontera de kernel.

**Qué de esto está medido contra defectos y qué falta.**
`test_qa_contra_defectos.py` corre QA sobre dos entregas reales del registro:
acepta las dos, que son correctas, y rechaza cuatro defectos sembrados nombrando
el criterio que cada uno rompió y no otro. Lo que ahí **no** se prueba es que el
prompt de `productor_qa` sepa derivar los casos leyendo la prosa del criterio: los
casos de esos tests están transcriptos del `procedimiento` que el plan escribió.
Esa medición necesita una corrida con modelo y está pendiente. El encabezado de
ese archivo explica también por qué el único rechazo real del `factory.db` no
sirve como caso de QA.

## Heredar un plan ya verificado

Un plan que se produjo y se pagó no tiene por qué volver a producirse para poder
ejecutarse.

```
./.venv/bin/python correr.py --desde-corrida <run_id> \
    --definicion-developer "…/Developer Agent.md"
```

**El plan se identifica por la corrida que lo produjo**, no por su `plan_id`, que
lo declara el agente. La corrida heredera salta la fase Requirement, copia el
pedido, y declara en `plan_heredado` de dónde vino el plan, de qué veredicto se
fía y **con qué modo se produjo el original** — sin eso, una entrega hecha por un
modelo sobre un plan hecho por otro no se puede interpretar después.

**El techo se hereda descontado:** el del pedido menos lo gastado en todo el
linaje. El techo pertenece al trabajo, no a la corrida; si cada corrida
arrancara con el techo entero, partir el trabajo en dos sería la forma de
evadirlo.

**Heredar un plan que ya produjo código se niega.** Con `--reejecutar` se acepta
y la corrida declara a qué ejecuciones sucede: el plan es inmutable, sus
ejecuciones se suceden.

## Productor real de Entregas

El equivalente de T15 para el Developer: la función que invoca al modelo y
devuelve una Entrega. Mismo patrón que `productor.py` —factory, cliente
inyectable, ningún test toca la red— con tres diferencias medidas.

**Caché de prompt sobre el system prompt.** Los cuatro documentos que la Agent
Definition del Developer declara leer pesan unos 14.000 tokens y viajan en cada
iteración de cada unidad. Un plan de diez unidades con tres iteraciones son hasta
treinta llamadas con el mismo prefijo: sin caché, el contexto solo se come el
techo de USD 0.50 por unidad antes de generar una línea.

**Streaming con `max_tokens` en 32.000.** Una Entrega son cuatro archivos
completos escapados en JSON; el techo de 16.000 de T15 trunca en cuanto la unidad
es real, y truncar cuesta una iteración pagada que devuelve entrega vacía.

**La entrega vacía escala en vez de corregirse.** Si el modelo devuelve la
entrega vacía del contrato con su motivo, el productor levanta `UnidadAmbigua`,
el grafo del Developer la registra como `unidad_ambigua` y la cadena escala. No
va al verificador y no cuenta como iteración mala: es el criterio 6 del piso de
ADR-004, y reintentarla sería mandar a adivinar justo lo que el contrato prohíbe
adivinar. El costo se cobra igual — la invocación se pagó.

**El prompt no se desvía del verificador.** `verificador_entrega.REGLAS` declara
los identificadores que el verificador puede emitir, y hay un test que exige que
el prompt los nombre a todos. Sin eso los dos se separan en silencio y el modelo
produce contra reglas que ya no son las que lo rechazan.

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

[`examples/pedido-ejemplo.json`](examples/pedido-ejemplo.json) es esa plantilla
completada: un pedido válido, con los seis campos y los tres techos puestos, que
sirve para ver la forma de uno bueno antes de escribir el propio.

```
./.venv/bin/python src/intake.py --pedido examples/pedido-ejemplo.json
```

El pedido propio no se versiona: `mi-pedido.json` está en `.gitignore`, porque
es de quien corre la fábrica y no del repositorio.

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

La ruta se resuelve en dos pasos. Si `SOFTWARE_FACTORY_STATE_DIR` está definida,
el estado cuelga de ese directorio, y es la forma principal de cambiarlo:

```
$SOFTWARE_FACTORY_STATE_DIR/factory.db
```

Si no está definida, la ubicación se ancla en la del propio módulo y cae en el
directorio hermano del vault y de este repo, que es donde vive hoy:

```
<hermana-del-repo>/software-factory-state/factory.db
```

De ese mismo directorio cuelgan `trabajo/`, `entregas/` y `checkpointer/`. Una
sola variable gobierna las cuatro rutas a propósito: con una variable por ruta,
el estado podría quedar partido en discos distintos sin que nadie avise.

`trabajo/` y `entregas/` son hermanas y no la misma carpeta. La primera es
descartable y se borra al aprobar el Gate de salida; la segunda es la evidencia
de lo entregado —ADR-015— y sobrevive. La evidencia se escribe **desde los
eventos**, no copiando el directorio de trabajo: por eso es derivable, y si
alguna vez discrepara con el registro, gana el registro.

Si el directorio no existe, se crea al abrir el almacén. La ruta también es
configurable por constructor; los tests siempre usan una base temporal.

### Advertencia — R8

**El almacén no está versionado ni respaldado.** Vive fuera de todo repositorio
git a propósito: un hecho no tiene versiones, tiene ocurrencia. La contrapartida
es que **si ese directorio se pierde, se pierde toda la evidencia de todo lo que
la fábrica hizo, sin reconstrucción posible desde el Vault.**

Es el riesgo R8 del registro del Project Master Plan, hoy abierto. El
procedimiento de respaldo se declara en Infrastructure, documento todavía
bloqueado. Hasta entonces **el respaldo es manual y es responsabilidad del
CEO.**

`entregas/` entra en la misma categoría y hereda el mismo riesgo. Es regenerable
desde los eventos —esa es la ventaja de derivarla del registro—, pero solo
mientras el registro exista.

## Armazón de ejecución (T14)

La pieza que conecta a las otras seis y hace que exista una corrida. No agrega
lógica de negocio: T10 valida la definición, T8 valida el pedido, T12 mide y
corta, T11 abre y registra Gates, T7 verifica, T13 persiste. T14 los ordena con
un grafo de LangGraph, según ADR-006.

La especificación completa está en [`docs/T14-spec.md`](docs/T14-spec.md).

**Dos fases, no una.** Cargar la definición, validar el pedido e ingresarlo
ocurren **antes** del grafo: el `run_id` que devuelve el Intake es el `thread_id`
con el que LangGraph indexa el checkpoint, y una definición o un pedido
inválidos tienen que fallar sin escribir un solo evento.

```
./.venv/bin/python correr.py --pedido pedido.json --definicion "…/Requirement Agent.md"
./.venv/bin/python correr.py --pedido pedido.json --definicion "…/Requirement Agent.md" --stub
./.venv/bin/python correr.py --reanudar <run_id>
```

Una corrida nueva avanza hasta el primer Gate, imprime el `run_id` y **termina
el proceso**. El Gate se resuelve con la CLI de T11 y recién ahí se reanuda. Ese
ciclo es deliberado: un proceso vivo esperando a una persona durante horas
invita a ponerle un timeout, y ADR-004 lo prohíbe.

El productor es inyectable —`producir_fn(pedido, plan_anterior, incumplimientos,
contexto_vault)`— para que los tests pongan planes predecibles y para que la
conexión con el modelo real de T15 entrara sin tocar el armazón. Hoy `correr.py`
inyecta **el productor real por defecto**: cada iteración es una invocación al
modelo contra la API de Anthropic, con la credencial de `.env`.

`--stub` es lo que hay que pedir explícitamente para lo otro: reemplaza al
productor por uno de relleno que arma un plan mínimo que pasa T7 sin invocar a
nadie. Sirve para ejercitar el armazón de punta a punta sin gastar, y no exige
credencial.

**Una corrida sin `--stub` gasta dinero real.** Cada iteración se le factura a
la cuenta dueña de la `ANTHROPIC_API_KEY`, y una corrida que corrige el plan
itera más de una vez. El techo de costo de ADR-010 acota cuánto puede gastar una
corrida antes de escalar; no evita el gasto.

El checkpointer es SQLite y vive en `software-factory-state/checkpointer/`,
**separado de `factory.db`**. Uno es mutable por diseño y el otro inmutable por
diseño: es el punto 4 de ADR-006 y no se fusionan.

## Productor real (T15)

Lo que reemplaza al stub de T14: la función que invoca al modelo y devuelve un
Plan de Trabajo. El armazón no sabe que existe un modelo —recibe una función con
la firma que declara T14 y la llama—, así que T15 entró sin tocar el grafo.

**No decide nada del proceso.** No abre Gates, no mide techos, no verifica el
plan y no escribe en el Operational State. Produce un plan y declara cuánto
costó producirlo; quien recibe eso decide qué hacer.

**El costo se mide, no se estima.** Sale de los tokens que la propia respuesta
declara, multiplicados por el precio de lista del modelo, que está escrito a
mano en `PRECIOS_USD_POR_MTOK`. Un modelo sin precio declarado no arranca: sin
precio el consumo no se puede medir y el techo de ADR-010 sería decorativo.

Se cobran los cuatro contadores, no dos: entrada, salida, escritura de caché y
lectura de caché. La escritura vale 1,25x la entrada base si el caché dura 5
minutos y 2x si dura una hora, y la lectura 0,1x; los dos TTL vienen en campos
distintos y se cobran distinto. Cobrar sólo entrada y salida con el caching
encendido hacía que el techo midiera sobre una corrida más barata que la real.

Un precio desactualizado no falla, miente — y miente en las dos direcciones. El
que subestima no corta cuando tiene que cortar; el que sobreestima corta
corridas que podían seguir. Por eso la tabla lleva **fecha de verificación y
fuente**: un precio sin eso tiene el mismo defecto que un conteo escrito a mano.

### Configuración

```
cp .env.example .env      # y completar la key a mano
```

`ANTHROPIC_API_KEY` es obligatoria en modo modelo; `ANTHROPIC_MODEL` es
opcional y por defecto vale `claude-sonnet-5`. `.env` está en `.gitignore`: la
credencial no entra al repositorio, y tampoco al Operational State, que rechaza
por nombre toda clave que parezca un secreto.

### El modo de producción es un hecho de la corrida

Con qué se produce —el modelo o el stub— se decide **una sola vez, al abrir la
corrida**, y queda registrado en el Operational State como evento
`modo_produccion_fijado` antes de gastar un token. Junto al modo se anota el
nombre del modelo, como evidencia de contra qué se produjo.

`--reanudar` lee ese hecho en vez de deducirlo de los flags. Una corrida
iniciada con `--stub` se retoma con el stub aunque quien la reanude no repita el
flag: si el modo se dedujera de la invocación, olvidarse de `--stub` al reanudar
gastaría dinero real sin que nadie lo pidiera.

Los flags no eligen en una reanudación; a lo sumo contradicen. Pedir `--stub`
sobre una corrida abierta con el modelo, o `--modelo` sobre una abierta con el
stub, **falla** nombrando el modo registrado, en vez de quedarse con uno de los
dos. Y una corrida anterior a este registro no se reanuda: elegirle un modo
ahora sería decidir por ella si gasta dinero.

## Cómo se corren los tests

```
./.venv/bin/python -m unittest discover -s tests -v
```

Cuatrocientos noventa tests, uno por cada fila de los criterios de
aceptación de las ocho tareas, más los que cubren lo que se fue arreglando
después y las piezas de V0.2:

| Archivo | Tests | Cubre |
|---|---|---|
| `test_verificador.py` | 15 | los siete fixtures de T7, cinco sobre el vocabulario cerrado de la regla 8 y tres sobre la forma de la salida |
| `test_intake.py` | 9 | el criterio de aceptación de T8 |
| `test_agent_loader.py` | 10 | el criterio de aceptación de T10 |
| `test_gates.py` | 11 | el criterio de aceptación de T11 |
| `test_presupuesto.py` | 16 | el criterio de aceptación de T12, los dos formatos del consumo y el techo medido con el caché cobrado |
| `test_operational_state.py` | 8 | el criterio de aceptación de T13 |
| `test_grafo.py` | 20 | el criterio de aceptación de T14 y el registro del modo |
| `test_productor.py` | 29 | el criterio de aceptación de T15, el desglose del consumo y la tabla de precios verificada con sus cuatro contadores |
| `test_correr.py` | 14 | el modo de producción a través de la reanudación y la precedencia entre entorno y `.env` |
| `test_verificador_entrega.py` | 50 | un defecto sembrado por regla sobre la entrega limpia, las tres reglas que miran el inventario del espacio y que C4 lea la ruta del campo y no de la prosa |
| `test_cadena.py` | 71 | la cadena completa, el reintento, la detención, los dos techos de la cadena, el depósito de artefactos, el enganche de QA y qué hace cada nodo con una respuesta ilegible |
| `test_productor_entrega.py` | 33 | el productor de entregas, con cliente falso |
| `test_correr_cadena.py` | 33 | la costura entre la CLI y la cadena, el régimen declarado y el encendido de QA |
| `test_herencia.py` | 18 | heredar un plan verificado, el techo descontado y la reejecución |
| `test_aislamiento_del_estado.py` | 5 | que la suite no escriba en el área de estado real |
| `test_conteos_declarados.py` | 6 | que ninguna afirmación del repo cite un número que la máquina ya no tiene, ni un lenguaje que el Contrato del Developer ya no manda |
| `test_ejecutor.py` | 28 | cada garantía de la frontera de ADR-016 probada intentando violarla, y la negativa a ejecutar sin frontera de kernel |
| `test_verificacion_sustantiva.py` | 40 | el anclaje, el veredicto por criterio, el invariante de la superficie de rechazo contra salidas fabricadas y el Control 4: que la evidencia dependa del artefacto |
| `test_productor_qa.py` | 42 | el productor de casos de prueba, con cliente falso, la derivación que el prompt le pide, los supuestos de la entrega llegando al mensaje, y la Agent Definition del QA Agent |
| `test_qa_contra_defectos.py` | 16 | QA contra dos entregas reales del registro: acepta las correctas y rechaza cuatro defectos sembrados nombrando el criterio que cada uno rompió |
| `test_entrega_incremental.py` | 16 | ADR-019: que la parte N no vuelva a depositar lo que dejó la N-1, que la suite de las partes firmadas falle ruidosamente, y que pisar lo firmado se rechace y escale |

Todo lo que toca el Operational State corre contra una base temporal que se
destruye al terminar. La base real nunca se abre desde los tests.

**Ningún test invoca al modelo.** Los tres productores reales se ejercitan con un
cliente falso y la CLI con un espía en lugar del productor; `.env` queda fuera
de juego para que la credencial verdadera no se cuele en el entorno de un test. Correr la suite no
cuesta plata.
