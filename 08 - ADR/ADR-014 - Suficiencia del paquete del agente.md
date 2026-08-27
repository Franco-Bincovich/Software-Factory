---
tipo: adr
estado: aceptado
aprobado: 2026-08-27
version: 1.0
owner: CEO
actualizado: 2026-08-27
adr: [ADR-003, ADR-005, ADR-011]
aliases: [ADR-014]
---

# ADR-014 — El paquete del agente debe contener todo lo necesario para decidir

## Contexto

En la corrida real de la cadena Developer —`b84a066ec6fe4ea59377166f13f6f480`,
2026-08-27— el Developer Agent no recibió la ruta de su directorio de trabajo ni
la lista de archivos ya depositados en él. Trabajó sobre rutas relativas sin
saber dónde aterrizaban.

Las tres consecuencias están registradas en el Operational State:

**1. Un rechazo pagado.** En la iteración 1 de U2 (evento 48) el agente renombró
sus entregables a `pruebas-U2.html` y `demo-U2.html` para no pisar los homónimos
de U1. El verificador lo rechazó por C5 —archivo que ninguna unidad pidió— y por
C6 —faltan `pruebas.html` y `demo.html`— (evento 49). El intento costó USD
0.276285, el paso más caro de la cadena: los otros dos consumos registrados
fueron USD 0.034305 y USD 0.074106.

**2. Un supuesto falso escrito en un registro inmutable.** En la iteración 2
(evento 51) el agente cedió y declaró como supuesto que reemplazaría los archivos
de U1. Ese reemplazo nunca ocurrió: el evento 55 muestra que la plataforma
deposita cada unidad en su propio subdirectorio, `U1/` y `U2/`. El agente declaró
un daño que no hizo, y por ADR-011 punto 3 eso no se corrige nunca.

**3. Eventos atados a una máquina.** Los eventos 31 y 33 registran rutas
absolutas de la máquina donde se corrió (`/Users/franbincovich/...`). Desde el
commit `351f7ce` el código es portable, pero los eventos siguen sin serlo.

Las tres tienen la misma raíz: el agente decidió sobre información que no tenía.

## Opciones consideradas

**A. Endurecer el verificador.** Detectar antes el nombre inventado y rechazar
más rápido. Descartada: abarata el síntoma y no toca la causa. El agente seguiría
adivinando, y adivinar barato sigue siendo adivinar.

**B. Flexibilizar el contrato de entregables** para admitir sufijos por unidad.
Descartada: los nombres fijos son exactamente lo que hace verificable la entrega.
Admitir variantes convierte C6 en una regla que no puede fallar.

**C. Completar el paquete que recibe el agente.** Elegida.

**D. Que el agente consulte el directorio por su cuenta**, leyendo el disco antes
de producir. Descartada: contradice ADR-003 —lo que un agente lee se declara, no
se descubre— y hace que la entrega dependa del estado del disco al momento de
mirar, que no es reproducible.

## Decisión

### 1. El paquete lleva el domicilio y el inventario

El paquete que recibe el Developer incluye **la ruta absoluta de su directorio de
trabajo** y **la lista de archivos ya depositados en él**.

Con esos dos datos, la decisión que en la corrida real se tomó a ciegas —¿piso o
no piso lo de U1?— deja de ser una decisión: es una lectura.

### 2. El contrato de cuatro entregables no se modifica

Los nombres fijos se mantienen. El defecto no estaba en el contrato sino en que
el agente ignoraba dónde aterrizaban sus archivos.

Se acepta explícitamente que una unidad duplique un archivo ya entregado por
otra: que `pruebas.html` funcione abriéndolo solo vale más que ahorrar un
archivo. La redundancia es el precio de que cada unidad sea verificable por
separado, y es barato.

### 3. Los eventos registran rutas relativas al directorio de estado

No absolutas. Una ruta absoluta en el registro convierte la evidencia en algo que
solo se entiende en la máquina que la produjo.

**Los eventos ya escritos no se corrigen.** ADR-011 punto 3 no admite excepción,
y además los eventos 31 y 33 sirven ahora como evidencia de que la Fábrica corrió
atada a una máquina. Un registro que se limpia deja de probar.

### 4. Principio general: lo que no se entrega, se inventa

Esta es la norma, y aplica a todo agente presente y futuro:

> Todo dato que un agente necesite para decidir debe estar en el paquete que
> recibe.

Lo que no se le entrega, lo asume. Y el supuesto entra al registro con la misma
jerarquía que un hecho verificado: quien lea el evento 51 dentro de seis meses no
tiene forma de distinguir el supuesto inventado del dato comprobado, porque el
formato es el mismo.

De ahí lo que hace peligroso el problema. **Un agente que trabaja a ciegas no
falla ruidosamente: produce trabajo plausible sobre premisas inventadas.** No hay
excepción, ni traza, ni nada que mirar. Hay una entrega bien formada que responde
a un mundo que no existe.

Por eso la carga de la prueba se invierte: no es el agente el que tiene que
arreglárselas con lo que le llegó, es el paquete el que tiene que ser suficiente.

## Consecuencias

**Lo que habilita.** La cadena deja de pagar un rechazo por unidad. Sin la parte
1, cada unidad posterior a la primera paga un reintento: con cinco unidades son
cuatro rechazos garantizados, y el costo escala con el tamaño del plan en vez de
con su dificultad. Los supuestos declarados vuelven a ser lo que ADR-003 quiso
que fueran —zonas grises reales del plan— y no compensación por información
faltante.

**Lo que cuesta.** El paquete crece, y con él los tokens de entrada de cada
llamada. Se acepta: el inventario de un directorio de trabajo es corto, y un
rechazo cuesta USD 0.276285 mientras que unas líneas de listado cuestan órdenes
de magnitud menos.

**Lo que introduce.** Una obligación nueva sobre quien arma el paquete. Todo
agente que se defina de acá en adelante tiene que responder qué necesita saber
para decidir, y esa respuesta es parte de su definición, no del código que lo
invoca.

**Lo que no cambia.** El contrato de entregables, la capa de verificación de
ADR-005 y la inmutabilidad de ADR-011. Este ADR no relaja ninguna regla: agrega
información para que las reglas existentes se puedan cumplir.

## Decisiones que habilita

- Auditoría del paquete de cada agente: con el principio declarado, revisar una
  Agent Definition incluye preguntar qué decide y con qué datos.
- Cadenas de más de dos unidades sin costo de rechazo estructural.
- Comparación de corridas entre máquinas, una vez que los eventos dejen de llevar
  rutas absolutas.

## Decisiones que no resuelve

- **El formato concreto del inventario** —lista plana, árbol, con o sin tamaños—.
  Es implementación y se decide al construirlo.
- **Qué lleva el paquete de los demás agentes.** Este ADR fija el principio y lo
  aplica al Developer, que es donde se rompió. Cada Agent Definition declara lo
  suyo.
- **Cómo se detecta un paquete insuficiente antes de gastar tokens.** Hoy se
  descubre por el rechazo. Una verificación previa es deseable y no la necesita
  V0.2.
- **Qué hacer con los eventos ya escritos con rutas absolutas.** Nada: quedan.
  Convivir con evidencia vieja en un formato viejo es el costo de la
  inmutabilidad.
