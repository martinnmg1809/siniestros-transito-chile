from pathlib import Path
import sys
import tempfile
import unittest
import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrar_flujo import asignar_contratos, flujo_rezagado, normalizar_puntos
from modelos_conteo import ModeloConteo, ModeloHibrido, elegir_configuracion
from datos_modelado import cuarentena_espacial
from datos_ruta5 import cargar_eventos
from calibracion_modelos import ModeloCalibrado


class FlujoModelosTests(unittest.TestCase):
    def test_residuos_no_crean_puntos_de_cobro_distintos(self):
        np.testing.assert_array_equal(normalizar_puntos([4 - 1e-9, 4 + 1e-9, 4.5, 5.01]), [4, 4, 4.5, 5.01])

    def test_bordes_bypass_y_zonas_sin_flujo_no_se_rellenan(self):
        r = asignar_contratos([0, 220, 225, 405, 410, 415, 575, 660, 685, 900, 1100]).set_index("tramo")
        self.assertEqual(r.loc[225, "contrato"], "Talca-Chillán")
        self.assertEqual(r.loc[405, "contrato"], "Talca-Chillán")
        self.assertTrue(r.loc[[0, 220, 410, 575, 660, 1100], "contrato"].eq("").all())
        self.assertEqual(r.loc[685, "contrato"], "Collipulli-Temuco")

    def test_flujo_del_trimestre_objetivo_no_entra(self):
        asignacion = pd.DataFrame({"tramo": [225, 0], "contrato": ["A", ""]})
        serie = pd.DataFrame({"contrato": ["A", "A"], "periodo": pd.PeriodIndex(["2019Q3", "2020Q1"], freq="Q"),
                              "proxy_pasadas_por_punto_dia": [100., 99999.], "puntos_implicitos": [4., 4.],
                              "version_anexo": ["2024_4t"] * 2, "fuente": ["MOP"] * 2,
                              "celda_promedio": ["A1"] * 2, "celda_total": ["B1"] * 2})
        r = flujo_rezagado(asignacion, ["2020Q1"], serie).set_index("tramo")
        self.assertEqual(r.loc[225, "proxy_pasadas_por_punto_dia"], 100)
        self.assertTrue(pd.isna(r.loc[0, "proxy_pasadas_por_punto_dia"]))
        self.assertGreaterEqual(r.loc[225, "dias_desde_cierre"], 90)
        self.assertFalse(r.loc[225, "disponibilidad_publicacion_acreditada"])

    def test_cuarentena_no_imputa_ubicacion_y_preserva_fuente(self):
        d, _ = cargar_eventos()
        antes = d.copy(deep=True)
        limpios, q = cuarentena_espacial(d)
        self.assertEqual(len(q), 5)
        self.assertEqual(len(limpios), 14420)
        self.assertEqual(set(q.ID), {1407830, 1407806, 1408146, 1334758, 1429192})
        pd.testing.assert_frame_equal(d, antes)

    def test_hiperparametros_no_usan_el_test_actual(self):
        h = [{"familia": "Poisson", "variante": "clima", "cohorte": "ruta_completa", "anio_prueba": anio,
              "configuracion": cfg, "captura5": valor} for anio, cfg, valor in
             [(2022, 0, .2), (2022, 1, .19), (2023, 0, .2), (2023, 1, .19), (2024, 1, .99)]]
        i, anios = elegir_configuracion(h, "Poisson", "clima", "ruta_completa", 2024)
        self.assertEqual(i, 0)
        self.assertEqual(anios, [2022, 2023])

    def test_tres_familias_predicen_conteos_no_negativos_y_se_guardan(self):
        rng = np.random.default_rng(42)
        f = np.zeros((100, 9)); f[:, 0] = np.arange(100) % 2
        f[:, 1] = np.arange(100) % 24; f[:, 6] = np.arange(100) % 3
        f[:, 7] = np.log(100 + np.arange(100)); f[:, 8] = np.log(4.)
        y = (np.arange(100) % 2).astype(float); e = rng.uniform(1, 3, 100)
        for familia, parametros in [("Poisson", {"l2": 1.}),
                                    ("GradientBoosting", {"max_leaf_nodes": 7, "max_iter": 5}),
                                    ("RandomForest", {"max_depth": 4, "min_samples_leaf": 10})]:
            with self.subTest(familia=familia):
                m = ModeloConteo(familia, "clima_flujo", parametros).fit(f, y, e)
                pred = m.predict_rate(f)
                self.assertTrue(np.isfinite(pred).all() and (pred > 0).all())
                with tempfile.TemporaryDirectory() as td:
                    p = Path(td) / "modelo.joblib"; joblib.dump(m, p)
                    self.assertTrue(np.allclose(joblib.load(p).predict_rate(f), pred))
                    calibrado = ModeloCalibrado(m, .7, 2023)
                    joblib.dump(calibrado, p)
                    self.assertTrue(np.allclose(joblib.load(p).predict_rate(f), pred * .7))
                    self.assertTrue(np.array_equal(np.argsort(pred), np.argsort(calibrado.predict_rate(f))))
                with self.assertRaises(ValueError):
                    ModeloCalibrado(m, 0, 2023)
                con_faltante = f.copy(); con_faltante[0, 7] = np.nan
                with self.assertRaises(ValueError):
                    m.predict_rate(con_faltante)

    def test_hibrido_respalda_cuando_falta_flujo(self):
        class Constante:
            variante = "clima_flujo"
            def __init__(self, valor): self.valor = valor
            def predict_rate(self, f): return np.full(len(f), self.valor, dtype=float)
        f = np.zeros((3, 9)); f[:, 0] = [0, 1, 1]; f[2, 7] = np.nan
        m = ModeloHibrido(Constante(1), Constante(2), [1])
        self.assertTrue(np.array_equal(m.predict_rate(f), [1, 2, 1]))


if __name__ == "__main__":
    unittest.main()
