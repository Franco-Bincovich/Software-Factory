---
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-003, ADR-004, ADR-009, ADR-010, ADR-011]
aliases: [ADR-006]
---

# ADR-006 — LangGraph como coordinador

## Contexto

LangGraph venía siendo tratado como decisión tomada desde hace varias sesiones,
sin ADR que la registrara. Era deuda pura: exactamente el antipatrón que este
proyecto existe para evitar.

Al llegar a T14 la deuda dejó de ser formal. LangGraph trae implementaciones
propias de tres cosas que la fábrica ya construyó —persistencia de estado, pausa
para intervención humana, y memoria entre ejecuciones— y sin una decisión
explícita terminaríamos con dos fuentes de verdad para cada una.

Este ADR registra la elección y, sobre todo, **fija qué se delega y qué se
retiene**.

## Opciones consideradas

**A. Orquestación propia.** Máximo control, y es reinventar ejecución durable y
reanudación tras fallo, que son problemas resueltos y difíciles. Descartada.

**B. Hermes Agent.** Descartada en su momento: sin multi-tenancy y sin
seguimiento de costos, dos cosas que R7 y ADR-010 exigen.

**C. LangGraph.** Elegida. Framework de orquestación de bajo nivel para agentes
con estado, con ejecución durable, mecanismo de intervención humana y reanudación
desde el último punto completado. Usable sin el resto del ecosistema LangChain.

## Decisión

### 1. LangGraph es el coordinador de ejecución

Define el grafo de nodos, el orden, las bifurcaciones condicionales y la
reanudación tras fallo. Es la pieza que hace correr un Agent Run.

### 2. LangGraph no es fuente de verdad de nada

Ni de los hechos, ni de las aprobaciones, ni de las normas. Coordina la
ejecución; la verdad vive donde ya está decidido que viva.

### 3. División explícita de responsabilidades

| Capacidad | LangGraph | La fábrica | Autoridad |
|---|---|---|---|
| Orden de ejecución y bifurcaciones | Sí | — | LangGraph |
| Reanudación tras fallo | Checkpointer | — | LangGraph |
| Registro de qué ocurrió | — | Operational State | **La fábrica** |
| Pausa para decisión humana | `interrupt()` | — | LangGraph |
| Autoridad y registro del Gate | — | Motor de Gates | **La fábrica** |
| Medición y corte de presupuesto | — | Contador de presupuesto | **La fábrica** |
| Validación de la Agent Definition | — | Cargador | **La fábrica** |
| Memoria entre corridas | Store | Diferido a V0.2 | Sin uso en V0.1 |

### 4. El checkpointer no es evidencia

El checkpointer guarda **cómo reanudar**: se sobrescribe a medida que la
ejecución avanza. El Operational State guarda **qué pasó**: es inmutable por
diseño, con triggers que impiden modificarlo.

Son cosas distintas y no se fusionan. Un artefacto diseñado para pisarse no puede
ser la evidencia de una fábrica que se audita a sí misma.

### 5. `interrupt()` frena; el motor de Gates decide y registra

La pausa la provee LangGraph. La apertura, la resolución, el actor, el motivo y
la evidencia son del motor de Gates.

Razón concreta: la regla "el vencimiento nunca es aprobación" no puede depender
de la semántica de una librería de terceros. Si LangGraph cambiara su
comportamiento por defecto en una versión, cambiaría una garantía de ADR-004 sin
que nadie lo decidiera.

### 6. No se usan agentes preconstruidos

Nada de constructores que arman un agente completo en una línea. Ocultan el
control del flujo, y en esta fábrica el flujo es precisamente lo que está normado:
qué decide el agente, dónde frena, qué queda registrado.

Se usa la API de grafo explícita: nodos, aristas y estado declarados a mano.

### 7. Versión fija

La versión de LangGraph se fija exactamente en el archivo de dependencias. Nada de
rangos abiertos: un cambio de comportamiento en el mecanismo de interrupción
afectaría a los Gates, y eso no puede llegar por una actualización automática.

Actualizar la versión requiere correr la suite completa antes de fijarla.

### 8. Alcance del ecosistema

Se instala LangGraph solo. No se incorpora LangChain, ni herramientas de
observabilidad del mismo proveedor, ni su plataforma de despliegue. Si alguna
hiciera falta, es una decisión propia y requiere su ADR.

## Consecuencias

**Lo que habilita.** T14 tiene coordinador. La pregunta que ADR-010 dejó abierta
—si una corrida cortada reanuda o recomienza— tiene respuesta: reanuda, porque el
checkpointer lo permite.

**Lo que cuesta.** Es la primera dependencia pesada del repositorio, que hasta
ahora era librería estándar más un validador de esquemas. Arrastra un árbol de
paquetes que no controlamos. Se acepta porque construir ejecución durable propia
es peor negocio.

**Lo que introduce.** Duplicación deliberada: checkpointer y Operational State
guardan cosas parcialmente solapadas. Es intencional y está justificada en el
punto 4, pero es el tipo de cosa que en seis meses alguien va a querer
"simplificar" fusionando. Queda escrito acá que no se fusiona.

## Decisiones que habilita

- V0.1 T14 — armazón de ejecución.
- Agent Framework (pendiente) — el ciclo de vida de un Agent Run ya tiene
  mecanismo.

## Decisiones que no resuelve

- **Despliegue y escalado.** V1 no despliega, según ADR-008.
- **Observabilidad y trazas.** No lo necesita V0.1: el Operational State alcanza.
- **Multi-tenancy.** Es V0.4 y R7.
- **Memoria entre corridas.** V0.2, y se reconstruye desde el Operational State,
  no desde el store de LangGraph.
