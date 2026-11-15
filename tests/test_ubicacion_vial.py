"""Controles de ambigüedad, medida M, partes e independencia de las etiquetas."""
from pathlib import Path
import sys
import unittest
import importlib.util
import subprocess
import tempfile
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import proyecto
DISPONIBLE = all(importlib.util.find_spec(m) for m in ("shapely", "pyproj"))
if DISPONIBLE:
    import pandas as pd
    from pyproj import Transformer
    from ubicacion_vial import IndiceVial, decidir, es_ruta5_sur
    from descargar_eje_mop import validar_geolote
    from evaluar_asignacion_vial import etiquetar, wilson, metricas


@unittest.skipUnless(DISPONIBLE, "Instalar requirements-espacial.txt para comprobar el ensayo espacial")
class UbicacionVialTests(unittest.TestCase):
    def setUp(self):
        self.inv = Transformer.from_crs(32719, 4326, always_xy=True)
        self.x0, self.y0 = 350000, 6200000
        self.p = {"distancia_max_m": 75, "margen_competidora_m": 30,
                  "tolerancia_alternativas_ruta5_m": 200, "distancia_borde_tramo_m": 50,
                  "km_min": 0, "km_max_exclusivo": 1275, "tramo_km": 5}

    def feature(self, oid, sur, y, m0=20000, m1=21000, partes=None):
        def v(x, y, m):
            lon, lat = self.inv.transform(self.x0 + x, self.y0 + y)
            return [lon, lat, m]
        paths = partes or [[v(0, y, m0), v(1000, y, m1)]]
        return {"attributes": {"OBJECTID": oid, "ROL_LABEL": "5" if sur else "X-1",
                "ORIENTACION": "-", "NOMBRE_CAMINO": "Longitudinal Sur" if sur else "Otra vía"},
                "geometry": {"hasM": True, "paths": paths}}

    def candidato(self, indice, x=500, y=20):
        lon, lat = self.inv.transform(self.x0 + x, self.y0 + y)
        return indice.candidatos([lon], [lat])[0]

    def test_interpolar_medida_y_distancia_sin_usar_etiqueta_del_evento(self):
        i = IndiceVial([self.feature(1, True, 0), self.feature(2, False, 150)])
        c = self.candidato(i)
        self.assertAlmostEqual(c["km_estimado"], 20.5, places=5)
        self.assertAlmostEqual(c["distancia_ruta5_m"], 20, places=4)
        self.assertEqual(decidir(c, self.p), "candidato_asignable")
        self.assertTrue(es_ruta5_sur(self.feature(1, True, 0)["attributes"]))

    def test_la_via_cercana_y_el_borde_de_tramo_se_mantienen_ambiguos(self):
        i = IndiceVial([self.feature(1, True, 0), self.feature(2, False, 150)])
        self.assertEqual(decidir(self.candidato(i, y=70), self.p), "via_ambigua")
        self.assertEqual(decidir(self.candidato(i, x=10), self.p), "borde_tramo")

    def test_calzadas_con_medidas_incompatibles_no_se_eligen_por_desempate(self):
        i = IndiceVial([self.feature(1, True, 0), self.feature(3, True, 40, 21000, 22000),
                       self.feature(2, False, 150)])
        self.assertEqual(decidir(self.candidato(i, y=10), self.p), "medida_ambigua")

    def test_medida_ausente_o_con_salto_no_se_reconstruye_desde_atributos(self):
        for m0, m1 in [(None, None), (0, 1000000)]:
            i = IndiceVial([self.feature(1, True, 0, m0, m1), self.feature(2, False, 150)])
            self.assertEqual(decidir(self.candidato(i), self.p), "medida_ausente")

    def test_no_se_unen_partes_discontinuas(self):
        a, b = self.feature(1, True, 0), self.feature(3, True, 0)
        for v in b["geometry"]["paths"][0]:
            x, y = Transformer.from_crs(4326, 32719, always_xy=True).transform(v[0], v[1])
            v[0], v[1] = self.inv.transform(x + 2000, y)
        a["geometry"]["paths"].extend(b["geometry"]["paths"])
        i = IndiceVial([a, self.feature(2, False, 150)])
        self.assertEqual(decidir(self.candidato(i, x=1500), self.p), "fuera_distancia")

    def test_blancos_y_rutas_genericas_no_son_negativos(self):
        r = etiquetar(pd.Series([None, pd.NA, " ", "RUTA 5", "RUTA 5 SUR, OTRA", "RUTA 5 SUR", "RUTA 5 NORTE", "V-60"]))
        self.assertEqual(list(r), ["desconocida"] * 5 + ["ruta5sur", "otra_via", "otra_via"])
        self.assertLess(wilson(10, 10)[0], .95)

    def test_lotes_geometricos_truncados_o_sin_m_no_se_aceptan(self):
        d = {"features": [self.feature(1, True, 0)], "hasM": True, "spatialReference": {"wkid": 4326}}
        self.assertEqual(len(validar_geolote(d, [1])), 1)
        for fallo in ({**d, "exceededTransferLimit": True}, {**d, "hasM": False},
                      {**d, "hasZ": True}, {**d, "features": []}):
            with self.assertRaises(ValueError):
                validar_geolote(fallo, [1])

    def test_los_desconocidos_no_inflan_ni_penalizan_la_precision(self):
        d = pd.DataFrame({"etiqueta": ["ruta5sur", "otra_via", "desconocida"],
                          "km_estimado": [20.5] * 3, "Ubicación": [20.5, 5., 0.]})
        m = metricas(d, ["candidato_asignable"] * 3, 75)
        self.assertEqual(m["precision_etiquetados"], .5)
        self.assertEqual(m["sensibilidad_etiquetados"], 1)
        self.assertEqual(m["asignables_sin_etiqueta"], 1)

    def test_no_se_mezclan_propuestas_2025_de_otra_ejecucion(self):
        raiz = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "propuestas_2025.csv.gz"
            p.write_bytes(b"revision anterior")
            r = subprocess.run([sys.executable, str(raiz / "proyecto.py"), "evaluar_asignacion_vial",
                                "--geometria", "no_existe", "--conaset", "no_existe",
                                "--derivados", tmp], cwd=raiz, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("Ya existen propuestas de 2025", r.stderr)
            self.assertEqual(p.read_bytes(), b"revision anterior")


if __name__ == "__main__":
    unittest.main()
