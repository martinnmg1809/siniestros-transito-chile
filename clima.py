#!/usr/bin/env python3
"""
Descarga la serie horaria de precipitación 2020-2024 para las celdas ERA5 que
atraviesa la Ruta 5 Sur, y la guarda como matriz para el modelo.

Truco de eficiencia: la API acepta un rango de fechas por llamada, así que basta
UNA petición por celda para los 5 años (43.848 horas). Pedir día por día costaba
113.212 llamadas y reventaba la cuota; así son 62.

La grilla es de 0,25°, que es la resolución nativa de ERA5: pedir más precisión
sería inventarla.

Salida: clima_ruta5.npz con `precip` (n_celdas x 43848) y el mapa tramo -> celda.
"""
import csv, gzip, json, time, urllib.error, urllib.parse, urllib.request

import numpy as np

GRILLA = 0.25
INICIO, FIN = "2020-01-01", "2024-12-31"
URL = "https://archive-api.open-meteo.com/v1/archive"
KM_MAX, TRAMO = 2200, 5


def celdas_por_tramo():
    """Cada tramo de ruta se asocia a la celda ERA5 donde caen sus siniestros."""
    with gzip.open("ruta5_2020_2024.csv.gz", "rt", encoding="utf-8") as f:
        filas = [r for r in csv.DictReader(f) if r["Ruta"] == "RUTA 5 SUR"]
    acum = {}
    for r in filas:
        try:
            km = float(r["Ubicación"])
        except (TypeError, ValueError):
            continue
        if not (0 < km < KM_MAX):
            continue
        c = (round(float(r["Latitud"]) / GRILLA) * GRILLA,
             round(float(r["longitud"]) / GRILLA) * GRILLA)
        acum.setdefault(int(km // TRAMO) * TRAMO, []).append(c)
    # celda modal de cada tramo
    return {t: max(set(cs), key=cs.count) for t, cs in acum.items()}


def pedir(lat, lon, intentos=5):
    p = urllib.parse.urlencode({
        "latitude": f"{lat:.2f}", "longitude": f"{lon:.2f}",
        "start_date": INICIO, "end_date": FIN,
        "hourly": "precipitation", "timezone": "America/Santiago"})
    for i in range(intentos):
        try:
            with urllib.request.urlopen(f"{URL}?{p}", timeout=180) as r:
                return json.load(r)["hourly"]
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == intentos - 1:
                raise
            time.sleep(2 ** i * 10)


if __name__ == "__main__":
    t2c = celdas_por_tramo()
    celdas = sorted(set(t2c.values()))
    print(f"{len(t2c)} tramos -> {len(celdas)} celdas ERA5 de {GRILLA}°")

    series, tiempo = [], None
    for i, (lat, lon) in enumerate(celdas, 1):
        h = pedir(lat, lon)
        if tiempo is None:
            tiempo = h["time"]
        series.append([0.0 if v is None else v for v in h["precipitation"]])
        print(f"\r  celda {i}/{len(celdas)}", end="", flush=True)
    print()

    P = np.array(series, dtype=np.float32)
    np.savez_compressed(
        "clima_ruta5.npz", precip=P,
        celdas=np.array(celdas), tiempo=np.array(tiempo),
        tramos=np.array(sorted(t2c)),
        idx_celda=np.array([celdas.index(t2c[t]) for t in sorted(t2c)]))
    print(f"guardado: {P.shape[0]} celdas x {P.shape[1]} horas")
    print(f"horas con lluvia >= 0,1 mm: {(P >= 0.1).mean():.1%}")
