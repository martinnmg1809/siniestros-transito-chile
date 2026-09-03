#!/usr/bin/env python3
"""
Prepara, para cada ruta viable, todo lo que el modelo y la página necesitan:
tramos, geometría, celdas de clima, ciudades de referencia y la matriz de conteos.

Corre después de rutas.py y antes de entrenar_rutas.py.
Salida: rutas_datos.json
"""
import collections, csv, datetime, gzip, json, math, statistics

import numpy as np

from rutas import limpiar

GRILLA = 0.25          # resolución nativa de ERA5
INICIO = datetime.date(2020, 1, 1)
FIN = datetime.date(2024, 12, 31)
N_HORAS = (FIN - INICIO).days * 24 + 24
N_CIUDADES = 9


def cargar():
    por = collections.defaultdict(list)
    with gzip.open("siniestros_rutas.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                r["Ubicación"] = float(r["Ubicación"])
                r["Latitud"] = float(r["Latitud"]); r["longitud"] = float(r["longitud"])
            except (TypeError, ValueError):
                continue
            if r["FECHA"] and r["Hora_aprox"]:
                por[r["Ruta"]].append(r)
    return por


def ciudades_de(regs, tramo_km):
    """Referencias sobre la ruta: la comuna modal de cada zona, no kilometrajes a mano."""
    kmin = min(r["km"] for r in regs); kmax = max(r["km"] for r in regs)
    ancho = (kmax - kmin) / N_CIUDADES or 1
    zonas = collections.defaultdict(collections.Counter)
    for r in regs:
        zonas[min(int((r["km"] - kmin) // ancho), N_CIUDADES - 1)][r["COMUNA"]] += 1
    out, vistos = [], set()
    for z in sorted(zonas):
        com = zonas[z].most_common(1)[0][0]
        if com in vistos:
            continue
        vistos.add(com)
        pts = [r for r in regs if r["COMUNA"] == com]
        out.append({"nombre": com.title(),
                    "km": round(statistics.median(p["km"] for p in pts)),
                    "lat": round(statistics.median(p["Latitud"] for p in pts), 4),
                    "lon": round(statistics.median(p["longitud"] for p in pts), 4)})
    return out


def preparar(nombre, regs, tramo_km):
    for r in regs:
        r["tramo"] = int(r["km"] // tramo_km) * tramo_km
    tramos = sorted({r["tramo"] for r in regs})
    ix = {t: i for i, t in enumerate(tramos)}

    porT = collections.defaultdict(list)
    for r in regs:
        porT[r["tramo"]].append(r)

    geo, celdas_por_tramo, region = {}, {}, {}
    for t in tramos:
        pts = [(r["Latitud"], r["longitud"]) for r in porT[t]]
        la = statistics.median(p[0] for p in pts); lo = statistics.median(p[1] for p in pts)
        geo[t] = [round(la, 4), round(lo, 4)]
        celdas_por_tramo[t] = (round(la / GRILLA) * GRILLA, round(lo / GRILLA) * GRILLA)
        region[t] = collections.Counter(r["REGION"] for r in porT[t]).most_common(1)[0][0]

    # La tira horaria necesita ~50 filas legibles: en rutas largas se agrupan tramos,
    # en cortas cada tramo es una fila.
    agrupa = max(1, math.ceil(len(tramos) / 55))
    banda_km = tramo_km * agrupa

    celdas = sorted(set(celdas_por_tramo.values()))
    ic = {c: i for i, c in enumerate(celdas)}

    Y = np.zeros((len(tramos), N_HORAS), dtype=np.int16)
    for r in regs:
        t = (datetime.date.fromisoformat(r["FECHA"]) - INICIO).days * 24 \
            + int(float(r["Hora_aprox"]))
        if 0 <= t < N_HORAS:
            Y[ix[r["tramo"]], t] += 1

    CORTO = {"Metropolitana de Santiago": "R. Metropolitana",
             "Libertador General Bernardo O'Higgins": "O'Higgins",
             "Aysén del General Carlos Ibáñez del Campo": "Aysén",
             "Magallanes y de la Antártica Chilena": "Magallanes"}
    bandas = sorted({int(t // banda_km) * banda_km for t in tramos})
    bix = {b: i for i, b in enumerate(bandas)}
    reg_banda = []
    for b in bandas:
        cs = collections.Counter(region[t] for t in tramos
                                 if int(t // banda_km) * banda_km == b)
        r0 = cs.most_common(1)[0][0]
        reg_banda.append(CORTO.get(r0, r0))

    return {
        "nombre": nombre, "tramo_km": tramo_km,
        "banda_km": banda_km, "bandas": bandas,
        "banda_ix": [bix[int(t // banda_km) * banda_km] for t in tramos],
        "regiones_banda": reg_banda,
        "tramos": tramos, "n": len(regs),
        "geometria": {str(t): geo[t] for t in tramos},
        "celdas": [[round(c[0], 2), round(c[1], 2)] for c in celdas],
        "tramo_celda": [ic[celdas_por_tramo[t]] for t in tramos],
        "ciudades": ciudades_de(regs, tramo_km),
        "regiones": sorted({r["REGION"] for r in regs}),
    }, Y


if __name__ == "__main__":
    sel = json.load(open("rutas.json"))
    por = cargar()
    salida, cuentas = {}, {}
    for nombre, cfg in sel.items():
        limpios, _, _ = limpiar(por[nombre])
        limpios = [r for r in limpios if r["FECHA"] and r["Hora_aprox"]]
        d, Y = preparar(nombre, limpios, cfg["tramo"])
        salida[nombre] = d
        cuentas[nombre] = Y
        print(f"{nombre:<14} {d['n']:>6} siniestros  {len(d['tramos']):>4} tramos de "
              f"{d['tramo_km']} km  {len(d['celdas']):>3} celdas  "
              f"{len(d['ciudades'])} ciudades")
    json.dump(salida, open("rutas_datos.json", "w"), ensure_ascii=False)
    np.savez_compressed("cuentas.npz", **cuentas)
    tot = sum(len(v["celdas"]) for v in salida.values())
    print(f"\n{len(salida)} rutas · {tot} celdas de clima en total")
