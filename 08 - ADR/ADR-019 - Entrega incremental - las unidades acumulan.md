---
tipo: adr
estado: aceptado
aprobado: 2026-08-30
version: 1.0
owner: CEO
actualizado: 2026-08-30
adr: [ADR-005, ADR-010, ADR-014, ADR-015, ADR-016, ADR-017, ADR-018]
aliases: [ADR-019]
---

# ADR-019 — Entrega incremental: las unidades acumulan en vez de duplicar

## Contexto

Hoy cada unidad trabaja en su propio directorio y no puede ver a las otras. Una
unidad que necesita el artefacto de otra no tiene cómo alcanzarlo, así que lo
copia.

El aislamiento no es un descuido: lo imponen reglas escritas. **V5** y **C2**
—las que ADR-016 exigió como condición previa a ejecutar nada— rechazan por regla
cualquier ruta que salga del directorio de la unidad. La unidad que depende de
otra queda con dos salidas, y las dos rompen algo.

### Qué se verificó antes de escribir esto

Medido contra `factory.db` y `entregas/` del área de estado, el 2026-08-30.

**1. La duplicación no es un accidente de una corrida: son las cuatro que hubo.**

El registro tiene cuatro cadenas de dos unidades. **En las cuatro, U2 depositó una
copia byte a byte de un artefacto que U1 ya había entregado**, con el mismo
SHA-256:

| Cadena | Archivo duplicado | SHA-256 | Bytes |
|---|---|---|---:|
| `b84a066e…` | `src/es-email-valido.js` | `9d7a3c4278d6bca44b72ff87ecd52077292902cbfbd34907972d32e29a9b7680` | 307 |
| `957795bd…` | `src/validar-email.js` | `da253ad238732bc39fc11f8c786dc75a70da2ac21644341de320f7130a59cdbb` | 359 |
| `957795bd…` | `tests/validar-email.test.js` | `984472472471479cd210fc9eadc1822c2944c1f1cf41ffdffbb36c8814b7ed8c` | 1.266 |
| `94cc2ae4…` | `src/validar-email.js` | `9349ad40877d11367fdbf898a8bea680b2690d659eed1c4f92c5315799e292f1` | 328 |
| `f3b9ea34…` | `src/validar-email.js` | `1bd21eab341f8b3d921de96eb61bd82e1b892b187b1cf173f3c8bb7e75d7eb99` | 502 |

Las dos filas de `957795bd…` son el caso extremo y conviene mirarlo: el enunciado
de U2 era **escribir las pruebas**, y U2 entregó el archivo de pruebas de U1 sin
cambiarle un byte. De sus cuatro entregables, el único artefacto propio fue
`pruebas.html`. Se pagó una invocación completa del Developer para reproducir algo
que ya existía.

**2. El Developer sabe que está copiando y lo declara.** En las dos cadenas más
recientes el supuesto nombra la causa exacta, sin que nadie se lo preguntara:

> «(…) cada unidad trabaja en un directorio aislado y no puede referenciar
> archivos fuera del propio. Se incluye una copia idéntica de
> `src/validar-email.js` dentro de esta unidad para que el archivo de pruebas,
> `pruebas.html` y `demo.html` sean autocontenidos (…)» — U2 de `94cc2ae4…`.

> «(…) porque `pruebas.html` y `demo.html` deben cargar la lógica desde una ruta
> relativa dentro de su propio directorio y no pueden referenciar la carpeta de
> U1.» — U2 de `f3b9ea34…`.

No es un agente confundido. Es un agente que entendió bien el sistema y reportó lo
único que el sistema le dejaba hacer.

**3. El plan declara la dependencia y la ejecución no la honra.** Los cuatro
planes del registro declaran `U2 → dependencias: ["U1"]`. **Cuatro de cuatro.** El
Requirement Agent escribe el orden; la ejecución lo ignora y lanza las unidades
como si fueran independientes.

**4. Las consecuencias, medidas.**

- **QA juzga dos veces lo mismo.** Por ADR-018 punto 9, el paquete de QA lleva el
  depósito de la entrega. El depósito de U2 contiene el archivo idéntico al de U1,
  ya aprobado por el QA de U1. QA lo vuelve a verificar sin saber que ya lo hizo.

- **QA de U2 llegó al techo y no verificó nada.** En `f3b9ea34…`, el QA de U2
  (`7680cb8e…`) agotó los 8.000 tokens de salida —`productor_qa.py:75`— y la
  respuesta quedó cortada: evento `respuesta_ilegible`, motivo `truncada`. **Ese
  paso costó USD 0,124752 y no produjo veredicto.** El QA de U1, en la misma
  cadena y sobre el mismo problema, cerró en 2.263 tokens de salida por USD
  0,038712. La cadena murió ahí: `escalado_por_qa_ilegible`.

- **U2 escaló por ambigüedad antes de producir un archivo.** En `befbec37…`, U2
  (`45113d7b…`) escaló en la **iteración 0** con `unidad_ambigua`, por USD
  0,117162 y cero entregables. Su motivo enumera las dos salidas y las rechaza a
  las dos:

  > «Ninguna de las dos salidas disponibles —romper el aislamiento o duplicar la
  > lógica— es una decisión que me corresponda tomar por mi cuenta (…). Por eso no
  > adivino y escalo.»

**5. ADR-014 punto 2 ya había aceptado la duplicación por escrito**, con el
argumento de que «la redundancia es el precio de que cada unidad sea verificable
por separado, y es barato».

Lo que se midió arriba dice que el precio se calculó sobre el rubro equivocado.
Barato era el disco: un archivo de 502 bytes no le pesa a nadie. Lo que no se
puso en la cuenta es que la copia **también hay que producirla, verificarla y
juzgarla**, y ahí el precio deja de ser el de un archivo.

### Las cuatro fallas son la misma

La copia idéntica declarada como supuesto, el depósito de QA que arrastra código
ajeno, el techo de salida que se agota sin veredicto y la escalada por ambigüedad
antes de producir no son cuatro problemas. Son **cuatro caras de unidades
paralelas corriendo sobre trabajo que no es paralelo**, y el propio plan lo dice
en el campo `dependencias` de cada una de las cuatro corridas.

## Opciones consideradas

El escalamiento de `45113d7b…` enumeró las dos salidas que el sistema ofrece hoy.
Este ADR las descarta a las dos y toma una tercera.

**A. Que las unidades se alcancen entre sí**, con rutas relativas fuera del
directorio propio. Descartada: es exactamente lo que V5 y C2 prohíben, y esas
reglas son la puerta de la frontera de ejecución de ADR-016. Quitarlas para
resolver un problema de coordinación reabre un problema de seguridad, y ADR-016 ya
declaró que el orden no es negociable: primero la regla que rechaza, después la
ejecución.

**B. Aceptar la duplicación y hacerla barata.** Descartada porque **es el estado
actual** —ADR-014 punto 2 la aceptó explícitamente— y las cuatro corridas de
arriba son la medición de lo que costó. No es una opción a evaluar: es el
resultado que se está corrigiendo.

**C. Que las unidades dejen de ser paralelas.** Elegida.

## Decisión

Las unidades dejan de ser paralelas y pasan a ser **incrementos sobre un único
espacio de trabajo que crece**.

### 1. La parte N recibe el estado dejado por la parte N-1

Y le suma. **No hay que duplicar porque nunca se separó.**

Es la forma más directa de leer el hallazgo 3: el plan ya declara el orden. Lo que
cambia no es lo que el Requirement Agent escribe, sino que la ejecución lo cumpla.

Y elimina la causa raíz del hallazgo 2 sin pedirle nada al agente. Hoy el
Developer copia porque copiar es la única salida legal; mañana no copia porque el
archivo ya está donde tiene que estar. Por ADR-014 punto 4, un agente inventa lo
que no se le entrega: acá se le entrega.

### 2. Cada parte aprobada es un punto de retorno

Si algo se rompe más adelante, se vuelve **al último estado firmado** en vez de
descartar todo.

Es lo que hace tolerable perder el aislamiento. Con unidades separadas, el daño de
una unidad quedaba contenido en su directorio; con un espacio que crece, la
contención pasa a ser temporal en vez de espacial. Lo que antes protegía una pared
ahora lo protege una marca en el tiempo.

### 3. QA verifica la parte nueva y sus conexiones con lo anterior

Lo anterior **ya está aprobado y no se vuelve a juzgar**.

Eso es lo que mantiene el costo por paso plano en vez de crecer con el largo del
plan. Sin esta regla, el paso N verifica N unidades y el presupuesto de ADR-010
deja de alcanzar por la forma de la curva, no por la dificultad del trabajo.

Es también la corrección directa del hallazgo 4: hoy el QA de U2 vuelve a juzgar
un archivo que el QA de U1 ya aprobó, y ni siquiera sabe que lo está haciendo.

Las **conexiones** sí se verifican, y no son una excepción a la regla: son parte
nueva. Que lo aprobado siga siendo correcto por separado no dice nada sobre lo que
pasa cuando se lo junta con lo que llegó después.

### 4. La suite de tests de las partes aprobadas se corre completa en cada paso

**No es QA volviendo a juzgar. Es el ejecutor comprobando que lo firmado sigue
andando**, y no consume modelo.

La distinción es la del punto 7 de ADR-018 llevada un paso más: correr un test que
ya existe es mecánico y no emite veredicto nuevo; juzgar si el artefacto cumple el
criterio es sustantivo y cuesta. Confundirlos haría una de dos cosas, las dos
malas: o el costo del punto 3 vuelve a crecer con el largo del plan, o una
regresión sobre lo ya firmado pasa sin que nadie la vea.

Y es la contracara necesaria del punto 3: si lo aprobado no se vuelve a juzgar,
alguien tiene que garantizar que lo aprobado sigue funcionando.

### 5. Corregir es tocar la parte nueva teniendo en cuenta lo aprobado

**Lo firmado no se reabre.**

El bucle de corrección del Developer se mantiene igual, pero su alcance queda
acotado a lo que todavía no tiene firma. Un reintento que pudiera modificar lo
aprobado invalidaría el punto 2: el punto de retorno dejaría de ser un punto.

### 6. Revisar todo desde cero se declara en el plan o escala

Si una parte exige revisar todo desde cero, **eso tiene que estar declarado en el
plan**. Si aparece a mitad del desarrollo, **escala**.

Que aparezca tarde significa que el plan pidió algo incompatible con lo ya
aprobado, y reabrir lo firmado es decisión del CEO, no del Developer ni de QA. Es
el mismo criterio que el Developer aplicó por su cuenta en `befbec37…`: ante dos
salidas que rompen cosas distintas, no adivina.

## Consecuencias

**Esto reemplaza el modelo actual. No convive con él.** No hay un modo paralelo y
un modo incremental entre los que elegir por pedido: las unidades de un plan se
ejecutan en orden sobre un espacio que acumula, y punto. Un sistema con los dos
modelos tendría que decidir cuál usar en cada plan, y esa decisión se tomaría con
la misma información con la que hoy se duplica.

**Lo que habilita.** Que una unidad dependa de otra, que es lo que los cuatro
planes del registro ya declaran y ninguna corrida pudo cumplir. Desaparecen la
copia byte a byte, el supuesto que la justifica, la escalada por ambigüedad y la
verificación repetida de lo mismo.

**Lo que cuesta.** **Trabajo genuinamente paralelo —tres pantallas
independientes— pasa a ser más lento por diseño.** Es un precio aceptado y no una
consecuencia lateral: la fábrica prefiere ser más lenta en el caso que hoy no
falla que seguir rota en el caso que hoy falla. Cuando haya evidencia medida de
que el paralelismo real es la mayoría del trabajo, será una decisión posterior con
datos; hoy la evidencia es cuatro de cuatro en la otra dirección.

**Lo que introduce.** Un orden de ejecución que antes no existía y que ahora hay
que respetar, y con él una obligación nueva sobre el plan: el campo `dependencias`
deja de ser documentación y pasa a ser vinculante.

**Lo que no cambia.** La frontera de ADR-016, que no se ensancha: el espacio de
trabajo crece, pero sigue siendo un solo directorio del que no se puede salir. Los
techos de ADR-010, que siguen siendo de la cadena y no por agente. El contrato de
cuatro entregables. La inmutabilidad de ADR-011: los eventos que registran las
copias quedan como están, y son la evidencia de por qué se decidió esto.

## Decisiones que habilita

- Planes de más de dos unidades con dependencias reales entre ellas, que hasta hoy
  no eran ejecutables.
- Una **métrica de duplicación** sobre corridas nuevas: con el modelo incremental,
  dos artefactos con el mismo SHA-256 en la misma cadena pasan a ser una anomalía
  detectable en vez del funcionamiento normal.
- Que el campo `dependencias` del plan tenga consecuencia, y con ella una segunda
  medida de calidad del Requirement Agent junto a la de ADR-018 punto 5.

## Decisiones que no resuelve

- **El aislamiento entre unidades desaparece, y con él la garantía que ADR-014
  daba por descontada.** Su hallazgo 2 registró que el Developer de `b84a066e…`
  declaró un pisado que nunca ocurrió, porque la plataforma separaba las unidades
  en subdirectorios. Ese pisado **ahora es posible**. El riesgo que aquel ADR
  declaró inexistente pasa a ser real, y no por descuido: es el costo directo de
  la decisión de arriba.

- **El mecanismo de retorno y de integridad del espacio compartido.** Cómo se
  materializa un punto de retorno, cómo se vuelve a él y cómo se detecta que una
  parte nueva modificó algo firmado es implementación y se decide al construirlo.
  El punto 2 fija que tiene que existir, no cómo.

- **El techo de salida de QA.** `MAX_TOKENS = 8000` en `productor_qa.py:75` sigue
  siendo el mismo, y sigue siendo el que mató a `f3b9ea34…`. **Este ADR lo alivia
  al sacar la duplicación, no lo elimina**: QA de U2 tendrá menos que verificar,
  pero nada garantiza que lo que quede entre. Es un problema propio y necesita su
  propia decisión.

- **El orden en que se ejecutan unidades sin dependencia entre sí.** El plan
  declara dependencias, no un orden total. Qué hace la ejecución con dos unidades
  que no dependen una de la otra —secuencia por posición en el plan o alguna otra
  regla— no lo fija este ADR.

- **La enmienda al Contrato de Entrega** que ADR-016 dejó pendiente y ADR-018
  tampoco hizo. Sigue pendiente, y este ADR le agrega materia: el contrato describe
  entregables de una unidad aislada.
