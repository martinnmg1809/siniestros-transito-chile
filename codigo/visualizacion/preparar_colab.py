"""Prepara un ZIP local con el proyecto y originales, y una copia del notebook para Colab.

El ZIP no se publica en Git: incluye fuentes y joblib locales del equipo.
No descarga, ajusta ni modifica modelos, y no cambia el notebook final original.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from proyecto import RAIZ

SUBIR = '''# 1. Subir y verificar el ZIP complementario. Solo se solicita una vez por sesión.
import sys, os, json, hashlib, zipfile
from pathlib import Path
try:
    from google.colab import files
except ImportError:
    files = None

if files is not None:
    RAIZ_COLAB = Path("/content/siniestros_colab")
    if not (RAIZ_COLAB / "MANIFIESTO_COLAB.json").is_file():
        subidos = files.upload()
        zips = [Path(n) for n in subidos if n.lower().endswith(".zip")]
        if len(zips) != 1:
            raise ValueError("Selecciona únicamente Siniestros_Colab_Completo.zip")
        with zipfile.ZipFile(zips[0]) as z:
            for nombre in z.namelist():
                p = Path(nombre)
                if p.is_absolute() or ".." in p.parts:
                    raise ValueError("ZIP con rutas no admitidas")
            z.extractall(RAIZ_COLAB)
    manifiesto = json.loads((RAIZ_COLAB / "MANIFIESTO_COLAB.json").read_text())
    for nombre, digest in manifiesto["archivos_sha256"].items():
        if hashlib.sha256((RAIZ_COLAB / nombre).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Archivo distinto del paquete: {nombre}")
    os.chdir(RAIZ_COLAB)
    print("Proyecto listo:", Path.cwd())
    print("Archivos verificados:", len(manifiesto["archivos_sha256"]))
else:
    print("Preparación Colab omitida: se ejecuta en un entorno local ya preparado.")
'''
INSTALAR = '''# 2. Instalar únicamente las dependencias científicas necesarias.
import importlib.metadata as md
import subprocess, sys
if files is not None:
    if not (3, 11) <= sys.version_info[:2] <= (3, 13):
        raise RuntimeError("Usa un entorno de Python 3.11, 3.12 o 3.13 para estas versiones.")
    esperadas = {"numpy": ("numpy", "2.2.3"), "pandas": ("pandas", "2.2.3"),
        "scipy": ("scipy", "1.14.1"), "scikit-learn": ("sklearn", "1.6.1"),
        "matplotlib": ("matplotlib", "3.9.4"), "joblib": ("joblib", "1.6.0"),
        "xlrd": ("xlrd", "2.0.1")}
    cambiar = []
    for nombre, (modulo, version) in esperadas.items():
        try:
            actual = md.version(nombre)
        except md.PackageNotFoundError:
            actual = None
        if actual != version:
            cambiar.append((nombre, modulo))
    cargados = [modulo for _, modulo in cambiar if modulo in sys.modules]
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "-r", "requirements-colab.txt"], check=True)
    if cargados:
        raise RuntimeError("Instalación terminada. Reinicia la sesión de Python (sin desconectar y eliminar), "
            "y vuelve a ejecutar desde la primera celda. Los archivos de /content permanecen. "
            "Módulos que requieren recargarse: " + ", ".join(cargados))
    print("Dependencias listas. Continúa con las celdas originales del notebook.")
else:
    print("Se conserva el entorno local; no se instala ningún paquete.")
'''
INTRO = '''# Preparación para Google Colab

Esta es una copia del notebook final con dos celdas iniciales de preparación.
El contenido científico posterior coincide con el notebook final original.

1. Conéctate a una sesión de **CPU** y ejecuta la celda siguiente. Selecciona
   **Siniestros_Colab_Completo.zip**, preparado por el equipo.
2. Ejecuta la celda de dependencias. Si solicita reiniciar Python, reinicia la
   sesión de Python sin eliminar la máquina y vuelve a ejecutar desde arriba.
3. Continúa con **Ejecutar todas**. El cierre debe mostrar
   `CIERRE_NOTEBOOK_CORRECTO` y confirmar originales y bootstrap reproducidos.

El ZIP contiene código, tablas, modelos, clima, calendario, anexos y una emisión
histórica. No necesitas subir los archivos uno por uno ni montar todo tu Drive.
Los joblib del paquete son las copias originales del equipo. No se activan descargas
ni entrenamientos completos al leer el documento. No se verificó esta ejecución
en tu sesión remota; el paquete se comprobó en un directorio aislado local.
'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def preparar(salida):
    nb = json.loads((RAIZ / 'notebooks/EntregaFinal_Proyecto_DS.ipynb').read_text())
    for celda in nb['cells']:
        if celda['cell_type'] == 'code':
            celda['outputs'] = []
            celda['execution_count'] = None
    def celda(tipo, texto, identificador):
        c = {'cell_type': tipo, 'metadata': {}, 'source': texto.splitlines(keepends=True), 'id': identificador}
        if tipo == 'code':
            c.update(execution_count=None, outputs=[])
        return c
    nb['cells'] = [celda('markdown', INTRO, 'colab-preparacion'),
        celda('code', SUBIR, 'colab-archivos'), celda('code', INSTALAR, 'colab-dependencias')] + nb['cells']
    destino_nb = RAIZ / 'notebooks/EntregaFinal_Proyecto_DS_Colab.ipynb'
    destino_nb.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + '\n')
    archivos = subprocess.check_output(['git', 'ls-files', '-z'], cwd=RAIZ).decode().split('\0')
    incluidos = {n for n in archivos if n and not n.startswith('resultados/entrega_final/colab/')
                 and n != 'notebooks/EntregaFinal_Proyecto_DS_Colab.ipynb'}
    incluidos.update(['requirements-colab.txt', 'codigo/visualizacion/preparar_colab.py', 'notebooks/COLAB.md'])
    incluidos.update(['data/cache/clima_ruta5.npz', 'data/calendario/feriados.json',
        'data/fuentes/dgc/anexo_2023_4t.xls', 'data/fuentes/dgc/anexo_2024_4t.xls'])
    for nombre in ['ruta_completa_Poisson_clima_2023.joblib', 'ruta_completa_Poisson_clima_2024.joblib',
                   'candidato_reajustado2020_2024.joblib', 'candidato_reajustado2020_2024_recalibrado_con2024.joblib']:
        incluidos.add('resultados/modelos/artefactos/' + nombre)
    with (RAIZ / 'resultados/entrega_final/piloto_documentado.csv').open() as f:
        piloto = next(csv.DictReader(f))
    for carpeta in [piloto['carpeta_emision'], piloto['carpeta_capturas']]:
        incluidos.update(str(p.relative_to(RAIZ)) for p in sorted((RAIZ / carpeta).rglob('*')) if p.is_file())
    faltantes = [n for n in incluidos if not (RAIZ / n).is_file()]
    if faltantes:
        raise FileNotFoundError(f'Faltan insumos del paquete: {faltantes}')
    manifiesto = {'base_git': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=RAIZ, text=True).strip(),
        'alcance': 'Proyecto y fuentes locales para ejecutar la entrega; piloto histórico sin evaluación observada',
        'archivos_sha256': {n: sha(RAIZ / n) for n in sorted(incluidos)}}
    salida.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(salida, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for nombre in sorted(incluidos):
            z.write(RAIZ / nombre, nombre)
        z.writestr('MANIFIESTO_COLAB.json', json.dumps(manifiesto, ensure_ascii=False, indent=2) + '\n')
    auditoria = {'base_git': manifiesto['base_git'], 'archivos': len(incluidos), 'bytes_zip': salida.stat().st_size,
        'sha256_zip': sha(salida), 'sha256_notebook_colab': sha(destino_nb),
        'archivos_sha256': manifiesto['archivos_sha256'], 'ejecutado_en_colab_remoto': False,
        'comprobacion': 'Pendiente de validar extracción y ejecución aislada local; ver comprobaciones.md'}
    (salida.parent / 'auditoria.json').write_text(json.dumps(auditoria, ensure_ascii=False, indent=2) + '\n')
    print(f'ZIP local: {salida} ({salida.stat().st_size / 1048576:.2f} MiB, {len(incluidos)} archivos)')
    print('Notebook para Colab:', destino_nb)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida', type=Path, default=RAIZ / 'resultados/entrega_final/colab/Siniestros_Colab_Completo.zip')
    a = p.parse_args()
    preparar(a.salida)

if __name__ == '__main__':
    main()
