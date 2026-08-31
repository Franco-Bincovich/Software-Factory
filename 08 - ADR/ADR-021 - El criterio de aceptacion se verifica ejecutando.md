---
tipo: adr
estado: aceptado
aprobado: 2026-08-30
version: 1.0
owner: CEO
actualizado: 2026-08-30
adr: [ADR-005, ADR-010, ADR-016, ADR-018, ADR-020]
aliases: [ADR-021]
---

# ADR-021 — El criterio de aceptación se verifica ejecutando, no delegando

## Contexto

El `procedimiento` de un Acceptance Criterion dice cómo se comprueba que la
unidad cumple. Desde ADR-018 quien lo comprueba es el QA Agent, y lo hace dentro
de la frontera de ADR-016: `node -e`, sin red, sin instalar nada.

El Requirement Agent viene escribiendo procedimientos que **delegan la
comprobación en un ejecutor que del lado de acá de la frontera no existe**:

> «Correr el comando de ejecución de pruebas del proyecto sobre el archivo de
> pruebas y verificar que el reporte final indique cero fallos.»

No hay comando que correr ni reporte que leer. El criterio no tiene ningún caso
posible, y no por un defecto del QA Agent: por cómo está escrito el criterio.

### Qué se verificó antes de escribir esto

Contra `factory.db`, el 2026-08-30. El registro tiene 8 planes producidos,
con 29 Acceptance Criteria entre todos.

| Medición | Valor |
|---|---|
| Planes con al menos un criterio que delega | **7 de 8** |
| Criterios que delegan | 7 de 29 |
| De ésos, los que **no nombran ninguna herramienta** | **5 de 7** |
| Corridas que llegaron a ejecutar uno con QA encendido | 3 |
| De ésas, las que murieron truncadas contra el techo | **2** |

Siete de ocho no es un desliz: es **el comportamiento por defecto del
Requirement**. Y es el mismo defecto que ADR-018 punto 5 ya había anotado con
otra cifra —"2 de 11 criterios ejecutables"— sin llegar a nombrar la causa.

### Por qué QA no puede resolverlo por su cuenta

Un criterio que pide correr los tests de la unidad no tiene caso legal, y el
motivo lo pone el propio contrato de QA: **los tests que entregó el Developer no
valen como evidencia**, porque son el productor declarando que su producto está
bien. Aunque QA pudiera ejecutarlos —y no puede—, un caso construido sobre ellos
no comprobaría nada.

Con lo cual el agente queda en un callejón: el criterio le pide algo que su
propio prompt le prohíbe contar como prueba. Las dos corridas que llegaron ahí
con QA encendido murieron igual, y de la peor manera —`7680cb8e…` y `3a5b789f…`
se truncaron contra el techo de 8.000 tokens de salida **sin producir un solo
caso**—.

### Los tres que entregaron bien, y por qué eso no es un consuelo

De los 7 planes que la regla nueva corta, **3 entregaron la unidad igual**. Hay
que decir cómo, porque la diferencia importa y no es la que uno supondría:

- **`94cc2ae4…`** corrió con QA encendido. Los dos criterios de su U2 salieron
  `no_verificable_mecanicamente`, el Gate de salida los recibió así —el evento
  `gate_abierto` lleva `"no_verificables": 2` en el sometimiento— y **se resolvió
  `aprobado`**. El Gate no fue engañado: vio el número y firmó.
- **`cd812322…`** y **`957795bd…`** corrieron con `qa: false`. Su criterio
  delegado no lo verificó nadie, ni siquiera para declararlo no verificable.

En los tres casos el software salió por la puerta con esa parte sin comprobar.
**El costo fue invisible, no inexistente**, que es la forma que este defecto
comparte con el de ADR-020: la falla ruidosa aparece después y por casualidad, y
la silenciosa ya venía pasando.

### La economía

| Camino | Costo |
|---|---|
| Dejarlo pasar — `7680cb8e…`, murió truncada | USD 0,3282 |
| Dejarlo pasar — `3a5b789f…`, murió truncada | USD 0,1435 |
| Rebotar el plan — una iteración del Requirement | **USD 0,07** (media de las 8) |

Y las dos primeras terminan además en escalamiento a una persona, que es el
recurso caro de la Fábrica. Rebotar cuesta entre 2 y 5 veces menos, y es
automático.

## Decisión

### 1. El procedimiento describe una ejecución observable

Un Acceptance Criterion es válido si su `procedimiento` dice **qué se invoca y
qué valor se espera**. No es válido si delega la comprobación en una herramienta
—un runner, un gestor de paquetes, el comando de pruebas del proyecto— o en un
reporte producido por otro.

La forma correcta ya existe en el registro y es la mayoría: 22 de los 29
criterios son de la forma "ejecutar la función con tal entrada y verificar que
devuelve tal valor". La decisión no inventa un estilo nuevo, fija el que ya
funciona.

### 2. La regla mira `procedimiento` y ningún otro campo

Se agrega como **regla 9** de validez del Contrato del Plan de Trabajo.

Ésta es la parte que hay que decir como decisión, porque es la que alguien va a
querer "completar" extendiéndola a `artefacto_esperado`. **No se extiende**, y el
motivo es que los dos campos dicen cosas distintas:

- `artefacto_esperado` describe **qué se produce**. Una unidad puede tener que
  entregar legítimamente un archivo de pruebas. Prohibir ahí la palabra sería
  prohibirle a la Fábrica producir tests.
- `procedimiento` describe **cómo se comprueba**, y el que comprueba es QA,
  atado a la frontera de ADR-016.

La diferencia se ve en una unidad sola: «entregar `pruebas.js` con al menos dos
casos» es un artefacto impecable, y «correr la suite y ver que dé cero fallos» es
un procedimiento imposible. La misma unidad, y sólo el segundo campo está mal.
Una regla que mirara los dos **rechazaría la unidad entera por la mitad que
estaba bien**.

Es también la diferencia con la regla 8, que sí mira varios campos: allá el
lenguaje ajeno contamina donde aparezca, porque el Developer no lo sabe producir
en ninguna parte. Acá el problema no es la herramienta: es **quién tendría que
correrla**.

### 3. La regla y el prompt van juntos, o no van

El prompt del Requirement Agent enseña la forma correcta del procedimiento, con
el contraejemplo explícito de la delegación.

No es redundancia con la regla. Con 7 de 8 planes afectados, **la regla sola no
es un filtro: es un portón cerrado**. Si el Requirement sigue escribiendo lo
mismo, cada corrida entra en un ciclo de rebotes hasta agotar el techo de
iteraciones de ADR-010 —un techo que se agota de verdad: `68b6246f…` murió así,
por otra causa pero por el mismo mecanismo—. Y la regla rebota **el plan entero,
no el criterio**: un plan con cinco criterios buenos y uno delegado se reescribe
completo, sin garantía de que los cinco buenos vuelvan iguales.

Al revés también falla: el prompt es mejora estadística y no garantía, y sin
regla el plan malo llega al Developer igual que hasta ahora.

## La lección general: una regla léxica empuja el defecto al circunloquio

Esto merece sección propia porque no es sobre esta regla. Es sobre **toda regla
mecánica apoyada en vocabulario**, incluida ésta.

La regla 8 de ADR-020 prohibió nombrar `pytest`. Funcionó: los planes dejaron de
decir `pytest`. **El defecto no desapareció — se mudó a la perífrasis.** De los 7
criterios que la regla nueva corta, **5 no nombran ninguna herramienta**: dicen
"el comando de ejecución de pruebas del proyecto", que significa exactamente lo
mismo y no la cortaba nadie.

Esto se midió al diseñar la regla 9, y el hallazgo cambió el diseño. Una lista de
comandos —`npm test`, `jest`, `npx`— corre contra los 8 planes del registro y
corta 2 criterios; los 2 ya los cortaba la regla 8 por decir `pytest` en el mismo
renglón. **Aporte neto: cero.** La regla que se iba a escribir no habría servido
para nada, y sólo se supo porque se midió antes de encenderla.

Lo que se lleva de acá:

1. **Una regla léxica se mide contra el registro antes de encenderse**, no
   después. La intuición sobre qué escriben los agentes es mala: acá estuvo mal.
2. **Prohibir un nombre no prohíbe la conducta.** Lo que hay que buscar es la
   forma de la conducta, no su vocabulario más obvio.
3. **La regla nueva hereda el mismo límite.** Prohíbe `runner`, `comando de
   ejecución de pruebas`, `suite de pruebas` y las herramientas de JavaScript. Un
   Requirement que escriba "se ejecuta el archivo de verificación del proyecto y
   se lee su salida" la esquiva. Por eso el punto 3 de la Decisión: el prompt no
   es un complemento del cinturón, es la mitad que ataca la conducta en lugar de
   la palabra.

## Consecuencias

**Lo que se gana.** Un criterio que llega a QA es un criterio que QA puede
instanciar. El defecto se corta en T7, que cuesta 0,07 y es automático, en lugar
de aguas abajo, donde cuesta entre 2 y 5 veces más y termina en una persona.

**Lo que cuesta.** Planes rechazados que antes pasaban: 7 de los 8 del registro
lo habrían sido. Tres de ellos habían entregado bien —con la salvedad del
Contexto, que es toda la salvedad—. La primera corrida después de esto va a
rebotar más que las anteriores, y eso es la regla funcionando, no un defecto.

**Lo que no cambia.** La frontera de ADR-016. El contrato de QA, incluida la
regla de que los tests del Developer no valen como evidencia. La inmutabilidad
del plan una vez cerrado: la regla corre antes, en T7.

## Decisiones que habilita

- Medir la calidad de un plan por la proporción de criterios ejecutables, que
  hasta acá no era una magnitud sino una impresión.
- Un Gate de salida que pueda mirar `no_verificables` como señal y no sólo como
  dato informativo, ahora que el número tiene una causa nombrada.

## Decisiones que no resuelve

- **El límite léxico de la propia regla 9**, enunciado arriba. Se acepta a
  sabiendas: es la mitad mecánica de una defensa de dos mitades.

- **El techo de 8.000 tokens de salida de QA.** Es el síntoma con el que se
  descubrió todo esto y sigue sin tocarse. Un criterio bien escrito no lo alcanza;
  si lo alcanzara con criterios buenos, sería otro problema y otro ADR.

- **Qué hace el Gate de salida con `no_verificables` distinto de cero.** Hoy es
  información en el sometimiento y la decisión es del CEO. Que `94cc2ae4…` se
  firmara con 2 muestra que la información sola no alcanza, pero convertirlo en
  bloqueo es una decisión de control y no de verificación.

- **Los criterios que piden inspección visual** —"abrir el archivo de pruebas y
  contar los casos"—. Hay 3 en el registro. No delegan en una herramienta, así que
  la regla 9 no los toca, y tampoco son ejecutables. Son un defecto vecino y
  distinto.
