---
estado: en-revision
version: 1.0
owner: CEO
adr: [ADR-000, ADR-001, ADR-002]
actualizado: 2026-07-31
---

# Project Master Plan

Índice oficial del vault. Cualquier otro listado de documentos es navegación, no
estructura.

## Estado de la Fase 0

**Fase 0 — Diseño Estratégico.** No se implementa software. La fase cierra cuando todos
los documentos de este índice están en estado `aprobado`.

Documentos aprobados: 0 de 15.

## Índice

### 01 - Master Plan

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Project Master Plan]] | en-revisión | ADR-002 |
| [[Vision]] | pendiente | — |
| [[Objectives]] | pendiente | — |
| [[Scope]] | pendiente | ADR pendiente: primer corte funcional |
| [[Principles]] | pendiente | — |
| [[Roadmap]] | pendiente | ADR pendiente: secuencia de fases |
| [[Decision Making]] | pendiente | ADR-000 |

### 02 - Architecture

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Architecture]] | pendiente | ADR pendiente: modelo de capas |
| [[Technology Stack]] | bloqueado | requiere Agent Framework y Architecture |

### 03 - Agent Framework

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Agent Framework]] | pendiente | ADR pendiente: contrato de agente |
| [[Autonomy and HITL]] | pendiente | ADR pendiente: modelo de control |
| [[Verification]] | pendiente | ADR pendiente: capa de verificación |

### 04 - Knowledge Management

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Knowledge Management]] | pendiente | ADR pendiente: planos de conocimiento |

### 05 - Infrastructure

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Infrastructure]] | bloqueado | requiere Technology Stack |
| [[Security]] | pendiente | ADR pendiente: identidad y permisos de agentes |

### 06 - Standards

| Documento | Estado | ADR que lo sustenta |
|---|---|---|
| [[Standards]] | pendiente | — |
| [[Development Methodology]] | pendiente | ADR pendiente: ciclo de trabajo |

## Registro de riesgos

Riesgos vivos del proyecto. Se actualiza al cerrar cada ADR.

| # | Riesgo | Impacto | Estado |
|---|---|---|---|
| R1 | Verificación producida por el mismo tipo de sistema que produce el código: la autonomía se vuelve confianza ciega. | Alto | Abierto — mitigación en ADR de verificación |
| R2 | Costo de ejecución sin techo por agente ni por proyecto. | Alto | Abierto — sin ADR asignado |
| R3 | El CEO como único aprobador de todos los Gates lo convierte en cuello de botella por diseño. | Alto | Abierto — mitigación en ADR de control |
| R4 | Alcance abierto ("cualquier tipo de sistema") sin primer corte funcional. | Alto | Abierto — mitigación en ADR de primer corte |
| R5 | Bootstrapping: la plataforma construida por sus propios agentes genera dependencia circular. | Medio | Abierto |
| R6 | Agent Factory priorizada antes de operar los Core Agents de punta a punta. | Medio | Abierto |
| R7 | Aislamiento de datos entre proyectos de terceros no definido. | Medio | Abierto |

## Secuencia de decisión

Orden en que deben cerrarse los ADRs pendientes. No se altera sin ADR.

1. Contrato de agente
2. Modelo de control: autonomía y Gates
3. Capa de verificación y Acceptance Criteria
4. Planos de conocimiento
5. Modelo de capas de la arquitectura
6. Primer corte funcional de V1
7. Secuencia de fases del roadmap
8. Identidad y permisos de agentes

Technology Stack e Infrastructure quedan bloqueados hasta que 1 a 6 estén aprobados.
