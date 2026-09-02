#!/usr/bin/env python3
"""
Modelo Poisson de siniestros por tramo x hora en la Ruta 5 Sur.

Un siniestro en un tramo-hora concreto es un evento de probabilidad ~0,13 %, así que
no tiene sentido clasificar "hay/no hay accidente". Lo que se modela es la TASA
esperada de siniestros por tramo y hora, que es lo que permite decir "este tramo, este
viernes a las 20:00, tiene 4x el riesgo basal".

Estructura: en vez de materializar los 11,2 millones de celdas (tramo x fecha x hora),
se agrupa por (tramo, hora, día de semana, mes, tipo de feriado) con un offset igual al
número de días que caen en cada combinación. Es exactamente el mismo modelo, con tres
órdenes de magnitud menos de filas.

Validación TEMPORAL: entrena 2020-2023, prueba 2024. Nunca aleatoria — hay
autocorrelación y una partición al azar infla los resultados.

Uso:  python3 modelo.py [tramo_km]
"""
import collections, csv, datetime, gzip, json, sys

import numpy as np
from scipy import sparse
from scipy.optimize import minimize

TRAMO = int(sys.argv[1]) if len(sys.argv) > 1 else 5
KM_MAX = 2200
ANIOS_TRAIN = (2020, 2021, 2022, 2023)
ANIO_TEST = 2024
DOW = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
POS_FERIADO = ["no", "inicio", "intermedio", "final"]


# ---------------------------------------------------------------- datos

def cargar():
    with gzip.open("ruta5_2020_2024.csv.gz", "rt", encoding="utf-8") as f:
        filas = [r for r in csv.DictReader(f) if r["Ruta"] == "RUTA 5 SUR"]
    fer = json.load(open("feriados.json"))
    out = []
    for r in filas:
        try:
            km = float(r["Ubicación"])
        except (TypeError, ValueError):
            continue
        if not (0 < km < KM_MAX) or not r["FECHA"] or not r["Hora_aprox"]:
            continue
        out.append((int(km // TRAMO) * TRAMO, r["FECHA"], int(float(r["Hora_aprox"]))))
    return out, fer


def tipo_dia(fecha, fer):
    d = datetime.date.fromisoformat(fecha)
    pos = fer.get(fecha, {}).get("dia", "no") or "no"
    return d.weekday(), d.month, POS_FERIADO.index(pos if pos in POS_FERIADO else "no")


def agrupar(sinis, fer, anios, tramos):
    """-> (claves, y, exposicion_dias) agregando por (tramo, hora, dow, mes, feriado)."""
    dias = collections.Counter()
    d, fin = datetime.date(min(anios), 1, 1), datetime.date(max(anios), 12, 31)
    while d <= fin:
        dias[tipo_dia(d.isoformat(), fer)] += 1
        d += datetime.timedelta(days=1)

    cuenta = collections.Counter()
    for km, fecha, hora in sinis:
        if int(fecha[:4]) in anios:
            cuenta[(km, hora) + tipo_dia(fecha, fer)] += 1

    claves, y, expo = [], [], []
    for tr in tramos:
        for h in range(24):
            for (dow, mes, f), n in dias.items():
                claves.append((tr, h, dow, mes, f))
                y.append(cuenta.get((tr, h, dow, mes, f), 0))
                expo.append(n)
    return claves, np.array(y, float), np.array(expo, float)


def diseño(claves, tramos, con_tiempo=True):
    """One-hot disperso. con_tiempo=False deja solo el efecto de tramo (mapa estático)."""
    idx_tr = {t: i for i, t in enumerate(tramos)}
    bloques = [len(tramos)] + ([24, 7, 12, 4] if con_tiempo else [])
    off = np.cumsum([0] + bloques)
    filas, cols = [], []
    for i, (tr, h, dow, mes, f) in enumerate(claves):
        vals = [off[0] + idx_tr[tr]]
        if con_tiempo:
            vals += [off[1] + h, off[2] + dow, off[3] + mes - 1, off[4] + f]
        for c in vals:
            filas.append(i); cols.append(c)
    X = sparse.csr_matrix((np.ones(len(filas)), (filas, cols)),
                          shape=(len(claves), off[-1]))
    return sparse.hstack([X, np.ones((len(claves), 1))]).tocsr()


# ---------------------------------------------------------------- ajuste

def ajustar(X, y, expo, l2=1.0):
    logE = np.log(expo)

    def nll(b):
        eta = X @ b + logE
        eta = np.clip(eta, -30, 30)
        mu = np.exp(eta)
        return mu.sum() - y @ eta + l2 * b[:-1] @ b[:-1]

    def grad(b):
        eta = np.clip(X @ b + logE, -30, 30)
        g = X.T @ (np.exp(eta) - y)
        g[:-1] += 2 * l2 * b[:-1]
        return g

    b0 = np.zeros(X.shape[1])
    b0[-1] = np.log(max(y.sum(), 1) / expo.sum())
    r = minimize(nll, b0, jac=grad, method="L-BFGS-B",
                 options={"maxiter": 500, "maxfun": 600})
    return r.x


def desvianza(y, mu):
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(y > 0, y * np.log(y / mu), 0.0)
    return 2 * (t - (y - mu)).sum()


def captura(y, mu, expo, fracs=(0.05, 0.10, 0.20)):
    """
    Si dedicas el X% de las horas-tramo disponibles a vigilar las de mayor riesgo,
    ¿qué % de los siniestros reales cubres?

    Se ordena por TASA (mu/exposición), no por conteo esperado, y el eje X se acumula
    en exposición y no en número de celdas: las celdas agrupadas representan distinta
    cantidad de días, y sin esto el 5% de celdas no es el 5% del tiempo.
    """
    o = np.argsort(-(mu / expo))
    cx = np.cumsum(expo[o]) / expo.sum()
    cy = np.cumsum(y[o]) / y.sum()
    return [(f, cy[np.searchsorted(cx, f)]) for f in fracs]


# ---------------------------------------------------------------- main

if __name__ == "__main__":
    sinis, fer = cargar()
    tramos = sorted({s[0] for s in sinis})
    print(f"Ruta 5 Sur | tramos de {TRAMO} km | {len(sinis)} siniestros | "
          f"{len(tramos)} tramos\n")

    k_tr, y_tr, e_tr = agrupar(sinis, fer, ANIOS_TRAIN, tramos)
    k_te, y_te, e_te = agrupar(sinis, fer, (ANIO_TEST,), tramos)
    print(f"entrenamiento {ANIOS_TRAIN[0]}-{ANIOS_TRAIN[-1]}: {len(k_tr):,} celdas "
          f"agrupadas, {int(y_tr.sum())} siniestros")
    print(f"prueba {ANIO_TEST}:            {len(k_te):,} celdas agrupadas, "
          f"{int(y_te.sum())} siniestros\n")

    modelos = {}
    # B0: tasa constante
    mu0 = e_te * (y_tr.sum() / e_tr.sum())
    modelos["constante"] = mu0
    # B1: solo tramo (equivale al mapa de hotspots estático)
    Xs_tr, Xs_te = diseño(k_tr, tramos, False), diseño(k_te, tramos, False)
    bs = ajustar(Xs_tr, y_tr, e_tr)
    modelos["solo tramo (mapa estático)"] = np.exp(Xs_te @ bs + np.log(e_te))
    # B2: tramo + hora + día + mes + feriado
    Xf_tr, Xf_te = diseño(k_tr, tramos, True), diseño(k_te, tramos, True)
    bf = ajustar(Xf_tr, y_tr, e_tr)
    modelos["tramo + hora + día + mes + feriado"] = np.exp(Xf_te @ bf + np.log(e_te))

    print(f"{'modelo':<36}{'desvianza':>12}{'  mejora':>10}")
    d0 = desvianza(y_te, modelos["constante"])
    for nom, mu in modelos.items():
        d = desvianza(y_te, mu)
        print(f"{nom:<36}{d:>12,.0f}{(1 - d / d0) * 100:>9.1f}%")

    print(f"\nCurva de captura en {ANIO_TEST} "
          f"(% de siniestros reales cubiertos al vigilar el N% de celdas más riesgosas)")
    print(f"{'modelo':<36}{'top 5%':>10}{'top 10%':>10}{'top 20%':>10}")
    for nom, mu in modelos.items():
        c = captura(y_te, mu, e_te)
        print(f"{nom:<36}" + "".join(f"{v:>9.1%} " for _, v in c))

    # Efectos estimados, en múltiplos del basal
    n_tr = len(tramos)
    ef = {"hora": bf[n_tr:n_tr + 24], "dow": bf[n_tr + 24:n_tr + 31],
          "mes": bf[n_tr + 31:n_tr + 43], "feriado": bf[n_tr + 43:n_tr + 47]}
    print("\nEfectos multiplicativos (1,00 = celda promedio)")
    print("  hora:   ", " ".join(f"{h:02d}h={np.exp(v - ef['hora'].mean()):.2f}"
                                 for h, v in enumerate(ef["hora"]) if h % 3 == 0))
    print("  día:    ", " ".join(f"{DOW[i]}={np.exp(v - ef['dow'].mean()):.2f}"
                                 for i, v in enumerate(ef["dow"])))
    print("  feriado:", " ".join(f"{POS_FERIADO[i]}={np.exp(v - ef['feriado'][0]):.2f}"
                                 for i, v in enumerate(ef["feriado"])))
    np.save("coef_modelo.npy", bf)
    json.dump({"tramos": tramos, "tramo_km": TRAMO}, open("modelo_meta.json", "w"))
