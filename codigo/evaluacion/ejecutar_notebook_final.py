"""Ejecuta el único notebook autocontenido con un kernel real y guarda evidencia.

Entrena desde cero por defecto; se necesita CPU y tiempo para la comparación completa.
La carpeta de trabajo puede estar vacía: el notebook incorpora datos y módulos.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from traitlets.config import Config
from proyecto import RAIZ


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ejecutar(archivo, trabajo, salida, html, evidencia, kernel='python3'):
    archivo, trabajo = Path(archivo), Path(trabajo)
    trabajo.mkdir(parents=True, exist_ok=True)
    nb = nbformat.read(archivo, as_version=4)
    nbformat.validate(nb)
    fuentes = json.dumps([(c.cell_type,c.source) for c in nb.cells],ensure_ascii=False)
    inicio=time.time()
    NotebookClient(nb,timeout=7200,kernel_name=kernel,
        resources={'metadata':{'path':str(trabajo)}},allow_errors=False).execute()
    return guardar_ejecucion(nb, trabajo, salida, html, evidencia,
                             segundos=time.time()-inicio, fuentes=fuentes)


def guardar_ejecucion(nb, trabajo, salida, html, evidencia, *, segundos, fuentes=None):
    """Valida y conserva una ejecución real ya completada, sin volver a entrenar."""
    trabajo, salida, html, evidencia = map(Path, (trabajo, salida, html, evidencia))
    if fuentes is None:
        fuentes=json.dumps([(c.cell_type,c.source) for c in nb.cells],ensure_ascii=False)
    codigos=[c for c in nb.cells if c.cell_type=='code']
    if not codigos or any(c.execution_count is None for c in codigos):
        raise RuntimeError('Hay celdas sin ejecutar')
    if any(o.output_type=='error' for c in codigos for o in c.outputs):
        raise RuntimeError('Hay errores en la ejecución')
    texto='\n'.join(o.get('text','') for o in codigos[-1].outputs)
    estados=[o.get('data',{}).get('application/json') for o in codigos[-1].outputs
             if o.get('data',{}).get('application/json') is not None]
    if 'CIERRE_NOTEBOOK_CORRECTO' not in texto or len(estados)!=1:
        raise RuntimeError('No se alcanzó el cierre estructurado del notebook')
    estado=estados[0]
    if not estado.get('entrenamiento_completo') or estado.get('configuraciones_ajustadas')!=60:
        raise RuntimeError('La ejecución no entrenó el protocolo completo')
    nbformat.validate(nb)
    salida.parent.mkdir(parents=True,exist_ok=True);nbformat.write(nb,salida)
    config=Config({'TagRemovePreprocessor':{'enabled':True,'remove_input_tags':{'hide-input'}}})
    cuerpo,_=HTMLExporter(template_name='lab',config=config).from_notebook_node(nb)
    html.parent.mkdir(parents=True,exist_ok=True);html.write_text(cuerpo)
    evidencia.mkdir(parents=True,exist_ok=True)
    resultados=Path(estado['directorio_resultados'])
    nombres=['metricas','bootstrap','calibracion','seleccion_temporal','busqueda_temporal',
             'metricas_conteo_adicionales','metricas_binarias','curvas_binarias',
             'recalibracion_candidato','sensibilidad','cobertura_flujo']
    for nombre in nombres:shutil.copyfile(resultados/(nombre+'.csv'),evidencia/(nombre+'.csv'))
    for nombre in ['auditoria','reajuste','auditoria_entrega','resumen_ejecucion']:
        destino=evidencia/('protocolo/auditoria.json' if nombre=='auditoria' else
            'complemento/auditoria.json' if nombre=='auditoria_entrega' else nombre+'.json')
        destino.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(resultados/(nombre+'.json'),destino)
    registro={'estado':'CORRECTO','fecha_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'segundos':round(segundos,2),'celdas':len(nb.cells),'celdas_codigo':len(codigos),'errores':0,
        'directorio_inicial':str(trabajo),'reproduccion_efectiva':estado,
        'sha256_fuentes_celdas':hashlib.sha256(fuentes.encode()).hexdigest(),
        'sha256_notebook':sha(salida),'sha256_html':sha(html),
        'salidas_sha256':{p.name:sha(p) for p in evidencia.glob('*.csv')},
        'limite':'Comprobación local en kernel real; no se accedió a la cuenta remota de Colab.'}
    (evidencia/'auditoria.json').write_text(json.dumps(registro,ensure_ascii=False,indent=2)+'\n')
    print(f'NOTEBOOK FINAL CORRECTO: {len(codigos)} celdas, entrenamiento completo, {registro["segundos"]:.1f} s')
    return registro


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--notebook',type=Path,default=RAIZ/'notebooks/EntregaFinal_Proyecto_DS.ipynb')
    p.add_argument('--trabajo',type=Path,default=RAIZ)
    p.add_argument('--salida',type=Path)
    p.add_argument('--html',type=Path,default=RAIZ/'notebooks/EntregaFinal_Proyecto_DS.html')
    p.add_argument('--evidencia',type=Path,default=RAIZ/'resultados/entrega_final/ejecucion_autocontenida')
    p.add_argument('--kernel',default='python3')
    a=p.parse_args();ejecutar(a.notebook,a.trabajo,a.salida or a.notebook,a.html,a.evidencia,a.kernel)

if __name__=='__main__':main()
