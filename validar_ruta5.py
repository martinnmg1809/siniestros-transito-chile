#!/usr/bin/env python3
"""Validación reproducible de errores pendientes de Entrega 2.

python validar_ruta5.py [--sin-clima] [--replicas 2000]

Modelos originales M0/M1/M2/M3. Evalúa train/prueba por año, lluvia incremental,
calibración y captura por turnos. No selecciona hiperparámetros mirando 2024.
"""
import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from clima_utc import cargar_cache
from datos_ruta5 import cargar_eventos, referencia_entrenamiento, grilla_civil, exposicion_civil
from evaluacion import captura, captura_turnos, bootstrap_pareado, desvianza
from modelo import ajustar, POS_FERIADO


def codificar(tramos, tiempo, feriados, lluvia):
    pos = np.array([POS_FERIADO.index(feriados.get(t.date().isoformat(), {}).get("dia", "no"))
                    for t in tiempo], np.int32)
    dims = (len(tramos), 24, 7, 12, 4, 3)
    cod = np.arange(len(tramos), dtype=np.int32)[:, None] * 24 + tiempo.hour.to_numpy(dtype=np.int32)
    for d, valores in [(7, tiempo.dayofweek), (12, tiempo.month - 1), (4, pos), (3, lluvia)]:
        cod = cod * d + np.asarray(valores, dtype=np.int32)
    return cod, dims


def agrupar(codigo, y, exposicion, columnas, n_cod):
    c = codigo[:, columnas].ravel()
    e = np.broadcast_to(exposicion[columnas], (codigo.shape[0], len(columnas))).ravel()
    yy = y[:, columnas].ravel()
    valida = e > 0
    ce = np.bincount(c[valida], weights=e[valida], minlength=n_cod)
    cy = np.bincount(c[valida], weights=yy[valida], minlength=n_cod)
    ok = ce > 0
    return np.flatnonzero(ok), cy[ok], ce[ok]


def diseno(codigos, dims, bloques):
    resto = codigos.copy()
    comp = []
    for d in reversed(dims):
        comp.append(resto % d)
        resto //= d
    comp.reverse()
    off = np.cumsum([0] + [dims[b] for b in bloques])
    filas = np.tile(np.arange(len(codigos)), len(bloques))
    cols = np.concatenate([off[i] + comp[b] for i, b in enumerate(bloques)])
    x = sparse.csr_matrix((np.ones(len(filas)), (filas, cols)), shape=(len(codigos), off[-1]))
    return sparse.hstack([x, np.ones((len(codigos), 1))]).tocsr()


def predecir(codigo, dims, bloques, b, exposicion):
    # Evitar una matriz dispersa de todo el período simultáneamente.
    out = np.zeros(codigo.shape, float)
    for i in range(codigo.shape[0]):
        out[i] = np.exp(diseno(codigo[i], dims, bloques) @ b) * exposicion
    return out


def resumen(y, mu, expo):
    e = np.broadcast_to(expo, y.shape)
    v = e > 0
    yy, mm, ee = y[v].astype(float), mu[v], e[v]
    cap = dict(captura(yy, mm, ee))
    turnos = captura_turnos(y, mu)
    return {"siniestros": int(yy.sum()), "esperados": float(mm.sum()),
            "observado_esperado": float(yy.sum() / mm.sum()),
            "desvianza_por_hora": desvianza(yy, mm) / ee.sum(),
            "captura5": cap[.05], "captura10": cap[.10], "captura20": cap[.20],
            "captura5_turno": float(turnos["cubiertos"].sum() / yy.sum()),
            "mae_12h_calendario": float(abs(turnos["esperados"] - turnos["observados"]).mean())}


def calibracion(y, mu):
    yd, md = y.reshape(y.shape[0], -1, 24).sum(2).ravel(), mu.reshape(mu.shape[0], -1, 24).sum(2).ravel()
    decil = pd.qcut(pd.Series(md).rank(method="first"), 10, labels=False)
    t = pd.DataFrame({"decil": decil, "observados": yd, "esperados": md}).groupby("decil").sum()
    t["observado_esperado"] = t.observados / t.esperados
    return t.reset_index()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sin-clima", action="store_true", help="Ejecutar M0/M1/M2 sin descargar meteorología")
    p.add_argument("--replicas", type=int, default=2000)
    p.add_argument("--salida", type=Path, default=Path("resultados/validacion"))
    args = p.parse_args()
    eventos, auditoria = cargar_eventos()
    ref = referencia_entrenamiento(eventos)
    tramos = ref.tramo.to_numpy()
    tiempo, y, fuera = grilla_civil(eventos, tramos)
    fer = json.loads(Path("feriados.json").read_text())
    if max(int(k[:4]) for k in fer) < tiempo.year.max():
        raise ValueError("Calendario insuficiente para el período de evaluación")
    expo = exposicion_civil(tiempo)
    lluvia = np.zeros(y.shape, np.int8)
    meteo = None
    if not args.sin_clima:
        z = cargar_cache()
        meteo = json.loads(str(z["metadatos"]))
        if not np.array_equal(z["tramos"], tramos) or not np.array_equal(z["tiempo"], tiempo.to_numpy(dtype="datetime64[h]")):
            raise ValueError("Caché meteorológico y grilla incompatibles")
        if meteo["referencia_sha256"] != hashlib.sha256(ref.to_csv(index=False).encode()).hexdigest():
            raise ValueError("Cambió la referencia espacial: regenerar clima")
        if not np.array_equal(expo, z["exposicion_tiempo"]):
            raise ValueError("Exposición DST del caché meteorológico incompatible")
        precip = z["precip"][z["idx_celda"]]
        if not np.isfinite(precip[:, expo > 0]).all():
            raise ValueError("Clima faltante en horas existentes")
        lluvia = np.digitize(precip, [.1, .5]).astype(np.int8)
        lluvia[:, expo == 0] = 0  # Evitar códigos fuera de las tres categorías en horas inexistentes.
    excluidos_dst = int(y[:, expo == 0].sum())
    y[:, expo == 0] = 0
    codigo, dims = codificar(tramos, tiempo, fer, lluvia)
    specs = {"M1": [0], "M2": [0, 1, 2, 3, 4]}
    if not args.sin_clima:
        specs["M3"] = list(range(6))
    args.salida.mkdir(parents=True, exist_ok=True)
    ref.to_csv(args.salida / "referencia.csv", index=False)
    filas, boot, cals, diagnosticos, recalibraciones = [], [], [], [], []
    factor_previo = None
    for anio in (2022, 2023, 2024):
        ctr, cte = np.flatnonzero(tiempo.year < anio), np.flatnonzero(tiempo.year == anio)
        c, yt, et = agrupar(codigo, y, expo, ctr, int(np.prod(dims)))
        tasa0 = yt.sum() / et.sum()
        yf = y[:, cte].astype(float)
        ef = np.broadcast_to(expo[cte], yf.shape)
        preds = {"M0": tasa0 * ef}
        m0tr = np.broadcast_to(expo[ctr], y[:, ctr].shape) * tasa0
        filas.append({"anio_prueba": anio, "particion": "train", "modelo": "M0", **resumen(y[:, ctr], m0tr, expo[ctr])})
        filas.append({"anio_prueba": anio, "particion": "prueba", "modelo": "M0", **resumen(yf, preds["M0"], expo[cte])})
        for nombre, bloques in specs.items():
            b, diag = ajustar(diseno(c, dims, bloques), yt, et, devolver_diagnostico=True)
            diagnosticos.append({"anio_prueba": anio, "modelo": nombre, **diag})
            predtr = predecir(codigo[:, ctr], dims, bloques, b, expo[ctr])
            preds[nombre] = predecir(codigo[:, cte], dims, bloques, b, expo[cte])
            filas.append({"anio_prueba": anio, "particion": "train", "modelo": nombre, **resumen(y[:, ctr], predtr, expo[ctr])})
            filas.append({"anio_prueba": anio, "particion": "prueba", "modelo": nombre, **resumen(yf, preds[nombre], expo[cte])})
            cal = calibracion(yf, preds[nombre]); cal["anio_prueba"], cal["modelo"] = anio, nombre
            cals.append(cal)
            # Coeficientes de cada fold para inferencia reproducible, separados del modelo de producción.
            np.savez_compressed(args.salida / f"{nombre}_{anio}.npz", coef=b, dims=np.array(dims), bloques=np.array(bloques), tramos=tramos)
            if nombre == "M3":
                if factor_previo is not None:
                    nombre_cal = "M3_recalibrado"
                    preds[nombre_cal] = preds[nombre] * factor_previo
                    filas.append({"anio_prueba": anio, "particion": "train", "modelo": nombre_cal,
                                  **resumen(y[:, ctr], predtr * factor_previo, expo[ctr])})
                    filas.append({"anio_prueba": anio, "particion": "prueba", "modelo": nombre_cal,
                                  **resumen(yf, preds[nombre_cal], expo[cte])})
                    cal2 = calibracion(yf, preds[nombre_cal]); cal2["anio_prueba"], cal2["modelo"] = anio, nombre_cal
                    cals.append(cal2)
                    recalibraciones.append({"anio_prueba": anio, "factor": factor_previo,
                                            "origen": f"observado/esperado fuera de muestra de {anio - 1}"})
                    bcal = b.copy(); bcal[-1] += np.log(factor_previo)
                    np.savez_compressed(args.salida / f"{nombre_cal}_{anio}.npz", coef=bcal,
                                        dims=np.array(dims), bloques=np.array(bloques), tramos=tramos)
                # Se guarda para el siguiente año, nunca se aplica al año observado.
                factor_previo = yf.sum() / preds[nombre].sum()
            print(f"{anio}: {nombre} convergió ({diag['iteraciones']} iteraciones)", flush=True)
            del predtr
            gc.collect()
        validas = ef.ravel() > 0
        bloques_semana = np.broadcast_to(np.arange(len(cte)) // 168, yf.shape).ravel()[validas]
        for base, candidatos in [("M1", [k for k in ("M2", "M3") if k in preds]),
                                  ("M2", ["M3"] if "M3" in preds else [])]:
            modelos = {k: preds[k].ravel()[validas] for k in [base] + candidatos}
            if len(modelos) < 2:
                continue
            r = bootstrap_pareado(yf.ravel()[validas], modelos, bloques_semana,
                                  replicas=args.replicas, expo=ef.ravel()[validas])
            boot.extend({"anio_prueba": anio, "modelo": k, **v} for k, v in r.items())
        pd.DataFrame(filas).to_csv(args.salida / "metricas.csv", index=False)
        pd.DataFrame(boot).to_csv(args.salida / "bootstrap.csv", index=False)
        del c, yt, et, preds
        gc.collect()
    pd.concat(cals, ignore_index=True).to_csv(args.salida / "calibracion.csv", index=False)
    manifiesto = {"datos": auditoria, "fuera_del_dominio": fuera,
                  "eventos_en_hora_inexistente_excluidos": excluidos_dst,
                  "convencion_temporal": "24 etiquetas civiles por fecha; turnos 00-12 y 12-24 locales pueden durar 11/13 h en DST",
                  "meteorologia": meteo, "replicas_bootstrap": args.replicas,
                  "semilla": 42, "diagnosticos": diagnosticos,
                  "versiones": {n: importlib.metadata.version(n) for n in ("numpy", "pandas", "scipy")},
                  "seleccion": "Especificaciones originales y L2=1 fijos; 2024 ya fue inspeccionado en Entrega 2",
                  "calibracion": "Sin recalibrar con totales del año de prueba",
                  "recalibraciones": recalibraciones,
                  "calendario_sha256": hashlib.sha256(Path("feriados.json").read_bytes()).hexdigest(),
                  "flujo": "No se usan candidatos TMDA ni transacciones como exposición validada"}
    (args.salida / "auditoria.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2))
    print(pd.DataFrame(filas).query("particion == 'prueba'").to_string(index=False))


if __name__ == "__main__":
    main()
