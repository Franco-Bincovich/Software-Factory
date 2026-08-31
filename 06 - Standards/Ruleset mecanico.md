---
titulo: Ruleset mecánico
tipo: contrato
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-005]
aliases: [Ruleset mecánico, Ruleset]
---

# Ruleset mecánico

## Propósito

El subconjunto de la Constitución Técnica que una máquina puede verificar sin
juicio. Es a un artefacto de código lo que las nueve reglas del Contrato del Plan
de Trabajo son a un plan.

## Alcance

Cubre las reglas que se comprueban leyendo el código, sin ejecutarlo y sin
interpretar intención. **No cubre** las que exigen criterio —si un service tiene
demasiadas responsabilidades, si un nombre es claro, si una decisión de
arquitectura es correcta—. Esas quedan para la verificación sustantiva y para el
Gate humano.

## Autoridad

**Este documento es derivado.** La Constitución Técnica es la norma; esto es su
proyección mecánica.

Si difieren, **manda la Constitución** y este documento está desactualizado.
Cuando la Constitución cambie, este se regenera — no se parchea a mano.

---

## R1 — Límites de tamaño

Se cuentan líneas del archivo, sin excluir comentarios ni líneas en blanco.

| Tipo de archivo | Límite |
|---|---|
| Router / Page | 80 |
| Controller | 100 |
| Service | 150 |
| Repository | 100 |
| Componente React | 150 |
| Custom Hook | 80 |
| Schema / Types | 200 |
| Cualquier otro | 200 |

El tipo se deriva de la carpeta. Superar el límite es incumplimiento, sin
excepción no documentada.

## R2 — Capas: importaciones prohibidas

| Capa | No puede importar ni contener |
|---|---|
| Router | Acceso directo a la base. Lógica de negocio |
| Service | El framework HTTP. SQL literal. El ORM |
| Repository | Lógica de autorización |
| Integration | Decisiones de dominio |
| Component | Llamadas HTTP directas |

Comprobable: se analizan los imports y se buscan patrones de query fuera de
`repositories/`.

## R3 — Patrones prohibidos en el código

| Patrón | Dónde |
|---|---|
| `print(` / `console.log(` | Todo el proyecto |
| Interpolación de variables dentro de un string SQL | Todo el proyecto |
| Lectura del entorno fuera de `config/settings.py` | Todo el proyecto |
| `DELETE FROM` sobre tablas con borrado lógico | Migraciones y repositories |
| Secretos literales | Todo el proyecto, tests y fixtures incluidos |

La detección de secretos es **léxica y por lo tanto parcial**: reconoce formatos
conocidos y nombres de variable sospechosos, no un secreto guardado con nombre
inocente.

## R4 — Errores

Todo error levantado desde un service o un repository usa la clase de error
tipada de la aplicación, con `message`, `code` y `status_code`.

Los códigos son `UPPER_SNAKE_CASE`, en inglés.

Existe un único handler global de errores.

**Comprobable parcialmente:** que se use la clase y que el código respete el
formato, sí. Que el mensaje no revele estructura interna, no — eso es juicio.

## R5 — Configuración

`config/settings.py` es el único archivo que lee variables de entorno.

`.env` está en `.gitignore` desde el primer commit.

`.env.example` existe y declara **todas** las variables que `settings.py` usa. Un
desfasaje entre ambos es incumplimiento.

## R6 — Base de datos

Toda query usa parámetros. Cero concatenación.

Toda migración es un archivo numerado en `/migrations`, sin saltos en la
numeración.

Toda tabla con datos de usuario declara su mecanismo de aislamiento. **No existe
la opción de ninguno**: si el proyecto no declaró variante en `ARCHITECTURE.md`,
es incumplimiento.

## R7 — Logging

Prohibido loguear: contraseñas en cualquier forma, tokens completos, claves de
API, datos personales en texto plano.

Formato estructurado con `timestamp`, `level`, `message`, `module`.

`DEBUG` no aparece en código que llegue a producción.

## R8 — Tests

Todo service nuevo entra con: un test del camino feliz, un test por cada rama de
error que puede levantar, y un test de aislamiento si toca datos de tenant.

**Un service sin tests es incumplimiento**, no una observación.

Los fakes tienen que poder desmentir: devolver estados distintos, contar llamadas
y lanzar excepciones. **Comprobable parcialmente** — que el fake tenga esas
capacidades, sí; que el test las use bien, no.

## R9 — Commits

Formato: `tipo: descripción corta en presente e imperativo`.

Tipos válidos: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`.

Un commit no mezcla `refactor` con `fix`. Comprobable por heurística: un commit
`fix` que toca más archivos de los que el arreglo justifica se marca para
revisión, no se rechaza.

Prohibidos: mensajes vacíos de contenido —`wip`, `cambios`, `arreglar bug`—.

## R10 — Diff limpio

Antes de cerrar una entrega, el diff no contiene: secretos, `print(` o
`console.log(` de depuración, archivos fuera del alcance de la tarea, ni `.env`.

## R11 — Formateadores

`ruff format` y `prettier` **no se corren sobre código existente**. Comprobable
de la forma más directa: un commit cuyo diff toca cientos de líneas de formato
sin cambio de comportamiento es incumplimiento.

Un proyecto que arranca de cero puede adoptarlos, y entonces la decisión está en
su `DECISIONES.md`.

---

## Lo que este ruleset **no** puede verificar

Se declara explícitamente para que nadie confunda pasar el ruleset con estar
bien.

| Regla de la Constitución | Por qué no es mecánica |
|---|---|
| Un service con demasiadas responsabilidades | Exige juicio sobre el dominio |
| Nombres claros y sin abreviar | Exige juicio |
| El mensaje de error no revela estructura interna | Exige juicio |
| La división de un archivo es por responsabilidad | Exige juicio |
| Los cuatro estados de UI implementados | Exige ejecutar la interfaz |
| El fake efectivamente desmiente | Exige analizar el test |
| El código hace lo que el requerimiento pedía | Es verificación sustantiva |

**Pasar las once reglas no significa que el artefacto esté bien.** Significa que
no tiene los defectos que una máquina puede ver. Es exactamente la misma
limitación que tienen las reglas 2 y 5 del Contrato del Plan de Trabajo, y la
razón por la que la verificación sustantiva de V0.3 existe.

---

## Excepciones

Una regla se incumple **solo** si la excepción queda escrita en el
`DECISIONES.md` del proyecto, con fecha, motivo y alcance.

**Una excepción no documentada es un error, no una decisión.**

El verificador lee ese archivo y no marca incumplimiento sobre lo que esté
declarado ahí. Es lo que evita que el ruleset se vuelva algo que todos ignoran.

## Decisiones tomadas

1. Este documento es derivado y la Constitución manda si difieren.
2. Se regenera cuando la Constitución cambia; no se parchea.
3. Las reglas parcialmente comprobables se declaran parciales.
4. Una excepción documentada en `DECISIONES.md` suprime el incumplimiento.
5. Pasar el ruleset no equivale a estar bien.

## Decisiones abiertas

1. **Cómo se deriva el tipo de archivo cuando la carpeta no lo dice.** Hoy se
   infiere de la estructura; un archivo fuera de la estructura canónica no tiene
   límite asignado.
2. **Cuándo se regenera.** Manualmente al cambiar la Constitución. Automatizarlo
   es posterior a V1.
3. **Umbral de la heurística de R9.** Cuántos archivos de más justifican marcar
   un commit. Se calibra con datos.

## Impacto en otros documentos

[[Constitución Técnica]] — es su fuente. [[Verification]] — este ruleset es la
verificación estructural aplicada a código, análoga a las nueve reglas del Plan
de Trabajo. **QA Agent** (V0.3) — lo consume. [[Standards]] — las convenciones
del proyecto interno; este ruleset es para el software producido.
