# T7 — Verificador estructural

Especificación de construcción. No es documento del Vault: vive en el
repositorio de código. El Vault ya contiene la norma (ADR-005 y el Contrato del
Plan de Trabajo); esto es cómo se implementa.

---

## Qué es

Un validador que recibe un Plan de Trabajo y devuelve un veredicto binario más
la lista de incumplimientos. No corrige, no interpreta, no completa. Lo ejecuta
la plataforma, nunca el agente productor.

---

## Forma canónica del Plan de Trabajo

**JSON validado contra esquema.** La vista markdown para el Gate humano es
derivada y no autoritativa.

```
{
  "plan_id":        string,
  "run_id":         string,
  "pedido_id":      string,
  "sucede_a":       string | null,
  "restricciones": {
    "techo_costo":       number,
    "techo_tiempo_min":  number,
    "techo_iteraciones": number,
    "alcance_excluido":  [string]
  },
  "unidades": [
    {
      "id":         string,
      "enunciado":  string,
      "criterios": [
        {
          "condicion_observable": string,
          "resultado_esperado":   string,
          "procedimiento":        string
        }
      ],
      "dependencias":       [string],
      "rastreo":            string,
      "artefacto_esperado": string
    }
  ],
  "supuestos":        [string],
  "fuera_de_alcance": [string]
}
```

`alcance_excluido` se copia literal del pedido. `rastreo` es una cita textual
del pedido, no una paráfrasis — de eso depende que la regla 4 sea comprobable
por máquina.

---

## Las siete reglas

| # | Comprueba | Cómo | Mecánica |
|---|---|---|---|
| 1 | Toda unidad tiene ≥1 criterio | `criterios` no vacío | Total |
| 2 | Todo criterio tiene las tres partes | Los tres campos presentes y no vacíos | Parcial — verifica presencia, no calidad |
| 3 | Dependencias existen | Cada id de `dependencias` está en `unidades` | Total |
| 4 | Rastreo al pedido | El texto de `rastreo` aparece literal en el pedido | Total |
| 5 | Sin alcance excluido | Ningún término de `alcance_excluido` aparece en `enunciado` ni en `artefacto_esperado` | Parcial — coincidencia léxica |
| 6 | Máximo 10 unidades | `len(unidades) <= 10` | Total |
| 7 | Sin ciclos | Orden topológico del grafo de dependencias | Total |

**Las reglas 2 y 5 son parciales y hay que decirlo.** La 2 verifica que las tres
partes estén, no que el criterio sea bueno: un criterio con tres campos llenos
de texto vago pasa. La 5 detecta coincidencia de palabras, no de significado: un
plan que viola el alcance excluido usando otras palabras pasa.

Ambas son las que la verificación sustantiva de V0.3 tiene que cubrir. Hasta
entonces las cubre el Gate humano, y esa es la razón concreta por la que el Gate
de salida no es una formalidad.

---

## Salida del verificador

```
{
  "valido": boolean,
  "incumplimientos": [
    {
      "regla":    integer,
      "unidad":   string | null,
      "criterio": integer | null,
      "detalle":  string
    }
  ]
}
```

Un incumplimiento nombra siempre la regla y, cuando aplica, la unidad y el
criterio exactos. Un rechazo que no localiza el problema es inutilizable, y
además el campo 9 del Requirement Agent depende de esta precisión para poder
corregir en vez de regenerar.

---

## Comportamiento

- Evalúa **todas** las reglas siempre. No corta en el primer incumplimiento: el
  agente necesita la lista completa para corregir en una sola iteración.
- Si el JSON no valida contra el esquema, devuelve inválido con regla `0` y no
  evalúa el resto.
- No modifica el plan. No escribe en el Vault. Registra su resultado en el
  Operational State asociado al `run_id`.
- Cada ejecución del verificador cierra una iteración a efectos del techo de
  ADR-010.

---

## Criterio de aceptación de T7

Seis planes de prueba. El verificador detecta exactamente el defecto sembrado en
cada uno y no marca nada en el limpio.

| Fixture | Defecto sembrado | Debe disparar |
|---|---|---|
| `plan-ok.json` | Ninguno | Ninguna |
| `plan-r1.json` | Una unidad con `criterios: []` | Regla 1 |
| `plan-r2.json` | Un criterio sin `procedimiento` | Regla 2 |
| `plan-r3.json` | Dependencia a `U9`, que no existe | Regla 3 |
| `plan-r5.json` | Una unidad que produce interfaz gráfica, con "interfaz gráfica" en `alcance_excluido` | Regla 5 |
| `plan-r7.json` | U1 depende de U2 y U2 de U1 | Regla 7 |

Además: sobre `plan-ok.json` el verificador no debe reportar ningún
incumplimiento. Un falso positivo sobre el plan limpio invalida T7 igual que un
falso negativo.

---

## Fuera de alcance de T7

No valida el pedido de entrada — eso es T8. No aprueba ni rechaza planes: emite
un veredicto que el motor de Gates consume. No estima, no puntúa, no ordena por
calidad.
