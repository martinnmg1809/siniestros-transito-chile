"""Reproduce emisiones locales y genera un panel fechado sin emitir pronósticos nuevos."""
import argparse
import html
import json
import os
from pathlib import Path
import pandas as pd
from insumos_piloto import utc
from piloto_12h import reproducir


def revisar(raiz, salida, ahora):
    ahora=utc(ahora)
    salida.mkdir(parents=True,exist_ok=True)
    rows=[]
    for archivo in sorted(raiz.glob('20*/auditoria.json')):
        carpeta=archivo.parent
        reproducir(carpeta)
        a=json.loads(archivo.read_text())
        inicio,fin=utc(a['inicio_utc']),utc(a['fin_utc'])
        if ahora < utc(a['emision_utc']):
            raise ValueError('Emisión posterior al instante de revisión')
        estado='ventana terminada' if ahora>=fin else ('ventana en curso' if ahora>=inicio else 'ventana por comenzar')
        rows.append({'emision_utc':a['emision_utc'],'inicio_local':a['inicio_local'],
            'fin_local':a['fin_local'],'estado_temporal':estado,'reproduccion':'correcta',
            'evaluacion_observada':'pendiente; no hay observaciones completas acreditadas',
            'esperados':a['esperados_total'],'tramos_priorizados':a['tramos_seleccionados'],
            'reporte':os.path.relpath(carpeta/'reporte.html',salida)})
    if not rows:
        raise ValueError('No se encontraron emisiones con auditoría; no se genera un panel vacío')
    pd.DataFrame(rows).to_csv(salida/'registro.csv',index=False)
    tarjetas=[]
    for r in reversed(rows):
        tarjetas.append(f"<article><h2>{html.escape(r['estado_temporal'])}</h2><p>{html.escape(r['inicio_local'])} → {html.escape(r['fin_local'])}</p><p>{r['esperados']:.3f} siniestros esperados en toda la ruta · {r['tramos_priorizados']} tramos priorizados</p><p>Reproducción comprobada. Evaluación con siniestros observados pendiente.</p><a href='{html.escape(r['reporte'],quote=True)}'>Ver reporte de esta emisión</a></article>")
    pagina="""<!doctype html><html lang='es'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Piloto experimental · Ruta 5 Sur</title><style>body{font:17px system-ui;max-width:1000px;margin:40px auto;padding:0 24px;color:#173549;background:#f5f8fb}article{background:white;border:1px solid #ccdbe4;border-radius:14px;padding:20px;margin:20px 0}a{color:#075cad}.nota{background:#fff1c9;padding:18px;border-radius:10px}h1{font-size:28px}</style><h1>Predicción dinámica de siniestros en carreteras chilenas</h1><p class='nota'>Piloto experimental de Ruta 5 Sur. Las emisiones son predicciones congeladas; una ventana terminada no implica que haya sido evaluada. Los reportes históricos no son alertas vigentes.</p>"""
    pagina+=f'<p>Estado revisado a las {html.escape(ahora.isoformat())}. Panel estático: volver a ejecutar la revisión para actualizar estados.</p>'+''.join(tarjetas)+'</html>'
    (salida/'index.html').write_text(pagina)
    print('Panel local:',salida/'index.html')
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--emisiones',type=Path,default=Path('resultados/piloto'))
    p.add_argument('--salida',type=Path,default=Path('resultados/piloto/panel'))
    a=p.parse_args()
    revisar(a.emisiones,a.salida,pd.Timestamp.now(tz='UTC'))

if __name__=='__main__':main()
