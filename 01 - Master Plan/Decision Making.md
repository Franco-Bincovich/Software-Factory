---
titulo: Decision Making
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-000, ADR-001, ADR-002, ADR-004]
aliases: [Decision Making, Toma de decisiones]
---

# Decision Making

## Propósito

Definir qué es una decisión en este proyecto, cómo se toma, quién la aprueba,
cómo se registra y cómo se revierte.

## Alcance

Cubre las decisiones sobre la fábrica: arquitectura, alcance, contratos, permisos.
No cubre las decisiones que la fábrica toma durante una corrida —eso es Autonomy
and HITL— ni las de un proyecto concreto.

---

## Qué cuenta como decisión registrable

Una elección es registrable si cumple al menos una:

- **Condiciona decisiones futuras.** Elegir orquestador condiciona todo lo que se
  construya encima.
- **Es costosa de revertir.** Cambiar dónde viven los hechos después de mil
  corridas es caro.
- **Establece una restricción sobre agentes.** Todo lo que un agente puede o no
  puede hacer.
- **Define una frontera entre componentes.** Quién manda sobre qué.

Lo que no cumple ninguna es **implementación**, y no requiere ADR: qué motor de
base de datos concreto, cómo se llama una función, qué estructura interna tiene un
módulo.

**La prueba práctica:** si dentro de seis meses alguien pregunta "¿por qué esto es
así?" y la respuesta importa, es una decisión.

---

## Cómo se toma

### 1. Llega pre-cerrada

Se trae **una** recomendación fundada, con sus alternativas descartadas y el
motivo del descarte. No un menú de opciones para que el CEO elija.

Un menú traslada el trabajo de analizar a quien delegó ese trabajo. Si hay
genuinamente dos caminos defendibles, se recomienda uno y se dice qué haría
cambiar de opinión.

### 2. Se aprueba, se corrige o se rechaza

El CEO es hoy el único aprobador. Tres respuestas posibles, ninguna de ellas es
el silencio.

### 3. Se registra antes de construir sobre ella

Una decisión aprobada y no registrada es deuda. Vale mientras nadie la
contradiga, y cuando alguien la contradiga no habrá forma de saber quién tenía
razón.

---

## Estructura de un ADR

Seis partes, todas obligatorias:

**Contexto** — qué problema fuerza la decisión, y por qué ahora.
**Opciones consideradas** — las reales, con el motivo del descarte de cada una.
**Decisión** — qué se decide, en afirmaciones que se puedan verificar.
**Consecuencias** — qué habilita, qué cuesta, qué introduce.
**Decisiones que habilita** — qué se desbloquea.
**Decisiones que no resuelve** — qué queda abierto y con qué destino.

Las dos últimas son las que más se omiten y las que más valen: hacen visible la
secuencia sin que nadie tenga que reconstruirla leyendo todo.

### Sobre las opciones descartadas

**Se registran siempre**, incluso las obviamente malas. Sin ellas, dentro de seis
meses alguien va a proponer exactamente lo que ya se descartó, y no habrá forma de
saber si se descartó por buenas razones o porque no se pensó.

---

## Ciclo de vida de un ADR

**Propuesto** → **Aceptado** → **Reemplazado**

**Un ADR aceptado no se edita para cambiar lo que decide.** Se reemplaza con uno
nuevo que declara a cuál sucede y por qué cambió el análisis.

Corregir una errata no es cambiar una decisión. La prueba: si el cambio hace que
alguien haga algo distinto, es una decisión nueva.

Un ADR reemplazado **no se borra**. Las decisiones que se apoyaron en él siguen
refiriéndose a él.

---

## Secuencia de decisión

Los ADRs pendientes tienen orden declarado en el Project Master Plan, y **ese
orden no se altera sin ADR**.

Existe porque las decisiones se condicionan entre sí: cerrar una en el orden
equivocado significa decidirla sin la información que la anterior aportaba. El
caso concreto fue el plano de los hechos: sin él, ninguna Agent Definition podía
completarse, y eso no era evidente hasta leer el contrato de agente con
detenimiento.

---

## Decisiones diferidas

Una decisión diferida **no es una decisión pendiente**. Se declara con:

- Qué queda sin resolver.
- **A qué versión concreta se difiere.** No "más adelante".
- Qué se asume mientras tanto.
- Qué se rompe si el supuesto resulta falso.

Sin las cuatro, no es un diferimiento: es un olvido con mejor redacción.

Una decisión bien diferida **sale del tablero**. Las que pesan son las pendientes.

---

## Presupuesto de decisiones abiertas

**Máximo tres vivas al mismo tiempo.** Si aparece una cuarta, se cierra una
antes.

No es una preferencia de estilo: un inventario creciente de decisiones abiertas
es el síntoma más confiable de que el proyecto dejó de avanzar, porque cada una
bloquea trabajo y ninguna se resuelve sola.

---

## Cómo se revierte una decisión

Con un ADR nuevo que la reemplace, nunca editando el original.

El ADR de reversión declara: qué cambió en el análisis, qué evidencia nueva
apareció, y qué consecuencias tiene revertir sobre lo ya construido.

**Una decisión no se revierte por incomodidad.** Se revierte porque el análisis
cambió. La distinción importa sobre todo en las reglas que producen fricción a
propósito —el silencio no aprueba es el caso obvio—: el día que molesten, la
pregunta correcta es si el análisis cambió o si simplemente cansan.

## Decisiones tomadas

1. Una elección es registrable si condiciona, es costosa de revertir, restringe
   agentes o define una frontera.
2. Las decisiones llegan pre-cerradas, con una recomendación.
3. Las opciones descartadas se registran siempre.
4. Un ADR aceptado se reemplaza, no se edita.
5. Un diferimiento sin versión concreta no es un diferimiento.
6. Máximo tres decisiones abiertas vivas.

## Decisiones abiertas

1. **Delegación de aprobación.** El CEO es hoy el único aprobador y es un punto
   único de fallo. R3 sigue abierto.
2. **Revisión entre pares de los ADRs.** No existe. Mismo origen que la anterior.

## Impacto en otros documentos

**ADR-000** — este documento desarrolla su regla de que las normas viven
versionadas. **ADR-002** — la estructura de ADRs se apoya en su plantilla.
**Development Methodology** — la disciplina de construcción asume este ciclo.
**Project Master Plan** — la Secuencia de decisión es la aplicación concreta.
