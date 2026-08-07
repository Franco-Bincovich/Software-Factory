---
titulo: Principles
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-000, ADR-001, ADR-002, ADR-004, ADR-005]
aliases: [Principles, Principios]
---

# Principles

## Propósito

La lista canónica de principios de la fábrica. ADR-001 establece que existe una
sola y que vive acá. Cualquier otra enumeración de principios en el vault es
narrativa, no norma.

## Alcance

Un principio entra en esta lista solo si **decide algo**: si su ausencia haría
que alguna decisión concreta se tomara distinto. Los enunciados que suenan bien y
no cambian ninguna decisión no son principios, son decoración.

Cada uno declara qué decide. Si no se puede escribir esa línea, el principio no
entra.

**Estos principios gobiernan cómo opera la fábrica.** No gobiernan el software
que la fábrica produce: eso lo hacen los cuatro criterios de la Constitución
Técnica. Ver "Relación con la Constitución Técnica" al final.

---

## Precedencia

Los principios entran en conflicto. Cuando pasa, gana el nivel más alto.

| Nivel | Qué protege | Principios |
|---|---|---|
| **1** | **Verificabilidad** — que se pueda saber si algo está bien | 4, 5, 8 |
| **2** | **Trazabilidad** — que se pueda saber qué pasó y quién lo hizo | 3, 6, 7 |
| **3** | **Corrección** — que lo construido no hipoteque lo que viene | 1, 2 |
| **4** | **Honestidad** — que lo escrito sea verdad | 9, 10 |
| **5** | **Avance** — que el proyecto llegue a algún lado | 11, 12 |

El orden no es arbitrario. Si la verificabilidad cae, ningún otro principio se
puede comprobar: una fábrica que no puede decir si su trabajo está bien no tiene
nada que trazar, corregir ni documentar honestamente.

Avance va último a propósito. **El timebox nunca justifica saltear una
verificación.** Cuando el plazo aprieta, se recorta alcance — que es exactamente
lo que el principio 12 dice.

---

## Los doce principios

### 1. Arquitectura antes que implementación

Ninguna decisión de tecnología se toma antes de que estén cerradas las
decisiones arquitectónicas que la condicionan.

*Decide:* qué se puede escribir hoy y qué queda bloqueado. Es lo que mantiene a
Technology Stack e Infrastructure fuera del camino hasta que la Secuencia de
decisión los libere.

### 2. Calidad y mantenibilidad por encima de velocidad

Una solución rápida que hipoteca la evolución se rechaza, y se dice por qué.

*Decide:* que V0.1 se construya sobre LangGraph aunque con un solo agente esté
sobredimensionado. Reescribir el armazón después cuesta más que hacerlo bien
ahora.

### 3. Autonomía progresiva

Toda capacidad autónoma llega acompañada de tres cosas declaradas: qué decide el
agente solo, qué requiere aprobación humana, y qué evidencia queda registrada.

*Decide:* que ninguna Agent Definition existe sin el campo 6 de ADR-003
completo, y que el Autonomy Level sube con historial de corridas verificadas, no
por decisión.

### 4. El productor nunca aprueba su propio trabajo

Ningún Agent Run evalúa su propio criterio de terminación, ni el de otro Agent
Run que él mismo originó.

*Decide:* que el verificador estructural lo ejecute la plataforma y no el agente,
y que el agente no tenga esa herramienta en su lista autorizada.

### 5. El silencio nunca aprueba

Un Gate sin responder bloquea indefinidamente. No hay vencimiento, no hay valor
por defecto, no hay rama de "si no responde".

*Decide:* que el motor de Gates no contenga ningún parámetro de expiración, y que
un proceso frenado en un Gate termine en vez de quedarse vivo esperando.

### 6. Conocimiento como activo de primera clase

Toda decisión relevante se expresa como ADR, con contexto, opciones, decisión,
consecuencias, y qué habilita o bloquea.

*Decide:* que una elección tomada en conversación —LangGraph fue el caso— sea
deuda hasta que exista su ADR.

### 7. Las normas viven en el Vault; los hechos, en el Operational State

Lo que responde "qué debe pasar" es norma. Lo que responde "qué pasó" es hecho.
No comparten domicilio ni autoridad.

*Decide:* que los Planes de Trabajo producidos no se guarden en el Vault, y que
el Operational State quede fuera de control de versiones.

### 8. Los hechos no se editan

Un evento registrado no se modifica ni se borra. El estado actual se deriva de
sus eventos; una corrección es un evento nuevo.

*Decide:* que la inmutabilidad la fuerce la base de datos y no la disciplina de
quien programa.

### 9. Documentación que miente es peor que documentación ausente

Un documento que diverge de la implementación causa más daño que su inexistencia,
porque se le cree.

*Decide:* que un campo se llene solo cuando tenga valor verdadero. Nada de
marcadores de relleno, nada de estimaciones sin datos, nada de campos con
placeholder. Un campo que no se puede llenar de verdad se declara ausente y se
dice hasta cuándo.

### 10. Los nombres canónicos son honestos

Ningún agente lleva un nombre del vocabulario canónico si no cumple ese rol y
solo ese rol. Un agente que cumple varios lleva otro nombre y se declara
provisional.

*Decide:* que la interpretación de pedidos difusos nazca como Intake Agent en
V0.2 en vez de agregarse al Requirement Agent.

### 11. Las versiones se definen por capacidad, no por documentos

Una versión está terminada cuando la fábrica demuestra con una corrida real que
puede hacer algo que antes no podía.

*Decide:* que Fase 0 haya dejado de cerrar con diecisiete documentos aprobados.

### 12. El plazo es fijo; el alcance es la variable

Al llegar al límite de tiempo declarado, se recorta alcance. No se extiende el
plazo.

*Decide:* que si al día 7 falta una pieza de V0.1, sale en su forma mínima y se
mejora en V0.2.

---

## Relación con la Constitución Técnica

Existen dos conjuntos de principios en el proyecto y **gobiernan objetos
distintos**. No se fusionan y ninguno pisa al otro.

| | Estos doce principios | Los cuatro criterios de la Constitución |
|---|---|---|
| **Gobiernan** | Cómo opera la fábrica | El software que la fábrica produce |
| **Responden** | ¿Puede el agente hacer esto? ¿Está aprobado? ¿Queda registrado? | ¿Es seguro? ¿Escala? ¿Se entiende? ¿Está ordenado? |
| **Los aplica** | La capa de gobierno | El Developer Agent y el QA Agent |
| **Precedencia** | Los cinco niveles de arriba | Seguro → Escalable → Legible → Ordenado |

Un agente decidiendo cómo estructurar un service consulta los criterios de la
Constitución. La plataforma decidiendo si ese trabajo puede aprobarse consulta
estos principios.

### Cuando los dos se tocan

Ocurre en un solo punto: cuando cumplir un criterio de la Constitución exigiría
violar un principio de esta lista.

**Gana esta lista, siempre.** Un artefacto perfectamente seguro y escalable que
el agente aprobó por su cuenta no se acepta. La calidad del producto no compra
excepciones al gobierno de la fábrica — si lo hiciera, cualquier agente podría
justificar cualquier atajo apelando a la calidad de lo que produjo.

## Cómo se modifica esta lista

Agregar, quitar o reformular un principio requiere ADR. La lista no se edita por
conveniencia: cada principio decide cosas concretas, y cambiarlo cambia esas
decisiones.

Modificar la **precedencia** también requiere ADR, y es un cambio más grande que
agregar un principio: cambia cómo se resuelven todos los conflictos futuros.

## Decisiones tomadas

1. Un principio que no decide nada no entra en la lista.
2. Cada principio declara explícitamente qué decide.
3. Modificar la lista requiere ADR.

## Decisiones abiertas

Ninguna.

## Impacto en otros documentos

**ADR-001** — queda satisfecha la referencia a este archivo, que estaba
apuntando al vacío. **ADR-002** — la regla de principios ya tiene destino real.
**Project Master Plan** — el wikilink a Principles pasa a resolver.
