---
titulo: Objectives
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-008, ADR-010, ADR-011]
aliases: [Objectives, Objetivos]
---

# Objectives

## Propósito

Traducir los modos de falla de Vision en métricas medibles, con línea base
declarada y umbral de fracaso.

## Alcance

Cubre qué se mide, contra qué, y cuándo la medición existe. **No fija metas para
métricas sin línea base**: una meta sin punto de partida es un número inventado
con apariencia de objetivo.

---

## Advertencia sobre las líneas base

**Casi ninguna existe todavía.** Hay un solo dato real —el proyecto de
referencia— y un dato estimado —las horas semanales—. Todo lo demás se mide
recién cuando la fábrica corra.

Se declara así a propósito. Fijar metas sobre números inventados produce
objetivos que se cumplen o se incumplen sin que nadie sepa qué significó.

---

## O1 — Horas del fundador en producción

**El objetivo madre.** Vision dice que el problema es el tiempo del fundador; si
esta métrica no se mueve, nada de lo demás importa.

| | |
|---|---|
| **Línea base** | ~7 de 8 horas laborables diarias, en desarrollo asistido manual |
| **Qué mide** | Horas dedicadas a **producir**: escribir prompts de implementación, revisar código generado, corregir, integrar |
| **Qué no cuenta** | Horas dedicadas a **decidir**: resolver Gates, aprobar planes, revisar entregas |
| **Medible desde** | V0.1, de forma manual. Automatizable después |

La distinción entre producir y decidir es la métrica real. **El objetivo no es
llegar a cero horas**: es que las horas que queden sean de decisión y no de
ejecución.

**Umbral de fracaso:** que las horas de decisión superen a las horas de
producción que reemplazaron. Si supervisar la fábrica cuesta más que hacerlo a
mano, la fábrica es un costo neto.

## O2 — Costo por entrega

| | |
|---|---|
| **Ancla** | USD 415 por un desarrollo chico completo — backend, frontend, envío y recepción de mails, lectura de PDF. 35 horas × ARS 17.800 |
| **Qué mide** | Costo total de producir un artefacto equivalente con la fábrica |
| **Qué incluye** | Consumo de los agentes **más** las horas del fundador valorizadas |
| **Medible desde** | V0.1 parcialmente —consumo instrumentado—; completo en V1 |

**El costo de la fábrica no es solo lo que consumen los agentes.** Una entrega que
cuesta USD 20 de consumo y 20 horas de revisión cuesta más que el ancla. La
comparación honesta suma ambas cosas, y por eso O1 y O2 se leen juntas.

**Umbral de fracaso:** costo total por encima del ancla, de forma sostenida.

**Sobre el ancla:** es un dato real y único. Sirve como punto de comparación, no
como promedio. Un segundo proyecto de referencia lo vuelve más confiable.

## O3 — Retrabajo tras revisión

Traduce el criterio de calidad del fundador a algo medible.

**Dos clases de defecto, y solo una cuenta:**

| Clase | Qué es | Cuenta |
|---|---|---|
| **Superficie** | Colores, tipografía, estilo de un botón, decisiones estéticas | **No** |
| **Sustancia** | Función incorrecta o faltante, estructura mal resuelta, seguridad, algo que hay que rehacer | **Sí** |

| | |
|---|---|
| **Línea base** | No existe. Se establece con la primera entrega de la fábrica |
| **Qué mide** | Proporción del artefacto que hay que rehacer por defectos de sustancia, tras la revisión manual previa a producción |
| **Umbral de fracaso** | Más del 50% a rehacer |
| **Objetivo declarado** | Que la revisión manual no encuentre defectos de sustancia |
| **Medible desde** | La primera entrega real, V1 |

El umbral de fracaso y el objetivo están deliberadamente lejos uno del otro. El
umbral marca dónde la fábrica no sirve; el objetivo, dónde se quiere llegar. **La
métrica útil es la tendencia entre ambos**, no el valor de una entrega aislada.

## O4 — Tiempo de ciclo

| | |
|---|---|
| **Ancla** | 35 horas de trabajo humano para el proyecto de referencia |
| **Qué mide** | Tiempo entre el pedido por Intake y la entrega aprobada, incluyendo las esperas en Gates |
| **Medible desde** | V0.1 — los Gates dejan marca de apertura y resolución |

Incluye las esperas a propósito. Una fábrica que produce en diez minutos y espera
tres días una aprobación tiene un problema de ciclo real, aunque el consumo sea
bajo.

**Sin meta declarada** hasta tener corridas medidas.

## O5 — Costo de extender la fábrica

Mide el modo de falla 4 de Vision: que agregar algo nuevo sea más difícil que
hacerlo a mano.

| | |
|---|---|
| **Línea base** | No existe. Se establece comparando el esfuerzo de V0.1 con el de V0.2 |
| **Qué mide** | Tiempo entre decidir una capacidad nueva y tenerla funcionando |
| **Umbral de fracaso** | Que crezca versión a versión sin que la capacidad crezca proporcionalmente |
| **Medible desde** | V0.2, que es la primera comparación posible |

Es el objetivo más difícil de medir y el que detecta la falla más silenciosa. Una
fábrica que se endurece no falla: se deja de usar.

---

## Objetivos de doce meses

Dos, declarados por el fundador. **Están a distancias muy distintas.**

### Personal — una empresa a la que pedirle ayuda

Poder delegar desarrollos propios sin que consuman tiempo del fundador.

**Es alcanzable con V1.** Herramientas internas, sin terceros, sin aislamiento
entre clientes. Es exactamente lo que ADR-008 define como corte de V1.

### Laboral — entregar a un cliente algo hecho 100% por la fábrica

**Está más lejos que V1**, y conviene decirlo ahora.

Trabajar para terceros exige aislamiento entre clientes —R7— que el roadmap
difiere a V0.4 y que ADR-008 deja explícitamente fuera de V1. V1 produce
herramientas internas.

Hay tres caminos y **la decisión no está tomada**:

1. **Ampliar V1** para incluir un cliente. Rompe el corte ya decidido y agrega
   riesgo a la versión que tiene que demostrar la tesis.
2. **Agregar una versión posterior a V1** dentro de los doce meses. Mantiene el
   corte y estira el plazo.
3. **Aceptar que el objetivo laboral cae fuera de los doce meses.**

Se decide cuando V0.1 esté corriendo y haya datos de velocidad real. Decidirlo
hoy sería elegir sobre una estimación sin base.

---

## Lo que deliberadamente no se mide

**Cantidad de código producido.** No mide valor y premia lo contrario de lo que
se busca.

**Cobertura de tests.** Mide qué porción del código se ejecutó, no si hace lo
correcto.

**Cantidad de agentes.** Un agente que no se justifica por reglas propias es
costo, no capacidad.

**Documentos escritos.** Es el criterio que ya se reemplazó una vez, y por buenas
razones.

## Decisiones tomadas

1. La métrica madre son las horas del fundador, separando producir de decidir.
2. El costo por entrega incluye las horas del fundador valorizadas, no solo el
   consumo de los agentes.
3. Los defectos de superficie no cuentan como retrabajo; los de sustancia sí.
4. No se fijan metas para métricas sin línea base.
5. El objetivo laboral de doce meses está fuera del alcance de V1 y su
   resolución queda abierta.

## Decisiones abiertas

1. **Cómo se alcanza el objetivo laboral de doce meses.** Tres caminos
   planteados, ninguno elegido. Se decide con datos de V0.1.
2. **Meta concreta de O1.** Cuántas horas de decisión son aceptables. Se fija
   tras las primeras corridas.
3. **Cómo se instrumenta O1.** Hoy sería registro manual del fundador.

## Impacto en otros documentos

[[Vision]] — este documento traduce sus cuatro modos de falla en métricas.
[[ADR-010]] — el consumo instrumentado es el insumo de O2. [[ADR-008]] — la
tensión del objetivo laboral apunta a su corte de V1. [[Roadmap]] — si se elige
el camino 2, hay que agregarle una versión.
