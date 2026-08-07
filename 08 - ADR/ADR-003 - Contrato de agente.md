---
tipo: adr
estado: aceptado
aprobado: 2026-08-06
version: 1.0
owner: CEO
adr: [ADR-000, ADR-001]
aliases: [ADR-003]
actualizado: 2026-07-31
---

# ADR-003 — Contrato de agente

## Contexto

ADR-001 separó **Agent Definition** —la especificación— de **Agent Run** —una ejecución
concreta. Esa separación resolvió el vocabulario pero dejó abierto el contenido: qué
declara exactamente una Agent Definition y qué se registra de un Agent Run.

El vault archivado ya enunciaba cinco atributos para un agente: objetivo, responsabilidades,
límites de actuación, entradas y salidas, y herramientas autorizadas. Es una base correcta e
insuficiente. Los cinco describen qué hace un agente cuando todo sale bien y no dicen nada
sobre qué pasa cuando no: cuándo termina, cuándo falla, cuántas veces reintenta, a quién
escala, cuánto puede gastar.

Sin esos campos no hay autonomía diseñable, solo optimismo. Y sin un contrato completo,
**Agent Factory no es implementable**: no se puede generar dinámicamente instancias de algo
que no tiene tipo.

## Problema

¿Qué campos declara obligatoriamente una Agent Definition, y qué registra obligatoriamente
un Agent Run?

## Alternativas evaluadas

**Agente como instrucción más herramientas.** Es el enfoque habitual: se describe la tarea
en lenguaje natural y se le dan capacidades. Barato de crear, imposible de gobernar. El
alcance del agente vive en un texto, no en un contrato, y por lo tanto no es verificable ni
comparable entre agentes.

**Contrato declarativo con campos obligatorios.** La Agent Definition es un artefacto
versionado con campos que deben estar todos completos para que el agente exista. Cuesta más
crear un agente y hace posible auditarlo, presupuestarlo y generarlo automáticamente.

**Contrato con esquema formal de entrada y salida.** Igual que el anterior pero con
validación estructural estricta de datos. Es donde conviene terminar, pero exige decisiones
de representación que dependen del stack, todavía no decidido.

## Decisión

Se adopta el contrato declarativo. La definición del esquema formal de entrada y salida
queda diferida al momento de decidir el stack, sin que eso bloquee el resto.

### Agent Definition — campos obligatorios

Una Agent Definition sin los trece campos completos **no existe**: no se registra, no se
instancia, no se ejecuta. No se admiten campos vacíos ni marcados como pendientes.

1. **Identidad.** Identificador estable, nombre canónico según ADR-001, versión y estado.
2. **Propósito.** Una sola frase. Si requiere dos, son dos agentes.
3. **Entrada.** Qué recibe y qué debe cumplir para ser aceptada. Una entrada que no valida
   se rechaza antes de ejecutar, no se interpreta.
4. **Salida.** Qué produce, en qué forma, y dónde queda depositado.
5. **Herramientas autorizadas.** Lista cerrada. **Denegación por defecto:** lo que no está
   declarado, está prohibido.
6. **Alcance de decisión.** Tres listas explícitas: qué decide por sí mismo, qué propone
   para aprobación, qué tiene prohibido. Es el Autonomy Level del agente.
7. **Criterio de terminación.** Condición objetiva que define que el trabajo está hecho.
   **No puede ser evaluada por el propio Agent Run.**
8. **Presupuesto.** Techo de costo, de tiempo y de iteraciones. Los tres son obligatorios.
9. **Comportamiento ante fallo.** Qué constituye fallo, cuántos reintentos se permiten, y
   qué debe cambiar entre un intento y el siguiente. Reintentar idéntico no es reintentar.
10. **Escalamiento.** A quién escala —rol nombrado, nunca "un humano"—, con qué información
    mínima, y qué ocurre con el trabajo en curso mientras espera.
11. **Acceso al conocimiento.** Qué lee y qué escribe, distinguiendo Vault, Operational
    State y Memory según ADR-001. El acceso de escritura se declara por separado del de
    lectura.
12. **Evidencia.** Qué queda registrado obligatoriamente de cada ejecución.
13. **Dependencias.** Qué otras Agent Definitions necesita y en qué orden.

### Agent Run — registro obligatorio

Todo Agent Run registra: identificador propio; qué Agent Definition ejecutó y **en qué
versión exacta**; entrada recibida; inicio y fin; presupuesto consumido contra el declarado;
resultado —completado, fallado, escalado, cancelado—; artefactos producidos con su
identificador de integridad; decisiones tomadas dentro de su alcance; Gates disparados con
su desenlace; y traza de ejecución.

### Reglas que se derivan

**Un Agent Run siempre referencia una versión exacta de Agent Definition.** Cambiar la
definición no altera ejecuciones pasadas ni su interpretación.

**Presupuesto agotado es fallo.** No se extiende sobre la marcha. Un excedente requiere
Gate, y por lo tanto una persona.

**Terminación y verificación son actos separados.** El agente declara que terminó; otra cosa
comprueba que efectivamente terminó. Esa comprobación se define en el ADR de verificación.

**Agent Factory solo produce Agent Definitions que cumplan este contrato.** Con esto, Agent
Factory deja de ser una capacidad vaga y pasa a ser un generador de artefactos de un tipo
conocido.

## Justificación

Los campos 7 a 10 —terminación, presupuesto, fallo, escalamiento— son los que convierten la
autonomía en algo gobernable. Son también los que sistemáticamente se omiten, porque no
hacen falta cuando el agente funciona y solo se extrañan cuando no.

El campo 6 es la pieza que permite que autonomía y control se decidan por agente y no como
política global. Sin él, la única forma de regular el sistema es un interruptor único, y ese
interruptor termina siempre en la misma posición: siempre encendido o siempre apagado.

La denegación por defecto en herramientas es la única postura defendible cuando el sistema
puede crear agentes nuevos: un agente generado automáticamente no puede heredar permisos que
nadie le otorgó explícitamente.

## Consecuencias

**A favor.** Todo agente es auditable, presupuestable y comparable. Agent Factory se vuelve
implementable. El modelo de permisos y el de control tienen ahora dónde apoyarse. La
trazabilidad de una ejecución es reconstruible sin depender de logs sueltos.

**En contra.** Crear un agente pasa a ser caro. Trece campos obligatorios desalientan la
experimentación rápida, y va a haber presión para completar campos con valores de relleno
solo para poder avanzar: un criterio de terminación vago o un presupuesto arbitrario cumplen
la forma y vacían el fondo. La disciplina no la garantiza el contrato.

**Consecuencia no obvia.** El campo 8 obliga a tener una noción de costo antes de decidir el
stack, cuando lo habitual es al revés. Se asume deliberadamente: un sistema que puede lanzar
ejecuciones en cadena sin techo declarado es un riesgo económico abierto.

## Dependencias

**Requiere:** ADR-000, ADR-001.

**Habilita:** el modelo de control y Gates; la capa de verificación; Agent Factory; el modelo
de identidad y permisos; la definición de los Core Agents; y buena parte de los requisitos
que después condicionan el stack.

**Bloquea:** la existencia de agentes sin contrato completo; la asignación implícita de
herramientas; y cualquier ejecución sin presupuesto declarado.

## Decisiones que este ADR deja abiertas

- Quién evalúa el criterio de terminación. Materia del ADR de verificación.
- Qué acciones exigen Gate más allá de lo que declare cada agente. Materia del ADR de
  control.
- Cómo se representan formalmente entrada y salida. Diferido al stack.
- Cómo se fijan los valores concretos de presupuesto. Requiere el modelo económico, sin ADR
  asignado.

## Documentos afectados

**Crea:** `03 - Agent Framework/Agent Framework.md`, que desarrolla este contrato y lo
aplica a los ocho Core Agents.

**Condiciona:** `03 - Agent Framework/Autonomy and HITL.md`, `03 - Agent Framework/Verification.md`,
`05 - Infrastructure/Security.md`.
