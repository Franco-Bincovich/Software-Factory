---
titulo: Metodología manual (en retiro)
tipo: guia
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-003, ADR-005, ADR-011]
aliases: [Metodología manual]
---

# Metodología manual (en retiro)

Estas reglas gobiernan el desarrollo asistido manual. **La fábrica las
reemplaza por mecanismo.** No se borran de golpe: cada una se retira
cuando su contraparte automática esté funcionando, para que ninguna
desaparezca dejando un hueco que nadie note.

## Mapa de retiro

| Regla manual | Qué la reemplaza | Versión |
|---|---|---|
| Nunca diagnosticar e implementar en la misma sesión | Requirement Agent y Developer Agent separados | V0.2 |
| Una tarea atómica por sesión | Unidad de trabajo del Plan de Trabajo | V0.1 |
| Estructura de un buen prompt | Tarjeta de tarea con sus Acceptance Criteria | V0.1 |
| Estado explícito al inicio de la sesión | Operational State | V0.1 |
| Checklist de revisión del código generado | Verificación estructural del QA Agent | V0.3 |
| Feedback explícito, nunca corrección silenciosa | El rechazo nombra el criterio incumplido | V0.1 |
| La IA nunca commitea | La responsabilidad se acepta en el Gate, no en el commit | V0.2 |
| CLAUDE.md escrito a mano por proyecto | Contexto generado desde el Plan de Trabajo | V0.2 |

Una regla cuya contraparte ya está funcionando queda marcada como
retirada; el resto sigue vigente para todo trabajo manual.

## 15 · Trabajo con IA

Esta sección es la que más impacto tiene en la calidad del resultado.
El desarrollo asistido por IA bien hecho es más rápido y produce mejor código que el manual.
Mal hecho produce código que nadie entiende y que se rompe solo.

### 15.1 División de roles

| Rol | Responsabilidad |
|---|---|
| **IA en el chat** | Razonar arquitectura, evaluar alternativas, escribir los prompts de ejecución |
| **IA en el repositorio** | Ejecutar cambios de código dentro de un scope acotado |
| **El desarrollador** | Decidir, verificar el resultado y commitear |

La IA nunca commitea. **El commit es el acto de aceptar responsabilidad sobre el cambio**,
y esa responsabilidad es de una persona.

### 15.2 CLAUDE.md obligatorio

Todo repositorio tiene un `CLAUDE.md` en la raíz. Sin él, la IA no conoce el proyecto
e inventa convenciones en cada sesión.

```markdown
# CLAUDE.md — [Proyecto]

## Qué es este proyecto
[Una o dos oraciones]

## Tipo de producto
[SaaS público | Sistema para cliente | Herramienta interna]

## Stack
- Backend: Python 3.11 + FastAPI
- Frontend: React + Next.js (App Router) + TypeScript
- DB: PostgreSQL
- Deploy: [entorno]

## Estructura de carpetas
[Estructura real del proyecto]

## Convenciones
- Se sigue la Constitución de Desarrollo de la agencia
- Arquitectura: router → service → repo (sin controllers salvo orquestación multi-service)
- Errores: siempre AppError con message, code y status_code
- Límites de líneas: router 80 / service 150 / repo 100 / componente 150 / hook 80 / otros 200
- Logs: solo eventos de negocio y anomalías

## Reglas de ejecución
- Prohibido correr ruff format y prettier
- TypeScript se verifica con node_modules/.bin/tsc --noEmit
- No modificar archivos fuera del scope de la tarea
- Si un archivo supera su límite, proponer la división ANTES de escribir
- Docstring obligatorio en services e integrations
- Ante duda entre dos enfoques, preguntar antes de implementar
- No commitear nunca

## Estado actual
- Implementado: [...]
- En curso: [...]
- Deuda técnica conocida: ver DEUDA-TECNICA.md
```

Se actualiza cada vez que cambia algo relevante del proyecto.

### 15.3 Ciclo diagnóstico → implementación

**Nunca se diagnostica e implementa en la misma sesión.**

```
Sesión 1 — DIAGNÓSTICO (solo lectura)
  ↓ La IA lee el código, reporta qué encontró, no modifica nada
Revisión humana del reporte
  ↓ Se decide qué hacer con información real, no con suposiciones
Sesión 2 — IMPLEMENTACIÓN
  ↓ Prompt acotado, con las decisiones ya tomadas
Verificación y commit
```

Cuando se pide diagnosticar e implementar junto, la IA empieza a modificar mientras todavía
está entendiendo. Los primeros cambios se hacen sobre una comprensión parcial y los siguientes
se acumulan encima. El resultado es un cambio grande construido sobre una hipótesis que
nadie validó.

El prompt de diagnóstico dice explícitamente que **no se modifica ningún archivo**.

### 15.4 Una tarea atómica por sesión

```
# ❌ Una tarea gigante
"Construí el módulo completo de pagos: webhook, activación, emails y panel"

# ✅ Tareas atómicas, con commit entre cada una
Sesión 1: "Crear el schema Pydantic del payload del webhook"
Sesión 2: "Crear el endpoint que recibe y valida el payload"
Sesión 3: "Crear el service con la lógica de confirmación"
Sesión 4: "Integrar la activación en el service de usuarios"
```

Cuanto más grande la tarea, más contexto pierde la IA y más probable es que rompa algo
que no estaba en el pedido.

### 15.5 Verificación de la base antes de escribir el prompt

Si la tarea toca schema o datos, **antes de escribir el prompt de implementación se verifica
el estado real de la base** (ver 6.2). Las decisiones del prompt se toman sobre el catálogo vivo,
no sobre lo que dicen los archivos de migración.

Un prompt escrito sobre un schema desactualizado produce código que falla en runtime
y consume una sesión entera en descubrir por qué.

### 15.6 Estructura de un buen prompt

```
[Contexto del módulo donde se trabaja]
[Qué existe hoy y es relevante para la tarea]
[Qué se quiere lograr — específico y acotado]
[Decisiones ya tomadas, explícitas]
[Restricciones: límites de líneas, capas, prohibiciones]
[Qué NO tocar]
```

El bloque de **decisiones ya tomadas** es el que más ahorra tiempo. Sin él, la IA vuelve
a proponer alternativas que ya se descartaron y la sesión se va en rediscutir.

```
# ❌ Sin contexto
"Haceme un endpoint para buscar contactos"

# ✅ Con contexto
"Módulo de contactos del backend. Ya existe contact_repo.py con find_by_email() y save().
Necesito un endpoint GET /contacts/search que reciba 'industry' y 'company' como query
params opcionales y devuelva una lista paginada.

Decisiones tomadas: paginación por offset (no cursor), 20 por página fijo,
sin filtro por fecha en esta iteración.

Restricciones: arquitectura router → service → repo, máximo 80 líneas en el router,
docstring completo en el service, no tocar archivos fuera de contacts."
```

### 15.7 Estado explícito al inicio de cada respuesta

Toda sesión de trabajo abre declarando dónde está parado el trabajo:

```
COMPLETADO: [qué ya está hecho y verificado]
EN CURSO:   [qué se está haciendo ahora]
PENDIENTE:  [qué queda]
```

Esto evita rehacer lo hecho y evita dar por terminado lo que no lo está.

### 15.8 Barrido de código muerto antes de agregar

Antes de agregar funcionalidad a un service existente, se verifica que sus métodos actuales
tengan llamadores reales.

Un método sin callers es peor que código inútil: la IA lo lee como parte del diseño vigente
y construye lo nuevo tomándolo de referencia. El código muerto se elimina en un commit propio,
antes de empezar.

### 15.9 Revisión del código generado

```
[ ] Respeta la arquitectura por capas
[ ] Sin lógica de negocio en el router
[ ] Sin queries fuera del repository
[ ] Los nombres siguen las convenciones de la sección 3
[ ] Ningún archivo supera su límite de líneas
[ ] Los errores usan AppError con code y status_code correctos
[ ] Sin print() ni console.log()
[ ] Docstrings completos en services e integrations
[ ] No se modificaron archivos fuera del scope
[ ] No se duplica lógica que ya existe en otro módulo
[ ] Los tests nuevos tienen fakes que pueden desmentir (11.4)
```

### 15.10 Feedback explícito, nunca corrección silenciosa

Si el código generado no sigue las convenciones, se corrige **en el prompt siguiente**,
no editando a mano sin decir nada. Editar en silencio garantiza que el mismo error vuelva
en la próxima sesión.

```
"El código que generaste pone lógica de negocio en el router — eso va en el service.
Además el archivo quedó en 180 líneas y el límite es 150.
Reorganizalo respetando las capas y dividiendo donde haga falta."
```

### 15.11 Cuándo usar cada herramienta

| Herramienta | Casos ideales |
|---|---|
| **IA en el repositorio** | Refactors multiarchivo, búsquedas de patrones, auditorías de código, implementación acotada |
| **IA en el chat** | Diseño de features, evaluación de alternativas, escritura de prompts, arquitectura |
| **IA de diseño** | Componentes y pantallas, con el design system del producto como contexto obligatorio |
