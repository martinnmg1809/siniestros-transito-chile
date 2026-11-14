from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tendencia_anual import ajustar_tendencia


class TendenciaTests(unittest.TestCase):
    def test_recupera_tendencia_exacta_con_conteos_esperados(self):
        anios, horas = [2020, 2021, 2022], [8784, 8760, 8760]
        conteos = [h * .3 * 1.2 ** (a - 2020) for a, h in zip(anios, horas)]
        a, b = ajustar_tendencia(anios, conteos, horas)
        self.assertAlmostEqual(np.exp(b), 1.2, places=6)
        self.assertAlmostEqual(np.exp(a), .3, places=6)

    def test_con_dos_anios_reproduce_ambos_totales(self):
        a, b = ajustar_tendencia([2020, 2021], [2295, 3288], [8784, 8760])
        np.testing.assert_allclose(np.exp(a + b * np.array([0, 1])) * [8784, 8760], [2295, 3288], rtol=1e-6)


if __name__ == "__main__":
    unittest.main()
