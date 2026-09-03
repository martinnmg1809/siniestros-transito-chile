#!/usr/bin/env python3
"""
Descarga la precipitación horaria 2020-2024 para todas las celdas ERA5 que tocan
las rutas seleccionadas.

Las celdas se deduplican globalmente: rutas vecinas comparten celdas (la 68 y la 5
Norte cerca de Santiago, por ejemplo), así que 211 referencias se reducen bastante.
Una llamada por celda cubre los cinco años completos.

Salida: clima_rutas.npz
"""
import json, time, urllib.error, urllib.parse, urllib.request

import numpy as np

URL = "https://archive-api.open-meteo.com/v1/archive"
INICIO, FIN = "2020-01-01", "2024-12-31"


def pedir(lat, lon, intentos=6):
    p = urllib.parse.urlencode({
        "latitude": f"{lat:.2f}", "longitude": f"{lon:.2f}",
        "start_date": INICIO, "end_date": FIN,
        "hourly": "precipitation", "timezone": "America/Santiago"})
    for i in range(intentos):
        try:
            with urllib.request.urlopen(f"{URL}?{p}", timeout=180) as r:
                return json.load(r)["hourly"]["precipitation"]
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if i == intentos - 1:
                raise
            time.sleep(min(2 ** i * 5, 90))


if __name__ == "__main__":
    datos = json.load(open("rutas_datos.json"))
    todas = sorted({tuple(c) for d in datos.values() for c in d["celdas"]})
    print(f"{sum(len(d['celdas']) for d in datos.values())} referencias -> "
          f"{len(todas)} celdas únicas")

    # caché incremental en disco: la descarga tarda ~15 min y así es resumible
    import os
    CACHE = "clima_celdas.jsonl"
    series = {}
    if os.path.exists(CACHE):
        for linea in open(CACHE):
            k, v = json.loads(linea)
            series[k] = v
        print(f"  {len(series)} celdas ya en caché")

    with open(CACHE, "a") as cache:
        for i, (la, lo) in enumerate(todas, 1):
            k = f"{la},{lo}"
            if k in series:
                continue
            series[k] = pedir(la, lo)
            cache.write(json.dumps([k, series[k]]) + "\n")
            cache.flush()
            print(f"  {i}/{len(todas)}", flush=True)

    claves = [f"{la},{lo}" for la, lo in todas]
    P = np.array([[0.0 if v is None else v for v in series[k]] for k in claves],
                 dtype=np.float32)
    np.savez_compressed("clima_rutas.npz", precip=P, claves=np.array(claves))
    print(f"guardado: {P.shape[0]} celdas x {P.shape[1]} horas · "
          f"lluvia >= 0,1 mm en {(P >= 0.1).mean():.1%} de las horas")
