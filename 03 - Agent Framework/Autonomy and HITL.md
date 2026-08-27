---
titulo: Autonomy and HITL
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-003, ADR-004, ADR-009, ADR-010, ADR-011]
aliases: [Autonomy and HITL, HITL]
---

# Autonomy and HITL

## Propósito

Operar el modelo de control que ADR-004 decide. El ADR fija los seis criterios
que exigen Gate; este documento define qué significa autonomía en esta fábrica,
cómo se opera un Gate, y cómo sube el nivel de autonomía de un agente.

## Alcance

Cubre la definición de autonomía, el ciclo de un Gate, la regla de granularidad,
el escalamiento y la progresión de autonomía. No cubre qué se verifica —eso es
Verification— ni los permisos técnicos —eso es ADR-009—.

---

## Qué significa autónomo acá

**Autónomo no es "sin humanos". Es "sin humanos dentro de lo que tiene
permitido".**

Un agente con un perímetro angosto y bien declarado es plenamente autónomo dentro
de él. Un agente sin perímetro declarado no es autónomo: es incontrolado, que es
otra cosa.

Toda Agent Definition declara tres listas —qué decide solo, qué propone, qué
tiene prohibido— y esas tres listas **son** su nivel de autonomía. No hay un
número aparte que lo mida.

---

## Los tres niveles

**Bajo.** Autonomía de método. El agente decide cómo resolver; no decide qué
resolver ni si está terminado. Es donde nace todo agente.

**Medio.** Autonomía de método y de descomposición. El agente decide además cómo
partir el trabajo y en qué orden, dentro de un objetivo dado.

**Alto.** Se suma la aceptación de trabajo intermedio entre agentes, sin Gate
humano en cada traspaso. El Gate humano queda en los extremos.

**Ningún nivel incluye aprobar el propio trabajo.** No hay nivel de autonomía que
lo permita: es el campo 7 de ADR-003 y no admite excepción.

### Cómo se sube de nivel

Con historial de corridas verificadas, no por decisión. Concretamente: un agente
sube cuando existe evidencia registrada de que en ese nivel produjo resultados
que pasaron verificación de forma consistente.

Subir el nivel es ampliar capacidad y dispara el criterio 5 del piso de ADR-004.

---

## Ciclo de un Gate

**Apertura.** Se registra qué se somete, íntegro. El artefacto sometido queda en
la evidencia, no solo la decisión.

**Bloqueo.** La corrida se detiene. El reloj del techo de tiempo se detiene con
ella: esperar a una persona no consume presupuesto.

**Resolución.** Una persona decide. El actor queda registrado. Rechazar exige
motivo; aprobar no.

**Continuación o cierre.** Aprobado, sigue. Rechazado, la corrida termina y el
trabajo parcial se conserva.

### El silencio nunca aprueba

No hay vencimiento. No hay valor por defecto. No hay rama de "si no responde en X
tiempo".

Un Gate sin responder bloquea indefinidamente. Es deliberado, y su consecuencia
práctica es que un proceso frenado en un Gate **termina** en vez de quedarse vivo
esperando: un proceso vivo esperando horas invita a que alguien le agregue un
timeout.

Si alguna vez esta regla se invierte, será por un ADR que reemplace a ADR-004, no
por un parámetro de configuración.

---

## Granularidad: un Gate cubre una entrega

**Un Gate no es por línea, por archivo ni por acción.** Es por entrega.

Un agente que produce ocho documentos deja los ocho listos y somete uno solo:
"esto entra, sí o no". Un agente que escribe cien archivos de código los escribe
todos sin pedir nada, en su carpeta de salida, y somete el artefacto terminado.

La granularidad correcta es la unidad que tiene sentido aprobar o rechazar
entera. Si aprobar la mitad no significa nada, la mitad no es una unidad de Gate.

**Antes de la frontera, el agente es completamente autónomo.** El área de trabajo
del agente no requiere aprobación de nada.

---

## Los dos tipos de Gate

**Del piso obligatorio.** Los seis criterios de ADR-004. Ninguna Agent Definition
puede eliminarlos.

**Propios del agente.** Una Agent Definition puede agregar los suyos. Cuando lo
hace, **debe declararlo explícitamente** y decir que no corresponde al piso.

Esto importa: el Gate de salida del Requirement Agent no está en el piso —aprobar
un plan no es irreversible, no cruza el perímetro, no modifica una norma—. Es un
Gate propio. Leerlo como heredado haría creer que el piso cubre más de lo que
cubre.

**Nota, para quien lo busque y no lo encuentre.** Ese Gate estuvo vigente hasta
V0.2 y ya no existe: la versión 1.1 del [[Requirement Agent]] lo suprime, porque
al encadenarse el [[Developer Agent]] aprobar el plan y después aprobar la
entrega que sale de él es aprobar dos veces lo mismo. **La doctrina de esta
sección no cambia**, y el ejemplo sigue sirviendo justamente por eso: un Gate
propio lo agrega y lo saca la Agent Definition que lo declaró, sin tocar el piso.
Uno del piso no se podría haber sacado así.

---

## Escalamiento

Escalar no es fallar. Es el agente diciendo algo verdadero sobre el trabajo.

| Causa | Qué está diciendo |
|---|---|
| Ambigüedad de requerimiento | El pedido no permite derivar criterios sin adivinar |
| Trabajo demasiado grande | El pedido debería ser dos pedidos |
| Supuesto que invalidaría todo | Falta información de base |
| Techo agotado | El trabajo excedió lo previsto |

**Se escala a un rol nombrado**, nunca a "un humano". El escalamiento transfiere
la decisión, no la identidad: quien resuelve actúa con la suya.

El trabajo en curso se conserva íntegro y la corrida queda suspendida, no
cancelada.

---

## El costo de esto, dicho de frente

Este modelo produce fricción real y crece con el número de agentes. En V0.1 son
dos Gates por corrida; en V1 serán más.

**La respuesta correcta cuando la fricción moleste es reducir el volumen de
Gates, no debilitar la regla.** Reducir volumen significa agrupar mejor las
entregas o subir el nivel de autonomía con evidencia. Debilitar la regla significa
que el silencio empiece a decidir, y ahí la fábrica deja de tener control humano y
pasa a tener un sello.

## Decisiones tomadas

1. Autónomo significa sin humanos dentro del perímetro declarado.
2. Ningún nivel de autonomía incluye aprobar el propio trabajo.
3. Se sube de nivel con evidencia, no por decisión.
4. Un Gate cubre una entrega, no una acción.
5. Los Gates propios de un agente se declaran explícitamente como no heredados.
6. Cuando la fricción moleste, se reduce el volumen, no la regla.

## Decisiones abiertas

1. **Cuánta evidencia hace falta para subir de nivel.** Se define con datos de
   corridas reales; hoy no hay ninguna.
2. **Notificación de Gates.** En V0.1 el CEO consulta manualmente. Un canal de
   aviso llega cuando el volumen lo justifique.
3. **Delegación de aprobación.** Hoy el CEO es el único aprobador. R3 sigue
   abierto.

## Impacto en otros documentos

[[ADR-004]] — queda ejecutada su cláusula "Crea:". [[Agent Framework]] — la regla
de granularidad y el escalamiento se apoyan en este documento. [[Runbook V0.1]] —
la operación de Gates deriva de acá. [[Requirement Agent]] — su Gate de salida se
declara como propio siguiendo esta norma.
