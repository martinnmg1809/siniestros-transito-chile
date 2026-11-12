#!/usr/bin/env python3
"""Reajustar con 2020–2024 la configuración elegida exclusivamente antes de 2024.

No reemplaza el modelo del prototipo ni presenta el reajuste como evaluación.
"""
import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from datos_modelado import preparar_experimento, agrupar_modelado, atributos, expandir_prediccion
from modelos_conteo import ModeloConteo, ModeloHibrido
from calibracion_modelos import ModeloCalibrado
from validar_ruta5 import resumen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=Path("resultados/modelos"))
    args = p.parse_args()
    auditoria = json.loads((args.salida / "auditoria.json").read_text())
    nombre = auditoria["modelo_candidato_por_cv_pre2024"]
    seleccion = pd.read_csv(args.salida / "seleccion_temporal.csv")
    datos = preparar_experimento()
    ajustes = []

    def ajustar(cohorte, familia, variante, hasta=2024):
        filas = (np.arange(len(datos["tramos"])) if cohorte == "ruta_completa"
                 else np.flatnonzero(datos["cubiertos"]))
        grupos = [agrupar_modelado(datos, filas, a) for a in range(2020, hasta + 1)]
        claves, y, e = (np.concatenate([g[i] for g in grupos]) for i in range(3))
        f = atributos(claves, datos)
        if variante == "espacial":
            ids = np.unique(f[:, 0].astype(int))
            y = np.bincount(f[:, 0].astype(int), weights=y)[ids]
            e = np.bincount(f[:, 0].astype(int), weights=e)[ids]
            f = np.zeros((len(ids), 9)); f[:, 0] = ids
            parametros = {"l2": 1.}
        else:
            fila = seleccion.loc[seleccion.anio_prueba.eq(2024) & seleccion.cohorte.eq(cohorte)
                                 & seleccion.familia.eq(familia) & seleccion.variante.eq(variante)]
            if len(fila) != 1:
                raise ValueError("Selección anterior a 2024 ambigua o ausente")
            parametros = json.loads(fila.iloc[0].parametros)
        modelo = ModeloConteo(familia, variante, parametros).fit(f, y, e)
        ajustes.append({"cohorte": cohorte, "familia": familia, "variante": variante,
                        "ajuste_hasta": hasta, "parametros": parametros, **modelo.diagnostico})
        return modelo

    # El artefacto evaluado debe reproducir las cifras de la corrida, antes del reajuste.
    carpeta = args.salida / "artefactos"; carpeta.mkdir(exist_ok=True)
    metricas = pd.read_csv(args.salida / "metricas.csv")
    cohorte_eval = "hibrido_ruta_completa" if nombre.startswith("Hibrido_") else "ruta_completa"

    def cargar_evaluado(anio):
        if nombre == "M1":
            return ajustar("ruta_completa", "Poisson", "espacial", hasta=anio - 1)
        if nombre.startswith("Hibrido_"):
            familia, variante = nombre[len("Hibrido_"):].split("_", 1)
            return ModeloHibrido(joblib.load(carpeta / f"ruta_completa_{familia}_clima_{anio}.joblib"),
                                  joblib.load(carpeta / f"con_contrato_{familia}_{variante}_{anio}.joblib"),
                                  np.flatnonzero(datos["cubiertos"]))
        return joblib.load(carpeta / f"ruta_completa_{nombre}_{anio}.joblib")

    recalibracion = []
    for anio in [2023, 2024]:
        evaluado = cargar_evaluado(anio)
        claves = agrupar_modelado(datos, np.arange(len(datos["tramos"])), anio)[0]
        f_eval = atributos(claves, datos)
        mu, y_eval, e_eval = expandir_prediccion(claves, evaluado.predict_rate(f_eval), datos,
                                                np.arange(len(datos["tramos"])), [anio])
        comprobacion = resumen(y_eval, mu, e_eval)
        fila = metricas.loc[metricas.anio_prueba.eq(anio) & metricas.cohorte.eq(cohorte_eval)
                           & metricas.modelo.eq(nombre) & metricas.particion.eq("prueba")].iloc[0]
        for metrica, valor in comprobacion.items():
            if not np.isclose(valor, fila[metrica], rtol=1e-10, atol=1e-10):
                raise RuntimeError(f"El artefacto evaluado no reproduce {metrica} de {anio}")
        previa = metricas.loc[metricas.anio_prueba.eq(anio - 1) & metricas.cohorte.eq(cohorte_eval)
                              & metricas.modelo.eq(nombre) & metricas.particion.eq("prueba")].iloc[0]
        factor = float(previa.observado_esperado)
        recalibracion.extend([
            {"anio_prueba": anio, "modelo": nombre, "ajuste": "original", "factor": 1., "anio_factor": None, **comprobacion},
            {"anio_prueba": anio, "modelo": nombre, "ajuste": "recalibrado", "factor": factor,
             "anio_factor": anio - 1, **resumen(y_eval, mu * factor, e_eval)}])
        if anio == 2024:
            joblib.dump(ModeloCalibrado(evaluado, factor, anio - 1),
                        carpeta / "candidato_evaluado2024_recalibrado_con2023.joblib", compress=3)
    pd.DataFrame(recalibracion).to_csv(args.salida / "recalibracion_candidato.csv", index=False)
    del evaluado, f_eval, mu, y_eval, e_eval

    if nombre == "M1":
        modelo = ajustar("ruta_completa", "Poisson", "espacial")
    elif nombre.startswith("Hibrido_"):
        familia, variante = nombre[len("Hibrido_"):].split("_", 1)
        modelo = ModeloHibrido(ajustar("ruta_completa", familia, "clima"),
                               ajustar("con_contrato", familia, variante), np.flatnonzero(datos["cubiertos"]))
    else:
        familia, variante = nombre.split("_", 1)
        modelo = ajustar("ruta_completa", familia, variante)
    archivo = carpeta / "candidato_reajustado2020_2024.joblib"
    joblib.dump(modelo, archivo, compress=3)
    # Variante para un horizonte posterior: usa el O/E fuera de muestra de 2024.
    # No se presenta su ajuste con 2024 como evaluación de 2024.
    factor_final = float(comprobacion["observado_esperado"])
    calibrado = ModeloCalibrado(modelo, factor_final, 2024)
    archivo_cal = carpeta / "candidato_reajustado2020_2024_recalibrado_con2024.joblib"
    joblib.dump(calibrado, archivo_cal, compress=3)
    # Verificar persistencia con atributos reales, incluyendo zonas sin flujo.
    prueba = atributos(claves[np.linspace(0, len(claves) - 1, 1000, dtype=int)], datos)
    pred = modelo.predict_rate(prueba)
    coincide = np.array_equal(pred, joblib.load(archivo).predict_rate(prueba))
    if not coincide:
        raise RuntimeError("El artefacto recargado cambió sus predicciones")
    if not np.array_equal(calibrado.predict_rate(prueba), joblib.load(archivo_cal).predict_rate(prueba)):
        raise RuntimeError("El artefacto recalibrado cambió sus predicciones")
    manifest = {"modelo": nombre, "ajuste_desde": 2020, "ajuste_hasta": 2024,
                "eleccion": "Nombre y parámetros elegidos con validación de 2022/2023; sin usar puntuación de 2024",
                "evaluacion_del_artefacto": "Ninguna prueba futura: reajuste posterior a la evaluación histórica",
                "estado": "Artefacto de investigación; sin sustitución del prototipo operativo",
                "uso": "Requiere construir los mismos atributos y verificar vigencia del flujo, calendario y pronósticos",
                "filas_comprobacion_persistencia": len(prueba), "predicciones_identicas_al_recargar": coincide,
                "metricas_artefacto_evaluado2024_reproducidas": comprobacion,
                "artefacto_recalibrado": str(archivo_cal), "factor_recalibracion_final": factor_final,
                "anio_factor_final": 2024, "sha256_recalibrado": hashlib.sha256(archivo_cal.read_bytes()).hexdigest(),
                "recalibracion": "Factor global del año previo; no modifica el ranking ni escoge variantes con resultados del año objetivo",
                "hashes_codigo_postproceso": {n: hashlib.sha256(Path(n).read_bytes()).hexdigest()
                                               for n in ["reajustar_candidato.py", "calibracion_modelos.py"]},
                "artefacto": str(archivo), "sha256": hashlib.sha256(archivo.read_bytes()).hexdigest(),
                "ajustes": ajustes}
    (args.salida / "reajuste.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
