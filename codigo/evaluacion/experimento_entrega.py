"""Reejecuta el protocolo completo y añade métricas auxiliares para la entrega.

El ajuste y selección son los del módulo entrenar_comparacion, sin cambiar fuentes,
particiones, grillas ni métricas originales. Un observador del registro calcula
MAE/RMSE y diagnóstico binario desde esas mismas predicciones, en archivos separados.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
import pandas as pd
from threadpoolctl import threadpool_limits
import entrenar_comparacion as entrenamiento
import reajustar_candidato
from metricas_entrega import metricas_conteo, umbral_entrenamiento, diagnostico_binario


def ejecutar(salida):
    salida = Path(salida)
    if salida.exists():
        raise FileExistsError('La corrida requiere una carpeta nueva')
    inicio = time.time()
    metricas, binarias, curvas, umbrales = [], [], [], {}
    registrar_original = entrenamiento.registrar

    def registrar(tablas, anio, cohorte, nombre, particion, y, mu, e):
        registrar_original(tablas, anio, cohorte, nombre, particion, y, mu, e)
        contexto = {'anio_prueba': anio, 'cohorte': cohorte, 'modelo': nombre, 'particion': particion}
        metricas.append({**contexto, **metricas_conteo(y, mu, e)})
        clave = (anio, cohorte, nombre)
        if particion == 'train':
            umbrales[clave] = umbral_entrenamiento(y, mu, e)
        elif clave in umbrales:
            m, puntos = diagnostico_binario(y, mu, e, umbrales[clave],
                curvas=(anio == 2024 and cohorte == 'ruta_completa' and nombre != 'M0'))
            binarias.append({**contexto, **m})
            curvas.extend({**contexto, **p} for p in puntos)
        # Los híbridos no tienen partición train en el protocolo; no inventar un umbral.
        pd.DataFrame(metricas).to_csv(salida/'metricas_conteo_adicionales.csv', index=False)
        pd.DataFrame(binarias).to_csv(salida/'metricas_binarias.csv', index=False)
        pd.DataFrame(curvas).to_csv(salida/'curvas_binarias.csv', index=False)

    anterior = sys.argv
    try:
        entrenamiento.registrar = registrar
        sys.argv = ['entrenar_comparacion', '--salida', str(salida)]
        with threadpool_limits(limits=2):
            entrenamiento.main()
        entrenamiento.registrar = registrar_original
        gc.collect()
        sys.argv = ['reajustar_candidato', '--salida', str(salida)]
        with threadpool_limits(limits=2):
            reajustar_candidato.main()
    finally:
        entrenamiento.registrar = registrar_original
        sys.argv = anterior
    metadata = {'tipo': 'Entrenamiento completo durante la ejecución del notebook',
        'segundos': time.time()-inicio,
        'protocolo': 'Ventanas expansivas 2022/2023/2024; selección anterior a 2024; grilla original',
        'binario_auxiliar': 'Etiqueta y>0 por celda civil existente; score=conteo predicho; umbral p95 train, regla estricta >',
        'seleccion_binaria': False,
        'fuentes_codigo_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
             [Path(__file__), Path('codigo/evaluacion/metricas_entrega.py'), Path(entrenamiento.__file__)]},
        'salidas_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in salida.glob('*.csv')}}
    (salida/'auditoria_entrega.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    print(f'ENTRENAMIENTO_ENTREGA_CORRECTO: {metadata["segundos"]:.1f} s', flush=True)
    return metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida', type=Path, required=True)
    a = p.parse_args()
    ejecutar(a.salida)

if __name__ == '__main__':main()
