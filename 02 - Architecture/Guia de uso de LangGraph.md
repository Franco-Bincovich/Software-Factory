---
titulo: Guía de uso de LangGraph
tipo: norma
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-11
adr: [ADR-004, ADR-006, ADR-010, ADR-011]
aliases: [Guía de uso de LangGraph, LangGraph]
---

# Guía de uso de LangGraph

Cómo se usa LangGraph **en esta fábrica**. No es documentación del framework:
es el subconjunto que usamos, con las restricciones que ADR-006 impone.

**Documento vinculante.** Es `tipo: norma` y figura en el índice del
[[Project Master Plan]]: las cuatro reglas de la sección "Las cuatro reglas de
esta fábrica" obligan a quien construya T14, no son recomendaciones. Las
secciones explicativas están para que esas reglas se entiendan, no para
relativizarlas.

Para la documentación oficial: `docs.langchain.com/oss/python/langgraph`.

---

## Qué es, en una línea

Un framework de orquestación de bajo nivel para construir agentes con estado que
corren mucho tiempo, sobreviven a fallos y admiten intervención humana.

## Los cuatro conceptos que usamos

**Grafo de estado.** Se declara un objeto de estado y un conjunto de nodos. Cada
nodo es una función que recibe el estado y devuelve las claves que modifica.
LangGraph las fusiona.

**Nodo.** Una función. En nuestro caso, cada nodo delega en una pieza que ya
existe: `verificar` llama a T7, `intake` llama a T8. Los nodos no contienen
lógica propia.

**Arista condicional.** Una función que recibe el estado y devuelve el nombre del
siguiente nodo. Es donde vive nuestro flujo: si el plan validó, si quedan
iteraciones, si se alcanzó un techo.

**Checkpointer.** Persiste el estado después de cada nodo. Es lo que permite
matar el proceso y reanudar desde donde quedó, en vez de volver a empezar.

**Interrupción.** `interrupt()` frena el grafo en un punto y devuelve el control.
Al reanudar, el grafo sigue desde ahí con el valor que se le pase.

---

## Qué usamos y qué no

| | Uso |
|---|---|
| `StateGraph`, nodos, aristas condicionales | **Sí** |
| Checkpointer para reanudación | **Sí** |
| `interrupt()` para frenar en Gates | **Sí** |
| Constructores de agentes preconstruidos | **No** — ADR-006 punto 6 |
| Store de memoria de largo plazo | **No en V0.1** — diferido a V0.2 |
| LangChain | **No** — ADR-006 punto 8 |
| Herramientas de observabilidad del proveedor | **No** — el Operational State alcanza |
| Plataforma de despliegue del proveedor | **No** — V1 no despliega |

---

## Las cuatro reglas de esta fábrica

### 1. El checkpointer nunca es evidencia

Guarda cómo reanudar, no qué pasó. Se sobrescribe. Toda pregunta sobre qué
ocurrió se responde leyendo el Operational State.

Si alguna vez la respuesta a "¿por qué el agente hizo esto?" sale del
checkpointer, hay un evento que faltó registrar.

### 2. `interrupt()` frena, el motor de Gates decide

Nunca se resuelve un Gate desde el mecanismo de LangGraph. La secuencia es
siempre: T11 registra `gate_abierto` → `interrupt()` → el CEO resuelve por la
CLI de T11 → T11 registra `gate_resuelto` → se reanuda el grafo.

Invertir ese orden hace que la autoridad del Gate dependa de una librería.

### 3. Nunca un timeout en una interrupción

No se pasa parámetro de expiración, no se envuelve la interrupción en algo que
venza, no se agrega una rama de "si no responde". ADR-004: el vencimiento nunca
es aprobación.

### 4. Cada nodo que consuma se mide

Antes de cada nodo que invoque al modelo, `verificar_techos`. Después,
`registrar_consumo`. Sin excepción — un nodo que consume sin medir es la vía por
la que el presupuesto deja de existir.

---

## Los dos archivos de estado

Viven los dos en `software-factory-state/`, y son distintos:

| Archivo | Qué es | Mutable | Autoridad |
|---|---|---|---|
| `factory.db` | Operational State (T13) | **No** — triggers lo impiden | Evidencia |
| `checkpoints.db` | Estado de ejecución de LangGraph | Sí, por diseño | Reanudación |

**No se fusionan.** Es la duplicación deliberada que ADR-006 punto 4 justifica y
que alguien va a querer simplificar en seis meses. No se simplifica.

Ninguno de los dos está versionado ni respaldado automáticamente. Perder
`factory.db` es R8 y elimina toda la evidencia de la fábrica. Perder
`checkpoints.db` solo obliga a relanzar corridas en curso.

---

## Instalación

```
pip install langgraph==<versión fija>
```

Versión exacta, nunca rango. Actualizar exige correr la suite completa antes de
fijar la nueva, según ADR-006 punto 7.

No instalar `langchain`, ni paquetes de observabilidad, ni de despliegue del
mismo proveedor.

---

## Errores a evitar

**Poner lógica en los nodos.** Un nodo que decide algo es lógica que se escapó de
donde estaba normada. Los nodos delegan.

**Usar el estado del grafo como registro.** Es efímero y se sobrescribe. Todo lo
que importe va a `append`.

**Agregar un nodo para "manejar" un caso raro.** Si aparece un caso que el grafo
no contempla, probablemente es un escalamiento, no una rama nueva.

**Actualizar la versión sin correr la suite.** El mecanismo de interrupción es lo
que sostiene los Gates.

---

## Qué llega en V0.2

Subgrafos, para que cada agente sea su propio grafo compuesto en uno mayor. Y el
handoff entre agentes, que es donde el Plan de Trabajo deja de tener un consumidor
humano y pasa a tener uno automático.

Nada de eso se anticipa en V0.1. Un grafo de un nodo productivo es suficiente y
es lo que se construye.
