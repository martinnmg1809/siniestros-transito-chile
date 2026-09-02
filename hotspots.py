#!/usr/bin/env python3
"""
Prueba de concepto de puntos calientes: agrega los siniestros de la Ruta 5 Sur
en tramos de N kilómetros y los ordena por frecuencia y por letalidad.

Uso:  python3 hotspots.py [tramo_km]
"""
import collections, csv, gzip, sys

TRAMO = int(sys.argv[1]) if len(sys.argv) > 1 else 5
KM_MAX = 2200  # largo aproximado de la Ruta 5; sobre esto el campo viene sucio


def km(fila):
    try:
        v = float(fila["Ubicación"])
    except (ValueError, TypeError):
        return None
    return v if 0 < v < KM_MAX else None


with gzip.open("ruta5_2020_2024.csv.gz", "rt", encoding="utf-8") as f:
    filas = [r for r in csv.DictReader(f) if r["Ruta"] == "RUTA 5 SUR"]

siniestros, fallecidos = collections.Counter(), collections.Counter()
validos = 0
for r in filas:
    k = km(r)
    if k is None:
        continue
    validos += 1
    tramo = int(k // TRAMO) * TRAMO
    siniestros[tramo] += 1
    fallecidos[tramo] += int(float(r["FALLECIDOS"] or 0))

print(f"Ruta 5 Sur: {len(filas)} siniestros, {validos} con km válido "
      f"({100 * validos / len(filas):.1f}%)")
print(f"Tramos de {TRAMO} km con al menos un siniestro: {len(siniestros)}\n")

print(f"{'tramo (km)':>14} {'siniestros':>11} {'fallecidos':>11}")
for tramo, n in siniestros.most_common(15):
    print(f"{tramo:>6}-{tramo + TRAMO:<7} {n:>11} {fallecidos[tramo]:>11}")
