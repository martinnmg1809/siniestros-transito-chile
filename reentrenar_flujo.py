#!/usr/bin/env python3
"""Repetir solo el experimento de flujo tras normalizar residuos numéricos.

La corrida completa desde cero se reproduce con entrenar_comparacion.py.
Este comando conserva los ajustes sin flujo de una corrida anterior idéntica.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import shutil
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from datos_modelado import preparar_experimento, agrupar_modelado, atributos, expandir_prediccion
from modelos_conteo import ModeloConteo, ModeloHibrido, GRILLAS, elegir_configuracion
from entrenar_comparacion import registrar, comparar_bootstrap
from evaluacion import captura
from validar_ruta5 import calibracion


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--origen", type=Path, default=Path("resultados/modelos_pre_normalizacion"))
    p.add_argument("--salida", type=Path, default=Path("resultados/modelos"))
    args = p.parse_args()
    if args.origen.resolve() == args.salida.resolve():
        p.error("Origen y salida deben ser distintos para conservar la auditoría anterior")
    aud = json.loads((args.origen / "auditoria.json").read_text())
    for n in ["datos_modelado.py", "modelos_conteo.py", "entrenar_comparacion.py"]:
        if aud["hashes_codigo"][n] != hashlib.sha256(Path(n).read_bytes()).hexdigest():
            raise ValueError("Cambió código ajeno a la normalización de flujo; ejecutar corrida completa")
    datos = preparar_experimento()
    for n in ["fuente_siniestros", "fuentes_flujo_sha256", "clima_cache_sha256", "ids_cuarentena", "cobertura"]:
        if datos["metadata"][n] != aud["datos"][n]:
            raise ValueError(f"Cambió {n}; no es válido reutilizar ajustes")
    # Confirmar igualdad del proxy: el único cambio numérico permitido son los puntos.
    previo = pd.read_csv(args.origen / "flujo_rezagado.csv")
    serie = previo.pivot(index="tramo", columns="periodo_objetivo", values="proxy_pasadas_por_punto_dia")
    if not np.allclose(serie.to_numpy(), datos["proxy"], rtol=1e-14, atol=0, equal_nan=True):
        raise ValueError("Cambió el proxy de flujo además de los residuos numéricos")
    datos = preparar_experimento(args.salida)
    art = args.salida / "artefactos"; art.mkdir(exist_ok=True)
    for archivo in (args.origen / "artefactos").glob("*.joblib"):
        if "_clima_flujo" not in archivo.name:
            shutil.copy2(archivo, art / archivo.name)
    def cargar_csv(n): return pd.read_csv(args.origen / n)
    def sin_flujo(d): return d.loc[~d.modelo.str.endswith("_clima_flujo")].copy()
    metricas = sin_flujo(cargar_csv("metricas.csv")).to_dict("records")
    busq = cargar_csv("busqueda_temporal.csv")
    busqueda = busq.loc[busq.variante.ne("clima_flujo")].to_dict("records")
    sel = cargar_csv("seleccion_temporal.csv")
    selecciones = sel.loc[sel.variante.ne("clima_flujo")].to_dict("records")
    boot = sin_flujo(cargar_csv("bootstrap.csv")).to_dict("records")
    cals = [sin_flujo(cargar_csv("calibracion.csv"))]
    ajustes = [a for a in aud["ajustes"] if not a["modelo"].endswith("_clima_flujo")]
    casos = {"ruta_completa": np.arange(len(datos["tramos"])), "con_contrato": np.flatnonzero(datos["cubiertos"])}
    grupos = {caso: {a: agrupar_modelado(datos, filas, a) for a in range(2020, 2025)} for caso, filas in casos.items()}

    def predecir(modelo, caso, anio, f=None):
        claves = grupos[caso][anio][0]
        f = atributos(claves, datos) if f is None else f
        return expandir_prediccion(claves, modelo.predict_rate(f), datos, casos[caso], [anio])[0]

    def espacial(caso, anio, f):
        filas = casos[caso]; pasado = datos["tiempo"].year < anio
        y = datos["y"][np.ix_(filas, np.flatnonzero(pasado))].sum(axis=1)
        e = np.full(len(filas), datos["expo"][pasado].sum())
        f0 = np.zeros((len(filas), 9)); f0[:, 0] = filas
        modelo = ModeloConteo("Poisson", "espacial", {"l2": 1.}).fit(f0, y, e)
        return predecir(modelo, caso, anio, f)

    for anio in [2022, 2023, 2024]:
        caso = "con_contrato"; filas = casos[caso]
        tr = [grupos[caso][a] for a in range(2020, anio)]
        c_tr, y_tr, e_tr = (np.concatenate([g[i] for g in tr]) for i in range(3))
        orden = np.argsort(c_tr); c_tr, y_tr, e_tr = c_tr[orden], y_tr[orden], e_tr[orden]
        c_te, y_te, e_te = grupos[caso][anio]
        f_tr, f_te = atributos(c_tr, datos), atributos(c_te, datos)
        pred = {"M1": espacial(caso, anio, f_te)}; modelos_flujo = {}
        for familia in GRILLAS:
            variante = "clima_flujo"; nombre = f"{familia}_{variante}"
            elegida, anios_cv = elegir_configuracion(busqueda, familia, variante, caso, anio)
            for i in (range(len(GRILLAS[familia])) if anio < 2024 else [elegida]):
                m = ModeloConteo(familia, variante, GRILLAS[familia][i]).fit(f_tr, y_tr, e_tr)
                cap = dict(captura(y_te, m.predict_rate(f_te) * e_te, e_te))[.05]
                busqueda.append({"anio_prueba": anio, "cohorte": caso, "familia": familia, "variante": variante,
                                 "configuracion": i, "captura5": cap, "parametros": json.dumps(GRILLAS[familia][i]),
                                 "segundos_ajuste": m.diagnostico["segundos_ajuste"]})
                ajustes.append({"anio_prueba": anio, "cohorte": caso, "modelo": nombre, "configuracion": i, **m.diagnostico})
                print(f"{anio} {nombre} cfg{i}: {cap:.3%}, {m.diagnostico['segundos_ajuste']:.1f}s", flush=True)
                if i == elegida: seleccionado = m
            selecciones.append({"anio_prueba": anio, "cohorte": caso, "familia": familia, "variante": variante,
                                "configuracion": elegida, "anios_usados_para_elegir": ",".join(map(str, anios_cv)) or "ninguno; configuración simple prefijada",
                                "parametros": json.dumps(GRILLAS[familia][elegida])})
            modelos_flujo[familia] = seleccionado
            for particion, claves, f in [("train", c_tr, f_tr), ("prueba", c_te, f_te)]:
                mu, yy, ee = expandir_prediccion(claves, seleccionado.predict_rate(f), datos, filas,
                                                range(2020, anio) if particion == "train" else [anio])
                registrar(metricas, anio, caso, nombre, particion, yy, mu, ee)
                if particion == "prueba":
                    pred[nombre] = mu
                    cal = calibracion(yy, mu); cal["anio_prueba"], cal["cohorte"], cal["modelo"] = anio, caso, nombre
                    cals.append(cal)
            joblib.dump(seleccionado, art / f"{caso}_{nombre}_{anio}.joblib", compress=3)
            sin = joblib.load(art / f"{caso}_{familia}_clima_{anio}.joblib")
            pred[f"{familia}_clima"] = predecir(sin, caso, anio, f_te)
        refs = [("M1", [f"{f}_clima_flujo" for f in GRILLAS])]
        refs += [(f"{f}_clima", [f"{f}_clima_flujo"]) for f in GRILLAS]
        boot += comparar_bootstrap(datos, filas, anio, pred, refs, aud["replicas_bootstrap"], caso)
        del f_tr, c_tr, y_tr, e_tr
        gc.collect()
        f_full = atributos(grupos["ruta_completa"][anio][0], datos)
        hibridos = {"M1": espacial("ruta_completa", anio, f_full)}
        cols = np.flatnonzero(datos["tiempo"].year == anio)
        for familia in GRILLAS:
            general = joblib.load(art / f"ruta_completa_{familia}_clima_{anio}.joblib")
            mu = predecir(general, "ruta_completa", anio, f_full)
            nombre = f"Hibrido_{familia}_clima_flujo"
            con = mu.copy(); con[filas] = pred[f"{familia}_clima_flujo"]
            mu[filas] = pred[f"{familia}_clima"]
            hibridos[nombre], hibridos[f"Hibrido_{familia}_clima"] = con, mu
            registrar(metricas, anio, "hibrido_ruta_completa", nombre, "prueba", datos["y"][:, cols].astype(float), con, datos["expo"][cols])
            if anio == 2024:
                joblib.dump(ModeloHibrido(general, modelos_flujo[familia], filas),
                            art / f"hibrido_{familia}_clima_flujo_evaluado2024.joblib", compress=3)
        refs = [("M1", [f"Hibrido_{f}_clima_flujo" for f in GRILLAS])]
        refs += [(f"Hibrido_{f}_clima", [f"Hibrido_{f}_clima_flujo"]) for f in GRILLAS]
        boot += comparar_bootstrap(datos, casos["ruta_completa"], anio, hibridos, refs, aud["replicas_bootstrap"], "hibrido_ruta_completa")
        for n, filas_tabla in [("metricas", metricas), ("busqueda_temporal", busqueda), ("seleccion_temporal", selecciones), ("bootstrap", boot)]:
            pd.DataFrame(filas_tabla).to_csv(args.salida / f"{n}.csv", index=False)
        del f_full, f_te, pred, hibridos, modelos_flujo
        gc.collect()
    pd.concat(cals, ignore_index=True).to_csv(args.salida / "calibracion.csv", index=False)
    met = pd.DataFrame(metricas)
    cv = met.loc[met.cohorte.isin(["ruta_completa", "hibrido_ruta_completa"]) & met.particion.eq("prueba")
                 & met.anio_prueba.lt(2024) & met.modelo.ne("M0")]
    medias = cv.groupby("modelo").captura5.mean().to_dict()
    preferencia = ["M1"] + [f"{f}_clima" for f in GRILLAS] + [f"Hibrido_{f}_{v}" for v in ["clima", "clima_flujo"] for f in GRILLAS]
    aud.update({"datos": datos["metadata"], "ajustes": ajustes, "captura5_media_cv_ruta_completa": medias,
                "modelo_candidato_por_cv_pre2024": next(n for n in preferencia if medias[n] >= max(medias.values()) - .001),
                "normalizacion_puntos": "Residuos ≤1e-6 respecto a entero se normalizan; valor algebraico original preservado. No acredita físicamente los puntos.",
                "reutilizacion": "Modelos sin flujo conservados tras verificar hashes de código, fuentes, población y proxy. Solo se reajustaron variantes con flujo.",
                "auditoria_previa_sha256": hashlib.sha256((args.origen / "auditoria.json").read_bytes()).hexdigest()})
    aud["hashes_codigo"] = {n: hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in list(aud["hashes_codigo"]) + ["reentrenar_flujo.py"]}
    (args.salida / "auditoria.json").write_text(json.dumps(aud, ensure_ascii=False, indent=2))
    print("Corrección completa. Candidata:", aud["modelo_candidato_por_cv_pre2024"], flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
