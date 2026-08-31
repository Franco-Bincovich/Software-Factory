"""Criterio de aceptación de T10. Diez tests, uno por fila de la tabla."""

import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from agent_loader import CargaFallida, cargar  # noqa: E402
from operational_state import OperationalState  # noqa: E402

# RAIZ es software-factory-core, asi que el Vault cuelga de RAIZ.parent: vive en
# la raiz del repo, al lado del paquete y no adentro.
DEFINICION_REAL = RAIZ.parent / "03 - Agent Framework" / "Requirement Agent.md"

FRONTMATTER = """---
titulo: Agente de prueba
tipo: agent-definition
estado: aceptado
version: 1.0
owner: CEO
agent_id: agente-prueba
techo_costo_usd: 2
techo_tiempo_min: 20
techo_iteraciones: 5
herramientas: [leer_pedido, leer_vault]
vault_lectura: ["03 - Agent Framework/Contrato del Plan de Trabajo.md"]
vault_escritura: []
memory: none
---
"""

CAMPOS = (
    (1, "Identidad", "**Identificador:** `agente-prueba`. Version 1.0. Estado activo."),
    (2, "Propósito", "Convertir un pedido en un Plan de Trabajo."),
    (3, "Entrada", "Un pedido de Intake con sus cuatro campos."),
    (4, "Salida", "Un Plan de Trabajo depositado en el Operational State."),
    (5, "Herramientas autorizadas", "Lista cerrada de dos. Denegación por defecto."),
    (6, "Alcance de decisión", "Decide el método. Propone el plan. Tiene prohibido aprobarlo."),
    (7, "Criterio de terminación", "El plan pasa las nueve reglas y su Gate de salida."),
    (
        8,
        "Presupuesto",
        "**Costo:** USD 2 por Agent Run.\n**Tiempo:** 20 minutos de reloj.\n"
        "**Iteraciones:** 5 ciclos completos.",
    ),
    (9, "Comportamiento ante fallo", "Reintenta corrigiendo lo señalado, hasta agotar el techo."),
    (10, "Escalamiento", "Escala al CEO con el pedido íntegro y la condición disparada."),
    (11, "Acceso al conocimiento", "Vault: lectura. Operational State: lectura y escritura."),
    (12, "Evidencia", "Queda registrada cada iteración con su veredicto."),
    (13, "Dependencias", "Agent Definitions: ninguna. Requiere el contrato y el verificador."),
)


def documento(frontmatter=FRONTMATTER, campos=CAMPOS):
    partes = [frontmatter, "\n# Agente de prueba — Agent Definition\n"]
    for numero, nombre, contenido in campos:
        partes.append("\n## %d. %s\n\n%s\n" % (numero, nombre, contenido))
    return "".join(partes)


class BaseLoader(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.ruta_db = Path(self._dir.name) / "estado" / "factory-test.db"
        self.store = OperationalState(self.ruta_db)

    def tearDown(self):
        self.store.cerrar()
        self._dir.cleanup()

    def escribir(self, texto):
        ruta = Path(self._dir.name) / "definicion.md"
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    def eventos_totales(self):
        return self.store._conexion.execute("SELECT COUNT(*) FROM evento").fetchone()[0]

    def assertFalla(self, texto, *fragmentos):
        with self.assertRaises(CargaFallida) as capturado:
            cargar(self.escribir(texto))
        mensaje = str(capturado.exception)
        for fragmento in fragmentos:
            self.assertIn(fragmento, mensaje)
        return capturado.exception


class DefinicionCompleta(BaseLoader):
    def test_carga_y_expone_los_ocho_parametros(self):
        d = cargar(self.escribir(documento()))
        self.assertEqual(d.agent_id, "agente-prueba")
        self.assertEqual(d.techo_costo_usd, 2)
        self.assertEqual(d.techo_tiempo_min, 20)
        self.assertEqual(d.techo_iteraciones, 5)
        self.assertEqual(d.herramientas, ("leer_pedido", "leer_vault"))
        self.assertEqual(
            d.vault_lectura, ("03 - Agent Framework/Contrato del Plan de Trabajo.md",)
        )
        self.assertEqual(d.vault_escritura, ())
        self.assertEqual(d.memory, "none")
        # No expone el cuerpo: el runtime opera sobre parámetros, no sobre prosa.
        self.assertFalse(hasattr(d, "cuerpo"))
        self.assertFalse(hasattr(d, "body"))


class CampoDelCuerpoFaltante(BaseLoader):
    def test_falla_nombrando_cual_de_los_trece_falta(self):
        campos = [c for c in CAMPOS if c[0] != 10]
        self.assertFalla(documento(campos=campos), "falta el campo 10", "Escalamiento")


class CampoDelCuerpoVacio(BaseLoader):
    def test_encabezado_presente_sin_contenido_falla(self):
        campos = [(c[0], c[1], "" if c[0] == 12 else c[2]) for c in CAMPOS]
        self.assertFalla(documento(campos=campos), "campo 12", "no tiene contenido debajo")


class MarcadorDeRelleno(BaseLoader):
    def test_falla_nombrando_el_campo_y_el_marcador(self):
        campos = [(c[0], c[1], "TBD" if c[0] == 7 else c[2]) for c in CAMPOS]
        self.assertFalla(documento(campos=campos), "campo 7", "marcador de relleno 'TBD'")

        # Los acrónimos se buscan respetando mayúsculas: en castellano "todo" es
        # una palabra corriente y buscarla sin distinguir marcaría documentos sanos.
        sanos = [
            (c[0], c[1], "Todo escalamiento queda registrado." if c[0] == 12 else c[2])
            for c in CAMPOS
        ]
        cargar(self.escribir(documento(campos=sanos)))


class FrontmatterIncompleto(BaseLoader):
    def test_sin_techo_costo_usd_falla_nombrandolo(self):
        fm = FRONTMATTER.replace("techo_costo_usd: 2\n", "")
        self.assertFalla(documento(frontmatter=fm), "frontmatter", "'techo_costo_usd'")


class TechoInvalido(BaseLoader):
    def test_techo_en_cero_falla(self):
        fm = FRONTMATTER.replace("techo_costo_usd: 2", "techo_costo_usd: 0")
        self.assertFalla(documento(frontmatter=fm), "'techo_costo_usd' debe ser mayor que cero")


class EstadoNoAceptado(BaseLoader):
    def test_estado_propuesto_falla(self):
        fm = FRONTMATTER.replace("estado: aceptado", "estado: propuesto")
        self.assertFalla(documento(frontmatter=fm), "'estado' debe ser 'aceptado'")


class DiscrepanciaCuerpoFrontmatter(BaseLoader):
    def test_falla_nombrando_ambos_valores(self):
        campos = [
            (
                c[0],
                c[1],
                c[2].replace("USD 2 por", "USD 5 por") if c[0] == 8 else c[2],
            )
            for c in CAMPOS
        ]
        error = self.assertFalla(
            documento(campos=campos), "coherencia", "techo_costo_usd"
        )
        mensaje = str(error)
        self.assertIn("2", mensaje)
        self.assertIn("5", mensaje)
        self.assertIn("El cuerpo manda", mensaje)


class SinEfectosSecundarios(BaseLoader):
    def test_ningun_fallo_escribe_en_el_operational_state(self):
        casos = [
            documento(campos=[c for c in CAMPOS if c[0] != 3]),
            documento(frontmatter=FRONTMATTER.replace("estado: aceptado", "estado: propuesto")),
            documento(campos=[(c[0], c[1], "XXX" if c[0] == 5 else c[2]) for c in CAMPOS]),
        ]
        for texto in casos:
            with self.assertRaises(CargaFallida):
                cargar(self.escribir(texto))
        self.assertEqual(self.eventos_totales(), 0)
        # El módulo ni siquiera conoce al almacén.
        fuente = (RAIZ / "src" / "agent_loader.py").read_text(encoding="utf-8")
        self.assertNotIn("operational_state", fuente)


class DefinicionReal(BaseLoader):
    def test_carga_el_requirement_agent_del_vault_sin_error(self):
        self.assertTrue(DEFINICION_REAL.exists(), "falta la definición real en el vault")
        d = cargar(DEFINICION_REAL)
        self.assertEqual(d.agent_id, "requirement-agent")
        self.assertEqual(d.techo_costo_usd, 2)
        self.assertEqual(d.techo_tiempo_min, 20)
        self.assertEqual(d.techo_iteraciones, 5)
        self.assertEqual(
            d.herramientas,
            ("leer_pedido", "leer_vault", "escribir_salida", "escribir_operational_state"),
        )
        self.assertEqual(d.vault_escritura, ())
        self.assertEqual(d.memory, "none")


if __name__ == "__main__":
    unittest.main(verbosity=2)
