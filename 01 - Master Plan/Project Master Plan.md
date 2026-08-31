---
titulo: Project Master Plan
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
adr: [ADR-000, ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-012]
actualizado: 2026-08-11
---

# Project Master Plan

Índice oficial del vault. Cualquier otro listado de documentos es navegación, no
estructura.

El criterio de cierre de Fase 0 y el alcance de la versión en curso viven en
[[PLAN-V0.1]].

## Estado de la Fase 0

**Fase 0 — Diseño Estratégico.** Cerrada el 2026-08-07.

Los cinco ADRs que consume V0.1 están aprobados: ADR-005, ADR-008,
ADR-009, ADR-010 y ADR-011. Los dieciocho documentos del índice
existen como archivo.

Criterio de cierre según [[PLAN-V0.1]]: capacidad operativa demostrada,
no cantidad de documentos aprobados.

ADRs aprobados: 21 (ADR-000 a ADR-006, ADR-008 a ADR-021).

**Bloque B de V0.1 cerrado el 2026-08-11**, T14 incluido: el armazón de
ejecución corre de punta a punta. Fase siguiente: Bloque C —T15 primera corrida
real, T16 ejecución manual del plan, T17 corrida de control—, que es lo que
decide si V0.1 terminó según [[PLAN-V0.1]].

## Índice

### 01 - Master Plan

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Project Master Plan]] | aceptado | [[ADR-002]] |
| [[Vision]] | aceptado | — |
| [[Objectives]] | aceptado | — |
| [[Scope]] | aceptado | [[ADR-008]] |
| [[Principles]] | aceptado | — |
| [[Roadmap]] | aceptado | ADR pendiente: secuencia de fases |
| [[Decision Making]] | aceptado | [[ADR-000]] |

### 02 - Architecture

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Architecture]] | aceptado | ADR pendiente: modelo de capas |
| [[Technology Stack]] | aceptado | [[ADR-004]], [[ADR-006]], [[ADR-008]], [[ADR-011]] |
| [[Guía de uso de LangGraph]] | aceptado | [[ADR-004]], [[ADR-006]], [[ADR-010]], [[ADR-011]] |

### 03 - Agent Framework

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Agent Framework]] | aceptado | [[ADR-003]] |
| [[Autonomy and HITL]] | aceptado | [[ADR-004]] |
| [[Verification]] | aceptado | [[ADR-005]] |

### 04 - Knowledge Management

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Knowledge Management]] | aceptado | [[ADR-011]] |

### 05 - Infrastructure

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Infrastructure]] | aceptado | [[ADR-008]], [[ADR-009]], [[ADR-011]] |
| [[Security]] | borrador | [[ADR-009]] |

### 06 - Standards

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Standards]] | aceptado | — |
| [[Development Methodology]] | aceptado | ADR pendiente: ciclo de trabajo |

> El estado de cada documento se lee de su propio frontmatter. Los
> documentos de tipo `guia` no se listan acá: son navegación, no
> estructura.

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
| [[ADR-013]] | adr | aceptado |
| [[ADR-014]] | adr | aceptado |
| [[ADR-015]] | adr | aceptado |
| [[ADR-016]] | adr | aceptado |
| [[ADR-017]] | adr | aceptado |
| [[ADR-018]] | adr | aceptado |
| [[Contrato del Plan de Trabajo]] | contrato | aceptado |
| [[Contrato de Entrega del Developer]] | contrato | aceptado |
| [[Requirement Agent]] | agent-definition | aceptado |
| [[Developer Agent]] | agent-definition | aceptado |
| [[PLAN-V0.1]] | plan-de-version | aceptado |
| [[Project Master Plan]] | norma | aceptado |
| [[Ruleset mecánico]] | contrato | aceptado |
| [[Constitución Técnica]] | norma | aceptado |

## Registro de riesgos

Riesgos vivos del proyecto. Se actualiza al cerrar cada ADR.

| # | Riesgo | Impacto | Estado |
|---|---|---|---|
| R1 | Verificación producida por el mismo tipo de sistema que produce el código: la autonomía se vuelve confianza ciega. | Alto | Mitigado parcialmente — ADR-005. Verificación sustantiva diferida a V0.3. |
| R2 | Costo de ejecución sin techo por agente ni por proyecto. | Alto | Mitigado — ADR-010. |
| R3 | El CEO como único aprobador de todos los Gates lo convierte en cuello de botella por diseño. | Alto | Mitigado parcialmente — ADR-004. Persiste mientras exista un solo rol humano aprobador. |
| R4 | Alcance abierto ("cualquier tipo de sistema") sin primer corte funcional. | Alto | Mitigado — ADR-008. |
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
11. Modelo organizacional de agentes en Departamentos y Roles — pendiente,
    diferido a V0.3. Es ADR-007. Contexto en [[Agent Framework]], que lo declara
    fuera de su alcance; [[ADR-008]] confirma que V1 no lo necesita.

Los puntos 1 a 7 son los que cierran Fase 0 según [[PLAN-V0.1]].
Los puntos 8, 9 y 11 se difieren: no los consume V0.1.

Technology Stack e Infrastructure quedaron desbloqueados el 2026-08-07,
al cerrarse los puntos 1 a 7.
