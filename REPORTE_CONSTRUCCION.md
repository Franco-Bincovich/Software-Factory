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

---

## Correcciones 2026-07-31

Segunda pasada. Cierra los tres puntos abiertos de la sección 7 e incorpora ADR-003.
Nada de contenido se redactó ni interpretó: ADR-003 se transcribió literal.

### Qué se cambió

**Corrección 1 — colisión de README.**
`99 - Archive/README.md` → `99 - Archive/Archive (archivado).md`, con `git mv` para
preservar el historial. Ya no hay dos archivos `README.md` en el vault.

**Corrección 2 — regla de frontmatter en `README.md` de la raíz.**
La línea «Un documento sin frontmatter se considera inválido» se reemplazó por la
regla de exención para `00`–`07`, reportes de raíz y `99 - Archive`. Con esto quedan
cerradas las violaciones 1 y 2 de la sección 3.4: el `README.md` de la raíz y el
material del Archive ya no incumplen nada, porque dejaron de estar alcanzados.
Se agregó además la convención **Un solo README** a la sección de convenciones,
ubicada junto a las demás reglas de nombres de archivo.

**Corrección 3 — índice navegable.**
Las 17 filas de las seis tablas del índice del `Project Master Plan` pasaron a
wikilink en la columna *Documento*. Las columnas *Estado* y *ADR que lo sustenta* no
se tocaron: las menciones a `Agent Framework`, `Architecture` y `Technology Stack`
que aparecen ahí siguen siendo texto plano, como corresponde.

**Corrección 4 — ADR-003.**
Se creó `08 - ADR/ADR-003 - Contrato de agente.md` con el contenido literal: 158
líneas, 13 secciones, los 13 campos obligatorios del contrato. Frontmatter completo
con `aliases: [ADR-003]` tal como venía dictado. Se agregó `[[ADR-003]]` a la lista
de decisiones de `00 - Home/Home.md`.

### Verificación de `[[README]]`

**Resuelve sin ambigüedad.** `[[README]]` desde `00 - Home/Home.md` apunta a un único
destino, `README.md` de la raíz. El escaneo de nombres duplicados sobre los 21
archivos `.md` del vault da cero colisiones.

Estado completo de los enlaces del vault nuevo: **8 resueltos, 0 ambiguos.** Los 8
son los 2 `[[Project Master Plan]]` y el `[[README]]` de `Home.md`, los 3 enlaces a
ADRs por nombre completo, el `[[ADR-003]]` por alias, y el autoenlace del Master Plan.
Los cuatro alias —`ADR-000`, `ADR-001`, `ADR-002`, `ADR-003`— resuelven bien.

### Enlaces no resueltos en el índice: 16, no 15

**Esperado en el prompt: 15. Real: 16.** No es un error de la ejecución sino una
discrepancia de conteo que viene de los documentos mismos, y conviene resolverla.

Los números reales:

| Medición | Valor |
|---|---|
| Filas en las seis tablas del índice | **17** |
| Documentos que ya existen | 1 (`Project Master Plan`) |
| Wikilinks que no resuelven | **16** |

Los 16 no resueltos: `Vision`, `Objectives`, `Scope`, `Principles`, `Roadmap`,
`Decision Making`, `Architecture`, `Technology Stack`, `Agent Framework`,
`Autonomy and HITL`, `Verification`, `Knowledge Management`, `Infrastructure`,
`Security`, `Standards`, `Development Methodology`.

Son enlaces no resueltos intencionales, como pedía la Tarea 3: Obsidian los muestra
en otro color y el índice funciona como indicador de avance de la Fase 0. No se creó
ninguno de esos archivos.

**El "15" no aparece sólo en el prompt.** También está en dos documentos del vault:

- `Project Master Plan.md`, línea 19: «Documentos aprobados: 0 de 15.» Deberían ser 17.
- `ADR-002 - Estructura documental`: «un índice de quince completo», y su tabla de
  documentos lista 17.

**No corregí ninguno de los tres.** El conteo correcto es 17 documentos en el índice,
pero cambiarlo es contenido, y en el caso de ADR-002 es además un ADR ya emitido: por
la regla del propio ADR-000, un ADR no se edita, se supera. Queda para tu decisión si
esto se arregla con una errata en el Master Plan o si amerita un ADR.

### Correcciones a este mismo reporte

La sección 4.3 decía «los 11 documentos que todavía no existen» y a continuación
listaba 16 nombres. El número correcto es 16; el «11» venía del índice del vault viejo.
La sección 4.3 quedó además superada por la Corrección 3: ya no es cierto que el índice
no sea navegable.

### Puntos menores, para tu conocimiento

**Identidad de git.** No la configuré ni la pasé por línea de comandos, como pediste.
Los tres commits de esta pasada quedaron con la identidad que git dedujo sola del
sistema: `Franco Bincovich Granada <franbincovich@MacBook-Pro-de-Franco.local>`. Ese
mail no existe, es el hostname de la máquina. Los tres commits de la primera pasada
tienen `franbincovich@gmail.com`. **El historial quedó con dos autores distintos para
el mismo trabajo.** Conviene que fijes la identidad y decidas si reescribís los
últimos tres commits.

**Estilo del enlace a ADR-003.** Se agregó `[[ADR-003]]` literal, como indicaba el
prompt. Los otros tres de esa lista usan el nombre completo: `[[ADR-000 - Fundacion
del conocimiento]]`. Funciona igual —el alias resuelve— pero la lista quedó con dos
estilos mezclados. No lo uniformé.

**`Archive (archivado).md` y la convención de notas de carpeta.** La nueva convención
dice que las notas de carpeta se nombran `<Carpeta> - nota.md`, lo que daría
`Archive - nota.md`. El nombre aplicado es el que indicaste explícitamente en la
Corrección 1. Está en `99 - Archive`, que la nueva regla de frontmatter declara
material exento, así que la contradicción es menor. Sin cambios.

### Commits de esta pasada

```
fabf201  fix: resolver colision de README y precisar regla de frontmatter
a2a8f16  feat: indice del Master Plan navegable
7444822  feat: ADR-003 contrato de agente
```

---

## Cierre 2026-07-31

Estado final tras la reescritura de historial. Lo escrito arriba refleja el estado al
momento de cada pasada y no se corrige.

- Discrepancia de conteo: corregida. El índice tiene 17 documentos. Project Master Plan
  y ADR-002 actualizados; ADR-002 se editó por estar en estado 'propuesto'.
- Doble autoría del historial: resuelta. Identidad unificada en los ocho commits.
- Los SHAs citados en las secciones anteriores de este reporte corresponden al historial
  previo a la reescritura y ya no existen. Se conservan como registro de lo que se hizo,
  no como referencia navegable.
- Bundle pre-reescritura: descartado deliberadamente. La reescritura no alteró contenido.

---

## ADR-004 2026-07-31

Incorporación de ADR-004 y actualización del Master Plan. Append-only según la
convención de evidencia del README.

### Qué se creó

`08 - ADR/ADR-004 - Modelo de control.md`, transcripto literal: 203 líneas, 17
secciones, los 6 criterios del piso obligatorio. Frontmatter completo con
`adr: [ADR-000, ADR-001, ADR-003]` y `aliases: [ADR-004]` tal como venía dictado.

### Qué se actualizó

**`00 - Home/Home.md`.** `[[ADR-004]]` agregado al final de la lista de decisiones.

**`01 - Master Plan/Project Master Plan.md`**, tres cambios:

| Ubicación | Antes | Después |
|---|---|---|
| Tabla `03 - Agent Framework`, fila `Autonomy and HITL` | `ADR pendiente: modelo de control` | `[[ADR-004]]` |
| Registro de riesgos, R3 | `Abierto — mitigación en ADR de control` | `Mitigado parcialmente — ADR-004. Persiste mientras exista un solo rol humano aprobador.` |
| Secuencia de decisión, puntos 1 y 2 | sin marca | `— cerrado por ADR-003` y `— cerrado por ADR-004` |

### Validación de enlaces

| Medición | Resultado |
|---|---|
| Archivos `.md` en el vault | 22 |
| Nombres de archivo duplicados | 0 |
| Alias duplicados | 0 |
| Wikilinks que resuelven | 10 |
| Wikilinks ambiguos | **0** |
| Wikilinks no resueltos | 16 |

Los dos enlaces nuevos resuelven: `[[ADR-004]]` desde `Home.md` y desde el índice del
Master Plan, ambos a `08 - ADR/ADR-004 - Modelo de control.md`. Los cinco alias
—`ADR-000` a `ADR-004`— resuelven sin colisión.

Los 16 no resueltos son los mismos documentos pendientes del índice, sin cambios
respecto de la pasada anterior. Siguen siendo intencionales.

### Decisión de formato tomada por cuenta propia

**Cómo marcar «cerrados» los puntos 1 y 2 de la Secuencia de decisión.** El prompt pedía
marcarlos pero no fijaba notación. Usé el sufijo `— cerrado por ADR-NNN`, que replica el
estilo de anotación con raya que el propio documento ya usa en el registro de riesgos.
Es la única elección de forma de esta pasada. Si preferís tachado, negrita o una columna
de estado, se cambia.

### Observaciones, sin cambios aplicados

**La fila `Agent Framework` quedó desactualizada.** Sigue diciendo `ADR pendiente:
contrato de agente`, pero ese ADR ya existe: es ADR-003. Es la misma situación que la
fila `Autonomy and HITL` tenía antes de esta pasada. No estaba en el alcance del prompt.

**El estilo de la columna ADR quedó mezclado.** `Autonomy and HITL` ahora referencia
`[[ADR-004]]` como wikilink, mientras `Project Master Plan` y `Decision Making` siguen
con `ADR-002` y `ADR-000` en texto plano. Se aplicó lo indicado de forma literal. Los
tres son ADRs existentes, así que los tres podrían ser wikilink.

### Commits de esta pasada

```
63b8138  feat: ADR-004 modelo de control
```

El segundo commit de la pasada, `docs: actualizar indice y registro de riesgos`,
incluye también esta sección del reporte.

---

## Referencia RRHH 2026-08-01

Incorporación del primer proyecto de referencia y ampliación de ADR-002 para admitirlos.
Append-only según la convención de evidencia del README.

### Qué se incorporó

Nueva carpeta `07 - Projects/_reference/hr-karstec/`, con dos archivos:

| Archivo | Qué es |
|---|---|
| `ANALISIS_REFERENCIA.md` | 1.156 líneas. Análisis descriptivo de solo lectura del repositorio `VideCoding/RRHH`, en 12 secciones. Copiado sin editar. |
| `hr-karstec - nota.md` | Nota de referencia: qué es el material, fecha, ruta de origen, que no fue producido por la plataforma y que no es normativo. |

`.obsidian/app.json`: `07 - Projects/_reference/` agregado a `userIgnoreFilters`, junto a
`99 - Archive/`.

**El nombre de la carpeta es `hr-karstec`, no `rrhh`.** Lo determinó el punto 3 de las
verificaciones previas — ver abajo.

### Qué se editó de ADR-002

Se editó por estar en estado `propuesto`, conforme a la regla de mutabilidad que el README
declara desde la pasada anterior.

| Ubicación | Cambio |
|---|---|
| Tabla de carpetas, fila `07` | Descripción reemplazada: incorpora el subdirectorio `_reference` y declara que su contenido no es normativo. |
| Sección **Decisión**, al final | Bloque nuevo **Proyectos de referencia**: dónde viven, que son evidencia y no norma, que no se citan como fundamento, y que toda conclusión vinculante exige un ADR propio. |
| Frontmatter | `actualizado: 2026-07-31` → `2026-08-01`. |

`version` no se tocó: no se pidió.

### Resultado de las cuatro verificaciones previas

**1. `.git 2` — la premisa del prompt era incorrecta. Git funciona.**
El repositorio tiene un `.git/` real y operativo: `git status` responde, rama `main`,
working tree limpio, upstream configurado. `.git 2/` existe pero es un **directorio vacío,
cero entradas** — un artefacto de copia del Finder que quedó *al lado* del repositorio, sin
reemplazarlo. No interfiere: git no lo mira porque no se llama `.git`. **Consecuencia: el
análisis de historial sí fue posible** y está en la sección 8 del informe (176 commits, mayo
a julio de 2026). No se renombró ni se arregló nada.

**2. `CLAUDE.md` — leído completo, 692 líneas.**
Resumido en la sección 6.2 del informe, con sección propia. Es el archivo más relevante del
repositorio para lo que estamos haciendo: documentación escrita específicamente para que un
agente trabaje sobre ese código. Lo distintivo de su forma —jerarquía declarada de fuentes de
verdad, documentos obsoletos marcados en vez de borrados, advertencias contra correcciones
plausibles, inventario de deuda con números medidos y fecha, y quince reglas operativas
numeradas— está desarrollado ahí.

**3. Nombre real del proyecto: `HR Karstec`.**
`RRHH` es el nombre del repositorio y de la carpeta; `HR Karstec` es el del producto. Los dos
conviven en todo el repositorio. Evidencia en cinco documentos, incluidos los encabezados de
`CLAUDE.md`, del README y de ambos archivos de dependencias.

**Hallazgo asociado: ningún manifiesto de paquete declara el nombre del proyecto.** No hay
`package.json` en la raíz, el único es el del frontend y se llama literalmente `"frontend"`,
y el `pyproject.toml` del backend fue eliminado a propósito porque rompía el build de la
plataforma de deploy. El nombre vive en la documentación, no en la configuración.

Por eso la carpeta se llama **`hr-karstec`** y no `rrhh`, y la nota
**`hr-karstec - nota.md`**, siguiendo la convención `<Carpeta> - nota.md` del README.

**4. `migracionAWS/` — mezcla de código y documentación. No es infraestructura como código.**
21 archivos: 4 documentos Markdown, 7 módulos Python con sufijo `_NEW`, 3 migraciones SQL
numeradas 075–077, y 7 archivos de bytecode compilado. Estado: staging aislado, **no
ejecutado y no en producción** — existe para escribir el código del destino sin tocar el
backend vigente.

**No hay infraestructura como código en ninguna parte del repositorio**: verificado, sin
Terraform, CloudFormation, CDK, Serverless, Dockerfile ni docker-compose. Lo que hay es un
plan escrito y el código de aplicación que ese plan necesita; el aprovisionamiento es manual.

### Confirmación de saneamiento

**El informe no contiene datos sensibles ni credenciales.** Verificado por barrido automático
sobre el archivo final, con cero coincidencias en:

| Categoría | Resultado |
|---|---|
| Credenciales, claves, tokens | ninguna |
| Valores de variables de entorno | ninguno — solo los 18 **nombres** de `.env.example` |
| Identificadores de proyecto de proveedores cloud | ninguno |
| URLs de despliegue y dominios | ninguna |
| Nombres de personas | ninguno |
| Datos de negocio (dotación, nombres de empresas cliente, contenido de lotes) | ninguno |

Ningún `.env` real se abrió en ningún momento: solo `.env.example`, y de ahí únicamente los
nombres de variables. El informe declara su propio saneamiento en el encabezado, y su sección
11 enumera de forma explícita qué no se pudo determinar.

**El repositorio de origen quedó intacto:** working tree limpio, cero cambios, HEAD sin
mover. No se modificó, creó ni borró nada, y no se ejecutaron tests, builds ni instalaciones.

### Observación menor, sin cambios aplicados

`07 - Projects/.gitkeep` sigue en su lugar aunque la carpeta ya no está vacía. Es inofensivo
—git simplemente versiona un archivo vacío de más— pero contradice el criterio con que se
puso. No lo borré: no estaba en el alcance.

### Commits de esta pasada

```
42b0512  docs: ADR-002 admite proyectos de referencia
```

El segundo commit, `docs: incorporar analisis de referencia RRHH`, incluye la carpeta de
referencia, el cambio de `.obsidian/app.json` y esta sección del reporte.
