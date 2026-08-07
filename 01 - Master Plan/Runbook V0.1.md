---
titulo: Runbook V0.1
tipo: runbook
estado: aceptado
aprobado: 2026-08-07
version: 1.0
owner: CEO
actualizado: 2026-08-07
adr: [ADR-004, ADR-009, ADR-010, ADR-011]
aliases: [Runbook V0.1, Runbook]
---

# Runbook V0.1

Cómo se opera la fábrica una vez que T14 esté terminado. Es el documento que se
lee para usarla, no para entenderla.

---

## Las tres ubicaciones

| Qué | Dónde | Versionado |
|---|---|---|
| Normas — ADRs, contratos, Agent Definitions | `Software Factory/` | Git |
| Código — las siete piezas | `software-factory-core/` | Git |
| Hechos — evidencia y checkpoints | `software-factory-state/` | **No** |

Los tres son hermanos en el disco. **No se anidan.** El día que el estado quede
adentro de un repo, los hechos empiezan a versionarse y ADR-011 deja de
cumplirse.

---

## Ciclo completo de una corrida

### 1. Escribir el pedido

Copiar `templates/pedido.template.json` y completar los seis campos.

```json
{
  "que_se_quiere": "Herramienta que lee un CSV de altas de empleados y reporta qué filas no se pueden importar.",
  "para_que": "Validar exportaciones del sistema viejo antes de importarlas.",
  "alcance_excluido": ["interfaz gráfica", "conexión al sistema viejo"],
  "techo_costo_usd": 2,
  "techo_tiempo_min": 20,
  "techo_iteraciones": 5
}
```

Dos cosas que importan al escribirlo:

**`alcance_excluido` se compara por palabras.** Poner los términos que uno espera
ver escritos en un plan: `"interfaz gráfica"`, no `"nada visual"`.

**`que_se_quiere` y `para_que` son el texto rastreable.** Cada unidad del plan
tiene que citar textualmente una parte de esos dos campos. Si están escritos de
forma vaga, el agente no va a poder rastrear nada y va a escalar.

### 2. Lanzar

```
python correr.py --pedido pedidos/altas.json
```

Si el pedido es inválido, imprime todos los motivos y no abre corrida. **No deja
rastro**: un pedido mal armado no consume nada.

Si es válido, imprime el `run_id`, abre el Gate de entrada y **termina el
proceso**. Es lo esperado, no un error.

### 3. Resolver el Gate de entrada

```
python gates.py --listar
```

Muestra qué espera, desde cuándo, y el artefacto sometido.

```
python gates.py --resolver <run_id> --gate entrada --decision aprobado
python gates.py --resolver <run_id> --gate entrada --decision rechazado --motivo "el alcance excluido está incompleto"
```

Rechazar exige motivo. Aprobar no.

**No responder no aprueba nada.** La corrida espera indefinidamente. Es
deliberado.

### 4. Reanudar

```
python correr.py --reanudar <run_id>
```

El agente produce el plan. Si no pasa las siete reglas, corrige y reintenta hasta
el techo de iteraciones. Si pasa, abre el Gate de salida y vuelve a frenar.

### 5. Resolver el Gate de salida

Mismo mecanismo. Acá se lee el plan completo.

**Este Gate no es una formalidad.** La verificación estructural comprueba que
cada criterio tenga sus tres partes, no que sirvan. Un plan con criterios vagos
pero bien formados pasa la máquina y llega acá. Hasta V0.3 este es el único
control sustantivo que tiene la fábrica.

Qué mirar concretamente: ¿cada Acceptance Criterion se puede comprobar sin
preguntarle nada a nadie? ¿Las unidades cubren lo que se pidió, o falta algo?
¿Hay supuestos declarados que en realidad son ambigüedades del pedido?

### 6. Ejecutar el plan

En V0.1 lo ejecuta el CEO a mano con Claude Code, unidad por unidad, en el orden
que marcan las dependencias.

**Anotar cada vez que haya que improvisar algo que el plan no previó.** Ese es el
criterio de terminación de V0.1: si hubo que improvisar, el plan tenía un hueco y
el agente todavía no sirve.

---

## Qué hacer cuando algo sale mal

### El agente escaló

Cuatro causas posibles, y el evento dice cuál:

| Causa | Qué significa | Qué hacer |
|---|---|---|
| Ambigüedad de requerimiento | El pedido no permite derivar criterios sin adivinar | Reescribir el pedido y relanzar |
| Más de diez unidades | El pedido era demasiado grande | Partirlo en dos pedidos |
| Supuesto que invalidaría el plan | Falta información de base | Agregarla al pedido |
| Techo agotado | Se acabó plata, tiempo o iteraciones | Ver abajo |

**Un escalamiento no es un fracaso.** Los tres primeros son el agente diciendo
algo verdadero sobre el pedido.

### Se alcanzó un techo

La corrida se cortó y el trabajo parcial está conservado. **No se puede subir el
techo con la corrida viva**: se edita el valor en el frontmatter de la Agent
Definition y se relanza.

Subir un techo dispara Gate. Y si el mismo techo se sube tres veces sin que el
motivo cambie, el problema no es el trabajo: es la Agent Definition. Corresponde
revisarla, no seguir subiendo.

### El proceso murió a mitad

```
python correr.py --reanudar <run_id>
```

Retoma desde el último nodo completado, sin repetir lo hecho.

### Reconstruir qué pasó

```python
from operational_state import OperationalState
OperationalState().leer_run("<run_id>")
```

Devuelve todos los eventos en orden. **Si hace falta mirar la consola o los
checkpoints para entender algo, hay un evento que faltó registrar** — y eso es un
defecto, no una molestia.

---

## Respaldo — R8

`software-factory-state/factory.db` no está versionado ni respaldado. Si se
pierde, **se pierde toda la evidencia de todo lo que la fábrica hizo**, sin
reconstrucción posible desde el Vault.

Hasta que exista Infrastructure, el respaldo es manual y es responsabilidad del
CEO. Copiar el archivo a otro disco después de cada sesión de trabajo.

`checkpoints.db` no necesita respaldo: perderlo solo obliga a relanzar corridas
en curso.

---

## Lo que la fábrica no hace en V0.1

Interpretar pedidos difusos — el pedido entra estructurado. Escribir código —
solo produce el plan. Desplegar. Correr dos cosas a la vez. Escribir en el Vault.
Recordar corridas anteriores. Verificar contra el mundo: hasta V0.3 verifica
forma, no funcionamiento.
