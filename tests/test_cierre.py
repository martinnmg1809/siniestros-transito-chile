"""Detectar mezclas de cohortes, fuga temporal y corrupción de evidencia publicada."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verificar_cierre import verificar_tablas


class CierreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.salida = self.raiz / "resultados/modelos"
        self.salida.mkdir(parents=True)
        for archivo in (ROOT / "resultados/modelos").iterdir():
            if archivo.suffix in (".csv", ".json"):
                shutil.copy2(archivo, self.salida / archivo.name)
        a = json.loads((self.salida / "auditoria.json").read_text())
        r = json.loads((self.salida / "reajuste.json").read_text())
        for archivo in list(a["hashes_codigo"] | r["hashes_codigo_postproceso"]) + ["ruta5_2020_2024.csv.gz"]:
            shutil.copy2(ROOT / archivo, self.raiz / archivo)

    def modificar(self, nombre, cambio):
        ruta = self.salida / f"{nombre}.csv"
        tabla = pd.read_csv(ruta)
        cambio(tabla)
        tabla.to_csv(ruta, index=False)

    def test_evidencia_publicada_sin_fuentes_locales_ni_modelos(self):
        mensajes, _, _, _ = verificar_tablas(self.raiz)
        self.assertGreaterEqual(len(mensajes), 5)
        self.assertFalse((self.raiz / "clima_ruta5.npz").exists())
        self.assertFalse((self.salida / "artefactos").exists())

    def test_detecta_mezcla_de_poblacion_entre_cohortes(self):
        def cambiar(t):
            mascara = t.cohorte.eq("con_contrato") & t.anio_prueba.eq(2024) & t.particion.eq("prueba")
            t.loc[mascara, "siniestros"] = 2605
        self.modificar("metricas", cambiar)
        with self.assertRaisesRegex(ValueError, "Población"):
            verificar_tablas(self.raiz)

    def test_rechaza_el_anio_objetivo_en_seleccion(self):
        def cambiar(t):
            t.loc[t.anio_prueba.eq(2024), "anios_usados_para_elegir"] = "2022,2023,2024"
        self.modificar("seleccion_temporal", cambiar)
        with self.assertRaisesRegex(ValueError, "Años de selección"):
            verificar_tablas(self.raiz)

    def test_rechaza_recalibracion_con_el_anio_evaluado(self):
        def cambiar(t):
            t.loc[t.anio_prueba.eq(2024) & t.ajuste.eq("recalibrado"), "anio_factor"] = 2024
        self.modificar("recalibracion_candidato", cambiar)
        with self.assertRaisesRegex(ValueError, "Recalibración usa un año"):
            verificar_tablas(self.raiz)

    def test_no_oculta_filas_duplicadas(self):
        ruta = self.salida / "metricas.csv"
        t = pd.read_csv(ruta)
        pd.concat([t, t.iloc[[0]]]).to_csv(ruta, index=False)
        with self.assertRaisesRegex(ValueError, "claves duplicadas"):
            verificar_tablas(self.raiz)

    def test_detecta_codigo_distinto_del_que_genero_el_modelo(self):
        archivo = self.raiz / "datos_modelado.py"
        archivo.write_text(archivo.read_text() + "\n# versión diferente\n")
        with self.assertRaisesRegex(ValueError, "Hash distinto"):
            verificar_tablas(self.raiz)

    def test_no_acepta_sustituir_el_aporte_de_lluvia_por_otra_comparacion(self):
        def cambiar(t):
            i = t.index[t.modelo.eq("Poisson_clima") & t.referencia.eq("Poisson_calendario")][0]
            t.loc[i, "referencia"] = "Poisson_clima"
            t.loc[i, "diferencia_pp"] = 0.
        self.modificar("bootstrap", cambiar)
        with self.assertRaisesRegex(ValueError, "Bootstrap incompleto"):
            verificar_tablas(self.raiz)


if __name__ == "__main__":
    unittest.main()
