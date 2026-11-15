"""Controles sin red para el piloto de sombra de doce horas."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import proyecto
from insumos_piloto import ventana
from modelo_piloto import predecir
from piloto_12h import atributos_piloto, construir


class Piloto12hTests(unittest.TestCase):
    def setUp(self):
        self.config = {"zona": "America/Santiago", "ajuste_desde": 2020,
                       "cortes_precipitacion_mm": [0.1, 0.5], "presupuesto_maximo": 0.05}

    def test_ventana_son_doce_horas_reales_y_rechaza_hora_sin_zona(self):
        t = ventana("2026-11-14T21:36:00Z")
        self.assertEqual(len(t), 12)
        self.assertEqual(str(t[0]), "2026-11-14 22:00:00+00:00")
        self.assertEqual(str(t[-1]), "2026-11-15 09:00:00+00:00")
        with self.assertRaises(ValueError):
            ventana("2026-11-14 21:36:00")

    def test_atributos_usan_lluvia_y_calendario_sin_rellenar_flujo(self):
        t = pd.date_range("2026-11-14T22:00Z", periods=12, freq="h")
        lluvia = np.tile([0.0, 0.1, 0.6], 4).reshape(1, 12)
        f = atributos_piloto(t, lluvia, ["no"] * 12, self.config)
        self.assertEqual(f.shape, (12, 9))
        self.assertEqual(f[:, 5].tolist(), [0, 1, 2] * 4)
        self.assertTrue(np.isnan(f[:, 7:]).all())
        self.assertTrue((f[:, 6] == 6).all())

    def test_construccion_respeta_dominio_y_presupuesto_con_desempate_estable(self):
        r = pd.DataFrame({"tramo": np.arange(0, 1275, 5), "lat": np.linspace(-33, -42, 255),
                          "lon": np.linspace(-70, -73, 255)})
        t = pd.date_range("2026-11-14T22:00Z", periods=12, freq="h")
        p = np.zeros((255, 12))
        cats = [np.arange(255), np.arange(24), np.arange(7), np.arange(12), np.arange(4), np.arange(3)]
        modelo = {"intercepto": -3.0, "categorias": [x.tolist() for x in cats],
                  "coef_categorias": [[0.0] * len(x) for x in cats], "tendencia_media": 0.0,
                  "tendencia_escala": 1.0, "coef_tendencia": 0.0,
                  "factor_recalibracion_referencia": 0.8}
        _, plan, horas = construir(self.config, modelo, r, t, p, ["no"] * 12)
        self.assertEqual(len(plan), 255)
        self.assertEqual(plan.seleccionado_12h.sum(), 12)
        self.assertEqual(plan.loc[plan.seleccionado_12h, "tramo"].tolist(), list(range(0, 60, 5)))
        self.assertEqual(len(horas), 12)

    def test_prediccion_portable_no_depende_de_columnas_de_flujo_no_usadas(self):
        m = {"intercepto": -2.0, "categorias": [[0], [18], [5], [10], [0], [1]],
             "coef_categorias": [[0.1], [0.2], [0.3], [0.4], [0.5], [0.6]],
             "tendencia_media": 0.0, "tendencia_escala": 1.0, "coef_tendencia": 0.1}
        x = np.array([[0, 18, 5, 10, 0, 1, 6, np.nan, np.nan]], dtype=float)
        y = x.copy()
        y[:, 7:] = [999, -999]
        np.testing.assert_array_equal(predecir(m, x), predecir(m, y))
        with self.assertRaises(ValueError):
            predecir(m, np.array([[1, 18, 5, 10, 0, 1, 6, np.nan, np.nan]]))


if __name__ == "__main__":
    unittest.main()
