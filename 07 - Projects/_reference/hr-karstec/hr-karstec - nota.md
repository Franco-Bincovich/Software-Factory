# hr-karstec — nota de referencia

## Qué es este material

`ANALISIS_REFERENCIA.md` es un análisis descriptivo, de solo lectura, del repositorio de
**HR Karstec**: una plataforma interna de gestión del ciclo de vida del empleado,
multiempresa, desarrollada para un equipo de recursos humanos.

Se lo incorpora como **referencia de horizonte**: el tipo de resultado que una plataforma de
desarrollo basada en agentes debería poder producir. Su sección más útil a ese fin es la 9,
que inventaría qué artefactos entrega un proyecto terminado.

## Fecha y procedencia

- **Fecha del análisis:** 2026-08-01.
- **Ruta de origen:** `VideCoding/RRHH` (repositorio local, rama `main`).
- **Estado del repositorio al momento de leerlo:** 176 commits, mayo a julio de 2026,
  working tree limpio. No se modificó nada: el análisis fue estrictamente de lectura.

## Qué NO es

**No fue producido por la plataforma.** Es un desarrollo humano previo, ajeno a la Software
Factory. No se lo tomó como salida de ningún Agent Run.

**No es normativo.** No es un template, no es un standard y no es una decisión. Es una
muestra de uno, y su forma no obliga a nada.

**No se cita como fundamento de una decisión.** Conforme a ADR-002, el material de
`07 - Projects/_reference/` es evidencia, no norma. Cualquier conclusión que se quiera volver
vinculante —una convención, un artefacto obligatorio, un criterio de completitud— debe pasar
por un ADR propio que la asuma como decisión del proyecto.

## Saneamiento

El informe fue producido bajo restricción explícita de no incluir credenciales, valores de
variables de entorno, identificadores de proyecto de proveedores cloud, URLs de despliegue,
nombres de personas ni datos de negocio. Donde un archivo importaba por su estructura pero
tenía contenido sensible, se describe la estructura y se omite el contenido.

## Exclusión de búsquedas

`07 - Projects/_reference/` está declarado en `userIgnoreFilters` de Obsidian, junto con
`99 - Archive/`. Es material de consulta: no debe aparecer en el autocompletado de enlaces
mientras se escriben los documentos del vault.
