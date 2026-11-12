#!/usr/bin/env python3
"""Entrenar y comparar modelos con/sin flujo rezagado, en cohortes iguales.

python entrenar_comparacion.py
No modifica notebook ni página. Predice conteos: proxy DGC no es vehículo-km.
"""
import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from datos_modelado import preparar_experimento, agrupar_modelado, atributos, expandir_prediccion
from evaluacion import captura, bootstrap_pareado
from modelos_conteo import ModeloConteo, ModeloHibrido, GRILLAS, elegir_configuracion
from validar_ruta5 import resumen, calibracion


def registrar(tablas, anio, cohorte, nombre, particion, y, mu, e):
    tablas.append({"anio_prueba": anio, "cohorte": cohorte, "modelo": nombre,
                   "particion": particion, **resumen(y, mu, e)})


def comparar_bootstrap(datos, filas, anio, pred, referencias, replicas, cohorte):
    cols = np.flatnonzero(datos["tiempo"].year == anio)
    yf = datos["y"][np.ix_(filas, cols)].astype(float)
    ef = np.broadcast_to(datos["expo"][cols], yf.shape)
    valida = ef.ravel() > 0
    bloques = np.broadcast_to(np.arange(len(cols)) // 168, yf.shape).ravel()[valida]
    salida = []
    for base, candidatos in referencias:
        modelos = {k: pred[k].ravel()[valida] for k in [base] + candidatos}
        r = bootstrap_pareado(yf.ravel()[valida], modelos, bloques, replicas=replicas, expo=ef.ravel()[valida])
        salida.extend({"anio_prueba": anio, "cohorte": cohorte, "modelo": k, **v} for k, v in r.items())
    return salida


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=Path("resultados/modelos"))
    p.add_argument("--replicas", type=int, default=2000)
    p.add_argument("--familias", nargs="+", default=list(GRILLAS), choices=list(GRILLAS))
    args = p.parse_args()
    if args.replicas < 2:
        p.error("Se requieren al menos dos réplicas")
    salida = args.salida; salida.mkdir(parents=True, exist_ok=True)
    artefactos = salida / "artefactos"; artefactos.mkdir(exist_ok=True)
    datos = preparar_experimento(salida)
    casos = {"ruta_completa": np.arange(len(datos["tramos"])), "con_contrato": np.flatnonzero(datos["cubiertos"])}
    if not len(casos["con_contrato"]):
        raise ValueError("Ningún tramo con serie de flujo completa")
    print(json.dumps(datos["metadata"]["cobertura"], ensure_ascii=False), flush=True)
    grupos = {caso: {anio: agrupar_modelado(datos, filas, anio) for anio in range(2020, 2025)} for caso, filas in casos.items()}
    metricas, busqueda, selecciones, boot, cals, ajustes = [], [], [], [], [], []
    for anio in (2022, 2023, 2024):
        pred_anio, modelos_anio = {}, {}
        for caso, filas in casos.items():
            tr = [grupos[caso][a] for a in range(2020, anio)]
            c_tr, y_tr, e_tr = (np.concatenate([g[i] for g in tr]) for i in range(3))
            orden = np.argsort(c_tr)
            c_tr, y_tr, e_tr = c_tr[orden], y_tr[orden], e_tr[orden]
            c_te, y_te, e_te = grupos[caso][anio]
            f_tr, f_te = atributos(c_tr, datos), atributos(c_te, datos)
            pred_anio[caso], modelos_anio[caso] = {}, {}
            # Baseline espacial idéntico para todas las comparaciones en la cohorte.
            tramo_tr = f_tr[:, 0].astype(int)
            ids = np.unique(tramo_tr)
            b_y = np.bincount(tramo_tr, weights=y_tr)[ids]
            b_e = np.bincount(tramo_tr, weights=e_tr)[ids]
            f_base = np.zeros((len(ids), 9)); f_base[:, 0] = ids
            m1 = ModeloConteo("Poisson", "espacial", {"l2": 1.0}).fit(f_base, b_y, b_e)
            for particion, claves, f in [("train", c_tr, f_tr), ("prueba", c_te, f_te)]:
                tasa = m1.predict_rate(f)
                mu, yy, ee = expandir_prediccion(claves, tasa, datos, filas, range(2020, anio) if particion == "train" else [anio])
                registrar(metricas, anio, caso, "M1", particion, yy, mu, ee)
                mu0 = np.broadcast_to(ee, yy.shape) * (y_tr.sum() / e_tr.sum())
                registrar(metricas, anio, caso, "M0", particion, yy, mu0, ee)
                if particion == "prueba":
                    pred_anio[caso]["M1"] = mu
            variantes = ["clima"] if caso == "ruta_completa" else ["calendario", "clima", "clima_flujo"]
            for familia in args.familias:
                for variante in variantes:
                    elegida, anios_cv = elegir_configuracion(busqueda, familia, variante, caso, anio)
                    indices = range(len(GRILLAS[familia])) if anio < 2024 else [elegida]
                    seleccionado = None
                    for i in indices:
                        nombre = f"{familia}_{variante}"
                        modelo = ModeloConteo(familia, variante, GRILLAS[familia][i]).fit(f_tr, y_tr, e_tr)
                        tasa = modelo.predict_rate(f_te)
                        cap = dict(captura(y_te, tasa * e_te, e_te))[.05]
                        busqueda.append({"anio_prueba": anio, "cohorte": caso, "familia": familia,
                                         "variante": variante, "configuracion": i, "captura5": cap,
                                         "parametros": json.dumps(GRILLAS[familia][i]),
                                         "segundos_ajuste": modelo.diagnostico["segundos_ajuste"]})
                        ajustes.append({"anio_prueba": anio, "cohorte": caso, "modelo": nombre,
                                        "configuracion": i, **modelo.diagnostico})
                        print(f"{anio} {caso} {nombre} cfg{i}: captura={cap:.3%}, {modelo.diagnostico['segundos_ajuste']:.1f}s", flush=True)
                        if i == elegida:
                            seleccionado = modelo
                        del modelo
                        gc.collect()
                    if seleccionado is None:
                        raise RuntimeError("No se entrenó la configuración seleccionada")
                    selecciones.append({"anio_prueba": anio, "cohorte": caso, "familia": familia,
                                        "variante": variante, "configuracion": elegida,
                                        "anios_usados_para_elegir": ",".join(map(str, anios_cv)) or "ninguno; configuración simple prefijada",
                                        "parametros": json.dumps(GRILLAS[familia][elegida])})
                    modelos_anio[caso][nombre] = seleccionado
                    for particion, claves, f in [("train", c_tr, f_tr), ("prueba", c_te, f_te)]:
                        tasa = seleccionado.predict_rate(f)
                        mu, yy, ee = expandir_prediccion(claves, tasa, datos, filas, range(2020, anio) if particion == "train" else [anio])
                        registrar(metricas, anio, caso, nombre, particion, yy, mu, ee)
                        if particion == "prueba":
                            pred_anio[caso][nombre] = mu
                            cal = calibracion(yy, mu); cal["anio_prueba"], cal["cohorte"], cal["modelo"] = anio, caso, nombre
                            cals.append(cal)
                    joblib.dump(seleccionado, artefactos / f"{caso}_{nombre}_{anio}.joblib", compress=3)
                    pd.DataFrame(busqueda).to_csv(salida / "busqueda_temporal.csv", index=False)
                    pd.DataFrame(metricas).to_csv(salida / "metricas.csv", index=False)
                    gc.collect()
            refs = [("M1", [k for k in pred_anio[caso] if k != "M1"])]
            if caso == "con_contrato":
                refs += [(f"{f}_clima", [f"{f}_clima_flujo"]) for f in args.familias]
                refs += [(f"{f}_calendario", [f"{f}_clima"]) for f in args.familias]
            boot += comparar_bootstrap(datos, filas, anio, pred_anio[caso], refs, args.replicas, caso)
            del f_tr, f_te, c_tr, y_tr, e_tr
            gc.collect()
        # Predicción para toda la ruta: flujo solo donde existe, respaldo explícito.
        cols = np.flatnonzero(datos["tiempo"].year == anio)
        yy = datos["y"][:, cols].astype(float); ee = datos["expo"][cols]
        hibridos = {"M1": pred_anio["ruta_completa"]["M1"]}
        for familia in args.familias:
            for variante in ("clima", "clima_flujo"):
                nombre = f"Hibrido_{familia}_{variante}"
                mu = pred_anio["ruta_completa"][f"{familia}_clima"].copy()
                mu[casos["con_contrato"]] = pred_anio["con_contrato"][f"{familia}_{variante}"]
                hibridos[nombre] = mu
                registrar(metricas, anio, "hibrido_ruta_completa", nombre, "prueba", yy, mu, ee)
                if anio == 2024:
                    h = ModeloHibrido(modelos_anio["ruta_completa"][f"{familia}_clima"],
                                      modelos_anio["con_contrato"][f"{familia}_{variante}"], casos["con_contrato"])
                    joblib.dump(h, artefactos / f"hibrido_{familia}_{variante}_evaluado2024.joblib", compress=3)
        refs = [("M1", [k for k in hibridos if k != "M1"])]
        refs += [(f"Hibrido_{f}_clima", [f"Hibrido_{f}_clima_flujo"]) for f in args.familias]
        boot += comparar_bootstrap(datos, casos["ruta_completa"], anio, hibridos, refs, args.replicas, "hibrido_ruta_completa")
        pd.DataFrame(metricas).to_csv(salida / "metricas.csv", index=False)
        pd.DataFrame(selecciones).to_csv(salida / "seleccion_temporal.csv", index=False)
        pd.DataFrame(boot).to_csv(salida / "bootstrap.csv", index=False)
        del pred_anio, modelos_anio, hibridos
        gc.collect()
    pd.concat(cals, ignore_index=True).to_csv(salida / "calibracion.csv", index=False)
    # Selección de la solución para toda la ruta, con años anteriores a 2024.
    met = pd.DataFrame(metricas)
    cv = met.loc[met.cohorte.isin(["ruta_completa", "hibrido_ruta_completa"])
                 & met.particion.eq("prueba") & met.anio_prueba.lt(2024) & met.modelo.ne("M0")]
    medias = cv.groupby("modelo").captura5.mean().to_dict()
    preferencia = (["M1"] + [f"{f}_clima" for f in GRILLAS] +
                   [f"Hibrido_{f}_{v}" for v in ["clima", "clima_flujo"] for f in GRILLAS])
    candidata = next(n for n in preferencia if n in medias and medias[n] >= max(medias.values()) - .001)
    manifest = {"fecha_revision": "2026-11-12", "datos": datos["metadata"],
                "modelo_candidato_por_cv_pre2024": candidata, "captura5_media_cv_ruta_completa": medias,
                "ajustes": ajustes, "grillas": GRILLAS,
                "seleccion": "Ventana expansiva; 2022 prefijado, 2023 elige con 2022, 2024 con 2022/2023. Nunca por métricas de 2024.",
                "tolerancia_simplicidad_pp": .1, "replicas_bootstrap": args.replicas, "semilla": 42,
                "limites": ["Reanálisis meteorológico, no evaluación con pronósticos emitidos en el pasado",
                            "Proxy trimestral por contrato, no medición horaria por tramo ni vehículo-km",
                            "Revisión actual de anexos: disponibilidad histórica de publicación no acreditada",
                            "2024 ya inspeccionado en entregas anteriores; evaluación histórica reutilizada",
                            "RF: bootstrap de 80.000 filas agrupadas por árbol; no muestreo por ocurrencia del siniestro"],
                "versiones": {n: importlib.metadata.version(n) for n in ["numpy", "pandas", "scipy", "scikit-learn", "joblib"]},
                "hashes_codigo": {n: hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ["datos_modelado.py", "modelos_conteo.py", "integrar_flujo.py", "entrenar_comparacion.py"]}}
    (salida / "auditoria.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("Candidata por validación anterior a 2024:", candidata, flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
