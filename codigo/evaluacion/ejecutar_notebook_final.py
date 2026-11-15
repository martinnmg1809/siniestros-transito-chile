"""Ejecuta el notebook final con un kernel real y registra su evidencia.

No permite errores de celdas. Exporta HTML y conserva manifiesto de ejecución.
La ejecución normal reutiliza modelos; reentrenar exige editar el parámetro del notebook.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import time
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from proyecto import RAIZ


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ejecutar(archivo, raiz, salida, html, auditoria, kernel='python3', modo='local'):
    archivo, raiz = Path(archivo), Path(raiz)
    nb = nbformat.read(archivo, as_version=4)
    nbformat.validate(nb)
    inicio = time.time()
    fuentes_celdas = json.dumps([(c.cell_type, c.source) for c in nb.cells], ensure_ascii=False)
    hash_fuentes = hashlib.sha256(fuentes_celdas.encode()).hexdigest()
    entradas = {str(p.relative_to(raiz)): sha(p) for directorio in
                ['codigo', 'config', 'data/siniestros', 'resultados']
                for p in sorted((raiz / directorio).rglob('*'))
                if p.is_file() and p.suffix in {'.py', '.csv', '.gz', '.json', '.md', '.png'}
                and not any(x in p.parts for x in ['artefactos', 'piloto', 'entrega_final', '__pycache__'])}
    cliente = NotebookClient(nb, timeout=600, kernel_name=kernel,
                            resources={'metadata': {'path': str(raiz)}}, allow_errors=False)
    cliente.execute()
    nbformat.validate(nb)
    codigos = [c for c in nb.cells if c.cell_type == 'code']
    if not codigos or any(c.execution_count is None for c in codigos):
        raise RuntimeError('Hay celdas de código sin ejecutar')
    if any(o.output_type == 'error' for c in codigos for o in c.outputs):
        raise RuntimeError('Notebook con errores')
    ultima = '\n'.join(o.get('text', '') for o in codigos[-1].outputs)
    if 'CIERRE_NOTEBOOK_CORRECTO' not in ultima:
        raise RuntimeError('No se alcanzó el cierre del notebook')
    for nombre, digest in entradas.items():
        if sha(raiz / nombre) != digest:
            raise RuntimeError(f'Cambió la evidencia durante la ejecución: {nombre}')
    estados = [o.get('data', {}).get('application/json') for o in codigos[-1].outputs
               if o.get('data', {}).get('application/json') is not None]
    if len(estados) != 1:
        raise RuntimeError('Falta el registro estructurado del nivel de reproducción')
    estado_reproduccion = estados[0]
    if modo == 'publico' and not estado_reproduccion['artefactos'].startswith('pendiente'):
        raise RuntimeError('La copia pública contiene artefactos locales; revisar el aislamiento')
    salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, salida)
    exportador = HTMLExporter(template_name='lab')
    cuerpo, _ = exportador.from_notebook_node(nb)
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text(cuerpo)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=raiz,
                            capture_output=True, text=True).stdout.strip() or 'copia sin Git'
    registro = {'modo_solicitado': modo, 'estado': 'CORRECTO', 'commit_entrada': commit,
        'python_ejecutor': platform.python_version(), 'segundos': round(time.time() - inicio, 2),
        'celdas': len(nb.cells), 'celdas_codigo': len(codigos), 'celdas_con_error': 0,
        'kernel': kernel, 'reproduccion_efectiva': estado_reproduccion,
        'sha256_fuentes_celdas': hash_fuentes, 'librerias_notebook': {n: importlib.metadata.version(n)
            for n in ['nbformat', 'nbclient', 'nbconvert', 'ipykernel']},
        'entradas_sha256': entradas,
        'sha256_notebook_ejecutado': sha(salida), 'sha256_html': sha(html),
        'seleccion_cientifica_alterada': False,
        'limite': 'El modo público comprueba evidencia publicada; no equivale a reconstruir artefactos ausentes.'}
    auditoria.parent.mkdir(parents=True, exist_ok=True)
    auditoria.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + '\n')
    print(f'Notebook CORRECTO: {len(codigos)} celdas de código, sin errores, {registro["segundos"]} s')
    return registro


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--notebook', type=Path, default=RAIZ / 'notebooks/EntregaFinal_Proyecto_DS.ipynb')
    p.add_argument('--raiz', type=Path, default=RAIZ)
    p.add_argument('--salida', type=Path)
    p.add_argument('--html', type=Path, default=RAIZ / 'notebooks/EntregaFinal_Proyecto_DS.html')
    p.add_argument('--auditoria', type=Path, default=RAIZ / 'resultados/entrega_final/auditoria.json')
    p.add_argument('--kernel', default='python3')
    p.add_argument('--modo', choices=['local', 'publico'], default='local',
                   help='Etiqueta de la copia ejecutada; la presencia de insumos se determina en el notebook.')
    a = p.parse_args()
    ejecutar(a.notebook, a.raiz, a.salida or a.notebook, a.html, a.auditoria, a.kernel, a.modo)

if __name__ == '__main__':
    main()
