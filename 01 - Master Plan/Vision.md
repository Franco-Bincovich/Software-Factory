---
titulo: Vision
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-008]
aliases: [Vision, Visión]
---

# Vision

## Propósito

Declarar qué problema resuelve la fábrica, dónde termina, y qué la haría
fracasar. Es el documento contra el que se contrasta cualquier decisión que
parezca razonable pero desvíe el rumbo.

## Alcance

Cubre el problema, el destino, los modos de falla y las fronteras de identidad.
No cubre objetivos medibles —eso es Objectives— ni qué entra en cada versión
—eso es Scope y Roadmap—.

---

## El problema

**La capacidad de desarrollo está atada al tiempo del fundador.**

Se puede vender solo lo que se puede supervisar. Cada proyecto nuevo compite por
las mismas horas, y esas horas no crecen. El techo no es la demanda ni el
talento: es una sola agenda.

La consecuencia práctica es que hay trabajo que no se hace. Herramientas internas
que se postergan indefinidamente porque nunca son lo más urgente. Sistemas
complejos que se rechazan porque no entran en el calendario. Soporte sobre
sistemas ya entregados que compite con lo nuevo y siempre pierde.

## Qué resuelve

**Desarrollar a demanda sin que el tiempo del fundador sea el límite.**

Tres clases de trabajo, todas dentro del alcance:

**Herramientas internas** — lo que hoy se posterga por no ser urgente.
**Desarrollos complejos** — sistemas completos, del tipo de un sistema de
recursos humanos.
**Soporte sobre sistemas existentes** — mantener y evolucionar lo ya entregado,
que es el trabajo que más se descuida cuando el tiempo escasea.

Que las tres estén desde el principio no es un detalle: una fábrica que solo sabe
empezar cosas nuevas y no sabe mantenerlas resuelve la mitad del problema.

---

## El destino

**Una Software Factory Agéntica: atendida y operada íntegramente por agentes.**

La forma concreta que describe ese destino: **poder tener una conversación con el
CEO de esa empresa y que rinda cuentas de cómo viene todo.**

Esa imagen no es una metáfora. Implica capacidades que hoy no existen y que hay
que construir:

- **Estado agregado.** Alguien tiene que saber qué está en curso, qué está
  trabado y qué se entregó. Hoy el Operational State registra hechos crudos y
  nadie los sintetiza.
- **Rendición de cuentas.** Poder responder por qué algo se decidió así, no solo
  qué se decidió.
- **Interlocución.** Un punto de contacto que entienda una pregunta en lenguaje
  natural y responda con datos reales, no con una plantilla.

Ninguna está en el alcance de V1. Se anotan acá para que cuando lleguen no se
diseñen de cero, y para que las decisiones intermedias no las bloqueen.

## El camino

**Uso interno primero, y no como etapa de prueba.** La fábrica se valida
resolviendo el problema real de su dueño antes de resolvérselo a nadie más.

Trabajar para terceros exige aislamiento entre clientes, que es una capacidad
posterior a V1. Pero no es solo secuencia técnica: una fábrica que no le sirve a
quien la construyó tampoco le va a servir a un cliente.

---

## Qué la haría fracasar

Cuatro modos de falla. Están declarados para poder detectarlos temprano, no para
tranquilizar a nadie.

### 1. Costo por entrega

Si producir con la fábrica cuesta más que producir a mano, no hay narrativa que
lo salve. Es el más medible y el que primero da señales.

**Cómo se detecta:** el consumo por corrida está instrumentado desde V0.1
precisamente para esto. Los tres techos existen para que el costo sea un límite
declarado y no un descubrimiento.

### 2. Calidad de los desarrollos

Software que pasa las verificaciones y no sirve. Es el más peligroso porque no
avisa: un artefacto defectuoso que fue aprobado parece un éxito.

**Cómo se detecta:** es la razón de existir de la capa de verificación, y la razón
de que V0.3 use un dominio ajeno con defectos conocidos en vez de un caso cómodo.

### 3. Capacidad de los agentes

Que los agentes no alcancen para el trabajo real. Herramientas chicas sí, sistemas
complejos no.

**Cómo se detecta:** la escalera de versiones sube la dificultad
deliberadamente. Si la fábrica se estanca en un peldaño, ahí está el techo.

### 4. Dificultad creciente para extenderla

**Que agregar algo nuevo a la fábrica sea más difícil que hacerlo a mano.**

Es el modo de falla que mata en silencio: nadie declara que la fábrica fracasó,
simplemente se deja de usar porque cada cosa nueva cuesta demasiado. La
gobernanza que la hace confiable es exactamente lo que puede volverla rígida.

**Cómo se detecta:** el tiempo entre pedir una capacidad nueva y tenerla
funcionando. Si crece versión a versión, la fábrica se está endureciendo.

Es la tensión central del proyecto y no se resuelve de una vez: se administra.
Cada regla que se agrega tiene que ganarse su costo de rigidez.

---

## Qué no es

**No es un asistente de codificación.** Un asistente ayuda a una persona a
escribir código. Esto produce software con gobierno propio.

**No es un wrapper de chat.** No hay conversación libre con agentes. Hay un
flujo estandarizado con un punto único de ingreso.

**No es una herramienta de productividad personal.** Es la aclaración más
importante de esta sección: **la fábrica no es para uso personal del fundador.**
El uso interno es el primer cliente, no el único ni el destino. Todo lo que se
construya tiene que sostener trabajo para terceros aunque no lo haga todavía.

Esa frontera decide cosas concretas. Es la razón de que el aislamiento entre
clientes esté declarado como riesgo desde el principio en vez de aparecer cuando
haga falta, y la razón de que la trazabilidad exista antes de que nadie la exija.

---

## La tesis

**La fábrica produce evidencia además de artefactos.**

Sin la evidencia —quién pidió, contra qué criterios se aprobó, cuánto costó, qué
se verificó, quién autorizó— esto sería un envoltorio caro alrededor de un
modelo. Con ella, es una empresa que puede rendir cuentas de su trabajo.

Todo lo demás del proyecto es consecuencia de esa frase.

## Decisiones tomadas

1. El problema es la dependencia del tiempo del fundador, no el costo ni la
   velocidad.
2. El alcance incluye soporte y mantenimiento desde el principio, no solo
   desarrollo nuevo.
3. El destino es una fábrica operada íntegramente por agentes, con capacidad de
   rendir cuentas en conversación.
4. Uso interno primero, y no como etapa de prueba.
5. No es para uso personal: todo se construye pensando en terceros aunque
   todavía no los haya.

## Decisiones abiertas

1. **Cuándo se construye la capa de estado agregado y rendición de cuentas.**
   Posterior a V1, sin versión asignada.
2. **Qué mide "dificultad creciente para extenderla".** Se define con datos de
   varias versiones; hoy no hay ninguna.

## Impacto en otros documentos

**Objectives** — traduce estos modos de falla en métricas. **Scope** — declara
qué entra y qué no. **Roadmap** — el camino interno-primero deriva de acá.
**ADR-008** — el corte de V1 es la primera parada de este destino.
