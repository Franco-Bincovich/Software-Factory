---
tipo: adr
estado: aceptado
aprobado: 2026-08-28
version: 1.0
owner: CEO
actualizado: 2026-08-28
adr: [ADR-003, ADR-004, ADR-005, ADR-010, ADR-014, ADR-016, ADR-017]
aliases: [ADR-018]
---

# ADR-018 — Verificación sustantiva: el QA Agent

## Contexto

La verificación que la Fábrica ejecuta hoy comprueba **forma**: que los archivos
declarados estén, que la sintaxis compile, que se cumplan las reglas mecánicas.
`verificador_entrega.py` lo dice en su primera línea —"no ejecuta nada de lo que
verifica"— y sus veinte reglas son de presencia, forma y correspondencia con el
plan.

Lo que ninguna de ellas comprueba es que el código **haga lo que el plan pidió**.
Es la distinción del punto 4 de ADR-005: la estructural detecta forma, la
sustantiva detecta fallo silencioso y divergencia entre lo declarado y lo
implementado. R1 —nadie verifica de verdad lo que producen los agentes— sigue
abierta por esa mitad.

ADR-016 resolvió el obstáculo que bloqueaba construirla: dejó decidida la
frontera de ejecución —JavaScript autocontenido sobre Node, sin red, sin salir
del directorio de la unidad, con límite de tiempo y sin instalar nada— y exigió
que el límite fuera **mecánico y previo**. Esa regla existe: es **V5**, y hoy
rechaza por regla el entregable que declare dependencias, que sea una dependencia
instalada o que no se resuelva solo.

Es decir: la capacidad de ejecutar está decidida y su puerta está construida.
**Falta el agente que la use.** Éste es ese agente.

### Qué se verificó antes de escribir esto

**1. ADR-005 difirió esto por nombre y no lo cerró nadie.** Su sección "no
resuelve" dice: "**No resuelve** quién es el agente verificador ni cómo se compone
con el productor. Eso es ADR-007 y V0.3" (`ADR-005:145-147`). ADR-007 no existe, y
su hueco está reservado para otra cosa: el modelo organizacional en Departamentos
y Roles, según `ADR-008:171`, `Agent Framework.md:28` y el punto 11 de la
Secuencia de decisión (`Project Master Plan:151-153`).

Este ADR cierra el **quién** y el **cómo se compone**, que es la parte que V0.3
consume. El modelo organizacional sigue diferido y sigue siendo ADR-007.

**2. Los criterios de aceptación que la Fábrica escribió no son ejecutables como
están.** Medido contra `factory.db` el 2026-08-28, sobre los tres planes
producidos: **11 criterios, los 11 con procedimiento distinto**.

| Qué manda hacer el `procedimiento` | Criterios |
|---|---|
| Ejecutar el artefacto | 6 |
| Ejecutar o inspeccionar **los tests que entregó el Developer** | 5 |

De los 6 que ejecutan el artefacto, **3 nombran un intérprete de Python** —"Ejecutar
en un intérprete Python: `from validador import es_email_valido`"— que queda fuera
de la frontera de ADR-016, y **1 compara contra "el resultado esperado indicado en
esta lista"** sin que la lista esté en el criterio. Quedan **2 de 11** que un QA
podría ejecutar tal como están escritos.

Los 5 restantes mandan correr `pytest`, "el comando del test runner configurado en
el proyecto", o abrir el archivo de pruebas y contar los casos. Los cinco apuntan
al artefacto que el productor entregó como prueba de sí mismo.

Ese es el hallazgo que ordena las decisiones de abajo: **el problema de QA no es
sólo ejecutar, es contra qué**. Un QA que se limitara a obedecer el
`procedimiento` declarado ejecutaría los tests del Developer en cinco de once
casos y no verificaría nada.

## Opciones consideradas

**A. QA que lee el código y dictamina sobre su calidad.** Descartada para V0.3, no
por mala sino por ser **otro agente**: otro contrato, otra salida, otro criterio
de terminación. Construir los dos a la vez deja los dos sin probar, y el que hace
falta ahora es el que cierra R1.

**B. QA como segunda pasada del verificador estructural**, con más reglas de
forma. Descartada: no aporta nada que la primera pasada no haya visto. Reglas
mecánicas más finas siguen siendo mecánicas.

**C. QA que ejecuta y compara resultados contra lo esperado.** Elegida.

## Decisión

### 1. QA verifica resultados, no código

El QA Agent **ejecuta el entregable y compara la salida contra lo esperado**. No
lee el código para opinar sobre su calidad, su estilo o su diseño.

Lo que queda afuera queda afuera por decisión, no por olvido: el QA de código es
otro agente y no es V0.3. Si se construyen dos a la vez, ninguno de los dos queda
probado, y el que cierra R1 es éste.

### 2. Hace dos cosas, y las dos son necesarias

**(a) Ejecuta los criterios de aceptación que el plan declara para la unidad.** Es
el punto 1 de ADR-005 puesto a funcionar: los criterios viajan en la tarjeta de la
unidad justamente para ser ejecutados, y hasta hoy los ejecutaba una persona
abriendo `pruebas.html`.

**(b) Ejecuta pruebas propias.** Sin esto, QA no aportaría nada que el plan no
hubiera anticipado: verificaría exactamente lo que el Requirement Agent supo
prever, que es la definición de un segundo verificador estructural con más pasos.

El punto (b) es el que hace que QA valga. El punto 3 es el que impide que se
vuelva ingobernable.

### 3. El límite de las pruebas propias: los bordes de lo pedido

**QA prueba los bordes de lo que el plan pidió, nunca capacidades que el plan no
incluyó.** Si el plan declaró algo fuera de alcance, QA no puede exigirlo.

El motivo es concreto y es un modo de falla, no una preferencia. Sin ese límite el
Developer entra en un **bucle imposible**: cada reintento pasa las pruebas de la
vuelta anterior y falla pruebas nuevas que nadie pidió, hasta que se agota el techo
de iteraciones. No es un bucle que se rompa mejorando el código, porque el blanco
se mueve. Es la peor forma de gastar el presupuesto: pagando reintentos contra un
requerimiento que nunca se escribió.

El `fuera_de_alcance` del plan y el `restricciones.alcance_excluido` —los dos
campos que el plan ya declara— son vinculantes para QA en el mismo sentido en que
lo son para el Developer.

### 4. QA no confía en los tests que entregó el Developer

El Developer escribió el código **y** sus tests. Si el código está mal, los tests
lo acompañan: pasan porque fueron escritos contra la misma comprensión equivocada.
Es el defecto de REV-001 que ADR-005 usa como caso fundacional —tests unitarios
que pasaban sobre un tercio de la función muerta— y es exactamente lo que la
autoevaluación produce.

QA ejecuta contra **los criterios del plan** y contra **los suyos**. Los tests del
entregable son un artefacto del Developer, sujetos a verificación como cualquier
otro; no son el instrumento con el que se verifica.

Esto tiene una consecuencia inmediata sobre lo que la Fábrica ya escribió: los
cinco criterios medidos arriba que mandan correr el test runner del proyecto
**delegan el veredicto en el productor** y no son ejecutables por QA en esos
términos. Ver el punto 5.

### 5. Un criterio que no se puede ejecutar se declara, no se juzga

Un criterio que QA no puede comprobar mecánicamente se marca **"no verificable
mecánicamente"** y escala al Gate. QA no lo evalúa por juicio, no lo aproxima y no
lo da por cumplido.

La alternativa —que QA opine— reintroduce por la ventana lo que ADR-005 punto 2
sacó por la puerta: un criterio evaluado por juicio deja de ser binario y de tener
procedimiento, y su veredicto no se puede auditar.

**La cantidad de criterios no verificables por corrida es una señal sobre el
Requirement Agent, no sobre el Developer.** Si son muchos, el que está escribiendo
criterios que nadie puede comprobar es quien produce el plan, y castigar al
Developer por eso es leer mal el dato. Por eso **se registra como métrica del
Gate**: quien decide mira, junto al veredicto, cuánto de lo prometido no se pudo
comprobar.

La medición de arriba dice que esa métrica no va a ser cero: hoy daría 9 de 11.

### 6. Cuándo corre y con qué techos

**Por unidad, después del verificador estructural y antes del Gate de salida.** Si
QA rechaza, el Developer reintenta, con el mismo bucle de corrección que ya existe.

El orden no es arbitrario. La estructural es la puerta de la sustantiva —es la
consecuencia que ADR-016 declara en "lo que introduce"—: V5 rechaza antes de que
nada se ejecute, y ejecutar un entregable que no pasó la forma sería ejecutar sin
frontera.

**Los techos son los que ya existen. No se crean techos por agente.** Un techo por
agente convierte el presupuesto en una suma de límites locales que nadie puede
leer junta, y deja de estandarizar lo que ADR-010 estandarizó. QA consume del
mismo techo de la cadena que el resto.

### 7. QA y el verificador estructural son capas distintas, y las dos dejan veredicto

**Los dos veredictos se registran.** QA no revierte al verificador estructural ni
lo reemplaza: uno aprueba la **forma** y el otro el **fondo**, y una entrega
necesita los dos.

Que queden los dos registrados es lo que permite responder después la pregunta que
importa —¿esto se aprobó porque estaba bien hecho o porque estaba bien formado?—.
Un solo veredicto agregado la vuelve incontestable.

### 8. Qué produce

Una **tabla**: qué se verificó, con qué procedimiento, y **cumple o no cumple**.

**Sin porcentajes de cumplimiento.** Un 80% no dice si lo que falta es lo trivial o
lo esencial, y su única función real es hacer presentable un rechazo. Es la misma
razón por la que ADR-005 punto 2 exige que un criterio sea binario: un criterio
que admite grados no decide nada.

Los incumplimientos van en **el mismo formato que ya usa el verificador de
entregas** —`{regla, archivo, detalle}`—, para que el bucle de reintento del
Developer funcione igual y no haya que enseñarle a leer dos formas de rechazo.

### 9. Qué recibe

Por ADR-014 punto 4 —lo que no se entrega, se inventa—, el paquete de QA lleva
**todo lo necesario para decidir y nada que tenga que adivinar**:

- **El plan**, para saber qué se pidió y qué quedó fuera de alcance.
- **Los criterios de su unidad**, que son contra lo que juzga.
- **El depósito de la entrega**, que desde ADR-017 es donde el contenido existe:
  el evento sólo lleva ruta, rol y hash.

Un QA que tuviera que salir a buscar el artefacto no verifica una entrega: verifica
lo que encontró. Y por ADR-003, lo que un agente lee se declara, no se descubre.

## Consecuencias

**Lo que habilita.** V0.3. La verificación sustantiva de ADR-005 punto 4 deja de
ser una definición sin mecanismo, y la consecuencia que su punto 5 asume
explícitamente —que entre V0.1 y V0.2 la fábrica puede aprobar artefactos con
defectos del tipo REV-001— empieza a cerrarse. El Gate de salida deja de ser el
único control sustantivo.

**Lo que cuesta.** Una etapa más por unidad, con su costo y su tiempo dentro del
mismo techo. Rechazos que antes no existían: la Fábrica va a reintentar más y
entregar menos, y eso es el resultado buscado, no un efecto lateral.

**Lo que introduce.** Un veredicto nuevo en el registro y una métrica nueva en el
Gate —los criterios no verificables mecánicamente—. Y una obligación sobre el
Requirement Agent que hasta hoy no tenía consecuencia: escribir criterios que se
puedan ejecutar. La medición de este ADR dice que hoy no los escribe.

**Lo que no cambia.** El punto 3 de ADR-005 —el productor nunca es el
verificador—, que este ADR refuerza. La frontera de ADR-016, que no se amplía. Los
techos de ADR-010. El contrato de entregables. Y R7, que sigue abierta hasta V0.4.

## Decisiones que habilita

- La **Agent Definition del QA Agent**, que ahora tiene contra qué escribirse: sus
  trece campos, su paquete y su criterio de terminación se derivan de acá.
- Que el veredicto de `pruebas.html` deje de depender de que una persona abra un
  archivo, que es la condición de salida que el Contrato de Entrega declara en su
  línea 192.
- Una **métrica de calidad del Requirement Agent** medida sobre corridas reales y
  no sobre impresiones: cuántos de sus criterios resultan comprobables.

## Decisiones que no resuelve

- **El QA de código.** Calidad, estilo, diseño, deuda. Es otro agente y no es
  V0.3.

- **El aislamiento general de V0.4.** R7 sigue abierta con la misma fecha y el
  mismo dependiente. Este ADR consume la frontera angosta de ADR-016 y no la
  ensancha.

- **La verificación de entregables fuera de la frontera de ADR-016.** Lo que no es
  JavaScript autocontenido sobre Node no se ejecuta, y por lo tanto no se verifica
  sustantivamente. Incluye los criterios que hoy nombran un intérprete de Python:
  no se ejecutan, se declaran no verificables mecánicamente por el punto 5.

- **Cómo QA deriva sus pruebas propias de los bordes de la unidad.** El punto 3
  fija el límite —los bordes de lo pedido, nunca capacidades nuevas—; el
  procedimiento para encontrarlos es implementación y se decide al construirlo.

- **Qué hace el Gate con la métrica de criterios no verificables.** Se registra
  para que quien decide la mire. Si alcanza un umbral que dispare algo por sí sola
  es una decisión posterior, y con una sola corrida medida no hay con qué fijarlo.

- **El modelo organizacional en Departamentos y Roles.** Sigue diferido y sigue
  siendo ADR-007. Este ADR cierra quién verifica y cómo se compone con el
  productor; no abre dónde vive ese agente en una organización.

- **La enmienda al Contrato de Entrega** que ADR-016 dejó pendiente —declarar el
  lenguaje y la autocontención de V0.3 en adelante—. Sigue pendiente y este ADR
  tampoco la hace.
