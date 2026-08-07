---
tipo: adr
estado: aceptado
aprobado: 2026-08-06
version: 1.0
owner: CEO
actualizado: 2026-08-06
adr: [ADR-001, ADR-003, ADR-004, ADR-011]
aliases: [ADR-009]
---

# ADR-009 — Identidad y permisos de agentes

Cierra el punto 6 de la Secuencia de decisión del Project Master Plan.

## Contexto

ADR-003 ya resolvió la mitad del problema: el campo 5 fija que las herramientas
autorizadas son lista cerrada con denegación por defecto. Lo que no resolvió es
quién es el sujeto de esos permisos. Hoy, si se arrancara un Agent Run, actuaría
bajo la identidad y las credenciales del CEO.

Eso rompe algo más grave que la seguridad: rompe la trazabilidad. ADR-004 exige
evidencia registrada de quién decidió qué, y ADR-011 exige que todo hecho tenga
un actor. Si todos los agentes actúan como el CEO, el "quién" de toda la
evidencia es siempre el mismo y la evidencia deja de distinguir nada. Un vault
lleno de registros que dicen todos lo mismo es documentación que miente.

Hay además un problema de reversibilidad. Sin identidad separada, retirarle
permisos a un agente que se comporta mal significa retirárselos al CEO.

## Opciones consideradas

**A. Identidad única compartida.** Es el estado actual por omisión. Descartada
por lo anterior.

**B. Identidad por Agent Run.** Máxima granularidad. Descartada: el permiso es una
propiedad del rol, no de la ocurrencia. Emitir credenciales por ejecución agrega
gestión sin agregar control, y ADR-011 ya identifica cada corrida por su
identificador.

**C. Identidad por Agent Definition.** Elegida. El permiso acompaña al contrato,
que es donde ADR-003 ya lo declara.

## Decisión

### 1. La identidad pertenece a la Agent Definition

Cada Agent Definition tiene una identidad propia, estable y distinta de la de
cualquier persona. Los Agent Runs heredan esa identidad y se distinguen entre sí
por el identificador de corrida de ADR-011, no por identidades separadas.

### 2. Denegación por defecto, extendida a recursos

El campo 5 de ADR-003 aplica el principio a las herramientas. Este ADR lo
extiende a todo recurso: sistema de archivos, red, repositorios, servicios
externos y el propio Vault. Lo que la Agent Definition no declara explícitamente,
está prohibido. La lectura y la escritura se declaran por separado, como ya exige
el campo 11.

### 3. Ningún agente comparte credencial con una persona

Cada identidad tiene credenciales propias, de alcance mínimo, revocables
individualmente. Revocar las de un agente no debe afectar a ningún otro agente ni
a ninguna persona. Si revocar rompe algo más que al agente revocado, el alcance
estaba mal declarado.

### 4. Los secretos no entran al plano de los hechos

Ninguna credencial, token o secreto se registra en el Operational State, ni viaja
en el contexto de un Agent Run como texto, ni queda en el Vault. Es consecuencia
directa del punto 6 de ADR-011: nada se borra. Un secreto que entra al registro
queda ahí para siempre.

### 5. Escribir en el Vault exige Gate, siempre

Todo agente puede leer el Vault. Ninguno escribe en él sin Gate, porque escribir
en el Vault es efecto normativo y dispara el criterio 3 del piso de ADR-004. No
existe agente con permiso permanente de escritura sobre el Vault, y esa excepción
no puede declararse en una Agent Definition.

### 6. Ampliar permisos exige Gate

Ya lo fija el criterio 5 del piso de ADR-004 para herramientas. Se extiende a
recursos. Ampliar el alcance de una identidad es un cambio de capacidad, no un
ajuste de configuración.

### 7. No hay suplantación

Un agente nunca actúa en nombre de otro agente ni de una persona. El escalamiento
del campo 10 de ADR-003 transfiere la decisión, no la identidad: quien resuelve
un escalamiento lo hace con la suya y así queda registrado.

### 8. Toda acción registrada nombra a su actor

No se admite "el sistema" ni un actor vacío. Un hecho sin actor identificado es
un hecho huérfano, del mismo modo que uno sin corrida asociada.

### 9. Alcance en V0.1

Una sola identidad, la del Requirement Agent. Lee el pedido de entrada y el
Vault; escribe únicamente en su carpeta de salida y en el Operational State. Sin
acceso a red, sin acceso a repositorios, sin escritura sobre el Vault.

## Consecuencias

**Lo que habilita.** La evidencia empieza a distinguir actores, que es la
condición para que sirva. El campo 11 de las Agent Definitions pasa a tener
sujeto. Retirarle capacidad a un agente se vuelve una operación acotada.

**Lo que cuesta.** Cada agente nuevo trae una identidad y credenciales que
alguien tiene que emitir, guardar y rotar. Es gestión real y crece linealmente
con el catálogo de agentes. Se acepta porque la alternativa es no tener
trazabilidad.

**Lo que introduce.** El punto 4 obliga a que los secretos vivan en algún lado
que no es ni el Vault ni el Operational State, y ese lugar no existe todavía: es
Security e Infrastructure, hoy bloqueados. Mientras tanto la custodia es manual y
es responsabilidad del CEO. En V0.1 el volumen es una credencial, así que el
riesgo es tolerable; en V0.2 deja de serlo.

## Decisiones que habilita

- V0.1 T9 — Agent Definition del Requirement Agent, campos 5 y 11.
- V0.1 T13 — el registro de corrida ya puede nombrar a su actor.
- Security (pendiente) — parte de este ADR como piso.

## Decisiones que no resuelve

- **Dónde viven los secretos y cómo se rotan.** Es Security e Infrastructure.
- **Aislamiento entre proyectos y entre clientes.** Es V0.4 y R7.
- **Identidad frente a sistemas externos** — repositorios, servicios de terceros.
  No lo necesita V0.1, que no sale del disco local.
