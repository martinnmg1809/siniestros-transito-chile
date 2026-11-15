"""El punto de entrada debe resolver rutas sin depender de la carpeta del usuario."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EstructuraTests(unittest.TestCase):
    def test_verificacion_desde_otro_directorio(self):
        with tempfile.TemporaryDirectory() as temporal:
            resultado = subprocess.run([sys.executable, str(ROOT / "proyecto.py"), "verificar_cierre"],
                                       cwd=temporal, capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
            self.assertIn("Estado: CORRECTO", resultado.stdout)
            self.assertEqual(list(Path(temporal).iterdir()), [])

    def test_comando_desconocido_no_ejecuta_un_script(self):
        resultado = subprocess.run([sys.executable, str(ROOT / "proyecto.py"), "inexistente"],
                                   cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 2)
        self.assertIn("Comando desconocido", resultado.stderr)


if __name__ == "__main__":
    unittest.main()
