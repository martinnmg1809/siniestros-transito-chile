"""La evaluación binaria auxiliar no debe confundir conteos y etiquetas."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import proyecto
from metricas_entrega import diagnostico_binario, metricas_conteo, umbral_entrenamiento

class MetricasEntregaTests(unittest.TestCase):
    def test_conteos_multiples_son_una_celda_positiva(self):
        y=np.array([[0,2,0,1.]])
        mu=np.array([[.1,.8,.7,.2]])
        m,_=diagnostico_binario(y,mu,np.ones(4),.5)
        self.assertEqual((m['tn'],m['fp'],m['fn'],m['tp']),(1,1,1,1))
        self.assertEqual(m['accuracy'],.5);self.assertEqual(m['f1'],.5)
        self.assertEqual(m['prevalencia'],.5)

    def test_umbral_no_alerta_empates_y_excluye_horas_inexistentes(self):
        y=np.array([[0,0,2.]])
        mu=np.array([[.1,.1,999.]])
        e=np.array([1,1,0.])
        t=umbral_entrenamiento(y,mu,e)
        self.assertEqual(t,.1)
        m,_=diagnostico_binario(y,mu,e,t)
        self.assertEqual(m['fraccion_alertada'],0)
        self.assertTrue(np.isnan(m['roc_auc']))

    def test_errores_celda_y_total_turno_tienen_unidades_distintas(self):
        y=np.zeros((2,12));mu=np.ones((2,12))*.5
        m=metricas_conteo(y,mu,np.ones(12))
        self.assertEqual(m['rmse_celda'],.5)
        self.assertEqual(m['rmse_total_turno'],12)
        self.assertEqual(m['mae_total_turno'],12)

if __name__=='__main__':unittest.main()
