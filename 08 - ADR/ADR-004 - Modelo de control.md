---
tipo: adr
estado: aceptado
aprobado: 2026-08-06
version: 1.0
owner: CEO
adr: [ADR-000, ADR-001, ADR-003]
aliases: [ADR-004]
actualizado: 2026-07-31
---

# ADR-004 — Modelo de control

## Contexto

ADR-003 estableció que cada Agent Definition declara su alcance de decisión: qué decide por
sí misma, qué propone y qué tiene prohibido. Eso regula al agente desde adentro y es
insuficiente por sí solo: un agente mal declarado, o generado automáticamente por Agent
Factory, quedaría sin control efectivo. Hace falta un piso que no dependa de lo que cada
agente declare sobre sí mismo.

El vault archivado arrastraba dos problemas sobre este punto. Describía al humano
simultáneamente como portón de entrada previo a toda ejecución y como validador posterior al
despliegue, sin reconciliar ambos modelos. Y declaraba la supervisión humana como obligatoria
mientras su roadmap la implementaba después de haber entregado generación automática de
código, lo que hacía imposible cumplir el propio principio durante una fase entera.

A esto se suma un riesgo estructural ya registrado: todos los puntos de control convergen hoy
en una sola persona, que por diseño se vuelve cuello de botella del sistema entero.

## Problema

¿Qué acciones exigen decisión humana con independencia de lo que declare el agente, quién
decide, y qué ocurre con el trabajo en curso mientras esa decisión no llega?

## Alternativas evaluadas

**Gate por etapa del pipeline.** Una aprobación al final de cada fase del proceso. Es
predecible y fácil de explicar, pero ata el control a la estructura del proceso en vez de al
riesgo: obliga a aprobar cosas triviales por estar al final de una etapa, y deja pasar sin
control acciones graves que ocurren en el medio de una.

**Gate exclusivamente por Agent Definition.** Solo se controla lo que cada agente declara.
Máxima flexibilidad y ningún piso. Un agente con el alcance mal declarado no tiene control, y
el sistema puede crear agentes nuevos.

**Gate por propiedad de la acción.** Lo que dispara el control es la naturaleza de lo que se
va a hacer —si es reversible, si sale del perímetro, si cambia una norma, cuánto cuesta—, no
en qué momento del proceso ocurre ni qué agente la ejecuta. El control sigue al riesgo.

## Decisión

Se adopta el control por propiedad de la acción, con un piso obligatorio que ninguna Agent
Definition puede reducir.

### Piso obligatorio

Toda acción que cumpla al menos uno de estos criterios exige Gate, sin excepción y con
independencia del agente que la ejecute:

1. **Irreversibilidad.** No se puede deshacer sin costo relevante.
2. **Exposición externa.** Cruza el perímetro del sistema: publicación, entrega, comunicación
   con un tercero.
3. **Efecto normativo.** Modifica una norma del proyecto: un ADR, un Standard, contenido del
   Vault.
4. **Exceso de presupuesto.** Cualquier consumo por encima del techo declarado según ADR-003.
5. **Creación o ampliación de capacidad.** Crear una Agent Definition, o ampliar las
   herramientas autorizadas de una existente.
6. **Ambigüedad de requerimiento.** Los Acceptance Criteria no pueden derivarse sin
   interpretar la intención del solicitante.

Una Agent Definition puede **agregar** Gates propios. No puede eliminar ninguno del piso.

### Anatomía de un Gate

Todo Gate declara: qué se aprueba, identificado como artefacto concreto; qué evidencia se
presenta junto con él; qué rol aprueba; qué opciones tiene quien decide —aprobar, rechazar
con motivo, o aprobar con condición—; qué ocurre con el trabajo en curso mientras espera, sea
suspenderlo, continuarlo en paralelo o abortarlo; qué plazo tiene; y qué queda registrado del
desenlace.

Un Gate sin rol aprobador nombrado no es un Gate.

### Los tres momentos

**Gate de entrada.** Antes de comprometer recursos. Aprueba los Acceptance Criteria
derivados en Intake. Su función es evitar que el sistema gaste construyendo lo que no se
entendió.

**Gate de decisión.** Antes de tomar un camino costoso de revertir: arquitectura de la
solución, elección de tecnología del proyecto, cambios de alcance.

**Gate de salida.** Antes de exponer: despliegue, entrega, comunicación externa.

Los tres coexisten y responden a preguntas distintas: si vale la pena empezar, si el camino
es el correcto, si el resultado puede salir. Un modelo que elija uno solo deja los otros dos
descubiertos.

**Queda prohibida la aprobación posterior al despliegue.** Aprobar algo ya expuesto no es un
Gate: es una notificación.

### Vencimiento

El vencimiento de un Gate **nunca equivale a aprobación**. Un Gate no atendido dentro de su
plazo se rechaza o se escala, según declare el propio Gate. La aprobación por silencio queda
prohibida en todo Gate del piso obligatorio.

### Mecanismos de descarga

El control humano es un recurso escaso y su saturación degrada la calidad de las decisiones
más que su ausencia. Se admiten cuatro mecanismos, ninguno aplicable al piso obligatorio
salvo indicación expresa:

**Roles aprobadores diferenciados.** No todo Gate corresponde al mismo rol. El modelo declara
roles distintos aunque hoy los ocupe una sola persona: separarlos después es más caro que
declararlos ahora.

**Umbral.** Por debajo de un umbral declarado de costo o de alcance, la acción no genera
Gate. El umbral es un valor versionado, no un criterio del agente.

**Ventana de veto.** Para acciones reversibles y de bajo impacto: se ejecuta, se notifica, y
existe un plazo durante el cual puede revertirse sin justificación. No aplica a acciones
irreversibles ni de exposición externa.

**Aprobación por lote.** Gates del mismo tipo y del mismo rol se presentan agrupados.

### Autonomía progresiva

El Autonomy Level se declara por agente y por tipo de acción. Nunca es una propiedad global
de la plataforma ni una etapa temporal del roadmap.

**Aumentar el Autonomy Level de un agente es en sí una acción con efecto normativo y por lo
tanto exige Gate.** La propuesta de aumento debe acompañarse de evidencia: historial de Agent
Runs de esa Agent Definition cuyo resultado haya sido verificado objetivamente. Sin evidencia
no hay aumento.

Con esto la autonomía progresiva deja de ser una intención y pasa a ser un procedimiento con
condición de entrada.

### Regla de secuencia

**Ninguna capacidad autónoma se habilita antes que el Gate que la controla.** El Gate se
construye primero, la capacidad después. Cualquier planificación que invierta ese orden queda
invalidada por este ADR.

## Justificación

Atar el control a la propiedad de la acción y no a la etapa del proceso es lo que permite que
el mismo modelo siga siendo válido cuando el proceso cambie, cuando aparezcan agentes nuevos,
y cuando Agent Factory genere agentes que nadie diseñó a mano.

El piso obligatorio existe porque la alternativa —confiar en lo que cada agente declara sobre
sí mismo— falla precisamente en el caso que más importa: el agente generado automáticamente.

El vencimiento como rechazo y no como aprobación es la única postura compatible con la
irreversibilidad. Un sistema donde no responder equivale a autorizar convierte la desatención
en decisión, y la desatención es el estado más probable.

La regla de secuencia resuelve de raíz la contradicción del roadmap anterior. No se trata de
explicar por qué la supervisión llegaba tarde: se trata de que no puede llegar tarde.

## Consecuencias

**A favor.** El control es predecible y no depende de la buena fe de cada Agent Definition.
Agent Factory puede generar agentes sin abrir un agujero de gobierno. La autonomía progresiva
tiene un procedimiento concreto en vez de una aspiración. La contradicción entre principio de
supervisión y secuencia de construcción queda cerrada.

**En contra.** Introduce latencia estructural: hay puntos donde el sistema se detiene y
espera a una persona, y eso es deliberado. Mientras exista un solo rol humano, los mecanismos
de descarga alivian pero no eliminan el cuello de botella: lo mitigan reduciendo el volumen,
no distribuyéndolo. Va a haber presión sostenida para bajar el piso obligatorio cuando la
espera moleste, y ceder una vez vuelve discutible todo el resto.

**Consecuencia no obvia.** La regla de secuencia reordena el roadmap: varias capacidades que
figuraban como entregables tempranos quedan condicionadas a que exista antes su Gate
correspondiente. El roadmap se reescribe a partir de este ADR, no al revés.

## Dependencias

**Requiere:** ADR-000, ADR-001, ADR-003.

**Habilita:** la capa de verificación; el modelo de identidad y permisos; la reescritura del
roadmap; la definición de los Core Agents con su Autonomy Level inicial.

**Bloquea:** toda capacidad autónoma cuyo Gate no exista; la aprobación por silencio; la
aprobación posterior a la exposición; y cualquier Agent Definition que reduzca el piso
obligatorio.

## Decisiones que este ADR deja abiertas

- Los valores concretos de umbral y de plazo de cada Gate.
- Qué roles aprobadores existen y quién los ocupa mientras haya una sola persona.
- Cómo se notifica un Gate pendiente y por qué medio.
- Si la ventana de veto aplica a la promoción de conocimiento al Vault. Se decide en el ADR
  de gestión del conocimiento.
- Qué constituye evidencia suficiente para aumentar un Autonomy Level. Depende del ADR de
  verificación.

## Documentos afectados

**Crea:** `03 - Agent Framework/Autonomy and HITL.md`.

**Condiciona:** `01 - Master Plan/Roadmap.md`, que se escribe después de este ADR y no antes;
`03 - Agent Framework/Verification.md`; `05 - Infrastructure/Security.md`.
