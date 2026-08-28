# `fixtures/defectos-conocidos/`

Material para `tests/test_qa_contra_defectos.py`. **Nada de acá se escribió a mano.**
Todo salió del `factory.db` real el 2026-08-28, copiado verbatim del evento que lo
registró.

| Archivo | Sale de | Qué es |
|---|---|---|
| `plan-0001-u1.json` | evento 21, corrida `cd812322`, `iteracion_producida` | la unidad U1 del `PLAN-0001`, con sus dos criterios |
| `plan-emailvalidator-u1.json` | evento 67, corrida `957795bd`, `iteracion_producida` | la unidad U1 del `PLAN-EMAILVALIDATOR-001`, con su único criterio |
| `entrega-1a4fc044/` | evento 39, corrida `1a4fc044`, `entrega_producida` | los cuatro archivos que el Developer entregó para esa unidad |
| `entrega-6e131d4c/` | evento 75, corrida `6e131d4c`, `entrega_producida` | ídem, para la otra |

Las dos entregas fueron **aceptadas** por el verificador estructural en su primera
iteración, y las dos fueron producidas con modelo (`claude-sonnet-5`), no con `--stub`.

Se reproducen leyendo el evento y volcando `entrega.archivos[].contenido` a disco. Si
alguna vez hay que rehacerlo, ese es el procedimiento: nunca reescribir el JavaScript.

## Por qué hay que copiarlo y no leerlo del `factory.db`

El Operational State vive fuera del repo y no está versionado. Un test que lo leyera
pasaría o fallaría según qué corridas tenga la máquina, y desde ADR-017 el contenido de
las entregas nuevas ya no viaja en el evento. Acá el material queda fijo y auditable
contra el registro por el número de evento.

## Lo que *no* está acá, a propósito

**El único rechazo real del registro no sirve como defecto de QA.** Está explicado en el
encabezado de `tests/test_qa_contra_defectos.py`, sección "Lo que el registro no tiene".
Leerlo antes de agregar un caso creyendo que falta.
