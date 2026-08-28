---
tipo: adr
estado: aceptado
aprobado: 2026-08-28
version: 1.1
owner: CEO
actualizado: 2026-08-28
adr: [ADR-001, ADR-006, ADR-011, ADR-013, ADR-015]
aliases: [ADR-017]
---

# ADR-017 — Separación entre el registro de hechos y el depósito de artefactos

## Contexto

El evento `entrega_producida` guarda cada archivo entregado como `{ruta, rol,
contenido}`, donde `contenido` es el texto completo. ADR-015 dejó esto anotado
como **tensión viva y explícitamente sin resolver**, con la cifra medida, y
declaró que merecía decisión propia. Ésta es.

El Operational State es el registro de qué ocurrió: ADR-006 punto 2 le asigna
"Registro de qué ocurrió" en su tabla de autoridad y ADR-001 lo hace fuente de
verdad de los hechos, frente al Vault que lo es de las normas. Hoy hace además de
depósito de archivos. Son dos cosas distintas metidas en la misma tabla.

### Qué se verificó antes de escribir esto

Contra `factory.db` del área de estado, el 2026-08-28:

| Medición | Valor |
|---|---|
| Eventos registrados | 91 |
| Bytes de payload | 54.817 |
| Payload de los eventos `entrega_producida` | 26.801 en 5 eventos — **48,89%** |
| De eso, las cadenas `contenido` de 20 archivos | 20.122 — **36,71% del registro** |
| Payload total si el contenido no estuviera | 34.695 |

Las tres cifras que ADR-015 registró —54.817, 26.801 y 48,89%— coinciden exactas
con la base. Una precisión sobre su redacción, que no cambia nada: los 26.801
bytes son el **payload completo** de esos cinco eventos, no sólo el contenido de
los archivos; el contenido propiamente dicho son 20.122. La cifra y el porcentaje
que ADR-015 usa para dimensionar el problema son correctos.

### El problema no es el tamaño de hoy

Noventa y un eventos y cincuenta y cuatro kilobytes no molestan a nadie. Lo que
está mal es la **ley de crecimiento**: el registro crece con el tamaño de lo que
la Fábrica produce, no con la cantidad de hechos que registra.

Cinco corridas de un validador de email —veinte archivos chicos de JavaScript y
HTML— ya ocupan casi la mitad del registro. Un proyecto real con cien archivos no
lo degrada: lo vuelve inmanejable, y arrastra con él las propiedades que ADR-011
punto 2 le exige al sustrato —integridad transaccional, consulta sobre múltiples
corridas—, que se pagan sobre cada byte almacenado.

ADR-011 punto 1 define un hecho como aquello que, regenerado desde cero, perdería
información irrecuperable, y el contenido entregado califica. Eso justifica
**conservarlo**; no justifica conservarlo *adentro del evento*.

## Opciones consideradas

**A. Dejarlo como está.** Es el estado actual y tiene una virtud real: el evento
es autosuficiente, y eso fue lo que salvó la evidencia cuando ADR-015 comprobó
que el borrado del directorio de trabajo no destruía nada. Descartada por la ley
de crecimiento: la virtud se paga con un registro que no escala, y el momento de
cambiarlo es antes de que haya un proyecto real adentro, no después.

**B. Cortar por tamaño: contenido inline hasta N bytes, referencia por encima.**
Descartada. Hace que la forma del registro dependa del peso de lo registrado: dos
entregas equivalentes quedan escritas distinto según cuánto pesen, y todo lector
del registro tiene que manejar las dos formas para siempre, no como transición
sino como diseño.

**C. Comprimir el contenido dentro del evento.** Descartada. Posterga el problema
un orden de magnitud sin resolverlo, y vuelve ilegible el payload —hoy se lee con
`sqlite3` y la vista—, que es media utilidad del registro.

**D. Referencia y hash en el evento; los archivos en el área de entregas.**
Elegida.

## Decisión

### 1. El evento registra que hubo entrega y el hash de cada archivo

`entrega_producida` deja de llevar `contenido`. Registra la ruta, el rol y el
**SHA-256** de cada archivo. Los archivos viven en el área de entregas que
ADR-015 ya estableció.

El hash no es un adorno: es lo que ata las dos mitades. Con él, el registro sigue
identificando sin ambigüedad **qué** se entregó, aunque ya no lo contenga, y una
alteración posterior del depósito es detectable. Es el mismo razonamiento del
`CHECKSUMS.txt` de ADR-013 y del punto 2 de ADR-015: lo que congela una copia no
es guardarla, es poder demostrar después que es la misma.

### 2. No se migra lo existente

Las corridas anteriores conservan el contenido dentro de sus eventos. **No se
reescriben.**

ADR-011 punto 3 dice que un evento no se modifica ni se borra, y la razón que da
es que un registro editable no prueba nada. Reescribir noventa y un eventos para
ahorrar veinte kilobytes sería destruir evidencia por comodidad, y por un motivo
—espacio— que en este volumen ni siquiera existe. La inmutabilidad no admite
excepciones convenientes: la primera que se acepte fija el precedente de que el
registro se puede tocar cuando molesta.

### 3. El área de entregas deja de ser derivable

Ésta es la consecuencia estructural del punto 1 y hay que decirla como decisión,
no como efecto secundario.

ADR-015 punto 1 estableció el área de entregas como **materialización del
registro**: si se perdía, se regeneraba desde los eventos; si discrepaba, ganaba
el evento. Desde este ADR eso deja de ser cierto para las corridas nuevas. El
área de entregas pasa a ser **el único lugar donde el contenido existe**, y por
lo tanto pasa a ser tan crítica como `factory.db`.

**Se respaldan juntas o ninguna de las dos sirve.** Un `factory.db` sin su área
de entregas es un índice de archivos que ya no están; un área de entregas sin su
`factory.db` es un montón de archivos sin corrida, sin fecha y sin aprobación.

Esto **agrava R8** —`Project Master Plan:128`, "Pérdida del Operational State",
alto y abierto—. El riesgo estaba enunciado sobre un solo activo; ahora son dos, y
el respaldo tiene que cubrir los dos en el mismo acto. ADR-015 ya había anotado
que el área de entregas hereda el mismo riesgo; lo que cambia acá es que deja de
ser una copia conveniente y pasa a ser irreemplazable.

### 4. El cambio aplica sólo hacia adelante

No hay bandera de compatibilidad ni conversión. A partir de la implementación, los
eventos nuevos llevan hash y los viejos siguen llevando contenido.

De ahí se sigue una obligación concreta para el código que lea el registro:
**tiene que tolerar las dos formas de `entrega_producida`**, y distinguirlas por
presencia de campo, no por fecha. Un lector que asuma una sola forma rompe contra
el registro histórico, que es exactamente lo que el punto 2 promete preservar.

### 5. Se deposita **cada iteración**, no sólo la aceptada

Este punto se agrega al implementar. El ADR no lo había contemplado y no es un
detalle de implementación: decide qué evidencia sobrevive.

**El hallazgo.** Una iteración rechazada existía hasta acá únicamente adentro de
su evento. `escribir_entrega` sobre el área de trabajo corre recién cuando la
unidad sale entregada, así que lo que el verificador rechazó **nunca tocaba el
disco**. Mientras el evento llevaba el contenido eso no se notaba, porque el
evento alcanzaba. Sacándole el contenido al evento y depositando sólo lo
aceptado, ese código desaparecería del todo: sería la única pérdida real de
información de este cambio, y silenciosa.

En el registro hay hoy una sola iteración rechazada, y está medida contra
`factory.db` el 2026-08-28:

| Medición | Valor |
|---|---|
| Corrida | `cc2b9cf8`, unidad U2, iteración 1 |
| Veredicto | `verificacion_ejecutada` con `valido: false` |
| Payload del evento | **6.038 bytes**, de los cuales 4.335 son contenido de archivos |
| Dónde vive ese contenido hoy | Únicamente adentro de ese evento |

**La decisión.** Cada iteración deposita su contenido en
`entregas/<run_developer>/<iteracion>/`, rechazada o no.

El motivo es que ADR-015 punto 3 ya conserva el trabajo rechazado **por diseño**
—sólo se borra el directorio de una corrida aprobada, porque lo que se rechazó es
justamente lo que hay que poder mirar para entender por qué—. Depositar sólo lo
aceptado contradiría esa decisión por la puerta de atrás, sin discutirla.

Y no reintroduce el problema que este ADR combate. **El escalamiento que acá se
ataca es el del registro, no el del depósito.** El registro tiene que crecer con
la cantidad de hechos porque se consulta, se respalda transaccionalmente y
arrastra las propiedades que ADR-011 punto 2 le exige sobre cada byte. El
depósito es de escritura única y no paga nada de eso: que ocupe una carpeta por
iteración es exactamente lo que se esperaba de él.

Por corrida de Developer y no por unidad porque el `run_id` ya es único por
unidad, y colgar de él deja el rastro completo de una unidad —sus intentos y su
entrega— junto en un solo lugar.

## Consecuencias

### Lo que hay que decir de frente

**Hoy un evento basta para reconstruir la entrega. Después no.**

Ésa fue la propiedad que ADR-015 comprobó con dos controles —reconstruyó ocho
archivos borrados desde los eventos, y contrastó ocho contra disco byte a byte— y
es la propiedad que este ADR entrega a cambio de un registro que escala con los
hechos.

Se gana: un log cuyo tamaño depende de cuántas cosas pasaron y no de cuánto
pesaban. Se pierde: la autosuficiencia del evento. Lo que queda en el medio es el
hash, que no reemplaza al contenido pero hace dos cosas que valen —identifica sin
ambigüedad qué se entregó, y permite detectar si el depósito fue alterado—.

No es un intercambio neutro y no se lo presenta como tal. Es un intercambio
deliberado, hecho ahora porque el costo de hacerlo con un proyecto real adentro
es mucho mayor.

**Lo que habilita.** Un registro que se puede consultar, respaldar y mover con
independencia del tamaño de los entregables. Verificación de integridad del
depósito contra el registro, en cualquier momento y sin herramientas nuevas.

**Lo que cuesta.** Dos activos críticos en vez de uno, con respaldo todavía
manual. Un lector del registro más complicado, por las dos formas del punto 4.

**Lo que no cambia.** La inmutabilidad de ADR-011 punto 3. El borrado del
directorio de trabajo de una corrida aprobada. El área de entregas como tal, que
ADR-015 estableció y que este ADR sólo reclasifica de derivable a crítica. Y la
definición de hecho de ADR-011 punto 1: el contenido entregado sigue siendo
evidencia, sólo que deja de vivir dentro del evento que la nombra.

## Decisiones que habilita

- Política de retención sobre dos ejes separables: se puede purgar depósito sin
  tocar registro, cosa que hoy es imposible porque son lo mismo.
- Respaldo con estrategias distintas para cada mitad —el registro es chico y
  transaccional, el depósito es grande y de escritura única—.
- Un almacén de artefactos remoto más adelante, sin tocar el formato del evento:
  el evento ya no lleva contenido, lleva identidad.

## Decisiones que no resuelve

- **La política de retención.** Sigue sin definir. ADR-011 punto 6 la difirió
  hasta que el volumen lo justifique y anticipó que sería un ADR propio; ADR-015
  la volvió a diferir; esto tampoco la adelanta. Lo único que cambia es que ahora
  se puede formular sobre dos ejes en vez de uno.

- **El respaldo del área de entregas sigue siendo manual.** ADR-011 punto 7 y
  Knowledge Management dejan el procedimiento en Infrastructure, documento
  bloqueado por la Secuencia de decisión. Hasta que exista, el respaldo de las dos
  mitades es manual y es responsabilidad del CEO. Este ADR agrava el riesgo y no
  aporta la mitigación: decirlo es lo único honesto que puede hacer.

- **El formato exacto del evento y del depósito** —nombre del campo del hash, si
  hay manifiesto por corrida, cómo se nombra el archivo en el área—. Es
  implementación y se decide al construirlo.

- **Qué se hace a largo plazo con las dos formas de `entrega_producida`.** Conviven
  por decisión del punto 2. Si alguna vez estorban, la salida es un lector
  declarado, no una migración del registro.

- **La verificación periódica del depósito contra los hashes.** El hash habilita
  el control; quién lo corre y cuándo es Infrastructure.
