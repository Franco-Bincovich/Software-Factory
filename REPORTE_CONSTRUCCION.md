# Reporte de construcción del vault

Fecha: 2026-07-31 · Alcance: Tareas 1 a 7 del prompt de construcción.
Los 7 archivos nuevos se incorporaron sin editar su contenido; la única modificación
fue el `aliases` autorizado en los tres ADRs.

---

## 1. Árbol del vault resultante

```
.
├── .gitignore
├── .obsidian/
│   ├── app.json                (modificado — Tarea 5)
│   ├── appearance.json
│   ├── core-plugins.json
│   ├── graph.json
│   ├── templates.json          (nuevo — Tarea 5)
│   └── workspace.json          (ignorado por git)
├── README.md
├── REPORTE_CONSTRUCCION.md
├── 00 - Home/
│   └── Home.md
├── 01 - Master Plan/
│   └── Project Master Plan.md
├── 02 - Architecture/
│   └── .gitkeep
├── 03 - Agent Framework/
│   └── .gitkeep
├── 04 - Knowledge Management/
│   └── .gitkeep
├── 05 - Infrastructure/
│   └── .gitkeep
├── 06 - Standards/
│   └── .gitkeep
├── 07 - Projects/
│   └── .gitkeep
├── 08 - ADR/
│   ├── ADR-000 - Fundacion del conocimiento.md
│   ├── ADR-001 - Glosario canonico.md
│   └── ADR-002 - Estructura documental.md
├── 09 - Templates/
│   ├── ADR-template.md
│   └── attachments/
│       └── .gitkeep
└── 99 - Archive/
    ├── README.md
    ├── ESTADO_ACTUAL - reporte de lectura 2026-07-31.md
    └── vault-2026-07-30/
        ├── ADR-000 - Project Foundation (archivado).md
        ├── Architecture (archivado).md
        ├── Decision Making (archivado).md
        ├── Home (archivado).md
        ├── Objectives (archivado).md
        ├── Principles (archivado).md
        ├── Project Master Plan (archivado).md
        ├── Roadmap (archivado).md
        ├── Scope (archivado).md
        └── Vision (archivado).md
```

La carpeta `11 - ADR/` fue eliminada una vez vacía, según lo decidido durante la
ejecución. Total de archivos `.md` en el vault: 19 (6 del vault nuevo, 1 este reporte,
12 en `99 - Archive`).

---

## 2. Archivos archivados

Los 10 archivos del vault viejo, movidos a `99 - Archive/vault-2026-07-30/`. Contenido
sin tocar: sólo cambió el nombre.

| # | Nombre viejo | Nombre nuevo |
|---|---|---|
| 1 | `00 - Home/Home.md.md` | `Home (archivado).md` |
| 2 | `01 - Master Plan/Project Master Plan.md.md` | `Project Master Plan (archivado).md` |
| 3 | `01 - Master Plan/Vision.md` | `Vision (archivado).md` |
| 4 | `01 - Master Plan/Objectives.md` | `Objectives (archivado).md` |
| 5 | `01 - Master Plan/Scope.md` | `Scope (archivado).md` |
| 6 | `01 - Master Plan/Principles.md` | `Principles (archivado).md` |
| 7 | `01 - Master Plan/Roadmap.md` | `Roadmap (archivado).md` |
| 8 | `01 - Master Plan/Architecture.md` | `Architecture (archivado).md` |
| 9 | `01 - Master Plan/Decision Making.md` | `Decision Making (archivado).md` |
| 10 | `11 - ADR/ADR-000 - Project Foundation.md.md` | `ADR-000 - Project Foundation (archivado).md` |

Las tres dobles extensiones (`#1`, `#2`, `#10`) quedaron corregidas en el renombrado.

**Fuera de los 10, por instrucción explícita durante la ejecución:**

| Nombre viejo | Nombre nuevo |
|---|---|
| `ESTADO_ACTUAL.md` (raíz) | `99 - Archive/ESTADO_ACTUAL - reporte de lectura 2026-07-31.md` |

Se versiona en git, no lleva frontmatter y no cuenta como violación: es evidencia, no
un documento del vault. Está descripto en `99 - Archive/README.md`.

---

## 3. Violaciones de nomenclatura

Verificación sobre los 19 archivos `.md` y las 12 carpetas del vault.

### 3.1 Doble extensión — sin violaciones

Ninguna. Las tres que existían se corrigieron al archivar.

### 3.2 Tildes y caracteres especiales — sin violaciones de tildes

Ningún nombre de archivo ni de carpeta contiene caracteres no-ASCII. No hay tildes,
`ñ`, ni diéresis en ningún nombre. El riesgo de normalización de acentos entre sistemas
operativos no aplica.

**Nota, no violación:** los 10 archivos de `vault-2026-07-30/` contienen paréntesis
`(` `)` por el sufixo ` (archivado)` que la Tarea 2 exige. Son ASCII y no tienen el
problema de normalización, pero son los únicos caracteres no alfanuméricos del vault
más allá de espacios, guiones y puntos. Se deja constancia; no se corrigió.

### 3.3 Nombre de archivo único — 1 VIOLACIÓN

| Nombre | Ubicaciones |
|---|---|
| `README.md` | `README.md` (raíz) y `99 - Archive/README.md` |

**Esto es un conflicto entre dos instrucciones del prompt:** la Tarea 2 ordena crear
`99 - Archive/README.md`, y la Tarea 6 regla 3 exige nombre único en todo el vault,
incluido `99 - Archive`. Se cumplió la Tarea 2 y se reporta la colisión sin corregirla.

Tiene consecuencia real y está detallada en la sección 4.1: rompe el `[[README]]` de
`Home.md`. Es exactamente el problema que la Tarea 2 buscaba evitar con el sufijo
` (archivado)`, sólo que aparece por el README del propio Archive.

Corrección posible si la aprobás: renombrar `99 - Archive/README.md` a
`99 - Archive/Archive (archivado).md`, o a `99 - Archive/README (archivado).md`.
**No aplicada.**

### 3.4 Frontmatter obligatorio — 2 violaciones en el vault nuevo

Requisito: `estado`, `version`, `owner`, `actualizado`.

**Cumplen los 6 documentos del vault nuevo excepto `README.md`:**

| Archivo | estado | version | owner | actualizado | aliases |
|---|---|---|---|---|---|
| `00 - Home/Home.md` | aprobado | 1.0 | CEO | 2026-07-31 | — |
| `01 - Master Plan/Project Master Plan.md` | en-revision | 1.0 | CEO | 2026-07-31 | — |
| `08 - ADR/ADR-000 - Fundacion del conocimiento.md` | propuesto | 1.0 | CEO | 2026-07-31 | `[ADR-000]` |
| `08 - ADR/ADR-001 - Glosario canonico.md` | propuesto | 1.0 | CEO | 2026-07-31 | `[ADR-001]` |
| `08 - ADR/ADR-002 - Estructura documental.md` | propuesto | 1.0 | CEO | 2026-07-31 | `[ADR-002]` |
| `09 - Templates/ADR-template.md` | propuesto | 0.1 | CEO | `AAAA-MM-DD` | — |

Los tres `aliases` quedaron aplicados. `ADR-template.md` lleva `AAAA-MM-DD` como
marcador de plantilla, no como fecha: es correcto y no se tocó.

**Violación 1 — `README.md` (raíz): sin frontmatter.**
El propio README declara en su línea sobre convenciones que «un documento sin
frontmatter se considera inválido», y él mismo no lo tiene. Es uno de los 7 archivos
que llegaron redactados y no puedo editar su contenido. **No corregido.**

**Violación 2 — `99 - Archive/README.md`: sin frontmatter.**
Es el archivo que creé yo por la Tarea 2. Lo dejé sin frontmatter por coherencia con
el criterio que fijaste para `ESTADO_ACTUAL` —material del Archive es evidencia, no
documento del vault—, pero la Tarea 6 no hace esa excepción. **No corregido:** decidí
reportarlo antes que agregarle frontmatter por mi cuenta.

**No contabilizados como violación:**
- Los 10 archivos de `vault-2026-07-30/` no tienen frontmatter. Es el vault viejo tal
  cual estaba; agregárselo sería editar la evidencia.
- `ESTADO_ACTUAL - reporte de lectura 2026-07-31.md`, por tu instrucción explícita.
- `REPORTE_CONSTRUCCION.md` (este archivo) no está en la lista de documentos del vault
  ni en el índice del Master Plan.

---

## 4. Validación de enlaces

Se recorrieron todos los wikilinks `[[...]]` de los 6 documentos del vault nuevo,
resolviendo contra nombres de archivo, rutas y `aliases`. Total: 6 wikilinks, todos en
`Home.md`. Ni `Project Master Plan.md`, ni los tres ADRs, ni `README.md`, ni
`ADR-template.md` contienen wikilinks.

### 4.1 Enlaces rotos — categoría ERROR: 1

| Origen | Enlace | Problema |
|---|---|---|
| `00 - Home/Home.md` | `[[README]]` | **Ambiguo.** Resuelve a dos archivos: `README.md` (raíz) y `99 - Archive/README.md`. |

Obsidian va a elegir uno solo, probablemente el de la raíz por ser el de ruta más corta,
pero el enlace es frágil y el comportamiento no está garantizado entre versiones.

**Importante:** el filtro de exclusión de `99 - Archive/` configurado en la Tarea 5 **no
resuelve esto**. Excluir una carpeta la saca de búsquedas, del quick switcher y del
autocompletado, pero los archivos excluidos siguen siendo destino válido de wikilinks.
La única solución es renombrar, como se propone en 3.3.

### 4.2 Enlaces correctos: 5

| Origen | Enlace | Destino |
|---|---|---|
| `Home.md` | `[[Project Master Plan]]` ×2 | `01 - Master Plan/Project Master Plan.md` |
| `Home.md` | `[[ADR-000 - Fundacion del conocimiento]]` | `08 - ADR/ADR-000 - Fundacion del conocimiento.md` |
| `Home.md` | `[[ADR-001 - Glosario canonico]]` | `08 - ADR/ADR-001 - Glosario canonico.md` |
| `Home.md` | `[[ADR-002 - Estructura documental]]` | `08 - ADR/ADR-002 - Estructura documental.md` |

Los tres `aliases` quedaron verificados: `[[ADR-000]]`, `[[ADR-001]]` y `[[ADR-002]]`
resuelven correctamente y sin ambigüedad.

### 4.3 Pendientes de creación: 0 enlaces

**No hay ninguno, y conviene saber por qué.** El índice del `Project Master Plan` lista
los 15 documentos del vault en tablas de texto plano, no como wikilinks. Los 11
documentos que todavía no existen —`Vision`, `Objectives`, `Scope`, `Principles`,
`Roadmap`, `Decision Making`, `Architecture`, `Technology Stack`, `Agent Framework`,
`Autonomy and HITL`, `Verification`, `Knowledge Management`, `Infrastructure`,
`Security`, `Standards`, `Development Methodology`— aparecen nombrados pero no
enlazados, así que no generan enlaces rotos ni pendientes.

Consecuencia práctica: el índice no es navegable desde Obsidian y el grafo del vault
sólo muestra las 5 aristas que salen de `Home.md`. No es un error —el contenido llegó
así y no se edita— pero es algo a considerar cuando se escriban esos documentos.

---

## 5. Ajustes de Obsidian

Todos los pedidos de la Tarea 5 quedaron aplicados por archivo de configuración.
**Ninguno requiere ajuste manual.**

`.obsidian/app.json`:

```json
{
  "promptDelete": false,
  "attachmentFolderPath": "09 - Templates/attachments",
  "useMarkdownLinks": false,
  "newLinkFormat": "shortest",
  "userIgnoreFilters": ["99 - Archive/"]
}
```

| Pedido | Clave | Valor |
|---|---|---|
| Adjuntos en `09 - Templates/attachments` | `attachmentFolderPath` | ruta creada, con `.gitkeep` |
| Enlaces internos como wikilink | `useMarkdownLinks` | `false` |
| Ruta relativa más corta posible | `newLinkFormat` | `"shortest"` |
| Excluir `99 - Archive/` de búsquedas | `userIgnoreFilters` | `["99 - Archive/"]` |
| Carpeta de plantillas | ver abajo | `09 - Templates` |

**La carpeta de plantillas no vive en `app.json`.** Es configuración del plugin core
*Templates*, así que se creó `.obsidian/templates.json` con `{"folder": "09 - Templates"}`.
El plugin ya estaba habilitado en `core-plugins.json`. No es una limitación: el ajuste
quedó aplicado, sólo que en el archivo que corresponde.

**Verificación pendiente de tu parte:** Obsidian lee estos archivos al iniciar. Si la
aplicación estaba abierta durante la construcción, puede sobrescribirlos con su estado
en memoria al cerrarse. Conviene cerrar y reabrir el vault, y confirmar en Ajustes que
los cinco valores están donde corresponde.

**Sobre `userIgnoreFilters`:** oculta `99 - Archive/` de búsquedas, quick switcher,
grafo y sugerencias de enlace. **No** impide que un `[[...]]` resuelva hacia ahí — ver
sección 4.1.

---

## 6. Decisiones tomadas por cuenta propia

**Las dos ambigüedades de fondo —qué hacer con `ESTADO_ACTUAL.md` y con la carpeta
vacía `11 - ADR/`— se consultaron antes de ejecutar y se resolvieron con tu
instrucción.** Nada de contenido se redactó, completó ni interpretó.

Quedan cuatro decisiones menores, todas de procedimiento, ninguna sobre contenido ni
estructura:

**6.1 — En qué commit entró cada cosa.** El prompt especifica tres mensajes de commit
(Tareas 2, 4 y final) pero las Tareas 1, 3 y 5 no tienen commit propio. Las agrupé con
el commit especificado más cercano:

| Commit | Contiene |
|---|---|
| `chore: archivar vault inicial` | `.gitignore` + `.obsidian/` original + todo `99 - Archive/` |
| `feat: vault base con ADR-000, 001 y 002` | estructura de carpetas + los 7 archivos nuevos + `aliases` |
| `chore: reporte de construccion` | `.obsidian/app.json`, `.obsidian/templates.json` y este reporte |

**6.2 — Identidad de git.** El repositorio no tenía `user.name` ni `user.email`, y
tampoco hay configuración global en la máquina. Usé `franbincovich <franbincovich@gmail.com>`
sólo para estos tres commits, sin escribir nada en tu configuración. **Conviene que lo
fijes vos** antes del próximo commit, o git va a fallar:

```
git config user.name "Fran Bincovich"
git config user.email "franbincovich@gmail.com"
```

**6.3 — `.gitkeep` en `09 - Templates/attachments`.** La Tarea 3 pide `.gitkeep` en las
carpetas vacías de la lista de 11. `attachments` no está en esa lista —viene de la
Tarea 5— pero queda vacía y git no versiona directorios vacíos, así que sin `.gitkeep`
la carpeta de adjuntos desaparecería al clonar. Apliqué el mismo criterio.

**6.4 — `99 - Archive/` sin `.gitkeep`.** No lo lleva porque no está vacía.

**Sin `.gitkeep`, con contenido:** `00 - Home`, `01 - Master Plan`, `08 - ADR`,
`09 - Templates`, `99 - Archive`.
**Con `.gitkeep`, vacías:** `02 - Architecture`, `03 - Agent Framework`,
`04 - Knowledge Management`, `05 - Infrastructure`, `06 - Standards`, `07 - Projects`,
`09 - Templates/attachments`.

---

## 7. Resumen para acción

Tres cosas quedan abiertas y ninguna la resolví por mi cuenta:

1. **`[[README]]` de `Home.md` es ambiguo** por la colisión de nombre entre `README.md`
   y `99 - Archive/README.md`. Es la única falla funcional del vault. Renombrar el del
   Archive lo cierra.
2. **`README.md` de la raíz no tiene frontmatter**, contradiciendo la regla que él mismo
   enuncia. Es uno de los 7 archivos que no puedo editar.
3. **Fijar la identidad de git** antes del próximo commit.
