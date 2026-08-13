---
titulo: Agent Framework
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-001, ADR-003, ADR-004, ADR-005, ADR-006, ADR-009, ADR-010, ADR-011]
aliases: [Agent Framework]
---

# Agent Framework

## Propósito

Definir el marco que gobierna a todos los agentes: qué los define, cómo nacen,
cómo corren, cómo se comunican y cómo mueren.

ADR-003 declara que este documento existe. No repite el contrato de los trece
campos: lo opera. El ADR decide qué debe cumplir una Agent Definition; este
documento describe qué ocurre alrededor de ella.

## Alcance

Cubre el ciclo de vida de un agente y de una ejecución, el registro de
definiciones, y el protocolo de traspaso entre agentes. No cubre qué agentes
existen —eso es ADR-008— ni cómo se organizan en departamentos —eso es ADR-007,
diferido—.

---

## Las dos entidades

**Agent Definition.** Una norma. Vive en el Vault, versionada en git, aprobada
por un humano. Describe un rol permanente. Cambiarla es un acto normativo.

**Agent Run.** Un hecho. Vive en el Operational State, es inmutable, tiene
identificador propio. Es una ocurrencia de una definición.

Confundirlas es el error más caro posible en este sistema: lleva a editar la
evidencia o a versionar los hechos.

---

## Ciclo de vida de una Agent Definition

**Redacción.** Se escribe con los trece campos completos. Un campo vacío o con
marcador de relleno significa que la definición no existe todavía.

**Aprobación.** Un humano la aprueba. Pasa a `estado: aceptado` con fecha.

**Instanciación.** El cargador la lee, valida los trece campos del cuerpo y los
parámetros operativos del frontmatter, y comprueba la coherencia entre ambos. Si
algo falla, **no arranca**. No hay carga parcial ni valores por defecto.

**Modificación.** Los parámetros operativos —los techos, sobre todo— se editan
sin ADR. Elevar un techo dispara Gate. Modificar el alcance de decisión, las
herramientas o el criterio de terminación es cambiar el contrato y requiere
aprobación explícita.

**Retiro.** Una definición se retira declarándolo en su campo 1. No se borra: las
corridas que la ejecutaron siguen refiriéndose a ella.

### Regla de identidad

Una Agent Definition que cambia de propósito **no es la misma definición**. Se
retira y nace otra con nombre propio. Conservar el nombre mientras el rol cambia
rompe la trazabilidad de todas las corridas anteriores.

---

## Ciclo de vida de un Agent Run

1. **Identificación.** Se genera el identificador antes de consumir nada.
2. **Carga.** Se instancia la Agent Definition. Falla acá significa cero eventos.
3. **Entrada.** Se valida. Una entrada que no valida se rechaza, no se interpreta.
4. **Gates de entrada.** Se someten los que correspondan.
5. **Producción.** El agente trabaja dentro de su alcance de decisión.
6. **Verificación.** La ejecuta la plataforma o un agente verificador. Nunca el
   productor.
7. **Gates de salida.** Se somete el resultado.
8. **Cierre.** Se registra el resultado y se libera.

**En cualquier punto de 5 a 7**, alcanzar un techo corta la corrida y escala. El
trabajo parcial se conserva íntegro.

### Iteración, no regeneración

Cuando la verificación rechaza, el agente **corrige el artefacto existente**. No
produce uno nuevo desde cero. Regenerar íntegramente incumple el campo 9 de
ADR-003 y se trata como agotamiento inmediato.

Es la diferencia entre reintentar y volver a empezar, y es lo que hace que las
iteraciones converjan en vez de dar vueltas.

---

## Registro de Agent Definitions

Todas viven en `03 - Agent Framework/`, un archivo por definición, nombradas con
su nombre canónico.

El cargador es la única puerta de entrada al runtime. **No hay forma de ejecutar
un agente sin pasar por él**, y esa es la garantía de que el contrato de ADR-003
se cumple en ejecución y no solo en el papel.

---

## Protocolo de traspaso

La unidad que viaja entre agentes es el [[Plan de Trabajo]], definido en su propio
contrato. Sus propiedades relevantes acá:

- Los Acceptance Criteria viajan **adentro** de la tarjeta, no en un documento
  aparte.
- Un plan aprobado es **inmutable**. Si el trabajo cambia, se produce un plan
  nuevo que declara a cuál sucede.
- La forma canónica es estructurada; la vista legible es derivada y no
  autoritativa.

Sin inmutabilidad el traspaso no significa nada: el consumidor no puede trabajar
sobre un artefacto que cambia mientras lo consume.

En V0.1 el consumidor es humano y está declarado como temporal en la Agent
Definition. En V0.2 pasa a ser el Developer Agent, sin que el formato cambie.

---

## Permisos

Denegación por defecto, en todos los planos: herramientas, sistema de archivos,
red, repositorios, Vault.

Tres reglas que no admiten excepción declarable:

1. **Ningún agente escribe en el Vault sin Gate.** Es efecto normativo. Un Gate
   cubre una entrega completa, no un archivo.
2. **Ningún agente comparte credencial con una persona.**
3. **Ningún agente actúa en nombre de otro.** El escalamiento transfiere la
   decisión, no la identidad.

---

## Qué justifica un agente nuevo

Un área justifica su propia Agent Definition **solo si tiene reglas, herramientas
y criterios de verificación distintos de todas las demás**.

No alcanza con que sea un área distinta en el organigrama de una empresa humana.
El Deployment Agent existe porque es el único con acceso a ejecución de comandos;
no existe un Backend Agent separado del Frontend porque sus reglas son las
mismas.

## Decisiones tomadas

1. Una definición que cambia de propósito se retira; no se reescribe conservando
   el nombre.
2. El cargador es la única puerta al runtime.
3. La iteración corrige el artefacto existente; regenerar es agotamiento.
4. El Plan de Trabajo es la unidad de traspaso, y es inmutable.
5. Un agente nuevo se justifica por reglas, herramientas y verificación
   distintas, no por analogía organizacional.

## Decisiones abiertas

1. **Composición de agentes.** Cómo se encadenan dos Agent Runs sin intervención
   humana. Es V0.2.
2. **Creación dinámica.** La Agent Factory llega después de V1, cuando el
   contrato esté probado sobre varios agentes reales.
3. **Memoria entre corridas.** V0.2, reconstruida desde el Operational State.

## Impacto en otros documentos

[[ADR-003]] — queda ejecutada su cláusula "Crea:". **Contrato del Plan de
Trabajo** — este documento lo referencia sin reescribirlo. **Requirement Agent**
— es la primera definición sujeta a este marco. **ADR-007** (diferido) — el
modelo organizacional se apoyará en la regla de justificación de agentes.
