# T13 — Operational State

Especificación de construcción. Vive en el repositorio de código.
Implementa ADR-011.

---

## Qué es

El almacén de hechos de la fábrica. Todo lo que ocurrió durante una corrida se
escribe acá: qué pedido entró, qué produjo el agente, qué verificó la
plataforma, quién aprobó qué, cuánto se consumió.

Es la única fuente de verdad de los hechos. El Vault no participa.

---

## Dónde vive

Directorio hermano del vault y del repo de código:

```
/Users/franbincovich/Desktop/VSCode/software-factory-state/
```

**No versionado, no dentro de ningún repositorio git.** Un hecho no tiene
versiones, tiene ocurrencia.

Esto materializa R8: si ese directorio se pierde, se pierde toda la evidencia de
la fábrica sin reconstrucción posible. Hasta que exista Infrastructure, el
respaldo es manual.

## Sustrato

**SQLite**, archivo único, escritor único. Cumple las tres propiedades que exige
ADR-011: integridad transaccional, consulta sobre múltiples corridas, y
distinción entre eventos inmutables y estado derivado.

Condición de salida ya declarada en ADR-011: deja de alcanzar cuando aparezca
ejecución concurrente o aislamiento entre clientes, previstos en V0.4.

---

## Modelo

**Una sola tabla autoritativa: `evento`.** El estado actual de cualquier cosa se
deriva leyendo sus eventos. No hay tablas mutables en V0.1.

```sql
CREATE TABLE evento (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id   TEXT    NOT NULL,
  ts       TEXT    NOT NULL,   -- ISO 8601 UTC
  tipo     TEXT    NOT NULL,
  actor    TEXT    NOT NULL,
  payload  TEXT    NOT NULL    -- JSON
);

CREATE INDEX idx_evento_run  ON evento(run_id);
CREATE INDEX idx_evento_tipo ON evento(tipo);
```

`actor` nunca puede ser vacío ni `"sistema"`: ADR-009 punto 8 exige que toda
acción registrada nombre a su actor. Valores válidos en V0.1:
`requirement-agent`, `plataforma`, `CEO`.

### Inmutabilidad, forzada por la base

Los eventos no se editan ni se borran, según ADR-011 punto 3. No alcanza con no
escribir la función: la base lo impide.

```sql
CREATE TRIGGER evento_no_update BEFORE UPDATE ON evento
BEGIN SELECT RAISE(ABORT, 'evento es inmutable'); END;

CREATE TRIGGER evento_no_delete BEFORE DELETE ON evento
BEGIN SELECT RAISE(ABORT, 'evento es inmutable'); END;
```

### Tipos de evento en V0.1

| Tipo | Actor | Payload contiene |
|---|---|---|
| `run_iniciada` | plataforma | agent_definition_id, versión |
| `pedido_recibido` | plataforma | pedido completo, íntegro |
| `techos_declarados` | plataforma | costo, tiempo, iteraciones |
| `gate_abierto` | plataforma | tipo de gate, qué se somete |
| `gate_resuelto` | CEO | decisión, motivo si rechaza |
| `iteracion_producida` | requirement-agent | número de iteración, plan producido |
| `verificacion_ejecutada` | plataforma | veredicto y lista de incumplimientos |
| `consumo_registrado` | plataforma | costo, tiempo, iteraciones acumulados |
| `escalamiento` | requirement-agent | condición que lo disparó, info mínima |
| `run_cortada` | plataforma | qué techo se alcanzó |
| `run_finalizada` | plataforma | resultado |

Agregar tipos no requiere ADR. Quitar alguno, sí.

---

## Interfaz

```python
append(run_id, tipo, actor, payload) -> id
leer_run(run_id)                     -> [evento]  ordenados por id
gates_pendientes()                   -> [gate abierto sin resolver]
consumo(run_id)                      -> {costo, tiempo, iteraciones}
nuevo_run_id()                       -> str
```

**No existe función de update ni de delete.** No es un olvido: es la interfaz
completa.

`nuevo_run_id` genera un identificador único y opaco. Se llama antes de consumir
un solo token, según ADR-011 punto 4.

---

## Secretos

ADR-009 punto 4: ningún secreto entra al Operational State. Como nada se borra,
un secreto que entra queda para siempre.

`append` rechaza el evento si alguna clave del payload, a cualquier nivel de
anidamiento, coincide con: `password`, `passwd`, `secret`, `token`, `api_key`,
`apikey`, `credential`, `authorization`, `private_key`.

Es un control léxico y por lo tanto parcial. No detecta un secreto guardado bajo
un nombre inocente. Se declara como parcial en vez de fingir que cubre el caso.

---

## Criterio de aceptación de T13

| Prueba | Debe |
|---|---|
| Escribir y leer | `append` de cinco eventos, `leer_run` los devuelve en orden |
| Inmutabilidad — update | `UPDATE evento SET ...` falla con error de la base |
| Inmutabilidad — delete | `DELETE FROM evento` falla con error de la base |
| Reconstrucción | Con solo los eventos de una corrida se reconstruye qué pasó, sin consultar ninguna otra fuente |
| Actor obligatorio | `append` con actor vacío o `"sistema"` es rechazado |
| Secretos | `append` con payload que contiene `api_key` en cualquier nivel es rechazado |
| Consumo | `consumo` devuelve el acumulado correcto tras varios `consumo_registrado` |
| Gates | `gates_pendientes` devuelve solo los abiertos sin `gate_resuelto` posterior |
| Aislamiento entre corridas | Eventos de dos `run_id` distintos no se mezclan en `leer_run` |

---

## Fuera de alcance de T13

No decide cuándo se emite un evento — eso es de quien lo invoca. No implementa
Gates, ni el contador de presupuesto, ni la lógica de corte: solo persiste lo que
esas piezas producen. No expone interfaz de usuario. No tiene retención ni
purga: nada se borra en V0.1, según ADR-011 punto 6.
