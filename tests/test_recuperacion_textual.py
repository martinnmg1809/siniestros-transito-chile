"""El número publicado y la incertidumbre no se convierten en etiquetas inventadas."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import proyecto
from descargar_direcciones_conaset import validar, CAMPOS
from examinar_ambiguedades import examinar_direccion, escenario_bordes, resumir_escenario


class RecuperacionTextualTests(unittest.TestCase):
    def test_numero_decimal_explicito_no_se_declara_kilometraje_validado(self):
        d = examinar_direccion("Ruta 5 Sur 127,35, Requínoa", "REQUINOA")
        self.assertAlmostEqual(d["numero_textual"], 127.35)
        self.assertIn("sin_unidad_acreditada", d["estado_texto"])
        self.assertNotIn("km", d)

    def test_metros_y_cero_no_se_convierten_automaticamente(self):
        self.assertEqual(examinar_direccion("RUTA 5 SUR 36800, Buin", "Buin")["numero_textual"], 36800)
        self.assertEqual(examinar_direccion("RUTA 5 SUR 0, Paine", "Paine")["numero_textual"], 0)

    def test_caleteras_intersecciones_y_otra_ruta_no_se_confunden(self):
        self.assertEqual(examinar_direccion("CALETERA RUTA 5 SUR 25, Buin", "Buin")["estado_texto"], "caletera_o_servicio")
        self.assertEqual(examinar_direccion("CALLE & RUTA 5 SUR, Buin", "Buin")["estado_texto"], "interseccion")
        self.assertEqual(examinar_direccion("RUTA 5 NORTE 25, Buin", "Buin")["estado_texto"], "sin_mencion_literal")

    def test_comuna_discordante_y_numero_ausente_quedan_sin_resolver(self):
        self.assertEqual(examinar_direccion("RUTA 5 SUR 25, Maipo", "Buin")["estado_texto"], "comuna_no_coincide")
        self.assertTrue(np.isnan(examinar_direccion("RUTA 5 SUR, Buin", "Buin")["numero_textual"]))
        self.assertEqual(examinar_direccion(None, "Buin")["estado_texto"], "sin_mencion_literal")

    def test_redondeo_exploratorio_no_resuelve_via_ambigua_ni_modifica_original(self):
        d = pd.DataFrame({"estado": ["borde_tramo", "via_ambigua"], "km_estimado": [24.9999998] * 2})
        out, cambio = escenario_bordes(d, .001)
        self.assertEqual(list(cambio), [True, False])
        self.assertEqual(out.estado.iloc[1], "via_ambigua")
        self.assertEqual(d.estado.iloc[0], "borde_tramo")
        self.assertEqual(out.km_estimado.iloc[0], 25)

    def test_desconocidos_no_se_cuentan_como_falsos_positivos(self):
        d = pd.DataFrame({"estado": ["borde_tramo"] * 3, "km_estimado": [24.9999998] * 3,
                          "etiqueta": ["ruta5sur", "otra_via", "desconocida"], "Ubicación": [25, 0, 0]})
        m = resumir_escenario(d, .001)
        self.assertEqual(m["tp_exploratorios"], 1)
        self.assertEqual(m["fp_exploratorios"], 1)
        self.assertEqual(m["asignables_desconocidos"], 1)
        self.assertIn("post hoc", m["uso"])

    def test_complemento_rechaza_lote_truncado_repetido_o_de_otro_anio(self):
        f = {c: None for c in CAMPOS}
        f.update(FID=1, ID=10, **{"AÑO": 2025})
        d = {"features": [{"attributes": f}]}
        self.assertEqual(len(validar(d, [1], 2025)), 1)
        for datos, ids, anio in [({**d, "exceededTransferLimit": True}, [1], 2025),
                                 (d, [1, 2], 2025), (d, [1], 2024),
                                 ({"features": d["features"] * 2}, [1], 2025)]:
            with self.assertRaises(ValueError):
                validar(datos, ids, anio)


if __name__ == "__main__":
    unittest.main()
