# Verificador estructural de Entregas

Especificación de construcción. No es documento del Vault: vive en el
repositorio de código. El Vault ya contiene la norma —el Contrato de Entrega del
Developer, el Ruleset mecánico y la Agent Definition del Developer—; esto es cómo
se implementa.

Es el par de [T7](T7-spec.md) para código. Todo lo que T7 hace con un Plan de
Trabajo, esto lo hace con una Entrega.

---

## Qué es

Un validador que recibe una Entrega y el Plan de Trabajo que la originó, y
devuelve un veredicto binario más la lista de incumplimientos. No corrige, no
interpreta, no completa. Lo ejecuta la plataforma, nunca el agente productor.

**No ejecuta nada de lo que verifica.** El único proceso externo que lanza es
`node --check`, que parsea el archivo y termina sin correr una sola línea.

## Dos módulos

| Módulo | Qué sabe |
|---|---|
| `src/verificador_entrega.py` | Qué es una Entrega: el esquema, las reglas del contrato, la orquestación y la CLI |
| `src/inspeccion_js.py` | Texto de código: parseo, `<script>`, Ruleset, prohibiciones, anti-teatro. No sabe qué es una Entrega |

```
./.venv/bin/python src/verificador_entrega.py <entrega.json> --plan <plan.json>
```

El plan es obligatorio: lo exigen C1, C4 y V2. La unidad no se pasa por
separado — sale de la propia entrega, y que exista en el plan es C1.

---

## Forma canónica de la Entrega

```
{
  "unidad": string,
  "archivos": [
    {
      "ruta":      string,
      "rol":       "artefacto_esperado" | "auxiliar",
      "contenido": string,
      "motivo":    string        // solo los auxiliares, y es obligatorio en ellos
    }
  ],
  "supuestos": [string]
}
```

`additionalProperties: false` en los dos niveles. Por eso la regla C9 del
contrato —la entrega no trae más campos que los tres declarados— **no tiene
implementación propia: se cumple en el esquema y un campo de más se reporta como
C0**. Es la misma mecánica por la que T7 delega la forma en su regla 0.

---

## Los identificadores de regla

En T7 la regla es un entero, porque las siete salen de un solo documento. Acá
salen de tres, y el prefijo dice de cuál. Un incumplimiento que no se puede
rastrear al documento que lo exige no se puede discutir.

| Prefijo | Origen | Numeración |
|---|---|---|
| `C` | Contrato de Entrega del Developer | Su número exacto de regla de validez |
| `R` | Ruleset mecánico | Su número exacto de regla |
| `P` | Prohibiciones del Contrato de Entrega | Propia: no están numeradas en el documento |
| `V` | Este verificador | Propia: no tienen número en ningún documento |

**Cada defecto se reporta una sola vez, bajo el identificador más específico.**
La lectura del entorno es R3 en el Ruleset y prohibición en el contrato: se
reporta como `P2` y no como las dos. Una lista que muestra dos problemas donde
hay uno hace que el reintento corrija dos veces lo mismo.

### Las reglas

| id | Comprueba | Mecánica |
|---|---|---|
| `C0` | La entrega valida contra el esquema | Total |
| `C1` | La unidad declarada existe en el plan | Total |
| `C2` | Rutas relativas, sin `..`, sin vacías | Total |
| `C3` | Contenido completo, sin marcadores de fragmento | Parcial — coincidencia léxica |
| `C4` | El artefacto que la unidad declaró esperar está en la entrega | Parcial — extrae rutas de un campo en prosa |
| `C5` | Lo que no es uno de los cuatro entregables está declarado auxiliar y justificado | Total |
| `C6` | Los cuatro entregables presentes y ninguno vacío | Total |
| `C7` | Los dos HTML cargan la lógica y ninguno la reimplementa | Parcial — ve declaraciones, no equivalencia |
| `C8` | No hay dos archivos con la misma ruta | Total |
| `C9` | — | Cubierta por `C0` |
| `R1` | Ningún archivo pasa de 200 líneas | Total |
| `R3` | Sin `console.log(` ni secretos literales | Parcial — la detección de secretos es léxica |
| `R8` | El archivo de pruebas ejercita la lógica entregada | Parcial — que exista y la nombre, sí; que la pruebe bien, no |
| `P1` | No abre conexiones de red | Parcial — formas conocidas |
| `P2` | No lee variables de entorno | Parcial — formas conocidas |
| `P3` | No escribe fuera del directorio de trabajo | Parcial — formas conocidas |
| `V1` | Cada archivo de código parsea | Total |
| `V2` | Los nombres que mencionan los criterios aparecen en el código | Parcial — ver abajo |
| `V3` | `pruebas.html` invoca la función por su nombre | Total |
| `V4` | Los veredictos salen de ejecutar la función, no de texto fijo | Parcial — ver abajo |

**R10 no está, y es deliberado.** "Diff limpio" sin diff se traduce a cosas que
ya cubren `C5` —archivos que nadie pidió— y `R3` —restos de depuración y
secretos—. Un identificador que existe solo para que la Agent Definition no quede
desmentida es documentación que miente sobre lo que verifica. La Agent Definition
declara tres reglas del Ruleset, no cuatro.

### Las dos reglas más parciales, y qué no ven

**`V2` es angosto a propósito.** Los criterios de aceptación son prosa. Exigir
que cada palabra aparezca en el código produciría incumplimientos inventados, así
que solo se extraen los tokens con forma de identificador: lo que va entre
backticks, `camelCase` y `snake_case`. **Si la unidad no nombra identificadores,
V2 no encuentra nada y pasa en vacío.** Es preferible a inventar coincidencias
sobre prosa, y es la razón por la que conviene que los Acceptance Criteria
nombren las cosas por su nombre.

**`V4` es la comprobación más parcial de todas.** Detecta un veredicto pintado en
el HTML estático, fuera de todo `<script>`, y un literal de veredicto asignado
sin elegirlo — `textContent = "PASA"` se marca, `textContent = paso ? "PASA" :
"FALLA"` no. **No detecta** un script que invoca la función, ignora lo que
devuelve y escribe "PASA" igual. Eso queda para el Gate humano, que es el que
abre el archivo. Se declara acá para que nadie lea "pasó V4" como "las pruebas
son de verdad".

---

## Salida del verificador

```
{
  "valido": boolean,
  "incumplimientos": [
    {
      "regla":   string,
      "archivo": string | null,
      "detalle": string
    }
  ]
}
```

Misma forma que T7, con `archivo` donde aquel lleva `unidad` y `criterio`: es el
localizador que corresponde al artefacto que se verifica. Un rechazo que no
localiza el problema es inutilizable, y el campo 9 del Developer Agent depende de
esta precisión para poder corregir en vez de regenerar.

## Comportamiento

- Evalúa **todas** las reglas siempre. No corta en el primer incumplimiento: el
  agente necesita la lista completa para corregir en una sola iteración.
- Si la entrega no valida contra el esquema, devuelve `C0` y no evalúa el resto.
- **Si la entrega viene vacía, devuelve solo `C6` y no evalúa el resto.** Una
  entrega vacía con motivo es la salida que el contrato declara válida ante una
  unidad ambigua: no se corrige, se escala. Apilarle las demás reglas mandaría a
  reintentar lo que no se reintenta.
- **Si no hay `node` en el PATH, falla nombrando qué falta.** No degrada a
  "pasa": un verificador que no pudo parsear y aun así aprueba miente sobre lo
  que verificó. Mismo criterio que `ModeloSinPrecio` en T15.
- No modifica la entrega. No escribe en el Vault. No borra el directorio de
  trabajo.

---

## Criterio de aceptación

Una entrega limpia y un defecto sembrado por regla. El verificador detecta
exactamente el defecto de cada uno y no marca nada en la limpia. Un falso
positivo sobre la entrega limpia lo invalida igual que un falso negativo.

**Los defectos se siembran mutando la fixture limpia**, no con un archivo por
defecto como en T7. Es deliberado: una entrega lleva el contenido completo de
cuatro archivos, y veinte copias casi idénticas divergen sin que nadie lo note.
La mutación queda a dos líneas de su assert.

| Fixture | Qué es |
|---|---|
| `fixtures/entrega-ok.json` | La entrega limpia: `validarLegajo` con sus cuatro entregables |
| `fixtures/plan-entrega.json` | El plan de una sola unidad U1 a la que responde |

Es el mismo ejemplo que cierra el Contrato de Entrega del Developer, para que el
Vault y el código cuenten la misma historia.

Dos comprobaciones más allá de una por regla: que un esquema inválido no evalúe
el resto, y que dos defectos de reglas distintas se reporten los dos.

---

## Fuera de alcance

No ejecuta las pruebas ni abre los HTML: eso lo hace el humano en el Gate de
salida, y en V0.2 no hay otra cosa que lo haga. No aprueba ni rechaza entregas:
emite un veredicto que el motor de Gates consume. No verifica que el código haga
lo que la unidad pedía — eso es verificación sustantiva y llega en V0.3 con el
QA Agent. No está cableado al grafo: el armazón de V0.1 verifica planes y no sabe
de entregas, y conectarlo es trabajo de V0.2.
