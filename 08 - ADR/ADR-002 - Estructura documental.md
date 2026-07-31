---
estado: propuesto
version: 1.0
owner: CEO
actualizado: 2026-07-31
adr: [ADR-000, ADR-001]
aliases: [ADR-002]
---

# ADR-002 — Estructura documental

## Contexto

El vault anterior tenía dos índices que no coincidían: uno de dieciocho documentos en
el Master Plan y otro de diez secciones en Home. La numeración de carpetas iba de `00`
a `11` con nueve posiciones intermedias vacías, sin que ninguna documentación explicara
la taxonomía. Once de los dieciocho documentos del índice no existían.

## Problema

¿Qué documentos componen el vault, dónde vive cada uno, y cuál es el índice oficial?

## Alternativas evaluadas

**Conservar los dieciocho documentos.** Varios de ellos —KPIs, Quality, Future
Versions, Risks— no tienen contenido propio suficiente en esta fase y funcionan mejor
como secciones de otros documentos. Mantenerlos crea documentos huérfanos que nadie
escribe y que rompen el índice.

**Conjunto reducido con secciones absorbidas.** Menos documentos, cada uno con dueño y
alcance claro. Un documento se promueve a archivo propio cuando su contenido lo
justifica, mediante ADR.

## Decisión

**Índice único.** El índice oficial es `01 - Master Plan/Project Master Plan.md`.
`00 - Home/Home.md` es navegación y no declara estructura: enlaza al índice.

**Taxonomía de carpetas, sin huecos:**

```
00 - Home
01 - Master Plan
02 - Architecture
03 - Agent Framework
04 - Knowledge Management
05 - Infrastructure
06 - Standards
07 - Projects
08 - ADR
09 - Templates
99 - Archive
```

**Documentos del vault:**

| Carpeta | Documento |
|---|---|
| 01 | Project Master Plan · Vision · Objectives · Scope · Principles · Roadmap · Decision Making |
| 02 | Architecture · Technology Stack |
| 03 | Agent Framework · Autonomy and HITL · Verification |
| 04 | Knowledge Management |
| 05 | Infrastructure · Security |
| 06 | Standards · Development Methodology |
| 07 | un subdirectorio por proyecto, con su propia estructura |

**Contenidos absorbidos, sin documento propio en esta fase:**

- *KPIs* → sección de `Verification`. Las métricas que importan salen de criterios
  verificados, no de un documento aparte.
- *Quality* → repartido entre `Verification` (qué se comprueba) y `Standards` (qué se
  exige).
- *Risks* → sección de `Project Master Plan`. Un registro de riesgos vivo, no un
  documento estático.
- *Future Versions* → sección final de `Roadmap`.
- *Human in the Loop* → absorbido por `Autonomy and HITL`, que trata autonomía y control
  como una sola decisión porque lo son.

**Promoción a documento propio.** Cuando una sección supere el alcance de su documento
anfitrión, se promueve mediante ADR. No se crean documentos por anticipación.

**Regla de principios.** Solo `Principles.md` enuncia principios. Los demás documentos
los referencian por identificador.

## Justificación

El índice anterior tenía dieciocho documentos y once de ellos no existían. El conjunto
nuevo tiene diecisiete: se absorbieron cinco —KPIs, Quality, Risks, Future Versions y
Human in the Loop— y se agregaron tres —Autonomy and HITL, Verification y Standards. La
reducción neta es menor y no es el punto: el objetivo no fue tener menos documentos sino
que ninguno quede huérfano y que cada uno tenga un ADR que lo sustente. Los documentos
creados por anticipación no se escriben y degradan la confianza en el índice.

La fusión de autonomía y HITL en un solo documento responde a una contradicción
concreta del vault anterior: se los trataba como temas separados y por eso convivían un
principio de HITL obligatorio con un roadmap que lo implementaba recién en la anteúltima
fase.

## Consecuencias

**A favor:** el índice refleja lo que existe. Cada documento tiene alcance definido y no
se solapa con otro.

**En contra:** documentos como `Verification` cargan contenido heterogéneo —criterios,
métricas, gates— y van a crecer hasta necesitar división. Es deuda aceptada y explícita.

**Nota:** `07 - Projects` queda declarado pero sin estructura interna. Definirla exige
tener cerrado el modelo de aislamiento por proyecto, que es materia de otro ADR.

## Dependencias

**Requiere:** ADR-000, ADR-001.
**Habilita:** la escritura del Master Plan y del resto del vault.
**Bloquea:** creación de carpetas o documentos fuera de esta lista sin ADR.

## Documentos afectados

Crea el índice oficial. Fija la ubicación de todo documento futuro.
