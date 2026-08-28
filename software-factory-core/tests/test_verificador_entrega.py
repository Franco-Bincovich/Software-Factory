"""Criterio de aceptación del verificador de Entregas.

Un test por regla. Cada uno siembra su defecto sobre la entrega limpia y
comprueba que se dispara exactamente esa regla y ninguna otra. La entrega limpia
no reporta nada: un falso positivo sobre ella invalida el verificador igual que
un falso negativo.

**Los defectos se siembran mutando la fixture limpia, no con un archivo por
defecto.** Es una desviación deliberada del patrón de `test_verificador.py`: una
entrega lleva el contenido completo de cuatro archivos, y veinte copias casi
idénticas divergen sin que nadie lo note. Acá la mutación queda a dos líneas de
su assert.
"""

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import inspeccion_js  # noqa: E402
from verificador_entrega import verificar  # noqa: E402

FIXTURES = RAIZ / "fixtures"
ENTREGA_LIMPIA = json.loads((FIXTURES / "entrega-ok.json").read_text(encoding="utf-8"))
PLAN_LIMPIO = json.loads((FIXTURES / "plan-entrega.json").read_text(encoding="utf-8"))


def entrega():
    return copy.deepcopy(ENTREGA_LIMPIA)


def plan():
    return copy.deepcopy(PLAN_LIMPIO)


def archivo(entrega_, ruta):
    return next(a for a in entrega_["archivos"] if a["ruta"] == ruta)


def quitar(entrega_, ruta):
    entrega_["archivos"] = [a for a in entrega_["archivos"] if a["ruta"] != ruta]


def reglas(resultado):
    return {i["regla"] for i in resultado["incumplimientos"]}


class EntregaLimpia(unittest.TestCase):
    def test_no_reporta_nada(self):
        r = verificar(entrega(), plan())
        self.assertEqual(r["incumplimientos"], [], "falso positivo sobre la entrega limpia")
        self.assertTrue(r["valido"])


class DefectoSembrado(unittest.TestCase):
    def _comprobar(self, entrega_, plan_, regla_esperada):
        r = verificar(entrega_, plan_)
        self.assertFalse(r["valido"])
        self.assertEqual(
            reglas(r), {regla_esperada}, "debía disparar solo %s" % regla_esperada
        )
        return r

    # --- Contrato de Entrega ---

    def test_c0_campo_que_el_contrato_no_admite(self):
        e = entrega()
        e["notas"] = "un comentario al margen"
        r = self._comprobar(e, plan(), "C0")
        self.assertIn("notas", r["incumplimientos"][0]["detalle"])

    def test_c1_unidad_que_no_existe_en_el_plan(self):
        e = entrega()
        e["unidad"] = "U9"
        r = self._comprobar(e, plan(), "C1")
        self.assertIn("U9", r["incumplimientos"][0]["detalle"])

    def test_c2_ruta_absoluta_y_ruta_con_dos_puntos(self):
        e = entrega()
        for ruta in ("/etc/algo.js", "../afuera/otro.js"):
            e["archivos"].append(
                {"ruta": ruta, "rol": "auxiliar", "motivo": "hace falta", "contenido": "const a = 1;\n"}
            )
        r = self._comprobar(e, plan(), "C2")
        self.assertEqual({i["archivo"] for i in r["incumplimientos"]}, {"/etc/algo.js", "../afuera/otro.js"})

    def test_c3_marcador_de_fragmento(self):
        e = entrega()
        archivo(e, "demo.html")["contenido"] += "\n<!-- resto igual -->\n"
        r = self._comprobar(e, plan(), "C3")
        self.assertEqual(r["incumplimientos"][0]["archivo"], "demo.html")

    def test_c4_falta_el_artefacto_esperado(self):
        p = plan()
        p["unidades"][0]["artefacto_esperado"] = "src/validar-email.js y sus pruebas"
        r = self._comprobar(entrega(), p, "C4")
        self.assertIn("src/validar-email.js", r["incumplimientos"][0]["detalle"])

    def test_c5_archivo_que_nadie_pidio(self):
        e = entrega()
        e["archivos"].append(
            {"ruta": "notas.txt", "rol": "artefacto_esperado", "contenido": "apuntes\n"}
        )
        r = self._comprobar(e, plan(), "C5")
        self.assertEqual(r["incumplimientos"][0]["archivo"], "notas.txt")

    def test_c5_auxiliar_sin_motivo(self):
        e = entrega()
        e["archivos"].append(
            {"ruta": "datos.txt", "rol": "auxiliar", "contenido": "4471\n"}
        )
        r = self._comprobar(e, plan(), "C5")
        self.assertIn("no dice por qué", r["incumplimientos"][0]["detalle"])

    def test_c6_falta_un_entregable(self):
        e = entrega()
        quitar(e, "tests/validar-legajo.test.js")
        r = self._comprobar(e, plan(), "C6")
        self.assertIn("archivo de pruebas", r["incumplimientos"][0]["detalle"])

    def test_c6_y_c4_son_independientes(self):
        """Quitar demo.html rompe dos reglas distintas, y las dos se reportan.

        La unidad lo nombra en su artefacto esperado, así que falta el entregable
        (C6) y falta el artefacto que el plan pidió (C4). Son dos cosas.
        """
        e = entrega()
        quitar(e, "demo.html")
        r = verificar(e, plan())
        self.assertEqual(reglas(r), {"C4", "C6"})

    def test_c6_entrega_vacia_pide_escalamiento_y_no_reintento(self):
        e = entrega()
        e["archivos"] = []
        e["supuestos"] = ["La unidad se contradice con U2: pide validar y no validar el mismo campo."]
        r = verificar(e, plan())
        self.assertEqual(reglas(r), {"C6"})
        self.assertIn("escalamiento", r["incumplimientos"][0]["detalle"])

    def test_c6_entregable_vacio(self):
        """Vaciar el archivo de pruebas incumple C6 y, con razón, también R8."""
        e = entrega()
        archivo(e, "tests/validar-legajo.test.js")["contenido"] = "   \n"
        r = verificar(e, plan())
        self.assertIn("C6", reglas(r))
        self.assertEqual(reglas(r), {"C6", "R8"})

    def test_c7_el_html_no_carga_la_logica(self):
        e = entrega()
        demo = archivo(e, "demo.html")
        demo["contenido"] = demo["contenido"].replace(
            '<script src="./src/validar-legajo.js"></script>', ""
        )
        r = self._comprobar(e, plan(), "C7")
        self.assertIn("<script src>", r["incumplimientos"][0]["detalle"])

    def test_c7_el_html_reimplementa_la_logica(self):
        e = entrega()
        demo = archivo(e, "demo.html")
        demo["contenido"] = demo["contenido"].replace(
            "<script>\n  document.getElementById",
            "<script>\n  function validarLegajo(v) { return { valido: true, motivo: null }; }\n"
            "  document.getElementById",
        )
        r = self._comprobar(e, plan(), "C7")
        self.assertIn("Reimplementa", r["incumplimientos"][0]["detalle"])

    def test_c8_dos_archivos_con_la_misma_ruta(self):
        e = entrega()
        e["archivos"].append(copy.deepcopy(archivo(e, "demo.html")))
        r = self._comprobar(e, plan(), "C8")
        self.assertEqual(r["incumplimientos"][0]["archivo"], "demo.html")

    # --- Ruleset mecánico ---

    def test_r1_archivo_mas_largo_que_el_limite(self):
        e = entrega()
        logica = archivo(e, "src/validar-legajo.js")
        logica["contenido"] += "".join("// relleno %d\n" % n for n in range(220))
        r = self._comprobar(e, plan(), "R1")
        self.assertIn("el límite es 200", r["incumplimientos"][0]["detalle"])

    def test_r3_console_log_y_secreto_literal(self):
        e = entrega()
        logica = archivo(e, "src/validar-legajo.js")
        logica["contenido"] += '\nconsole.log("depurando");\nconst api_key = "abcdefgh12345678";\n'
        r = self._comprobar(e, plan(), "R3")
        self.assertEqual(len(r["incumplimientos"]), 2)

    def test_r8_las_pruebas_no_ejercitan_la_logica(self):
        e = entrega()
        archivo(e, "tests/validar-legajo.test.js")["contenido"] = "const nada = 1;\n"
        r = self._comprobar(e, plan(), "R8")
        self.assertIn("validarLegajo", r["incumplimientos"][0]["detalle"])

    # --- Prohibiciones del contrato ---

    def test_p1_abre_la_red(self):
        e = entrega()
        archivo(e, "src/validar-legajo.js")["contenido"] += '\nfetch("https://ejemplo.test/x");\n'
        r = self._comprobar(e, plan(), "P1")
        self.assertIn("fetch(", r["incumplimientos"][0]["detalle"])

    def test_p2_lee_variables_de_entorno(self):
        e = entrega()
        archivo(e, "src/validar-legajo.js")["contenido"] += "\nconst modo = process.env.MODO;\n"
        r = self._comprobar(e, plan(), "P2")
        self.assertIn("process.env", r["incumplimientos"][0]["detalle"])

    def test_p3_escribe_fuera_del_directorio(self):
        e = entrega()
        archivo(e, "src/validar-legajo.js")["contenido"] += '\nconst fs = require("node:fs");\n'
        r = self._comprobar(e, plan(), "P3")
        self.assertIn("fs", r["incumplimientos"][0]["detalle"])

    # --- Lo que no tiene número en ningún documento ---

    def test_v1_el_archivo_no_parsea(self):
        e = entrega()
        archivo(e, "src/validar-legajo.js")["contenido"] += "\nfunction roto( {\n"
        r = self._comprobar(e, plan(), "V1")
        self.assertIn("no parsea", r["incumplimientos"][0]["detalle"])

    def test_v2_un_nombre_del_criterio_no_esta_en_el_codigo(self):
        p = plan()
        p["unidades"][0]["criterios"][0]["resultado_esperado"] = "`calcularEdad` devuelve un número"
        r = self._comprobar(entrega(), p, "V2")
        self.assertIn("calcularEdad", r["incumplimientos"][0]["detalle"])

    def test_v3_pruebas_html_no_invoca_la_funcion(self):
        e = entrega()
        pruebas = archivo(e, "pruebas.html")
        pruebas["contenido"] = pruebas["contenido"].replace(
            "validarLegajo(caso.entrada)", "caso.entrada"
        )
        r = self._comprobar(e, plan(), "V3")
        self.assertIn("validarLegajo", r["incumplimientos"][0]["detalle"])

    def test_v4_veredicto_escrito_a_mano(self):
        e = entrega()
        pruebas = archivo(e, "pruebas.html")
        pruebas["contenido"] = pruebas["contenido"].replace(
            '<p id="resumen"></p>', '<p id="resumen"></p>\n<p>PASA</p>'
        ).replace(
            'fila.insertCell().textContent = paso ? "PASA" : "FALLA";',
            'fila.insertCell().textContent = "PASA";',
        )
        r = self._comprobar(e, plan(), "V4")
        self.assertEqual(len(r["incumplimientos"]), 2)
        self.assertTrue(any("HTML estático" in i["detalle"] for i in r["incumplimientos"]))

    def test_v5_manifiesto_de_dependencias(self):
        e = entrega()
        e["archivos"].append(
            {
                "ruta": "package.json",
                "rol": "auxiliar",
                "motivo": "declara las dependencias",
                "contenido": '{ "dependencies": { "lodash": "^4.17.21" } }\n',
            }
        )
        r = self._comprobar(e, plan(), "V5")
        self.assertEqual(r["incumplimientos"][0]["archivo"], "package.json")
        self.assertIn("instalar", r["incumplimientos"][0]["detalle"])

    def test_v5_dependencia_ya_instalada(self):
        e = entrega()
        e["archivos"].append(
            {
                "ruta": "node_modules/lodash/index.js",
                "rol": "auxiliar",
                "motivo": "la biblioteca",
                "contenido": "module.exports = {};\n",
            }
        )
        r = self._comprobar(e, plan(), "V5")
        self.assertEqual(r["incumplimientos"][0]["archivo"], "node_modules/lodash/index.js")

    def test_v5_require_de_un_paquete_externo(self):
        e = entrega()
        pruebas = archivo(e, "tests/validar-legajo.test.js")
        pruebas["contenido"] = 'const _ = require("lodash");\n' + pruebas["contenido"]
        r = self._comprobar(e, plan(), "V5")
        self.assertIn("lodash", r["incumplimientos"][0]["detalle"])
        self.assertIn("instalarlo", r["incumplimientos"][0]["detalle"])

    def test_v5_import_de_un_paquete_externo(self):
        e = entrega()
        logica = archivo(e, "src/validar-legajo.js")
        logica["contenido"] = 'import validator from "validator";\n' + logica["contenido"]
        r = self._comprobar(e, plan(), "V5")
        self.assertIn("validator", r["incumplimientos"][0]["detalle"])

    def test_v5_require_relativo_que_sale_del_directorio_de_la_unidad(self):
        """C2 no lo ve: mira las rutas declaradas, no las que el código resuelve.

        La ruta `tests/validar-legajo.test.js` es relativa y no tiene `..`, así
        que C2 la aprueba. El `require` de adentro sí se escapa.
        """
        e = entrega()
        pruebas = archivo(e, "tests/validar-legajo.test.js")
        pruebas["contenido"] = pruebas["contenido"].replace(
            '"../src/validar-legajo.js"', '"../../U1/src/validar-legajo.js"'
        )
        r = self._comprobar(e, plan(), "V5")
        self.assertIn("fuera del directorio de la unidad", r["incumplimientos"][0]["detalle"])

    def test_v5_require_de_una_ruta_absoluta(self):
        e = entrega()
        logica = archivo(e, "src/validar-legajo.js")
        logica["contenido"] += '\nconst otro = require("/opt/lib/otro.js");\n'
        r = self._comprobar(e, plan(), "V5")
        self.assertIn("ruta absoluta", r["incumplimientos"][0]["detalle"])

    def test_v5_script_src_a_un_cdn(self):
        """P1 conoce `fetch` y compañía, no un `src`: sin V5 esto se bajaba de la red."""
        e = entrega()
        demo = archivo(e, "demo.html")
        demo["contenido"] = demo["contenido"].replace(
            '<script src="./src/validar-legajo.js"></script>',
            '<script src="https://cdn.ejemplo.test/lib.js"></script>\n'
            '<script src="./src/validar-legajo.js"></script>',
        )
        r = self._comprobar(e, plan(), "V5")
        self.assertIn("se baja de la red", r["incumplimientos"][0]["detalle"])

    def test_v5_los_builtins_de_node_y_las_rutas_propias_pasan(self):
        """La entrega limpia ya usa `node:test`, `node:assert` y `../src/…`.

        Se afirma explícito porque es la mitad de la regla: V5 rechazando todo
        sería igual de inútil que V5 no existiendo.
        """
        e = entrega()
        logica = archivo(e, "src/validar-legajo.js")
        logica["contenido"] += '\nconst path = require("node:path");\n'
        logica["contenido"] += 'const { sep } = require("path");\n'
        logica["contenido"] += 'const fsp = require("fs/promises");\n'
        fallos = [
            i for i in verificar(e, plan())["incumplimientos"] if i["regla"] == "V5"
        ]
        self.assertEqual(fallos, [])


ENTREGA_DEPOSITADA = FIXTURES / "entrega-depositada"

# Los cuatro entregables tal como quedaron en el área de entregas, con su hash.
# El hash está acá para que se note si alguien los edita: dejarían de ser la
# evidencia que este test dice estar usando.
ENTREGABLES_DEPOSITADOS = {
    "src/u1.js": "337bda7982233dfd35ecbe3f82006981",
    "tests/u1.test.js": "b0446b133e317d139ee65b00c327502d",
    "pruebas.html": "2c3616861b01c30a582ce3a814504d17",
    "demo.html": "ffb87315d407ccc50c979fbe3c206f0f",
}


class TrabajoYaAprobado(unittest.TestCase):
    """V5 contra la forma real que la fábrica emite.

    Es la comprobación que decide si la regla está bien escrita. Los casos
    sembrados sólo demuestran que V5 rechaza; éste demuestra que rechaza *lo
    que hay que rechazar*. Si marca la salida que la cadena produce cuando todo
    salió bien, está mal la regla, no la salida.

    **De dónde salieron los fixtures.** Son copia byte a byte de
    `entregas/5bf52c6d1bee4325b0ff563de29d3fb7/U1`, extraídos el 2026-08-28 del
    área de entregas —`entregas/`, donde ADR-015 materializa la evidencia—.
    Ese día había dieciséis corridas depositadas y los cuatro entregables eran
    **idénticos en las dieciséis**: una variante de contenido por archivo,
    verificado por hash. Por eso una unidad es el conjunto entero y no una
    muestra —copiar dieciséis veces los mismos bytes no agregaría un solo
    caso—, y por eso cubre las formas de carga que la fábrica produce hoy:
    `require` de builtin (`node:test`, `node:assert`), `require` relativo al
    propio directorio (`../src/u1.js`) y `<script src="./src/u1.js">`.

    **Qué son y qué no.** Son archivos que la cadena depositó de verdad, no
    casos inventados para que la regla pase: tienen los cuatro entregables del
    contrato y la forma exacta que emite el productor. Pero no pasaron por un
    Gate, y salieron del stub —la primera línea de `src/u1.js` lo dice:
    "producida por el stub del Developer. No hubo modelo"—. Para lo que este
    test comprueba —que V5 no rechace la forma que la fábrica emite— alcanza;
    para afirmar que V5 tolera todo lo que un modelo podría escribir, no.
    Cuando una corrida con modelo materialice evidencia, conviene sumarla acá.

    La redacción anterior decía "entregas reales que ya pasaron el Gate de
    salida" y afirmaba que el Gate las había aprobado. Se corrigió contra la
    evidencia: el cruce del `factory.db` real contra `entregas/` mostró que las
    24 corridas depositadas son huérfanas —ninguna tiene un solo evento en el
    store— y que son todas salida de la propia suite. El fixture sirve igual,
    pero por su forma, no por una aprobación que nunca existió.

    Antes vivía leyendo `entregas/` directamente. Se cambió por dos razones:
    ese directorio está fuera del repo, así que el test se salteaba en CI y en
    cualquier otra máquina; y la suite depositaba ahí sus propias corridas, con
    lo que terminaba validando en parte lo que ella misma acababa de generar.
    """

    def test_los_entregables_depositados_pasan_v5(self):
        for ruta, hash_esperado in sorted(ENTREGABLES_DEPOSITADOS.items()):
            archivo_ = ENTREGA_DEPOSITADA / ruta
            with self.subTest(archivo=ruta):
                self.assertTrue(archivo_.is_file(), "falta el fixture %s" % ruta)
                crudo = archivo_.read_bytes()
                self.assertEqual(
                    hashlib.md5(crudo).hexdigest(),
                    hash_esperado,
                    "%s ya no es la entrega que se depositó" % ruta,
                )
                # V5 razona sobre rutas relativas al directorio de la unidad,
                # que es la raíz que la entrega declara. Es la misma forma en
                # la que llegan por el campo `ruta`.
                fallos = inspeccion_js.v5_autocontencion(
                    ruta, crudo.decode("utf-8")
                )
                self.assertEqual(
                    fallos, [], "V5 rechaza trabajo ya aprobado: %s" % ruta
                )

    def test_el_fixture_esta_completo(self):
        """Un fixture vaciado a medias pasaría el test de arriba sin mirar nada.

        Son los cuatro entregables que el contrato exige, ni uno más: un
        archivo suelto en el directorio significa que alguien agregó un caso
        inventado al conjunto que dice ser evidencia.
        """
        presentes = {
            p.relative_to(ENTREGA_DEPOSITADA).as_posix()
            for p in ENTREGA_DEPOSITADA.rglob("*")
            if p.is_file()
        }
        self.assertEqual(presentes, set(ENTREGABLES_DEPOSITADOS))


class SinNode(unittest.TestCase):
    def test_falla_en_vez_de_aprobar_lo_que_no_pudo_parsear(self):
        original = inspeccion_js.shutil.which
        inspeccion_js.shutil.which = lambda _: None
        try:
            with self.assertRaises(inspeccion_js.NodeNoDisponible):
                verificar(entrega(), plan())
        finally:
            inspeccion_js.shutil.which = original


class FormaDeLaSalida(unittest.TestCase):
    def test_todas_las_claves_declaradas(self):
        e = entrega()
        e["archivos"].append(
            {"ruta": "/afuera.js", "rol": "artefacto_esperado", "contenido": "const a = 1;\n"}
        )
        for resultado in (verificar(entrega(), plan()), verificar(e, plan())):
            self.assertEqual(set(resultado), {"valido", "incumplimientos"})
            self.assertIsInstance(resultado["valido"], bool)
            for fallo in resultado["incumplimientos"]:
                self.assertEqual(set(fallo), {"regla", "archivo", "detalle"})
                self.assertIsInstance(fallo["regla"], str)
                self.assertIsInstance(fallo["detalle"], str)
                self.assertTrue(fallo["archivo"] is None or isinstance(fallo["archivo"], str))

    def test_esquema_invalido_no_evalua_el_resto(self):
        e = entrega()
        e["notas"] = "x"
        archivo(e, "src/validar-legajo.js")["contenido"] += '\nconsole.log("y");\n'
        r = verificar(e, plan())
        self.assertEqual(reglas(r), {"C0"})

    def test_evalua_todas_las_reglas_sin_cortar_en_la_primera(self):
        e = entrega()
        archivo(e, "demo.html")["contenido"] += "\n<!-- resto igual -->\n"
        archivo(e, "src/validar-legajo.js")["contenido"] += '\nconsole.log("y");\n'
        r = verificar(e, plan())
        self.assertEqual(reglas(r), {"C3", "R3"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
