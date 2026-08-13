# T10 — Cargador de Agent Definition

Especificación de construcción. Vive en el repositorio de código.
Implementa el contrato de ADR-003.

---

## Qué es

Lee una Agent Definition desde el Vault, verifica que cumpla los trece campos, y
**se niega a arrancar si falta alguno**. No es un validador opcional: es la
puerta por la que un agente pasa de documento a instancia ejecutable.

ADR-003 es explícito: una Agent Definition sin los trece campos completos no
existe — no se registra, no se instancia, no se ejecuta.

---

## Problema y su resolución

La Agent Definition está escrita en prosa, porque es una norma que una persona
tiene que poder leer y aprobar. Pero el runtime necesita valores estructurados:
los tres techos, el identificador, las herramientas autorizadas.

**Resolución: el frontmatter lleva los parámetros operativos; el cuerpo lleva la
norma.** El cuerpo manda: si difieren, la carga falla y hay que corregir el
documento. No se resuelve el conflicto en favor de ninguno de los dos
automáticamente.

Esto requiere un parche al documento `03 - Agent Framework/Requirement Agent.md`,
agregando al frontmatter:

```yaml
agent_id: requirement-agent
techo_costo_usd: 2
techo_tiempo_min: 20
techo_iteraciones: 5
herramientas: [leer_pedido, leer_vault, escribir_salida, escribir_operational_state]
vault_lectura: ["03 - Agent Framework/Contrato del Plan de Trabajo.md", "08 - ADR/ADR-001 - Glosario canonico.md"]
vault_escritura: []
memory: none
```

`vault_escritura: []` no es un campo vacío: es la declaración explícita de que
este agente no escribe en el Vault, conforme al punto 5 de ADR-009.

---

## Qué valida

**Sobre el cuerpo.** Los trece encabezados de ADR-003, presentes, en orden, con
el número y el nombre exactos, y con contenido no vacío debajo de cada uno.

Rechaza además si el cuerpo de cualquier campo contiene marcadores de relleno:
`TBD`, `TODO`, `por definir`, `a definir`, `N/A`, `placeholder`, `XXX`.

**Sobre el frontmatter.** Los ocho campos operativos presentes. Los tres techos
numéricos y mayores que cero. `estado: aceptado`. `agent_id` no vacío.

**Coherencia entre ambos.** Los tres techos del frontmatter aparecen con el mismo
valor en el cuerpo del campo 8. Si no coinciden, falla nombrando la
discrepancia — no elige uno.

---

## Comportamiento ante fallo

**No arranca.** No carga parcialmente, no usa valores por defecto, no advierte y
sigue.

El error nombra: qué campo, si fue el cuerpo o el frontmatter, y qué se esperaba.
Un error que dice "definición inválida" sin más no sirve.

Ningún evento se escribe en el Operational State: si el agente no se pudo cargar,
no hay corrida que registrar.

---

## Interfaz

```python
cargar(ruta_agent_definition) -> AgentDefinition   # o levanta excepción
```

El objeto devuelto expone: `agent_id`, `version`, los tres techos,
`herramientas`, `vault_lectura`, `vault_escritura`, `memory`.

**No expone el texto del cuerpo.** El cuerpo es la norma que una persona aprueba;
el runtime opera sobre los parámetros. Exponerlo invitaría a que alguna pieza
intente interpretarlo.

---

## Criterio de aceptación de T10

| Prueba | Debe |
|---|---|
| Definición completa | Carga y expone los ocho parámetros con los valores correctos |
| Campo del cuerpo faltante | Falla nombrando cuál de los trece falta |
| Campo del cuerpo vacío | Encabezado presente sin contenido debajo: falla nombrándolo |
| Marcador de relleno | Un campo con `TBD`: falla nombrando el campo y el marcador |
| Frontmatter incompleto | Sin `techo_costo_usd`: falla nombrándolo |
| Techo inválido | `techo_costo_usd: 0`: falla |
| Estado no aceptado | `estado: propuesto`: falla |
| Discrepancia cuerpo/frontmatter | Frontmatter dice 2, cuerpo dice 5: falla nombrando ambos valores |
| Sin efectos secundarios | Ningún fallo escribe en el Operational State |
| Definición real | Carga `03 - Agent Framework/Requirement Agent.md` del vault sin error |

La última es la que importa: la definición real del Requirement Agent tiene que
cargar limpia.

---

## Fuera de alcance

No ejecuta al agente. No verifica que las herramientas declaradas existan —eso es
T14. No lee ni escribe el Vault más allá del archivo de la definición.
