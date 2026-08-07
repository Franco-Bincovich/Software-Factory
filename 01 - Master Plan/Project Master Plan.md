---
estado: en-revision
version: 1.0
owner: CEO
adr: [ADR-000, ADR-001, ADR-002, ADR-003, ADR-004, ADR-005]
actualizado: 2026-07-31
---

# Project Master Plan

Índice oficial del vault. Cualquier otro listado de documentos es navegación, no
estructura.

El criterio de cierre de Fase 0 y el alcance de la versión en curso viven en
[[PLAN-V0.1]].

## Estado de la Fase 0

**Fase 0 — Diseño Estratégico.** Cerrada el 2026-08-07.

Los cinco ADRs que consume V0.1 están aprobados: ADR-005, ADR-008,
ADR-009, ADR-010 y ADR-011. Los diecisiete documentos del índice
existen como archivo.

Criterio de cierre según [[PLAN-V0.1]]: capacidad operativa demostrada,
no cantidad de documentos aprobados.

ADRs aprobados: 12 (ADR-000 a ADR-006, ADR-008 a ADR-012).
Fase siguiente: construcción de V0.1, tarea T14 pendiente.

## Índice

### 01 - Master Plan

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Project Master Plan]] | en-revision | [[ADR-002]] |
| [[Vision]] | pendiente | — |
| [[Objectives]] | pendiente | — |
| [[Scope]] | pendiente | ADR pendiente: primer corte funcional |
| [[Principles]] | pendiente | — |
| [[Roadmap]] | pendiente | ADR pendiente: secuencia de fases |
| [[Decision Making]] | pendiente | [[ADR-000]] |

### 02 - Architecture

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Architecture]] | pendiente | ADR pendiente: modelo de capas |
| [[Technology Stack]] | bloqueado | requiere Agent Framework y Architecture |

### 03 - Agent Framework

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Agent Framework]] | pendiente | [[ADR-003]] |
| [[Autonomy and HITL]] | pendiente | [[ADR-004]] |
| [[Verification]] | pendiente | [[ADR-005]] |

### 04 - Knowledge Management

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Knowledge Management]] | pendiente | [[ADR-011]] |

### 05 - Infrastructure

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Infrastructure]] | bloqueado | requiere Technology Stack |
| [[Security]] | pendiente | [[ADR-009]] |

### 06 - Standards

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Standards]] | pendiente | — |
| [[Development Methodology]] | pendiente | ADR pendiente: ciclo de trabajo |

> Los estados de esta tabla describen documentos que aún no existen como
> archivo. Su estado real se declara en su propio frontmatter cuando se
> creen.

### Artefactos vinculantes

| Documento | Tipo | Estado |
|---|---|---|
| [[ADR-000]] | adr | aceptado |
| [[ADR-001]] | adr | aceptado |
| [[ADR-002]] | adr | aceptado |
| [[ADR-003]] | adr | aceptado |
| [[ADR-004]] | adr | aceptado |
| [[ADR-005]] | adr | aceptado |
| [[ADR-006]] | adr | aceptado |
| [[ADR-008]] | adr | aceptado |
| [[ADR-009]] | adr | aceptado |
| [[ADR-010]] | adr | aceptado |
| [[ADR-011]] | adr | aceptado |
| [[ADR-012]] | adr | aceptado |
| [[Contrato del Plan de Trabajo]] | contrato | aceptado |
| [[Requirement Agent]] | agent-definition | aceptado |
| [[PLAN-V0.1]] | plan-de-version | aceptado |
| [[Ruleset mecánico]] | contrato | pendiente de ingreso |

> Los documentos de tipo `guia` no se listan: son navegación, no
> estructura.

## Registro de riesgos

Riesgos vivos del proyecto. Se actualiza al cerrar cada ADR.

| # | Riesgo | Impacto | Estado |
|---|---|---|---|
| R1 | Verificación producida por el mismo tipo de sistema que produce el código: la autonomía se vuelve confianza ciega. | Alto | Mitigado parcialmente — ADR-005. Verificación sustantiva diferida a V0.3. |
| R2 | Costo de ejecución sin techo por agente ni por proyecto. | Alto | Mitigado — ADR-010. |
| R3 | El CEO como único aprobador de todos los Gates lo convierte en cuello de botella por diseño. | Alto | Mitigado parcialmente — ADR-004. Persiste mientras exista un solo rol humano aprobador. |
| R4 | Alcance abierto ("cualquier tipo de sistema") sin primer corte funcional. | Alto | Abierto — mitigación en ADR de primer corte |
| R5 | Bootstrapping: la plataforma construida por sus propios agentes genera dependencia circular. | Medio | Abierto |
| R6 | Agent Factory priorizada antes de operar los Core Agents de punta a punta. | Medio | Abierto |
| R7 | Aislamiento de datos entre proyectos de terceros no definido. | Medio | Abierto |
| R8 | Pérdida del Operational State: sin respaldo automático, perder ese almacén elimina toda la evidencia de la fábrica sin reconstrucción posible desde el Vault. | Alto | Abierto — mitigación en Infrastructure, hoy bloqueado. ADR-011. |

## Secuencia de decisión

Orden en que deben cerrarse los ADRs pendientes. No se altera sin ADR.

1. Contrato de agente — cerrado por ADR-003
2. Modelo de control: autonomía y Gates — cerrado por ADR-004
3. Capa de verificación y Acceptance Criteria — cerrado por ADR-005
4. Planos de conocimiento — cerrado por ADR-011
5. Primer corte funcional de V1 — cerrado por ADR-008
6. Identidad y permisos de agentes — cerrado por ADR-009
7. Modelo de costo y presupuesto — cerrado por ADR-010
8. Modelo de capas de la arquitectura — pendiente, diferido
9. Secuencia de fases del roadmap — pendiente, diferido
10. Taxonomía documental — cerrado por ADR-012

Los puntos 1 a 7 son los que cierran Fase 0 según [[PLAN-V0.1]].
Los puntos 8 y 9 se difieren: no los consume V0.1.

Technology Stack e Infrastructure quedaron desbloqueados el 2026-08-07,
al cerrarse los puntos 1 a 7.
