#!/usr/bin/env python3
"""
Entrena un modelo Poisson por ruta y valida temporalmente (2020-2023 -> 2024).

Cada ruta lleva su propio modelo: la estructura espacial no se comparte entre
carreteras y agruparlas obligaría a un efecto de ruta que no aporta nada.

Se DESCARTA toda ruta cuyo modelo completo no supere al MAPA ESTÁTICO fuera de
muestra. No basta con ganarle al azar: si sumar hora, día, feriado y clima no
mejora la captura respecto de usar solo la ubicación, esa capa está aportando
ruido, y presentarla como predicción dinámica sería falso. Con 500-700
siniestros repartidos en 20 tramos eso pasa con facilidad.

Salida: modelos.json (solo las rutas que pasan) y un informe por consola.
"""
import datetime, json

import numpy as np
from scipy import sparse

from modelo import POS_FERIADO, ajustar, desvianza, captura

INICIO = datetime.date(2020, 1, 1)
N_HORAS = 43848
CORTES = [0.1, 0.5]
DIMS_T = (24, 7, 12, 4, 3)          # hora, día, mes, feriado, lluvia


def grilla_tiempo(fer):
    dias = N_HORAS // 24
    fechas = [INICIO + datetime.timedelta(days=i) for i in range(dias)]
    pos = []
    for d in fechas:
        p = fer.get(d.isoformat(), {}).get("dia", "no")
        pos.append(POS_FERIADO.index(p if p in POS_FERIADO else "no"))
    return (np.tile(np.arange(24), dias),
            np.repeat([d.weekday() for d in fechas], 24),
            np.repeat([d.month - 1 for d in fechas], 24),
            np.repeat(pos, 24),
            np.repeat([d.year for d in fechas], 24))


def diseño(cods, dims, n_bloques):
    off = np.cumsum([0] + list(dims[:n_bloques]))
    resto, comp = cods.copy(), []
    for d in reversed(dims):
        comp.append(resto % d); resto //= d
    comp = comp[::-1]
    filas = np.tile(np.arange(len(cods)), n_bloques)
    cols = np.concatenate([off[b] + comp[b] for b in range(n_bloques)])
    X = sparse.csr_matrix((np.ones(len(filas)), (filas, cols)),
                          shape=(len(cods), off[-1]))
    return sparse.hstack([X, np.ones((len(cods), 1))]).tocsr()


def agrupar(cod, Y, mask, n_cod):
    y = np.bincount(cod[mask], weights=Y[mask], minlength=n_cod)
    e = np.bincount(cod[mask], minlength=n_cod)
    ok = e > 0
    return np.flatnonzero(ok), y[ok], e[ok].astype(float)


if __name__ == "__main__":
    datos = json.load(open("rutas_datos.json"))
    fer = json.load(open("feriados.json"))
    cuentas = np.load("cuentas.npz")
    z = np.load("clima_rutas.npz", allow_pickle=True)
    Pmap = {k: i for i, k in enumerate(z["claves"])}
    P = z["precip"]

    hora, dow, mes, pos, anio = grilla_tiempo(fer)
    salida = {}
    print(f"{'ruta':<14}{'n':>6}{'tramos':>8}{'2024':>7}"
          f"{'mejora':>9}{'top5%':>8}{'estático':>10}  veredicto")

    for nombre, d in datos.items():
        Y = cuentas[nombre].astype(float)
        nT = len(d["tramos"])
        idx = np.array([Pmap[f"{c[0]},{c[1]}"] for c in d["celdas"]])
        lluvia = np.digitize(P[idx][np.array(d["tramo_celda"])], CORTES).astype(np.int32)

        dims = (nT,) + DIMS_T
        tr_ix = np.repeat(np.arange(nT), N_HORAS).reshape(nT, N_HORAS)
        cod = (((((tr_ix * 24 + hora) * 7 + dow) * 12 + mes) * 4 + pos) * 3
               + lluvia).ravel()
        n_cod = int(np.prod(dims))
        Yf = Y.ravel()
        tr = np.tile(anio <= 2023, nT); te = np.tile(anio == 2024, nT)

        c_tr, y_tr, e_tr = agrupar(cod, Yf, tr, n_cod)
        c_te, y_te, e_te = agrupar(cod, Yf, te, n_cod)
        if y_te.sum() < 40:
            print(f"{nombre:<14}{d['n']:>6}{nT:>8}{int(y_te.sum()):>7}"
                  f"{'—':>9}{'—':>8}{'—':>10}  muy pocos siniestros en 2024")
            continue

        b = ajustar(diseño(c_tr, dims, 6), y_tr, e_tr)
        mu = np.exp(diseño(c_te, dims, 6) @ b + np.log(e_te))
        b_s = ajustar(diseño(c_tr, dims, 1), y_tr, e_tr)      # solo tramo
        mu_s = np.exp(diseño(c_te, dims, 1) @ b_s + np.log(e_te))

        d0 = desvianza(y_te, e_te * (y_tr.sum() / e_tr.sum()))
        mejora = 1 - desvianza(y_te, mu) / d0
        cap = captura(y_te, mu, e_te)[0][1]
        cap_s = captura(y_te, mu_s, e_te)[0][1]

        # El criterio no es "mejor que el azar" sino "mejor que el mapa estático".
        # Si añadir hora, día, feriado y clima no mejora la captura fuera de muestra,
        # esa capa está metiendo ruido y presentarla como predicción sería falso.
        pasa = mejora > 0.005 and cap > cap_s
        motivo = ("ok" if pasa else
                  "el modelo completo no supera al mapa estático")
        print(f"{nombre:<14}{d['n']:>6}{nT:>8}{int(y_te.sum()):>7}"
              f"{mejora:>8.1%}{cap:>8.1%}{cap_s:>10.1%}  {motivo}")
        if not pasa:
            continue

        off = np.cumsum([0] + list(dims))
        salida[nombre] = {
            **{k: d[k] for k in ("nombre", "tramo_km", "tramos", "geometria",
                                 "celdas", "tramo_celda", "ciudades", "regiones", "n",
                                 "banda_km", "bandas", "banda_ix", "regiones_banda")},
            "cortes_lluvia": CORTES,
            "basal_ruta_hora": float(y_tr.sum() / e_tr.sum() * nT),
            "validacion": {"mejora": round(float(mejora), 4),
                           "captura5": round(float(cap), 4),
                           "captura5_estatico": round(float(cap_s), 4),
                           "siniestros_2024": int(y_te.sum())},
            "coef": {"tramo": b[off[0]:off[1]].tolist(),
                     "hora": b[off[1]:off[2]].tolist(),
                     "dow": b[off[2]:off[3]].tolist(),
                     "mes": b[off[3]:off[4]].tolist(),
                     "feriado": b[off[4]:off[5]].tolist(),
                     "lluvia": b[off[5]:off[6]].tolist(),
                     "intercepto": float(b[-1])},
        }

    json.dump(salida, open("modelos.json", "w"), ensure_ascii=False)
    print(f"\n{len(salida)} de {len(datos)} rutas pasan la validación -> modelos.json")
