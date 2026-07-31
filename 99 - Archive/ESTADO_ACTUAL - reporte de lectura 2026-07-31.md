# ESTADO ACTUAL

> Reporte de lectura del vault `Software Factory`.
> Alcance: los 10 archivos `.md` existentes al 2026-07-31. No contiene propuestas,
> ni arquitectura, ni decisiones. Sólo lo que está escrito y lo que falta.
> Todas las citas son `archivo:línea`.

---

## 1. INVENTARIO

Total: **10 archivos `.md`**, en 3 carpetas. No hay código, ni diagramas externos,
ni archivos que no sean Markdown (aparte de la configuración de `.obsidian/`, que no
es documentación).

| # | Archivo | Líneas | Bytes | Última modificación | Estado real |
|---|---------|--------|-------|---------------------|-------------|
| 1 | `00 - Home/Home.md.md` | 23 | 198 | 2026-07-30 19:17 | **Esqueleto vacío.** 10 encabezados `##`, 9 de ellos sin ningún contenido (líneas 7-23). Único contenido: un wikilink (línea 5). |
| 2 | `01 - Master Plan/Project Master Plan.md.md` | 32 | 565 | 2026-07-30 19:41 | **Índice + carátula.** Estado autodeclarado: "Versión 0.1 / En construcción" (líneas 7-8). Campo `Última actualización:` vacío (línea 10). 18 entradas de índice, 11 apuntan a documentos inexistentes. |
| 3 | `01 - Master Plan/Vision.md` | 49 | 1718 | 2026-07-30 19:30 | **Redactado, continuo, sin estado declarado.** Prosa completa, sin secciones vacías, sin TODOs. No declara versión, owner ni fecha. |
| 4 | `01 - Master Plan/Objectives.md` | 37 | 1390 | 2026-07-30 19:31 | **Redactado, formato lista, sin estado declarado.** 4 bloques de bullets sin desarrollo, sin criterios de medición. |
| 5 | `01 - Master Plan/Scope.md` | 39 | 945 | 2026-07-30 19:32 | **Redactado, formato lista, sin estado declarado.** Introduce 2 componentes (`Backend Agent`, `Context Engine`, líneas 36-37) que no aparecen en ningún otro documento. |
| 6 | `01 - Master Plan/Principles.md` | 48 | 1214 | 2026-07-30 19:33 | **Redactado, formato lista, sin estado declarado.** 34 principios enunciados como bullets de una línea, ninguno desarrollado. |
| 7 | `01 - Master Plan/Roadmap.md` | 205 | 3755 | 2026-07-30 19:43 | **Redactado, sin estado declarado.** 6 fases. Estructura interna inconsistente entre fases (ver §5). Sin fechas, sin responsables, sin estimaciones. |
| 8 | `01 - Master Plan/Architecture.md` | 363 | 5558 | 2026-07-30 19:45 | **Borrador autodeclarado.** Estado explícito: "Versión 0.1 / Diseño conceptual" (líneas 348-354). Es el documento más extenso y el único con diagramas (ASCII, líneas 70-103 y 241-278). Cierra apuntando a 4 documentos que no existen (líneas 356-364). |
| 9 | `01 - Master Plan/Decision Making.md` | 111 | 1947 | 2026-07-30 19:42 | **Redactado, sin estado declarado.** Define el marco de decisión y el contenido de un Decision Record (líneas 90-101), pero no define plantilla, numeración, ubicación ni quién aprueba. |
| 10 | `11 - ADR/ADR-000 - Project Foundation.md.md` | 0 | 0 | 2026-07-30 19:12 | **Archivo vacío (0 bytes).** Sin título, sin encabezado, sin una sola línea. |

### Observaciones de inventario

- **No existe ningún documento "cerrado".** Ningún archivo declara estado `final`,
  `aprobado` o `cerrado`. Los dos que declaran estado dicen "En construcción"
  (`Project Master Plan.md.md:8`) y "Diseño conceptual" (`Architecture.md:354`).
  Para los 7 restantes, clasificarlos como "cerrado" o "borrador" sería una
  interpretación mía: **están sin estado declarado — ambiguo.** Lo único
  verificable es que su prosa no tiene huecos internos ni marcas de pendiente.
- **Todos los archivos fueron creados/modificados el mismo día**, 2026-07-30, en una
  ventana de 33 minutos (19:12 → 19:45). No hay historial: el directorio **no es un
  repositorio git**, por lo que no existe trazabilidad de cambios más allá del
  `mtime` del sistema de archivos. Esto choca con `Principles.md:13` ("Toda decisión
  debe ser trazable") y `Objectives.md:27` ("Garantizar trazabilidad y versionado").
- **Ningún archivo tiene frontmatter YAML.** No hay metadatos de versión, owner,
  estado ni fecha en 8 de los 10 archivos; los otros 2 los tienen como texto libre.
- **3 archivos tienen doble extensión `.md.md`**: `Home.md.md`,
  `Project Master Plan.md.md`, `ADR-000 - Project Foundation.md.md`. Consecuencia
  verificable: en Obsidian su nombre base pasa a ser `Home.md`, `Project Master Plan.md`,
  etc., por lo que el wikilink `[[Project Master Plan]]` (`Home.md.md:5`) y la entrada
  del índice no resuelven al archivo real. Los otros 7 archivos (`.md` simple) sí
  resuelven.
- **Numeración de carpetas con huecos:** existen `00 - Home`, `01 - Master Plan`,
  `11 - ADR`. Las carpetas `02` a `10` no existen. El esquema implica una taxonomía
  de ~12 secciones que no está documentada en ningún archivo — ambiguo si es
  intencional (reserva de espacio) o accidental.

---

## 2. DECISIONES EXPLÍCITAS

Afirmaciones enunciadas como decisión ya tomada, no como opción.

**Nota transversal que aplica a todas:** ninguna de estas decisiones tiene un ADR.
La carpeta `11 - ADR/` contiene un único archivo de 0 bytes. Es decir, según el
criterio del propio proyecto —`Decision Making.md:35`: *"Una decisión no documentada
no forma parte oficialmente del conocimiento del proyecto"*— y su exigencia de
registro (`Decision Making.md:90-101`), **el número de decisiones formalmente
registradas es cero.** Todo lo que sigue está afirmado en prosa, no en un registro.

### Conocimiento y documentación

| # | Decisión | Ubicación |
|---|----------|-----------|
| D1 | Obsidian es la fuente oficial de conocimiento del proyecto. | `Architecture.md:62`, reafirmado en `Architecture.md:187-189` ("Fuente oficial: Obsidian."), `Objectives.md:12`, `Scope.md:6`, `Decision Making.md:33` |
| D2 | Una decisión no documentada no forma parte del conocimiento oficial del proyecto. | `Decision Making.md:35` |
| D3 | La documentación es la fuente oficial del conocimiento; todo cambio importante debe quedar documentado. | `Principles.md:6-7`, `Vision.md:43` |
| D4 | El conocimiento debe estar disponible tanto para humanos como para agentes. | `Architecture.md:60` |

### Alcance

| # | Decisión | Ubicación |
|---|----------|-----------|
| D5 | Human in the Loop es obligatorio. | `Principles.md:11` (enunciado como obligación), `Vision.md:41`, `Scope.md:9` |
| D6 | Quedan **fuera** del alcance: agentes completamente autónomos sin supervisión. | `Scope.md:18` |
| D7 | Quedan **fuera** del alcance: decisiones arquitectónicas automáticas. | `Scope.md:20` |
| D8 | Quedan **fuera** del alcance: dependencias de herramientas propietarias específicas. | `Scope.md:21` |
| D9 | Quedan **fuera** del alcance: desarrollo fuera de los estándares definidos y automatizaciones sin documentación. | `Scope.md:19`, `Scope.md:22` |
| D10 | La primera meta es una plataforma que desarrolle **aplicaciones backend** de forma semiautónoma. | `Scope.md:28` |
| D11 | La V1 contiene exactamente 7 elementos: Knowledge Base, Infraestructura, Backend Agent, Context Engine, Human in the Loop, Documentación automática, Testing automático. | `Scope.md:32-40` |

### Arquitectura

| # | Decisión | Ubicación |
|---|----------|-----------|
| D12 | La plataforma se organiza en capas. El diagrama fija 5 bloques: Human in the Loop Layer → Factory Orchestration Layer → agentes → Knowledge Management Layer → Infrastructure Layer. | `Architecture.md:70-103` |
| D13 | La enumeración textual fija 5 capas: Orchestration, Agent, Knowledge Management, Software Development, Infrastructure. | `Architecture.md:107-236` (encabezados en 109, 130, 166, 193, 216) — **no coincide con D12, ver §4-C1** |
| D14 | El flujo de desarrollo es secuencial y fijo: Requerimiento → Requirement Agent → Architecture Agent → Development Agent → Testing Agent → Documentation Agent → Deployment → Human Validation. | `Architecture.md:241-278` |
| D15 | Los agentes iniciales son 6: Requirement, Architect, Developer, Testing, Documentation, Security. | `Architecture.md:149-162` |
| D16 | La comunicación entre componentes se hace por interfaces, eventos, mensajes estructurados y contratos versionados. No deben existir dependencias ocultas. | `Architecture.md:284-295` |
| D17 | Cada agente debe tener objetivo específico, responsabilidades, límites de actuación, entradas/salidas definidas y herramientas autorizadas. | `Architecture.md:136-146` |
| D18 | La evolución arquitectónica atraviesa 4 niveles: Asistencia → Coordinación → Automatización → Software Factory Autónoma. | `Architecture.md:303-323` |
| D19 | Toda modificación arquitectónica importante debe generar registro de decisión, evaluación de impacto, actualización documental y revisión de dependencias. | `Architecture.md:327-338` |
| D20 | Principios técnicos adoptados: Clean Architecture, SOLID, DRY, KISS, modularidad, bajo acoplamiento, alta cohesión, desarrollo orientado a componentes, testing por defecto. | `Principles.md:20-28` |

### Proceso y gobierno

| # | Decisión | Ubicación |
|---|----------|-----------|
| D21 | El roadmap tiene 6 fases nombradas: 0.1 Foundation, 0.2 Architecture Definition, 0.3 Agent Framework, 0.4 Development Automation, 0.5 Human in the Loop, 1.0 Autonomous Software Factory. | `Roadmap.md:43`, `:69`, `:96`, `:123`, `:149`, `:174` |
| D22 | No se incorporan capacidades avanzadas sin haber consolidado las dependencias previas. | `Roadmap.md:15-19` |
| D23 | El proceso de decisión tiene 6 pasos obligatorios: identificación, alternativas, impacto, selección, documentación, revisión. | `Decision Making.md:79-86` |
| D24 | Un Decision Record debe incluir 6 campos: contexto, problema, alternativas evaluadas, decisión, justificación, consecuencias. | `Decision Making.md:94-101` |
| D25 | Las decisiones se clasifican en 3 tipos: estratégicas, arquitectónicas, operativas. | `Decision Making.md:41-73` |
| D26 | Las decisiones se revisan cuando cambia la arquitectura, aparecen nuevas restricciones, o la decisión deja de ser válida. | `Decision Making.md:105-111` |
| D27 | El owner del Master Plan es el "Arquitecto Principal". | `Project Master Plan.md.md:9` |
| D28 | El Master Plan se compone de 18 documentos, enumerados en un índice canónico. | `Project Master Plan.md.md:16-33` |

---

## 3. DECISIONES IMPLÍCITAS

Cosas afirmadas al pasar que condicionan la arquitectura y nunca se elevaron a
decisión explícita ni a ADR.

| # | Afirmación implícita | Dónde aparece | Qué condiciona |
|---|----------------------|---------------|----------------|
| I1 | **Obsidian no es sólo repositorio humano: es la interfaz de lectura de los agentes en tiempo de ejecución.** | `Architecture.md:60` ("disponible para humanos y agentes") + `Principles.md:37` ("Los agentes consultan la base de conocimiento antes de actuar") + `Architecture.md:187-189` | Obliga a que un vault de Markdown sea consumible programáticamente. No se menciona ningún mecanismo (índice, embeddings, API, parser, formato). |
| I2 | **Existe un componente llamado `Context Engine`.** Aparece una sola vez, sin definición, como entregable de V1. | `Scope.md:37` — única aparición en todo el vault | Es un componente de primer nivel que no figura en ninguna capa de `Architecture.md:107-236` ni en ninguna fase de `Roadmap.md`. Su relación con "Memoria y contexto" (`Roadmap.md:108`) y con la Knowledge Management Layer no está declarada. |
| I3 | **El agente de desarrollo de V1 es backend-only.** | `Scope.md:36` ("Backend Agent") + `Scope.md:28` ("aplicaciones backend") | La lista canónica de agentes (`Architecture.md:155`) dice "Developer Agent", sin especialización por stack. Que la especialización sea por capa técnica (backend/frontend) y no sólo por rol (developer/tester) es una decisión estructural nunca enunciada. |
| I4 | **El pipeline es lineal, sin iteración, sin rechazo y sin retorno.** | `Architecture.md:241-278` | El diagrama no tiene bifurcaciones ni loops. Si el Testing Agent falla, el flujo no define retorno al Development Agent. Condiciona todo el diseño del orquestador y contradice la naturaleza iterativa asumida en `Vision.md:20-27`. |
| I5 | **La validación humana ocurre al final, después del deployment.** | `Architecture.md:272-277` (Deployment → Human Validation) | Implica desplegar antes de aprobar. Nunca se enuncia como decisión y contradice la capa HITL previa a la orquestación (`Architecture.md:76`). Ver §4-C2. |
| I6 | **V1 opera un solo proyecto a la vez.** | Deducible de `Objectives.md:38` ("Escalar la plataforma para múltiples proyectos simultáneos" listado como objetivo *a largo plazo*) | Ni `Architecture.md` ni `Scope.md` mencionan multi-tenancy, aislamiento de contexto entre proyectos, o namespacing del conocimiento. La carpeta `Projects` existe como sección vacía en `Home.md.md:21`. |
| I7 | **Los agentes se organizan por rol funcional, no por proyecto ni por producto.** | `Architecture.md:130-162` | Determina el modelo de asignación y el ciclo de vida de los agentes. Nunca se compara con la alternativa (equipos de agentes por proyecto). |
| I8 | **Existe versionado, pero no se nombra ningún mecanismo.** | `Scope.md:11`, `Objectives.md:27`, `Principles.md:46`, `Architecture.md:292` ("contratos versionados") | Cuatro documentos exigen versionado y trazabilidad; ninguno dice con qué. El vault, de hecho, **no está bajo control de versiones**. Ambiguo si se asume git, el historial de Obsidian, u otra cosa. |
| I9 | **Hay una taxonomía de ~12 áreas de conocimiento numeradas.** | Estructura de carpetas: `00 - Home`, `01 - Master Plan`, `11 - ADR` | El salto de `01` a `11` reserva 9 posiciones intermedias. Esa taxonomía condiciona dónde vive cada documento futuro y no está escrita en ningún archivo. |
| I10 | **Convención bilingüe: nombres de archivo, capas y agentes en inglés; contenido en español.** | Todo el vault: `Architecture.md`, `Roadmap.md`, "Knowledge Management Layer", "Requirement Agent" vs. prosa en español | Es una convención de nomenclatura consistente pero no declarada. No hay documento de estándares que la fije, y ya produce dobletes ("Knowledge Base" / "base de conocimiento"). |
| I11 | **Deben existir "Estándares iniciales" como entregable de la fase actual.** | `Roadmap.md:61` | Presupone un documento de Standards (`Home.md.md:11` tiene la sección) que no existe. Es un entregable comprometido de la fase 0.1 sin artefacto. |
| I12 | **Los agentes producen su propia documentación.** | `Principles.md:38`, `Vision.md:25`, `Architecture.md:209` | Implica que la fuente de verdad (Obsidian, D1) es escrita por agentes, no sólo leída. No hay ninguna mención a control de escritura, revisión, o conflicto entre lo escrito por humanos y por agentes. |
| I13 | **La Software Factory se construirá a sí misma con sus propios agentes.** | `Objectives.md:37` ("Permitir que la Software Factory evolucione utilizando sus propios agentes") + `Roadmap.md:197-205` | Es una decisión de bootstrapping con consecuencias fuertes (orden de construcción, riesgo de dependencia circular) enunciada como un bullet de objetivo a largo plazo. |
| I14 | **Existe un rol único de decisión, el "Arquitecto Principal".** | `Project Master Plan.md.md:9` | Es el único rol humano nombrado en todo el vault. `Decision Making.md` define el *proceso* de decisión pero nunca dice **quién aprueba**. La existencia de un aprobador único queda implícita en el campo Owner. |

---

## 4. CONTRADICCIONES

### C1 — El diagrama de capas y la lista de capas no son la misma arquitectura

Ambas afirmaciones están **en el mismo documento**.

> **`Architecture.md:70-103`** (diagrama):
> `Human Operator → Human in the Loop Layer → Factory Orchestration Layer →
> [Requirement Agent | Architecture Agent | Development Agent] →
> Knowledge Management Layer → Infrastructure Layer`

> **`Architecture.md:107-236`** (enumeración): `## 1. Orchestration Layer` (109),
> `## 2. Agent Layer` (130), `## 3. Knowledge Management Layer` (166),
> `## 4. Software Development Layer` (193), `## 5. Infrastructure Layer` (216)

Diferencias verificables:
- La **Human in the Loop Layer** aparece en el diagrama (`:76`) y **no existe** en la
  enumeración.
- La **Software Development Layer** aparece en la enumeración (`:193`) y **no existe**
  en el diagrama.
- El diagrama la llama **"Factory Orchestration Layer"** (`:81`); la enumeración,
  **"Orchestration Layer"** (`:109`).
- El diagrama pone Knowledge Management **debajo** de los agentes, como capa
  inferior de flujo; la enumeración la describe como repositorio transversal
  (`:166-189`), sin posición.

### C2 — El humano está antes de todo, y también al final de todo

> **`Architecture.md:76`**: la `Human in the Loop Layer` está inmediatamente debajo
> del `Human Operator` y **por encima** de la orquestación: nada se ejecuta sin
> pasar por ella.

> **`Architecture.md:277`**: en el flujo de desarrollo, `Human Validation` es el
> **último** paso, **después** de `Deployment` (`:272`).

Las dos ubicaciones describen modelos incompatibles de control: portón de entrada
vs. validación posterior al despliegue. Ningún documento reconcilia ambas.

### C3 — HITL es obligatorio desde el inicio, pero se implementa en la fase 0.5

> **`Principles.md:11`**: "Human in the Loop es obligatorio."
> **`Scope.md:9`**: HITL listado dentro de "Incluye".
> **`Architecture.md:76`**: HITL como capa superior de la arquitectura.

> **`Roadmap.md:149-153`**: `# Version 0.5 - Human in the Loop` — "Objetivo:
> Implementar supervisión humana dentro del ciclo de desarrollo."
> **`Roadmap.md:164`**: "Flujos de aprobación" es entregable **de la 0.5**.
> **`Roadmap.md:168-170`**: su dependencia es "Desarrollo automatizado funcional".

Es decir: la fase 0.4 (`Roadmap.md:123-135`) entrega generación de código, testing y
documentación automática **antes** de que existan los flujos de aprobación. Durante
esa fase el principio "obligatorio" de `Principles.md:11` no se puede cumplir.
`Scope.md:22` ("No incluye: automatizaciones sin documentación") y `Scope.md:18`
quedan igualmente en tensión con ese orden.

### C4 — "Sin herramientas propietarias" vs. "Obsidian es la fuente oficial"

> **`Scope.md:21`** — bajo "No Incluye": "Dependencias de herramientas propietarias
> específicas."

> **`Architecture.md:62`**: "La fuente oficial de conocimiento del proyecto es
> Obsidian." Reafirmado en `Architecture.md:187-189`, `Objectives.md:12`
> ("Centralizar todo el conocimiento en Obsidian"), `Scope.md:6` (en el mismo
> documento, 15 líneas antes de la exclusión) y `Decision Making.md:33`.

Obsidian es una herramienta específica y propietaria, y es dependencia declarada en
5 lugares. Ningún documento aclara si la exclusión se refiere sólo a la plataforma
producida y no a la de trabajo — **ambiguo**, pero tal como está escrito, se pisan.

### C5 — La fase 0.1 no está cerrada, pero ya hay entregables de la 0.2

> **`Roadmap.md:63-65`**: criterio de avance de la fase 0.1: "La base conceptual debe
> estar documentada y validada."
> **`Roadmap.md:69-88`**: la fase **0.2** es la que entrega "Arquitectura general",
> "Diagramas" y "Decisiones arquitectónicas"; su dependencia declarada es
> "Foundation completa" (`Roadmap.md:90-92`).

> **`Project Master Plan.md.md:7-8`**: "Versión: 0.1 / Estado: En construcción" — la
> 0.1 no está cerrada.
> **`Architecture.md:348-354`**: sin embargo `Architecture.md` ya existe, con
> arquitectura general y diagramas, y se autodeclara "Versión: 0.1".

O el entregable de 0.2 se produjo antes de cerrar 0.1, o la etiqueta "0.1" de
`Architecture.md:350` no se refiere a la fase del roadmap sino a la versión del
documento. **Ambiguo** cuál de las dos, y esa ambigüedad es en sí misma un problema
de vocabulario (ver §6-V7). En ambas lecturas, el estado real del roadmap no coincide
con los artefactos existentes.

### C6 — "Sin decisiones arquitectónicas automáticas" vs. un Architecture Agent en el pipeline

> **`Scope.md:20`** — bajo "No Incluye": "Decisiones arquitectónicas automáticas."

> **`Architecture.md:252`**: el `Architecture Agent` ocupa un paso propio del flujo,
> entre `Requirement Agent` y `Development Agent`, sin punto de validación humana
> intermedio (`Architecture.md:241-278`).
> **`Architecture.md:153`**: "Architect Agent" figura entre los agentes iniciales.

Si el Architect Agent diseña sin aprobación intermedia, produce decisiones
arquitectónicas automáticas. **Marco esto como ambiguo, no como contradicción
cerrada**: ningún documento define si "diseñar" y "decidir" son lo mismo, ni
`Principles.md:35` ("Los agentes no toman decisiones fuera de su alcance") aclara
cuál es el alcance del Architect Agent.

### C7 — El mismo agente tiene dos nombres en el mismo documento

> **`Architecture.md:88`**: "Requirement Agent   Architecture Agent   Development Agent"
> **`Architecture.md:151-155`**: "Requirement Agent", "**Architect** Agent",
> "**Developer** Agent"
> **`Architecture.md:252`, `:257`**: "Architecture Agent", "Development Agent"

Dos nomenclaturas coexisten en un mismo archivo. Ver también §6-V1 y §6-V2.

### C8 — Cuatro listas de principios distintas, ninguna declarada canónica

Existen 4 conjuntos de principios en 4 documentos, con solapamiento parcial y
formulaciones que no coinciden:

- `Vision.md:39-50` — "Principios Fundamentales" (10 ítems)
- `Principles.md:3-49` — "Principios Generales / Desarrollo / Agentes / Calidad" (34 ítems)
- `Architecture.md:13-63` — "Principios Arquitectónicos" (5 ítems desarrollados)
- `Roadmap.md:13-37` — "Principios del Roadmap" (4 ítems)
- `Decision Making.md:11-35` — "Principios de decisión" (3 ítems)

El mismo principio aparece con 4 enunciados distintos:
> `Vision.md:44`: "Arquitectura antes que implementación."
> `Principles.md:5`: "La arquitectura tiene prioridad sobre la implementación."
> `Decision Making.md:13`: "Arquitectura antes que **velocidad**."
> `Roadmap.md:23`: "Arquitectura primero."

Y compite con `Roadmap.md:35`: "Calidad antes que velocidad." Ningún documento
establece cuál lista prevalece si dos se contradicen.

### C9 — El índice del Master Plan y el índice de Home no coinciden

> **`Project Master Plan.md.md:16-33`**: 18 documentos.
> **`Home.md.md:4-23`**: 10 secciones — Master Plan, Roadmap, Architecture,
> Standards, Technology Stack, Agent Framework, Infrastructure, Knowledge, Projects, ADR.

`Home.md.md` incluye **Standards**, **Projects** y **ADR**, que no están en el índice
del Master Plan. El Master Plan incluye Vision, Objectives, Scope, Principles,
Development Methodology, Human in the Loop, Security, Quality, KPIs, Risks, Future
Versions y Decision Making, que no están en Home. Ningún documento declara cuál de
los dos es la estructura oficial.

---

## 5. HUECOS

### 5.1 Documentos referenciados que no existen

**Desde `Project Master Plan.md.md:16-33`** (índice, 11 de 18 entradas rotas):

| Línea | Wikilink | Existe |
|-------|----------|--------|
| 22 | `[[Technology Stack]]` | ❌ |
| 23 | `[[Agent Framework]]` | ❌ |
| 24 | `[[Knowledge Management]]` | ❌ |
| 25 | `[[Infrastructure]]` | ❌ |
| 26 | `[[Development Methodology]]` | ❌ |
| 27 | `[[Human in the Loop]]` | ❌ |
| 28 | `[[Security]]` | ❌ |
| 29 | `[[Quality]]` | ❌ |
| 30 | `[[KPIs]]` | ❌ |
| 31 | `[[Risks]]` | ❌ |
| 32 | `[[Future Versions]]` | ❌ |

(Las 7 restantes — Vision, Objectives, Scope, Principles, Roadmap, Architecture,
Decision Making — sí existen.)

**Desde `Architecture.md:356-364`** ("Próximos documentos relacionados"): repite
`[[Technology Stack]]`, `[[Agent Framework]]`, `[[Knowledge Management]]`,
`[[Infrastructure]]` — los 4 inexistentes.

**Desde `Home.md.md:5`**: `[[Project Master Plan]]` — el archivo en disco se llama
`Project Master Plan.md.md`, cuyo nombre base para Obsidian es `Project Master
Plan.md`. El enlace, tal como está escrito, no resuelve.

**Enlace que sí resuelve**: `Architecture.md:342` → `[[Decision Making]]`. Es el
único wikilink funcional entre documentos de contenido en todo el vault.

### 5.2 Secciones vacías

- `Home.md.md:7-23` — 9 encabezados sin una sola línea de contenido: Roadmap (7),
  Architecture (9), Standards (11), Technology Stack (13), Agent Framework (15),
  Infrastructure (17), Knowledge (19), Projects (21), ADR (23).
- `Project Master Plan.md.md:10` — "Última actualización:" sin valor.
- `11 - ADR/ADR-000 - Project Foundation.md.md` — archivo de **0 bytes**. El ADR
  fundacional, que por su nombre debería registrar la decisión base del proyecto,
  está completamente vacío.

### 5.3 Promesas de "se definirá más adelante"

| Ubicación | Texto | Qué queda pendiente |
|-----------|-------|---------------------|
| `Architecture.md:356` | "Próximos documentos relacionados:" | Stack, Agent Framework, Knowledge Management, Infrastructure |
| `Architecture.md:346-354` | "Estado Actual / Versión 0.1 / Diseño conceptual" | Todo el documento se declara no-final |
| `Project Master Plan.md.md:8` | "Estado: En construcción" | Todo el Master Plan |
| `Roadmap.md:197-205` | "Evolución futura. Las siguientes versiones **podrán** incorporar:" | Mayor autonomía, nuevos agentes, optimización por métricas, autoevaluación, mejora continua — 5 ítems sin fase asignada |
| `Roadmap.md:61` | "Estándares iniciales" como entregable | No existe documento de estándares |
| `Decision Making.md:92` | "Las decisiones importantes deben registrarse mediante **documentos específicos**" | No se define plantilla, numeración, ubicación ni formato de esos documentos |

### 5.4 Definiciones ausentes que el propio texto exige

- **Quién aprueba.** `Decision Making.md:79-86` define 6 pasos de decisión pero
  ningún paso asigna responsable. `Principles.md:39` dice que los agentes "solicitan
  aprobación cuando corresponde" sin definir cuándo corresponde ni a quién.
  `Architecture.md:125` asigna "gestionar aprobaciones humanas" a la Orchestration
  Layer sin describir el mecanismo.
- **Plantilla de ADR.** `Decision Making.md:94-101` lista los 6 campos, pero no
  existe archivo de plantilla ni convención de numeración. El único ADR del vault
  está vacío.
- **Criterios de avance por fase.** `Roadmap.md:63-65` define "Criterio de avance"
  sólo para la fase 0.1. Las fases 0.2, 0.3, 0.4, 0.5 y 1.0 tienen "Dependencias"
  (`:90`, `:116`, `:143`, `:168`) pero **ninguna tiene criterio de avance**. La 1.0
  no tiene ni dependencias ni criterio; tiene "Resultado esperado" (`:191`).
- **Fechas, responsables y esfuerzo.** El roadmap completo (205 líneas) no contiene
  ninguna fecha, ningún nombre y ninguna estimación.
- **Métricas.** `Objectives.md:35` ("Reducir significativamente los tiempos") y
  `Vision.md:12` ("reduciendo significativamente los tiempos") usan "significativamente"
  sin valor. `Roadmap.md:166` compromete "Métricas de supervisión" y el índice
  compromete `[[KPIs]]` (`Project Master Plan.md.md:30`); ninguna métrica está
  definida en ningún documento.
- **Definición de "calidad profesional".** `Vision.md:10`, `Objectives.md:5` y
  `Roadmap.md:37` ("criterios mínimos de calidad") la invocan; `[[Quality]]`
  (`Project Master Plan.md.md:29`) no existe.
- **Riesgos.** `Decision Making.md:24` exige considerar riesgos en toda decisión;
  `[[Risks]]` (`Project Master Plan.md.md:31`) no existe.
- **Seguridad.** Hay un `Security Agent` (`Architecture.md:161`) y "Seguridad" como
  servicio de infraestructura (`Architecture.md:228`); `[[Security]]`
  (`Project Master Plan.md.md:28`) no existe.
- **Testing.** "Testing por defecto" (`Principles.md:28`), `Testing Agent`
  (`Architecture.md:157`), "Testing automático" en V1 (`Scope.md:40`): ningún
  documento define estrategia, cobertura ni herramientas.
- **Tecnología.** Ningún documento nombra un lenguaje, un framework, un modelo de
  IA, un proveedor ni un runtime. `[[Technology Stack]]` no existe.

### 5.5 Huecos estructurales del vault

- Carpetas `02` a `10` inexistentes (ver §1).
- El vault no está bajo control de versiones (no es repositorio git), pese a
  `Objectives.md:27`, `Scope.md:11` y `Principles.md:46`.
- No existe glosario, pese a la cantidad de términos con múltiples significados (§6).
- No existe README ni documento de convenciones de nomenclatura del propio vault.

---

## 6. VOCABULARIO

### 6.1 Conceptos con más de un nombre

| # | Concepto | Nombres usados | Ubicaciones |
|---|----------|----------------|-------------|
| V1 | Agente que diseña | **Architecture Agent** / **Architect Agent** | `Architecture.md:88`, `:252` vs. `Architecture.md:153` |
| V2 | Agente que programa | **Development Agent** / **Developer Agent** / **Backend Agent** | `Architecture.md:88`, `:257` vs. `Architecture.md:155` vs. `Scope.md:36` |
| V3 | El repositorio de conocimiento | **Knowledge Management Layer** / **Knowledge Base** / **Knowledge** / **base de conocimiento** / **Obsidian** / **Knowledge Management** (documento) | `Architecture.md:166` / `Scope.md:34` / `Home.md.md:19` / `Principles.md:37` / `Architecture.md:62` / `Project Master Plan.md.md:24` — **6 nombres para lo que parece un solo concepto**, aunque no está declarado que lo sean (ambiguo si `Knowledge Base` ⊂ `Knowledge Management Layer` o si son lo mismo) |
| V4 | La capa que coordina | **Factory Orchestration Layer** / **Orchestration Layer** / **sistema de orquestación** | `Architecture.md:81` / `Architecture.md:109` / `Architecture.md:311` |
| V5 | El principio de prioridad arquitectónica | **"Arquitectura antes que implementación"** / **"La arquitectura tiene prioridad sobre la implementación"** / **"Arquitectura antes que velocidad"** / **"Arquitectura primero"** | `Vision.md:44` / `Principles.md:5` / `Decision Making.md:13` / `Roadmap.md:23` (ver §4-C8) |
| V6 | El registro de una decisión | **Decision Record** / **Registro de decisión** / **ADR** / **Registro de decisiones** | `Decision Making.md:90` / `Architecture.md:331` / nombre de carpeta `11 - ADR` / `Roadmap.md:165` — la sigla ADR sólo aparece en el nombre de carpeta y archivo; **ningún documento la define ni la vincula a `Decision Making.md:90-101`** |

### 6.2 Términos usados con más de un significado

| # | Término | Significado A | Significado B | Significado C+ |
|---|---------|---------------|---------------|----------------|
| V7 | **Versión / 0.1** | Versión del **documento**: `Architecture.md:348-350`, `Project Master Plan.md.md:7` | Fase del **roadmap**: `Roadmap.md:43` "Version 0.1 - Foundation" | Ambos valen "0.1" simultáneamente, lo que hace imposible saber a cuál se refiere `Architecture.md:350` (ver §4-C5). **Ambiguo.** |
| V8 | **Human in the Loop** | Principio obligatorio: `Principles.md:11`, `Vision.md:41` | Capa arquitectónica: `Architecture.md:76` | Fase del roadmap: `Roadmap.md:149`; documento del índice: `Project Master Plan.md.md:27`; paso final del flujo ("Human Validation"): `Architecture.md:277`; ítem de alcance: `Scope.md:9`, `Scope.md:38`. **6 referentes distintos para el mismo término.** |
| V9 | **Autónomo / Autonomía** | En el nombre del proyecto y de la meta: "Software Factory **Autónoma**" (`Vision.md:4`, `Roadmap.md:174`, `Architecture.md:5`) | Excluido explícitamente del alcance: "agentes completamente **autónomos** sin supervisión" (`Scope.md:18`) | Gradual: "La **autonomía** de los agentes debe aumentar progresivamente" (`Roadmap.md:31`). El término nombra a la vez la meta y lo prohibido. |
| V10 | **Software Factory** | La **plataforma** que se construye: `Vision.md:10`, `Objectives.md:5` | El **agente/sistema** que ejecuta: `Vision.md:18` ("la Software Factory sea capaz de: analizar, diseñar…") | Una **entidad operable**: `Roadmap.md:178` ("Operar una Software Factory"), y un **producto replicable** implícito en `Objectives.md:38`. **Ambiguo** si es un producto, una instancia o un modelo operativo. |
| V11 | **Documentación** | Fuente de verdad / insumo: `Principles.md:6`, `Decision Making.md:33` | Artefacto producido por los agentes: `Vision.md:25`, `Architecture.md:209`, `Scope.md:39` | Agente: "Documentation Agent" `Architecture.md:159`; fase del flujo: `Architecture.md:267`. La misma palabra designa el input autoritativo y el output generado (ver §3-I12). |
| V12 | **Nivel** vs. **Fase/Versión** | Niveles 1-4 de evolución arquitectónica: `Architecture.md:303-323` | Versiones 0.1-1.0 del roadmap: `Roadmap.md:43-193` | Dos escalas de madurez paralelas, con nombres parecidos ("Nivel 4 - Software Factory Autónoma" `:321` vs. "Version 1.0 - Autonomous Software Factory" `:174`) y **sin ninguna correspondencia declarada** entre ellas. |
| V13 | **Contexto / Memoria** | Capacidad del Agent Framework: "Memoria y contexto" `Roadmap.md:108` | Componente de V1: "Context Engine" `Scope.md:37` | Relación no declarada entre ambos, ni con la Knowledge Management Layer. **Ambiguo.** |
| V14 | **Trazabilidad / Auditoría / Observabilidad** | Trazabilidad: `Objectives.md:27`, `Scope.md:11`, `Principles.md:13` | Auditoría: `Objectives.md:28`, `Principles.md:45`, `Roadmap.md:159` | Observabilidad: `Objectives.md:28`, `Architecture.md:230`. Tres términos con campos semánticos superpuestos, ninguno definido, sin frontera entre ellos. |
| V15 | **Principio** | Principio fundamental del proyecto: `Vision.md:39` | Principio de desarrollo/código: `Principles.md:18-28` | Principio de agentes (`Principles.md:32`), de calidad (`:43`), arquitectónico (`Architecture.md:13`), del roadmap (`Roadmap.md:13`), de decisión (`Decision Making.md:11`). **7 alcances distintos de la misma palabra**, sin jerarquía declarada. |
| V16 | **Estándar** | Entregable de la fase 0.1: `Roadmap.md:61` | Sección del vault: `Home.md.md:11` | Criterio de exclusión: `Scope.md:19` ("Desarrollo fuera de los estándares definidos"). Se lo invoca como norma vinculante en `Scope.md:19` sin que exista el documento que lo define. |
| V17 | **Capa (Layer)** | Bloque del diagrama de flujo vertical: `Architecture.md:70-103` | Agrupación lógica de responsabilidades: `Architecture.md:107-236` | Las dos listas no coinciden (§4-C1), por lo que "capa" designa dos particiones distintas del sistema. **Ambiguo.** |
| V18 | **Agente** | Rol / especificación: `Architecture.md:130-146`, `Principles.md:34` | Ejecutor en tiempo de ejecución: `Architecture.md:317`, `Roadmap.md:31` | Nunca se distingue entre la definición de un agente y su instancia. Condiciona la orquestación. **Ambiguo, no resuelto en ningún documento.** |

---

## Resumen cuantitativo

| Métrica | Valor |
|---------|-------|
| Documentos existentes | 10 |
| Documentos vacíos (0 bytes) | 1 (`ADR-000`) |
| Documentos que son sólo esqueleto/índice | 2 (`Home.md.md`, `Project Master Plan.md.md`) |
| Documentos con contenido redactado | 7 |
| Documentos que declaran su estado | 2 de 10 |
| Documentos declarados "cerrado" o "final" | **0** |
| Documentos referenciados que no existen | 11 (+1 enlace roto por doble extensión) |
| ADRs escritos | **0** |
| Decisiones explícitas identificadas | 28 |
| Decisiones implícitas identificadas | 14 |
| Contradicciones identificadas | 9 (1 marcada como ambigua: C6) |
| Términos con múltiples significados o nombres | 18 |
| Wikilinks funcionales entre documentos de contenido | 1 (`Architecture.md:342`) |
| Fechas, responsables o estimaciones en el roadmap | 0 |
| Tecnologías nombradas en todo el vault | 1 (Obsidian) |

---

*Reporte generado el 2026-07-31 por lectura directa de los 10 archivos. No contiene
propuestas ni interpretaciones fuera de lo marcado explícitamente como ambiguo.*
