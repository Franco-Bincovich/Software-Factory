---
titulo: Infrastructure
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-008, ADR-009, ADR-011]
aliases: [Infrastructure, Infraestructura]
---

# Infrastructure

## Propósito

Declarar dónde corre la fábrica, dónde corre lo que produce, y cómo se protege lo
que no se puede perder.

## Alcance

Cubre la infraestructura de la fábrica, el respaldo del Operational State, el
despliegue local de V1, y lo que cada patrón de construcción necesita para correr
en producción. No cubre la elección entre patrones —eso es Technology Stack—.

---

## Parte 1 — Infraestructura de la fábrica

### Dónde corre

**En la máquina del fundador.** Sin servidores, sin nube, sin servicios
gestionados. Es lo correcto para V1: la fábrica no atiende a nadie más que a su
dueño.

### Las tres ubicaciones

| Qué | Dónde | Git | Se puede perder |
|---|---|---|---|
| Normas | `Software Factory/` | Sí | No — se recupera del remoto |
| Código | `software-factory-core/` | Sí | No — se recupera del remoto |
| Hechos | `software-factory-state/` | **No** | **Sí, y es irrecuperable** |

**Hermanas, nunca anidadas.** Anidar el código dentro del vault llenaría el
historial normativo de commits de implementación. Anidar el estado dentro de un
repo versionaría los hechos, contra ADR-011.

Dentro de `software-factory-state/` conviven dos archivos con naturalezas
opuestas: el Operational State, inmutable y autoritativo, y el checkpointer de
ejecución, mutable por diseño y sin valor probatorio. **No se fusionan.**

### R8 — el riesgo que este documento hereda

El Operational State está fuera de git. **Si se pierde, se pierde toda la
evidencia de todo lo que la fábrica hizo, sin reconstrucción posible desde el
Vault.**

Es la contrapartida honesta de separar hechos de normas, y es el riesgo más
concreto que el proyecto tiene hoy.

#### Política de respaldo para V1

**Copia posterior a cada sesión de trabajo, a un destino fuera de la máquina.**
Manual, y responsabilidad del fundador.

Tres reglas:

1. **El respaldo se verifica, no se supone.** Un respaldo que nadie restauró
   nunca no es un respaldo. Al menos una restauración de prueba antes de la
   primera corrida real.
2. **El respaldo conserva versiones anteriores.** Copiar encima del último no
   protege contra corrupción: propaga el archivo dañado.
3. **El checkpointer no se respalda.** Perderlo solo obliga a relanzar corridas
   en curso.

#### Por qué sigue siendo manual

Automatizarlo exige que la fábrica escriba fuera de su perímetro, y eso amplía
permisos por una razón operativa antes de que Security esté cerrado. En V1 el
volumen es una máquina y una sesión por día: es tolerable.

**Deja de serlo cuando existan clientes.** La automatización del respaldo es
condición previa a trabajar para terceros, no una mejora.

### Requisitos de la máquina

Runtime del orquestador y sus dependencias. Cliente de git. Espacio para el
directorio de despliegue descartable. Acceso a red **únicamente** para el
proveedor de modelos y los repositorios de paquetes.

Ningún agente tiene acceso a red en V0.1. El acceso lo tiene el proceso, no el
agente.

---

## Parte 2 — Despliegue local

Lo que ADR-008 habilita para V1. Es la única forma de despliegue disponible.

### El directorio descartable

Un directorio de despliegue por corrida, declarado. **Todo ocurre adentro.**

La regla que sostiene todo lo demás: **si algo no se deshace borrando el
directorio, está prohibido.** Es lo que mantiene el despliegue reversible, y por
lo tanto fuera del criterio 1 del piso de ADR-004.

### Las cinco condiciones

1. Directorio descartable, declarado por corrida.
2. Entorno aislado, nunca instalación global.
3. Sin servicios persistentes ni puertos escuchando.
4. Prueba de humo obligatoria: instalar no es desplegar.
5. Solo el Deployment Agent ejecuta comandos, con lista cerrada.

### Los tres huecos previos al Deployment Agent

Están en Security y se repiten acá porque son de infraestructura:

**Cuál es la lista cerrada de comandos.** Sin ella, "acceso a ejecución"
significa acceso total.

**Cómo se impide la evasión.** Un comando permitido que puede invocar a otros
anula la lista.

**Qué se hace con las dependencias del artefacto.** Instalarlas es ejecutar
código que nadie revisó. Es el vector más obvio y no está resuelto.

**Los tres se cierran antes de instanciar el Deployment Agent**, no antes de V1.

---

## Parte 3 — Infraestructura del software producido

Qué necesita cada patrón para correr en producción. **No aplica a V1**, que
despliega solo en local; se declara para que los proyectos nazcan sabiendo a qué
apuntan.

### Infraestructura mínima, común a los dos patrones

Según la sección 12.2 de la Constitución Técnica:

```
├── Cómputo         ← servicio de la aplicación
├── Base de datos   ← gestionada, con backups automáticos
├── Almacenamiento  ← archivos estáticos y backups
├── Logs y alertas  ← centralizados, con alerta sobre errores 5xx
└── DNS             ← dominio y certificado
```

### Patrón A

Cómputo en contenedor o instancia. PostgreSQL gestionado con backups
automáticos. Almacenamiento de objetos. Logs y métricas centralizados con alerta
de 5xx. Dominio con certificado válido y HTTPS obligatorio.

Variables no sensibles en el gestor del servicio; secretos en el gestor de
secretos del proveedor. **Nunca un `.env` en el servidor.**

### Patrón B

CloudFront como entrada con dominio propio, redirigiendo HTTP a HTTPS. S3 privado
con Block Public Access y acceso exclusivo desde CloudFront mediante OAC — sin
S3 Website Hosting. API Gateway HTTP API con integración Lambda proxy. Lambda con
IAM de mínimo privilegio, timeout y memoria definidos por prueba, y clientes de
SDK inicializados fuera del handler. Secrets Manager para credenciales.
CloudWatch para logs, métricas y alarmas. Certificado ACM emitido en `us-east-1`.
WAF según exposición.

Comportamiento de CloudFront: `/*` al bucket, `/api/*` a la API, con caché
deshabilitada para la API salvo endpoints explícitamente cacheables. Assets
estáticos con TTL alto y nombres versionados.

### Reglas comunes

**Infraestructura declarada como código**, idealmente. Un despliegue que depende
de pasos manuales que solo alguien conoce no es repetible.

**Verificar las limitaciones de la plataforma antes de elegir dónde corre cada
parte** — tareas en background, procesos largos, timeouts y persistencia de
archivos entre invocaciones. Una limitación conocida se documenta en el
`ARCHITECTURE.md` del proyecto junto con la estrategia para cuando el volumen la
vuelva bloqueante.

**Los tests pasan antes de cada despliegue.** Si un test falla, el despliegue no
sale.

**El backup de la base se verifica, no se supone.** Es la misma regla que R8, y
por el mismo motivo.

---

## Entornos

**Un solo entorno en V1: local.** No hay staging, no hay producción, no hay
integración continua.

Es coherente con que V1 no despliega fuera de la máquina. Agregar entornos antes
de tener algo que desplegar sería infraestructura decorativa.

**Los proyectos que la fábrica produzca** sí van a necesitar entornos propios.
Cuántos y cuáles se declara en el `ARCHITECTURE.md` de cada uno.

---

## Custodia de secretos

**Manual y del fundador, en V1.** El volumen es una credencial: la del proveedor
de modelos.

Ningún secreto entra al Operational State, ni al Vault, ni al contexto de un
Agent Run como texto. Como nada se borra, un secreto que entra queda para
siempre.

**El gestor de secretos propio es lo primero que se construye después de V1.**
Con seis agentes y despliegue local, una credencial pasa a ser varias y la
custodia manual deja de escalar.

## Decisiones tomadas

1. La fábrica corre en la máquina del fundador. Sin nube en V1.
2. Tres ubicaciones hermanas, nunca anidadas.
3. El respaldo del Operational State es manual, verificado con una restauración
   de prueba, y conserva versiones anteriores.
4. La automatización del respaldo es condición previa a trabajar para terceros.
5. Un solo entorno en V1.
6. La custodia de secretos es manual mientras sea una credencial.

## Decisiones abiertas

1. **Lista cerrada de comandos del Deployment Agent**, evasión, y tratamiento de
   dependencias. Bloqueantes para instanciarlo.
2. **Gestor de secretos propio.** Primera obra después de V1.
3. **Respaldo automático del Operational State.** Condición previa a terceros.
4. **Dónde corre la fábrica cuando deje de ser una máquina.** Sin versión
   asignada; se decide cuando la concurrencia de V0.4 lo exija.
5. **Infraestructura como código para los proyectos producidos.** Declarada como
   ideal, sin herramienta elegida.

## Impacto en otros documentos

**ADR-011** — este documento cumple su exigencia de política de respaldo.
**Security** — comparte los tres huecos del Deployment Agent. **Technology
Stack** — desarrolla qué necesita cada patrón. **Registro de riesgos** — R8 pasa
de "sin mitigación" a "mitigación manual declarada"; se cierra del todo cuando el
respaldo se automatice.
