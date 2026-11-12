#!/usr/bin/env python3
"""
Calcula el riesgo esperado por tramo y hora para las próximas N horas, combinando
el modelo entrenado con el pronóstico horario de Open-Meteo.

Devuelve conteos ESPERADOS, no probabilidades: la tasa base es de 0,13 % por
tramo-hora, así que una probabilidad por tramo no le sirve a nadie. Lo accionable
es el conteo esperado de la ruta completa y el riesgo relativo de cada tramo.
"""
import datetime, json, urllib.parse, urllib.request
from zoneinfo import ZoneInfo
from feriados import validar_cobertura

import numpy as np

FORECAST = "https://api.open-meteo.com/v1/forecast"
POS_FERIADO = ["no", "inicio", "intermedio", "final"]


def pronostico(celdas, horas=12):
    p = urllib.parse.urlencode({
        "latitude": ",".join(f"{c[0]:.2f}" for c in celdas),
        "longitude": ",".join(f"{c[1]:.2f}" for c in celdas),
        "hourly": "precipitation", "forecast_days": 2,
        "timezone": "GMT"})
    d = json.load(urllib.request.urlopen(f"{FORECAST}?{p}", timeout=120))
    if isinstance(d, dict):
        d = [d]
    tiempos = d[0]["hourly"]["time"]
    ahora = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    utc = [datetime.datetime.fromisoformat(t).replace(tzinfo=datetime.timezone.utc) for t in tiempos]
    indices = [i for i, t in enumerate(utc) if t >= ahora][:horas]
    if len(d) != len(celdas) or len(indices) != horas:
        raise ValueError("Pronóstico incompleto")
    if any(r["hourly"]["time"] != tiempos for r in d):
        raise ValueError("Celdas de pronóstico con timestamps incompatibles")
    P = np.array([r["hourly"]["precipitation"] for r in d], dtype=float)[:, indices]
    if not np.isfinite(P).all() or (P < 0).any():
        raise ValueError("Lluvia pronosticada faltante o inválida; no se asume seco")
    local = [utc[i].astimezone(ZoneInfo("America/Santiago")).isoformat(timespec="minutes") for i in indices]
    return local, P


def calcular(modelo, feriados, horas=12):
    ahora = datetime.datetime.now(ZoneInfo("America/Santiago"))
    validar_cobertura([ahora.date(), (ahora + datetime.timedelta(hours=horas)).date()],
                     modelo.get("calendario_cobertura", (2020, 2024)))
    c = modelo["coef"]
    tramos = modelo["tramos"]
    tc = np.array(modelo["tramo_celda"])
    tiempos, P = pronostico(modelo["celdas"], horas)

    lluvia = np.digitize(P[tc], modelo["cortes_lluvia"])          # (n_tramos, horas)
    eta = np.repeat(np.array(c["tramo"])[:, None] + c["intercepto"],
                    len(tiempos), axis=1)
    for j, t in enumerate(tiempos):
        dt = datetime.datetime.fromisoformat(t)
        f = feriados.get(dt.date().isoformat(), {}).get("dia", "no")
        eta[:, j] += (c["hora"][dt.hour] + c["dow"][dt.weekday()]
                      + c["mes"][dt.month - 1]
                      + c["feriado"][POS_FERIADO.index(
                          f if f in POS_FERIADO else "no")])
    eta = eta + np.array(c["lluvia"])[lluvia]
    mu = np.exp(eta)

    return {
        "generado": ahora.isoformat(timespec="minutes"),
        "horas": tiempos,
        "tramos": tramos,
        "mu": mu.tolist(),
        "lluvia": lluvia.tolist(),
        "precip": P[tc].round(2).tolist(),
        "total": float(mu.sum()),
        "basal": modelo["basal_ruta_hora"] * len(tiempos),
        "geometria": modelo["geometria"],
        "feriado": {t: feriados.get(
            datetime.datetime.fromisoformat(t).date().isoformat(), {}).get("dia", "no")
            for t in tiempos},
    }


if __name__ == "__main__":
    m = json.load(open("modelo_final.json"))
    fer = json.load(open("feriados.json"))
    r = calcular(m, fer)
    json.dump(r, open("riesgo.json", "w"))

    mu = np.array(r["mu"])
    print(f"Ruta 5 Sur — próximas {len(r['horas'])} h desde {r['horas'][0]}")
    print(f"  esperados: {r['total']:.2f} siniestros "
          f"(basal {r['basal']:.2f}, {r['total']/r['basal']:.2f}x)\n")
    print("  por hora:")
    for j, t in enumerate(r["horas"]):
        n_ll = int((np.array(r['lluvia'])[:, j] > 0).sum())
        print(f"    {t[11:16]}  {mu[:,j].sum():.3f}  "
              f"{'█' * int(mu[:,j].sum()*40)} "
              f"{'lluvia en ' + str(n_ll) + ' tramos' if n_ll else ''}")
    print("\n  tramos más riesgosos (suma 12 h):")
    tot = mu.sum(1); o = np.argsort(-tot)[:8]
    for i in o:
        print(f"    km {r['tramos'][i]:>4}-{r['tramos'][i]+5:<4} {tot[i]:.4f}  "
              f"({tot[i]/ (r['basal']/len(r['tramos'])):.1f}x el tramo promedio)")
