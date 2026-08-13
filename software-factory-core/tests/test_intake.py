"""Criterio de aceptación de T8. Nueve tests, uno por fila de la tabla."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from intake import PedidoRechazado, ingresar, texto_rastreable, validar  # noqa: E402
from operational_state import OperationalState  # noqa: E402

PEDIDO_VALIDO = {
    "que_se_quiere": "Herramienta que lee un CSV de altas de empleados y reporta qué filas no se pueden importar.",
    "para_que": "Para dejar de revisar a mano cada archivo que manda la consultora.",
    "alcance_excluido": ["interfaz gráfica", "conexión al sistema viejo"],
    "techo_costo_usd": 2,
    "techo_tiempo_min": 20,
    "techo_iteraciones": 5,
}


class BaseIntake(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self._dir.name) / "estado" / "factory-test.db"
        self.store = OperationalState(self.ruta)

    def tearDown(self):
        self.store.cerrar()
        self._dir.cleanup()

    def pedido(self, **cambios):
        p = copy.deepcopy(PEDIDO_VALIDO)
        p.update(cambios)
        return p

    def eventos_totales(self):
        return self.store._conexion.execute("SELECT COUNT(*) FROM evento").fetchone()[0]

    def assertRechazaSinEventos(self, pedido, fragmento):
        with self.assertRaises(PedidoRechazado) as capturado:
            ingresar(pedido, self.store)
        self.assertIn(fragmento, str(capturado.exception))
        # Un pedido inválido no deja rastro de corrida.
        self.assertEqual(self.eventos_totales(), 0)


class PedidoValido(BaseIntake):
    def test_devuelve_run_id_y_deja_tres_eventos_en_orden(self):
        run_id = ingresar(self.pedido(), self.store)
        self.assertTrue(run_id)
        eventos = self.store.leer_run(run_id)
        self.assertEqual(
            [e["tipo"] for e in eventos],
            ["run_iniciada", "pedido_recibido", "techos_declarados"],
        )
        self.assertEqual(self.eventos_totales(), 3)
        self.assertEqual(eventos[0]["payload"]["agent_definition_id"], "requirement-agent")
        self.assertEqual(
            eventos[2]["payload"], {"costo": 2, "tiempo": 20, "iteraciones": 5}
        )


class CampoFaltante(BaseIntake):
    def test_rechaza_nombrando_el_campo_y_no_escribe(self):
        for campo in PEDIDO_VALIDO:
            with self.subTest(campo=campo):
                p = self.pedido()
                del p[campo]
                self.assertRechazaSinEventos(p, "falta el campo '%s'" % campo)


class CampoVacio(BaseIntake):
    def test_rechaza_que_se_quiere_en_blanco(self):
        self.assertRechazaSinEventos(
            self.pedido(que_se_quiere="   "), "'que_se_quiere' está vacío"
        )


class TechoCero(BaseIntake):
    def test_rechaza_techo_costo_cero(self):
        self.assertRechazaSinEventos(
            self.pedido(techo_costo_usd=0), "'techo_costo_usd' debe ser mayor que cero"
        )


class TechoNoNumerico(BaseIntake):
    def test_rechaza_techo_tiempo_en_texto(self):
        self.assertRechazaSinEventos(
            self.pedido(techo_tiempo_min="veinte"), "'techo_tiempo_min' no es numérico"
        )


class IteracionesDecimales(BaseIntake):
    def test_rechaza_iteraciones_no_enteras(self):
        self.assertRechazaSinEventos(
            self.pedido(techo_iteraciones=2.5), "'techo_iteraciones' debe ser entero"
        )


class AlcanceExcluidoConVacio(BaseIntake):
    def test_rechaza_termino_excluido_vacio(self):
        self.assertRechazaSinEventos(
            self.pedido(alcance_excluido=["interfaz gráfica", ""]), "'alcance_excluido[1]' está vacío"
        )


class IntegridadDelPedido(BaseIntake):
    def test_el_payload_es_identico_al_archivo_de_entrada(self):
        archivo = Path(self._dir.name) / "pedido.json"
        archivo.write_text(json.dumps(PEDIDO_VALIDO, ensure_ascii=False), encoding="utf-8")
        desde_archivo = json.loads(archivo.read_text(encoding="utf-8"))

        run_id = ingresar(desde_archivo, self.store)
        registrado = [
            e for e in self.store.leer_run(run_id) if e["tipo"] == "pedido_recibido"
        ][0]["payload"]
        self.assertEqual(registrado, desde_archivo)
        # Íntegro y sin normalizar: ni una clave de más, ni una de menos.
        self.assertEqual(set(registrado), set(PEDIDO_VALIDO))


class TextoRastreable(BaseIntake):
    def test_devuelve_exactamente_que_se_quiere_mas_para_que(self):
        p = self.pedido()
        self.assertEqual(
            texto_rastreable(p), p["que_se_quiere"] + "\n" + p["para_que"]
        )
        # Ni los techos ni el alcance excluido forman parte del texto rastreable.
        texto = texto_rastreable(p)
        self.assertNotIn("interfaz gráfica", texto)
        self.assertNotIn("20", texto)
        self.assertEqual(validar(p), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
