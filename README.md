# software-factory-core

Verificador estructural de Planes de Trabajo — tarea T7 de V0.1.

Recibe un Plan de Trabajo en JSON y el texto del pedido que lo originó, y
devuelve un veredicto binario más la lista de incumplimientos. No corrige, no
interpreta y no completa planes: solo comprueba y localiza. Lo ejecuta la
plataforma, nunca el agente que produjo el plan.

La especificación completa está en [`docs/T7-spec.md`](docs/T7-spec.md).

```
schema/     esquema JSON del Plan de Trabajo
src/        el verificador
fixtures/   el pedido base y los seis planes de prueba
tests/      un test por fixture
docs/       la especificación
```

## Requisitos

Python 3.9 o superior y `jsonschema`. Es la única dependencia fuera de la
librería estándar.

```
python3 -m venv .venv
./.venv/bin/pip install jsonschema
```

## Cómo se corre

```
./.venv/bin/python src/verificador.py <plan.json> --pedido <pedido.txt>
```

El pedido es obligatorio: la regla 4 comprueba que el `rastreo` de cada unidad
aparezca literal en él.

```
./.venv/bin/python src/verificador.py fixtures/plan-ok.json --pedido fixtures/pedido.txt
```

Imprime el veredicto en JSON por salida estándar. Termina en 0 si el plan es
válido y en 1 si no lo es.

```json
{
  "valido": false,
  "incumplimientos": [
    {
      "regla": 3,
      "unidad": "U4",
      "criterio": null,
      "detalle": "La dependencia 'U9' no corresponde a ninguna unidad del plan."
    }
  ]
}
```

Evalúa las siete reglas siempre y devuelve la lista completa; no corta en el
primer incumplimiento. Si el plan no valida contra el esquema devuelve regla `0`
y no evalúa el resto.

## Cómo se corren los tests

```
./.venv/bin/python -m unittest discover -s tests -v
```

Nueve tests: uno por cada uno de los seis fixtures y tres sobre la forma de la
salida. Cada test de fixture comprueba que se dispara exactamente la regla
sembrada y ninguna otra; el del plan limpio comprueba cero incumplimientos.
