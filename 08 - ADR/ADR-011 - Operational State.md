---
estado: aceptado
aprobado: 2026-08-06
version: 1.0
owner: CEO
actualizado: 2026-08-06
aliases: [ADR-011]
---

# ADR-011 — Operational State

Cierra el punto 4 de la Secuencia de decisión del Project Master Plan
("Planos de conocimiento").

## Contexto

ADR-001 nombró el Operational State y estableció que es fuente de verdad de los
hechos, pero de su ubicación solo dijo que "vive fuera del Vault". Es la única
localización negativa del vault: se sabe dónde no está y no se sabe dónde está.

Eso bloquea tres cosas concretas. El campo 11 de ADR-003 obliga a toda Agent
Definition a declarar qué lee y qué escribe distinguiendo Vault, Operational
State y Memory: sin domicilio, ninguna Agent Definition se puede completar y por
lo tanto ningún agente existe. El punto 7 de ADR-005 exige que cada verificación
deje evidencia registrada, y esa evidencia no tiene dónde caer. Y el motor de
Gates necesita persistir aprobaciones pendientes, que son el ejemplo textual que
ADR-001 da de hecho.

El riesgo de no decidirlo ahora es conocido: la primera ejecución empieza a
escribir estado donde le queda cómodo —archivos sueltos, el propio Vault, memoria
del proceso— y en dos semanas hay una fuente de verdad de facto que nadie
decidió. Es el mismo problema que ADR-000 resolvió para la documentación,
trasladado al plano operativo.

## Opciones consideradas

**A. Los hechos en el Vault, en carpetas separadas.** Descartada: contradice
ADR-001 de frente, y además ensucia el historial de git —fuente de verdad de las
normas según ADR-000— con miles de eventos operativos. El historial normativo se
vuelve ilegible.

**B. Archivos sueltos fuera del Vault, uno por Agent Run.** Simple y tentador.
Descartada por dos razones: el estado de un Gate es mutable —pendiente pasa a
aprobado— y la mutación sobre archivos sueltos no tiene integridad
transaccional; y cualquier pregunta que cruce corridas ("qué Gates están sin
responder", "cuánto se consumió esta semana") se resuelve rastrillando texto.

**C. Almacén transaccional embebido, local, fuera del Vault.** Elegida.

**D. Base de datos gestionada.** Correcta a término, prematura hoy: agrega
infraestructura antes de que exista una sola corrida, y Infrastructure está
bloqueado por la Secuencia de decisión.

## Decisión

### 1. Qué es un hecho

Pertenece al Operational State todo lo que, si se regenerara desde cero, perdería
información irrecuperable. Un ADR se puede reescribir; una corrida que ya ocurrió,
no. Esa es la prueba, y separa sin ambigüedad los tres planos de ADR-001.

En caso de duda, el criterio operativo es: si responde "qué debe pasar", es norma
y vive en el Vault; si responde "qué pasó", es hecho y vive acá.

### 2. Dónde vive

El Operational State reside **fuera del repositorio del Vault y fuera de control
de versiones**. No se commitea. Un hecho no tiene versiones: tiene ocurrencia.

Sustrato para V0.1: **almacén transaccional embebido, local, de escritor único**.
La implementación concreta es un parámetro, no una decisión de este ADR —del
mismo modo que los techos de presupuesto viven en la Agent Definition y no en un
ADR. Este ADR fija las propiedades que el sustrato debe cumplir: integridad
transaccional, consulta sobre múltiples corridas, y capacidad de distinguir
eventos inmutables de estado mutable.

**Condición de salida declarada:** el sustrato embebido deja de alcanzar cuando
aparezca ejecución concurrente o aislamiento entre clientes —previstos en V0.4—.
Migrar es un ADR nuevo, no una enmienda a éste.

### 3. Los eventos no se editan

Todo lo que ocurrió se registra una vez y no se modifica ni se borra. El estado
actual de cualquier entidad se deriva de sus eventos, no se sobrescribe. Un Gate
aprobado no reemplaza al Gate pendiente: lo sucede.

Esto es lo que hace que la evidencia sea evidencia. Un registro editable no
prueba nada.

### 4. Toda corrida tiene identidad

Cada Agent Run recibe un identificador único al iniciarse, antes de consumir un
solo token. Todo artefacto producido, toda decisión tomada, todo consumo medido y
toda aprobación otorgada se referencian a ese identificador. Un hecho sin corrida
asociada es un hecho huérfano y no se admite.

### 5. Entidades mínimas de V0.1

Agent Run, unidad de trabajo con sus Acceptance Criteria, resultado de
verificación, Gate con su resolución y su autor, y consumo contra los tres techos
del campo 8 de ADR-003.

La lista crece por versión. No requiere ADR ampliarla; sí lo requiere quitar
alguna.

### 6. Nada se borra en V0.1

No hay política de retención. El volumen es despreciable y el costo de haber
borrado algo que después hacía falta no lo es. Cuando el volumen importe, será un
ADR.

### 7. El Operational State necesita respaldo declarado

Consecuencia directa de no estar en git: **si se pierde, se pierde toda la
evidencia de todo lo que la fábrica hizo**, sin posibilidad de reconstrucción
desde el Vault. Su respaldo es obligatorio y su procedimiento se declara en
Infrastructure. Hasta que ese documento exista, el respaldo es manual y es
responsabilidad del CEO.

## Consecuencias

**Lo que habilita.** El campo 11 de ADR-003 pasa a ser completable, y con él
existe la primera Agent Definition. El punto 7 de ADR-005 tiene domicilio. El
motor de Gates puede persistir aprobaciones. ADR-009 tiene dónde registrar qué
identidad actuó.

**Lo que cuesta.** El sustrato embebido tiene fecha de vencimiento conocida y va
a haber que migrarlo. Se acepta a cambio de no arrastrar infraestructura antes de
la primera corrida. La inmutabilidad del punto 3 hace que corregir un dato mal
registrado exija un evento de corrección en vez de una edición, que es más lento
y es el punto.

**Lo que introduce.** Un activo crítico sin respaldo automático. Es la
contrapartida honesta de sacar los hechos de git y queda anotada como riesgo
hasta que Infrastructure lo resuelva.

## Decisiones que habilita

- V0.1 T9 — Agent Definition del Requirement Agent, campo 11.
- V0.1 T13 — registro de corrida.
- ADR-005 punto 7 — evidencia de verificación.
- ADR-009 — identidad y permisos: dónde queda registrado quién actuó.

## Decisiones que no resuelve

- **Qué motor concreto.** Es implementación y se decide al construir T13.
- **Respaldo y recuperación.** Es Infrastructure, hoy bloqueado.
- **Memory.** ADR-001 ya dice que nunca es fuente de verdad y se reconstruye. Su
  mecanismo de reconstrucción es otro ADR, y no lo necesita V0.1.
- **Retención y purga.** Diferido hasta que el volumen lo justifique.

## Crea

- `04 - Knowledge Management/Knowledge Management.md` — documento normativo
  derivado.
