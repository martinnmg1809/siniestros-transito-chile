#!/usr/bin/env python3
"""
¿Aporta el clima al modelo de siniestros? Comparación limpia sobre la Ruta 5 Sur.

La validación anterior (validar_clima.py) mostró que ERA5 reproduce mal la etiqueta
`Estado_Atm` de Carabineros (kappa 0,26). Pero esa es una pregunta distinta: aquí no
interesa reproducir la etiqueta, sino saber si la precipitación MEJORA LA PREDICCIÓN
del número de siniestros. Se responde midiendo, no razonando.

A diferencia de modelo.py, aquí la agrupación tiene que incluir el clima, que varía
por tramo y por hora. Se arma la grilla completa (255 tramos x 43.848 horas = 11,2 M
de celdas) con numpy y se colapsa por código entero.

Validación temporal: entrena 2020-2023, prueba 2024.
"""
import csv, datetime, gzip, json

import numpy as np
from scipy import sparse
from scipy.optimize import minimize

from modelo import POS_FERIADO, DOW, ajustar, desvianza, captura

TRAMO, KM_MAX = 5, 2200
INICIO = datetime.date(2020, 1, 1)
N_HORAS = 43848
CORTES = [0.1, 0.5]   # seco / llovizna / lluvia


def grilla_tiempo(fer):
    """Atributos temporales de cada una de las 43.848 horas."""
    dias = N_HORAS // 24
    fechas = [INICIO + datetime.timedelta(days=i) for i in range(dias)]
    hora = np.tile(np.arange(24), dias)
    dow = np.repeat([d.weekday() for d in fechas], 24)
    mes = np.repeat([d.month - 1 for d in fechas], 24)
    pos = np.repeat([POS_FERIADO.index(
        fer.get(d.isoformat(), {}).get("dia", "no")
        if fer.get(d.isoformat(), {}).get("dia", "no") in POS_FERIADO else "no")
        for d in fechas], 24)
    anio = np.repeat([d.year for d in fechas], 24)
    return hora, dow, mes, pos, anio


def cuentas(tramos):
    """Matriz (n_tramos x 43848) con el número de siniestros de cada celda."""
    ix = {t: i for i, t in enumerate(tramos)}
    Y = np.zeros((len(tramos), N_HORAS), dtype=np.int16)
    with gzip.open("ruta5_2020_2024.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Ruta"] != "RUTA 5 SUR" or not r["FECHA"] or not r["Hora_aprox"]:
                continue
            try:
                km = float(r["Ubicación"])
            except (TypeError, ValueError):
                continue
            if not (0 < km < KM_MAX):
                continue
            tr = int(km // TRAMO) * TRAMO
            if tr not in ix:
                continue
            t = (datetime.date.fromisoformat(r["FECHA"]) - INICIO).days * 24 \
                + int(float(r["Hora_aprox"]))
            if 0 <= t < N_HORAS:
                Y[ix[tr], t] += 1
    return Y


def agrupar(codigo, Y, mask, n_cod, exposicion=None):
    if exposicion is not None:
        exposicion = np.asarray(exposicion, float)
        if exposicion.shape != codigo.shape:
            raise ValueError("Exposición incompatible con códigos")
        mask = mask & (exposicion > 0)
    y = np.bincount(codigo[mask], weights=Y[mask], minlength=n_cod)
    e = np.bincount(codigo[mask], weights=None if exposicion is None else exposicion[mask], minlength=n_cod)
    ok = e > 0
    return np.flatnonzero(ok), y[ok], e[ok].astype(float)


def diseño(cods, dims, con_clima):
    """One-hot disperso a partir del código entero, decodificando cada bloque."""
    bloques = list(dims) if con_clima else list(dims[:-1])
    off = np.cumsum([0] + bloques)
    resto, comp = cods.copy(), []
    for d in reversed(dims):
        comp.append(resto % d); resto //= d
    comp = comp[::-1]                       # [tramo, hora, dow, mes, feriado, clima]
    filas, cols = [], []
    for b, c in enumerate(comp[:len(bloques)]):
        filas.append(np.arange(len(cods))); cols.append(off[b] + c)
    X = sparse.csr_matrix(
        (np.ones(len(cods) * len(bloques)),
         (np.concatenate(filas), np.concatenate(cols))),
        shape=(len(cods), off[-1]))
    return sparse.hstack([X, np.ones((len(cods), 1))]).tocsr()


if __name__ == "__main__":
    # La evaluación nueva integra DST, train/prueba y comparación incremental.
    from validar_ruta5 import main
    main()
