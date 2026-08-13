---
titulo: Scope
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-004, ADR-008, ADR-009]
aliases: [Scope, Alcance]
---

# Scope

## Propósito

Declarar qué puede hacer la fábrica, qué no, y —sobre todo— **cómo se amplía esa
frontera**.

## Alcance

Cubre el alcance funcional, el mecanismo de ampliación, el manejo de lo que no se
puede resolver, y el límite de la autoconstrucción. No cubre qué entra en cada
versión —eso es Roadmap— ni cómo se construye —eso es Development Methodology—.

---

## La frontera es móvil

El alcance de la fábrica **no es una lista fija**. Empieza angosto y se amplía.

Al principio va a haber mucho software fuera de su alcance. El destino es que la
gran mayoría de los pedidos entren. Entre esos dos puntos hay un recorrido, y este
documento existe para que ese recorrido sea deliberado en vez de accidental.

Por eso lo que importa acá no es el inventario de hoy —que caduca— sino **la
distinción entre lo que todavía no puede y lo que nunca va a poder**.

### Todavía no ≠ nunca

| | Qué es | Qué pasa con el tiempo |
|---|---|---|
| **Todavía no** | Falta capacidad. Es un problema de madurez | Se amplía cuando haya evidencia |
| **Nunca** | Está prohibido por decisión, no por capacidad | No se amplía. Cambiarlo requiere ADR |

Confundirlas es caro en las dos direcciones. Tratar un "nunca" como "todavía no"
lleva a construir hacia donde no hay que ir. Tratar un "todavía no" como "nunca"
congela la frontera y produce el modo de falla 4 de Vision.

---

## Lo que nunca entra

Cuatro fronteras permanentes. No son limitaciones técnicas: son decisiones.

### 1. La fábrica no cambia sus propias reglas de gobierno

Puede producir agentes, herramientas y capacidades. **No puede modificar lo que la
limita.**

Un sistema que edita sus propias reglas de gobierno no tiene gobierno. Está ya
garantizado por la arquitectura: escribir en el Vault es efecto normativo y exige
Gate, sin excepción declarable.

### 2. La fábrica no aprueba su propio trabajo

En ningún nivel de autonomía, en ninguna versión. Es el principio de precedencia
más alta.

### 3. Software donde el costo de un defecto es irreversible

Nada donde una falla implique daño físico, sanitario o legal irreparable. No es
una cuestión de capacidad del modelo: es que la fábrica no puede rendir cuentas de
ese riesgo, y la evidencia que produce no alcanza para ese estándar.

### 4. Trabajo que exige certificaciones formales que la agencia no tiene

Cumplimiento regulatorio auditado por terceros, certificación formal de
accesibilidad, normas sectoriales con auditoría externa. La fábrica puede producir
software que las respete; **no puede firmar que las cumple.**

---

## Lo que todavía no entra

Inventario al día de hoy. **Caduca**, y esa es la intención.

| Fuera hoy | Qué falta para que entre |
|---|---|
| Trabajo para terceros | Aislamiento entre clientes. R7, V0.4 |
| Varios proyectos en paralelo | Concurrencia. V0.4 |
| Despliegue remoto | Security e Infrastructure. Post V1 |
| Interfaces gráficas | Alcance de V1 |
| Creación dinámica de agentes | Contrato probado sobre varios agentes reales. Post V1 |
| Sistemas de alta concurrencia o tiempo real | Sin evidencia de capacidad. Sin versión asignada |
| Proyectos de más de diez unidades de trabajo por plan | Composición y descomposición jerárquica. V0.2 en adelante |

---

## Cómo se amplía la frontera

**Con evidencia, no con optimismo.** Una capacidad entra al alcance cuando la
fábrica demostró que puede sostenerla, no cuando parece que podría.

El mecanismo:

1. Un pedido cae fuera del alcance. La fábrica lo declara.
2. Se identifica qué capacidad concreta falta.
3. Esa capacidad se asigna a una versión, con criterio de terminación propio.
4. Cuando la versión demuestra la capacidad, el alcance se amplía y **este
   documento se actualiza**.

**Un pedido rechazado repetidamente por la misma causa es información, no una
molestia.** Es la fábrica señalando dónde está su próximo peldaño.

---

## Declaración de incapacidad

Cuando la fábrica no puede resolver un pedido, **lo dice, y lo dice de forma
usable**.

Es una capacidad, no un mensaje de error. Requiere dos cosas que hoy no existen:
evaluar la factibilidad **antes** de comprometerse, y traducir un límite técnico a
lenguaje que un cliente entienda.

### Los dos registros

Todo escalamiento por incapacidad produce **dos versiones del mismo hecho**:

**Registro técnico** — para el fundador. Qué capacidad falta, qué la bloquea, a
qué versión está asignada. Vive en el Operational State.

**Registro funcional** — para llevarle al cliente. Qué parte del pedido no se
puede resolver y qué implica, **sin una sola palabra técnica**. Sin nombres de
componentes, sin arquitectura, sin jerga.

Ejemplo del mismo hecho en los dos registros:

> **Técnico:** el pedido requiere procesamiento concurrente de más de un proyecto
> simultáneo; el sustrato del Operational State es de escritor único; capacidad
> asignada a V0.4.
>
> **Funcional:** este trabajo necesita atender varias cosas al mismo tiempo, y hoy
> el sistema resuelve de a una. Se puede hacer en etapas, o esperar a que esa
> capacidad esté lista.

**El registro funcional propone alternativas cuando existen.** "No se puede" a
secas no le sirve a nadie que tenga que hablar con un cliente.

### Cuándo se declara

**Antes de consumir presupuesto, siempre que sea posible.** Descubrir a la mitad
que no se puede es peor que descubrirlo al principio: gastó y no entregó.

Es una razón concreta para que el Intake Agent de V0.2 evalúe factibilidad, no
solo interprete el pedido.

---

## Autoconstrucción

**Puede construirse a sí misma en sus capacidades. No en sus reglas.**

| Puede producir | No puede |
|---|---|
| Agentes nuevos | Modificar el piso de Gates |
| Herramientas para agentes existentes | Ampliar sus propios permisos |
| Habilidades y automatizaciones internas | Cambiar sus techos de presupuesto |
| Sus propias herramientas de trabajo | Alterar la capa de verificación |
| Herramientas internas fuera del runtime | Tocar el motor de Gates, el contador de presupuesto, el Operational State o el cargador de definiciones |
| El código del Deployment Agent | Escribir su propia lista de comandos autorizados |

### La regla que lo sostiene

**Todo lo que la fábrica produzca para sí misma llega como propuesta a un Gate.**
Nunca se autoconcede capacidad.

Ya está garantizado sin agregar nada: crear una Agent Definition es escribir una
norma en el Vault —criterio 3 del piso, efecto normativo— y es crear capacidad
—criterio 5—. Dos criterios se activan a la vez.

### Cuándo se habilita

**Cuando existan cuatro agentes construidos a mano y el QA Agent esté probado.**
No antes, y no depende de que V1 esté terminada.

Los cuatro a mano: **Intake, Requirement, Developer y QA**. Son el mínimo que
cierra el circuito con verificación independiente — uno recibe, uno planifica,
uno produce, y uno verifica sin haber producido. Con eso no hay autoaprobación en
ningún eslabón.

#### QA existiendo no alcanza: tiene que estar probado

Es la condición que importa y la que puede fallar en silencio.

Si se paraleliza con un QA Agent que nunca demostró que encuentra defectos, todo
lo que la fábrica construya después queda verificado por algo cuya capacidad
nunca se comprobó. Y como no se comprobó, nadie se va a enterar.

**La prueba está definida:** el criterio de terminación de V0.3 — el QA Agent
encuentra los defectos sembrados del agente externo de REV-001. Dominio ajeno,
respuesta conocida, imposible hacer trampa.

#### El problema de la verificación circular

De acá sale el orden, y es la razón por la que QA no puede ser lo último.

Si el Developer Agent escribiera al QA Agent, entonces el QA que verifica el
trabajo del Developer habría sido escrito por el Developer. **Es autoaprobación
con un paso de distancia**, y que un humano dé las órdenes no lo arregla: el
problema no es la intención, es que la cadena de verificación se cierra sobre sí
misma.

Por eso el QA Agent se construye a mano, y antes de habilitar la
autoconstrucción.

#### Trabajo en paralelo

Habilitada la autoconstrucción, el trabajo manual y el autónomo avanzan en
paralelo. Con una regla:

**Un artefacto tiene un solo dueño por vez.** Lo que la fábrica está
construyendo no se toca a mano, y lo que se está haciendo a mano no entra a un
pedido. Sin esa regla, en dos semanas hay dos versiones de algo y nadie sabe cuál
vale.

#### El corte en Deployment

La fábrica puede escribir el código del Deployment Agent. **La lista cerrada de
comandos autorizados se escribe a mano, siempre.**

Esa lista es lo único que limita al único agente con acceso a ejecución de
comandos. Si la escribiera la fábrica, ese agente habría definido sus propios
límites.

## Decisiones tomadas

1. El alcance es una frontera móvil, no una lista fija.
2. Se distingue "todavía no" de "nunca", y la segunda categoría requiere ADR para
   cambiar.
3. La frontera se amplía con evidencia demostrada, no con expectativa.
4. Toda incapacidad produce dos registros: técnico y funcional.
5. El registro funcional no lleva jerga y propone alternativas cuando existen.
6. La fábrica construye sus capacidades, nunca sus reglas.
7. La autoconstrucción se habilita cuando existan cuatro agentes a mano —Intake,
   Requirement, Developer, QA— y el QA Agent esté probado contra defectos
   conocidos. No depende de que V1 esté terminada.
8. El QA Agent se construye a mano por el problema de verificación circular.
9. En paralelo, un artefacto tiene un solo dueño por vez.
10. La lista de comandos del Deployment Agent se escribe a mano, siempre.

## Decisiones abiertas

1. **Cómo se evalúa factibilidad antes de comprometerse.** Es una capacidad
   nueva del Intake Agent, V0.2.
2. **Quién produce el registro funcional.** Podría ser el mismo agente que
   escala, o una capacidad aparte. Se decide en V0.2.
3. **Qué evidencia habilita una ampliación de alcance.** Hoy se decide caso por
   caso; con varias versiones habrá criterio.
4. **Cómo se detecta que un artefacto tiene dos dueños.** La regla está
   declarada; el mecanismo de control, no.

## Impacto en otros documentos

[[Vision]] — este documento operativiza su destino de "la gran mayoría de los
pedidos". [[Roadmap]] — el inventario de "todavía no" se corresponde con sus
versiones. [[ADR-004]] — los dos criterios del piso que bloquean la
autoconcesión de capacidad. [[Agent Framework]] — la Agent Factory hereda el
límite de autoconstrucción.
