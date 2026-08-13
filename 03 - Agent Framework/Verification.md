---
titulo: Verification
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-003, ADR-004, ADR-005, ADR-011]
aliases: [Verification, Verificación]
---

# Verification

## Propósito

Operar la capa de verificación que ADR-005 decide. El ADR fija que el productor
nunca verifica y que la verificación tiene dos niveles; este documento describe
cómo se escribe un criterio verificable, qué se comprueba en cada nivel, y qué
queda descubierto hoy.

## Alcance

Cubre la escritura de Acceptance Criteria, los dos niveles de verificación, el
tratamiento del rechazo y la evidencia. No cubre quién es el agente verificador
—eso llega en V0.3— ni la cobertura de tests como métrica, que no es materia de
este documento.

---

## Cómo se escribe un criterio verificable

Tres partes obligatorias. Falta una, no es un criterio.

**Condición observable.** Qué se mira. No qué se pretende: qué se mira.
**Resultado esperado.** Binario. Sin grados, sin "en gran medida".
**Procedimiento.** Cómo se mira. Alguien que no escribió el plan tiene que poder
ejecutarlo sin preguntar nada.

### Ejemplos

**Válido:** dado un archivo con dos filas de legajo 4471, la salida reporta ambas
con su número de fila. Se comprueba corriendo la herramienta sobre el archivo de
prueba y contando las filas del reporte.

**Inválido:** *maneja bien los duplicados.* No es observable, no es binario, no
dice cómo comprobarlo.

**Inválido y peligroso:** *el código es de buena calidad.* Tiene forma de
criterio y no lo es. Este tipo pasa la verificación estructural, porque la
estructural comprueba presencia y no calidad.

### Un criterio que no se puede escribir es una señal

Si las tres partes no se pueden escribir, el problema no es el criterio: es que
el requerimiento es ambiguo. Dispara el criterio 6 del piso de ADR-004 y se
escala. No se escribe un criterio vago para poder seguir.

---

## Los dos niveles

### Verificación estructural

Mecánica, sin agente, sobre la forma del artefacto. Disponible desde V0.1.

Comprueba: que toda unidad tenga criterio, que todo criterio tenga sus tres
partes, que las dependencias existan y no formen ciclos, que todo sea rastreable
al pedido, y que nada caiga en el alcance excluido.

**Dos de esas comprobaciones son parciales, y hay que saberlo.** La de las tres
partes verifica presencia, no calidad. La de alcance excluido detecta
coincidencia de palabras, no de significado: un plan que viola el alcance usando
otras palabras pasa.

### Verificación sustantiva

Ejecución real del artefacto contra sus dependencias, sus fuentes y sus casos
borde. Requiere agente verificador. **Diferida a V0.3.**

Detecta lo que la estructural no puede: fallo silencioso, degradación sin alarma,
divergencia entre lo documentado y lo implementado.

---

## Lo que hoy queda descubierto

Entre V0.1 y V0.3, la fábrica **puede aprobar artefactos con defectos reales**.
No es un riesgo teórico: es el patrón exacto del agente externo que motivó
REV-001, donde un componente muerto no emitía error, una fuente quedaba
permanentemente vieja con peso completo, y los pesos se redistribuían en
silencio.

Nada de eso lo detecta comparar un artefacto contra su propia especificación.

**El único control sustantivo durante ese período es la aprobación humana en el
Gate de salida.** Por eso ese Gate no puede tratarse como formalidad, y por eso
el Runbook indica explícitamente qué mirar al resolverlo.

---

## Tratamiento del rechazo

Un rechazo **nombra el criterio incumplido y dónde**. Un rechazo que no localiza
el problema es inutilizable: manda al productor a corregir a ciegas, o peor, a
corregir cosas que estaban bien.

Una verificación fallida **no es un fallo del agente** en el sentido del campo 9
de ADR-003. Devuelve el trabajo con la lista completa de incumplimientos —no el
primero— para que se corrija en una sola iteración.

---

## Evidencia

Cada comprobación registra: qué criterio, qué procedimiento se aplicó, qué
resultado, sobre qué versión del artefacto, y quién o qué la ejecutó. Vive en el
Operational State.

Sin ese registro no hay forma de responder después por qué algo se aprobó, y una
aprobación de la que no se puede rendir cuentas no vale nada.

---

## Lo que no es verificación

**Cobertura de tests.** Mide qué porción del código se ejecutó, no si hace lo
correcto. El agente externo de REV-001 tenía tests que pasaban.

**Que el artefacto corra sin errores.** Correr sin errores y estar roto en
silencio es exactamente el modo de falla que preocupa.

**Que el agente diga que terminó.** El campo 7 de ADR-003 lo prohíbe
explícitamente.

## Decisiones tomadas

1. Un criterio sin las tres partes no es válido.
2. Un criterio que no se puede escribir es señal de ambigüedad, no de criterio
   defectuoso.
3. Las comprobaciones parciales se declaran parciales.
4. El rechazo devuelve la lista completa, no el primer incumplimiento.
5. Cobertura de tests no es evidencia de corrección.

## Decisiones abiertas

1. **Quién es el agente verificador.** V0.3.
2. **Cómo se verifica sustantivamente un artefacto que depende de fuentes
   externas vivas.** Es el caso difícil y es el que REV-001 expone.
3. **Qué se hace cuando la verificación sustantiva y la estructural discrepan.**
   No puede ocurrir en V0.1 porque la sustantiva no existe.

## Impacto en otros documentos

[[ADR-005]] — queda ejecutada su cláusula "Crea:". **Contrato del Plan de
Trabajo** — sus siete reglas de validez son la aplicación de este documento.
**Quality** (pendiente) — debe partir de la distinción entre los dos niveles y no
tratar cobertura como corrección. [[Runbook V0.1]] — la sección del Gate de
salida deriva de acá.
