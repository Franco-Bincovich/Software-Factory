---
tipo: adr
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-11
adr: [ADR-000, ADR-002]
aliases: [ADR-012]
---

# ADR-012 — Taxonomía documental

## Contexto

Desde que se empezó a construir, apareció en el frontmatter un campo `tipo:` que
ningún ADR declara. Ya lleva cinco valores distintos —`plan-de-version`,
`contrato`, `agent-definition`, `guia`, `runbook`, `norma`— y ninguno está
definido en ninguna parte.

Es una taxonomía emergiendo sola. Hoy es inofensiva; en veinte documentos es un
vocabulario paralelo al de ADR-001, con valores inventados sobre la marcha y
significados que nadie fijó.

Hay además un problema conexo que el crecimiento del vault dejó al descubierto:
el Project Master Plan se declara "índice oficial del vault" y no lista nueve
documentos activos, incluidos los nueve ADRs y los dos artefactos de
`03 - Agent Framework/`. La estructura declarada y la estructura real no
coinciden.

## Opciones consideradas

**A. Eliminar el campo `tipo:`.** Simple, y pierde información real: no es lo
mismo una norma que una guía a la hora de saber si un documento obliga.

**B. Declarar la taxonomía en un ADR nuevo.** Elegida.

**C. Reemplazar ADR-002.** Desproporcionado. ADR-002 decide la estructura de
carpetas y sigue siendo correcto; esto le agrega una dimensión.

## Decisión

### 1. El campo `tipo:` es obligatorio y su lista es cerrada

Seis valores. Un documento con un `tipo:` fuera de la lista, o sin el campo, no
está bien formado.

| Valor | Qué es | Obliga | Ejemplo |
|---|---|---|---|
| `adr` | Decisión arquitectónica registrada | Sí | ADR-005 |
| `norma` | Documento normativo derivado de uno o más ADRs | Sí | Verification |
| `contrato` | Formato o interfaz que otras piezas deben cumplir | Sí | Contrato del Plan de Trabajo |
| `agent-definition` | Definición de un agente según ADR-003 | Sí | Requirement Agent |
| `plan-de-version` | Alcance y criterio de terminación de una versión | Sí | PLAN-V0.1 |
| `guia` | Material de apoyo. Explica, no decide | **No** | Runbook V0.1 |

Ampliar la lista requiere ADR. Es deliberado: la facilidad para inventar
categorías es lo que produjo el problema.

### 2. Solo `guia` no obliga

Los otros cinco son vinculantes. Un documento de tipo `guia` que contradiga a uno
vinculante está equivocado, y la contradicción se resuelve siempre en favor del
vinculante.

Esto le da al campo su función real: **saber de un vistazo si un documento manda
o solo explica.**

### 3. Los ADRs llevan `tipo: adr`

Hoy no lo llevan. Se agrega, para que la taxonomía cubra el vault entero y no
solo lo escrito después de cierta fecha.

### 4. El índice oficial cubre todo el vault

El Project Master Plan declara ser el índice oficial. Para que eso sea verdad
tiene que listar todo documento vinculante del vault activo, no solo los
diecisiete de diseño estratégico.

Se organiza en dos partes:

- **Documentos de diseño estratégico** — los dieciocho originales.
- **Artefactos vinculantes** — ADRs, contratos, Agent Definitions y planes de
  versión.

Los de tipo `guia` no se listan como estructura: son navegación, y ahí la frase
actual del Master Plan es correcta.

### 5. Un documento fuera del índice no obliga

Si un documento vinculante no figura en el índice, el índice está incompleto y
hay que corregirlo. Pero mientras no figure, **no se le puede exigir a nadie que
lo cumpla**: no hay forma de saber que existe.

Es la única regla de este ADR que tiene efecto sobre el comportamiento, y por eso
está.

## Consecuencias

**Lo que habilita.** Un documento nuevo tiene categoría antes de escribirse.
Preguntar "¿esto obliga?" tiene respuesta mecánica. El índice deja de mentir.

**Lo que cuesta.** Hay que tocar los nueve ADRs para agregarles `tipo: adr` y
reestructurar el índice del Master Plan. Es trabajo mecánico, pero toca
documentos ya aprobados. Se acepta porque agregar un campo de clasificación no
cambia lo que ninguno de ellos decide.

**Lo que no cambia.** ADR-002 sigue vigente: las carpetas `00`–`99` no se tocan.
Este ADR agrega una dimensión de clasificación, no una estructura nueva.

## Decisiones que habilita

- Auditoría automática del vault: con `tipo:` obligatorio y lista cerrada, un
  validador puede detectar documentos mal formados.
- Alcance de lectura de agentes: `vault_lectura` puede expresarse por tipo cuando
  el vault crezca.

## Decisiones que no resuelve

- **Qué hacer con documentos que no son ninguno de los seis tipos** —README,
  reportes de construcción—. Quedan fuera del índice y no obligan, que es lo
  correcto.
- **Versionado semántico de documentos.** El campo `version` existe y su
  semántica no está declarada. No lo necesita nada hoy.
