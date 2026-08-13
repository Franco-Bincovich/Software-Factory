---
titulo: Architecture
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-000, ADR-001, ADR-003, ADR-004, ADR-005, ADR-006, ADR-009, ADR-010, ADR-011]
aliases: [Architecture, Arquitectura]
---

# Architecture

## Propósito

Describir cómo está compuesta la fábrica: qué capas existen, qué hace cada una y
qué no puede hacer. Es el documento que explica el sistema completo a alguien que
llega nuevo.

## Alcance

Cubre la estructura conceptual y las fronteras entre capas. **No nombra
tecnologías** salvo las ya decididas por ADR, porque Technology Stack sigue
bloqueado.

---

## La idea central

La fábrica **no es un generador de código**. Es una empresa digital operada por
agentes, y la diferencia está en una sola cosa: **la fábrica produce evidencia
además de artefactos**.

Un generador de código produce código. Esta fábrica produce código y, junto a él,
el registro de quién lo pidió, contra qué criterios se aprobó, cuánto costó, qué
se verificó y quién lo autorizó. Si esa evidencia no existiera, el sistema sería
un envoltorio caro alrededor de un modelo.

Todo lo que sigue es la estructura que hace posible esa evidencia.

---

## Las cinco capas

```
   ┌──────────────────────────────────────────────────────┐
   │  INTAKE                                              │
   │  Punto único de ingreso. Valida, no interpreta       │
   └───────────────────────┬──────────────────────────────┘
                           ▼
   ┌──────────────────────────────────────────────────────┐
   │  GOBIERNO                                            │
   │  Gates · presupuesto · identidad · escalamiento      │
   └───────────────────────┬──────────────────────────────┘
                           ▼
   ┌──────────────────────────────────────────────────────┐
   │  ORQUESTACIÓN                                        │
   │  Grafo de ejecución · reanudación tras fallo         │
   └───────────────────────┬──────────────────────────────┘
                           ▼
   ┌──────────────────────────────────────────────────────┐
   │  AGENTES                                             │
   │  Producen. Cada uno con su contrato de trece campos  │
   └───────────────────────┬──────────────────────────────┘
                           ▼
   ┌──────────────────────────────────────────────────────┐
   │  VERIFICACIÓN                                        │
   │  Estructural hoy · sustantiva en V0.3                │
   └──────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────┐
   │  CONOCIMIENTO — atraviesa todas                      │
   │  Vault (normas) · Operational State (hechos)         │
   └──────────────────────────────────────────────────────┘
```

### Intake

Un solo punto de entrada. Ninguna otra vía existe: no hay chat con agentes, no
hay invocación directa.

En V0.1 es un mecanismo que valida un pedido estructurado. En V0.2 pasa a ser un
agente que interpreta lenguaje natural, y el mecanismo sigue existiendo debajo.

**Lo que la capa garantiza:** todo trabajo tiene un origen registrado.

### Gobierno

Decide **cuándo un agente puede seguir**. Cuatro mecanismos:

**Gates** — seis criterios de piso más los propios de cada agente. El silencio
nunca aprueba.
**Presupuesto** — tres techos por corrida, medidos durante, con corte duro.
**Identidad** — cada agente actúa con la suya, con denegación por defecto sobre
todo recurso.
**Escalamiento** — a un rol nombrado, conservando el trabajo en curso.

Esta capa es la que hace que la autonomía sea acotada en vez de ilimitada. Sin
ella no hay fábrica: hay agentes sueltos.

**Lo que la capa garantiza:** ninguna acción relevante ocurre sin autorización o
sin límite.

### Orquestación

Define el orden de ejecución, las bifurcaciones y la reanudación tras fallo. Es
LangGraph, según ADR-006.

**No es fuente de verdad de nada.** Coordina; la verdad vive en la capa de
conocimiento. El estado que la orquestación guarda para reanudar es mutable por
diseño y no es evidencia.

**Lo que la capa garantiza:** una corrida sobrevive a un fallo del proceso.

### Agentes

Producen. Cada uno definido por trece campos obligatorios, sin los cuales no
existe.

Un agente es autónomo dentro de su alcance de decisión declarado, y solo ahí. No
elige qué construir, no cambia su presupuesto, no amplía sus permisos y **no
aprueba su propio trabajo**.

Un área justifica un agente propio solo si tiene reglas, herramientas y criterios
de verificación distintos de todas las demás.

**Lo que la capa garantiza:** ningún agente existe sin contrato completo.

### Verificación

Declara si un artefacto cumple. Nunca la ejecuta quien produjo.

Dos niveles: estructural, mecánica, disponible desde V0.1; y sustantiva, que
ejecuta el artefacto contra el mundo real, diferida a V0.3.

**Lo que la capa garantiza hoy:** que la forma esté bien.
**Lo que no garantiza hasta V0.3:** que funcione.

### Conocimiento

Atraviesa todas las capas y es la más importante para la tesis del sistema.

**Vault** — las normas. Versionado en git, aprobado por humanos.
**Operational State** — los hechos. Fuera de git, inmutable, indexado por corrida.

La separación es rígida a propósito. Sin ella, o los hechos ensucian el historial
normativo, o las normas se vuelven editables por quien corre.

**Lo que la capa garantiza:** cualquier corrida se reconstruye leyendo solo los
hechos registrados.

---

## Las fronteras que no se cruzan

Son cinco, y cada una existe porque su violación rompe algo concreto.

| Frontera | Qué rompe cruzarla |
|---|---|
| El productor no verifica | La verificación deja de significar algo |
| El agente no escribe en el Vault sin Gate | La fábrica puede reescribir las reglas que la limitan |
| Los hechos no se editan | La evidencia deja de ser evidencia |
| El orquestador no es fuente de verdad | Dos versiones de qué pasó, ninguna autoritativa |
| El silencio no aprueba | El control humano se vuelve un sello |

---

## Cómo fluye un trabajo

1. Entra un pedido por Intake. Se valida. Si no valida, se rechaza sin dejar
   corrida.
2. Se abre la corrida con identificador propio, antes de consumir nada.
3. Gate de entrada: se aprueban pedido y techos.
4. Se carga la Agent Definition. Si le falta un campo, no arranca.
5. El agente produce, midiendo consumo contra los tres techos.
6. La plataforma verifica. Si rechaza, el agente **corrige** el artefacto
   existente y reintenta hasta el techo de iteraciones.
7. Gate de salida: se aprueba la entrega.
8. Se cierra la corrida. Todo quedó registrado.

En cualquier punto: alcanzar un techo corta y escala, conservando el trabajo
parcial.

---

## Lo que la arquitectura todavía no resuelve

**Concurrencia.** Un proyecto por vez. El sustrato del Operational State es de
escritor único y la migración está declarada para V0.4.

**Aislamiento entre clientes.** R7 sin mitigar. Por eso V1 es solo interno.

**Composición de agentes.** Cómo se encadenan dos Agent Runs sin humano en el
medio. Es V0.2 y es la prueba de fuego de esta arquitectura: hasta que ocurra, la
fábrica es un agente con gobierno, no una cadena.

**Creación dinámica de agentes.** La Agent Factory llega después de V1.

## Decisiones tomadas

1. Cinco capas más una transversal de conocimiento.
2. La orquestación no es fuente de verdad.
3. Las cinco fronteras no admiten excepción declarable.
4. La evidencia es parte del producto, no un subproducto.

## Decisiones abiertas

1. **Modelo de capas formal** — punto 8 de la Secuencia de decisión, diferido.
2. **Concurrencia y aislamiento** — V0.4.
3. **Composición** — V0.2.

## Impacto en otros documentos

[[Technology Stack]] (bloqueado) — hereda las capacidades que cada capa exige, sin
tecnología asignada. [[Infrastructure]] (bloqueado) — hereda R8 y el requisito de
respaldo del Operational State. [[Agent Framework]] — desarrolla la capa de
agentes. [[Verification]], [[Autonomy and HITL]], [[Knowledge Management]] —
desarrollan sus capas respectivas.
