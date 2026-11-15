"""Sensibilidad urbana de ranking fijo y umbrales de lluvia, sin reselección."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import time
import joblib
import numpy as np
import pandas as pd
from proyecto import RAIZ
from datos_ruta5 import cargar_eventos, referencia_entrenamiento, grilla_civil
from datos_modelado import preparar_experimento, cuarentena_espacial, agrupar_modelado, atributos, expandir_prediccion
from clima_utc import cargar_cache
from modelos_conteo import ModeloConteo
from validar_ruta5 import resumen
from evaluacion import pesos_seleccion, captura_turnos, bootstrap_pareado
from verificar_cierre import verificar_tablas

ESCENARIOS = {'actual': [.1, .5], 'A': [.05, .5], 'B': [.1, 1.]}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def zonas(s):
    z = s.fillna('').astype(str).str.strip().str.upper()
    return z.where(z.isin(['RURAL', 'URBANA']), 'DESCONOCIDA')


def recodificar(datos, precip, cortes):
    if len(cortes) != 2 or not 0 < cortes[0] < cortes[1]:
        raise ValueError('Cortes inválidos')
    p = np.asarray(precip)
    if p.shape != datos['codigo'].shape or not np.isfinite(p[:, datos['expo'] > 0]).all():
        raise ValueError('Lluvia faltante o forma incompatible')
    if (p[:, datos['expo'] > 0] < 0).any():
        raise ValueError('Lluvia negativa')
    lluvia = np.digitize(p, cortes)
    lluvia[:, datos['expo'] == 0] = 0
    periodos = datos['dims'][-1]
    if datos['dims'][-2] != 3:
        raise ValueError('Codificación incompatible')
    nuevo = dict(datos)
    viejo = (datos['codigo'] // periodos) % 3
    nuevo['codigo'] = datos['codigo'] + (lluvia - viejo) * periodos
    return nuevo


def top_turnos(mu, n=12):
    totales = mu.reshape(mu.shape[0], -1, 12).sum(axis=2)
    return np.argsort(-totales, axis=0, kind='stable')[:n]


def verificar_metricas(r, tabla, anio, modelo):
    t = tabla[(tabla.anio_prueba == anio) & (tabla.modelo == modelo) &
              (tabla.cohorte == 'ruta_completa') & (tabla.particion == 'prueba')]
    if len(t) != 1:
        raise ValueError('Referencia de métricas no única')
    for k, valor in r.items():
        np.testing.assert_allclose(valor, t.iloc[0][k], rtol=1e-8, atol=1e-10, err_msg=f'{anio} {modelo} {k}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, default=Path('resultados/sensibilidad'))
    args = parser.parse_args()
    verificar_tablas(RAIZ)
    args.salida.mkdir(parents=True, exist_ok=False)
    inicio = pd.Timestamp.now(tz='UTC').isoformat()
    fuentes = ['config/protocolo_sensibilidad.md', 'codigo/evaluacion/sensibilidad.py',
               'codigo/datos/datos_modelado.py', 'codigo/modelos/modelos_conteo.py',
               'codigo/modelos/modelo.py', 'codigo/evaluacion/evaluacion.py',
               'codigo/evaluacion/validar_ruta5.py', 'codigo/datos/datos_ruta5.py',
               'data/siniestros/ruta5_2020_2024.csv.gz', 'data/cache/clima_ruta5.npz',
               'data/calendario/feriados.json', 'resultados/modelos/metricas.csv',
               'resultados/modelos/seleccion_temporal.csv']
    for anio in [2022, 2023, 2024]:
        fuentes.append(f'resultados/modelos/artefactos/ruta_completa_Poisson_clima_{anio}.joblib')
    hashes = {f: sha(f) for f in fuentes}
    datos = preparar_experimento()
    eventos, _ = cargar_eventos(); eventos, _ = cuarentena_espacial(eventos)
    eventos['zona_analisis'] = zonas(eventos.ZONA)
    ref = referencia_entrenamiento(eventos)
    cache = cargar_cache()
    index = {tuple(c): i for i, c in enumerate(cache['celdas'])}
    ix = [index[tuple(c)] for c in np.round(ref[['lat', 'lon']].to_numpy() / .25) * .25]
    precip = cache['precip'][ix]
    assert np.array_equal(recodificar(datos, precip, ESCENARIOS['actual'])['codigo'], datos['codigo'])
    filas = np.arange(len(datos['tramos']))
    tabla = pd.read_csv('resultados/modelos/metricas.csv')
    selec = pd.read_csv('resultados/modelos/seleccion_temporal.csv')
    counts, urban, boot, metricas, ranking, cambios, fits = [], [], [], [], [], [], []
    ys = {}
    for zona in ['RURAL', 'URBANA', 'DESCONOCIDA']:
        ev = eventos[eventos.zona_analisis == zona]
        _, yz, fuera = grilla_civil(ev, datos['tramos'])
        for year in range(2020, 2025):
            cols = datos['tiempo'].year == year
            counts.append(dict(anio=year,zona=zona,registros=int(ev.anio.eq(year).sum()),
                eventos_evaluables=int(yz[:,cols][:,datos['expo'][cols]>0].sum()),
                excluidos_dst=int(yz[:,cols][:,datos['expo'][cols]==0].sum())))
        if fuera:
            raise ValueError('Eventos de zona fuera del dominio')
        yz[:,datos['expo']==0] = 0
        ys[zona] = yz
    assert np.array_equal(sum(ys.values()), datos['y'])
    pd.DataFrame(counts).to_csv(args.salida/'poblacion_zona.csv',index=False)
    for year in [2022,2023,2024]:
        cols = np.flatnonzero(datos['tiempo'].year == year)
        k, _, _ = agrupar_modelado(datos,filas,year)
        model = joblib.load(f'resultados/modelos/artefactos/ruta_completa_Poisson_clima_{year}.joblib')
        mu,y,e = expandir_prediccion(k,model.predict_rate(atributos(k,datos)),datos,filas,[year])
        base = resumen(y,mu,e); verificar_metricas(base,tabla,year,'Poisson_clima')
        metricas.append(dict(escenario='actual',anio=year,**base))
        sel = selec[(selec.anio_prueba==year)&(selec.cohorte=='ruta_completa')&(selec.familia=='Poisson')&(selec.variante=='clima')]
        params = json.loads(sel.iloc[0].parametros)
        assert model.parametros == params
        # Reconstruir M1 espacial con su especificación original, no seleccionar.
        train = datos['tiempo'].year < year
        fb = np.zeros((len(filas),9)); fb[:,0]=filas
        m1 = ModeloConteo('Poisson','espacial',{'l2':1.0}).fit(fb,datos['y'][:,train].sum(axis=1),np.full(len(filas),datos['expo'][train].sum()))
        mu1 = m1.predict_rate(fb)[:,None] * e
        verificar_metricas(resumen(y,mu1,e),tabla,year,'M1')
        ef = np.broadcast_to(e,y.shape); valid=ef.ravel()>0
        preds={'M1':mu1.ravel()[valid], 'Poisson_clima':mu.ravel()[valid]}
        pesos={n:pesos_seleccion(p,ef.ravel()[valid],.05) for n,p in preds.items()}
        bloques=np.broadcast_to(np.arange(len(cols))//168,y.shape).ravel()[valid]
        for zona, yy in [('TOTAL',y)]+[(z,v[:,cols].astype(float)) for z,v in ys.items()]:
            total=yy.sum()
            for n, pred in [('M1',mu1),('Poisson_clima',mu)]:
                cap=pesos[n]@yy.ravel()[valid]/total if total else np.nan
                turn= captura_turnos(yy,pred)['cubiertos'].sum()/total if total else np.nan
                urban.append(dict(anio=year,zona=zona,modelo=n,eventos=int(total),captura5=cap,captura5_turno=turn))
            if total:
                b=bootstrap_pareado(yy.ravel()[valid],preds,bloques,replicas=2000,expo=ef.ravel()[valid])['Poisson_clima']
                boot.append(dict(anio=year,zona=zona,**b))
        top0=top_turnos(mu)
        for nombre in ['A','B']:
            alter=recodificar(datos,precip,ESCENARIOS[nombre])
            original=(datos['codigo'][:,cols]//20)%3; nuevo=(alter['codigo'][:,cols]//20)%3
            cambios.append(dict(anio=year,escenario=nombre,fraccion_horas_reales_categoria_distinta=float(((original!=nuevo)*e).sum()/(len(filas)*e.sum()))))
            grupos=[agrupar_modelado(alter,filas,a) for a in range(2020,year)]
            kt,yt,et=(np.concatenate([g[i] for g in grupos]) for i in range(3))
            orden=np.argsort(kt); kt,yt,et=kt[orden],yt[orden],et[orden]
            t0=time.monotonic()
            print(f'Ajustando {nombre} prueba {year} {params}',flush=True)
            fitted=ModeloConteo('Poisson','clima',params).fit(atributos(kt,alter),yt,et)
            ke,_,_=agrupar_modelado(alter,filas,year)
            alt,_,_=expandir_prediccion(ke,fitted.predict_rate(atributos(ke,alter)),alter,filas,[year])
            result=resumen(y,alt,e)
            metricas.append(dict(escenario=nombre,anio=year,**result))
            top=top_turnos(alt)
            coincidencia=np.array([len(set(top0[:,i])&set(top[:,i]))/12 for i in range(top.shape[1])])
            ranking.append(dict(anio=year,escenario=nombre,tramos_por_turno=12,coincidencia_media=coincidencia.mean(),coincidencia_minima=coincidencia.min()))
            fits.append(dict(anio=year,escenario=nombre,parametros=params,**fitted.diagnostico))
            print(f'{nombre} {year}: captura {result["captura5"]:.4%}; {time.monotonic()-t0:.1f}s',flush=True)
            del alter,grupos,kt,yt,et,fitted,alt;gc.collect()
        for name,rows in [('urbana',urban),('urbana_ic',boot),('lluvia',metricas),('ranking',ranking),('categorias',cambios)]:
            pd.DataFrame(rows).to_csv(args.salida/f'{name}.csv',index=False)
    assert all(sha(f)==h for f,h in hashes.items()),'Cambió un insumo durante la corrida'
    audit=dict(inicio_utc=inicio,fin_utc=pd.Timestamp.now(tz='UTC').isoformat(),commit_entrada=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        escenarios=ESCENARIOS,fuentes_sha256=hashes,ajustes=fits,controles_metricas_originales='Poisson y M1, nueve métricas por año, rtol=1e-8 atol=1e-10',
        urbana='ranking fijo; presupuesto en todos los tramos; no ajuste rural',lluvia='sin selección de umbral; no reemplaza candidata',
        salidas_sha256={p.name:sha(p) for p in sorted(args.salida.glob('*.csv'))},versiones={'numpy':np.__version__,'pandas':pd.__version__})
    (args.salida/'auditoria.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print('Sensibilidad terminada',args.salida,flush=True)

if __name__=='__main__':
    main()
