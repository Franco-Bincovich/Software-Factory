---
tipo: adr
estado: aceptado
aprobado: 2026-08-27
version: 1.0
owner: CEO
actualizado: 2026-08-27
adr: [ADR-003, ADR-005, ADR-009]
aliases: [ADR-013]
---

# ADR-013 — Política de vendoring de skills externas

## Contexto

Una skill externa es texto de instrucciones que un agente ejecuta con sus propios
permisos, alojado en el repositorio de un tercero. Sin control, el autor original
puede reescribirlo sin aviso y sin aprobación.

Además muchas skills traen código ejecutable y archivos no documentales: de las
cinco primeras que se relevaron, cuatro traen scripts de Python, dos traen HTML y
una trae un PDF. Nada de eso es texto de instrucciones, y todo eso viaja junto en
la misma carpeta.

## Opciones consideradas

**A. Instalador automático de marketplace.** Cómodo, se actualiza solo. Sin
control sobre qué cambia ni cuándo: lo que el agente ejecuta hoy puede no ser lo
que se aprobó ayer, y nadie se entera.

**B. Vendoring firmado.** Elegida. Copia congelada en el repositorio propio, con
manifiesto, checksums y aprobación humana por skill.

## Decisión

Opción B. La política se declara en `skills/MANIFIESTO.md` y consta de cuatro
reglas, que se transcriben acá textualmente:

**1.** Se copia únicamente la carpeta de la skill. Ningún archivo de instrucciones que viva en la raíz del repo de origen —`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `hooks/` o cualquier equivalente— entra al repo sin una decisión explícita y firmada. Esos archivos le hablan al agente, no a la skill, y arrastran comportamiento que nadie pidió.

**2.** Actualizar una skill es un pull request revisado por un humano. Nunca automático. No hay sincronización periódica, ni script que traiga la última versión del upstream por su cuenta: cada cambio se mira, se compara contra lo que ya está y se aprueba a mano.

**3.** Ninguna skill se habilita mientras contenga archivos que no sean texto plano legible por un humano. El criterio es amplio: se declaran y se leen todos los archivos no documentales, no solo los ejecutables, porque un HTML puede traer JavaScript y un PDF es un formato con superficie de ataque propia. Estar copiada en el repo y estar habilitada son dos estados distintos: lo primero es este manifiesto, lo segundo exige que alguien haya leído todo lo que no sea markdown y que exista una frontera de ejecución aislada, un lugar donde correr esos archivos sin acceso al resto del sistema.

**4.** Las dependencias declaradas por una skill se congelan a versión exacta antes de habilitarla. Un `requirements.txt` sin versiones fijadas es motivo de rechazo: el hash del commit congela la skill, no lo que la skill descarga de internet al instalarse.

## Consecuencias

**Lo que cuesta.** Mantenimiento manual. Cada actualización de una skill es un
pull request que alguien tiene que mirar, y ninguna llega sola. A cambio se
obtiene control verificable: en cualquier momento se puede comprobar que lo que
el agente va a ejecutar es exactamente lo que se aprobó.

**Lo que no hay.** Sincronización automática. Es deliberado, no una carencia.

**Lo que cambia en el vocabulario.** Estar copiada y estar habilitada son estados
distintos. Una skill puede vivir en el repositorio durante meses sin que ningún
agente pueda usarla. El manifiesto registra lo primero; la columna "aprobado por"
registra lo segundo.

## Evidencia — dos correcciones durante la implementación

Las dos son falsos verdes: verificaciones que dieron bien y no debían. Se
documentan porque justifican las reglas mejor que cualquier argumento abstracto.

**1. Verificación contra el clon local en vez de contra el upstream.** La primera
verificación dio 49 de 49 idénticos. Comparaba contenido CRLF contra contenido
CRLF: el clon de origen en Windows había escrito los archivos con saltos de línea
convertidos, y la copia preservó fielmente esos bytes convertidos. Los blobs en
git estaban en LF. El manifiesto afirmaba copia textual del commit de origen y
describía bytes distintos de los de ese commit.

**2. Regla de protección con alcance corto.** Corregido lo anterior, un clon
limpio en Windows seguía fallando los 49 archivos. La regla `-text` de
`.gitattributes` cubría el contenido vendoreado pero no `CHECKSUMS.txt`, que vive
un nivel arriba: `core.autocrlf` le agregaba un CR al final de cada línea y
`sha256sum -c` fallaba por nombre de archivo inexistente, no por hash incorrecto.
Se había blindado el contenido y quedado desprotegida la herramienta que lo
verifica.

Ninguna de las dos apareció en la máquina donde se hizo el trabajo. Las dos
aparecieron al verificar desde un clon limpio, sin el estado previo.

## Lección transferible

Un prompt a un agente debe declarar la afirmación que el trabajo va a sostener al
terminar, no solo los pasos a ejecutar. "Verificar integridad" produjo
verificación local; la propiedad buscada era reproducibilidad por un tercero. Los
pasos se deducen de la afirmación; la afirmación no se deduce de los pasos.

Aplica al diseño de la verificación de V0.3: el defecto que importa aparece en el
clon limpio, no en el workspace donde el productor trabajó. Un verificador que
corre sobre el directorio de trabajo del agente comparte su estado, y por lo tanto
comparte sus puntos ciegos.

## Decisiones que habilita

El uso de skills externas por parte de los agentes de la Fábrica, una vez que
existan las dos piezas que hoy no existen: un cargador de skills y una frontera de
ejecución aislada. Hasta entonces las skills vendoreadas son contenido
versionado, no capacidad disponible.

## Decisiones que no resuelve

- **Qué agente puede usar qué skill.** Es materia de ADR-009 cuando exista el
  cargador.
- **Cómo se ejecuta el código de una skill.** La frontera de ejecución aislada no
  está diseñada. La regla tercera la exige sin decir cómo se construye.
- **Qué se hace cuando el upstream de una skill desaparece.** La copia congelada
  sobrevive, pero no hay política de fin de vida.
