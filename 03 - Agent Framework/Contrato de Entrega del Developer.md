---
titulo: Contrato de Entrega del Developer
tipo: contrato
estado: aceptado
aprobado: 2026-08-26
version: 1.0
owner: CEO
actualizado: 2026-08-26
adr: [ADR-003, ADR-004, ADR-005, ADR-009, ADR-011]
aliases: [Contrato de Entrega del Developer, Entrega del Developer, Entrega]
---

# Contrato de Entrega del Developer

Artefacto de construcción de V0.2. Es el equivalente para código del [[Contrato
del Plan de Trabajo]]: aquel fija qué forma tiene lo que devuelve el Requirement
Agent, éste fija qué forma tiene lo que devuelve el Developer Agent. Deriva de
ADR-003, ADR-005 y ADR-009. No forma parte de los dieciocho documentos del
índice de Fase 0: es un contrato operativo, no un documento normativo de diseño
estratégico.

## Propósito

Fijar qué es una Entrega: la salida del Developer Agent. El Plan de Trabajo es
lo que entra; la Entrega es lo que sale. Es el segundo punto de contacto de la
cadena y el primero donde lo que viaja es código, así que su forma determina qué
puede verificarse después sin abrir una conversación con quien lo produjo.

## Alcance

Define la estructura, las reglas de validez, las prohibiciones y el caso de no
entrega. No define quién produce la Entrega ni cómo: eso es la Agent Definition
del Developer. Tampoco define la verificación sustantiva del código —si el
código está bien, no si está completo—, que llega en V0.3 con el QA Agent.

---

## Dónde vive una Entrega

**En el Operational State y en el directorio de trabajo, no en el Vault.** Una
entrega es el resultado de una ejecución concreta: responde "qué se produjo",
que es un hecho, no una norma. Aplica la prueba del punto 1 de ADR-011 — si se
regenerara desde cero se perdería información irrecuperable, porque el modelo no
produce dos veces el mismo código.

El registro de la entrega —qué unidad, qué archivos, qué supuestos— es un hecho
de la corrida. Los archivos producidos quedan en el directorio de trabajo
declarado. Lo que vive en el Vault es este contrato. Las entregas que se
produzcan, no.

## La entrega es inmutable

Una entrega registrada no se edita. Si el código cambia —porque la verificación
lo rechazó, o porque la unidad se volvió a ejecutar—, se produce una entrega
nueva que declara a cuál sucede. Es el punto 3 de ADR-011: los hechos no se
editan, se suceden.

Sin esta regla la verificación no significa nada: no se puede verificar un
artefacto que cambia mientras se lo verifica, y no se puede rastrear qué versión
del código fue la que pasó.

---

## Estructura

### Forma de la entrega

El Developer devuelve **un objeto JSON con tres campos**. Ninguno admite vacío
salvo donde se aclara.

1. **Unidad.** El identificador de la unidad de trabajo que ejecutó, tal como lo
   declara el plan. Uno solo: una entrega corresponde a una unidad.
2. **Archivos.** La lista de archivos producidos, cada uno con su ruta relativa
   y su contenido completo.
3. **Supuestos.** Lo que el plan no definía y el agente resolvió por su cuenta.
   Lista, posiblemente vacía.

**Nada más.** Sin texto explicativo antes ni después, sin comentarios al margen,
sin preámbulo, sin resumen de lo que hizo. La entrega no se lee: se valida. Todo
lo que un validador no puede comprobar es ruido que ocupa el lugar de lo que sí.

### Archivo válido

Cada archivo de la lista tiene ruta y contenido, y las dos cosas son estrictas.

**Ruta siempre relativa, nunca absoluta.** Una ruta absoluta ata la entrega a la
máquina donde se produjo y convierte un artefacto trasladable en uno que solo
sirve ahí.

**Sin `..` en ninguna parte de la ruta.** Ni al principio, ni en el medio, ni
disfrazado dentro de un segmento. Una ruta con `..` es una escritura fuera del
directorio de trabajo escrita de otra manera, y eso está prohibido más abajo.

**Contenido completo, nunca fragmentos.** El archivo se escribe tal cual viene,
sin combinarlo con nada anterior. Están prohibidos los marcadores del tipo
`// resto igual`, `...`, `// sin cambios`, o cualquier variante que delegue en
el lector la reconstrucción del archivo. Un contenido parcial obliga a quien lo
recibe a interpretar, e interpretar es exactamente lo que el contrato existe
para evitar.

### Correspondencia con el plan

Cada archivo se ata a la unidad que lo pidió.

**Si la unidad declaró un artefacto esperado, ese archivo tiene que estar.** El
campo 6 del Plan de Trabajo dice qué produce la unidad y dónde queda depositado;
una entrega que no lo trae no ejecutó la unidad, hizo otra cosa.

**Si entrega archivos adicionales, los declara auxiliares y dice por qué.** Un
auxiliar legítimo existe —un archivo de datos de prueba, un módulo que la lógica
necesita—, pero existe declarado. Un archivo que aparece sin justificación es
alcance que se agregó solo, y es contra eso que se comprueba la quinta regla
estructural de ADR-005.

### Supuestos

Mismo criterio que en el [[Contrato del Plan de Trabajo]]: lo que el plan no
definía y el agente resolvió por su cuenta se declara explícito y por separado,
nunca embebido en un comentario del código. Un supuesto escondido en el código
no es un supuesto declarado: es una decisión que alguien va a descubrir cuando
falle.

Un supuesto que, de ser falso, invalidaría la unidad entera no se declara:
dispara el criterio 6 del piso de ADR-004 —ambigüedad de requerimiento— y la
entrega no se produce. Se escala. Es lo que dice la sección "Cuando no puede".

---

## Los cuatro entregables de la cadena

Son cuatro archivos. No tres, no cinco.

| # | Entregable | Para quién | Cómo cambia |
|---|---|---|---|
| 1 | El código de la lógica | La cadena | Crece por agregado |
| 2 | El archivo de pruebas escrito | La automatización | Crece por agregado |
| 3 | `pruebas.html` | El humano que verifica | Se reescribe entero |
| 4 | `demo.html` | El humano que decide | Se reescribe entero |

Los dos primeros son los que ya existen en cualquier repositorio. Los dos
últimos son la condición para que un humano pueda cerrar un Gate sin instalar
nada ni leer código: uno le muestra que la lógica cumple sus criterios, el otro
le muestra la lógica funcionando.

**Son de la cadena, no de la unidad.** Por ADR-019 las unidades de un plan son
partes sucesivas sobre un mismo espacio de trabajo que crece, así que lo que se
exige es que los cuatro **estén presentes en el espacio** al cerrar cada parte, no
que cada parte los haya producido todos. Una parte cuyo trabajo es agregar
pruebas cumple con la lógica que dejó la anterior.

### Contenido y agregadores

La última columna de la tabla no es descriptiva: es la que hace que una parte
pueda agregar sin duplicar ni pisar.

**El código de la lógica y el archivo de pruebas son contenido, y crecen por
agregado.** Cada parte suma sus archivos y no toca los de las anteriores. Volver a
escribir un archivo de contenido que ya está en el espacio se rechaza, y por dos
motivos distintos según el caso: con el mismo contenido es **duplicar** —el
trabajo ya estaba hecho—, y con contenido distinto es **modificar lo aprobado**,
que ya tiene firma.

**`pruebas.html` y `demo.html` son agregadores, y se reescriben enteros.** Existen
para mostrar todo lo que hay en el espacio, así que la parte que agrega lógica los
tiene que rehacer o dejan de mostrar lo nuevo. Reescribirlos no es pisar trabajo
ajeno: es lo único que pueden hacer. Congelarlos sería congelar el resumen para
proteger el contenido.

**La distinción es por nombre y se declara acá**, no la decide quien verifica
mirando el archivo. Los agregadores son exactamente dos y se llaman `pruebas.html`
y `demo.html`. Todo lo demás es contenido, incluido un archivo que se llame
`index.html`. Una regla que adivinara qué es un agregador se equivoca el día que
alguien elija mal un nombre.

### `pruebas.html`

Se abre **en cualquier navegador, sin servidor y sin instalación**. Doble clic
sobre el archivo y listo.

Ejecuta **la lógica real** contra los casos declarados en los Acceptance
Criteria de la unidad, y muestra cuáles pasaron y cuáles no.

**Está prohibido que contenga resultados escritos a mano.** El veredicto de cada
caso sale de invocar la función y comparar contra lo esperado, nunca de un texto
fijo que dice "PASA". Un `pruebas.html` con resultados escritos es documentación
que miente, y miente en el peor lugar posible: en el que existe para no tener
que confiar.

### `demo.html`

Es una **interfaz operable por una persona**: entrada, acción y resultado en
pantalla, sin recargar la página.

Tiene que **cargar la misma función que usa `pruebas.html`**. Está prohibido
duplicar la lógica. Dos copias de una función divergen —siempre, y en silencio—
y a partir de ese momento la demo muestra un comportamiento que las pruebas no
comprueban.

### Cómo se carga la lógica

Los dos HTML cargan el archivo de lógica con un `<script src="...">` clásico. No
con `import`, no con `type="module"`: los módulos ES no cargan desde `file://` en
ningún navegador actual, y eso rompe el requisito de abrirse sin servidor.

### El lenguaje de la lógica en V0.2

De lo anterior se sigue que la lógica de una unidad tiene que ser cargable por
un navegador. **En V0.2 eso se cierra a favor de JavaScript.**

No es una preferencia de lenguaje: es lo que impone el mecanismo de
verificación. Si `pruebas.html` ejecuta la lógica real sin servidor, esa lógica
la tiene que poder cargar un navegador, y no hay una segunda manera de sostener
las dos cosas a la vez.

**El Patrón A del [[Technology Stack]] sigue vigente y sigue siendo el patrón por
defecto de lo que la fábrica produce.** Python + FastAPI, React + Next.js,
PostgreSQL: nada de eso cambia. Lo que este contrato fija es el lenguaje de la
unidad que el Developer Agent entrega en V0.2, con el único mecanismo de
verificación que V0.2 tiene —un humano abriendo dos archivos—, no la
arquitectura del producto que la fábrica construye.

**Se revisa cuando la fábrica pueda ejecutar código.** En cuanto exista un
verificador que corra las pruebas en vez de mostrárselas a una persona,
`pruebas.html` deja de ser el único camino al veredicto y el lenguaje deja de
estar determinado por el navegador.

---

## Prohibiciones

Denegación por defecto, según ADR-009. Estas cuatro no admiten excepción
declarable.

1. **No escribe fuera del directorio de trabajo declarado.** Ni por ruta
   absoluta, ni por `..`, ni por enlace simbólico.
2. **No abre conexiones de red.** Ninguna, para nada, tampoco para "consultar
   documentación".
3. **No lee variables de entorno.** Ahí viven las credenciales, y un agente que
   las lee las puede devolver dentro del contenido de un archivo.
4. **No modifica archivos que no declaró.** Lo que no está en la lista de
   archivos de la entrega no fue tocado. Si fue tocado y no está en la lista, la
   entrega miente sobre lo que hizo.

---

## Cuando no puede

**Si la unidad es ambigua o contradictoria, devuelve la entrega vacía con el
motivo. No adivina.**

Es el mismo criterio que `ProductorSinContexto` en T15: cuando falta lo que hace
falta para producir bien, el productor no produce algo peor, falla nombrando qué
faltó. Un agente que completa huecos por su cuenta produce código que parece
correcto y responde a un requerimiento que nadie pidió.

La entrega vacía es una entrega válida: declara la unidad, lista de archivos
vacía, y el motivo en el lugar de los supuestos. No es un error de
infraestructura y no se reintenta. Dispara el criterio 6 del piso de ADR-004 y
se escala a un humano.

---

## Reglas de validez

Una entrega que viole cualquiera de estas se rechaza sin llegar al Gate.

1. La entrega declara exactamente una unidad, y esa unidad existe en el plan.
2. Toda ruta es relativa y ningún segmento es `..`.
3. Todo archivo trae contenido completo, sin marcadores de omisión.
4. Si la unidad declaró un artefacto esperado, ese archivo está en la entrega.
5. Todo archivo que no es el artefacto esperado está declarado auxiliar y
   justificado.
6. Están los cuatro entregables —lógica, pruebas, `pruebas.html`, `demo.html`—
   presentes en el espacio de trabajo: los que trae la entrega más los que ya
   dejaron las partes anteriores.
7. `pruebas.html` y `demo.html` cargan el archivo de lógica; ninguno de los dos
   la reimplementa.
8. No hay dos archivos con la misma ruta.
9. La entrega no trae más campos que los tres declarados.
10. Ningún archivo de contenido repite una ruta que otra parte ya depositó. Los
    dos agregadores —`pruebas.html` y `demo.html`— son la única excepción, y lo
    son por nombre.

Las reglas 1 a 10 se comprueban leyendo la entrega, sin ejecutar nada. Eso es
deliberado y es lo que la sección siguiente explica.

---

## Lo que la Entrega deliberadamente no lleva

**El veredicto de sus propias pruebas.** El Developer no declara "los tests
pasan". Es el punto central de ADR-005: el productor nunca verifica lo que
produjo. Quien ejecuta dice si pasó.

**Métricas de cobertura.** Un número de cobertura sin criterio de qué había que
cubrir es una cifra con apariencia de información. Lo que había que cubrir son
los Acceptance Criteria de la unidad, y eso ya se comprueba mirando
`pruebas.html`.

**Un informe de lo que hizo.** El código es el informe. Una narración de las
decisiones que el agente tomó, aparte de los supuestos declarados, es texto que
nadie valida y que envejece contra el código en la primera corrección.

**Parches o diffs.** La entrega son archivos completos. Un parche exige un
estado previo exacto para aplicarse, y ata la entrega a un momento del
repositorio en vez de a la unidad del plan.

Los cuatro se incorporan si alguna vez tienen valor verdadero. Un campo que se
llena con un placeholder es exactamente el mecanismo por el que la documentación
empieza a mentir.

---

## Qué se ejecuta en V0.2: nada

**En V0.2 nada de la entrega se ejecuta automáticamente.**

El verificador revisa **estructura**: las diez reglas de validez de más arriba.
Comprueba presencia, forma y correspondencia con el plan. No corre las pruebas,
no abre los HTML y no evalúa si el código hace lo que dice.

El humano abre **los dos HTML**. `pruebas.html` le dice si la lógica cumple los
criterios de la unidad; `demo.html` le deja usarla. Con esas dos cosas resuelve
el Gate.

Que la verificación sea estructural y la sustantiva sea humana no es una
limitación provisoria mal disimulada: es lo que ADR-005 decide para este nivel.
La verificación sustantiva automática exige un agente verificador, y ese agente
es V0.3. Hasta entonces, los cuatro entregables existen precisamente para que la
parte humana del trabajo sea abrir dos archivos, no leer un repositorio.

---

## Ejemplo completo

Una unidad chica y real, con sus cuatro archivos, como molde.

**Unidad U1 del plan.** *Enunciado:* validar que un legajo tenga exactamente
cuatro dígitos. *Artefacto esperado:* `src/validar-legajo.js`. *Acceptance
Criteria:* dado `"4471"`, la función devuelve válido; dado `""`, devuelve
inválido con motivo `vacio`; dado `"44a1"`, inválido con motivo `no_numerico`;
dado `"447"`, inválido con motivo `longitud`. Se comprueba abriendo
`pruebas.html` y contando las filas en verde.

### La entrega

Así viaja, con el contenido de los archivos como strings y los saltos de línea
escapados. Se muestra un archivo entero para que la forma no quede en duda; los
otros tres van igual y su contenido está en los bloques siguientes.

```json
{
  "unidad": "U1",
  "archivos": [
    {
      "ruta": "src/validar-legajo.js",
      "rol": "artefacto_esperado",
      "contenido": "// Un legajo válido es exactamente cuatro dígitos.\nfunction validarLegajo(valor) {\n  if (typeof valor !== \"string\" || valor.trim() === \"\") {\n    return { valido: false, motivo: \"vacio\" };\n  }\n  const limpio = valor.trim();\n  if (!/^[0-9]+$/.test(limpio)) {\n    return { valido: false, motivo: \"no_numerico\" };\n  }\n  if (limpio.length !== 4) {\n    return { valido: false, motivo: \"longitud\" };\n  }\n  return { valido: true, motivo: null };\n}\n\nif (typeof module !== \"undefined\") {\n  module.exports = { validarLegajo };\n}\n"
    },
    {
      "ruta": "tests/validar-legajo.test.js",
      "rol": "artefacto_esperado",
      "contenido": "..."
    },
    {
      "ruta": "pruebas.html",
      "rol": "artefacto_esperado",
      "contenido": "..."
    },
    {
      "ruta": "demo.html",
      "rol": "artefacto_esperado",
      "contenido": "..."
    }
  ],
  "supuestos": [
    "El plan no dice qué hacer con espacios alrededor del valor. Se descartan antes de validar.",
    "El plan no fija los nombres de los motivos. Se usan vacio, no_numerico y longitud."
  ]
}
```

### `src/validar-legajo.js`

```javascript
// Un legajo válido es exactamente cuatro dígitos.
function validarLegajo(valor) {
  if (typeof valor !== "string" || valor.trim() === "") {
    return { valido: false, motivo: "vacio" };
  }
  const limpio = valor.trim();
  if (!/^[0-9]+$/.test(limpio)) {
    return { valido: false, motivo: "no_numerico" };
  }
  if (limpio.length !== 4) {
    return { valido: false, motivo: "longitud" };
  }
  return { valido: true, motivo: null };
}

if (typeof module !== "undefined") {
  module.exports = { validarLegajo };
}
```

Declarado como función global para que los dos HTML lo carguen con un `<script>`
clásico, y exportado además para que el archivo de pruebas lo consuma desde
Node. Un solo archivo, una sola definición.

### `tests/validar-legajo.test.js`

```javascript
const test = require("node:test");
const assert = require("node:assert");
const { validarLegajo } = require("../src/validar-legajo.js");

test("cuatro dígitos es válido", () => {
  assert.deepStrictEqual(validarLegajo("4471"), { valido: true, motivo: null });
});

test("vacío se rechaza por vacio", () => {
  assert.deepStrictEqual(validarLegajo(""), { valido: false, motivo: "vacio" });
});

test("con letras se rechaza por no_numerico", () => {
  assert.deepStrictEqual(validarLegajo("44a1"), { valido: false, motivo: "no_numerico" });
});

test("tres dígitos se rechaza por longitud", () => {
  assert.deepStrictEqual(validarLegajo("447"), { valido: false, motivo: "longitud" });
});
```

Un test por Acceptance Criterion. La correspondencia es uno a uno y por eso se
puede comprobar.

### `pruebas.html`

```html
<!doctype html>
<meta charset="utf-8">
<title>Pruebas — validarLegajo (U1)</title>
<script src="./src/validar-legajo.js"></script>

<h1>validarLegajo — Acceptance Criteria de U1</h1>
<p id="resumen"></p>
<table id="tabla" border="1" cellpadding="6">
  <tr><th>Entrada</th><th>Esperado</th><th>Obtenido</th><th>Veredicto</th></tr>
</table>

<script>
  // Los casos son los Acceptance Criteria de la unidad, tal como los declara
  // el plan. Nada más entra acá.
  const casos = [
    { entrada: "4471", esperado: { valido: true,  motivo: null } },
    { entrada: "",     esperado: { valido: false, motivo: "vacio" } },
    { entrada: "44a1", esperado: { valido: false, motivo: "no_numerico" } },
    { entrada: "447",  esperado: { valido: false, motivo: "longitud" } },
  ];

  let pasan = 0;
  const tabla = document.getElementById("tabla");

  for (const caso of casos) {
    const obtenido = validarLegajo(caso.entrada);   // se ejecuta la lógica real
    const paso = JSON.stringify(obtenido) === JSON.stringify(caso.esperado);
    if (paso) pasan++;

    const fila = tabla.insertRow();
    fila.style.background = paso ? "#d8f5d8" : "#f5d8d8";
    fila.insertCell().textContent = JSON.stringify(caso.entrada);
    fila.insertCell().textContent = JSON.stringify(caso.esperado);
    fila.insertCell().textContent = JSON.stringify(obtenido);
    fila.insertCell().textContent = paso ? "PASA" : "FALLA";
  }

  document.getElementById("resumen").textContent =
    pasan + " de " + casos.length + " criterios pasan.";
</script>
```

Ningún veredicto está escrito: cada uno sale de comparar lo que devolvió la
función contra lo que el criterio esperaba. Si la lógica se rompe, la página lo
muestra en rojo sin que nadie la toque.

### `demo.html`

```html
<!doctype html>
<meta charset="utf-8">
<title>Demo — validarLegajo (U1)</title>
<script src="./src/validar-legajo.js"></script>

<h1>Validar un legajo</h1>
<input id="entrada" placeholder="4471">
<button id="validar">Validar</button>
<p id="resultado"></p>

<script>
  document.getElementById("validar").addEventListener("click", () => {
    const r = validarLegajo(document.getElementById("entrada").value);
    document.getElementById("resultado").textContent =
      r.valido ? "Válido" : "Inválido — " + r.motivo;
  });
</script>
```

Carga el mismo `src/validar-legajo.js` que `pruebas.html`. No hay una segunda
copia de la regla de los cuatro dígitos en ninguna parte de la entrega.

---

## Decisiones tomadas

1. La Entrega es un objeto de tres campos —unidad, archivos, supuestos— y nada
   más.
2. Las rutas son relativas, sin `..`, y el contenido siempre completo.
3. Cada archivo se ata a la unidad; lo que excede el artefacto esperado se
   declara auxiliar y se justifica.
4. Toda unidad produce cuatro entregables: lógica, pruebas, `pruebas.html` y
   `demo.html`.
5. `pruebas.html` ejecuta la lógica real; los resultados escritos a mano están
   prohibidos.
6. `demo.html` carga la misma función que `pruebas.html`; duplicar la lógica está
   prohibido.
7. Fuera del directorio de trabajo, la red y las variables de entorno están
   cerrados por defecto.
8. Ante unidad ambigua o contradictoria, entrega vacía con motivo. No se adivina.
9. En V0.2 la verificación automática es estructural; la sustantiva la hace un
   humano abriendo los dos HTML.
10. En V0.2 la lógica de una unidad se escribe en JavaScript, porque
    `pruebas.html` la tiene que poder cargar un navegador. El Patrón A del
    Technology Stack no cambia; esta decisión se revisa cuando la fábrica pueda
    ejecutar código.

## Decisiones abiertas

1. **Serialización y esquema concreto de la Entrega.** Este contrato fija que
   debe existir una forma estructurada y validable, no cuál. Se cierra junto con
   el verificador de entregas.
2. **Qué ocurre con la entrega sucesora** cuando parte de los archivos de la
   anterior ya quedaron depositados. Es el mismo problema que el plan sucesor y
   se resuelve con él.
3. **Entregas que abarcan varias unidades.** Hoy una entrega es una unidad. Si
   el encadenamiento de V0.2 muestra que el ida y vuelta por unidad es caro, se
   revisa con datos de corridas, no antes.

## Impacto en otros documentos

[[Contrato del Plan de Trabajo]]: es la entrada de la que este contrato es la
salida. El campo 6 de una unidad —artefacto esperado— pasa a tener consumidor
real: la regla de validez 4 se comprueba contra él. [[Agent Framework]]: el
protocolo de traspaso deja de tener un solo artefacto que viaja; este contrato es
el segundo y debe absorberlo o referenciarlo, no reescribirlo. [[Verification]]:
la verificación estructural de V0.2 se aplica sobre las diez reglas de acá, y
`pruebas.html` es el procedimiento de comprobación de los criterios de la unidad.
[[Technology Stack]]: sin cambio — el Patrón A sigue siendo el patrón por defecto
de lo que la fábrica produce; lo que se fija acá es el lenguaje de la unidad
entregada, no la arquitectura del producto. [[Roadmap]]: V0.2 queda con su artefacto de salida definido; sin él, "código sin
intervención entre etapas" no tiene forma comprobable.
