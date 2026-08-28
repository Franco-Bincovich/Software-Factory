---
tipo: adr
estado: aceptado
aprobado: 2026-08-28
version: 1.1
owner: CEO
actualizado: 2026-08-28
adr: [ADR-004, ADR-005, ADR-011, ADR-013]
aliases: [ADR-015]
---

# ADR-015 — Conservación de la evidencia de entrega

## Contexto

Al aprobarse el Gate de salida, la reanudación borra el directorio de trabajo de
la corrida (`directorio_borrado`, `cadena.py:251`). El evento de aprobación queda
afirmando "entregado" sin que exista, en disco, nada de lo entregado.

### Qué se verificó antes de escribir esto

En la corrida `957795bd327d4269a122ded56793c573` —2026-08-28, la que validó
ADR-014— el cierre son tres eventos consecutivos: el 89 resuelve el Gate de
salida como aprobado, el 90 registra `directorio_borrado` sobre
`trabajo/957795bd…`, y el 91 cierra con `run_cerrada` y resultado `"entregado"`.
El directorio no está en disco.

La corrida anterior, `b84a066ec6fe4ea59377166f13f6f480`, sí conserva el suyo. No
por diseño: su **último** evento es el 56, `gate_resuelto` de salida. Nunca se
reanudó después del Gate, así que el borrado no llegó a ejecutarse. Sobrevive por
accidente, y ese accidente es lo que permitió el segundo control de abajo.

### La evidencia no se pierde: los eventos la llevan entera

El diagnóstico inicial era que borrar el directorio destruía la entrega. Es
falso, y conviene dejarlo escrito porque cambia la decisión.

Los eventos `entrega_producida` guardan cada archivo como `{ruta, rol,
contenido}`, donde `contenido` es el texto completo. El docstring de
`borrar_directorio` ya lo afirmaba —"la entrega registrada en el Operational
State lleva el contenido completo de cada archivo"—. Se comprobó en vez de
creerle, con dos controles:

**Control 1 — reconstrucción de lo borrado.** Se reconstruyeron desde los eventos
los 8 archivos de `957795bd` (4 de U1 y 4 de U2), cuyo directorio ya no existe.
Salen los 8 completos, con su SHA-256.

**Control 2 — evento contra disco.** En `b84a066`, que conserva ambos, se
contrastó el contenido de cada archivo del evento contra el archivo en disco:
**8 de 8 idénticos, byte a byte**.

Los dos controles prueban lo mismo: **el problema es de forma, no de pérdida.**

### Lo que falta

No falta la evidencia: falta la evidencia **materializada**. Recuperarla exige
correr un script que camine las sub-corridas, extraiga los payloads y reescriba
los archivos. Eso no es una defensa ante un reclamo de cliente.

El principio de Verificabilidad es de nivel 1 en la tabla de precedencia
—Principles, principios 4, 5 y 8— y exige que lo aprobado se pueda reexaminar
después. Una aprobación sin objeto verificable no es evidencia: es una
afirmación.

Y la aprobación hoy tampoco nombra un objeto. El evento que la registra es
literalmente `{"decision": "aprobado", "gate": "salida"}`, y el `gate_abierto`
que se somete a quien decide lleva **sólo nombres de archivo**, sin contenido ni
hashes. Se firma una lista de nombres.

La consecuencia comercial cae de ahí. Cuando la Fábrica entregue a terceros, la
defensa ante un reclamo es poder mostrar tres cosas: qué se pidió, qué se entregó
y qué se firmó. El tercer término existe, pero en un formato que no se le puede
mostrar a nadie.

## Opciones consideradas

**A. Reconstruir a demanda desde los eventos, sin área de entregas.** Es
exactamente lo que hoy se puede hacer, y es lo que se hizo en el control 1.
Descartada: la evidencia queda a distancia de un script que hay que escribir,
mantener y ejecutar correctamente bajo presión. "Está reconstruible desde el log"
no es mostrable ante un reclamo, y una herramienta de recuperación que sólo se
usa el día del problema es una herramienta que nadie probó.

**B. Materializar la entrega al aprobar.** Elegida.

**C. No borrar nada.** Descartada: acumula el descarte de todas las corridas junto
a la evidencia válida, y a los pocos meses ninguna de las dos se encuentra. Un
depósito donde todo convive es un depósito donde nada se ubica.

**D. Guardar el contenido de los archivos dentro del evento.** No es una opción a
decidir: **ya es el estado actual**, y es la razón por la que la evidencia
sobrevivió al borrado. Se registra acá para que nadie la proponga como novedad ni
la descarte como si no estuviera implementada. Su costo se trata más abajo.

## Decisión

### 1. La evidencia se materializa, no se conserva

Al aprobarse el Gate de salida, la plataforma **escribe** la entrega en un área de
entregas, separada del área de trabajo e identificada por corrida. La escribe
desde los eventos, que ya la tienen: no es una copia del directorio de trabajo
antes de borrarlo, es una materialización del registro.

Que la fuente sea el evento y no el disco no es un detalle de implementación. Es
lo que hace que el área de entregas sea derivable: si se pierde, se regenera; si
discrepa con los eventos, gana el evento, por ADR-011.

El argumento es **legibilidad y traspaso**, no pérdida de datos. Lo que se gana
es una carpeta que se abre en un navegador y se le entrega a un tercero sin
intermediar código.

### 2. El Gate registra el hash de lo aprobado

El evento de resolución del Gate incluye el **SHA-256 de cada archivo aprobado**.

Sin eso, "aprobado" no identifica qué se aprobó, y una modificación posterior del
área de entregas sería indetectable. Es el mismo razonamiento del `CHECKSUMS.txt`
de ADR-013: lo que congela una copia no es guardarla, es poder demostrar después
que es la misma.

Esta parte vale por sí sola, con área de entregas o sin ella. Es la que convierte
la firma en una firma sobre algo.

### 3. Sólo se borra el trabajo de una corrida aprobada

La separación es **por estado, no por antigüedad**, y corta en los dos sentidos.
Una corrida que no llegó a aprobarse no deja evidencia de entrega, porque no hubo
entrega; y tampoco pierde su directorio de trabajo, porque el borrado cuelga de
la aprobación.

Que el trabajo rechazado quede es lo correcto, no un descuido. **Es lo que
permite entender por qué se rechazó.** El evento de rechazo lleva un motivo; el
directorio lleva el código sobre el que ese motivo se pronunció, y sin los dos el
rechazo es una opinión sin objeto —el mismo defecto que el punto 2 le corrige a
la aprobación—. Borrarlo destruiría la evidencia del fallo, que es justamente la
que sirve para no repetirlo. Una corrida abandonada corre la misma suerte por el
mismo mecanismo: sin Gate de salida resuelto no hay borrado.

Y lo que el borrado descarta, en el caso aprobado, es **la copia de trabajo, no
la evidencia**: los eventos la conservan igual y desde este ADR además está
materializada. Por eso ahí borrar sí es seguro.

> **Corrección contra el código.** La redacción original de este punto decía que
> el trabajo de las corridas rechazadas o abandonadas "se sigue borrando", y
> describía un comportamiento que no existe: el borrado siempre estuvo
> condicionado a que el Gate de salida se resolviera aprobando —`_nodo_fin`, en
> `grafo.py`—. Se detectó al implementar el ADR y se corrigió el ADR contra el
> código, no al revés. Un documento que manda destruir algo tiene que decir lo
> que el sistema hace, porque alguien lo va a leer como una orden.

## Consecuencias

**Lo que habilita.** Una entrega aprobada se puede mostrar, abrir y reexaminar sin
correr nada. La aprobación pasa a tener objeto: el hash ata la firma a un estado
concreto de los archivos.

**Lo que cuesta.** Crece el uso de disco, de forma proporcional a **las entregas
aprobadas, no a los intentos**. Es el escalamiento que se quería: se paga por lo
que se entregó, no por lo que costó llegar.

**Lo que introduce.** Un área nueva que hay que respaldar junto al Operational
State. ADR-011 punto 7 ya declara que perder el Operational State es perder toda
la evidencia de todo lo que la Fábrica hizo, y que hasta que exista Infrastructure
el respaldo es manual y del CEO. La evidencia de entrega entra en la misma
categoría: **es tan irreemplazable como los eventos** y hereda el mismo riesgo
anotado.

**Lo que no cambia.** La inmutabilidad de ADR-011 punto 3, el borrado del
directorio de trabajo, y el contenido de los eventos `entrega_producida`. Este
ADR no saca nada: agrega una materialización y un hash.

## Decisiones que habilita

- Entrega a terceros con evidencia mostrable, que es precondición de facturar
  trabajo de la Fábrica.
- Verificación de integridad de una entrega vieja contra la firma que la aprobó.
- Auditoría de una corrida cerrada sin necesidad de herramientas de
  reconstrucción.

## Decisiones que no resuelve

- **La política de retención.** Cuánto tiempo se conserva una entrega aprobada
  queda sin definir. ADR-011 punto 6 difirió el tema hasta que el volumen lo
  justifique y anticipó que sería un ADR propio; esto no lo adelanta.

- **El Operational State es hoy registro de hechos y depósito de archivos a la
  vez.** Es una tensión viva y este ADR **no la resuelve**. Las cifras al momento
  de escribirlo: de **54.817 bytes de payload en 91 eventos, 26.801 son contenido
  de archivos dentro de eventos `entrega_producida`** — el **48,89%**, casi la
  mitad del registro.

  ADR-011 punto 1 define un hecho como aquello que, regenerado desde cero,
  perdería información irrecuperable, y el contenido entregado califica. Pero un
  log cuyo tamaño crece con **el tamaño de los entregables** y no con la cantidad
  de hechos escala mal, y presiona sobre las propiedades que ADR-011 punto 2 le
  exige al sustrato. Cinco corridas de un validador de email ya dejan la mitad del
  registro ocupada por HTML y JavaScript; un entregable real lo desborda.

  **Merece decisión propia.** Las salidas posibles —mover el contenido a un
  almacén de artefactos y dejar en el evento sólo la referencia y el hash,
  mantenerlo como está, o algún corte por tamaño— tienen consecuencias sobre
  ADR-011 que exceden a este ADR. Se documenta acá porque se descubrió acá, no
  porque se resuelva acá.

- **El formato del área de entregas** —jerarquía, nombres, si lleva un índice o un
  manifiesto—. Es implementación y se decide al construirlo.

- **Qué se hace con las corridas ya cerradas.** `957795bd` cerró antes de este ADR
  y su entrega sigue sólo en los eventos. Es reconstruible —el control 1 lo
  demuestra— y no se materializa retroactivamente.
