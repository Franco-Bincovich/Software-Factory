---
estado: aceptado
aprobado: 2026-08-06
version: 1.0
owner: CEO
actualizado: 2026-08-06
adr: [ADR-003, ADR-004, ADR-011]
aliases: [ADR-010]
---

# ADR-010 — Modelo de costo y presupuesto

Cierra el punto 7 de la Secuencia de decisión del Project Master Plan. Es la
mitigación de R2.

## Contexto

El campo 8 de ADR-003 exige tres techos obligatorios —costo, tiempo e
iteraciones— y el criterio 4 del piso de ADR-004 convierte el exceso en Gate.
Falta lo del medio: qué mide cada techo exactamente, cuándo se mide, y qué pasa
en el instante en que se alcanza.

Sin eso, los tres techos son declaraciones. Un agente autónomo en bucle por un
error de reintento es la forma más común y más cara de fallar, y es la que ocurre
sin que nadie la mire, de noche, la primera vez que algo queda corriendo.

## Decisión

### 1. Los techos son por Agent Run

No por proyecto, no por día, no por agente acumulado. Cada corrida arranca con
sus tres techos completos. Un run que termina sin agotarlos no deja saldo para el
siguiente.

### 2. Qué mide cada techo

**Costo** — consumo económico atribuible a la corrida, en moneda. Incluye todo lo
que la corrida haya provocado, no solo lo que consumió directamente.

**Tiempo** — tiempo transcurrido desde el inicio de la corrida, no tiempo de
cómputo. Una corrida esperando la resolución de un Gate no consume tiempo: el
reloj se detiene mientras el trabajo está en manos de una persona, y se reanuda
al retomar. Esperar a un humano no puede ser motivo de corte.

**Iteraciones** — ciclos completos de intento y evaluación. Un intento que
produce un resultado y lo somete a comprobación es una iteración, haya sido
aceptado o rechazado. Es el techo que primero se agota cuando un agente entra en
bucle, y por eso es el que más importa que esté bien puesto.

### 3. Alcanzar cualquiera de los tres corta

No pide permiso, no continúa en modo degradado, no negocia. Corta y escala según
el campo 10 de ADR-003. El Gate del criterio 4 de ADR-004 se abre después del
corte, no en lugar del corte: la aprobación sirve para decidir si se reanuda, no
para permitir que siga mientras se decide.

### 4. Agotar no es fallar

El campo 9 de ADR-003 define el fallo. Agotar un techo es distinto: no es que el
agente se haya equivocado, es que el trabajo excedió lo previsto. El trabajo
parcial se conserva y se registra íntegro. No se descarta, no se revierte.

La distinción importa porque el comportamiento ante fallo incluye reintentos y
agotar un techo nunca debe disparar un reintento automático.

### 5. La medición ocurre durante, no al final

Un techo que se verifica al terminar la corrida no es un techo: es una
estadística. La comprobación es continua y el corte es inmediato.

### 6. Los valores viven en la Agent Definition

Este ADR fija que los techos existen, qué miden y qué pasa al alcanzarlos. Los
números concretos son parámetros de cada Agent Definition y se editan sin ADR.
Elevar uno dispara Gate por el criterio 4 de ADR-004 y queda registrado con su
motivo.

### 7. Un techo elevado repetidamente es un techo mal puesto

Si el mismo techo se eleva tres veces sin que el motivo cambie, el problema no es
el trabajo: es la Agent Definition. Corresponde revisarla, no seguir subiendo.
Que quede escrito evita el desplazamiento silencioso, que es el modo en que los
límites dejan de existir sin que nadie decida eliminarlos.

### 8. Sin techos declarados no se arranca

Los tres son obligatorios según ADR-003. Una Agent Definition sin los tres no
existe, y un pedido que no declare su techo de costo no ingresa.

### 9. Todo consumo se registra

En el Operational State, por corrida, según ADR-011. También el de las corridas
cortadas: especialmente el de las corridas cortadas, que son las que enseñan
dónde estaban mal los números.

## Consecuencias

**Lo que habilita.** R2 pasa a mitigado. La primera corrida instrumentada
produce los datos que hoy no existen para calcular presupuestos reales — hasta
ahora cualquier número habría sido inventado.

**Lo que cuesta.** El corte duro del punto 3 puede interrumpir trabajo casi
terminado y desperdiciarlo. Es deliberado: la alternativa es un límite que cede
bajo presión, que no es un límite. El punto 5 obliga a instrumentar la medición
desde la primera corrida, lo que agrega trabajo a T12.

**Lo que no cubre.** El costo agregado por proyecto, por mes o por cliente. No lo
necesita V0.1 y calcularlo sin datos reales sería inventar. Se difiere hasta
tener corridas medidas.

## Decisiones que habilita

- V0.1 T9 — campo 8 de la Agent Definition.
- V0.1 T12 — contador de presupuesto sobre los tres techos.
- V0.1 T8 — el formulario de Intake puede exigir techo declarado.

## Decisiones que no resuelve

- **Costo agregado y proyección presupuestaria.** Diferido hasta tener datos.
- **Atribución de costo a un cliente.** Es V0.4 y R7.
- **Qué se hace con el trabajo parcial de una corrida cortada** más allá de
  conservarlo: si se reanuda desde ahí o se recomienza. Depende de si existe
  checkpointing, que es una decisión de Agent Framework todavía abierta.
