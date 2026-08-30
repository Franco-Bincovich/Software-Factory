---
tipo: adr
estado: aceptado
aprobado: 2026-08-30
version: 1.0
owner: CEO
actualizado: 2026-08-30
adr: [ADR-003, ADR-005, ADR-010, ADR-014, ADR-016, ADR-018, ADR-019]
aliases: [ADR-020]
---

# ADR-020 — El lenguaje y la ruta son decisiones del plan, no prosa

## Contexto

El 2026-08-30 la corrida `68b6246f…` murió por iteraciones agotadas sin producir
un solo archivo aceptado. La causa no fue un defecto del Developer ni del
verificador: fue que **el plan comprometió un lenguaje que la Fábrica no sabe
producir, y nadie tenía cómo comprobar la contradicción**.

El Requirement Agent escribió, en `supuestos`:

> «Se asume que el lenguaje de implementación es Python y el framework de pruebas
> es pytest, dado que el pedido no especifica lenguaje ni herramientas.»

Es un supuesto razonable y está bien declarado. También es imposible: el
[[Contrato de Entrega del Developer]] cierra V0.2 a favor de JavaScript, y no por
gusto — `pruebas.html` ejecuta la lógica real sin servidor, así que un navegador
tiene que poder cargarla. El Requirement no lee ese contrato: su `vault_lectura`
son el Contrato del Plan de Trabajo y el Glosario. Supuso de buena fe sobre
información que no tenía.

### El lazo, medido

El plan fijó `artefacto_esperado` así:

> «Archivo de código fuente con la función de validación de email, depositado en
> el repositorio del proyecto **(ej. `src/validate_email.py`)**.»

`src/validate_email.py` era **un ejemplo**. C4 lo leyó como obligación. Las tres
iteraciones del Developer `2fb7feb6…` están en el registro y son el lazo entero:

| Iteración | Qué entregó | Qué se le rechazó |
|---|---|---|
| 1 | los cuatro entregables en JavaScript | `C4` — la unidad declara `src/validate_email.py` y la entrega no lo trae |
| 2 | lo mismo, más `src/validate_email.py` | `C5` (nadie pidió ese archivo), `C6` (falta la lógica del espacio), `R8` y `V3` (las pruebas no invocan nada) |
| 3 | vuelve a JavaScript | `C4` otra vez |

No hay entrega legal. C4 exige un `.py`; C6, R8 y V3 exigen JavaScript
ejecutable. El Developer osciló entre las dos hasta agotar el techo de ADR-010.

**Costó USD 0,365671** —0,045934 del Requirement y 0,319737 de las tres
iteraciones del Developer— para llegar a cero archivos aceptados.

### La misma falla, silenciosa, ya había pasado

`94cc2ae4…`, esa misma mañana, con el mismo defecto en el plan:

> «Se asume que la función se implementará en **Python** y las pruebas unitarias
> usando el framework estándar de pruebas del lenguaje (**unittest** o
> **pytest**) (…)»

Esa corrida **no murió: llegó a entregado**. El `artefacto_esperado` de sus dos
unidades no traía ejemplo de ruta, así que C4 no tuvo qué exigir. El Developer
entregó lo único que sabe hacer —`src/validar-email.js`,
`tests/validar-email.test.js`, `pruebas.html`, `demo.html`—, el verificador no
encontró nada que objetar, **el Gate de salida se aprobó a las 16:36:35** y la
evidencia se materializó en `entregas/94cc2ae4…`.

Una entrega en JavaScript firmada contra un plan firmado que decía Python. **No
es que el verificador falló**: la contradicción entre el lenguaje del plan y el
del contrato no era comprobable por nadie, y el Gate firmó encima.

Es el mismo patrón que el parseo silencioso de QA que ADR-018 arrastró: **la
falla ruidosa apareció después y por casualidad, y la silenciosa ya había pasado
sin que nadie la viera**. Lo que hizo visible a `68b6246f…` no fue la
contradicción —esa estaba en las dos— sino un detalle accidental de redacción:
que el ejemplo de ruta tuviera una barra.

### Por qué C4 se tragó un ejemplo y descartó una decisión

Hasta acá C4 sacaba rutas del texto de `artefacto_esperado` con una expresión
regular, y después filtraba: se quedaba con los tokens que tuvieran barra o
extensión `.js` / `.html`. El filtro no era un principio, era una protección por
forma, y erraba en las dos direcciones:

- `src/validate_email.py` **pasaba** —tiene barra— y se volvía vinculante, aunque
  el plan lo hubiera escrito precedido de «ej.».
- Un `validador.py` a secas **se descartaba en silencio** —sin barra, ni `.js` ni
  `.html`—, aunque fuera la ruta que el plan sí quería fijar.

**Ninguna expresión regular mejor arregla eso, porque la información no está en
el texto.** Un ejemplo y una decisión se escriben igual. Lo que faltaba no era
mejor parseo: era que el plan dijera cuál de las dos cosas estaba haciendo.

### La regla nueva, corrida hacia atrás contra el registro

Antes de escribirla se la evaluó sobre los siete planes que hay en `factory.db`:

| Corrida | Incumplimientos | Términos que la disparan |
|---|---:|---|
| `e531030f…` | 15 | `python`, `pytest`, `.py` |
| `68b6246f…` | 6 | `python`, `pytest`, `.py` |
| `94cc2ae4…` | 4 | `python`, `pytest`, `unittest` |
| `befbec37…` | 1 | `pytest` |
| `cd812322…` | 0 | — |
| `957795bd…` | 0 | — |
| `f3b9ea34…` | 0 | — |

**Cuatro de siete se habrían cortado en T7, antes de invocar al Developer.** No
es azar: es frecuencia, y es la respuesta a la pregunta de si esto se arregla
caso por caso.

`befbec37…` es el que más dice: ese plan **delegó** el lenguaje en `supuestos` en
vez de elegirlo, y aun así escribió `pytest` en el `procedimiento` de un
criterio. La contradicción se le pasaba entera al paso siguiente, que es el que
ejecuta el criterio. Por eso la regla mira los criterios y no sólo los supuestos.

## Opciones consideradas

**Para el lenguaje.**

- **A. Sólo en el prompt del Requirement.** Descartada. Es prosa pidiéndole al
  agente que no se equivoque, que es exactamente lo que ya pasó cuatro veces. Un
  plan inválido tiene que ser rechazable por máquina o vuelve.
- **B. Una regla del verificador de planes, con la lista en `verificador.py`.**
  Elegida.
- **C. Una regla que lea el lenguaje del Contrato de Entrega del Developer.**
  Descartada: acopla el verificador de planes al contrato del Developer por diez
  palabras. La desincronización se vigila con un test que compara los dos sin que
  ninguno importe al otro, el patrón que ya usa `test_conteos_declarados.py`.

**Para la ruta.**

- **i. Arreglar C4 para que no extraiga rutas de un ejemplo.** Descartada. Le
  pone un cartel al defecto: el mismo string sigue haciendo dos trabajos y se
  sigue confiando en que el agente escriba bien.
- **ii. Separar el campo en el Contrato del Plan.** Elegida. Es lo único que
  convierte «una ruta declarada es una decisión» en algo que el esquema
  garantiza.

## Decisión

### 1. El lenguaje de la Fábrica es un hecho, no un supuesto del plan

Mientras V0.2 esté cerrada a JavaScript, **el Requirement Agent no puede suponer
otro lenguaje**. No es una decisión de cada corrida: es una propiedad del
Developer, escrita en su contrato.

### 2. La regla 8 de T7 lo hace exigible

Un plan que nombra un lenguaje que la Fábrica no puede producir es **inválido**.
La regla se evalúa sobre `supuestos` y, por unidad, sobre `enunciado`,
`artefacto_esperado`, `ruta_artefacto` y las tres partes de cada criterio.

**El vocabulario es cerrado y declarado, no inferido.** `TERMINOS_AJENOS` y
`EXTENSIONES_AJENAS` viven en `verificador.py` y se prohíben término por término.
No se intenta adivinar el lenguaje de un plan: **una regla que adivina se
equivoca en silencio**, que es justamente el defecto que este ADR corrige. Un
plan que compromete Python sin nombrarlo —describiendo un `setup.py` sin decir
«Python»— pasa. Se prefiere el falso negativo: un falso positivo cuesta un plan
rechazado y una iteración pagada.

`LENGUAJE_DE_LA_FABRICA = "JavaScript"` está repetido en el código y no importado
del Vault, y un test del guardián falla el día que el Contrato y la constante
digan cosas distintas.

#### Los dos campos que la regla 8 no mira

`fuera_de_alcance` y `restricciones.alcance_excluido` quedan afuera a propósito.
En los dos, nombrar un lenguaje es **excluirlo**: «no se implementa en Python» es
una aclaración legítima, y prohibirla obligaría a escribir peor. El segundo
además se copia literal del pedido, así que rechazar el plan por su contenido
sería castigar al agente por obedecer.

### 3. `ruta_artefacto` es un campo del plan, obligatorio y anulable

`artefacto_esperado` dice **qué** produce la unidad y es prosa. `ruta_artefacto`
dice **dónde**, exactamente, y es lo único que C4 comprueba. Son dos campos
porque son dos cosas.

**Es obligatorio y admite `null`.** `null` significa «el plan no fija la ruta,
que la elija el Developer», y eso es una decisión. Omitir el campo no sería una
decisión, sería un olvido, y **las dos se leerían igual**. Por eso no se puede
omitir.

El prompt del Requirement prohíbe escribir rutas de ejemplo en la prosa. Es la
mitad blanda de la regla; la dura es que la prosa ya no obliga a nada.

### 4. C4 lee el campo y la compara entera

C4 deja de extraer rutas del texto. Y **compara la ruta completa, sin caer al
nombre de archivo**: antes `src/a.js` satisfacía a `lib/a.js`, y eso tenía
sentido cuando cada unidad trabajaba en su propio subdirectorio y el prefijo era
ruido. Con el espacio único de ADR-019 el prefijo es parte de la decisión, y
aceptar otro sería volver a convertir la ruta declarada en una sugerencia.

Con `ruta_artefacto` en `null` queda en pie la primera mitad de la regla —que
algo venga declarado como artefacto esperado—, que es la que no depende de saber
cuál.

## Consecuencias

**Lo que corta.** Un plan con lenguaje ajeno muere en T7, antes de que se invoque
al Developer. En `68b6246f…` eso habría ahorrado los USD 0,319737 de las tres
iteraciones y habría dejado un rechazo que el Requirement sabe corregir —el campo
9 de su Agent Definition— en vez de un escalamiento.

**Lo que cuesta.** Las reglas de T7 pasan de siete a ocho, y la octava es
parcial, como la 2 y la 5. Todo lo que declaraba «las siete reglas» —trece
afirmaciones registradas en el Vault y en el código— dice ahora ocho.

**Lo que ata a V0.2.** La regla 8 es correcta mientras el Contrato cierre el
lenguaje. El día que V0.3 abra un segundo lenguaje, la constante y la lista
cambian juntas y el test del guardián obliga a que el Contrato cambie con ellas.
Eso es deliberado: la regla envejece de forma ruidosa, no silenciosa.

**Lo que no cambia.** El Patrón A del [[Technology Stack]] sigue vigente: lo que
esta regla fija es el lenguaje de la lógica de una unidad en V0.2, no la
tecnología que la Fábrica sabe recomendar. Los planes ya firmados en el registro
quedan como están; ADR-011 no se toca y son la evidencia de esta decisión.

## Decisiones que habilita

- Una **medida de calidad del Requirement Agent** sobre el lenguaje, junto a las
  de ADR-018 punto 5 y ADR-019.
- Que C4 sea una regla **total** en vez de parcial, porque deja de interpretar
  prosa.
- Que el Developer reciba la ruta exigida como un dato aparte y nítido, en vez de
  tener que descubrirla adentro de una oración.

## Decisiones que no resuelve

- **Un plan que compromete un lenguaje sin nombrarlo sigue pasando.** Es el falso
  negativo elegido en el punto 2. La alternativa —inferir el lenguaje— se
  descartó por escrito y no se reabre sin evidencia de que el falso negativo
  cuesta más que el falso positivo.

- **La regla 8 no sabe si el plan es coherente consigo mismo.** Un plan que fija
  `ruta_artefacto: "src/algo.js"` y describe en el enunciado una arquitectura de
  servidor pasa las ocho reglas. Eso es verificación sustantiva del plan y sigue
  siendo trabajo del Gate humano.

- **Que el Requirement lea el Contrato de Entrega del Developer.** Se evaluó y no
  se hizo: agrandar `vault_lectura` mete el contrato entero en cada system prompt
  del Requirement para transmitir una frase. La frase viaja en el prompt de T7 y
  la regla la hace exigible. Si más adelante el Requirement necesita más del
  contrato que el lenguaje, la decisión se vuelve a mirar.

- **El resto de lo que ADR-016 dejó pendiente.** Este ADR declara el lenguaje del
  lado del plan. La autocontención de V0.3 en adelante sigue pendiente.
