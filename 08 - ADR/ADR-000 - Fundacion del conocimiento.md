---
estado: aceptado
aprobado: 2026-08-06
version: 1.0
owner: CEO
actualizado: 2026-07-31
aliases: [ADR-000]
---

# ADR-000 — Fundación del conocimiento

## Contexto

El vault inicial del proyecto contenía diez archivos escritos en una sola sesión,
ninguno declarado cerrado, sin control de versiones, con cero ADRs y con el ADR
fundacional vacío. Un reporte de lectura identificó nueve contradicciones, catorce
decisiones tomadas de facto sin registro y dieciocho términos con más de un
significado.

La causa común es que se escribieron documentos antes de tomar decisiones. La
documentación quedó como lugar donde las decisiones aparecen afirmadas, no
registradas.

## Problema

¿Cuál es la fuente de verdad del proyecto, en qué formato vive, y qué gobierna
la escritura de un documento?

## Alternativas evaluadas

**Obsidian como fuente de verdad.** Es lo que declaraba el vault anterior. Obsidian
es una aplicación específica: atarle la fuente de verdad crea dependencia de producto
y contradice la exclusión de herramientas propietarias del alcance original. Además
no ofrece control de concurrencia ni historial.

**Base de datos documental.** Resuelve concurrencia y consulta, pero saca al humano
del circuito de edición directa y exige infraestructura antes de haber decidido la
arquitectura. Prematuro en esta fase.

**Markdown plano bajo control de versiones.** El formato es abierto y legible sin
herramientas. El control de versiones aporta historial, autoría, reversibilidad y
revisión por propuesta de cambio. Obsidian pasa a ser un visor intercambiable.

## Decisión

1. La fuente de verdad del proyecto es **markdown plano bajo control de versiones**.
   Obsidian es un visor recomendado, nunca un requisito.
2. La unidad de decisión es el **ADR**. Una decisión sin ADR no es una decisión del
   proyecto, sin importar dónde esté afirmada.
3. **Ningún documento del vault se escribe antes que el ADR que lo sustenta.**
4. Todo documento lleva frontmatter con estado, versión, owner, ADRs que lo sustentan
   y fecha. Un documento sin frontmatter es inválido.
5. Un documento en estado `borrador` no puede citarse como fundamento de otra decisión.
6. Un ADR aprobado no se edita: se supera con un ADR posterior que lo referencia.
7. El vault anterior se conserva completo en `99 - Archive` como evidencia del punto
   de partida. No se copia contenido de él: se lo usa como insumo para decidir.

## Justificación

El formato abierto elimina el lock-in y la contradicción de alcance. El control de
versiones convierte la trazabilidad —declarada como principio en cuatro documentos del
vault anterior y nunca ejecutable— en una propiedad del sistema y no en una promesa.
La regla de ADR antes que documento ataca la causa raíz: mientras escribir sea más
barato que decidir, el vault vuelve a llenarse de decisiones implícitas.

## Consecuencias

**A favor:** todo cambio queda con autor, fecha y motivo. El vault es portable. Las
decisiones son auditables y reversibles. El grafo de dependencias entre decisiones
es reconstruible.

**En contra:** escribir se vuelve más lento y más burocrático. No se puede documentar
una idea sin antes cerrarla como decisión, lo que en fases exploratorias resulta
incómodo. Exige disciplina sostenida: la regla se rompe la primera vez que alguien
escribe "esto lo documento ahora y el ADR lo hago después".

**Mitigación de esa incomodidad:** el material exploratorio no decidido tiene lugar
propio y no se mezcla con el vault formal. Su tratamiento se decide en el ADR de
gestión del conocimiento.

## Dependencias

**Requiere:** ninguno. Es el ADR fundacional.
**Habilita:** todos los ADRs siguientes.
**Bloquea:** cualquier propuesta de fuente de verdad alternativa, y cualquier
documento escrito sin ADR previo.

## Documentos afectados

Crea: `README.md`, `09 - Templates/ADR-template.md`, estructura completa de carpetas.
Archiva: los diez documentos del vault anterior.
