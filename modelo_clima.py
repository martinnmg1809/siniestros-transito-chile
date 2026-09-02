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


def agrupar(codigo, Y, mask, n_cod):
    y = np.bincount(codigo[mask], weights=Y[mask], minlength=n_cod)
    e = np.bincount(codigo[mask], minlength=n_cod)
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
    z = np.load("clima_ruta5.npz", allow_pickle=True)
    tramos = list(z["tramos"]); idx_c = z["idx_celda"]; P = z["precip"]
    fer = json.load(open("feriados.json"))

    hora, dow, mes, pos, anio = grilla_tiempo(fer)
    Y = cuentas(tramos)
    n_tr = len(tramos)
    print(f"Ruta 5 Sur | {n_tr} tramos x {N_HORAS} horas = {n_tr * N_HORAS:,} celdas")
    print(f"siniestros ubicados en la grilla: {Y.sum()}")

    # clima por tramo-hora, discretizado
    lluvia = np.digitize(P[idx_c], CORTES).astype(np.int32)      # (n_tr, T)
    print(f"reparto de clima: seco {(lluvia == 0).mean():.1%} | "
          f"llovizna {(lluvia == 1).mean():.1%} | lluvia {(lluvia == 2).mean():.1%}\n")

    dims = (n_tr, 24, 7, 12, 4, 3)
    tr_ix = np.repeat(np.arange(n_tr), N_HORAS).reshape(n_tr, N_HORAS)
    cod = ((((tr_ix * 24 + hora) * 7 + dow) * 12 + mes) * 4 + pos) * 3 + lluvia
    n_cod = int(np.prod(dims))

    cod, Yf = cod.ravel(), Y.ravel().astype(float)
    es_train = np.tile(anio <= 2023, n_tr)
    es_test = np.tile(anio == 2024, n_tr)

    res = {}
    for nombre, con_clima in [("sin clima", False), ("con clima", True)]:
        c_tr, y_tr, e_tr = agrupar(cod, Yf, es_train, n_cod)
        c_te, y_te, e_te = agrupar(cod, Yf, es_test, n_cod)
        b = ajustar(diseño(c_tr, dims, con_clima), y_tr, e_tr)
        mu = np.exp(diseño(c_te, dims, con_clima) @ b + np.log(e_te))
        res[nombre] = (y_te, mu, e_te, b)
        print(f"{nombre}: {len(c_tr):,} celdas agrupadas en entrenamiento")

    y_te, _, e_te, _ = res["sin clima"]
    d0 = desvianza(y_te, e_te * (y_te.sum() / e_te.sum()))
    print(f"\n{'modelo':<34}{'desvianza':>12}{'mejora':>9}"
          f"{'top 5%':>9}{'top 10%':>9}{'top 20%':>9}")
    for nombre, (y, mu, e, _) in res.items():
        d = desvianza(y, mu)
        c = captura(y, mu, e)
        print(f"{nombre:<34}{d:>12,.0f}{(1 - d / d0) * 100:>8.1f}%"
              + "".join(f"{v:>8.1%} " for _, v in c))

    b = res["con clima"][3]
    ef = b[sum(dims[:5]) - 0:]  # bloque de clima
    off = np.cumsum([0] + list(dims))
    ef = b[off[5]:off[5] + 3]
    print("\nEfecto multiplicativo de la lluvia (1,00 = seco)")
    for i, n in enumerate(["seco", "llovizna (0,1-0,5 mm/h)", "lluvia (>0,5 mm/h)"]):
        print(f"  {n:<26}{np.exp(ef[i] - ef[0]):.3f}")
