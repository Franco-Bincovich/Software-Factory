"""Criterio de aceptación de la verificación sustantiva — ADR-018.

**Los dos tests que sostienen el diseño son `TestSuperficieDeRechazo` y
`TestControl4`.** Todo lo demás comprueba comportamiento; ésos comprueban los dos
invariantes:

- un incumplimiento sólo puede nombrar un criterio que el plan escribió para esta
  unidad —el límite contra rechazar de más—;
- un caso que pasa sin que su salida dependa del artefacto no cuenta como
  evidencia, y el criterio al que se colgaba escala en vez de darse por cumplido
  —el límite contra aceptar de más—.

El primero corre contra salidas fabricadas y hostiles a propósito, no contra lo
que produzca el modelo, porque la garantía tiene que valer para cualquier salida,
incluida la que a nadie se le ocurrió pedirle a un modelo.

No se ejecuta Node en este archivo. El ejecutor se inyecta, que es para lo que
`verificar` recibe `ejecutar_fn`: lo que se prueba acá es el anclaje, la
comparación y la emisión del veredicto, no la frontera —eso ya está en
`test_ejecutor`—. El Control 4 con Node de verdad está en
`test_qa_contra_defectos`.

## Por qué el ejecutor de mentira mira el depósito

Desde el Control 4 el depósito dejó de ser un parámetro decorativo: `verificar`
lo copia por cada ejecución y le planta el centinela para ver si la salida
cambia. Un doble que devolviera siempre lo mismo sin mirar el directorio
simularía **exactamente el caso vacuo**, y todos los tests de acá caerían en
`sin_evidencia`.

Así que el doble lee el depósito que recibe y devuelve el centinela cuando lo
encuentra. Eso convierte a la propia bandera del doble en lo que está bajo
prueba: `Ejecutor(mira_el_artefacto=True)` es un caso que comprueba el
entregable, y `False` es uno que finge. No hay que fabricar nada más.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import ejecutor  # noqa: E402
import verificacion_sustantiva as vs  # noqa: E402

#: El entregable de mentira. Existe en el depósito para que los casos puedan
#: nombrarlo en `archivo`, que desde el Control 1 es obligatorio.
ENTREGABLE = "logica.js"


def criterio(condicion, esperado="", procedimiento=""):
    return {
        "condicion_observable": condicion,
        "resultado_esperado": esperado,
        "procedimiento": procedimiento,
    }


def unidad_de(*condiciones, uid="U1"):
    return {"id": uid, "criterios": [criterio(c) for c in condiciones]}


UNIDAD = unidad_de("suma dos números", "resta dos números")


def centinela_plantado_en(deposito):
    """El centinela que `verificar` dejó en el depósito, o `None`.

    Se busca por la marca y no por el valor porque el valor se sortea por tanda
    —justamente para que no pueda coincidir con ningún `espera`—, así que el
    doble no puede conocerlo de antemano.
    """
    for raiz, _, archivos in os.walk(deposito):
        for nombre in archivos:
            try:
                texto = Path(raiz, nombre).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if vs.MARCA_CENTINELA in texto:
                desde = texto.index(vs.MARCA_CENTINELA)
                return texto[desde : desde + len(vs.MARCA_CENTINELA) + 32]
    return None


def resultado(salida):
    return ejecutor.Resultado(
        salida=salida, error="", codigo=0, cortado_por_tiempo=False,
        frontera="ninguna", segundos=0.0,
    )


class Ejecutor:
    """Un ejecutor de mentira que devuelve lo que se le dijo y anota a quién corrió.

    Anotar las expresiones es lo que permite afirmar que un caso descartado
    **no se ejecutó**, en vez de afirmar solamente que no aparece en la tabla.
    Un caso podado tarde igual habría gastado la frontera.

    `mira_el_artefacto` es la diferencia entre un caso que comprueba la entrega y
    uno vacuo: ver el encabezado del archivo.
    """

    def __init__(self, salidas=None, por_defecto="ok", mira_el_artefacto=True):
        self.salidas = salidas or {}
        self.por_defecto = por_defecto
        self.mira_el_artefacto = mira_el_artefacto
        self.corridas = []
        self.depositos = []

    def __call__(self, deposito, expresion):
        self.corridas.append(expresion)
        self.depositos.append(deposito)
        if self.mira_el_artefacto:
            centinela = centinela_plantado_en(deposito)
            if centinela is not None:
                return resultado(centinela)
        salida = self.salidas.get(expresion, self.por_defecto)
        if isinstance(salida, BaseException):
            raise salida
        return resultado(salida)


def caso(indice, expresion, espera, **extra):
    base = {
        "criterio": indice,
        "expresion": expresion,
        "espera": espera,
        "archivo": ENTREGABLE,
    }
    base.update(extra)
    return base


class ConDeposito(unittest.TestCase):
    """Un depósito de verdad en disco.

    Desde la copia limpia por ejecución no alcanza con una ruta inventada: el
    módulo copia el directorio y le escribe adentro. Un test contra `/depo` ya no
    estaría probando lo mismo que corre en producción.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.deposito = os.path.join(tmp.name, "deposito")
        os.makedirs(os.path.join(self.deposito, "src"))
        Path(self.deposito, ENTREGABLE).write_text(
            "module.exports = {};\n", encoding="utf-8"
        )
        Path(self.deposito, "src", "otro.js").write_text(
            "module.exports = {};\n", encoding="utf-8"
        )

    def verificar(self, unidad, casos, falso=None):
        return vs.verificar(unidad, casos, self.deposito, falso or Ejecutor())


# --- Control 1 — el anclaje -------------------------------------------------


class TestAnclaje(ConDeposito):
    """El anclaje poda antes de ejecutar, y dice por qué podó."""

    def test_un_caso_sin_criterio_no_se_ejecuta(self):
        falso = Ejecutor()
        salida = self.verificar(
            UNIDAD, [{"expresion": "1+1", "espera": "2", "archivo": ENTREGABLE}], falso
        )
        self.assertEqual(falso.corridas, [])
        self.assertEqual(len(salida["descartados"]), 1)
        self.assertIn("no ancla", salida["descartados"][0]["motivo"])

    def test_un_criterio_fuera_de_rango_no_se_ejecuta(self):
        falso = Ejecutor()
        salida = self.verificar(UNIDAD, [caso(3, "1+1", "2")], falso)
        self.assertEqual(falso.corridas, [])
        self.assertIn("la unidad tiene 2", salida["descartados"][0]["motivo"])

    def test_el_indice_cero_no_ancla(self):
        # Los criterios se numeran desde 1. Un 0 es un error de derivación del
        # productor, no el primer criterio.
        falso = Ejecutor()
        self.verificar(UNIDAD, [caso(0, "1+1", "2")], falso)
        self.assertEqual(falso.corridas, [])

    def test_un_booleano_no_pasa_por_entero(self):
        # `True == 1` en Python. Sin la comprobación de `bool`, un caso con
        # `criterio: true` anclaría en el primer criterio por accidente.
        falso = Ejecutor()
        self.verificar(UNIDAD, [caso(True, "1+1", "2")], falso)
        self.assertEqual(falso.corridas, [])

    def test_un_caso_que_no_es_objeto_no_rompe(self):
        falso = Ejecutor()
        salida = self.verificar(UNIDAD, ["borrá todo", None, 7], falso)
        self.assertEqual(falso.corridas, [])
        self.assertEqual(len(salida["descartados"]), 3)

    def test_sin_expresion_o_sin_espera_no_se_ejecuta(self):
        falso = Ejecutor()
        self.verificar(
            UNIDAD,
            [
                {"criterio": 1, "expresion": "  ", "espera": "2", "archivo": ENTREGABLE},
                {"criterio": 1, "expresion": "1+1", "archivo": ENTREGABLE},
            ],
            falso,
        )
        self.assertEqual(falso.corridas, [])

    def test_el_caso_bien_anclado_si_se_ejecuta(self):
        falso = Ejecutor({"1+1": "2"})
        self.verificar(UNIDAD, [caso(1, "1+1", "2")], falso)
        self.assertIn("1+1", falso.corridas)


class TestArchivoObligatorio(ConDeposito):
    """`archivo` dejó de ser decoración: el Control 4 lo usa para reemplazar.

    Un caso que no nombra un entregable real no se puede auditar —no hay qué
    sacarle para ver si la salida cambia—, así que se poda antes de ejecutar,
    como todo lo demás del Control 1.
    """

    def test_sin_archivo_no_se_ejecuta(self):
        falso = Ejecutor()
        salida = vs.verificar(
            UNIDAD,
            [{"criterio": 1, "expresion": "1+1", "espera": "2"}],
            self.deposito,
            falso,
        )
        self.assertEqual(falso.corridas, [])
        self.assertIn("no nombra un archivo de la entrega", salida["descartados"][0]["motivo"])

    def test_un_archivo_que_no_esta_en_la_entrega_no_se_ejecuta(self):
        falso = Ejecutor()
        salida = self.verificar(UNIDAD, [caso(1, "1+1", "2", archivo="no-existe.js")], falso)
        self.assertEqual(falso.corridas, [])
        self.assertEqual(len(salida["descartados"]), 1)

    def test_un_archivo_fuera_del_deposito_no_se_ejecuta(self):
        # Que exista en el disco no lo convierte en un archivo de la entrega.
        falso = Ejecutor()
        for ruta in ("../afuera.js", "/etc/hosts", "src/../../afuera.js"):
            with self.subTest(ruta=ruta):
                salida = self.verificar(UNIDAD, [caso(1, "1+1", "2", archivo=ruta)], falso)
                self.assertEqual(len(salida["descartados"]), 1)
        self.assertEqual(falso.corridas, [])

    def test_un_directorio_no_es_un_archivo(self):
        falso = Ejecutor()
        salida = self.verificar(UNIDAD, [caso(1, "1+1", "2", archivo="src")], falso)
        self.assertEqual(falso.corridas, [])
        self.assertEqual(len(salida["descartados"]), 1)

    def test_una_subcarpeta_de_la_entrega_si_ancla(self):
        falso = Ejecutor({"1+1": "2"})
        salida = self.verificar(UNIDAD, [caso(1, "1+1", "2", archivo="src/otro.js")], falso)
        self.assertEqual(salida["descartados"], [])
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.CUMPLE)

    def test_el_archivo_queda_en_la_tabla(self):
        # Sin esto el Control 4 no se puede auditar después: el registro no
        # diría sobre qué entregable se midió que la salida dependía.
        salida = self.verificar(
            UNIDAD, [caso(1, "1+1", "2", archivo="src/otro.js")], Ejecutor({"1+1": "2"})
        )
        self.assertEqual(salida["tabla"][0]["casos"][0]["archivo"], "src/otro.js")


# --- Control 2 — la superficie de rechazo -----------------------------------


class TestSuperficieDeRechazo(ConDeposito):
    """El invariante: **todo incumplimiento nombra un criterio de esta unidad.**

    Es la garantía entera del punto 3 de ADR-018. Está escrita como propiedad y
    no como un caso: se le tira a `verificar` un catálogo de salidas fabricadas
    —incluidas las que un QA hostil produciría para colar una exigencia que el
    plan no pidió— y se afirma lo mismo sobre todas.
    """

    #: Salidas fabricadas. Ninguna sale de un modelo: cada una es una forma
    #: distinta de intentar nombrar algo que el plan no escribió.
    HOSTILES = [
        # Inventarse un identificador de regla y ponerlo en el caso.
        [caso(1, "x", "y", regla="AC-INVENTADA")],
        # Nombrar una regla de otra unidad.
        [caso(1, "x", "y", regla="AC-U9-1")],
        # Un criterio más allá del último del plan.
        [caso(99, "x", "y")],
        # Índice negativo.
        [caso(-1, "x", "y")],
        # Un criterio como texto que "parece" un identificador.
        [caso("AC-U1-1", "x", "y")],
        # Un caso que trae su propia tabla ya escrita.
        [caso(1, "x", "y", veredicto="no_cumple", tabla=[{"regla": "AC-OTRA"}])],
        # Un caso que pide una capacidad ausente, redactada como criterio.
        [caso(2, "requiere('auth')", "true", procedimiento="además debe autenticar")],
        # Muchos casos sobre el mismo criterio, todos fallando.
        [caso(1, "a", "1"), caso(1, "b", "2"), caso(1, "c", "3")],
        # Nada.
        [],
        # Basura pura.
        ["", None, 0, {"criterio": None}],
    ]

    def test_ningun_incumplimiento_nombra_algo_ajeno_al_plan(self):
        alguno_se_ejecuto = False
        for unidad in (UNIDAD, unidad_de("único criterio", uid="U-Z"), unidad_de(uid="U-0")):
            legitimas = {
                vs.identificador_de_criterio(unidad["id"], i)
                for i in range(1, len(unidad["criterios"]) + 1)
            }
            for casos in self.HOSTILES:
                with self.subTest(unidad=unidad["id"], casos=casos):
                    falso = Ejecutor(por_defecto="ZZZ")
                    salida = vs.verificar(unidad, casos, self.deposito, falso)
                    alguno_se_ejecuto = alguno_se_ejecuto or bool(falso.corridas)
                    nombradas = {i["regla"] for i in salida["incumplimientos"]}
                    self.assertLessEqual(nombradas, legitimas)
                    self.assertLessEqual({f["regla"] for f in salida["tabla"]}, legitimas)
        # Sin esto la propiedad se cumpliría de taquito con un Control 1 que
        # podara todo: dos conjuntos vacíos también están contenidos.
        self.assertTrue(alguno_se_ejecuto)

    def test_una_unidad_sin_criterios_no_puede_ser_rechazada(self):
        """El caso límite del invariante, y el que más importa.

        Sin criterios no hay superficie de rechazo, así que ningún caso —por
        muchos que QA fabrique— puede producir un incumplimiento.
        """
        vacia = unidad_de(uid="U-0")
        for casos in self.HOSTILES:
            salida = vs.verificar(vacia, casos, self.deposito, Ejecutor(por_defecto="ZZZ"))
            self.assertEqual(salida["incumplimientos"], [])
            self.assertEqual(salida["tabla"], [])

    def test_la_tabla_tiene_una_fila_por_criterio_ni_una_mas(self):
        """Corolario estructural: la tabla es del plan, no de los casos.

        Diez casos sobre un criterio siguen siendo una fila. Si la tabla
        creciera con los casos, el bucle estaría invertido.
        """
        salida = self.verificar(
            UNIDAD,
            [caso(1, "e%d" % n, "1") for n in range(10)],
            Ejecutor(por_defecto="1"),
        )
        self.assertEqual(len(salida["tabla"]), len(UNIDAD["criterios"]))
        self.assertEqual(
            [f["regla"] for f in salida["tabla"]], ["AC-U1-1", "AC-U1-2"]
        )

    def test_un_criterio_fallado_produce_un_solo_incumplimiento(self):
        salida = self.verificar(
            UNIDAD,
            [caso(1, "a", "1"), caso(1, "b", "1"), caso(1, "c", "1")],
            Ejecutor(por_defecto="ZZZ"),
        )
        self.assertEqual([i["regla"] for i in salida["incumplimientos"]], ["AC-U1-1"])


# --- Control 4 — la evidencia tiene que depender del artefacto --------------


class TestControl4(ConDeposito):
    """**El invariante contra aceptar de más.**

    Un caso que emite `cumple` sin que su salida dependa del artefacto no cuenta
    como evidencia, y el criterio al que se colgaba escala en vez de darse por
    cumplido. Una aceptación falsa se firma en el Gate; un rechazo injusto al
    menos se descubre en el bucle.
    """

    def test_un_caso_vacuo_no_da_por_cumplido_el_criterio(self):
        # El doble no mira el depósito: devuelve lo mismo con el entregable o
        # con el centinela. Es exactamente `console.log('false')`.
        salida = self.verificar(
            UNIDAD, [caso(1, "console.log('2')", "2")],
            Ejecutor({"console.log('2')": "2"}, mira_el_artefacto=False),
        )
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.NO_VERIFICABLE)
        self.assertEqual(salida["no_verificables"], ["AC-U1-1", "AC-U1-2"])

    def test_un_caso_vacuo_no_se_convierte_en_incumplimiento(self):
        """No se le imputa al Developer un defecto de QA.

        Contarlo como `no_cumple` sería fabricar el rechazo injusto para tapar
        la aceptación falsa: cambiar un problema por el otro.
        """
        salida = self.verificar(
            UNIDAD, [caso(1, "e", "2")],
            Ejecutor({"e": "2"}, mira_el_artefacto=False),
        )
        self.assertEqual(salida["incumplimientos"], [])
        self.assertNotEqual(salida["tabla"][0]["veredicto"], vs.NO_CUMPLE)

    def test_el_caso_vacuo_queda_registrado_con_su_motivo(self):
        salida = self.verificar(
            UNIDAD, [caso(1, "e", "2")],
            Ejecutor({"e": "2"}, mira_el_artefacto=False),
        )
        self.assertEqual(len(salida["sin_evidencia"]), 1)
        self.assertEqual(salida["sin_evidencia"][0]["motivo"], vs.NO_DEPENDE)
        self.assertIn(ENTREGABLE, salida["sin_evidencia"][0]["detalle"])

    def test_un_caso_que_si_depende_del_artefacto_cuenta(self):
        """El control negativo. Sin esto, un Control 4 que descarta todo pasaría."""
        salida = self.verificar(
            UNIDAD, [caso(1, "e", "2")], Ejecutor({"e": "2"}, mira_el_artefacto=True)
        )
        self.assertEqual(salida["sin_evidencia"], [])
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.CUMPLE)

    def test_el_centinela_no_se_le_planta_al_caso_que_ya_fallo(self):
        """Sólo los verdes se miden: el rojo deja `no_cumple` sea vacuo o no.

        Es la mitad del costo del control, así que conviene que esté afirmado y
        no sólo escrito en un comentario.
        """
        falso = Ejecutor({"e": "otra cosa"})
        self.verificar(UNIDAD, [caso(1, "e", "2")], falso)
        self.assertEqual(len(falso.corridas), 2)

    def test_el_caso_verde_se_corre_tres_veces(self):
        falso = Ejecutor({"e": "2"})
        self.verificar(UNIDAD, [caso(1, "e", "2")], falso)
        self.assertEqual(len(falso.corridas), 3)

    def test_un_caso_no_determinista_no_es_evidencia(self):
        class Azaroso(Ejecutor):
            def __call__(self, deposito, expresion):
                self.corridas.append(expresion)
                return resultado("2" if len(self.corridas) % 2 else "3")

        salida = self.verificar(UNIDAD, [caso(1, "e", "2")], Azaroso())
        self.assertEqual(salida["sin_evidencia"][0]["motivo"], vs.NO_DETERMINISTA)
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.NO_VERIFICABLE)
        self.assertEqual(salida["incumplimientos"], [])

    def test_cada_ejecucion_ve_una_copia_limpia(self):
        """Un caso no puede hacer pasar a otro dejándole un archivo.

        El ejecutor le da permiso de escritura sobre la raíz del depósito.
        Repetir la tanda en el mismo orden no lo detectaría —la contaminación se
        reproduce igual—, así que lo que se afirma acá es que el segundo caso
        **no ve** lo que dejó el primero.
        """

        class Escribe(Ejecutor):
            def __call__(self, deposito, expresion):
                self.corridas.append(expresion)
                rastro = Path(deposito, "rastro.txt")
                if expresion == "dejar":
                    rastro.write_text("x", encoding="utf-8")
                    return resultado("1")
                return resultado("1" if rastro.exists() else "0")

        salida = self.verificar(
            UNIDAD, [caso(1, "dejar", "1"), caso(2, "leer", "1")], Escribe()
        )
        self.assertEqual(salida["tabla"][1]["casos"][0]["obtenido"], "0")
        self.assertEqual(salida["tabla"][1]["veredicto"], vs.NO_CUMPLE)

    def test_el_deposito_real_no_se_toca(self):
        antes = {
            p.relative_to(self.deposito).as_posix(): p.read_text(encoding="utf-8")
            for p in Path(self.deposito).rglob("*")
            if p.is_file()
        }
        self.verificar(UNIDAD, [caso(1, "e", "2")], Ejecutor({"e": "2"}))
        despues = {
            p.relative_to(self.deposito).as_posix(): p.read_text(encoding="utf-8")
            for p in Path(self.deposito).rglob("*")
            if p.is_file()
        }
        self.assertEqual(antes, despues)

    def test_el_centinela_es_irrepetible(self):
        # Si pudiera coincidir con el `espera` de un caso, un caso legítimo
        # sobreviviría al reemplazo y lo declararíamos vacuo siendo real.
        sorteados = {vs.centinela_nuevo() for _ in range(200)}
        self.assertEqual(len(sorteados), 200)
        self.assertTrue(all(c.startswith(vs.MARCA_CENTINELA) for c in sorteados))

    def test_el_modulo_centinela_se_deja_usar(self):
        # No es un `throw`: tiene que dejar correr la expresión entera para
        # delatar también al caso que carga el archivo y no lo usa.
        codigo = vs.modulo_centinela("XX")
        self.assertIn("Proxy", codigo)
        self.assertNotIn("throw", codigo)

    def test_los_descartados_y_los_sin_evidencia_no_se_mezclan(self):
        """Dos fallas distintas del productor, dos claves.

        "QA no derivó un caso" y "QA derivó un caso que no comprobaba nada" se
        cuentan aparte, o la métrica del punto 5 de ADR-018 deja de decir cuál
        de las dos pasó.
        """
        salida = self.verificar(
            UNIDAD,
            [caso(1, "e", "2"), caso(2, "f", "9", archivo="no-existe.js")],
            Ejecutor({"e": "2"}, mira_el_artefacto=False),
        )
        self.assertEqual(len(salida["descartados"]), 1)
        self.assertEqual(len(salida["sin_evidencia"]), 1)
        self.assertNotIn("motivo", salida["sin_evidencia"][0]["caso"])


# --- el veredicto -----------------------------------------------------------


class TestVeredicto(ConDeposito):
    def test_la_forma_del_incumplimiento_es_la_del_verificador_de_entrega(self):
        salida = self.verificar(
            UNIDAD, [caso(1, "sumar(1,1)", "2")], Ejecutor(por_defecto="3")
        )
        incumplimiento = salida["incumplimientos"][0]
        self.assertEqual(set(incumplimiento), {"regla", "archivo", "detalle"})
        self.assertEqual(incumplimiento["archivo"], ENTREGABLE)
        self.assertIn("sumar(1,1)", incumplimiento["detalle"])

    def test_cumple_cuando_la_salida_coincide(self):
        salida = self.verificar(
            UNIDAD, [caso(1, "sumar(1,1)", "2")], Ejecutor({"sumar(1,1)": "2"})
        )
        self.assertEqual(salida["incumplimientos"], [])
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.CUMPLE)

    def test_la_comparacion_ignora_espacios_a_los_costados_y_nada_mas(self):
        coincide = self.verificar(UNIDAD, [caso(1, "e", "2")], Ejecutor({"e": "  2\n"}))
        self.assertEqual(coincide["tabla"][0]["veredicto"], vs.CUMPLE)

        parcial = self.verificar(UNIDAD, [caso(1, "e", "2")], Ejecutor({"e": "22"}))
        self.assertEqual(parcial["tabla"][0]["veredicto"], vs.NO_CUMPLE)

    def test_no_hay_porcentajes_en_ninguna_fila(self):
        # Punto 4 de ADR-018: el veredicto es binario. Una fila sólo puede decir
        # una de tres cosas.
        salida = self.verificar(
            UNIDAD, [caso(1, "a", "1"), caso(2, "b", "9")],
            Ejecutor({"a": "1", "b": "0"}),
        )
        for fila in salida["tabla"]:
            self.assertIn(fila["veredicto"], (vs.CUMPLE, vs.NO_CUMPLE, vs.NO_VERIFICABLE))

    def test_el_corte_por_tiempo_no_cumple(self):
        class Lento(Ejecutor):
            def __call__(self, deposito, expresion):
                self.corridas.append(expresion)
                return ejecutor.Resultado(
                    salida="2", error="", codigo=0, cortado_por_tiempo=True,
                    frontera="ninguna", segundos=10.0,
                )

        salida = self.verificar(UNIDAD, [caso(1, "e", "2")], Lento())
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.NO_CUMPLE)
        self.assertIn("cortado por tiempo", salida["tabla"][0]["casos"][0]["obtenido"])

    def test_un_deposito_rechazado_no_cumple_pero_no_escala(self):
        # V5 rechaza algo del depósito: es del entregable, no de la máquina.
        falso = Ejecutor({"e": ejecutor.EntradaRechazada("hay un require")})
        salida = self.verificar(UNIDAD, [caso(1, "e", "2")], falso)
        self.assertEqual(salida["tabla"][0]["veredicto"], vs.NO_CUMPLE)
        self.assertIn("rechazó el depósito", salida["tabla"][0]["casos"][0]["obtenido"])

    def test_sin_frontera_sube(self):
        # Que la máquina no pueda verificar no es un incumplimiento del
        # entregable: no se atrapa acá.
        falso = Ejecutor({"e": ejecutor.SinFrontera("no hay sandbox")})
        with self.assertRaises(ejecutor.SinFrontera):
            self.verificar(UNIDAD, [caso(1, "e", "2")], falso)


# --- la métrica del punto 5 -------------------------------------------------


class TestNoVerificables(ConDeposito):
    def test_un_criterio_sin_caso_anclado_se_declara_no_verificable(self):
        salida = self.verificar(UNIDAD, [caso(1, "a", "1")], Ejecutor({"a": "1"}))
        self.assertEqual(salida["no_verificables"], ["AC-U1-2"])
        self.assertEqual(salida["tabla"][1]["veredicto"], vs.NO_VERIFICABLE)

    def test_no_verificable_no_es_incumplimiento(self):
        """No se juzga: se declara y escala al Gate. Punto 5 de ADR-018."""
        salida = self.verificar(UNIDAD, [], Ejecutor())
        self.assertEqual(salida["incumplimientos"], [])
        self.assertEqual(len(salida["no_verificables"]), 2)

    def test_un_caso_descartado_deja_su_criterio_no_verificable(self):
        # El corolario del anclaje: podar el caso es lo que produce la métrica.
        salida = self.verificar(
            UNIDAD,
            [caso(1, "a", "1"), {"criterio": 2, "expresion": "b", "archivo": ENTREGABLE}],
            Ejecutor({"a": "1"}),
        )
        self.assertEqual(salida["no_verificables"], ["AC-U1-2"])

    def test_todo_verificado_da_cero(self):
        salida = self.verificar(
            UNIDAD, [caso(1, "a", "1"), caso(2, "b", "2")],
            Ejecutor({"a": "1", "b": "2"}),
        )
        self.assertEqual(salida["no_verificables"], [])


if __name__ == "__main__":
    unittest.main()
