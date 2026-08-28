---
tipo: adr
estado: aceptado
aprobado: 2026-08-28
version: 1.0
owner: CEO
actualizado: 2026-08-28
adr: [ADR-003, ADR-004, ADR-005, ADR-008, ADR-009]
aliases: [ADR-016]
---

# ADR-016 — Frontera de ejecución para verificación sustantiva

## Contexto

La verificación actual es estructural: comprueba que los archivos existan, que la
sintaxis compile y que se cumplan las reglas mecánicas. `verificador_entrega.py`
lo dice en su primera línea de docstring —"**No ejecuta nada de lo que verifica**"—
y sus diecinueve reglas son todas de forma, presencia y correspondencia con el
plan.

Lo que no comprueba es que el código haga lo que el plan pidió. Es exactamente la
distinción del punto 4 de ADR-005: la verificación estructural detecta forma, la
sustantiva detecta fallo silencioso y divergencia entre lo declarado y lo
implementado. La segunda exige ejecutar el artefacto.

Y ejecutar código generado por un agente sin frontera es el hueco declarado en
**R7** —"Aislamiento entre proyectos y entre clientes", `05 - Infrastructure/Security.md:134`—,
cuya mitigación está fechada en V0.4 y depende de un workspace aislado que no
existe. ADR-008 punto 5 lo repite desde el otro lado: R7 no se mitiga en V1 y por
eso no puede haber clientes.

El cruce es el problema. **El aislamiento completo es V0.4 y el QA Agent es V0.3**
—ADR-005 punto 5 lo fecha ahí, y ADR-005 punto 4 declara que la verificación
sustantiva "requiere agente verificador"—. Sin resolver ese cruce hay dos salidas
y las dos son malas: o QA no se puede construir, o se construye sin verificar de
verdad y repite R1 con una capa más de ceremonia encima.

### Qué se verificó antes de escribir esto

**1. El Contrato de Entrega exige JavaScript, y sólo para V0.2.** La sección "El
lenguaje de la lógica en V0.2" (`Contrato de Entrega del Developer.md:175-183`) y
la decisión 10 (línea 496) cierran el lenguaje a favor de JavaScript, con el
motivo declarado: `pruebas.html` tiene que poder cargar la lógica sin servidor, y
eso lo impone el navegador, no una preferencia.

**El contrato no ata V0.3.** Al revés: la línea 192 declara la condición de
salida —"**Se revisa cuando la fábrica pueda ejecutar código.** En cuanto exista
un verificador que corra las pruebas en vez de mostrárselas a una persona,
`pruebas.html` deja de ser el único camino al veredicto y el lenguaje deja de
estar determinado por el navegador"—, que es precisamente lo que este ADR
habilita. Este ADR no le atribuye al contrato un alcance sobre V0.3 que el
contrato no reclama.

**2. La autocontención es emergente, no exigida.** Ningún documento normativo usa
la palabra ni escribe la regla. Se **sigue** de tres reglas que sí están escritas:

- carga por `<script src>` clásico, sin `import` ni `type="module"` (líneas 169-173);
- se abre "sin servidor y sin instalación" (línea 147);
- prohibición 2: no abre conexiones de red, "ninguna, para nada" (línea 206).

Pero **ninguna de las nueve reglas de validez la comprueba**, y
`verificador_entrega.py` no tiene regla equivalente: sus identificadores emitibles
son C0-C8, R1, R3, R8, P1-P3 y V1-V4, y ninguno mira dependencias declaradas.

**3. Ningún entregable actual declara dependencias.** Comprobado sobre las 12
corridas de `entregas/` y sobre `trabajo/`: cero `package.json`, cero
`node_modules`, cero `import`. Los 42 `require` son builtins —`node:test` ×14,
`node:assert` ×14— o rutas relativas al propio directorio de la unidad
(`../src/u1.js` ×12, `../src/es-email-valido.js` ×2).

El punto 3 es el que hace viable la decisión: la frontera coincide hoy con lo que
la Fábrica produce de hecho. El punto 2 es el que la hace peligrosa si se la deja
implícita, y es lo que la sección "El límite es mecánico" resuelve.

## Decisión

### 1. Frontera mínima para V0.3

La verificación ejecuta **únicamente entregables de JavaScript autocontenido**,
con Node, y bajo cuatro restricciones:

1. **Sin acceso a red.**
2. **Sin acceso al sistema de archivos fuera del directorio de la unidad.**
3. **Con límite de tiempo por ejecución.**
4. **Sin instalación de nada.**

Es la frontera **suficiente para lo que la Fábrica produce hoy** —el punto 3 de
arriba lo mide—, no un sandbox general, y no pretende serlo. Un sandbox general es
V0.4 y sigue siendo V0.4 después de este ADR.

La restricción es de la misma familia que las cinco condiciones de despliegue
local de ADR-008: contener la capacidad en el lugar más angosto posible antes de
concedérsela a nadie. Y hereda la postura de ADR-009: denegación por defecto sobre
todo recurso, y lo que no está declarado está prohibido.

### 2. El límite es mecánico

Un entregable que declare dependencias, requiera instalación, acceda a red o
escriba fuera de su directorio **se rechaza por regla antes de ejecutarse**. No se
intenta y se ve qué pasa.

Sin esa regla, el primer proyecto con dependencias se va a ejecutar igual y la
frontera va a existir sólo en el papel. Una frontera que depende de que el
contenido resulte inofensivo no es una frontera: es una expectativa.

**Y hoy la frontera se apoyaría en una propiedad que nadie verifica.** Ese es el
hallazgo del punto 2 de la verificación previa: la autocontención de los
entregables es emergente —se sigue de cómo se cargan los HTML y de la prohibición
de red—, pero ninguna regla la comprueba. La coincidencia del punto 3 es un hecho
observado sobre 12 corridas, no una garantía del sistema; el día que un plan pida
una unidad con una dependencia, nada la detiene.

**La regla que falta es exactamente ésa, y este ADR la exige como condición previa
a ejecutar nada.** El orden importa y no es negociable: primero la regla que
rechaza, después la ejecución. Al revés, la primera corrida con dependencias es la
que descubre que la frontera no estaba.

## Consecuencias

**Lo que habilita.** QA se puede construir ahora, contra defectos conocidos, sin
esperar infraestructura. La verificación sustantiva de ADR-005 punto 4 deja de ser
una definición sin mecanismo, y la consecuencia asumida en su punto 5 —que entre
V0.1 y V0.2 la fábrica puede aprobar artefactos con defectos del tipo REV-001—
empieza a cerrarse.

**Lo que cuesta.** La Fábrica **no puede aceptar pedidos cuyos entregables excedan
esa frontera** hasta que exista aislamiento real. Es una restricción sobre el
negocio, no sólo sobre el código, y se declara como tal: hay trabajo que no se
toma.

**Lo que introduce.** Una regla de rechazo nueva en la capa de verificación
estructural, que corre antes que cualquier ejecución. La verificación estructural
gana una responsabilidad: ser la puerta de la sustantiva.

**Lo que no cambia.** El punto 3 de ADR-005 —el productor nunca es el
verificador—, las prohibiciones del Contrato de Entrega, y el hecho de que R7
sigue abierta hasta V0.4. Este ADR no la mitiga: la esquiva por angostura.

## Decisiones que habilita

- El **QA Agent** y con él V0.3: la verificación sustantiva pasa a tener un
  entorno de ejecución definido contra el cual escribirse.
- Que el veredicto de `pruebas.html` deje de depender de que un humano abra un
  archivo, que es la condición de salida que el Contrato de Entrega declara en su
  línea 192.

## Decisiones que no resuelve

- **El aislamiento general de V0.4.** R7 sigue abierta con la misma fecha y el
  mismo dependiente —workspace aislado—. Esta frontera no la adelanta ni la
  reemplaza.

- **La ejecución de entregables con dependencias.** Queda prohibida, no resuelta.
  Es el mismo hueco que `Security.md` anota como "Revisión de dependencias antes
  de instalarlas", pendiente para antes de V1: instalar una dependencia es
  ejecutar código que nadie revisó.

- **Cualquier lenguaje distinto de JavaScript.** La frontera es de JavaScript
  sobre Node. Python, y con él el Patrón A del Technology Stack, queda afuera.

- **La enmienda al Contrato de Entrega.** El contrato declara el lenguaje sólo
  para V0.2 y no escribe la autocontención en ninguna de sus nueve reglas de
  validez. **Necesita una enmienda que declare el lenguaje y la autocontención de
  V0.3 en adelante, y este ADR no la hace.** Se nombra acá para que la regla
  mecánica del punto 2 tenga de dónde derivarse cuando se construya: hoy tendría
  que inventar su propio fundamento.
