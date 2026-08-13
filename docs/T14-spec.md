# T14 — Armazón de ejecución

Especificación de construcción. Vive en el repositorio de código.
Implementa ADR-006. Es la última tarea del Bloque B de V0.1.

---

## Qué es

La pieza que conecta las seis anteriores y hace que exista una corrida. Hasta
ahora T7, T8, T10, T11, T12 y T13 son módulos que no se conocen entre sí.

**T14 no agrega lógica de negocio.** Todo lo que decide ya está decidido en las
otras piezas: T10 valida la definición, T12 mide y corta, T11 abre y registra
Gates, T7 verifica, T13 persiste. T14 los ordena.

---

## El grafo

```
                    ┌─────────────────────────────┐
                    │                             │
  cargar ──► intake ──► [gate entrada] ──► producir ──► verificar
                                              ▲            │
                                              │            ▼
                                              └──────── ¿válido?
                                            (quedan iters)  │
                                                            │ sí
                                                            ▼
                                                    [gate salida]
                                                            │
                                                            ▼
                                                           fin

  Cualquier nodo que consuma: si T12 devuelve TechoAlcanzado ──► escalar ──► fin
```

### Nodos

| Nodo | Qué hace | Delega en |
|---|---|---|
| `cargar` | Carga y valida la Agent Definition | T10 |
| `intake` | Valida el pedido y abre la corrida | T8 |
| `gate_entrada` | Somete pedido y techos, frena | T11 + `interrupt()` |
| `producir` | Invoca al modelo para producir o corregir el plan | — |
| `verificar` | Valida el plan contra las siete reglas | T7 |
| `gate_salida` | Somete el plan aprobado por T7, frena | T11 + `interrupt()` |
| `escalar` | Registra el escalamiento y termina | T13 |
| `fin` | Cierra la corrida | T13 |

### Aristas condicionales

**Después de `verificar`:**
- Plan válido → `gate_salida`
- Plan inválido y quedan iteraciones → `producir`, con la lista de
  incumplimientos en el estado
- Plan inválido y techo de iteraciones alcanzado → `escalar`

**Después de `gate_entrada` y `gate_salida`:**
- Aprobado → sigue
- Rechazado → `fin`, con el trabajo parcial conservado

**Antes de `producir`:**
- `verificar_techos` devuelve `TechoAlcanzado` → `escalar`

---

## Estado del grafo

```python
{
  "run_id":            str,
  "definicion":        AgentDefinition,
  "pedido":            dict,
  "texto_rastreable":  str,
  "plan":              dict | None,
  "incumplimientos":   list,
  "iteracion":         int,
  "resultado":         str | None
}
```

El estado del grafo es **estado de ejecución, no evidencia**. Lo que importa se
escribe además en el Operational State. Si los dos difieren, manda el Operational
State: es la aplicación directa del punto 4 de ADR-006.

---

## Nodo `producir`

Es el único nodo que invoca al modelo y el único que consume presupuesto.

**Recibe en el contexto:** el pedido, el Contrato del Plan de Trabajo leído del
Vault, la lista de incumplimientos si es una corrección, y el plan anterior si lo
hay.

**Primera iteración:** produce un plan desde el pedido.

**Iteraciones siguientes:** **corrige el plan existente.** No regenera. Lo
prohíbe el campo 9 de la Agent Definition: regenerar íntegramente se trata como
agotamiento inmediato.

**Al terminar:**
1. `registrar_consumo(run_id, costo)` — el costo real de la invocación
2. `append(run_id, "iteracion_producida", "requirement-agent", {iteracion, plan})`

**Alcance de lectura del Vault:** exactamente los dos documentos que declara
`vault_lectura` en el frontmatter de la Agent Definition. Ni uno más. Ampliarlo
requiere Gate por el criterio 5 del piso de ADR-004.

---

## Integración con LangGraph

**Grafo explícito.** `StateGraph` con nodos y aristas declarados a mano. No se
usan constructores de agentes preconstruidos, según el punto 6 de ADR-006.

**Checkpointer.** Persistencia de estado de ejecución para reanudar tras fallo.
Vive junto al Operational State, en `software-factory-state/`, en un archivo
**separado** de `factory.db`. No se mezclan: uno es mutable por diseño y el otro
inmutable por diseño.

**Interrupciones.** `interrupt()` frena en los dos nodos de Gate. Antes de
interrumpir, T11 ya registró `gate_abierto`. Al reanudar, T11 registra
`gate_resuelto`. La decisión llega por la CLI de T11, no por el mecanismo de
LangGraph.

**Versión fija**, según el punto 7 de ADR-006.

---

## Interfaz

```
correr.py --pedido ruta/al/pedido.json
correr.py --reanudar <run_id>
```

`--pedido` inicia una corrida nueva. Cuando llega a un Gate, imprime el `run_id`
y termina el proceso: la corrida queda esperando.

`--reanudar` retoma una corrida cuyo Gate ya fue resuelto con la CLI de T11.

Este ciclo —corre, frena, resolvés, reanudás— es deliberado. Un proceso que se
queda vivo esperando una decisión humana durante horas invita a agregarle un
timeout, y ADR-004 lo prohíbe.

---

## Criterio de aceptación de T14

| Prueba | Debe |
|---|---|
| Definición inválida | Con un campo borrado, no arranca. Cero eventos |
| Pedido inválido | No arranca. Cero eventos |
| Frena en el Gate de entrada | La corrida se detiene, el evento queda, el proceso termina |
| Rechazo en entrada | La corrida termina sin producir nada |
| Corrida completa | Pedido válido, ambos Gates aprobados, plan producido y válido |
| Corrección | Un plan inválido en la primera iteración se corrige en la segunda, sin regenerar |
| Techo de iteraciones | Con techo 2 y un plan que nunca valida, escala tras la segunda |
| Techo de costo | Con techo artificialmente bajo, corta y registra cuál |
| El reloj se detiene | Un Gate resuelto tras una espera larga no agota el techo de tiempo |
| Reanudación tras fallo | Matando el proceso a mitad, `--reanudar` retoma sin repetir el nodo completado |
| Trazabilidad | La corrida se reconstruye leyendo solo el Operational State |
| Sin escritura en el Vault | Ninguna corrida escribe en el Vault. Verificable por inspección |

**La prueba de trazabilidad es la que decide.** Si hay que mirar la consola o el
checkpointer para entender qué pasó, T14 no está terminado.

---

## Notas de implementación

Tres puntos que la spec no prescribe y que se resuelven en código:

1. **Evento de apertura de corrida.** El nodo `intake` debe registrar el primer
   evento en el Operational State (vía T13) antes de que la corrida avance. Sin
   ese evento, la apertura no queda trazada y la prueba de trazabilidad falla.
   Llamada esperada: `append(run_id, "corrida_abierta", "requirement-agent", {pedido})`.

2. **`verificar_techos` como nodo propio.** El diagrama lo muestra como arista
   condicional, pero la decisión de cortar por techo debe quedar registrada como
   evento en T13 *antes* de llegar a `escalar`. Implementar como nodo de una
   línea que llama a T12 y rutea; si corta, registra
   `append(run_id, "techo_alcanzado", "requirement-agent", {techo, valor})`.

3. **`texto_rastreable` en el estado del grafo.** Ningún nodo lo puebla según la
   spec. Si es el output legible del plan, usar `plan` directamente. Si cumple
   otra función, documentarla en el código. Si no cumple ninguna, eliminarlo del
   estado.

---

## Fuera de alcance

No implementa el Developer Agent ni ningún otro. No ejecuta el plan producido: en
V0.1 lo ejecuta el CEO a mano, y eso es T16. No expone interfaz gráfica ni API.
No corre dos corridas a la vez.
