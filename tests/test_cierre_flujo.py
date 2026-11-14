"""La integración debe detectar tablas de cobertura alteradas sin sobrescribirlas."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class CierreFlujoTests(unittest.TestCase):
    def ejecutar(self, salida):
        return subprocess.run([sys.executable, str(ROOT / "cierre_flujo.py"),
                               "--comprobar", "--salida", str(salida)], cwd=ROOT,
                              capture_output=True, text=True)

    def test_tabla_publicada_concilia_sin_escritura(self):
        archivo = ROOT / "resultados/cierre/cobertura_flujo_detalle.csv"
        antes = archivo.read_bytes()
        resultado = self.ejecutar(archivo)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
        self.assertIn("comprobado sin escritura", resultado.stdout)
        self.assertEqual(archivo.read_bytes(), antes)

    def test_rechaza_una_cobertura_manipulada_y_la_conserva(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "cobertura.csv"
            tabla = pd.read_csv(ROOT / "resultados/cierre/cobertura_flujo_detalle.csv")
            tabla.loc[0, "siniestros"] += 1
            tabla.to_csv(archivo, index=False)
            antes = archivo.read_bytes()
            resultado = self.ejecutar(archivo)
            self.assertNotEqual(resultado.returncode, 0)
            self.assertIn("NO CONCILIA", resultado.stderr)
            self.assertEqual(archivo.read_bytes(), antes)

    def test_una_tabla_ausente_no_se_genera_al_comprobar(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "ausente.csv"
            resultado = self.ejecutar(archivo)
            self.assertNotEqual(resultado.returncode, 0)
            self.assertIn("no existe", resultado.stderr)
            self.assertFalse(archivo.exists())


if __name__ == "__main__":
    unittest.main()
