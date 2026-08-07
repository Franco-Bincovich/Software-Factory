# T11 — Motor de Gates

Especificación de construcción. Vive en el repositorio de código.
Implementa ADR-004.

---

## Qué es

El mecanismo que frena una corrida y espera una decisión humana. No decide nada:
abre, bloquea, registra la resolución y devuelve el control.

---

## Los dos Gates de V0.1

**Gate de entrada.** Se someten el pedido y los tres techos, antes de consumir.
Corresponde al criterio 6 del piso de ADR-004 —ambigüedad de requerimiento— y al
criterio 4 —techos declarados—.

**Gate de salida.** Se somete el Plan de Trabajo producido, después de que pasó
la verificación estructural. **No corresponde a ningún criterio del piso**: es un
Gate propio de la Agent Definition, de los que ADR-004 permite agregar.

---

## Regla que gobierna todo lo demás

**El vencimiento nunca es aprobación.** No hay timeout. No hay valor por defecto.
No hay parámetro configurable de expiración.

Un Gate abierto bloquea la corrida indefinidamente hasta que una persona lo
resuelva. Si nadie lo resuelve, la corrida no avanza — para siempre, si hace
falta.

Esta ausencia es deliberada y no debe implementarse "por si acaso". Si en algún
momento se decide lo contrario, será por un ADR que reemplace a ADR-004.

---

## Ciclo de un Gate

**Abrir.** `append(run_id, "gate_abierto", "plataforma", {gate, somete})`
donde `gate` es `"entrada"` o `"salida"`, y `somete` es el artefacto sometido
íntegro: el pedido con sus techos, o el plan con el veredicto de T7.

**Bloquear.** La corrida no avanza. El reloj del techo de tiempo se detiene.

**Resolver.** `append(run_id, "gate_resuelto", "CEO", {gate, decision, motivo})`
donde `decision` es `"aprobado"` o `"rechazado"`.

- `motivo` es **obligatorio si rechaza**, opcional si aprueba. Un rechazo sin
  motivo no le sirve a nadie.
- El actor es siempre `CEO`. Ninguna pieza puede resolver un Gate en nombre de
  una persona.

**Continuar o terminar.** Aprobado: la corrida sigue. Rechazado: la corrida
termina con `run_finalizada` y el trabajo parcial se conserva.

---

## Restricciones

1. No se puede resolver un Gate que no está abierto.
2. No se puede resolver dos veces el mismo Gate.
3. No se puede abrir un Gate de salida si el de entrada no fue aprobado.
4. No se puede abrir un segundo Gate del mismo tipo en la misma corrida.

Cada una falla con error explícito, nombrando la corrida y el Gate.

---

## Ventanas de espera

Cada par `gate_abierto` / `gate_resuelto` define una ventana. T12 excluye la
suma de esas ventanas del techo de tiempo, según el punto 2 de ADR-010: esperar a
un humano no puede matar una corrida.

T11 no calcula el descuento — solo deja los eventos con sus marcas de tiempo para
que T12 lo haga.

---

## Interfaz

```
gates.py --listar
gates.py --resolver <run_id> --gate entrada|salida --decision aprobado|rechazado [--motivo "..."]
```

`--listar` muestra todos los Gates abiertos sin resolver, de todas las corridas,
con el artefacto sometido y desde cuándo esperan.

```python
abrir(run_id, gate, somete) -> None
esta_bloqueada(run_id)      -> bool
resolucion(run_id, gate)    -> {decision, motivo} | None
```

---

## Criterio de aceptación de T11

| Prueba | Debe |
|---|---|
| Abrir y bloquear | Tras `abrir`, `esta_bloqueada` es verdadero |
| Resolver aprobando | Tras resolver, `esta_bloqueada` es falso y `resolucion` devuelve la decisión |
| Rechazo sin motivo | Falla. No escribe evento |
| Aprobación sin motivo | Se acepta |
| Resolver Gate no abierto | Falla nombrando la corrida y el Gate |
| Resolver dos veces | El segundo intento falla |
| Salida antes de entrada | Abrir el Gate de salida sin entrada aprobada falla |
| Duplicado del mismo tipo | Abrir dos Gates de entrada en la misma corrida falla |
| Actor | El evento `gate_resuelto` tiene actor `CEO`, siempre |
| Listar | `--listar` muestra los abiertos de dos corridas distintas sin mezclarlos |
| Sin timeout | **No existe ningún parámetro, constante ni rama de código que apruebe por vencimiento.** Verificable por inspección del módulo |

---

## Fuera de alcance

No calcula el descuento de tiempo — eso es T12. No decide qué somete a Gate:
quien lo invoca decide. No notifica por ningún canal: en V0.1 el CEO consulta
con `--listar`.
