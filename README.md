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
titulo:        # excepto ADRs, cuyo H1 es el título
tipo:          # adr | norma | contrato | agent-definition | plan-de-version | guia
estado:        # propuesto | borrador | aceptado | reemplazado | retirado | archivado
aprobado:      # fecha, vacío mientras esté propuesto
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-000, ADR-001]
aliases: []
---
```

Los seis valores de `tipo:` son lista cerrada según ADR-012: los cinco primeros
obligan, `guia` no. El orden de los campos lo fija Standards; los seis estados son
los de la sección "Estados de un documento".

El frontmatter es obligatorio para todo documento ubicado en las carpetas numeradas
`00` a `07`. `README.md`, los reportes de raíz y el material de `99 - Archive` son
artefactos de repositorio o evidencia, no documentos del vault, y quedan exentos.
Un documento en estado `borrador` no puede ser citado como fundamento de otra decisión.

**ADRs.** Numeración correlativa de tres dígitos desde `ADR-000`. Nunca se editan
una vez aprobados: se superan con un ADR nuevo que los referencia.

**Evidencia append-only.** Los reportes y el material de 99 - Archive no se corrigen
retroactivamente. Un dato que quedó desactualizado se cierra con una sección nueva,
nunca editando la anterior.

## Estados de un documento

Lista cerrada. Aplica a todo documento del vault, no solo a los ADRs.

| Estado | Significado |
|---|---|
| `propuesto` | Documento en discusión. No obliga. |
| `borrador` | Documento en elaboración. No obliga. |
| `aceptado` | Documento aprobado y vigente. Obliga según su tipo. |
| `reemplazado` | Sustituido por una versión posterior o por otro documento. Se conserva como referencia. Indicar el sucesor. |
| `retirado` | Documento que fue normativo y ya no lo es. Se conserva como referencia histórica. |
| `archivado` | Material movido a `99 - Archive/`. Sin valor normativo. |

`propuesto` y `borrador` son estados de trabajo: el documento se edita libremente. La
inmutabilidad rige desde que pasa a `aceptado`. Un ADR aceptado solo se supera con un
ADR posterior, y el superado queda en `reemplazado` nombrando a su sucesor.
