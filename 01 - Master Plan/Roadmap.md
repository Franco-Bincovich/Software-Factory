---
titulo: Roadmap
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-004, ADR-005, ADR-008, ADR-009, ADR-011]
aliases: [Roadmap]
---

# Roadmap

## Propósito

Declarar la secuencia de versiones, qué capacidad nueva habilita cada una y cómo
se sabe que está terminada.

## Alcance

Cubre de V0.1 a V1. Lo posterior a V1 no se planifica: se decide con la evidencia
de haberlo construido.

---

## La regla que gobierna este documento

**Una versión se define por capacidad operativa demostrada, no por documentos
escritos ni por funcionalidades listadas.**

Está terminada cuando la fábrica hace, con una corrida real, algo que antes no
podía. Un documento aprobado no termina nada. Una funcionalidad implementada
tampoco, si no se demostró corriendo.

Corolario: **cada versión tiene un criterio de terminación binario y observable**.
Si para saber si una versión terminó hay que discutir, el criterio está mal
escrito.

---

## La escalera

### V0.1 — Un agente, un ciclo cerrado, evidencia

**Capacidad nueva:** llevar un pedido desde el ingreso hasta un artefacto
verificado, con un solo agente, sin que el CEO toque código en el medio.

**Qué existe al terminar:** Requirement Agent, formulario de Intake, verificador
estructural, motor de Gates, contador de presupuesto, Operational State, armazón
de ejecución.

**Terminada cuando:** una corrida produce un Plan de Trabajo que pasa la
verificación, con ambos Gates atendidos, y **el plan se ejecuta a mano sin
improvisar ninguna tarea que no previera**. La corrida se reconstruye leyendo solo
el registro.

**Timebox:** 7 días hábiles. Al día 7 se recorta alcance, no se extiende el plazo.

### V0.2 — Cadena de custodia

**Capacidad nueva:** el trabajo pasa de un agente a otro sin humano en el medio.

**Qué se agrega:** Intake Agent —interpretación de pedidos difusos—, Developer
Agent, handoff formal entre agentes, y memoria entre corridas limitada a planes
aprobados.

**Terminada cuando:** un pedido en lenguaje natural se convierte en plan y en
código sin intervención entre etapas, con Gates solo en los extremos.

**Es la prueba de fuego de la arquitectura.** Hasta que ocurra, la fábrica es un
agente con gobierno, no una cadena.

### V0.3 — Verificación que sirve

**Capacidad nueva:** detectar defectos que la verificación estructural no puede
ver — fallo silencioso, degradación sin alarma, divergencia entre lo documentado
y lo implementado.

**Qué se agrega:** QA Agent y verificación sustantiva.

**Terminada cuando:** el QA Agent encuentra los defectos sembrados del agente
externo de REV-001. Dominio ajeno, defectos conocidos, criterio objetivo.

**Por qué acá y no antes:** exige un artefacto ejecutable y un agente verificador,
y ninguno de los dos existe antes de V0.2.

### V0.4 — Identidad, permisos y aislamiento

**Capacidad nueva:** varios proyectos sin contaminarse, con trazabilidad de quién
hizo qué.

**Qué se agrega:** identidad propia por agente con credenciales separadas,
workspace aislado por proyecto, y migración del Operational State a un sustrato
que admita concurrencia.

**Terminada cuando:** dos proyectos corren en secuencia sin contaminarse y el
registro distingue qué agente hizo cada cosa.

**Mitiga R7** parcialmente. Es la condición previa para pensar en terceros.

### V1 — Herramientas internas de punta a punta

**Capacidad nueva:** producir software terminado sin que el CEO escriba código.

**Qué se agrega:** Documentation Agent y Deployment Agent, con despliegue local
en entorno descartable y prueba de humo.

**Terminada cuando:** tres herramientas internas entregadas, cada una nacida de un
pedido por Intake y terminada con su Gate de salida, sin una línea de
implementación escrita por el CEO.

Tres y no una: una puede salir por suerte.

---

## Qué queda fuera de este roadmap

**Trabajo para terceros.** Exige R7 mitigado del todo. Después de V1.

**Agent Factory.** Crear agentes dinámicamente exige que el contrato de ADR-003
esté probado sobre varios agentes reales. En V1 son seis escritos a mano.

**Despliegue remoto.** Exige Security e Infrastructure, hoy bloqueados.

**Departamentos y Roles.** El modelo organizacional no lo necesita nada hasta la
Agent Factory. Seis agentes no son un organigrama.

---

## Cómo se avanza de versión

**No se empieza la siguiente hasta que la anterior demuestre su capacidad.** No
se paraleliza: construir V0.2 mientras V0.1 no corrió significa construir sobre
supuestos.

**Cada versión puede recortar alcance, nunca extender el plazo.** Lo que se cae
del recorte pasa a la siguiente y queda declarado.

**Cada versión es un momento legítimo para parar.** Eso es lo que este documento
existe para dar: la posibilidad de terminar.

## Decisiones tomadas

1. Las versiones se definen por capacidad demostrada.
2. Cada una tiene criterio de terminación binario.
3. No se paralelizan versiones.
4. El plazo es fijo; el alcance es la variable.

## Decisiones abiertas

1. **Timebox de V0.2 a V1.** Se declara al arrancar cada una, con los datos de la
   anterior. Estimarlos hoy sería inventar.
2. **Qué tres herramientas internas para V1.** Se eligen al cerrar V0.4.
3. **Qué viene después de V1.** Se decide con la evidencia de haberlo construido.

## Impacto en otros documentos

[[PLAN-V0.1]] — es el desarrollo detallado del primer peldaño. [[ADR-008]] —
define el corte de V1 y este documento lo ordena en el tiempo. **Project Master
Plan** — el criterio de cierre de Fase 0 apunta acá.
