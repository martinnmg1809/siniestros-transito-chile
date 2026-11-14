"""Evitar aceptar lotes parciales o eliminar eventos válidos en el EDA nuevo."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import proyecto
from descargar_revision_conaset import CAMPOS, validar_ids, validar_lote
from explorar_conaset_2025 import cargar_instantanea, controles, resumir, comparar_historico


def evento(fid=1, anio=2025):
    return {"FID": fid, "ID": fid, "AÑO": anio,
            "FECHA": int(pd.Timestamp(f"{anio}-01-01", tz="UTC").timestamp() * 1000),
            "Dia_semana": "Miércoles" if anio == 2025 else "Lunes", "Mes": "Enero",
            "Hora": "8:15:00", "Hora_aprox": 8, "REGION": "Valparaíso", "COMUNA": "Isla de Pascua",
            "TIPO_SINIE": "COLISIÓN", "ZONA": "URBANA", "Ruta": " ", "Ubicación": 0,
            "FALLECIDOS": 0, "TOTAL_LESI": 1, "GRAVES": 0, "MENOS_GRAV": 0, "LEVES": 1,
            "Latitud": -27.1, "longitud": -109.3}


class Conaset2025Tests(unittest.TestCase):
    def test_no_se_aceptan_lotes_truncados_duplicados_ni_ajenos(self):
        f = {"features": [{"attributes": evento()}]}
        self.assertEqual(len(validar_lote(f, [1])), 1)
        for datos, ids in (({**f, "exceededTransferLimit": True}, [1]),
                           (f, [1, 2]), (f, [2]), ({"features": f["features"] * 2}, [1])):
            with self.assertRaises(ValueError):
                validar_lote(datos, ids)
        with self.assertRaises(ValueError):
            validar_ids({"objectIds": [1, 1]}, 2)
        with self.assertRaises(ValueError):
            validar_ids({"objectIds": [1]}, 2)

    def test_hora_sin_cero_inicial_es_valida_y_no_desplaza_la_fecha(self):
        f = evento()
        c, fechas, horas, _ = controles(pd.DataFrame([f]))
        self.assertFalse(c.hora_invalida.iloc[0])
        self.assertFalse(c.hora_aprox_no_coincide.iloc[0])
        self.assertFalse(c.dia_semana_no_coincide.iloc[0])
        self.assertEqual(horas.iloc[0], 8)
        self.assertEqual(str(fechas.iloc[0].date()), "2025-01-01")
        for invalida in ("24:00:00", "8:60:00", "8:00:61", "", None):
            f["Hora"] = invalida
            self.assertTrue(controles(pd.DataFrame([f]))[0].hora_invalida.iloc[0])

    def test_blanco_y_cero_impiden_identificar_ruta_pero_isla_no_es_error(self):
        c, _, _, coord = controles(pd.DataFrame([evento()]))
        self.assertTrue(c.ruta_ausente.iloc[0])
        self.assertTrue(c.km_ausente_cero_o_negativo.iloc[0])
        self.assertTrue(c.fuera_recuadro_continental.iloc[0])
        self.assertFalse(c.coordenada_invalida_o_cero.iloc[0])
        self.assertTrue(coord.iloc[0])

    def test_eventos_parecidos_no_se_eliminan_ni_se_inventan_dias(self):
        tablas = resumir(pd.DataFrame([evento(1), evento(2)]))
        self.assertEqual(tablas["resumen"].registros.iloc[0], 2)
        self.assertEqual(tablas["resumen"].dias_con_eventos.iloc[0], 1)
        self.assertEqual(tablas["resumen"].dias_calendario.iloc[0], 365)
        self.assertEqual(tablas["repeticiones"].filas_iguales_sin_identificadores.iloc[0], 2)

    def test_el_contraste_detecta_cambios_sin_confundir_otras_rutas(self):
        f = evento(1, 2024)
        f["Ruta"], f["Ubicación"] = "RUTA 5 SUR", 10
        antiguo = pd.DataFrame([f, {**f, "ID": 9, "Ruta": "RUTA 5 NORTE"}])
        antiguo["FECHA"] = "2024-01-01"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "historico.csv"
            antiguo.to_csv(p, index=False)
            actual = pd.DataFrame([{**f, "Ubicación": 15}])
            r = comparar_historico(actual, p).set_index("control").registros
            self.assertEqual(r.id_en_ambas_versiones, 1)
            self.assertEqual(r.id_solo_en_historico, 0)
            self.assertEqual(r["diferencias_Ubicación"], 1)
            self.assertEqual(r.diferencias_FECHA, 0)

    def test_la_lectura_rechaza_archivo_alterado_o_instantanea_incompleta(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "manifiesto.json").write_text(json.dumps({"verificacion_completa": False}))
            with self.assertRaisesRegex(ValueError, "no completó"):
                cargar_instantanea(p)
            crudo = b'{}'
            (p / "lote.json.gz").write_bytes(gzip.compress(b'{"cambio":1}'))
            m = {"verificacion_completa": True, "archivos": [{"archivo": "lote.json.gz",
                 "sha256_respuesta": hashlib.sha256(crudo).hexdigest()}]}
            (p / "manifiesto.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "Hash distinto"):
                cargar_instantanea(p)


if __name__ == "__main__":
    unittest.main()
