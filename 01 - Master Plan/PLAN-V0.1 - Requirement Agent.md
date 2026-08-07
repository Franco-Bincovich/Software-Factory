---
titulo: PLAN-V0.1 — Requirement Agent
tipo: plan-de-version
estado: aceptado
aprobado: 2026-08-06
version: 1.0
dueño: Franco Bincovich Granada
fecha: 2026-08-06
aliases: [PLAN-V0.1, V0.1]
---

# PLAN-V0.1 — Requirement Agent

## Propósito

Llevar la fábrica desde cero ejecución hasta un Agent Run completo, verificado y
registrado, con un solo agente.

Este documento existe para poder detectar desvío. Si en algún momento se está
construyendo algo que no figura acá, o se está discutiendo una decisión que este
documento declara diferida, hay desvío y corresponde volver a este texto antes
de seguir.

---

## Por qué existe esta versión

El criterio de salida anterior de Fase 0 era "17 documentos aprobados". Ese
criterio mide documentación, no capacidad: los 17 documentos pueden estar
cerrados y no existir nada que corra. V0.1 inaugura un eje distinto — **la
fábrica versiona por capacidad operativa, no por documentos escritos** — y cada
versión se declara terminada cuando la fábrica puede hacer algo que antes no
podía, demostrado con una corrida.

Se arranca por el agente que planifica y no por el que produce, porque la salida
del Requirement Agent es el contrato de entrada de todos los agentes
posteriores. Construir primero el consumidor obligaría a inventar ese formato a
mano y a rehacerlo después. Este orden produce el contrato antes que sus
consumidores.

---

## Alcance

### Entra en V0.1

- El **Requirement Agent**: recibe un pedido estructurado y produce un plan de
  trabajo con tareas y criterios de aceptación.
- El **formulario de Intake** como mecanismo de ingreso, no como Agent
  Definition.
- Seis de las nueve piezas de runtime, en su versión mínima: registro de Agent
  Definitions con cargador validador, identidad de agente, motor de Gates,
  techo de presupuesto, registro de corrida, contrato de tarea.

### No entra en V0.1

Interpretación de pedidos difusos. Developer Agent, QA Agent, Documentation
Agent. Handoff entre agentes. Despliegue de cualquier tipo. Ejecución en
paralelo. Escritura del agente sobre el vault. Agent Factory. Frontend.
Elección de stack por proyecto. Verificación contra el mundo.

### Autonomía del agente

Conforme a ADR-001, autónomo significa sin humanos dentro de lo que tiene
permitido. En V0.1 ese perímetro es angosto y deliberado.

**Decide solo:** cómo descomponer el trabajo, cuántas tareas, en qué orden, qué
depende de qué, y qué criterio de aceptación lleva cada tarea.

**No decide:** si el plan se aprueba, si el alcance cambia, si se sube el
presupuesto, ni si está terminado. No puede declararse aprobado a sí mismo.

**Autonomy Level:** bajo. Autonomía de método, no de objetivo ni de aceptación.
Subirlo exige historial de corridas verificadas, conforme a ADR-004.

---

## Timebox

**7 días hábiles.** Al día 7 la versión corre o se recorta alcance. El plazo es
fijo, el alcance es la variable. No se extiende el plazo bajo ninguna
circunstancia: si al día 6 el registro de corrida está a medias, sale en su
forma mínima y se mejora en V0.2.

| Bloque | Contenido | Días |
|---|---|---|
| A | Decisiones — cinco ADRs en versión mínima | 1–2 |
| B | Construcción — nueve tareas de runtime | 3–5 |
| C | Corrida — se rompe y se arregla | 6–7 |

---

## Bloque A — Decisiones (días 1–2)

Los cinco ADRs llegan redactados y cerrados, con la decisión tomada y su
justificación. El CEO aprueba, corrige o rechaza. No se usa el formato de
opciones abiertas. Las cinco tareas son independientes entre sí.

| Tarea | Qué cierra | Criterio de aceptación |
|---|---|---|
| **T1 — ADR-005** | Capa de verificación. Alcance V0.1: verificación estructural contra criterios declarados. El que produce no aprueba. Verificación contra el mundo diferida a V0.3, declarada como alcance diferido y no como omisión | El ADR nombra las cinco reglas estructurales de T7 y declara explícitamente qué no cubre |
| **T2 — ADR-008** | Corte de V1 y la escalera V0.1 → V1 | Cada versión de la escalera tiene criterio de terminación binario y observable |
| **T3 — ADR-009** | Identidad y permisos. Alcance V0.1: una identidad propia, una credencial, alcance mínimo — lee el pedido, escribe solo en su carpeta de salida | El registro de corrida distingue al agente del CEO como autores |
| **T4 — ADR-010** | Modelo de costo. Techo de presupuesto por corrida, unidad de medida, comportamiento al alcanzarlo | Define que al alcanzar el techo se corta, no se avisa |
| **T5 — ADR-011** | Localización del **Operational State** — término canónico de ADR-001. Dónde viven los hechos: registro de corrida, evidencia de verificación, estado de Gates | Especifica ruta, formato y si se versiona |

**T5 no es paralelo: bloquea a T9 y a T13.** El campo 11 de ADR-003 obliga a
declarar qué lee y qué escribe el agente distinguiendo Vault, Operational State y
Memory. Sin ADR-011 cerrado, la Agent Definition no se puede completar y el
registro de corrida no tiene domicilio. **T5 se escribe primero del bloque A.**

**Fuera del camino crítico:** ADR-006 (LangGraph como coordinador) es deuda de
registro de una decisión ya tomada. Se escribe cualquier día de la semana; no
bloquea nada.

---

## Bloque B — Construcción (días 3–5)

**T6 es la ruta crítica.** T7 y T9 lo esperan. Se arranca por ahí.

| Tarea | Qué es | Criterio de aceptación | Depende de |
|---|---|---|---|
| **T6 — Esquema del plan de trabajo** | El formato fijo de salida del agente. Es el contrato de entrada del Developer Agent en V0.2. Cerrado por [[Contrato del Plan de Trabajo]]. | Un plan escrito a mano valida contra el esquema; uno al que le falta un criterio de aceptación, no | T1 |
| **T7 — Verificador estructural** | Rechaza el plan si: hay tarea sin criterio de aceptación, criterio no medible, dependencia a tarea inexistente, tarea no rastreable al pedido original, o alcance no solicitado. Si el plan supera 10 tareas, escala en vez de entregar. Cerrado. Implementado en software-factory-core/src/verificador.py. | Sobre cinco planes con un defecto sembrado cada uno, detecta los cinco; sobre un plan limpio, no marca falsos positivos | T6 |
| **T8 — Formulario de Intake** | Campos fijos: qué se quiere, para qué, qué NO entra, techo de presupuesto | Un pedido sin techo declarado no arranca | T4 |
| **T9 — Agent Definition del Requirement Agent** | Los 13 campos obligatorios de ADR-003, completos. Cerrado por [[Requirement Agent]]. | Ningún campo vacío. Declara consumidor temporal: humano | T3, T4 |
| **T10 — Cargador con validación** | Lee la Agent Definition y se niega a arrancar si falta un campo | Borrando un campo a propósito, no arranca e indica cuál falta | T9 |
| **T11 — Motor de Gates** | Gate de entrada — se aprueba pedido y techos antes de gastar. Corresponde al criterio 6 del piso de ADR-004. Gate de salida — se aprueba el plan producido. **No corresponde a ningún criterio del piso: es un Gate propio del agente**, de los que ADR-004 permite agregar, y se declara como tal en la Agent Definition. Vencimiento nunca es aprobación | Un Gate sin responder no deja avanzar. Queda registrado quién aprobó y cuándo | T8 |
| **T12 — Contador de presupuesto** | Mide consumo real contra los **tres techos** que exige el campo 8 de ADR-003 —costo, tiempo e iteraciones— y corta al alcanzar cualquiera de ellos | Con cada uno de los tres techos puesto artificialmente bajo, la corrida se corta y el registro declara cuál se alcanzó | T4, T5 |
| **T13 — Registro de corrida** | Un archivo por corrida: qué Agent Definition, qué pedido, qué consumió, qué produjo, qué Gates hubo, quién aprobó. Cerrado. Implementado en software-factory-core/src/operational_state.py. | Se reconstruye qué pasó leyendo solo el registro, sin mirar la consola | T5 |
| **T14 — Armazón LangGraph** | Grafo de un nodo con los Gates alrededor | Corre de punta a punta encadenando T10 a T13 | T10, T11, T12, T13 |

---

## Bloque C — Corrida (días 6–7)

| Tarea | Criterio de aceptación |
|---|---|
| **T15 — Primera corrida real** | Entra un pedido por el formulario, sale un plan que pasa T7, los dos Gates atendidos, registro de corrida completo |
| **T16 — Ejecución manual del plan** | El plan se ejecuta con Claude Code sin improvisar ninguna tarea que el plan no previó |
| **T17 — Corrida de control** | Un segundo pedido distinto, sin tocar código entre una corrida y otra |

---

## Criterio de terminación de V0.1

Los tres a la vez: T15 pasa, T16 pasa, T17 pasa.

**T16 es el que decide.** Un plan de trabajo, a diferencia del código, no se
puede verificar mecánicamente: puede estar perfectamente bien formado y ser
malo. Si al ejecutarlo hubo que improvisar una tarea que el plan no previó, el
plan tenía un hueco y el agente no sirve todavía. Está bien formado pero no está
bien.

---

## Decisiones tomadas

1. **V0.1 se construye sobre LangGraph** aunque con un solo agente esté
   sobredimensionado. Un grafo de un nodo es trivial de escribir; reescribir el
   armazón en V0.2 no lo es.
2. **La interpretación de pedidos difusos se difiere a V0.2** y, cuando llegue,
   nace como **Intake Agent** — no se le agrega al Requirement Agent. Agregarla
   cambiaría la identidad del agente conservando el nombre y rompería la
   trazabilidad de las corridas de V0.1.
3. **Intake en V0.1 es mecanismo, no Agent Definition.** Queda asentado para que
   no se lea después que el Intake Agent existía desde V0.1.
4. **Verificación contra el mundo diferida a V0.3.** V0.1 verifica contra la
   especificación declarada.
5. **El registro de corrida vive fuera del vault de reglas**, conforme a la
   separación de ADR-001 entre reglas y hechos.
6. **La ejecución manual del plan es criterio de terminación**, no una prueba
   opcional.
7. **Ningún agente lleva un nombre del vocabulario canónico si no cumple ese rol
   y solo ese rol.** Un agente que cumple varios roles lleva otro nombre y se
   declara provisional.
8. **Los techos son editables; subirlos no lo es en silencio.** Los valores viven
   en la Agent Definition, no en un ADR, y se cambian cuando haga falta. Elevar
   un techo dispara Gate por el criterio 4 del piso de ADR-004 y queda
   registrado.
9. **El Gate de salida de V0.1 es un Gate propio del agente**, no heredado del
   piso obligatorio. Se declara explícitamente en la Agent Definition para que no
   se lea como si el piso lo cubriera.

---

## Decisiones abiertas

1. **Caso de prueba de T15 y T17.** Vence el día 5. Por defecto, si no se elige:
   validador de altas de empleados sobre CSV. Candidato alternativo de control:
   el plan de trabajo de algo ya construido en HR Karstec, donde la respuesta
   correcta es conocida.
2. **Dónde vive la regla de nombres canónicos** — ADR-007 o ADR corto propio. No
   bloquea V0.1.

---

## Escalera de versiones

V0.1 es el primer peldaño de una escalera declarada. Cada peldaño es un momento
legítimo para parar.

| Versión | Capacidad nueva | Terminada cuando |
|---|---|---|
| **V0.1** | Un agente, un ciclo cerrado, evidencia | Una corrida produce un plan ejecutable sin improvisación |
| **V0.2** | Developer Agent e Intake Agent. Handoff formal | Un pedido difuso se convierte en plan y en código sin intervención entre etapas |
| **V0.3** | Verificación contra el mundo | El QA Agent encuentra los defectos sembrados del agente de sentimiento |
| **V0.4** | Identidad por agente, permisos acotados, aislamiento entre proyectos | Dos proyectos corren en secuencia sin contaminarse y el log distingue quién hizo qué |
| **V1** | Según ADR-008 | Tres herramientas internas de punta a punta, sin código escrito por el CEO |

---

## Riesgos de esta versión

**El dominio es cómodo.** Producir un plan de trabajo es de las cosas que un
modelo hace mejor. Un éxito en V0.1 no prueba que la fábrica sirva para software
real: prueba que el ciclo de gobierno cierra, que es otra cosa y es la que se
necesita primero.

**Un plan malo pero bien formado pasa la verificación estructural.** Todos los
planes de V0.1 se leen enteros. Es tolerable solo si los proyectos son chicos, y
por eso el límite de 10 tareas es una regla del agente y no una sugerencia.

**El CEO sigue siendo el único aprobador.** R3 no se mitiga en V0.1. Se difiere.

---

## Impacto en otros documentos

| Documento | Impacto |
|---|---|
| **Project Master Plan** | El criterio de salida de Fase 0 deja de ser 17 documentos aprobados y pasa a ser los cinco ADRs del bloque A. Requiere reescritura de la sección de secuencia |
| **ADR-002** | Las nueve piezas de runtime necesitan dueño documental. Seis se construyen en V0.1; las tres restantes — manejo de fallo, workspace aislado, escritura al vault — quedan declaradas como pendientes con versión asignada |
| **ADR-003** | T9 es la primera instancia real del contrato de 13 campos. Si algún campo no aplica a un agente que no produce código, el contrato tiene un hueco y hay que registrarlo |
| **ADR-004** | T11 es la primera implementación del motor de Gates. Los dos Gates de V0.1 se corresponden con los criterios de ambigüedad de requerimiento y exceso de presupuesto |
| **Registro de riesgos** | R1 pasa a mitigado parcialmente al cerrar T1. R2 pasa a mitigado al cerrar T4 y T12. R3 sin cambios |
| **Agent Framework** (pendiente) | T6, T9 y T10 son insumo directo: son el contrato de tarea y el ciclo de carga de un agente, observados en un caso real |
| **Human in the Loop** (pendiente) | T11 define el mecanismo concreto que ese documento tiene que normar |
