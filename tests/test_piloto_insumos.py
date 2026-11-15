"""Errores reales de fuentes deben impedir una emisión, sin imputar condiciones."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import proyecto
from insumos_piloto import verificar_corte, alinear_pronostico, calendario, capturar

class InsumosPilotoTests(unittest.TestCase):
    def test_captura_posterior_y_vieja_rechazadas(self):
        r={'captura_inicio_utc':'2026-11-14T20:00Z','captura_fin_utc':'2026-11-14T20:01Z'}
        for emision in ['2026-11-14T20:00:30Z','2026-11-14T23:00Z']:
            with self.assertRaises(ValueError):verificar_corte([r],emision,120)
        verificar_corte([r],'2026-11-14T20:02Z',120)

    def test_pronostico_incompleto_o_nulo_impide_predecir(self):
        t=pd.date_range('2026-11-14T22:00Z',periods=12,freq='h')
        base={'latitude':-35.,'longitude':-71.,'utc_offset_seconds':0,
              'hourly_units':{'precipitation':'mm'}}
        for horas,lluvia in [(t,[None]*12),(t[:-1],[0.]*11)]:
            d={**base,'hourly':{'time':[x.isoformat() for x in horas],'precipitation':lluvia}}
            with patch('insumos_piloto.leer',return_value=d):
                with self.assertRaises(ValueError):alinear_pronostico(Path('.'),[{'celdas_solicitadas':[[-35.,-71.]]}],[[-35.,-71.]],t)

    def test_calendario_fuera_de_cobertura_y_feriado_no_validado(self):
        c={'zona':'America/Santiago','periodos_festivos_validados':False,'margen_dias_feriado':2}
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'cal.csv';f.write_text('fecha,dia\n2026-11-14,no\n')
            with self.assertRaises(ValueError):calendario(Path(td),[],f,pd.date_range('2026-11-16T12:00Z',periods=12,freq='h'),c)
            with patch('insumos_piloto.leer',return_value=[{'countryCode':'CL','date':'2026-11-15'}]):
                with self.assertRaises(ValueError):calendario(Path(td),[{'anio':2026}],f,pd.date_range('2026-11-14T12:00Z',periods=2,freq='h'),c)

    def test_falla_proveedor_no_se_sustituye_por_lluvia_cero(self):
        with tempfile.TemporaryDirectory() as td,patch('insumos_piloto.pedir',side_effect=TimeoutError('Proveedor no responde')):
            with self.assertRaises(TimeoutError):capturar(Path(td)/'captura',[[-35.,-71.]],{'zona':'America/Santiago','meteorologia':'ecmwf_ifs025'})

if __name__=='__main__':unittest.main()
