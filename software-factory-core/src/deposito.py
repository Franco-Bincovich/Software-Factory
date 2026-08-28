"""El depósito de artefactos — ADR-017.

ADR-017 separó dos cosas que estaban en la misma tabla: el **registro de qué
pasó** y el **depósito de lo que se produjo**. Este módulo es la segunda mitad.

El evento `entrega_producida` registra la ruta, el rol y el **SHA-256** de cada
archivo. El contenido vive acá. El hash es lo que ata las dos mitades: el
registro sigue identificando sin ambigüedad qué se entregó aunque ya no lo
contenga, y una alteración posterior del depósito es detectable.

## El orden no es indiferente

Se deposita, se relee lo escrito para comprobarlo contra su hash, y recién
entonces se appendea el evento. El corte deja archivos sin evento, nunca evento
sin archivos, y eso es deliberado.

Un archivo sin evento es basura inerte: nadie lo reclama —todo lector entra por
`run_id`— y el reintento lo sobrescribe con contenido idéntico en la misma ruta,
porque el hash de lo mismo es el mismo. Se limpia solo. Un evento sin archivo es
el registro afirmando una entrega y exhibiendo el hash de algo que no existe, y
**no se puede corregir**: por ADR-011 punto 3 un evento no se modifica ni se
borra. Queda ahí para siempre. Es la "afirmación sin objeto" contra la que se
escribió ADR-015.

Es el mismo orden que ya usa `grafo._nodo_fin`, que materializa antes de borrar
para que un corte no deje ni copia ni evidencia.

## Las dos formas del evento

ADR-017 punto 4: el cambio aplica sólo hacia adelante y no se migra nada. Los
eventos anteriores conservan el contenido adentro; los nuevos llevan hash. Todo
lector tiene que tolerar las dos formas y **distinguirlas por presencia de
campo, no por fecha**.

Acá eso se resuelve en un solo lugar: `entrega_del_evento` devuelve siempre una
entrega con contenido, lo tuviera el evento o haya que ir a buscarlo al
depósito. Aguas abajo nadie sabe de qué forma vino, que es la única manera de
que las dos convivan sin ensuciar cada consumidor.
"""

import hashlib
from pathlib import Path

from operational_state import absoluta_desde


class RutaFueraDelDirectorio(RuntimeError):
    """Una ruta de la entrega escaparía del directorio de trabajo.

    Es la regla C2 del verificador de entregas, comprobada otra vez acá y a
    propósito. Escribir es irreversible: lo que verifica un módulo y ejecuta otro
    se comprueba en los dos.
    """


class DepositoIncompleto(RuntimeError):
    """El evento nombra un archivo que no está en el depósito.

    Desde ADR-017 el contenido existe únicamente en el área de entregas. Si
    falta, no hay de dónde sacarlo: se levanta acá en vez de seguir con una
    entrega a medias.
    """


class DepositoAlterado(RuntimeError):
    """Un archivo del depósito no coincide con el hash que el evento registró.

    Es para lo que está el hash. El registro es inmutable y el depósito no, así
    que el registro es el que manda sobre qué debería haber ahí.
    """


def sha256_de(contenido):
    """El hash del archivo tal como el evento lo registra.

    Se calcula sobre el texto codificado en UTF-8, que es exactamente lo que
    `escribir_entrega` deposita en disco. Si se calculara sobre otra cosa, el hash
    firmado en el Gate no serviría para comprobar el archivo materializado.
    """
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def escribir_entrega(directorio, entrega):
    """Materializa los archivos de una entrega ya verificada.

    Escribe la plataforma, no el agente: el agente declara qué archivos produjo y
    la plataforma los deposita donde corresponde. Es la misma separación por la
    que el agente no ejecuta su propia verificación.

    Solo se llama con una entrega que pasó el verificador. Aun así se comprueba
    que ninguna ruta escape del directorio, porque escribir no se deshace.
    """
    raiz = Path(directorio).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    escritos = []
    for archivo in entrega["archivos"]:
        destino = (raiz / archivo["ruta"]).resolve()
        if raiz not in destino.parents and destino != raiz:
            raise RutaFueraDelDirectorio(
                "la ruta '%s' de la entrega quedaría fuera del directorio de "
                "trabajo '%s'." % (archivo["ruta"], raiz)
            )
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(archivo["contenido"], encoding="utf-8")
        escritos.append(archivo["ruta"])
    return escritos


def ruta_de_iteracion(raiz_entregas, run_developer, iteracion):
    """Dónde vive el contenido de una iteración: `<run_developer>/<iteracion>/`.

    **Cada iteración, no sólo la aceptada.** Una iteración rechazada existía
    hasta ADR-017 únicamente adentro de su evento: `escribir_entrega` sobre el
    área de trabajo corre recién cuando la unidad salió entregada, así que lo que
    el verificador rechazó nunca tocaba el disco. Si el evento pierde el
    contenido y sólo se deposita lo aceptado, ese código desaparece — y ADR-015
    punto 3 lo conserva por diseño, porque es lo que permite entender por qué se
    rechazó.

    Por corrida de Developer y no por unidad: el `run_id` ya es único por unidad,
    y colgar de él deja el rastro de una unidad junto en un solo lugar.
    """
    return Path(raiz_entregas) / run_developer / str(iteracion)


def depositar(entrega, destino):
    """Deposita el contenido y devuelve la entrega tal como va al evento.

    Relee cada archivo y lo compara contra el hash de lo que se quiso escribir.
    No es paranoia: el evento va a afirmar ese hash, y afirmarlo sin haber
    mirado el disco sería volver a firmar sobre algo que nadie vio.

    De cada archivo conserva todo menos el contenido, y le agrega el `sha256`.
    Los otros campos —`rol`, `motivo`— son parte de qué se entregó y pesan
    nada; el contenido es lo único que hacía crecer el registro con el tamaño de
    lo producido en vez de con la cantidad de hechos.
    """
    escribir_entrega(destino, entrega)
    raiz = Path(destino)
    archivos = []
    for archivo in entrega["archivos"]:
        esperado = sha256_de(archivo["contenido"])
        escrito = sha256_de((raiz / archivo["ruta"]).read_text(encoding="utf-8"))
        if escrito != esperado:
            raise DepositoAlterado(
                "el archivo '%s' quedó en el depósito con hash %s y la entrega "
                "declaraba %s." % (archivo["ruta"], escrito, esperado)
            )
        registrado = {k: v for k, v in archivo.items() if k != "contenido"}
        registrado["sha256"] = esperado
        archivos.append(registrado)
    return dict(entrega, archivos=archivos)


def rehidratar(entrega, deposito):
    """Le devuelve el contenido a una entrega que el evento registró por hash.

    Comprueba cada archivo contra su hash. Que una lectura verifique parece de
    más hasta que se piensa qué significa que no lo haga: el área de entregas es
    desde ADR-017 el único lugar donde el contenido existe, y leerla sin
    comprobar sería confiar en un depósito mutable para reconstruir evidencia.
    """
    raiz = Path(deposito)
    archivos = []
    for archivo in entrega["archivos"]:
        origen = raiz / archivo["ruta"]
        if not origen.is_file():
            raise DepositoIncompleto(
                "el evento registra el archivo '%s' con hash %s, pero no está en "
                "el depósito '%s'." % (archivo["ruta"], archivo["sha256"], raiz)
            )
        contenido = origen.read_text(encoding="utf-8")
        real = sha256_de(contenido)
        if real != archivo["sha256"]:
            raise DepositoAlterado(
                "el archivo '%s' del depósito '%s' tiene hash %s y el evento "
                "registró %s. El registro es inmutable y el depósito no: manda "
                "el registro." % (archivo["ruta"], raiz, real, archivo["sha256"])
            )
        recuperado = {k: v for k, v in archivo.items() if k != "sha256"}
        recuperado["contenido"] = contenido
        archivos.append(recuperado)
    return dict(entrega, archivos=archivos)


def entrega_del_evento(payload, base):
    """La entrega de un `entrega_producida`, con contenido, venga como venga.

    Las dos formas se distinguen **por presencia de campo**, que es lo que manda
    ADR-017 punto 4. Por fecha sería más simple y estaría mal: el registro
    histórico no lleva una marca de versión y el día de la implementación no es
    un dato que el evento tenga.

    La entrega vacía —válida por contrato ante una unidad ambigua— no tiene
    archivos y por lo tanto no tiene depósito que consultar.
    """
    entrega = payload["entrega"]
    archivos = entrega.get("archivos") or []
    if all("contenido" in archivo for archivo in archivos):
        return entrega
    return rehidratar(entrega, absoluta_desde(payload["deposito"], base))
