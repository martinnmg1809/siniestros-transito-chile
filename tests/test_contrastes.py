from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import proyecto  # noqa: F401  (rutas de codigo/)
from contrastes_poisson import pares_contraste, contrastar, ejemplo_turno, huella, razon_tendencia
from modelos_conteo import ModeloConteo
from calibracion_modelos import ModeloCalibrado


def combinaciones(n=1500, semilla=3):
    """Combinaciones únicas (como las claves agrupadas); flujo ausente como en tramos sin contrato."""
    r = np.random.default_rng(semilla)
    f = np.unique(np.column_stack([r.integers(0, 4, n), r.integers(0, 4, n), r.integers(0, 2, n),
                                   r.integers(0, 2, n), r.integers(0, 4, n), r.integers(0, 3, n),
                                   r.integers(0, 2, n)]), axis=0).astype(float)
    return np.column_stack([f, np.full((len(f), 2), np.nan)])


class ContrastesTests(unittest.TestCase):
    def test_pares_solo_combinaciones_observadas_y_un_atributo_distinto(self):
        f = combinaciones()
        i, k = pares_contraste(f, "lluvia", 0, 2)
        self.assertTrue(len(i) > 0)
        np.testing.assert_array_equal(f[i, 5], 0)
        np.testing.assert_array_equal(f[k, 5], 2)
        otras = [0, 1, 2, 3, 4, 6]
        np.testing.assert_array_equal(f[i][:, otras], f[k][:, otras])

    def test_sin_pares_falla_en_vez_de_inventar_combinaciones(self):
        f = combinaciones()
        f = f[f[:, 5] != 2]
        with self.assertRaises(ValueError):
            contrastar(np.ones(len(f)), np.ones(len(f)), f, "lluvia", 0, 2)

    def test_poisson_aditivo_da_razon_constante_entre_categorias(self):
        r = np.random.default_rng(0)
        f = combinaciones(3000)
        expo = r.integers(1, 50, len(f)).astype(float)
        y = r.poisson(expo * .01 * np.exp(.4 * (f[:, 5] == 2)))
        m = ModeloConteo("Poisson", "clima", {"l2": .3}).fit(f, y.astype(float), expo)
        tasa = m.predict_rate(f)
        c = contrastar(tasa, expo, f, "lluvia", 0, 2)
        self.assertAlmostEqual(c["razon_min"], c["razon_max"], places=10)
        self.assertGreater(c["razon_mediana"], 1)
        # Un factor global de recalibración no cambia razones ni la huella del ajuste base.
        cal = ModeloCalibrado(m, .7, 2023)
        c2 = contrastar(cal.predict_rate(f), expo, f, "lluvia", 0, 2)
        self.assertAlmostEqual(c["razon_mediana"], c2["razon_mediana"], places=12)
        self.assertEqual(huella(m), huella(cal))

    def test_razon_de_tendencia_recupera_el_cambio_anual(self):
        r = np.random.default_rng(1)
        f = combinaciones(3000)
        expo = np.full(len(f), 2000.)
        y = r.poisson(expo * .01 * 1.3 ** f[:, 6]).astype(float)
        m = ModeloConteo("Poisson", "clima", {"l2": 0.}).fit(f, y, expo)
        self.assertAlmostEqual(razon_tendencia(m), 1.3, delta=.03)
        self.assertAlmostEqual(razon_tendencia(ModeloCalibrado(m, .5, 2023)), razon_tendencia(m))

    def test_turno_de_ejemplo_respeta_presupuesto_y_agrega_la_ruta(self):
        t = pd.date_range("2024-01-01", "2024-01-02 23:00", freq="h")
        datos = {"tiempo": t, "tramos": np.arange(0, 200, 5)}
        n = len(datos["tramos"])
        mu = np.tile(np.linspace(.01, .4, n)[:, None], (1, len(t)))
        y = np.zeros_like(mu); y[-1, 13] = 1
        d = ejemplo_turno(mu, y, datos, "2024-01-01 12:00", .5, 2023)
        tramos = d.iloc[:-1]
        self.assertAlmostEqual(tramos.peso_presupuesto_5pct.sum(), .05 * n)
        self.assertEqual(tramos.tramo_km.iloc[0], 195)
        self.assertAlmostEqual(d.iloc[-1].esperado_original, mu[:, 12:24].sum())
        self.assertAlmostEqual(d.iloc[-1].esperado_recalibrado, .5 * mu[:, 12:24].sum())
        self.assertEqual(d.iloc[-1].observado, 1)
        with self.assertRaises(ValueError):
            ejemplo_turno(mu, y, datos, "2024-01-01 07:00", .5, 2023)


if __name__ == "__main__":
    unittest.main()
