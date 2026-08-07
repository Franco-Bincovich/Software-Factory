---
titulo: Development Methodology
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-000, ADR-002, ADR-003, ADR-005]
aliases: [Development Methodology, Metodología]
---

# Development Methodology

## Propósito

Definir cómo se construye la fábrica: el ciclo de trabajo, la disciplina de
ejecución y las reglas que evitan los modos de falla ya identificados.

Es metodología para construir **la fábrica**, no para el software que la fábrica
produzca. Eso último lo define el Plan de Trabajo de cada proyecto.

## Alcance

Cubre el ciclo decisión → especificación → construcción → verificación, la
disciplina de prompts, el manejo de decisiones abiertas y el timebox. No cubre
estándares de código —eso es Standards— ni el gobierno de la ejecución —eso es
Autonomy and HITL—.

---

## El ciclo

### 1. La decisión, antes que nada

Ninguna pieza se construye antes de que estén cerradas las decisiones que la
condicionan. Una decisión cerrada es un ADR aprobado.

**Las decisiones llegan pre-cerradas.** Se trae una recomendación fundada para
aprobar, corregir o rechazar — no un menú de opciones. Un menú traslada al CEO el
trabajo de analizar, que es justamente lo que se delegó.

### 2. La especificación, antes del código

Cada pieza se especifica antes de construirse. Una especificación completa
incluye:

- Qué es y qué **no** es.
- El comportamiento, con las reglas explícitas.
- **Un criterio de aceptación por fila de una tabla**, cada uno verificable.
- Lo que queda fuera de alcance.

Sin criterio de aceptación escrito antes, la construcción no arranca. Es la misma
regla que la fábrica le aplica a sus propios agentes.

### 3. La construcción, contra la especificación

El ejecutor construye lo que la especificación dice. **No inventa contenido, no
interpreta, no completa huecos.** Si la especificación es ambigua, lo reporta en
vez de resolverlo por su cuenta.

### 4. La verificación, antes de cerrar

Un test por cada fila de la tabla de criterios de aceptación. Ninguna pieza se
cierra sin su suite pasando.

Y una condición que no es negociable: **una pieza está terminada cuando existe
evidencia de que hace lo que dice**, no cuando el código está escrito.

---

## Disciplina de prompts al ejecutor

Todo prompt de construcción tiene esta forma:

**Tareas numeradas**, cada una con su criterio de aceptación.
**Rutas exactas** de archivo. Nada de "donde corresponda" sin decir cómo
decidirlo.
**Prohibición explícita de inventar contenido.**
**Commits separados** por cambio lógico, con sus mensajes declarados.
**Una sección "NO HAGAS"** con lo que queda fuera de alcance.
**Reporte final** con las decisiones de forma que hubo que tomar porque el prompt
no las fijaba.

Ese último punto es el que más valor produce. Las decisiones de forma reportadas
son donde aparecen los huecos de la especificación, y varias correcciones
importantes salieron de ahí.

### Verificar antes de mover, mover antes de borrar

Toda operación destructiva se encadena a su verificación. Un archivo se borra solo
después de comprobar que la copia es idéntica.

---

## Manejo de decisiones abiertas

**Máximo tres decisiones abiertas vivas.** Si aparece una cuarta, se cierra una
antes. Un inventario creciente de decisiones abiertas es el síntoma más confiable
de que el proyecto dejó de avanzar.

**Una decisión diferida no es una decisión pendiente.** Se marca como diferida a
una versión concreta y sale del tablero. Lo diferido no pesa; lo pendiente sí.

**Cada análisis cierra con las decisiones abiertas que genera.** Explícitas, no
implícitas.

---

## Timebox

**El plazo es fijo. El alcance es la variable.**

Al llegar al límite, se recorta. La pieza que falte sale en su forma mínima o
pasa a la versión siguiente, declarada. No se extiende el plazo — extenderlo una
vez lo vuelve extensible siempre.

---

## Modos de falla conocidos y su antídoto

Cada uno de estos ocurrió, acá o en el artefacto de referencia externo.

| Modo de falla | Antídoto |
|---|---|
| Documentación que diverge de la implementación | Un campo se llena solo cuando tiene valor verdadero. Nada de marcadores de relleno |
| Decisión tomada en conversación y nunca registrada | Es deuda hasta que exista su ADR. LangGraph fue el caso |
| Componente que falla en silencio | El artefacto declara qué se degradó. Sin alarma no hay entrega |
| Rechazo que no localiza el problema | Nombra la unidad y el criterio exactos, y devuelve la lista completa |
| Estimación sin datos con apariencia de dato | No se estima hasta tener corridas medidas |
| Estructura declarada que no coincide con la real | El índice cubre todo documento vinculante, o se corrige |

---

## Reglas de repositorio

**Tres ubicaciones hermanas, nunca anidadas.** Normas en el vault, código en su
repo, hechos afuera de ambos y sin versionar.

**Un commit por cambio lógico**, con mensaje que diga qué cambió y no cómo.

**Ninguna dependencia nueva sin justificación.** El repositorio arrancó con
librería estándar; cada agregado se declara y se fija la versión exacta.

## Decisiones tomadas

1. Las decisiones llegan pre-cerradas, no como menú de opciones.
2. Sin criterio de aceptación escrito, no se construye.
3. Un test por criterio de aceptación.
4. Máximo tres decisiones abiertas vivas.
5. Lo diferido sale del tablero; lo pendiente no.
6. El plazo es fijo y el alcance es la variable.

## Decisiones abiertas

1. **Cuándo la fábrica empieza a construirse a sí misma.** Hoy la construye el
   CEO con el ejecutor. El criterio de salida de ese andamio no está definido.
2. **Revisión entre pares.** Hoy el CEO es el único revisor. R3 sigue abierto.

## Impacto en otros documentos

**Standards** — desarrolla las convenciones concretas que este documento asume.
**PLAN-V0.1** — es la aplicación de esta metodología a la primera versión.
**Decision Making** — desarrolla cómo se toma y registra una decisión.
