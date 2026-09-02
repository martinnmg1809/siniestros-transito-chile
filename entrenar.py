#!/usr/bin/env python3
"""
Entrena el modelo final sobre TODO el período (2020-2024) y guarda lo necesario
para predecir, en un JSON liviano.

Separado de generar_pagina.py a propósito: entrenar es lento y se hace de vez en
cuando; generar la página es rápido y se hace cada hora.

Salida: modelo_final.json — coeficientes por bloque, geometría de cada tramo y
el mapeo tramo -> celda ERA5 para pedir el pronóstico.
"""
import collections, csv, gzip, json

import numpy as np

from modelo import ajustar
from modelo_clima import CORTES, N_HORAS, cuentas, diseño, grilla_tiempo, agrupar

KM_MAX, TRAMO = 2200, 5


def geometria(tramos):
    """Punto representativo (mediana) de cada tramo, para dibujar la ruta."""
    pts = collections.defaultdict(list)
    with gzip.open("ruta5_2020_2024.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Ruta"] != "RUTA 5 SUR":
                continue
            try:
                km = float(r["Ubicación"])
            except (TypeError, ValueError):
                continue
            if 0 < km < KM_MAX:
                pts[int(km // TRAMO) * TRAMO].append(
                    (float(r["Latitud"]), float(r["longitud"])))
    out = {}
    for t in tramos:
        p = np.array(pts[t])
        out[int(t)] = [float(np.median(p[:, 0])), float(np.median(p[:, 1]))]
    return out


if __name__ == "__main__":
    z = np.load("clima_ruta5.npz", allow_pickle=True)
    tramos = [int(t) for t in z["tramos"]]
    idx_c, P, celdas = z["idx_celda"], z["precip"], z["celdas"]
    fer = json.load(open("feriados.json"))

    hora, dow, mes, pos, _ = grilla_tiempo(fer)
    Y = cuentas(tramos)
    n_tr = len(tramos)
    lluvia = np.digitize(P[idx_c], CORTES).astype(np.int32)

    dims = (n_tr, 24, 7, 12, 4, 3)
    tr_ix = np.repeat(np.arange(n_tr), N_HORAS).reshape(n_tr, N_HORAS)
    cod = (((((tr_ix * 24 + hora) * 7 + dow) * 12 + mes) * 4 + pos) * 3
           + lluvia).ravel()

    todo = np.ones(cod.shape, bool)
    c, y, e = agrupar(cod, Y.ravel().astype(float), todo, int(np.prod(dims)))
    print(f"{len(c):,} celdas agrupadas | {int(y.sum())} siniestros | "
          f"{int(e.sum()):,} horas-tramo")

    b = ajustar(diseño(c, dims, True), y, e)
    off = np.cumsum([0] + list(dims))

    # Conteo esperado por hora en toda la ruta, en condiciones promedio
    basal = float(y.sum() / e.sum() * n_tr)

    json.dump({
        "tramo_km": TRAMO,
        "tramos": tramos,
        "cortes_lluvia": CORTES,
        "basal_ruta_hora": basal,
        "coef": {
            "tramo": b[off[0]:off[1]].tolist(),
            "hora": b[off[1]:off[2]].tolist(),
            "dow": b[off[2]:off[3]].tolist(),
            "mes": b[off[3]:off[4]].tolist(),
            "feriado": b[off[4]:off[5]].tolist(),
            "lluvia": b[off[5]:off[6]].tolist(),
            "intercepto": float(b[-1]),
        },
        "geometria": geometria(tramos),
        "celdas": [[float(a), float(o)] for a, o in celdas],
        "tramo_celda": [int(i) for i in idx_c],
    }, open("modelo_final.json", "w"))

    print(f"basal: {basal:.4f} siniestros/hora en toda la ruta "
          f"({basal * 12:.2f} en 12 h)")
    print("guardado: modelo_final.json")
