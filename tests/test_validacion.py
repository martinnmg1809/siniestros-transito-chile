import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluacion import captura, curva_captura, pesos_seleccion, captura_turnos, bootstrap_pareado, desvianza
from modelo import ajustar, agrupar
from datos_ruta5 import cargar_eventos, referencia_entrenamiento, exposicion_civil
from clima_utc import alinear_utc
from flujo_vehicular import normalizar_ramas, exposicion_vehiculo_km
from feriados import validar_cobertura


class CapturaTests(unittest.TestCase):
    def test_constante_diagonal_e_invariante_al_orden(self):
        y, e = np.array([0, 12, 2, 8]), np.array([1., 3., 8., 2.])
        for orden in (np.arange(4), np.array([3, 0, 2, 1])):
            self.assertTrue(np.allclose([v for _, v in captura(y[orden], e[orden] * .1, e[orden])], [.05, .1, .2]))

    def test_frontera_exacta_y_empates_uniformes(self):
        e, mu = np.array([2., 8., 10.]), np.array([4., 16., 5.])
        w = pesos_seleccion(mu, e, .25)
        self.assertAlmostEqual(w @ e, .25 * e.sum())
        self.assertTrue(np.allclose(w, [.5, .5, 0]))

    def test_agrupar_no_cambia_captura(self):
        y = np.array([2., 0., 1., 0.])
        mu = np.array([3., 3., 1., 1.])
        a = captura(y, mu, np.ones(4), (.1, .25, .5, .8))
        b = captura(np.array([2., 1.]), np.array([6., 2.]), np.array([2., 2.]), (.1, .25, .5, .8))
        self.assertTrue(np.allclose(a, b))

    def test_curva_y_pesos_concuerdan(self):
        y, mu, e = np.array([4, 2, 8]), np.array([6., 2., 1.]), np.array([2., 1., 5.])
        for f in [0, .05, .33, 1]:
            c = captura(y, mu, e, (f,))[0][1]
            self.assertAlmostEqual(c, pesos_seleccion(mu, e, f) @ y / y.sum())

    def test_sin_eventos_e_insumos_invalidos(self):
        self.assertTrue(np.isnan(captura(np.zeros(2), np.ones(2), np.ones(2))[0][1]))
        for y, mu, e in [([1], [-1], [1]), ([1], [1], [0]), ([1], [np.nan], [1])]:
            with self.assertRaises(ValueError):
                captura(y, mu, e)

    def test_turnos_presupuesto_no_se_transfiere(self):
        y = np.array([[10, 0], [0, 2]])
        mu = np.array([[10, 0], [0, 2]])
        r = captura_turnos(y, mu, fraccion=.5, horas=1)
        self.assertTrue(np.allclose(r["cubiertos"], [10, 2]))
        uniforme = captura_turnos(y, np.ones((2, 2)), fraccion=.5, horas=1)
        self.assertTrue(np.allclose(uniforme["cubiertos"], [5, 1]))

    def test_bootstrap_pareado_y_exposicion(self):
        y, e = np.array([4., 1., 3., 2.]), np.array([1., 2., 1., 2.])
        modelos = {"base": e, "mejor": np.array([4., 1., 4., 1.])}
        r = bootstrap_pareado(y, modelos, [0, 0, 1, 1], fraccion=.5, replicas=100, expo=e)["mejor"]
        dif = captura(y, modelos["mejor"], e, (.5,))[0][1] - .5
        self.assertAlmostEqual(r["diferencia_pp"], dif * 100)
        self.assertLessEqual(r["ic95_inf_pp"], r["ic95_sup_pp"])

    def test_desvianza_con_ceros(self):
        self.assertEqual(desvianza([0, 2], [0, 2]), 0)
        self.assertTrue(np.isinf(desvianza([1], [0])))


class DatosYAjusteTests(unittest.TestCase):
    def test_tasa_poisson_con_exposicion(self):
        x = sparse.csr_matrix(np.ones((3, 1)))
        b, diag = ajustar(x, [1, 2, 3], [2, 3, 7], devolver_diagnostico=True)
        self.assertAlmostEqual(np.exp(b[0]), .5, places=5)
        self.assertTrue(diag["convergio"])

    def test_optimizar_sin_convergencia_no_devuelve_coeficientes(self):
        class Fallo:
            success, x, fun, message, nit = False, np.array([0.]), 1., "límite", 500
        with patch("modelo.minimize", return_value=Fallo()):
            with self.assertRaises(RuntimeError):
                ajustar(sparse.csr_matrix([[1.]]), [1], [1])

    def test_anios_no_contiguos_no_agregan_exposicion_intermedia(self):
        _, _, e = agrupar([], {}, [2020, 2022], [0])
        self.assertEqual(e.sum(), (366 + 365) * 24)

    def test_referencia_ignora_observaciones_futuras(self):
        d, auditoria = cargar_eventos()
        self.assertEqual(auditoria["registros_validos"], 14425)
        a = referencia_entrenamiento(d)
        b = referencia_entrenamiento(d.loc[d.anio.le(2021)])
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(len(a), 255)
        self.assertTrue(a.loc[a.tramo.isin([1055, 1130]), "geometria_interpolada"].all())


class MeteorologiaTests(unittest.TestCase):
    def test_no_inferir_feriados_de_2026_con_calendario_2024(self):
        with self.assertRaises(ValueError):
            validar_cobertura(["2026-11-12"])

    def test_pronostico_null_no_se_convierte_en_seco(self):
        import riesgo
        ahora = pd.Timestamp.now(tz="UTC").floor("h")
        t = pd.date_range(ahora, periods=24, freq="h").strftime("%Y-%m-%dT%H:%M").tolist()
        respuesta = {"hourly": {"time": t, "precipitation": [None] * 24}}
        with patch("riesgo.urllib.request.urlopen") as llamada, patch("riesgo.json.load", return_value=respuesta):
            with self.assertRaises(ValueError):
                riesgo.pronostico([[0, 0]])

    def respuesta(self, inicio, fin):
        t = pd.date_range(inicio, fin + " 23:00", freq="h", tz="UTC")
        return {"hourly": {"time": t.strftime("%Y-%m-%dT%H:%M").tolist(), "precipitation": [1.] * len(t)}}

    def test_cambio_horario_no_se_desplaza_por_posicion(self):
        r = self.respuesta("2024-04-06", "2024-04-08")
        t, lluvia, e = alinear_utc(r, "2024-04-06", "2024-04-07")
        self.assertEqual(e.sum(), 49)
        self.assertEqual((e == 2).sum(), 1)
        self.assertTrue(np.allclose(lluvia, 1))
        r = self.respuesta("2024-09-07", "2024-09-09")
        _, lluvia, e = alinear_utc(r, "2024-09-07", "2024-09-08")
        self.assertEqual(e.sum(), 47)
        self.assertEqual((e == 0).sum(), 1)
        self.assertTrue(np.isnan(lluvia[e == 0]).all())
        self.assertTrue(np.array_equal(e, exposicion_civil(pd.date_range("2024-09-07", "2024-09-08 23:00", freq="h"))))

    def test_null_no_es_seco(self):
        r = self.respuesta("2024-01-01", "2024-01-03")
        r["hourly"]["precipitation"][12] = None
        with self.assertRaises(ValueError):
            alinear_utc(r, "2024-01-01", "2024-01-02")


class FlujoTests(unittest.TestCase):
    def test_respeta_anio_del_registro_y_no_suma_ramas(self):
        f = {"attributes": {"OBJECTID": 1, "ESTACION_DE_CONTROL": "10-1", "ANO": 2022,
                             "ROL_RAMA_1": "RUTA 5", "TMDA_RAMA_1": 100,
                             "ROL_RAMA_2": "RUTA 5", "TMDA_RAMA_2": 120},
             "geometry": {"x": -73, "y": -42}}
        with tempfile.TemporaryDirectory() as td:
            Path(td, "capa_2.json").write_text(json.dumps({"features": [f]}))
            r = normalizar_ramas(td)
            self.assertEqual(r.anio_medicion.tolist(), [2022, 2022])
            self.assertEqual(r.tmda.tolist(), [100, 120])

    def test_exposicion_no_rellena_tramos_sin_datos(self):
        tabla = pd.DataFrame({"tramo": [0], "anio_objetivo": [2024], "tmda": [240],
                              "disponible_desde": ["2023-12-01"], "fuente": ["MOP"], "metodo": ["validado"]})
        e = exposicion_vehiculo_km(tabla, pd.date_range("2024-01-01", periods=2, freq="h"), [0, 5], "2023-12-31")
        self.assertTrue(np.allclose(e[0], 50))
        self.assertTrue(np.isnan(e[1]).all())
        tabla["disponible_desde"] = "2024-01-02"
        with self.assertRaises(ValueError):
            exposicion_vehiculo_km(tabla, ["2024-01-01"], [0], "2023-12-31")

    def test_anexo_real_dgc_unidades_y_celda(self):
        from flujo_concesiones import extraer, FUENTES
        archivo = Path(__file__).resolve().parents[1] / "data/fuentes/dgc/anexo_2024_4t.xls"
        if not archivo.exists():
            self.skipTest("Fuente descargable no presente")
        d = extraer(archivo, "2024_4t", FUENTES["2024_4t"])
        r = d.loc[d.contrato.eq("Santiago-Talca y Acceso Sur a Santiago") & d.anio.eq(2024) & d.trimestre.eq(1)].iloc[0]
        self.assertEqual(r.transacciones_trimestre, 25229771)
        self.assertEqual(r.celda_total, "CI24")
        self.assertEqual(r.dias, 91)
        self.assertFalse(r.disponibilidad_historica_acreditada)


if __name__ == "__main__":
    unittest.main()
