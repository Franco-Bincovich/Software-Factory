---
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-003, ADR-004, ADR-005, ADR-009, ADR-011]
aliases: [ADR-008]
---

# ADR-008 — Primer corte funcional de V1

Cierra el punto 5 de la Secuencia de decisión. Es el último ADR pendiente para
cerrar Fase 0.

## Contexto

Sin un corte declarado, V1 es un horizonte móvil: siempre falta una capacidad
más y nunca hay un momento legítimo para parar. El criterio anterior —diecisiete
documentos aprobados— medía documentación, no capacidad, y ya fue reemplazado.

Este ADR define qué tiene que poder hacer la fábrica para que V1 esté terminada,
y qué queda explícitamente afuera.

## Decisión

### 1. Qué es V1

**La fábrica produce herramientas internas de punta a punta sin que el CEO
escriba código.**

Criterio de terminación: **tres herramientas internas entregadas**, cada una
nacida de un pedido por Intake y terminada con su Gate de salida aprobado, sin
que el CEO haya escrito una línea de implementación en ninguna de las tres.

Tres y no una: una puede salir por suerte. Tres seguidas, sin tocar el armazón
entre ellas, es capacidad.

### 2. Los seis agentes de V1

| Agent Definition | Qué hace |
|---|---|
| Intake Agent | Convierte un pedido en lenguaje natural en un pedido estructurado |
| Requirement Agent | Convierte el pedido estructurado en un Plan de Trabajo |
| Developer Agent | Ejecuta las unidades de trabajo y produce el artefacto |
| QA Agent | Verifica el artefacto contra los Acceptance Criteria |
| Documentation Agent | Produce las instrucciones de uso e instalación |
| Deployment Agent | Instala en un entorno local descartable y corre la prueba de humo |

Seis, ninguno más. Architect y Security son Core Agents del catálogo de ADR-001 y
**no se instancian en V1**: un área justifica su propio agente solo si tiene
reglas, herramientas y criterios de verificación distintos de todas las demás, y
en herramientas internas chicas no los tienen.

El Deployment Agent sí los tiene, y por eso existe. Es el único agente con acceso
a ejecución de comandos, y aislar esa capacidad en un agente angosto es
precisamente el motivo de separarlo del Developer Agent.

No hay separación Backend / Frontend: es un solo Developer Agent. Partirlo antes
de tener evidencia de que las reglas difieren sería crear un agente por analogía
con cómo se organizan las empresas humanas, no por necesidad.

### 3. V1 despliega en local, y solo en local

**La fábrica instala lo que produjo en un entorno local descartable y verifica
que arranque.** No publica, no sube nada, no toca ningún sistema externo.

La razón de fondo no es comodidad: es que **es la única forma de saber que las
instrucciones de instalación son verdaderas**. Un README que nadie ejecutó es
una hipótesis. Instalar y arrancar convierte la documentación en algo verificado,
y elimina el modo de falla más común de los artefactos entregados.

#### Las cinco condiciones

1. **Directorio de despliegue descartable.** Todo ocurre dentro de un directorio
   declarado por corrida. Borrarlo deshace el despliegue por completo. **Si algo
   no se deshace borrando el directorio, está prohibido.**
2. **Entorno aislado, nunca instalación global.** Las dependencias se instalan
   dentro del entorno del despliegue. Nada se agrega al sistema.
3. **Sin servicios persistentes ni puertos.** Nada queda corriendo después de la
   prueba de humo. Nada escucha en la red.
4. **Prueba de humo obligatoria.** Instalar no es desplegar. El despliegue está
   terminado cuando el artefacto arranca y responde correctamente a un caso
   conocido, definido como Acceptance Criterion de su propia unidad de trabajo.
5. **Solo el Deployment Agent ejecuta comandos.** Lista cerrada de comandos
   autorizados en su Agent Definition, denegación por defecto. Ningún otro agente
   tiene esa capacidad.

#### Por qué no dispara Gate propio

Un despliegue que se deshace borrando un directorio no es irreversible, así que
no activa el criterio 1 del piso de ADR-004. Y no cruza el perímetro del sistema,
así que tampoco el criterio 2.

El despliegue ocurre **antes** del Gate de salida, y su resultado —incluida la
prueba de humo— forma parte de lo que se somete a aprobación. Aprobás una entrega
que ya se demostró instalable, no una promesa de que lo es.

#### Lo que sigue prohibido

Publicar en cualquier destino remoto. Tocar sistemas externos. Modificar
configuración del sistema operativo. Instalar globalmente. Dejar procesos vivos.
Escribir fuera del directorio de despliegue.

Eso es despliegue remoto y sigue bloqueado: exige identidad frente a sistemas
externos, que ADR-009 difirió, e Infrastructure, que la Secuencia de decisión
mantiene bloqueado.

### 4. Dos Gates por entrega

**Gate de entrada** — se aprueban el pedido interpretado y los techos.
**Gate de salida** — se aprueba la entrega completa.

Más los Gates que dispare el piso de ADR-004 por otras causas. En particular, el
Documentation Agent dispara el criterio 3 —efecto normativo— cada vez que quiera
escribir en el Vault: un Gate por entrega, no por archivo.

### 5. Herramientas internas únicamente

Nada para terceros. R7 —aislamiento entre clientes— no se mitiga en V1 y por lo
tanto no puede haber clientes.

### 6. Sin ejecución concurrente

Un proyecto por vez. La concurrencia y el aislamiento entre proyectos son V0.4,
y el sustrato del Operational State está declarado como de escritor único.

### 7. Sin Agent Factory

Crear agentes dinámicamente exige que el contrato de ADR-003 esté probado sobre
varios agentes reales, y en V1 son cinco escritos a mano. La creación dinámica
llega después de V1.

## Lo que V1 explícitamente no hace

Desplegar fuera del entorno local descartable. Trabajar para terceros. Correr
cosas en paralelo. Crear agentes. Elegir stack por proyecto. Producir interfaces
gráficas. Escribir en el Vault sin Gate. Aprobar su propio trabajo, en ningún
nivel.

## Consecuencias

**Lo que habilita.** Fase 0 cierra. Technology Stack e Infrastructure se
desbloquean. Las versiones intermedias tienen destino declarado.

**Lo que cuesta.** El acceso a ejecución de comandos es la ampliación de permisos
más grande del proyecto. Queda contenida en un solo agente, dentro de un
directorio descartable y con lista cerrada de comandos, pero es la primera vez
que la fábrica actúa sobre la máquina y no solo sobre archivos que produce. El
documento de Security deja de ser diferible después de V1.

**Lo que difiere.** Despliegue remoto, terceros, concurrencia y Agent Factory
quedan todos fuera y con versión asignada. Ninguno vuelve a discutirse antes de
V1.

## Decisiones que habilita

- Technology Stack e Infrastructure — quedan desbloqueados al aprobarse este ADR.
- Roadmap — las versiones intermedias V0.2 a V0.4 tienen destino.
- Agent Framework — el catálogo de agentes de V1 está cerrado.

## Decisiones que no resuelve

- **Cuándo se instancian Architect y Security.** Después de V1, con evidencia de
  que su área tiene reglas distintas.
- **La lista cerrada de comandos del Deployment Agent.** Se define al escribir su
  Agent Definition, y ampliarla dispara Gate por el criterio 5 del piso.
- **Despliegue remoto.** Bloqueado hasta que existan Security e Infrastructure.
- **Qué tres herramientas internas.** Se eligen cuando V0.4 esté cerrada.
- **Modelo organizacional en Departamentos y Roles.** Es ADR-007, y V1 no lo
  necesita: cinco agentes no son un organigrama.
