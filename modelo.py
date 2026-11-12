#!/usr/bin/env python3
"""
Modelo Poisson de siniestros por tramo x hora en la Ruta 5 Sur.

El objetivo es estimar el conteo esperado por tramo y hora para priorizar vigilancia.
Se elige regresión por ese objetivo; la rareza del evento no impide matemáticamente
usar clasificación. Sin flujo vehicular, las tasas son por hora, no por conductor.

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
from evaluacion import captura, curva_captura, desvianza

TRAMO = 5
KM_MAX = 2200
ANIOS_TRAIN = (2020, 2021, 2022, 2023)
ANIO_TEST = 2024
DOW = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
POS_FERIADO = ["no", "inicio", "intermedio", "final"]


# ---------------------------------------------------------------- datos

def cargar():
    from datos_ruta5 import cargar_eventos
    datos, _ = cargar_eventos(tramo_km=TRAMO)
    fer = json.load(open("feriados.json"))
    out = [(int(r.tramo), r.fecha.date().isoformat(), int(r.hora)) for r in datos.itertuples()]
    return out, fer


def tipo_dia(fecha, fer):
    d = datetime.date.fromisoformat(fecha)
    pos = fer.get(fecha, {}).get("dia", "no") or "no"
    return d.weekday(), d.month, POS_FERIADO.index(pos if pos in POS_FERIADO else "no")


def agrupar(sinis, fer, anios, tramos):
    """Conteos agrupados y exposición horaria, incluyendo cambios de horario."""
    import pandas as pd
    dias = collections.Counter()
    for anio in sorted(set(anios)):
        horas = pd.date_range(f"{anio}-01-01", f"{anio + 1}-01-01",
                              tz="America/Santiago", freq="h", inclusive="left")
        for h in horas:
            dias[(h.hour,) + tipo_dia(h.date().isoformat(), fer)] += 1

    cuenta = collections.Counter()
    for km, fecha, hora in sinis:
        if int(fecha[:4]) in anios:
            cuenta[(km, hora) + tipo_dia(fecha, fer)] += 1

    claves, y, expo = [], [], []
    for tr in tramos:
        for (h, dow, mes, f), n in dias.items():
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

def ajustar(X, y, expo, l2=1.0, devolver_diagnostico=False):
    y, expo = np.asarray(y, float), np.asarray(expo, float)
    if (X.shape[0] != len(y) or y.shape != expo.shape or y.ndim != 1
            or not np.isfinite(y).all() or not np.isfinite(expo).all()
            or (y < 0).any() or (expo <= 0).any() or y.sum() <= 0
            or not np.isfinite(l2) or l2 < 0):
        raise ValueError("Datos o exposición inválidos para el ajuste Poisson")
    logE = np.log(expo)

    def nll(b):
        eta = X @ b + logE
        mu = np.exp(eta)
        return mu.sum() - y @ eta + l2 * b[:-1] @ b[:-1]

    def grad(b):
        eta = X @ b + logE
        g = X.T @ (np.exp(eta) - y)
        g[:-1] += 2 * l2 * b[:-1]
        return g

    b0 = np.zeros(X.shape[1])
    b0[-1] = np.log(max(y.sum(), 1) / expo.sum())
    r = minimize(nll, b0, jac=grad, method="L-BFGS-B",
                 options={"maxiter": 1000, "maxfun": 1500, "ftol": 1e-10})
    if not r.success or not np.isfinite(r.x).all() or not np.isfinite(r.fun):
        raise RuntimeError(f"Poisson no convergió: {r.message} (iteraciones={r.nit})")
    info = {"convergio": bool(r.success), "iteraciones": int(r.nit),
            "objetivo": float(r.fun), "mensaje": str(r.message)}
    return (r.x, info) if devolver_diagnostico else r.x


# ---------------------------------------------------------------- main

if __name__ == "__main__":
    TRAMO = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sinis, fer = cargar()
    pasado = [s[0] for s in sinis if int(s[1][:4]) in ANIOS_TRAIN]
    tramos = list(range(min(pasado), max(pasado) + TRAMO, TRAMO))
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
