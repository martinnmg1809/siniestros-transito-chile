#!/usr/bin/env python3
"""Convierte la salida de descargar_conaset.py a CSV comprimido (más liviano y usable en pandas)."""
import csv, datetime, gzip, json, sys

entrada = sys.argv[1] if len(sys.argv) > 1 else "ruta5_2020_2025.json"
salida = sys.argv[2] if len(sys.argv) > 2 else "ruta5_2020_2024.csv.gz"

filas = json.load(open(entrada))
if not filas:
    raise SystemExit("archivo vacío")

# ArcGIS entrega las fechas como epoch en milisegundos
CAMPOS_FECHA = {"FECHA", "Fecha"}


def normalizar(fila):
    fila = dict(fila)
    for c in CAMPOS_FECHA & fila.keys():
        ms = fila[c]
        fila[c] = "" if ms is None else datetime.datetime.fromtimestamp(
            ms / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
    return fila


with gzip.open(salida, "wt", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(normalizar(x) for x in filas)

print(f"OK: {len(filas)} filas -> {salida}")
