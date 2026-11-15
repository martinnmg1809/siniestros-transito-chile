"""Controles de población y recodificación para sensibilidad aislada."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import proyecto
from sensibilidad import zonas, recodificar
from validar_ruta5 import codificar

class SensibilidadTests(unittest.TestCase):
    def test_etiqueta_desconocida_no_se_convierte_en_rural(self):
        self.assertEqual(zonas(pd.Series([' Urbana ', 'RURAL', None, '', 'Rutas'])).tolist(),
                         ['URBANA','RURAL','DESCONOCIDA','DESCONOCIDA','DESCONOCIDA'])

    def test_recodificar_preserva_calendario_tramo_y_periodo_y_no_muta_original(self):
        t=pd.date_range('2020-01-01',periods=6,freq='h')
        p=np.array([[0,.05,.1,.49,.5,1.],[1,.5,.49,.1,.05,0]])
        old,dims=codificar([0,5],t,{},np.digitize(p,[.1,.5]))
        codigo=old.astype(np.int64)*20+3
        datos={'codigo':codigo.copy(),'dims':dims+(20,),'expo':np.ones(6)}
        new=recodificar(datos,p,[.05,1.])
        expected,_=codificar([0,5],t,{},np.digitize(p,[.05,1.]))
        np.testing.assert_array_equal(new['codigo'],expected.astype(np.int64)*20+3)
        np.testing.assert_array_equal(datos['codigo'],codigo)
        np.testing.assert_array_equal(recodificar(datos,p,[.1,.5])['codigo'],codigo)

    def test_faltantes_validos_rechazados_hora_inexistente_sin_exposicion(self):
        d={'codigo':np.array([[20,0]]),'dims':(1,3,20),'expo':np.array([1,0])}
        p=np.array([[np.nan,np.nan]])
        with self.assertRaises(ValueError):recodificar(d,p,[.1,.5])
        p[0,0]=.1
        self.assertEqual(recodificar(d,p,[.05,1.])['codigo'][0,1],0)
        for cuts in [[.5,.1],[0,.5]]:
            with self.assertRaises(ValueError):recodificar(d,p,cuts)

if __name__=='__main__':unittest.main()
