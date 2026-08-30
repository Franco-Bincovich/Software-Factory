"""La suite de las partes firmadas, corrida en cada paso — ADR-019 punto 4.

Cada parte deja un archivo de pruebas en el espacio. Cuando la parte N entrega,
se corren **todos** los archivos de prueba que dejaron las partes anteriores
sobre el espacio tal como quedaría con la entrega nueva adentro. Si alguno falla,
la parte N rompió algo que ya tenía firma.

## Por qué no lo hace QA

Porque no cuesta un token. QA es un modelo que lee, propone casos y los mide;
esto es correr archivos que ya existen y mirar el código de salida. Meterlo en QA
gastaría presupuesto por cada parte para volver a verificar lo que ya se aprobó, y
—peor— haría que la comprobación dependiera de que el modelo se acuerde de
hacerla. Acá es mecánico: o el archivo termina en 0 o no.

## Por qué falla ruidosamente y no como un aviso

Un incumplimiento de regresión entra en la misma lista que los del verificador
estructural y los de QA, con la misma forma `{regla, archivo, detalle}`. El
identificador es `REG-<parte>` y nombra **a quién le rompió el test**, no a quién
lo rompió: el Developer de la parte N ya sabe quién es, lo que no sabe es qué
tocó. El detalle trae el final del stderr por lo mismo.

## Por qué se corre sobre una copia

El depósito de una iteración es el registro de auditoría de ADR-017 y tiene un
SHA-256 fijado por archivo. `ejecutor.ejecutar_archivo` le da al proceso permiso
de escritura sobre la raíz, así que un test que escribiera algo dejaría el hash
del evento mintiendo. Se copia una vez por tanda y se corre ahí.

**Una copia por tanda y no una por archivo**, a diferencia de
`verificacion_sustantiva`. Allá las expresiones las escribe un modelo y el control
existe porque un caso puede contaminar a otro; acá los archivos son los tests que
la propia Fábrica ya aprobó. Lo que se protege es el depósito, no la independencia
entre tests firmados.
"""

import os
import shutil
import tempfile

import ejecutor
import inspeccion_js as ins
import verificador_entrega

# Cuánto stderr entra en el detalle. Un stack de Node entero taparía la lista de
# incumplimientos que el Developer tiene que leer; las últimas líneas son las que
# dicen qué aserción falló.
LINEAS_DE_ERROR = 12


def _incumplimiento(regla, archivo, detalle):
    return {"regla": regla, "archivo": archivo, "detalle": detalle}


def _cola(texto):
    lineas = (texto or "").strip().splitlines()
    return "\n".join(lineas[-LINEAS_DE_ERROR:]) or "(sin salida de error)"


def archivos_de_prueba(inventario):
    """Los archivos de prueba que dejaron las partes anteriores, con su parte.

    Sale del inventario del espacio y no del disco: el inventario es lo que la
    plataforma firmó parte por parte, así que sabe de quién es cada test. Un
    barrido del directorio devolvería también los que trae la entrega en curso,
    que todavía no están aprobados y los verifica QA.
    """
    return [
        {"ruta": a["ruta"], "parte": a["parte"]}
        for a in inventario
        if ins.es_js(a["ruta"]) and verificador_entrega.es_prueba(a["ruta"])
    ]


def _una(copia, prueba, ejecutar_fn):
    regla = "REG-%s" % prueba["parte"]
    try:
        resultado = ejecutar_fn(copia, prueba["ruta"])
    except ejecutor.EntradaRechazada as rechazo:
        return [
            _incumplimiento(
                regla,
                prueba["ruta"],
                "el ejecutor rechazó el espacio de trabajo y no se pudo correr la "
                "suite de la parte %s: %s" % (prueba["parte"], rechazo),
            )
        ]
    if resultado.cortado_por_tiempo:
        return [
            _incumplimiento(
                regla,
                prueba["ruta"],
                "La suite de pruebas de la parte %s no terminó en %s segundos. "
                "Algo de esta entrega la dejó colgada."
                % (prueba["parte"], resultado.segundos),
            )
        ]
    if resultado.codigo != 0:
        return [
            _incumplimiento(
                regla,
                prueba["ruta"],
                "La suite de pruebas de la parte %s, que estaba aprobada, falla con "
                "esta entrega (código %s). Lo aprobado no se rompe: corregí lo tuyo, "
                "no lo suyo.\n%s"
                % (prueba["parte"], resultado.codigo, _cola(resultado.error)),
            )
        ]
    return []


def correr(deposito, pruebas, ejecutar_fn=None):
    """Corre la suite de las partes firmadas y devuelve sus incumplimientos.

    `deposito` es el directorio donde ya está materializado el espacio con la
    entrega nueva adentro —el que arma `deposito.depositar` con su `base`—, así
    que lo que se mide es el efecto de esta parte sobre lo anterior.

    Sin pruebas firmadas no hay nada que correr y no se copia nada: es el caso de
    la primera parte de una cadena.
    """
    if not pruebas:
        return []
    ejecutar_fn = ejecutor.ejecutar_archivo if ejecutar_fn is None else ejecutar_fn
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        copia = os.path.join(tmp, "espacio")
        shutil.copytree(deposito, copia)
        for prueba in pruebas:
            fallos += _una(copia, prueba, ejecutar_fn)
    return fallos


__all__ = ["archivos_de_prueba", "correr"]
