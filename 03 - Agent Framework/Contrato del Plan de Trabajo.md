---
titulo: Contrato del Plan de Trabajo
tipo: contrato
estado: aceptado
aprobado: 2026-08-06
version: 1.1
owner: CEO
actualizado: 2026-08-26
adr: [ADR-003, ADR-004, ADR-005, ADR-010, ADR-011]
aliases: [Contrato del Plan de Trabajo, Plan de Trabajo]
---

# Contrato del Plan de Trabajo

Artefacto de construcción de V0.1, tarea T6. Deriva de ADR-005. No forma parte
de los dieciocho documentos del índice de Fase 0: es un contrato operativo, no
un documento normativo de diseño estratégico.

## Propósito

Fijar qué es un Plan de Trabajo: la salida del Requirement Agent y la entrada del
Developer Agent a partir de V0.2. Es el único punto de contacto entre ambos, así
que su forma determina qué puede pasar de un agente al siguiente.

## Alcance

Define la estructura, las reglas de validez y el ciclo de vida del artefacto.
No define quién lo produce ni cómo. Eso es la Agent Definition (T9).

---

## Dónde vive un Plan de Trabajo

**En el Operational State, no en el Vault.** Un plan es el resultado de una
ejecución concreta: responde "qué se decidió hacer", que es un hecho, no una
norma. Aplica la prueba del punto 1 de ADR-011 — si se regenerara desde cero se
perdería información irrecuperable.

Lo que vive en el Vault es este contrato. Los planes que se produzcan, no.

## El plan es inmutable

**Un Plan de Trabajo queda inmutable cuando pasa la verificación estructural y
ese veredicto queda registrado en el Operational State.** Desde ese evento no se
edita. Si el trabajo cambia, se produce un plan nuevo que declara a cuál sucede.
Coherente con el punto 3 de ADR-011: los hechos no se editan, se suceden.

Sin esta regla el traspaso no significa nada: el Developer Agent no puede
consumir un artefacto que puede cambiar mientras lo consume.

### Por qué el ancla es la verificación y no una firma

Hasta la versión 1.0 de este contrato el plan quedaba inmutable **al aprobarse en
el Gate de salida del Requirement Agent**. Ese Gate se suprime en V0.2 —aprobar
el plan y después aprobar la entrega que sale de él es aprobar dos veces lo
mismo—, así que el ancla se mueve al hecho observable que ya estaba debajo: el
veredicto de la verificación estructural, registrado con su corrida y su
iteración.

**Lo que se conserva es la propiedad, no el procedimiento.** Lo que la
inmutabilidad tiene que garantizar es una sola cosa: que exista un momento
identificable a partir del cual el plan no se toca, para que quien lo consume no
esté trabajando sobre algo que cambia. Una firma da ese momento. Un veredicto
registrado también, y además es comprobable por máquina y no depende de que
alguien esté disponible.

**Un plan que todavía no pasó la verificación no es inmutable: es un borrador.**
Se corrige, y de hecho el ciclo de reintento lo corrige. Que cada iteración
modifique el plan de la anterior no viola esta regla, porque la inmutabilidad
empieza en el veredicto válido y no antes. Esto no era explícito en 1.0 y
conviene que lo sea: la regla nunca prohibió iterar, prohibía editar lo ya
cerrado.

**El momento se corrió hacia atrás, no hacia adelante.** El plan queda cerrado
antes que en 1.0 —cuando pasa T7, no cuando alguien firma—, así que el período
durante el cual podía cambiar se acorta. La regla se endurece, no se afloja.

---

## Estructura

### Cabecera

Identificador del plan, estable y único. Identificador de la corrida que lo
produjo, según el punto 4 de ADR-011. Referencia al pedido de Intake que lo
originó. Plan al que sucede, si sucede a alguno. Estado.

### Restricciones heredadas del pedido

Los tres techos declarados —costo, tiempo, iteraciones— según ADR-010. Y el
**alcance excluido**: lo que el pedido dijo explícitamente que no entra. Se
copia literal, no se interpreta. Es contra esta lista que se comprueba la quinta
regla estructural de ADR-005.

### Unidades de trabajo

Cada unidad lleva seis campos obligatorios. Ninguno admite vacío.

1. **Identificador.** Único dentro del plan. Estable: no se renumera si se
   agrega o quita una unidad.
2. **Enunciado.** Una sola acción verificable. Si el enunciado necesita una
   conjunción para expresarse —"hacer X y validar Y"— son dos unidades. La regla
   es la misma que ADR-003 aplica al propósito de un agente.
3. **Acceptance Criteria.** Uno o más. Cada uno con las tres partes del punto
   siguiente.
4. **Dependencias.** Identificadores de otras unidades del mismo plan. Solo
   internas: una dependencia hacia algo que no está en el plan no es una
   dependencia, es un supuesto.
5. **Rastreo.** A qué parte del pedido responde esta unidad. Es lo que permite
   comprobar la cuarta regla estructural de ADR-005 sin interpretar intención.
6. **Artefacto esperado.** Qué produce la unidad y dónde queda depositado.

### Acceptance Criterion — las tres partes

Un criterio válido tiene las tres. Le falta una, no es un criterio.

- **Condición observable.** Qué se mira. No qué se pretende: qué se mira.
- **Resultado esperado.** Binario. Se cumple o no. Sin grados, sin "en gran
  medida", sin "razonablemente".
- **Procedimiento de comprobación.** Cómo se mira. Quién no escribió el plan
  tiene que poder ejecutarlo sin preguntar nada.

Ejemplo de criterio válido: *dado un archivo con dos filas de legajo 4471, la
salida reporta ambas con su número de fila. Se comprueba corriendo la herramienta
sobre el archivo de prueba y contando las filas del reporte.*

Ejemplo de criterio inválido: *maneja bien los duplicados.* No es observable, no
es binario y no dice cómo comprobarlo.

### Supuestos

Todo lo que el agente tuvo que asumir porque el pedido no lo decía. Se declaran
explícitos y por separado, nunca embebidos en una unidad de trabajo.

Un supuesto que, de ser falso, invalidaría el plan entero no se declara: dispara
el criterio 6 del piso de ADR-004 —ambigüedad de requerimiento— y el plan no se
entrega. Se escala.

### Fuera de alcance del plan

Lo que el plan deliberadamente no hace, incluso si el pedido podría sugerirlo.
Distinto del alcance excluido de la cabecera: aquel viene del pedido, éste es
decisión del agente y por lo tanto se justifica.

---

## Reglas de validez

Las cinco reglas estructurales de ADR-005, aplicadas a este artefacto. Un plan
que viole cualquiera se rechaza y vuelve al ciclo de corrección; no queda
cerrado, y por lo tanto tampoco queda inmutable.

1. Toda unidad de trabajo tiene al menos un Acceptance Criterion.
2. Todo Acceptance Criterion tiene las tres partes.
3. Toda dependencia apunta a una unidad que existe en el mismo plan.
4. Toda unidad declara su rastreo al pedido.
5. Ninguna unidad cae dentro del alcance excluido declarado.

Dos reglas adicionales propias de este contrato:

6. El plan no supera diez unidades de trabajo. Superarlo no es un error del
   agente: es señal de que el pedido era demasiado grande, y se escala.
7. No hay ciclos en el grafo de dependencias.

---

## Lo que el Plan de Trabajo deliberadamente no lleva

**Estimación de esfuerzo o duración por unidad.** No hay datos históricos para
estimar. Una estimación sin datos es una cifra inventada con apariencia de
información, y documentación que miente es peor que documentación ausente. Se
incorpora cuando existan corridas medidas.

**Asignación de agente.** En V0.1 no hay a quién asignar. Se incorpora en V0.2,
cuando exista el Developer Agent y el campo tenga valor verdadero.

**Prioridad.** El orden lo determina el grafo de dependencias. Una prioridad
además de las dependencias sería una segunda fuente de verdad sobre lo mismo.

Los tres se agregan cuando tengan valor verdadero, no antes. Un campo que se
llena con un placeholder es exactamente el mecanismo por el que la documentación
empieza a mentir.

---

## Forma canónica

La forma canónica de un Plan de Trabajo es **estructurada y validable
automáticamente contra este contrato**. La vista legible para personas es
derivada y nunca autoritativa: si difieren, manda la estructurada.

La serialización concreta es implementación y se decide al construir T7. Este
contrato fija que debe existir una forma estructurada, no cuál.

---

## Decisiones tomadas

1. Los planes producidos viven en el Operational State; solo este contrato vive
   en el Vault.
2. Un plan verificado es inmutable; se sucede, no se edita. Desde 1.1 el ancla
   es el veredicto registrado, no una firma.
3. Una unidad de trabajo es una sola acción verificable.
4. Un Acceptance Criterion sin las tres partes no es válido.
5. Las dependencias son internas al plan; lo externo es supuesto.
6. Esfuerzo, asignación y prioridad quedan fuera hasta que tengan valor
   verdadero.
7. La forma estructurada manda sobre la legible.

## Decisiones abiertas

1. **Serialización concreta.** Se cierra al construir T7.
2. **Qué ocurre con el plan sucesor** cuando parte del trabajo del plan anterior
   ya se ejecutó. Es problema de V0.2, cuando exista ejecución.

## Impacto en otros documentos

[[Agent Framework]] (pendiente): este contrato es su insumo directo y debe
absorberlo o referenciarlo, no reescribirlo. [[PLAN-V0.1]]: cierra T6 y define el
alcance exacto de T7. [[ADR-008]]: el corte de V1 puede ahora definir "entregado"
en términos de unidades de trabajo con criterios cumplidos.
