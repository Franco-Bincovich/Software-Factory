---
titulo: Security
tipo: norma
estado: borrador
aprobado: 2026-08-07
version: 0.1
owner: CEO
actualizado: 2026-08-07
adr: [ADR-004, ADR-008, ADR-009, ADR-011]
aliases: [Security, Seguridad]
---

# Security

## Estado: borrador

Este documento está incompleto a propósito y **declara qué le falta**. Se
completa cuando Infrastructure se desbloquee.

Existe ahora porque ADR-008 introdujo despliegue local, y con él la ampliación de
permisos más grande del proyecto: un agente que ejecuta comandos en la máquina
del CEO. Diferir la seguridad después de esa decisión sería incoherente.

## Propósito

Definir la postura de seguridad **de la fábrica operando**. No de lo que la
fábrica produce.

## Alcance

Cubre permisos de agentes, custodia de secretos, superficie de ataque del
despliegue local y los riesgos propios de operar con modelos de lenguaje.

**No cubre la seguridad del software producido.** Eso vive en la sección 9 de la
Constitución Técnica y **no se duplica acá**: prompt separado del input,
sanitización, contenido externo como no confiable, control de costos como vector
de ataque, validación del output, y la regla de que la IA filtra pero no decide.

Si este documento y la Constitución dijeran cosas distintas sobre lo mismo, uno
de los dos estaría mintiendo. Por eso se referencia, no se copia.

---

## Lo que ya está decidido

### Permisos

Denegación por defecto sobre todo recurso: herramientas, sistema de archivos,
red, repositorios, Vault. Lo que la Agent Definition no declara, está prohibido.

Identidad propia por agente, credenciales separadas, revocables
individualmente. Ningún agente comparte credencial con una persona. Ningún agente
actúa en nombre de otro.

Ampliar permisos dispara Gate por el criterio 5 del piso de ADR-004.

### Secretos

Ninguna credencial entra al Operational State, ni viaja como texto en el contexto
de un Agent Run, ni queda en el Vault. Como nada se borra, un secreto que entra
queda para siempre.

El control por nombres de clave es **léxico y por lo tanto parcial**: no detecta
un secreto guardado bajo un nombre inocente.

### Escritura en el Vault

Ningún agente escribe sin Gate. No admite excepción declarable. El Vault es donde
viven las reglas que gobiernan a los agentes, y un agente con escritura
permanente ahí puede modificar sus propios límites.

---

## Despliegue local — la superficie nueva

El Deployment Agent es el único con acceso a ejecución de comandos. Aislar esa
capacidad en un agente angosto es el motivo de que exista separado.

Cinco condiciones, ya decididas en ADR-008:

1. Directorio de despliegue descartable. **Si algo no se deshace borrando el
   directorio, está prohibido.**
2. Entorno aislado, nunca instalación global.
3. Sin servicios persistentes ni puertos.
4. Prueba de humo obligatoria.
5. Lista cerrada de comandos autorizados.

### Lo que falta decidir acá, y es lo importante

**Cuál es exactamente esa lista de comandos.** Es el control que sostiene todo lo
demás y todavía no existe. Sin ella, "acceso a ejecución de comandos" significa
acceso total.

**Cómo se impide la evasión.** Una lista cerrada de comandos no sirve si uno de
los comandos permitidos puede invocar a otros. Instalar dependencias, por
ejemplo, ejecuta código de terceros por diseño.

**Qué pasa con las dependencias que el artefacto declara.** Instalarlas es
ejecutar código que nadie revisó. Es el vector más obvio y no está resuelto.

Los tres se cierran antes de instanciar el Deployment Agent, no antes de V1.

---

## Riesgos propios de operar con modelos

**Inyección por contenido del pedido.** El pedido de Intake es entrada no
confiable: lo escribe una persona, pero podría contener instrucciones dirigidas
al modelo. En V0.1 el riesgo es bajo porque el único autor es el CEO. Deja de
serlo cuando existan otros solicitantes.

**Inyección por contenido leído.** Un agente que lee archivos de un proyecto lee
contenido que no controla. Aplica la regla de la Constitución: contenido externo
es input no confiable.

**Costo como vector.** Un pedido construido para hacer iterar al agente
indefinidamente es un ataque de costo. Mitigado por los tres techos de ADR-010,
que cortan sin negociar.

**Exfiltración por el artefacto producido.** Un agente con acceso de lectura al
Vault podría incluir su contenido en lo que produce. Mitigado hoy porque
`vault_lectura` es una lista cerrada de dos documentos. Deja de estar mitigado
cuando esa lista crezca.

---

## Lo que este documento no resuelve

| Hueco | Depende de | Cuándo |
|---|---|---|
| Dónde viven los secretos y cómo se rotan | Infrastructure | Bloqueado |
| Respaldo del Operational State — R8 | Infrastructure | Bloqueado |
| Lista cerrada de comandos del Deployment Agent | Su Agent Definition | Antes de V1 |
| Aislamiento entre proyectos y entre clientes — R7 | Workspace aislado | V0.4 |
| Identidad frente a sistemas externos | Despliegue remoto | Después de V1 |
| Revisión de dependencias antes de instalarlas | Deployment Agent | Antes de V1 |

**Mientras tanto:** la custodia de secretos es manual y del CEO. El volumen en
V0.1 es una credencial, así que es tolerable. En V0.2 deja de serlo.

## Decisiones tomadas

1. La seguridad del software producido vive en la Constitución Técnica y no se
   duplica acá.
2. El acceso a ejecución de comandos queda contenido en un solo agente.
3. Un despliegue que no se deshace borrando su directorio está prohibido.
4. El control de secretos por nombres de clave se declara parcial.

## Decisiones abiertas

Las seis de la tabla de huecos. Ninguna se resuelve sin desbloquear
Infrastructure o sin escribir la Agent Definition del Deployment Agent.

## Impacto en otros documentos

**ADR-009** — este documento lo desarrolla. **ADR-008** — la sección de despliegue
local deriva de él y le agrega los tres huecos que hay que cerrar antes.
**Constitución Técnica** — referenciada, no duplicada. **Infrastructure**
(bloqueado) — hereda la custodia de secretos y R8.
