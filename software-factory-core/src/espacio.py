"""El espacio de trabajo que crece, y su punto de retorno — ADR-019.

Hasta ADR-019 cada unidad tenía su propio subdirectorio y no veía a las otras.
Desde acá hay **un solo espacio por cadena**, y cada parte le suma. La contención
que antes daba una pared —el subdirectorio— ahora la da una marca en el tiempo:
cada parte aprobada deja un commit, y volver es volver a ese commit.

## Por qué git y no un mecanismo propio

Porque ya existe y ya está medido. Un punto de retorno hecho a mano sería, en el
mejor caso, una copia del directorio por parte firmada —que es exactamente lo que
ADR-019 sacó del medio— y en el peor, un formato nuevo que hay que respaldar,
verificar y explicar. Git da el commit, el diff contra lo firmado y la vuelta
atrás sin escribir ninguna de las tres cosas.

**El SHA del commit es un hecho y se registra como tal.** No es reproducible —lo
determinan también la fecha y el autor—, así que por el punto 1 de ADR-011 tiene
que estar en el Operational State: regenerar la corrida no lo recupera.

**Firma la plataforma, nunca el agente.** Es la misma separación por la que el
agente no ejecuta su propia verificación: el Developer declara qué archivos
produjo y la plataforma decide si eso queda firmado.

## Por qué `.git` no viaja al depósito

El depósito es lo que se ejecuta, y `ejecutor.revisar_entrada` recorre el
directorio entero rechazando todo lo que no sea texto UTF-8 —`.git/index` y los
objetos son binarios—. Antes que aflojar esa regla, que es la puerta de la
frontera de ADR-016, el `.git` no entra: `copiar_sin_git` es el único lugar donde
el espacio versionado se convierte en un depósito ejecutable, y ahí se lo saca.
"""

import shutil
import subprocess
from pathlib import Path

# Quién firma. No es una persona y el registro no debe sugerir que lo sea.
AUTOR = "Software Factory <plataforma@software-factory.local>"
NOMBRE, CORREO = AUTOR.split(" <")[0], AUTOR.split(" <")[1].rstrip(">")

IGNORAR = shutil.ignore_patterns(".git")


class GitNoDisponible(RuntimeError):
    """No hay `git` en el PATH, o falló una operación sobre el espacio.

    No se degrada a "seguí sin punto de retorno": ADR-019 punto 2 es lo que hace
    tolerable haber perdido el aislamiento entre unidades. Sin él, una parte que
    rompe algo firmado no tiene a dónde volver.
    """


def _git(directorio, *argumentos):
    try:
        completado = subprocess.run(
            ["git", "-C", str(directorio), *argumentos],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise GitNoDisponible(
            "no hay `git` en el PATH. El punto de retorno de ADR-019 punto 2 se "
            "materializa con un commit por parte aprobada; sin git no hay a dónde "
            "volver cuando una parte rompe algo firmado."
        )
    except subprocess.CalledProcessError as fallo:
        raise GitNoDisponible(
            "`git %s` falló en '%s' con código %s: %s"
            % (" ".join(argumentos), directorio, fallo.returncode, fallo.stderr.strip())
        )
    return completado.stdout.strip()


def iniciar(directorio):
    """Deja el espacio versionado. Idempotente: se llama al crear y al reanudar.

    La identidad y el `commit.gpgsign` se fijan **locales al espacio**. Local y
    no global porque esto es un directorio descartable de la Fábrica y no tiene
    por qué tocar la configuración de nadie; y `gpgsign` apagado porque una firma
    GPG abriría un pedido de passphrase que colgaría la cadena sin decir por qué.
    Lo que acá se firma es una parte del trabajo, no una autoría.
    """
    ruta = Path(directorio)
    ruta.mkdir(parents=True, exist_ok=True)
    if not (ruta / ".git").is_dir():
        _git(ruta, "init", "--quiet")
    _git(ruta, "config", "user.name", NOMBRE)
    _git(ruta, "config", "user.email", CORREO)
    _git(ruta, "config", "commit.gpgsign", "false")
    return str(ruta)


def firmar(directorio, mensaje):
    """Cierra una parte aprobada y devuelve el SHA de su commit.

    `--allow-empty` a propósito: la correspondencia entre parte firmada y punto
    de retorno tiene que ser total. Una parte que sólo reescribió los agregadores
    con contenido idéntico no cambió ningún byte, y aun así se aprobó; sin commit
    quedaría sin punto al cual volver y el mapa tendría un agujero.
    """
    _git(directorio, "add", "--all")
    _git(directorio, "commit", "--allow-empty", "--quiet", "--message", mensaje)
    return _git(directorio, "rev-parse", "HEAD")


def ultimo_firmado(directorio):
    """El SHA de la última parte firmada, o `None` si todavía no hay ninguna."""
    if not (Path(directorio) / ".git").is_dir():
        return None
    try:
        return _git(directorio, "rev-parse", "HEAD")
    except GitNoDisponible:
        # Espacio recién iniciado: hay `.git` y no hay commits. No es un fallo.
        return None


def volver(directorio, commit):
    """Devuelve el espacio al estado exacto de una parte firmada.

    Es el punto de retorno de ADR-019 punto 2 puesto a andar. Descarta lo que
    haya quedado suelto de una parte que no llegó a firmarse —una corrida que se
    cortó a mitad deja archivos que nadie aprobó—, y por eso limpia también lo no
    versionado: si no, la parte siguiente arrancaría sobre restos de la anterior
    y el "último estado firmado" no sería el estado.
    """
    _git(directorio, "reset", "--hard", "--quiet", commit)
    _git(directorio, "clean", "-fdq")


def copiar_sin_git(origen, destino):
    """Copia el espacio a donde se va a ejecutar, sin su historia.

    Es la única frontera entre el espacio versionado y el depósito ejecutable.
    Ver el encabezado del módulo: `ejecutor.revisar_entrada` rechaza todo lo que
    no sea texto UTF-8, y los objetos de git no lo son.
    """
    shutil.copytree(origen, destino, ignore=IGNORAR, dirs_exist_ok=True)
    return str(destino)


__all__ = [
    "GitNoDisponible",
    "copiar_sin_git",
    "firmar",
    "iniciar",
    "ultimo_firmado",
    "volver",
]
