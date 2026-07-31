---
estado: propuesto
version: 1.0
owner: CEO
actualizado: 2026-07-31
adr: [ADR-000]
aliases: [ADR-001]
---

# ADR-001 — Glosario canónico

## Contexto

El reporte de lectura del vault anterior identificó dieciocho términos usados con más
de un significado o con más de un nombre. Entre ellos, "Human in the Loop" con seis
referentes distintos, "Agente" sin distinción entre especificación e instancia de
ejecución, y "0.1" designando a la vez la versión de un documento y una fase del
roadmap.

Varias de las contradicciones detectadas no eran desacuerdos de diseño sino colisiones
de vocabulario: el mismo concepto nombrado de dos maneras y tratado como si fueran dos.

## Problema

¿Qué significa exactamente cada término del proyecto, y cuál es su único nombre válido?

## Alternativas evaluadas

**Glosario descriptivo.** Registrar los usos existentes sin elegir. Conserva la
ambigüedad y no resuelve nada.

**Glosario canónico vinculante.** Un término, un significado, un nombre. Todo uso
distinto es un error corregible. Cuesta cerrar discusiones ahora, evita rediscutirlas
después.

## Decisión

Se adopta el siguiente glosario como vinculante. Todo documento, ADR, prompt de agente,
nombre de componente y nombre de archivo usa exclusivamente estos términos.

### Entidades del sistema

**Software Factory** — la plataforma. Singular, siempre. No designa un agente, ni un
proyecto, ni un producto replicable.

**Agent Definition** — la especificación de un agente: qué hace, qué recibe, qué
produce, qué herramientas puede usar, dónde para. Es un artefacto versionado. No se
ejecuta.

**Agent Run** — una ejecución concreta de una Agent Definition, con su entrada, su
contexto, su costo, su resultado y su traza. Es un hecho, no una norma.

Esta distinción es la más importante del glosario. "Agente" a secas queda prohibido
en documentación normativa: obliga a decir cuál de los dos se está nombrando.

**Core Agents** — el conjunto permanente de Agent Definitions de la plataforma.

**Agent Factory** — el mecanismo que crea Agent Definitions nuevas.

**Orchestrator** — el componente que decide qué Agent Run se dispara, en qué orden y
con qué entrada. Nombre único: no "Factory Orchestration Layer", no "sistema de
orquestación".

**Intake** — punto único de ingreso de requerimientos. Es un componente, no un agente:
puede estar implementado por uno.

### Conocimiento

**Vault** — el repositorio de conocimiento en markdown bajo control de versiones. Es el
artefacto físico.

**Knowledge Layer** — la capa de la arquitectura que da acceso al conocimiento. Es
componente de software, no el Vault. Un documento habla de uno o del otro, nunca de
ambos con la misma palabra.

Quedan prohibidos como sinónimos: "Knowledge Base", "base de conocimiento",
"Knowledge Management Layer".

**Context** — el conjunto de información que recibe un Agent Run para operar. Es
efímero y pertenece a una única ejecución.

**Memory** — información que persiste entre Agent Runs. Nunca es fuente de verdad:
se reconstruye desde el Vault y desde el estado operativo.

**Operational State** — hechos del sistema en curso: proyectos, tareas, ejecuciones,
aprobaciones pendientes. Vive fuera del Vault. El Vault es fuente de verdad de las
normas; el Operational State lo es de los hechos.

### Control y autonomía

**HITL** — el principio: existen puntos donde una persona decide y sin esa decisión el
flujo no avanza. Solo designa el principio.

**Gate** — un punto de control concreto: qué se aprueba, quién aprueba, qué pasa si se
rechaza, qué evidencia queda. HITL es el principio, el Gate es su implementación.
"Human Validation" queda prohibido.

**Autonomy Level** — grado de autonomía de una Agent Definition, declarado por agente y
por tipo de acción. No es una propiedad de la plataforma ni una etapa temporal.

"Autónomo" nunca significa "sin intervención humana". Significa "sin intervención
humana dentro del alcance declarado en su Agent Definition".

### Proceso

**Fase** — etapa del roadmap. Se nombran `Fase 0`, `Fase 1`, `Fase 2`. Nunca con
números de versión.

**Versión** — se aplica exclusivamente a documentos, ADRs y contratos. Nunca a fases.

Queda eliminada la escala paralela de "Niveles de evolución arquitectónica": el grado
de autonomía se expresa con Autonomy Level por agente, no con una escala global.

**Acceptance Criteria** — condiciones verificables que definen que un requerimiento
está cumplido. Se producen en Intake y son obligatorias para abrir un proyecto.

**Verification** — comprobación objetiva de un Acceptance Criteria. La ejecuta la capa
de verificación, nunca el Agent Run que produjo el artefacto.

### Documentación

**Platform Documentation** — documentación de la Software Factory. Vive en el Vault de
plataforma. La escriben personas.

**Product Documentation** — documentación del software que la plataforma produce. Vive
en el proyecto. La escriben Agent Runs.

"Documentación" a secas queda prohibido en documentación normativa.

### Gobierno

**ADR** — único nombre para un registro de decisión. Quedan prohibidos "Decision
Record" y "registro de decisión".

**Principio** — enunciado normativo del proyecto. Existe **una sola lista canónica**,
en `01 - Master Plan/Principles.md`. Ningún otro documento enuncia principios propios:
los referencia.

**Standard** — norma vinculante de ejecución. Vive en `06 - Standards`. Un standard sin
documento no es invocable.

**Traceability** — poder reconstruir por qué existe un artefacto y qué decisión lo
originó.

**Auditability** — poder demostrar ante un tercero qué pasó, quién aprobó y cuándo.

**Observability** — poder ver el estado del sistema mientras opera.

Son tres propiedades distintas con mecanismos distintos. No se usan como sinónimos.

### Nombres fijos de los Core Agents

`Intake Agent`, `Requirement Agent`, `Architect Agent`, `Developer Agent`, `QA Agent`,
`Documentation Agent`, `Security Agent`, `Deployment Agent`.

Quedan prohibidas las variantes "Architecture Agent", "Development Agent",
"Testing Agent", "Backend Agent". La especialización técnica —backend, frontend, datos—
es un atributo de la Agent Definition, no un agente distinto.

## Justificación

Cada término con dos significados es una discusión que se va a repetir en cada
documento. Resolverlos ahora cuesta una decisión; resolverlos después cuesta reescribir
todo lo que se haya escrito mientras tanto.

La distinción Agent Definition / Agent Run es la que más rinde: sin ella no se puede
diseñar el contrato de agente, ni Agent Factory, ni el modelo de permisos, ni la
trazabilidad de ejecuciones.

## Consecuencias

**A favor:** los documentos siguientes se escriben sin ambigüedad. Los nombres de
componentes, carpetas y contratos salen del glosario y no se inventan.

**En contra:** obliga a corregir el vocabulario cada vez que se desvía, incluso en
conversación informal. Algunos términos van a resultar rígidos —"Agent Definition" es
más largo que "agente"— y va a haber tentación de volver a la forma corta.

**Efecto secundario:** la eliminación de la escala de "Niveles de evolución" y la
prohibición de listas de principios paralelas cierran dos contradicciones del vault
anterior sin necesidad de ADR adicional.

## Dependencias

**Requiere:** ADR-000.
**Habilita:** todos los documentos y ADRs siguientes.
**Bloquea:** cualquier uso de los términos prohibidos en documentación del proyecto.

## Documentos afectados

Todos. Ningún documento se escribe antes de este.
