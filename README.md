# Vault — Software Factory Autónoma

Base de conocimiento oficial del proyecto. Markdown plano bajo control de versiones.
Obsidian es el visor recomendado, no un requisito.

## Regla fundamental

**Ningún documento se escribe antes que el ADR que lo sustenta.**
El ADR es la unidad de decisión. El documento es su desarrollo.
Si algo no tiene ADR detrás, no entra al vault.

## Estructura de carpetas

| Carpeta | Contenido |
|---|---|
| `00 - Home` | Punto de entrada y navegación |
| `01 - Master Plan` | Visión, objetivos, alcance, principios, roadmap, gobierno de decisión |
| `02 - Architecture` | Arquitectura de la plataforma y stack tecnológico |
| `03 - Agent Framework` | Contrato de agente, autonomía y HITL, verificación |
| `04 - Knowledge Management` | Modelo de conocimiento y memoria |
| `05 - Infrastructure` | Infraestructura, operación, seguridad |
| `06 - Standards` | Normas vinculantes de desarrollo y metodología |
| `07 - Projects` | Un subdirectorio por proyecto ejecutado por la plataforma |
| `08 - ADR` | Architecture Decision Records |
| `09 - Templates` | Plantillas |
| `99 - Archive` | Material superado, conservado como evidencia |

No se crean carpetas nuevas sin ADR.

## Convenciones

**Nombres de archivo.** Inglés, sin doble extensión, sin numeración salvo ADRs.
**Contenido.** Español rioplatense.
**Términos técnicos canónicos.** Inglés, según ADR-001. Un término, un significado, un nombre.

**Un solo README.** Existe un único `README.md` en todo el vault, en la raíz. Las
notas de carpeta se nombran `<Carpeta> - nota.md`.

**Frontmatter obligatorio en todo documento:**

```yaml
---
estado: borrador | en-revision | aprobado | superado
version: 0.1
owner: CEO
adr: [ADR-000, ADR-001]
actualizado: 2026-07-31
---
```

El frontmatter es obligatorio para todo documento ubicado en las carpetas numeradas
`00` a `07`. `README.md`, los reportes de raíz y el material de `99 - Archive` son
artefactos de repositorio o evidencia, no documentos del vault, y quedan exentos.
Un documento en estado `borrador` no puede ser citado como fundamento de otra decisión.

**ADRs.** Numeración correlativa de tres dígitos desde `ADR-000`. Nunca se editan
una vez aprobados: se superan con un ADR nuevo que los referencia.

**Evidencia append-only.** Los reportes y el material de 99 - Archive no se corrigen
retroactivamente. Un dato que quedó desactualizado se cierra con una sección nueva,
nunca editando la anterior.

## Estados de un ADR

`propuesto` → `aprobado` → `superado por ADR-NNN`

Un ADR rechazado se conserva con estado `rechazado`. No se borra.

Un ADR en estado `propuesto` se edita libremente. La inmutabilidad rige desde que pasa
a `aprobado`: a partir de ahí solo se supera con un ADR posterior.
