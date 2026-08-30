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

**El régimen no es una constante: depende de la corrida.** Una corrida sin
Developer declara `gates: ["entrada"]`, porque sin entrega no hay nada que
aprobar en el de salida. Declarar dos y abrir uno hace que el registro se
contradiga a sí mismo.

### El cierre comprueba el régimen que la corrida declaró

`fin` no escribe `run_cerrada` sin antes verificar que la corrida cumplió lo que
prometió. Si el régimen declara dos Gates y la corrida cierra habiendo aprobado
uno —o abre uno que no declaró—, **levanta `RegimenIncumplido` en vez de cerrar
en verde**, deja el hecho escrito y no borra el directorio de trabajo.

Se aplica solo a los cierres que afirman haber completado el trabajo:
`entregado` y `plan_verificado`. Un rechazo humano o un escalamiento cierran
legítimamente sin haber abierto todos los Gates, porque no prometieron lo
contrario.

Esta comprobación no existe por un defecto puntual. Existe porque **el registro
es lo único que la fábrica tiene**, y una corrida cuyo registro se contradice es
peor que una que falla: la que falla se ve.

### Tener cadena o no es un hecho, no un default

Una corrida nueva **exige** declararlo: `--definicion-developer` para ejecutar
las unidades, o `--solo-plan` para producir el plan y cerrar sin ejecutarlas. No
hay valor por defecto, y pedir los dos es error de uso.

```
cadena_fijada  {developer: "…/Developer Agent.md"}
cadena_fijada  {developer: null, motivo: "se pidió --solo-plan: …"}
```

Se escribe **siempre**, haya cadena o no. Sin eso, leyendo los eventos de una
corrida sin unidades no se distingue "nadie pidió cadena" de "se pidió y no se
armó". Es el mismo criterio que `modo_produccion_fijado`: una decisión que
cambia lo que la fábrica hace no se resuelve por la ausencia de un flag.

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

## Heredar un plan ya verificado

Un plan que se produjo y se pagó no tiene por qué volver a producirse para poder
ejecutarse.

```
./.venv/bin/python correr.py --desde-corrida <run_id> \
    --definicion-developer "…/Developer Agent.md"
```

**El plan se identifica por la corrida que lo produjo, no por su `plan_id`.** Ese
campo lo declara el agente —el stub emite siempre el mismo— y dos planes
distintos pueden traerlo igual. Dentro de esa corrida, el plan es el de la última
`iteracion_producida` cuya verificación dio válido.

**No se vuelve a verificar.** El plan es inmutable y su veredicto está
registrado; reverificarlo sería aplicarle las reglas de hoy a algo juzgado bajo
las de entonces, y daría a entender que el registro puede estar mal. Lo que se
anota es **de qué verificación nos fiamos**, por id de evento.

La corrida heredera **salta la fase Requirement**: va del Gate de entrada directo
a ejecutar las unidades. Es un parámetro de `crear_grafo` que cambia una sola
arista, no un grafo aparte, para que no haya dos definiciones del mismo grafo
separándose con el tiempo.

**Lleva Gate de entrada**, y no por formalidad: comprometer el presupuesto del
Developer sobre un plan que puede ser viejo es una decisión de recursos, que es
para lo que ADR-004 pone ese Gate. Lo que somete es el plan y el techo con su
descuento, no el pedido.

```
pedido_heredado  {…el pedido copiado…}
plan_heredado    {de_corrida, origen, plan_id, iteracion, veredicto_evento,
                  modo_de_origen, ejecuciones_previas, reejecuta}
```

El pedido viaja **copiado y con tipo propio**: `pedido_recibido` significa "entró
por Intake" y esto no entró por ahí. Una corrida tiene que poder leerse sola.

`modo_de_origen` registra con qué se produjo el plan original. Sin eso, leer una
entrega producida por un modelo sobre un plan producido por otro —o por el stub—
no se puede interpretar después. El modo de la heredera es propio: son dos
corridas y dos hechos, así que ensayar con `--stub` la ejecución de un plan
producido por el modelo es legítimo y queda dicho.

### El techo se hereda descontado

**El techo pertenece al trabajo, no a la corrida.** El pedido dijo que esto puede
costar hasta cierto monto y producir el plan ya consumió parte. La corrida
heredera arranca con **el techo del pedido menos lo gastado en todo el linaje**
—la corrida de origen, las herederas anteriores y todas sus corridas de
Developer—. Si no queda nada, se niega antes de gastar.

Si cada corrida arrancara con el techo entero, partir el trabajo en dos corridas
sería la forma de evadirlo, y un techo evadible no es un techo.

### Reejecutar es un acto declarado

Heredar un plan que **ya produjo código** se niega. Reejecutarlo deja el registro
con dos respuestas a "qué código satisface este plan", que es la misma clase de
problema que el registro contradiciéndose.

Con `--reejecutar` se acepta, y la corrida nueva declara en `ejecuciones_previas`
a cuáles sucede. El plan es inmutable; sus ejecuciones son hechos que se suceden.

Heredar de una corrida que a su vez heredó **resuelve a la raíz**: `de_corrida`
guarda lo que se nombró y `origen` la corrida que produjo el plan, así que el
linaje y el descuento se calculan sobre una sola cadena.

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
| `gates_de_la_cadena` | pedido | Bajo qué régimen de Gates corrió, según tenga cadena o no |
| `cadena_fijada` | pedido | Si la corrida tiene Developer, o el motivo de que no |
| `pedido_heredado` · `plan_heredado` | pedido | De dónde vino el plan, de qué veredicto se fía y con qué modo se produjo |
| `regimen_incumplido` | pedido | La corrida cerró sin cumplir lo que declaró. Nunca debería aparecer |
| `directorio_trabajo` · `directorio_borrado` | pedido | Dónde se trabajó y cuándo se descartó |
| `unidad_lanzada` · `unidad_entregada` · `unidad_fallida` | pedido | Qué unidad, en qué corrida |
| `plan_detenido` | pedido | Qué falló y qué quedó sin ejecutar |
| `techo_cadena_alcanzado` | pedido | Cuánto se gastó y cuál era el límite |
| `cadena_iniciada` | Developer | De qué corrida de Requirement viene |
| `entrega_producida` | Developer | Cada iteración: la ruta, el rol y el **SHA-256** de cada archivo, y el depósito donde vive el contenido. Desde ADR-017 el contenido no va adentro |
| `verificacion_ejecutada` | Developer | **Mismo nombre que en T7**, a propósito: `presupuesto.consumo` cuenta iteraciones contando ese tipo |
| `run_iniciada` | Developer | De ahí sale el arranque del reloj del techo de tiempo |

## Modo de producción

**Un solo modo para toda la cadena.** El plan y las entregas se producen con lo
mismo: `--stub` usa los dos productores de relleno, y el modo modelo usa los dos
reales —`productor.py` para el plan y `productor_entrega.py` para las entregas—.
Una corrida no produce el plan contra el modelo y el código con el stub, ni al
revés: es un solo hecho de la corrida.

El productor de entregas contra el modelo es el equivalente de T15 para el
Developer, y tiene tres diferencias con aquel, las tres medidas:

- **Caché de prompt sobre el system prompt.** Los cuatro documentos que el
  Developer lee pesan ~14.000 tokens y viajan en cada iteración de cada unidad.
  Un plan de diez unidades con tres iteraciones son hasta treinta llamadas con el
  mismo prefijo; sin caché el contexto solo se come el techo de USD 0.50.
- **Streaming con `max_tokens` en 32.000.** Una Entrega son cuatro archivos
  completos escapados en JSON. El techo de T15 trunca en cuanto la unidad es
  real, y truncar cuesta una iteración pagada que no sirve.
- **La entrega vacía escala en vez de corregirse.** `UnidadAmbigua` sale del
  productor, la atrapa el grafo del Developer y se registra como
  `unidad_ambigua`. No va al verificador y no cuenta como iteración mala:
  reintentarla tres veces quemaría el techo en una unidad que ya dijo que no se
  puede.

Con qué definición de Developer corre la cadena es un hecho de la corrida
—`cadena_fijada`—, con el mismo criterio que el modo de producción: reanudar con
otra definición, o pedir cadena en una corrida abierta con `--solo-plan`,
cambiaría en silencio quién ejecutó las unidades.

---

## Criterio de aceptación

`tests/test_cadena.py`, sesenta y ocho tests contra un Operational State, un
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
| Depósito de artefactos | El evento lleva hash y no contenido; la entrega se reconstruye desde el área; cada iteración deposita la suya, también la rechazada; un evento viejo con contenido se sigue leyendo; el hash detecta una alteración; falta un archivo y la cadena levanta en vez de armar un prompt incompleto; el corte deja archivos sin evento y el reintento los sobrescribe |
| Enganche de QA — ADR-018 | Corre una vez por unidad, después del verificador estructural y antes del Gate de salida; recibe el depósito que registró ADR-017; el productor y la definición van juntos o no van; el incumplimiento sustantivo entra al mismo bucle de corrección que el estructural y lo acota el techo del Developer; sin frontera escala en vez de aprobar; la métrica de criterios no verificables llega al Gate, y sin QA es `None` y no cero |

`tests/test_herencia.py` cubre heredar un plan verificado: que ejecute sin
producir uno nuevo, que las dos corridas queden atadas, que el techo se descuente
sobre el linaje, que reejecutar sea explícito y que la reanudación de una
heredera no vuelva a la fase Requirement.

`tests/test_correr_cadena.py` cubre la costura entre la CLI y la cadena, que es
donde estaba el hueco: que una corrida nueva sin declarar cadena no arranque y no
deje rastro, que con `--definicion-developer` ejecute las unidades de verdad, que
`--solo-plan` declare un solo Gate y lo registre con su motivo, y que declarar
dos Gates y cerrar con uno levante en vez de cerrar en verde.

## Fuera de alcance

No hay paralelismo. No hay
reanudación parcial dentro de una unidad. No se verifica que el código haga lo
que la unidad pedía: eso es verificación sustantiva y llega en V0.3.
