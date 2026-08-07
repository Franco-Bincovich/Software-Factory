---
titulo: Standards
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.1
owner: CEO
actualizado: 2026-08-07
adr: [ADR-000, ADR-001, ADR-002, ADR-012]
aliases: [Standards, Estándares]
---

# Standards

## Propósito

Fijar las convenciones concretas del proyecto: cómo se nombra, cómo se estructura
un documento, cómo se commitea, cómo se organiza el código.

**No contiene buenas prácticas genéricas.** Cada convención de acá es una
respuesta a algo que pasó o que va a pasar en este proyecto.

## Alcance

Cubre nombres, frontmatter, estructura documental, commits y organización del
código. No cubre estilo de programación de un lenguaje concreto: eso llega cuando
Technology Stack se desbloquee.

---

## Nombres

### Documentos

**ADRs:** `ADR-NNN - Título en minúscula.md`. Número de tres dígitos, sin ceros
omitidos.

**Normas y contratos:** el nombre en el idioma en que estaba el índice original.
Los diecisiete documentos de diseño estratégico están en inglés —`Architecture`,
`Verification`— y los posteriores en castellano. **Es una inconsistencia real y se
conserva a propósito**: renombrarlos rompería enlaces sin resolver ningún
problema.

**Agent Definitions:** el nombre canónico del agente, tal cual — `Requirement
Agent.md`.

**Especificaciones de construcción:** `TN - Descripción.md`, con el número de
tarea del plan de versión.

### Alias

Todo documento vinculante declara al menos un alias corto y estable. Es lo que
permite enlazar `[[ADR-005]]` sin escribir el nombre completo, y lo que hace que
renombrar un archivo no rompa los enlaces.

**Un alias idéntico al nombre del archivo no aporta nada.** Los alias existen para
dar formas cortas alternativas.

### Vocabulario

El glosario de ADR-001 es obligatorio. **Agent Definition** y **Agent Run** se
usan con precisión y no se intercambian. "Agente" sin calificar está prohibido en
documentos vinculantes.

Las fases se nombran **Fase 0, Fase 1, Fase 2**. Ningún nombre propio.

---

## Frontmatter

Campos obligatorios en todo documento vinculante, en este orden:

```yaml
titulo:        # excepto ADRs, cuyo H1 es el título
tipo:          # uno de los seis de ADR-012
estado:        # propuesto | borrador | aceptado | reemplazado
aprobado:      # fecha, vacío mientras esté propuesto
version:
owner:
actualizado:
adr: []        # los ADRs de los que depende
aliases: []
```

`borrador` es un estado legítimo y no un documento a medias: designa un
documento que declara explícitamente qué le falta y por qué. Un
documento incompleto que no declara sus huecos no es borrador, está mal
escrito.

**`adr:` refleja las dependencias reales del cuerpo.** Si el documento cita un
ADR, ese ADR está en la lista. Un frontmatter desactualizado es documentación que
miente, en su forma más chica y más fácil de dejar pasar.

**Los estados se escriben sin tilde** — `en-revision`, no `en-revisión`. Cualquier
validación por texto los compara literalmente.

---

## Estructura de un documento

**ADRs:** contexto → opciones consideradas → decisión → consecuencias →
decisiones que habilita → decisiones que no resuelve.

**Normas y contratos:** propósito → alcance → contenido → decisiones tomadas →
decisiones abiertas → impacto en otros documentos.

Las dos últimas secciones son obligatorias. Un documento sin "decisiones
abiertas" declaradas está afirmando que no dejó ninguna, y eso casi nunca es
cierto.

### Prosa sobre listas

Se usa prosa cuando el razonamiento tiene hilo argumental, y listas solo cuando el
contenido es realmente enumerable. Una lista de afirmaciones inconexas oculta que
no hay argumento.

### Marcadores de relleno prohibidos

`TBD`, `TODO`, `por definir`, `N/A`, `placeholder`. **Un campo que no se puede
llenar de verdad se declara ausente y se dice hasta cuándo.**

---

## Commits

**Un commit por cambio lógico.** Si el mensaje necesita una conjunción, son dos
commits.

Formato: `tipo: descripción en minúscula, sin tilde`

| Tipo | Para qué |
|---|---|
| `feat` | Funcionalidad nueva |
| `fix` | Corrección de comportamiento |
| `test` | Tests |
| `docs` | Documentación, vault incluido |
| `refactor` | Cambio interno sin cambio de comportamiento |

El mensaje dice **qué cambió**, no cómo. `docs: ADR-005 capa de verificacion`, no
`docs: agregué un archivo`.

**Sin tildes en los mensajes**, por consistencia con lo ya commiteado.

---

## Repositorios

**Tres ubicaciones hermanas, nunca anidadas:**

| Qué | Dónde | Git |
|---|---|---|
| Normas | `Software Factory/` | Sí |
| Código | `software-factory-core/` | Sí |
| Hechos | `software-factory-state/` | **No** |

Anidar el código dentro del vault haría que el historial normativo se llene de
commits de implementación. Anidar el estado dentro de un repo haría que los hechos
se versionen, contra ADR-011.

### Estructura del repo de código

```
/schema      esquemas de datos
/src         implementación, un módulo por pieza
/fixtures    datos de prueba
/tests       un archivo por módulo
/templates   plantillas para el usuario
/docs        especificaciones de construcción
```

**Un módulo por pieza del plan.** `verificador.py` es T7, `gates.py` es T11. La
correspondencia es directa a propósito: hace obvio qué implementa qué.

### Dependencias

**Ninguna sin justificación declarada.** El repositorio arrancó con librería
estándar; cada agregado se declara y se **fija la versión exacta**, nunca un
rango.

Actualizar una dependencia exige correr la suite completa antes de fijar la nueva
versión.

---

## Tests

**Un test por criterio de aceptación de la especificación.** No más, no menos: la
correspondencia uno a uno es lo que permite verificar que la especificación se
cumplió entera.

Los tests corren contra datos temporales, **nunca contra el estado real**.

Un test verifica **lo que la especificación dice**, no lo que el código hace. Un
test escrito mirando la implementación confirma que el código hace lo que hace,
que no es información.

## Decisiones tomadas

1. La inconsistencia de idioma en los nombres se conserva.
2. Todo documento vinculante declara alias corto y estable.
3. Los estados se escriben sin tilde.
4. Un commit por cambio lógico, sin tildes en el mensaje.
5. Un módulo por pieza del plan.
6. Un test por criterio de aceptación.
7. Versiones de dependencias fijas, nunca rangos.

## Decisiones abiertas

1. **Estilo de código por lenguaje.** Bloqueado hasta Technology Stack.
2. **Semántica del campo `version`.** Existe y no está definida. Nada lo necesita
   hoy.
3. **Convención de nombres para artefactos producidos por la fábrica.** Se define
   cuando produzca el primero.

## Impacto en otros documentos

**ADR-012** — este documento aplica su taxonomía. **ADR-002** — desarrolla sus
convenciones de estructura. **Development Methodology** — asume estas
convenciones. **Technology Stack** (bloqueado) — heredará la sección de estilo de
código.
