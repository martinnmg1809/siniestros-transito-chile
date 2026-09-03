#!/usr/bin/env python3
"""
Selecciona y limpia las rutas que tienen datos suficientes para modelar.

Dos problemas reales de los datos de CONASET que se resuelven aquí:

1. El campo `Ubicación` (kilometraje) mezcla unidades: en varias rutas una fracción
   de los registros viene en METROS. En la Ruta 68 eso produce valores de 84.300
   que en realidad son el km 84,3. Pero la Ruta 5 Sur sí llega legítimamente al km
   1.226, así que dividir por 1000 a ciegas la arruinaría. La regla se decide POR
   RUTA eligiendo la transformación que maximiza la correlación entre el km
   declarado y la posición geográfica real proyectada sobre el eje de la ruta.

2. Quedan outliers sueltos: se recortan por rango robusto sobre el km ya corregido.

Salida: rutas.json con la configuración de cada ruta viable.
"""
import collections, json, math, sys

import numpy as np

MIN_POR_TRAMO = 18      # densidad mínima; la Ruta 5 Sur tiene ~58
MIN_TRAMOS = 8          # menos que esto no da un mapa interesante
MIN_CORR = 0.90         # el km tiene que describir la posición sobre la ruta


def eje(la, lo):
    """Proyección 1D sobre el eje principal de la ruta (km equivalentes)."""
    X = np.c_[(lo - lo.mean()) * math.cos(math.radians(la.mean())), la - la.mean()]
    u = np.linalg.svd(X - X.mean(0), full_matrices=False)[2][0]
    return X @ u


def corr(km, la, lo):
    if len(km) < 50:
        return 0.0
    c = np.corrcoef(km, eje(la, lo))[0, 1]
    return 0.0 if np.isnan(c) else abs(c)


def limpiar(v):
    """Devuelve (registros limpios, regla aplicada, correlación final)."""
    base = [x for x in v
            if isinstance(x.get("Ubicación"), (int, float)) and x["Ubicación"] > 0
            and x.get("Latitud") and x.get("longitud")]
    if len(base) < 50:
        return [], "sin datos", 0.0
    km = np.array([x["Ubicación"] for x in base], float)
    la = np.array([x["Latitud"] for x in base])
    lo = np.array([x["longitud"] for x in base])

    kmm = np.where(km > 1000, km / 1000, km)          # metros -> km
    opciones = [("tal cual", km), ("metros a km", kmm)]
    regla, kmf = max(opciones, key=lambda o: corr(o[1], la, lo))

    # recorte robusto de lo que sobrevive
    lo_q, hi_q = np.percentile(kmf, [0.5, 99.5])
    m = (kmf >= lo_q) & (kmf <= hi_q)
    out = []
    for x, k, ok in zip(base, kmf, m):
        if ok:
            y = dict(x); y["km"] = float(k); out.append(y)
    kf = np.array([x["km"] for x in out])
    lf = np.array([x["Latitud"] for x in out]); of = np.array([x["longitud"] for x in out])
    return out, regla, corr(kf, lf, of)


def perfilar(registros, tramo=5):
    kf = np.array([x["km"] for x in registros])
    lo_k, hi_k = kf.min(), kf.max()
    ntr = max(1, int((hi_k - lo_k) // tramo) + 1)
    celdas = {(round(x["Latitud"] / .25) * .25, round(x["longitud"] / .25) * .25)
              for x in registros}
    return dict(km_min=float(lo_k), km_max=float(hi_k), tramo=tramo,
                n_tramos=ntr, por_tramo=len(registros) / ntr, celdas=len(celdas))


if __name__ == "__main__":
    d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "todas.json"))
    por = collections.defaultdict(list)
    for x in d:
        por[x["Ruta"]].append(x)

    cand = [r for r, _ in sorted(((r, len(v)) for r, v in por.items()),
                                 key=lambda t: -t[1])[:20]]
    print(f"{'ruta':<14}{'n':>6}{'limpios':>9}{'regla':>14}{'corr':>7}"
          f"{'tramos':>8}{'n/tramo':>9}{'celdas':>8}  veredicto")
    sel = {}
    for r in cand:
        limpios, regla, c = limpiar(por[r])
        if not limpios:
            continue
        # rutas largas con pocos datos: agrandar el tramo hasta alcanzar densidad
        for tramo in (5, 10, 20):
            p = perfilar(limpios, tramo)
            if p["por_tramo"] >= MIN_POR_TRAMO:
                break
        ok = (c >= MIN_CORR and p["por_tramo"] >= MIN_POR_TRAMO
              and p["n_tramos"] >= MIN_TRAMOS)
        motivo = ("ok" if ok else
                  "km no describe la posición" if c < MIN_CORR else
                  "muy pocos datos por tramo" if p["por_tramo"] < MIN_POR_TRAMO else
                  "ruta demasiado corta")
        print(f"{r:<14}{len(por[r]):>6}{len(limpios):>9}{regla:>14}{c:>7.3f}"
              f"{p['n_tramos']:>8}{p['por_tramo']:>9.1f}{p['celdas']:>8}  {motivo}")
        if ok:
            sel[r] = dict(regla=regla, corr=round(c, 4), n=len(limpios), **p)
    json.dump(sel, open("rutas.json", "w"), ensure_ascii=False, indent=1)
    print(f"\n{len(sel)} rutas viables -> rutas.json")
