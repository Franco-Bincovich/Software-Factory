# T12 — Contador de presupuesto

Especificación de construcción. Vive en el repositorio de código.
Implementa ADR-010.

---

## Qué es

Mide el consumo de una corrida contra sus tres techos y la corta al alcanzar
cualquiera de ellos. Mide **durante**, no al final: un techo que se verifica
cuando la corrida terminó no es un techo, es una estadística.

---

## Los tres techos

**Costo.** Suma de los deltas de todos los eventos `consumo_registrado` de la
corrida. Cada evento lleva lo consumido en ese momento, no el acumulado: el
acumulado es estado derivado y no se guarda como hecho.

**Tiempo.** Tiempo de reloj desde `run_iniciada`, **menos** la suma de las
ventanas de espera de Gates. Cada par `gate_abierto` / `gate_resuelto` define una
ventana que se descuenta. Un Gate abierto y todavía sin resolver descuenta desde
que se abrió hasta ahora.

Esperar a un humano no consume presupuesto, según el punto 2 de ADR-010.

**Iteraciones.** Cantidad de eventos `verificacion_ejecutada` de la corrida. Cada
ejecución del verificador cierra una iteración.

---

## Comportamiento al alcanzar un techo

Corta. No pide permiso, no sigue en modo degradado, no negocia.

1. `append(run_id, "run_cortada", "plataforma", {techo, valor_alcanzado, limite})`
2. La corrida se detiene.
3. El trabajo parcial **se conserva íntegro**. No se descarta, no se revierte.

**Agotar no es fallo.** Según el punto 4 de ADR-010, no dispara reintento
automático. Es materia de escalamiento, no de reintento.

El Gate del criterio 4 de ADR-004 se abre después del corte, no en lugar del
corte: sirve para decidir si se relanza, no para permitir que siga mientras se
decide.

---

## Elevar un techo

**T12 no lo implementa.** Elevar un techo es cambiar un parámetro de la Agent
Definition y relanzar. Modificar un techo con la corrida viva permitiría que el
límite ceda bajo presión, que es precisamente lo que el punto 7 de ADR-010 busca
evitar.

---

## Interfaz

```python
consumo(run_id)                    -> {costo, tiempo_min, iteraciones}
verificar(run_id, definicion)      -> None | TechoAlcanzado
registrar_consumo(run_id, costo)   -> None
```

`verificar` se llama antes de cada operación que consuma y después de cada
iteración. Devuelve `None` si hay margen; `TechoAlcanzado` con el techo, el valor
y el límite si no.

Quien recibe `TechoAlcanzado` detiene la corrida. `verificar` no emite
`run_cortada`: lo emite quien corta, para que la responsabilidad de cortar quede
en un solo lugar.

---

## Criterio de aceptación de T12

| Prueba | Debe |
|---|---|
| Suma de deltas | Tres `consumo_registrado` de 0.5 dan costo 1.5, no 0.5 |
| Costo bajo el techo | Con techo 2 y consumo 1.5, `verificar` devuelve `None` |
| Costo en el techo | Con techo 2 y consumo 2.0, devuelve `TechoAlcanzado` nombrando costo |
| Costo sobre el techo | Con consumo 2.5, devuelve `TechoAlcanzado` |
| Iteraciones | Cinco `verificacion_ejecutada` con techo 5 devuelven `TechoAlcanzado` |
| Tiempo neto | Con 30 min transcurridos y una ventana de Gate de 15, el tiempo contado es 15 |
| Gate abierto sin resolver | La ventana descuenta desde que se abrió hasta ahora |
| Dos ventanas | Se descuentan ambas |
| Tiempo bajo el techo por el descuento | Con techo 20, 35 min de reloj y 20 de espera, devuelve `None` |
| Prioridad | Si dos techos se alcanzan juntos, `TechoAlcanzado` nombra ambos |
| Sin efectos | `verificar` no escribe ningún evento |
| Corrida sin consumo | `consumo` de una corrida recién iniciada devuelve ceros, no falla |

---

## Fuera de alcance

No corta por sí mismo — devuelve el veredicto. No abre Gates. No decide si se
relanza. No proyecta costo a futuro ni agrega por proyecto: eso quedó diferido en
ADR-010 hasta tener corridas medidas.
