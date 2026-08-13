# T8 — Formulario de Intake

Especificación de construcción. Vive en el repositorio de código.

---

## Qué es

El punto único de ingreso de pedidos a la fábrica. **Es un mecanismo, no una
Agent Definition**: no interpreta, no completa, no infiere. Valida y registra.

La interpretación de pedidos difusos llega en V0.2 como Intake Agent.

---

## Forma del pedido

Un archivo JSON que el CEO completa a partir de una plantilla.

```
{
  "que_se_quiere":     string,
  "para_que":          string,
  "alcance_excluido":  [string],
  "techo_costo_usd":   number,
  "techo_tiempo_min":  number,
  "techo_iteraciones": integer
}
```

`alcance_excluido` es la lista de cosas que el pedido deja explícitamente
afuera. Es contra esta lista que T7 evalúa su regla 5, así que conviene que los
términos sean los que uno espera ver en un plan: `"interfaz gráfica"`, no
`"nada visual"`.

## Qué cuenta como "el pedido" para la regla 4

T7 comprueba que el `rastreo` de cada unidad sea una cita textual del pedido.
El texto contra el que compara es:

```
que_se_quiere + "\n" + para_que
```

Ni más ni menos. `alcance_excluido` y los techos no forman parte del texto
rastreable.

---

## Validación

Se rechaza el pedido, sin iniciar corrida, si:

1. Falta cualquiera de los seis campos.
2. `que_se_quiere` o `para_que` están vacíos o son solo espacios.
3. `alcance_excluido` no es lista, o contiene elementos vacíos.
4. Cualquiera de los tres techos no es numérico o no es mayor que cero.
5. `techo_iteraciones` no es entero.

El rechazo nombra qué campo y por qué. No corrige, no completa por defecto.

**El rechazo ocurre antes de generar `run_id`.** Un pedido inválido no consume
nada y no deja corrida abierta, conforme al campo 3 de la Agent Definition: una
entrada que no valida se rechaza antes de ejecutar.

---

## Qué hace cuando el pedido es válido

En este orden exacto:

1. `nuevo_run_id()`
2. `append(run_id, "run_iniciada", "plataforma", {agent_definition_id, version})`
3. `append(run_id, "pedido_recibido", "plataforma", {pedido completo, íntegro})`
4. `append(run_id, "techos_declarados", "plataforma", {costo, tiempo, iteraciones})`
5. Devuelve el `run_id`

El pedido se registra **íntegro y sin normalizar**, conforme al punto 2 del
campo 12 de la Agent Definition. Si el CEO escribió algo raro, queda como lo
escribió.

No abre el Gate de entrada: eso es T11.

---

## Interfaz

```
intake.py --pedido ruta/al/pedido.json
```

Devuelve el `run_id` por salida estándar si el pedido es válido. Exit 0. Si no,
imprime los rechazos y exit 1.

Se entrega además una plantilla en `templates/pedido.template.json` con los seis
campos vacíos y un comentario de uso en el README.

---

## Criterio de aceptación de T8

| Prueba | Debe |
|---|---|
| Pedido válido | Devuelve run_id y deja exactamente tres eventos en el Operational State, en orden |
| Campo faltante | Rechaza nombrando el campo. Cero eventos escritos |
| Campo vacío | Rechaza `que_se_quiere: "   "`. Cero eventos |
| Techo cero | Rechaza `techo_costo_usd: 0`. Cero eventos |
| Techo no numérico | Rechaza `techo_tiempo_min: "veinte"`. Cero eventos |
| Iteraciones decimales | Rechaza `techo_iteraciones: 2.5`. Cero eventos |
| Alcance excluido con vacío | Rechaza `["interfaz gráfica", ""]`. Cero eventos |
| Integridad del pedido | El payload de `pedido_recibido` es idéntico al archivo de entrada |
| Texto rastreable | La función que arma el texto para la regla 4 devuelve exactamente `que_se_quiere + "\n" + para_que` |

"Cero eventos" es parte del criterio en todos los rechazos: un pedido inválido no
deja rastro de corrida.

---

## Fuera de alcance

No interpreta ni reformula el pedido. No abre Gates. No invoca al agente. No
tiene interfaz gráfica.
