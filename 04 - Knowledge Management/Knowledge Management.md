---
titulo: Knowledge Management
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-000, ADR-001, ADR-002, ADR-009, ADR-011]
aliases: [Knowledge Management, Gestión del conocimiento]
---

# Knowledge Management

## Propósito

Operar los planos de conocimiento que ADR-001 nombra y ADR-011 localiza. Este
documento responde una sola pregunta con precisión: **dado un dato cualquiera,
dónde vive y quién manda sobre él**.

## Alcance

Cubre los cuatro planos, la prueba para clasificar un dato nuevo, el flujo de
escritura al Vault y la política de respaldo. No cubre el mecanismo de
reconstrucción de Memory —diferido a V0.2— ni la infraestructura de respaldo
—bloqueada—.

---

## Los cuatro planos

| Plano | Qué contiene | Dónde | Versionado | Autoridad |
|---|---|---|---|---|
| **Vault** | Normas: ADRs, contratos, Agent Definitions, principios | `Software Factory/` | Git | Fuente de verdad de las normas |
| **Operational State** | Hechos: corridas, evidencia, Gates, consumo | `software-factory-state/factory.db` | **No** | Fuente de verdad de los hechos |
| **Context** | Lo que recibe un Agent Run para operar | Efímero, en memoria | No | Ninguna — pertenece a una ejecución |
| **Memory** | Lo que persiste entre corridas | Sin uso en V0.1 | No | **Nunca** — se reconstruye |

Hay un quinto artefacto que no es un plano de conocimiento y conviene nombrarlo
para que nadie lo confunda: el **checkpointer** de LangGraph, en
`checkpoints.db`. Guarda estado de ejecución para reanudar tras fallo. Es mutable
por diseño y **no es evidencia de nada**.

---

## La prueba para clasificar un dato

**Si se regenerara desde cero, ¿se perdería información irrecuperable?**

Sí → es un hecho. Va al Operational State.
No → es una norma. Va al Vault.

Formulada de otra manera, para el caso dudoso: si responde *qué debe pasar*, es
norma. Si responde *qué pasó*, es hecho.

Casos resueltos por esta prueba:

- Un ADR se puede reescribir → norma → Vault.
- Un Plan de Trabajo producido por una corrida → hecho → Operational State.
- El **Contrato** del Plan de Trabajo → norma → Vault.
- El resultado de una verificación → hecho → Operational State.
- Una Agent Definition → norma → Vault.
- El consumo de una corrida → hecho → Operational State.

---

## Reglas del Vault

**Git es la fuente de verdad; Obsidian es visor.** Ninguna operación depende de
Obsidian.

**Ningún agente escribe sin Gate.** Escribir en el Vault es efecto normativo y
dispara el criterio 3 del piso de ADR-004. No existe agente con permiso
permanente, y esa excepción no puede declararse en una Agent Definition.

**Un Gate cubre una entrega completa**, no un archivo. Un agente que produce ocho
documentos somete uno solo.

**Un documento aprobado no se edita para cambiar lo que decide.** Se reemplaza.
Corregir una errata es distinto de cambiar una decisión.

---

## Reglas del Operational State

**No se versiona.** Un hecho no tiene versiones, tiene ocurrencia.

**No se edita ni se borra.** La inmutabilidad la fuerza la base de datos, no la
disciplina de quien programa. El estado actual se deriva de los eventos; una
corrección es un evento nuevo, no una edición.

**Todo hecho tiene corrida y actor.** Un hecho sin identificador de corrida es
huérfano. Un actor vacío o llamado "el sistema" es inadmisible: la trazabilidad
existe para distinguir quién hizo qué.

**Ningún secreto entra.** Como nada se borra, un secreto que entra queda para
siempre. El control por nombres de clave es parcial y se declara parcial.

**Nada se borra en V0.1.** No hay retención ni purga. Cuando el volumen importe,
será un ADR.

---

## Respaldo — R8

El Operational State está fuera de git. **Si se pierde, se pierde toda la
evidencia de todo lo que la fábrica hizo, sin reconstrucción posible desde el
Vault.**

Es la contrapartida honesta de separar hechos de normas, y no tiene mitigación
automática hasta que exista Infrastructure, hoy bloqueado.

**Mientras tanto:** respaldo manual, responsabilidad del CEO, copia del archivo a
otro disco después de cada sesión de trabajo. `checkpoints.db` no necesita
respaldo: perderlo solo obliga a relanzar corridas en curso.

Es el riesgo más concreto que la fábrica tiene hoy y el único cuya mitigación
depende de un documento bloqueado.

---

## Memory

**Sin uso en V0.1.** Cada Agent Run parte sin conocimiento de los anteriores.

**Diferida a V0.2**, con alcance ya definido: lectura de los Planes de Trabajo
**aprobados** de corridas anteriores, desde el Operational State.

Dos restricciones que ya están decididas y conviene que no se pierdan:

**Los planes rechazados nunca entran a Memory.** Sin una razón registrada de por
qué se rechazaron, no son material de aprendizaje.

**Memory se reconstruye desde el Operational State, nunca desde el Vault ni desde
una carpeta propia del agente.** Un agente con su propia carpeta de conocimiento
sería un quinto plano sin autoridad declarada, y su contenido divergiría en
silencio de los hechos.

Se difiere porque hasta V0.3 no existe verificación sustantiva, y sin ella un
plan defectuoso que fue aprobado una vez se convierte en plantilla de los
siguientes.

## Decisiones tomadas

1. La prueba de clasificación es la regeneración: qué se perdería.
2. El checkpointer no es un plano de conocimiento y no es evidencia.
3. El respaldo del Operational State es manual y del CEO hasta que exista
   Infrastructure.
4. Memory se reconstruye desde el Operational State, y solo desde planes
   aprobados.

## Decisiones abiertas

1. **Mecanismo de reconstrucción de Memory.** V0.2.
2. **Respaldo automático.** Infrastructure, bloqueado.
3. **Retención y purga.** Diferido hasta que el volumen lo justifique.
4. **Búsqueda sobre el Vault.** Ningún agente la necesita hoy: el alcance de
   lectura es una lista cerrada de documentos.

## Impacto en otros documentos

**ADR-011** — queda ejecutada su cláusula "Crea:". **ADR-001** — la separación
normas/hechos pasa de conceptual a operativa. **Runbook V0.1** — la sección de
respaldo deriva de acá. **Infrastructure** (bloqueado) — hereda R8 como su
primera obligación.
