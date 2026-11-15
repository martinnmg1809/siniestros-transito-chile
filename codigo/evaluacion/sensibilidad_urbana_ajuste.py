"""Excluir eventos etiquetados urbanos del entrenamiento; objetivo rural exploratorio."""
import argparse
import json
from pathlib import Path
import subprocess
import gc
import numpy as np
import pandas as pd
from proyecto import RAIZ
from datos_modelado import preparar_experimento, cuarentena_espacial, agrupar_modelado, atributos, expandir_prediccion
from datos_ruta5 import cargar_eventos, grilla_civil
from modelos_conteo import ModeloConteo
from validar_ruta5 import resumen
from verificar_cierre import verificar_tablas
from sensibilidad import zonas, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,default=Path('resultados/sensibilidad/ajuste_rural'))
    a=p.parse_args();verificar_tablas(RAIZ);a.salida.mkdir(parents=True,exist_ok=False)
    inicio=pd.Timestamp.now(tz='UTC').isoformat()
    paths=['config/protocolo_sensibilidad_urbana_ajuste.md','codigo/evaluacion/sensibilidad_urbana_ajuste.py',
        'codigo/evaluacion/sensibilidad.py','codigo/datos/datos_modelado.py','codigo/datos/datos_ruta5.py',
        'codigo/modelos/modelos_conteo.py','codigo/modelos/modelo.py','codigo/evaluacion/validar_ruta5.py',
        'codigo/evaluacion/evaluacion.py','data/siniestros/ruta5_2020_2024.csv.gz',
        'data/cache/clima_ruta5.npz','data/calendario/feriados.json',
        'resultados/modelos/seleccion_temporal.csv','resultados/modelos/metricas.csv']
    hashes={f:sha(f) for f in paths}
    datos=preparar_experimento();original=datos['y']
    eventos,_=cargar_eventos();eventos,_=cuarentena_espacial(eventos)
    _,yr,fuera=grilla_civil(eventos[zonas(eventos.ZONA)=='RURAL'],datos['tramos'])
    assert fuera==0
    yr[:,datos['expo']==0]=0
    datos=dict(datos,y=yr);filas=np.arange(len(datos['tramos']))
    sel=pd.read_csv('resultados/modelos/seleccion_temporal.csv')
    rows=[];fits=[]
    for year in [2022,2023,2024]:
        train=datos['tiempo'].year<year;test=datos['tiempo'].year==year
        assert np.array_equal(yr[:,test],original[:,test]),'Pruebas diferentes; revisar comparabilidad'
        grupos=[agrupar_modelado(datos,filas,x) for x in range(2020,year)]
        kt,yt,et=(np.concatenate([g[i] for g in grupos]) for i in range(3))
        orden=np.argsort(kt);kt,yt,et=kt[orden],yt[orden],et[orden]
        cfg=sel[(sel.anio_prueba==year)&(sel.cohorte=='ruta_completa')&(sel.familia=='Poisson')&(sel.variante=='clima')]
        params=json.loads(cfg.iloc[0].parametros)
        print(f'Ajuste rural {year}: {int(yt.sum())} eventos de entrenamiento, {params}',flush=True)
        m=ModeloConteo('Poisson','clima',params).fit(atributos(kt,datos),yt,et)
        k,_,_=agrupar_modelado(datos,filas,year)
        mu,y,e=expandir_prediccion(k,m.predict_rate(atributos(k,datos)),datos,filas,[year])
        r=resumen(y,mu,e)
        contexto=dict(anio=year,eventos_train_rural=int(yr[:,train].sum()),eventos_train_original=int(original[:,train].sum()),urbanos_excluidos_train=int(original[:,train].sum()-yr[:,train].sum()))
        rows.append(dict(**contexto,modelo='Poisson_clima_rural',**r));fits.append(dict(anio=year,parametros=params,**m.diagnostico))
        f=np.zeros((len(filas),9));f[:,0]=filas
        m1=ModeloConteo('Poisson','espacial',{'l2':1.}).fit(f,yr[:,train].sum(axis=1),np.full(len(filas),datos['expo'][train].sum()))
        rows.append(dict(**contexto,modelo='M1_rural',**resumen(y,m1.predict_rate(f)[:,None]*e,e)))
        print(f'Poisson rural {year}: captura {r["captura5"]:.4%}, O/E {r["observado_esperado"]:.4f}',flush=True)
        del m,m1,grupos,kt,yt,et,mu;gc.collect()
        pd.DataFrame(rows).to_csv(a.salida/'metricas.csv',index=False)
    assert all(sha(f)==h for f,h in hashes.items())
    audit=dict(inicio_utc=inicio,fin_utc=pd.Timestamp.now(tz='UTC').isoformat(),commit_entrada=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        fuentes_sha256=hashes,ajustes=fits,objetivo='Conteos etiquetados RURAL; comparación exploratoria sin cambio de candidata',
        prueba_identica_al_original=True,seleccion_nueva=False,metricas_sha256=sha(a.salida/'metricas.csv'))
    (a.salida/'auditoria.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
