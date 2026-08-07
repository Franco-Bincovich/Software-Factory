---
titulo: Technology Stack
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-004, ADR-006, ADR-008, ADR-011]
aliases: [Technology Stack, Stack]
---

# Technology Stack

## Propósito

Declarar con qué tecnología se construye la fábrica y con qué tecnología
construye la fábrica, que son dos cosas distintas y no se mezclan.

Y fijar **cómo se elige** entre los patrones disponibles para un pedido concreto.

## Alcance

Cubre el stack interno de la fábrica y los patrones de construcción para el
software que produce. No cubre infraestructura ni despliegue —eso es
Infrastructure— ni las reglas de código —eso es la Constitución Técnica—.

---

## Dos stacks, no uno

Es la distinción que ordena todo este documento.

| | Stack interno | Patrones de construcción |
|---|---|---|
| **Qué es** | Con qué está hecha la fábrica | Con qué construye la fábrica |
| **Quién decide** | ADR | Tabla de decisión, por proyecto |
| **Cambia** | Casi nunca | Por pedido |

Confundirlos llevaría a que la fábrica construya todo con lo que ella misma está
hecha, que es una razón pésima para elegir una tecnología.

---

## Parte 1 — Stack interno de la fábrica

Todo decidido por ADR. Se registra acá para tenerlo en un solo lugar.

| Capacidad | Tecnología | Fuente |
|---|---|---|
| Orquestación de agentes | LangGraph, versión fija | ADR-006 |
| Lenguaje del runtime | Python | Consecuencia de LangGraph |
| Operational State | Almacén transaccional embebido, escritor único | ADR-011 |
| Estado de ejecución | Checkpointer de LangGraph, archivo separado | ADR-006 |
| Vault | Markdown bajo git, Obsidian como visor | ADR-000 |
| Validación de esquemas | Validador de JSON Schema | T7 |

### Reglas del stack interno

**Versiones exactas, nunca rangos.** Un cambio de comportamiento en el mecanismo
de interrupción afectaría a los Gates, y eso no puede llegar por una
actualización automática.

**Ninguna dependencia nueva sin justificación declarada.** El repositorio arrancó
con librería estándar; cada agregado se declara.

**No se incorpora el ecosistema del proveedor del orquestador** — ni LangChain, ni
sus herramientas de observabilidad, ni su plataforma de despliegue.

### Condiciones de salida ya declaradas

El almacén embebido deja de alcanzar cuando aparezca ejecución concurrente o
aislamiento entre clientes, previstos en V0.4. Migrar es un ADR nuevo.

---

## Parte 2 — Los dos patrones de construcción

La fábrica reconoce **dos patrones**. Ninguno es el correcto en abstracto: cada
uno resuelve un perfil de problema distinto.

**Solo uno está habilitado hoy.**

| Patrón | Estado | Qué falta para habilitarlo |
|---|---|---|
| **A — servicio persistente** | **Habilitado** | — |
| **B — web serverless** | **Declarado, no habilitado** | Su paquete normativo completo |

Un patrón declarado y no habilitado **no se elige**. La tabla de decisión existe y
hoy resuelve siempre a A; los disparadores de B se registran igual, porque un
pedido que los active es la señal de que llegó el momento de habilitarlo.

### Patrón A — Aplicación con servicio persistente

El de la Constitución Técnica. Es el patrón **por defecto**.

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Frontend | React + Next.js (App Router) + TypeScript |
| Datos | PostgreSQL |
| Cómputo | Contenedor o instancia |
| Nube | AWS |

**Qué habilita:** tareas en background, procesos largos sin límite de timeout,
transacciones relacionales con joins, persistencia de archivos entre peticiones,
y aislamiento de datos por Row Level Security según la sección 6.5 de la
Constitución.

**Qué cuesta:** infraestructura que corre y se paga aunque nadie la use, y
operación permanente.

### Patrón B — Web serverless — **no habilitado**

Se declara completo para que, cuando se habilite, no se diseñe de cero.

| Capa | Tecnología |
|---|---|
| Entrada, CDN y HTTPS | CloudFront con dominio propio |
| Frontend | Build estático en S3, bucket privado con OAC |
| API | API Gateway HTTP API, integración Lambda proxy |
| Backend | Lambda, funciones chicas y sin estado |
| Datos | DynamoDB |
| Secretos | Secrets Manager |
| Observabilidad | CloudWatch, WAF según exposición |
| TLS y DNS | ACM en us-east-1 + Route 53 |

Frontend y API bajo un único dominio: `/*` va a S3, `/api/*` va a API Gateway.

**Qué habilita:** escalado automático por demanda, costo cercano a cero sin
tráfico, sin servidores que operar, distribución global del frontend.

**Qué cuesta:** timeout de petición acotado, sin procesos largos, arranque en
frío, modelo de datos sin joins ni transacciones multi-tabla, y sin persistencia
de archivos entre invocaciones.

#### Qué le falta a Patrón B para habilitarse

Tres piezas. Ninguna es opcional.

**Constitución Técnica B.** La estructura de capas de la Constitución actual
—router, service, repository— no mapea a handlers de función. Los límites de
tamaño no aplican igual. El modelado de datos por patrones de acceso es una
disciplina distinta de normalizar relacional, no una variante.

**Ruleset mecánico B.** Las once reglas actuales asumen la estructura de A. Sin
su propio ruleset, **un proyecto en B no tiene verificación estructural** y el QA
Agent no tendría contra qué comparar.

**Mecanismo de aislamiento de datos.** La sección 6.5 de la Constitución exige
dos capas de contención y sus dos variantes son de PostgreSQL. En B esa sección
no aplica y no hay reemplazo escrito. **Es bloqueante para cualquier proyecto
multi-cliente.**

---

## Paquetes normativos

Los dos patrones **no tienen agentes propios**. Tienen paquetes normativos
propios.

Un paquete normativo es el conjunto de documentos que un agente carga para
trabajar en un patrón: su Constitución Técnica, su Ruleset mecánico y sus
convenciones de estructura.

| | Paquete A | Paquete B |
|---|---|---|
| Constitución Técnica | Existe | Falta |
| Ruleset mecánico | Existe | Falta |
| Aislamiento de datos | Sección 6.5 | Falta |

### Por qué no son áreas separadas

Aplicando la regla de Agent Framework —un área justifica su propio agente solo si
tiene reglas, herramientas y criterios de verificación distintos— los patrones
pasan la prueba de las **reglas** y la de la **verificación**, pero no la de las
**herramientas**: el flujo de trabajo es el mismo. Planificar, producir,
verificar, documentar.

Y hay una razón más fuerte. **El noventa por ciento de una Agent Definition es
gobierno**: Gates, techos, escalamiento, evidencia, alcance de decisión. Eso es
idéntico en los dos patrones. Duplicar el set de agentes duplicaría el gobierno,
y el día que un arreglo se aplique en uno solo, divergen.

Es el modo de falla 4 de Vision en su forma más concreta: la fábrica volviéndose
más cara de extender que de esquivar.

**Un set de agentes, dos paquetes normativos.** El mecanismo ya existe: es
`vault_lectura` en el frontmatter de cada Agent Definition.

### La excepción plausible

**Deployment.** Desplegar un contenedor y desplegar una distribución de CDN con
almacenamiento estático y funciones son conjuntos de herramientas genuinamente
distintos, y la lista cerrada de comandos sería otra.

Si al escribir la Agent Definition del Deployment Agent para B la lista de
comandos no se parece en nada a la de A, **ahí sí corresponde partirlo**. Se
decide con la lista en la mano, no antes.

---

## Cómo se elige

**No lo decide un agente por criterio propio.** Lo resuelve una tabla de
decisión declarada. Determinista, auditable, y sin necesidad de un Architect
Agent que ADR-008 no instancia.

### Regla base

**Hoy todo resuelve a Patrón A**, porque es el único habilitado. Tres razones lo
sostienen: la Constitución Técnica está escrita para él, el Ruleset mecánico
verifica contra él, y es donde la agencia tiene experiencia real.

Los disparadores y bloqueadores de abajo se evalúan y se registran igual. **Un
pedido que active disparadores de B y no tenga bloqueadores es la señal de que
llegó el momento de habilitarlo** — y mientras tanto, es información que hay que
darle al cliente en el registro funcional.

### Disparadores hacia Patrón B

Basta uno para considerarlo.

| Disparador | Por qué |
|---|---|
| Tráfico esporádico o impredecible, con línea base cercana a cero | El costo de A se paga aunque no haya uso |
| Sitio principalmente estático con API mínima | A es infraestructura de más |
| El cliente exige escalado automático sin operación | Es lo que B da de fábrica |
| Presupuesto de infraestructura muy acotado | B cuesta casi nada sin tráfico |

### Bloqueadores de Patrón B

Basta uno para descartarlo, **aunque haya disparadores a favor**.

| Bloqueador | Por qué |
|---|---|
| Tareas en background o procesos que exceden el timeout de petición | Lambda no los sostiene |
| Modelo de datos relacional con joins o transacciones multi-tabla | DynamoDB no es el lugar |
| Persistencia de archivos entre peticiones | Lambda no tiene estado |
| Arranque en frío inaceptable para el caso de uso | Es inherente al patrón |
| Aislamiento multi-cliente por Row Level Security | Es una capacidad de PostgreSQL |

**Los bloqueadores ganan a los disparadores.** Siempre.

### Qué pasa hoy cuando un pedido pide B

Se produce en Patrón A si no hay bloqueadores para A, y **se declara en el
registro funcional que existe una arquitectura más adecuada que todavía no está
disponible**. No se oculta.

Si además hay bloqueadores para A —el pedido no se puede resolver bien con el
único patrón habilitado— es una declaración de incapacidad según Scope, y se
escala.

### Cuando no alcanza

Si el pedido no da información suficiente para evaluar los disparadores ni los
bloqueadores, **se escala**. Es ambigüedad de requerimiento y dispara el criterio
6 del piso de ADR-004.

No se elige por defecto ante la duda: elegir mal el patrón es de las decisiones
más caras de revertir.

### Cuándo se decide

**Antes de producir el plan**, y la elección se somete en el **Gate de entrada**
junto con el pedido y los techos.

Migrar de patrón a mitad de un proyecto es costoso de revertir —criterio 1 del
piso—, así que la decisión se aprueba antes de que exista trabajo que migrar.

---

## Cómo se comunica la elección

**Dos registros**, igual que la declaración de incapacidad de Scope.

**Registro técnico** — para el fundador. Qué patrón, qué disparadores se
activaron, qué bloqueadores se descartaron y con qué evidencia del pedido. Vive
en el Operational State.

**Registro funcional** — para llevarle al cliente. **Cero jerga.** Sin nombres de
servicios, sin arquitectura, sin siglas.

Ejemplo de la misma elección en los dos registros:

> **Técnico:** Patrón B. Disparadores: tráfico esporádico, sitio mayormente
> estático. Bloqueadores evaluados: sin tareas en background, sin joins, sin
> archivos persistentes, sin requisito multi-cliente.
>
> **Funcional:** este sistema va a tener uso irregular —mucho en algunos momentos
> y casi nada en otros—. Elegimos una arquitectura que se adapta sola a esa
> demanda: cuando nadie lo usa, casi no cuesta; cuando hay picos, absorbe el
> tráfico sin intervención. La contrapartida es que no sirve para procesos que
> tarden mucho en completarse, y este sistema no los necesita.

**El registro funcional siempre dice la contrapartida.** Una elección presentada
sin su costo no es una explicación, es una venta.

---

## Lo que no se decide acá

**Librerías dentro de cada patrón.** Es implementación y se decide por proyecto,
declarándolo en su `DECISIONES.md`.

**Proveedor de modelos.** Anthropic, según la Constitución.

**Un tercer patrón.** Agregar uno requiere ADR y, sobre todo, extender el Ruleset
mecánico: un patrón sin reglas verificables es un patrón sin QA.

## Decisiones tomadas

1. El stack interno de la fábrica y los patrones de construcción son cosas
   distintas.
2. Dos patrones disponibles, no uno.
3. Patrón A es el default; B se elige por disparadores.
4. Los bloqueadores ganan a los disparadores.
5. La elección la resuelve una tabla de decisión, no el criterio de un agente.
6. Ante información insuficiente se escala, no se elige por defecto.
7. La elección se somete en el Gate de entrada.
8. Se comunica en dos registros, y el funcional siempre declara la contrapartida.
9. Patrón B queda declarado y no habilitado hasta tener su paquete normativo
   completo.
10. Los patrones tienen paquetes normativos propios, **no agentes propios**.

## Decisiones abiertas

1. **Cuándo se habilita Patrón B.** Sin versión asignada. Requiere sus tres
   piezas normativas y no bloquea V1.
2. **Si el Deployment Agent se parte por patrón.** Se decide con la lista de
   comandos escrita.
3. **Umbrales concretos de los disparadores.** "Tráfico esporádico" no es
   binario. Se calibra con proyectos reales.

## Impacto en otros documentos

**Constitución Técnica** — es la norma de Patrón A; hay que declarar
explícitamente qué secciones no aplican a B. **Ruleset mecánico** — hoy solo
cubre A. **Infrastructure** — desarrolla qué necesita cada patrón para correr.
**Scope** — la tabla de decisión usa el mismo mecanismo de dos registros.
**ADR-008** — este documento se desbloqueó con su aprobación.
