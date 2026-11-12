"""Comprobaciones de las decisiones de EDA, sin ajustar modelos del proyecto."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from explorar_datos import (perfil_numerico, comparar_versiones, cobertura_espacial,
                            discordancias_espaciales, actualizar_readme, MARCAS)
from flujo_vehicular import clasificar_rol


class ExploracionTests(unittest.TestCase):
    def test_faltante_cero_e_infinito_no_se_mezclan(self):
        p = perfil_numerico([np.nan, 0, -1, np.inf, 3])
        self.assertEqual(p["faltantes"], 1)
        self.assertEqual(p["ceros"], 1)
        self.assertEqual(p["infinitos"], 1)
        self.assertEqual(p["negativos"], 1)
        self.assertEqual(p["positivos"], 1)
        self.assertEqual(p["mediana"], 3)

    def test_marcadores_no_son_codigos_de_ruta(self):
        self.assertEqual(clasificar_rol(" - "), "marcador")
        self.assertEqual(clasificar_rol(" S/ ROL "), "sin_rol_identificado")
        self.assertEqual(clasificar_rol(""), "ausente")
        self.assertEqual(clasificar_rol(None), "ausente")
        self.assertEqual(clasificar_rol("Ruta 5"), "identificado")

    def versiones(self):
        return pd.DataFrame({"version_anexo": ["2023_4t", "2024_4t"], "contrato": ["Ejemplo"] * 2,
                             "anio": [2023] * 2, "trimestre": [1] * 2,
                             "transacciones_trimestre": [300., 330.],
                             "pasadas_promedio_por_punto_mes": [10., 11.]})

    def test_versiones_no_se_suman_y_revision_queda_visible(self):
        canon, revision = comparar_versiones(self.versiones())
        self.assertEqual(len(canon), 1)
        self.assertEqual(canon.transacciones_trimestre.iloc[0], 330)
        self.assertEqual(revision.diferencia_transacciones_trimestre.iloc[0], 30)
        self.assertTrue(revision.cambio_transacciones_trimestre.iloc[0])
        self.assertAlmostEqual(canon.puntos_cobro_implicitos.iloc[0], 10)

    def test_duplicado_dentro_de_version_no_se_oculta(self):
        d = self.versiones()
        with self.assertRaises(ValueError):
            comparar_versiones(pd.concat([d, d.iloc[[0]]], ignore_index=True))

    def test_cobertura_penaliza_antiguedad_y_excluye_mismo_anio(self):
        c = pd.DataFrame({"estacion": ["reciente", "antigua", "futura"], "anio_medicion": [2023, 2014, 2024],
                          "lat": [-34., -35., -35.], "lon": [-71.] * 3,
                          "distancia_eje_km": [0.] * 3, "km_proyectado": [2.5, 12.5, 12.5]})
        ref = pd.DataFrame({"tramo": [0, 10]})
        eventos = pd.DataFrame({"anio": [2024, 2024], "tramo": [0, 10]})
        r = cobertura_espacial(c, ref, eventos)
        rec = r.loc[r.anio.eq(2024) & r.antiguedad_max_anios.eq(2) & r.alcance_longitudinal_km.eq(5)].iloc[0]
        vieja = r.loc[r.anio.eq(2024) & r.antiguedad_max_anios.eq("sin_limite") & r.alcance_longitudinal_km.eq(5)].iloc[0]
        self.assertEqual(rec.tramos_candidatos, 1)
        self.assertEqual(vieja.tramos_candidatos, 2)
        self.assertFalse(rec.disponibilidad_historica_acreditada)

    def test_discordancia_espacial_no_se_oculta_en_correlacion_global(self):
        d = pd.DataFrame({"ID": [1, 2], "FECHA": ["2020-01-01"] * 2, "Ruta": ["RUTA 5 SUR"] * 2,
                          "REGION": ["X"] * 2, "COMUNA": ["Y"] * 2, "km": [1., 6.], "tramo": [0, 5],
                          "Latitud": [-34., -40.], "longitud": [-71., -71.]})
        ref = pd.DataFrame({"tramo": [0, 5], "lat": [-34., -34.05], "lon": [-71., -71.]})
        r = discordancias_espaciales(d, ref)
        self.assertFalse(r.bandera_mayor_10km.iloc[0])
        self.assertTrue(r.bandera_mayor_10km.iloc[1])
        self.assertGreater(r.distancia_referencia_km.iloc[1], 600)
        self.assertEqual(d.km.iloc[1], 6)  # No imputa ni corrige la fuente.

    def test_actualizar_readme_es_idempotente_y_preserva_otras_secciones(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "README.md"
            archivo.write_text("# Proyecto\n\n## Desarrollo de la Entrega 3\n\nTexto anterior.\n")
            bloque = MARCAS[0] + "\nEDA comprobado\n" + MARCAS[1] + "\n"
            actualizar_readme(archivo, bloque)
            antes = archivo.read_text()
            actualizar_readme(archivo, bloque)
            self.assertEqual(archivo.read_text(), antes)
            self.assertIn("Texto anterior.", archivo.read_text())


if __name__ == "__main__":
    unittest.main()
