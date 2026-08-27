# La cadena de V0.2

Especificación de construcción. Vive en el repositorio de código. El Vault
contiene la norma —Requirement Agent 1.1, Developer Agent, el Contrato
del Plan de Trabajo y el Contrato de Entrega—; esto es cómo se implementa.

**Capacidad que agrega:** un pedido se convierte en plan y en código sin ninguna
persona en el medio.

---

## Dos corridas encadenadas, no una

El `run_id` del pedido **es** el de la cadena. Lleva los dos Gates, el directorio
de trabajo y el registro de qué unidades corrieron. Cada unidad abre su propia
corrida de Developer, con identificador y presupuesto propios.

Que sean dos y no una es lo que permite **reintentar al Developer sin volver a
producir el plan**: lo que se reintenta es la corrida de la unidad.

El encadenamiento queda registrado como hecho de la corrida del Developer:

```
cadena_iniciada  {viene_de: <run del pedido>, unidad: "U1", plan_id: "..."}
```

## Dos Gates en toda la cadena

**Gate de entrada**, sobre el pedido y los techos. **Gate de salida**, sobre la
entrega. Nada entre medio.

**El Gate de salida sobre el plan se suprimió.** Aprobar el plan y después
aprobar la entrega que sale de él es aprobar dos veces lo mismo. Está justificado
en la versión 1.1 del Requirement Agent; no necesitó ADR porque nunca fue un Gate
del piso de ADR-004.

Cada corrida declara bajo qué régimen corrió, sin que haya que deducirlo de la
versión del código:

```
gates_de_la_cadena  {gates: ["entrada","salida"], suprimido: "salida_de_plan", motivo: "..."}
```

El ciclo queda en dos paradas:

```
correr.py --pedido … --definicion-developer …   → Gate de entrada, corta
[el CEO resuelve]
correr.py --reanudar <run>                      → plan, T7, U1 … Un, Gate de salida, corta
[el CEO abre pruebas.html y demo.html, resuelve]
correr.py --reanudar <run>                      → cierra y borra el directorio
```

Entre la primera y la segunda parada no hay intervención. Eso es la cadena.

---

## Los módulos

| Módulo | Qué hace |
|---|---|
| `src/grafo.py` | El grafo de la cadena. Ejecutar las unidades es **un nodo** |
| `src/grafo_developer.py` | El grafo de **una** unidad: techos, producir, verificar, reintentar |
| `src/cadena.py` | El coordinador: orden, corridas de Developer, techo de la cadena, directorio |

**El coordinador se inyecta**, con el mismo criterio con el que se inyecta el
productor: `grafo.py` ordena la corrida y no sabe qué es un Developer. Sin
coordinador inyectado la corrida cierra con `plan_verificado`, que es el
Requirement Agent corriendo solo.

**El grafo del Developer se compila sin checkpointer.** No tiene `interrupt`, así
que no hay nada que reanudar a mitad. La reanudación de la cadena la resuelve el
nodo del grafo externo.

## El orden lo decide el plan

El coordinador lee el grafo de dependencias y ejecuta primero las unidades sin
dependencias. **El Developer nunca decide qué sigue**: recibe una unidad y
devuelve una entrega.

El orden es **determinista**: dentro de cada tanda habilitada se ordena por
identificador. Dos corridas del mismo plan ejecutan en el mismo orden, y una
cadena que no se puede repetir igual no se puede investigar.

**Secuencial.** Una unidad por vez, aun las independientes. El Operational State
es de escritor único y la arquitectura declara un proyecto por vez; paralelizar
es V0.4.

## Si una unidad falla, se detiene el plan completo

No siguen las unidades independientes. En V0.2 la simplicidad vale más que el
aprovechamiento: media entrega repartida entre unidades que anduvieron y otras
que no es más difícil de explicar en un Gate que una detención limpia.

```
unidad_fallida  {unidad, run_developer, motivo}
plan_detenido   {unidad, motivo, sin_ejecutar: [...]}
```

## Cada artefacto va a su verificador

El plan al verificador de planes, la entrega al de entregas. **El coordinador
elige según qué produjo el agente, no según cuál corre.** En la práctica cada
grafo llama al que corresponde a lo que su nodo de producción devuelve.

## Reintento

Si el verificador de entregas rechaza, el Developer **corrige la entrega
anterior** con la lista de incumplimientos. No regenera. Mismo patrón que el
Requirement, y por la misma razón: lo exige el campo 9 de la Agent Definition.

---

## El techo de la cadena

Los techos del Developer son **por unidad**. Por encima de ellos, **el techo de
costo del pedido acota la suma de todas las corridas** —Requirement y todos los
Developer— y se comprueba **antes de lanzar cada unidad**.

Es la defensa que reemplaza al Gate suprimido: un plan malo ya no se detecta con
una firma, se paga con presupuesto, y el techo acota cuánto. Las dos cosas se
decidieron juntas y no vale una sin la otra.

```
techo_cadena_alcanzado  {costo, limite, unidad}
```

## El directorio de trabajo

Uno por corrida de plan, descartable, **fuera del repositorio y fuera del
Vault**. Su ruta queda registrada para que la persona sepa dónde mirar.

**Cada unidad escribe en su propio subdirectorio**, y no es un detalle: el
Contrato de Entrega fija los nombres `pruebas.html` y `demo.html`, iguales para
toda unidad. Dos unidades en la misma carpeta se pisarían justamente los dos
archivos que existen para que alguien verifique. Las rutas de la entrega siguen
siendo relativas a su unidad; el prefijo lo pone la plataforma.

**Escribe la plataforma, no el agente.** El agente declara qué archivos produjo;
la plataforma los deposita. Es la misma separación por la que el agente no
ejecuta su propia verificación. Y aunque la regla C2 del verificador ya comprobó
que ninguna ruta escapa del directorio, el coordinador lo comprueba otra vez:
escribir no se deshace.

**Se borra recién después de que el Gate de salida se resolvió aprobando.** Nunca
antes: mientras el Gate esté pendiente, o si la corrida escaló, el directorio es
lo que la persona necesita mirar. Borrarlo no pierde nada —la entrega registrada
lleva el contenido completo de cada archivo— y queda registrado con su ruta, que
es el ítem 8 de evidencia de la Agent Definition. `--conservar-trabajo` no lo
borra.

---

## Idempotencia

`ejecutar_unidades` es **un nodo de LangGraph, y al reanudar se re-ejecuta desde
su primera línea** — igual que los nodos de Gate. Las unidades que ya entregaron
se saltean leyendo el Operational State, no el checkpointer: es el punto 4 de
ADR-006, si los dos difieren manda el Operational State.

Sin esa idempotencia, reanudar volvería a producir —y a pagar— lo ya entregado.

## Hechos nuevos

Ninguno exigió tocar el esquema de la base ni los triggers de inmutabilidad.

| Evento | Corrida | Qué registra |
|---|---|---|
| `gates_de_la_cadena` | pedido | Bajo qué régimen de Gates corrió |
| `directorio_trabajo` · `directorio_borrado` | pedido | Dónde se trabajó y cuándo se descartó |
| `unidad_lanzada` · `unidad_entregada` · `unidad_fallida` | pedido | Qué unidad, en qué corrida |
| `plan_detenido` | pedido | Qué falló y qué quedó sin ejecutar |
| `techo_cadena_alcanzado` | pedido | Cuánto se gastó y cuál era el límite |
| `cadena_iniciada` | Developer | De qué corrida de Requirement viene |
| `entrega_producida` | Developer | La entrega de cada iteración, íntegra |
| `verificacion_ejecutada` | Developer | **Mismo nombre que en T7**, a propósito: `presupuesto.consumo` cuenta iteraciones contando ese tipo |
| `run_iniciada` | Developer | De ahí sale el arranque del reloj del techo de tiempo |

## Modo de producción

**No existe todavía un productor de entregas contra el modelo** — es el
equivalente de T15 para el Developer. Lo único disponible es el stub, así que
pedir la cadena en modo modelo **falla nombrando eso**. Caer al stub en una
corrida que alguien abrió creyendo que produce contra el modelo entregaría código
de relleno con apariencia de código producido.

Con qué definición de Developer corre la cadena es un hecho de la corrida
—`developer_fijado`—, con el mismo criterio que el modo de producción: reanudar
con otra definición cambiaría en silencio quién ejecutó las unidades.

---

## Criterio de aceptación

`tests/test_cadena.py`, diecisiete tests contra un Operational State, un
checkpointer y un directorio de trabajo temporales.

| Cubre | Qué comprueba |
|---|---|
| Cadena completa | Dos corridas, el encadenamiento registrado, dos Gates y ninguno en el medio, el Gate de salida sometiendo la entrega y no el plan |
| Cada artefacto a su verificador | El plan con reglas enteras, la entrega con reglas con prefijo |
| Presupuestos separados | El consumo de cada corrida y la suma de la cadena |
| Orden | Primero las unidades sin dependencias; cada unidad recibe las entregas de las que depende |
| Reintento | Dos iteraciones, la segunda recibe entrega anterior e incumplimientos, y los archivos previos llegan intactos |
| Detención | U1 entrega, U3 falla, **U2 no se lanza aunque no dependa de U3**; la cadena escala sin abrir el Gate de salida |
| Techo de la cadena | Corta antes de lanzar la unidad que lo pasaría |
| Directorio | Un subdirectorio por unidad; se borra recién tras el Gate aprobado; no se borra si escaló; una ruta que escapa no se escribe |
| Idempotencia | Reentrar no relanza ni repaga lo entregado, y reusa el directorio |

## Fuera de alcance

No hay productor de entregas contra el modelo. No hay paralelismo. No hay
reanudación parcial dentro de una unidad. No se verifica que el código haga lo
que la unidad pedía: eso es verificación sustantiva y llega en V0.3.
