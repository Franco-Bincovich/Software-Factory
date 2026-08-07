---
titulo: ADR-005 - Capa de verificacion y Acceptance Criteria
tipo: adr
estado: aceptado
aprobado: 2026-08-06
version: 1.0
owner: CEO
actualizado: 2026-08-06
adr: [ADR-001, ADR-003, ADR-004, ADR-011]
aliases: [ADR-005]
---

# ADR-005 — Capa de verificación y Acceptance Criteria

Cierra el punto 3 de la Secuencia de decisión del Project Master Plan.

## Contexto

R1 —nadie verifica de verdad lo que producen los agentes— es el riesgo más
serio del proyecto y sigue abierto. ADR-003 ya prohíbe la autoevaluación: el
campo 7 establece que el criterio de terminación "no puede ser evaluada por el
propio Agent Run". Pero no dice quién la evalúa, contra qué, ni dónde queda la
evidencia. Una prohibición sin mecanismo es una intención.

La revisión del agente de sentimiento externo (REV-001) aportó el caso concreto.
Ese agente tenía tests unitarios que pasaban y un documento de diseño completo, y
aun así corría con un tercio de su función muerta sin emitir un solo error: el
componente de noticias quedaba excluido y los pesos se redistribuían en silencio,
el VIX quedaba permanentemente viejo con peso completo, y el código y el
documento habían divergido en tres puntos. Ninguno de esos defectos lo detecta un
test unitario, y ninguno lo detecta comparar el artefacto contra su propia
especificación. Es la evidencia de que existen dos niveles de verificación
distintos y de que confundirlos produce aprobaciones falsas.

## Opciones consideradas

**A. Verificación como responsabilidad del agente productor.** Cada Agent
Definition declara cómo verifica lo suyo. Descartada: contradice el campo 7 de
ADR-003 y reproduce exactamente R1.

**B. Verificación como agente separado desde el inicio (QA Agent).** Correcta a
término, pero exige que exista un segundo agente antes de que exista el primero.
Inviable como punto de partida.

**C. Verificación como capacidad de plataforma, con agentes verificadores
incorporándose por versión.** La verificación estructural es mecánica y no
requiere agente; la verificación sustantiva sí, y llega cuando el QA Agent
exista. Elegida.

## Decisión

### 1. Los Acceptance Criteria viajan en la tarjeta de la tarea

No en un documento aparte, no en el contexto del agente, no en el prompt. La
unidad de trabajo lleva escritos adentro los criterios contra los que va a ser
juzgada. Un artefacto sin criterios declarados en su propia tarjeta no es
verificable y no se produce.

### 2. Un Acceptance Criterion válido cumple tres condiciones

- **Observable.** Se comprueba mirando el artefacto o ejecutándolo, no
  razonando sobre la intención de quien lo pidió.
- **Binario.** Se cumple o no se cumple. No admite grados ni "en gran medida".
- **Con procedimiento declarado.** Dice cómo se comprueba, no solo qué debe
  pasar.

Un criterio que no puede escribirse cumpliendo las tres condiciones no es un
criterio defectuoso: es la señal de que el requerimiento es ambiguo, y dispara
Gate por el criterio 6 del piso obligatorio de ADR-004.

### 3. El productor nunca es el verificador

Ningún Agent Run evalúa su propio criterio de terminación, ni el de otro Agent
Run que él mismo haya originado. Reafirma el campo 7 de ADR-003 y le da
mecanismo.

### 4. La verificación tiene dos niveles, y son distintos

**Verificación estructural.** Mecánica, sin agente, sobre la forma del
artefacto. Es capacidad de plataforma desde V0.1. Rechaza cuando:

1. Alguna unidad de trabajo carece de Acceptance Criteria.
2. Algún criterio no cumple las tres condiciones del punto 2.
3. Hay dependencia declarada hacia una unidad que no existe.
4. Hay contenido no rastreable a una frase del pedido original.
5. Hay alcance que el pedido excluyó explícitamente.

**Verificación sustantiva.** Ejecución real del artefacto contra sus
dependencias, sus fuentes y sus casos borde. Detecta lo que la estructural no
puede: fallo silencioso, degradación sin alarma, divergencia entre documento e
implementación. Requiere agente verificador.

### 5. La verificación sustantiva se difiere a V0.3

Es alcance diferido, no omisión. Se difiere porque exige el QA Agent y un
artefacto ejecutable, y V0.1 no produce ninguno de los dos.

Consecuencia que se asume explícitamente: **entre V0.1 y V0.2, la fábrica puede
aprobar artefactos con defectos del tipo encontrado en REV-001.** Mientras dure,
la aprobación humana en el Gate de salida es el único control sustantivo y no
puede tratarse como formalidad.

### 6. El rechazo nombra el criterio incumplido

Una verificación fallida no es un fallo del agente en el sentido del campo 9 de
ADR-003. Devuelve el trabajo al productor identificando qué criterio no se
cumplió y por qué. Un rechazo que no nombra el criterio es un rechazo
inutilizable.

### 7. Toda verificación deja evidencia

Cada comprobación registra: qué criterio, qué procedimiento se aplicó, qué
resultado, sobre qué versión del artefacto, y quién o qué la ejecutó. Es un
hecho, no una norma: vive en el Operational State según ADR-001. **Su
localización concreta depende de ADR-011 y este ADR no la resuelve.**

## Consecuencias

**Lo que habilita.** La verificación estructural es construible sin agentes y sin
haber resuelto el stack, así que V0.1 puede arrancar. Las tres condiciones del
punto 2 le dan al Requirement Agent un criterio objetivo de calidad de su propia
salida. El punto 1 convierte la tarjeta de tarea en el contrato de handoff entre
agentes, que es lo que V0.2 necesita.

**Lo que cuesta.** Un plan bien formado puede ser malo y pasa la verificación
estructural. Todo lo que produzca V0.1 se lee entero. Escribir criterios que
cumplan las tres condiciones es más lento que escribir criterios vagos, y esa
lentitud es deliberada.

**Lo que no cubre.** Nada de lo que exige ejecutar el artefacto. Hasta V0.3, la
fábrica verifica forma, no funcionamiento.

## Decisiones que habilita

- ADR-008 — primer corte de V1: ya puede definir qué significa "entregado".
- Agent Framework: el contrato de tarea del punto 1 es su insumo directo.
- V0.1 T6 y T7: esquema del plan de trabajo y verificador estructural.

## Decisiones que bloquea o depende

- **Depende de ADR-011.** El punto 7 exige un lugar para la evidencia y ADR-001
  solo dice que vive fuera del Vault. Hasta que ADR-011 cierre, la evidencia no
  tiene domicilio.
- **Bloquea a Quality** (pendiente): cobertura de tests no es evidencia de
  corrección. Ese documento debe partir de la distinción del punto 4.
- **No resuelve** quién es el agente verificador ni cómo se compone con el
  productor. Eso es ADR-007 y V0.3.

## Crea

- `03 - Agent Framework/Verification.md` — documento normativo derivado.
