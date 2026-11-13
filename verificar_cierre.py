#!/usr/bin/env python3
"""Comprobar la evidencia de Entrega 3 sin descargar ni entrenar modelos.

Por defecto verifica las tablas publicadas y sus manifiestos. --con-artefactos
también requiere las fuentes originales y modelos locales de confianza del equipo;
reconstruye las predicciones de la candidata. No ejecuta la suite de pruebas.
"""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import numpy as np
import pandas as pd


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)


def cerca(actual, esperado, nombre):
    exigir(np.isclose(float(actual), float(esperado), rtol=1e-9, atol=1e-10),
           f"{nombre}: {actual} no coincide con {esperado}")


def sha256(archivo):
    with Path(archivo).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def comprobar_hash(raiz, archivo, esperado):
    ruta = raiz / archivo
    exigir(ruta.is_file(), f"Falta {archivo}; consultar docs/cierre/01_reproducibilidad.md")
    exigir(sha256(ruta) == esperado, f"Hash distinto: {archivo}; no mezclar versiones de evidencia")


def unico(tabla, columnas, nombre):
    exigir(not tabla.empty, f"{nombre}: tabla vacía")
    exigir(not tabla.duplicated(columnas).any(), f"{nombre}: claves duplicadas")


def verificar_tablas(raiz):
    raiz = Path(raiz)
    carpeta = raiz / "resultados/modelos"
    a = json.loads((carpeta / "auditoria.json").read_text())
    r = json.loads((carpeta / "reajuste.json").read_text())
    tablas = {n: pd.read_csv(carpeta / f"{n}.csv") for n in
              ["metricas", "cobertura_flujo", "busqueda_temporal", "seleccion_temporal",
               "bootstrap", "calibracion", "recalibracion_candidato"]}
    for archivo, digest in (a["hashes_codigo"] | r["hashes_codigo_postproceso"]).items():
        comprobar_hash(raiz, archivo, digest)
    comprobar_hash(raiz, "ruta5_2020_2024.csv.gz", a["datos"]["fuente_siniestros"]["sha256"])
    mensajes = ["Código de modelado y fuente de siniestros coinciden con los hashes de la corrida."]
    cobertura = tablas["cobertura_flujo"]
    unico(cobertura, ["anio"], "cobertura")
    esperada = pd.DataFrame(a["datos"]["cobertura"]).sort_values("anio").reset_index(drop=True)
    pd.testing.assert_frame_equal(cobertura.sort_values("anio").reset_index(drop=True), esperada)
    exigir(set(cobertura.anio) == set(range(2020, 2025)), "Cobertura temporal incompleta")
    cerca(cobertura.siniestros_total.sum(), a["datos"]["registros_modelado"], "Población modelada")
    m = tablas["metricas"]
    clave = ["anio_prueba", "cohorte", "modelo", "particion"]
    unico(m, clave, "métricas")
    familias = list(a["grillas"])
    casos = {"ruta_completa": ["M0", "M1"] + [f"{f}_clima" for f in familias],
             "con_contrato": ["M0", "M1"] + [f"{f}_{v}" for f in familias for v in
                                               ("calendario", "clima", "clima_flujo")],
             "hibrido_ruta_completa": [f"Hibrido_{f}_{v}" for f in familias for v in ("clima", "clima_flujo")]}
    esperadas = {(anio, coh, modelo, part) for anio in (2022, 2023, 2024) for coh, modelos in casos.items()
                 for modelo in modelos for part in (["prueba"] if coh.startswith("hibrido") else ["train", "prueba"])}
    exigir(set(m[clave].itertuples(index=False, name=None)) == esperadas, "Métricas incompletas o de otro protocolo")
    numericas = [c for c in m.columns if c not in clave]
    exigir(np.isfinite(m[numericas].to_numpy(float)).all(), "Métricas no finitas")
    exigir((m[numericas] >= 0).all().all(), "Métricas negativas")
    idx = m.set_index(clave)
    for fila in m.itertuples(index=False):
        anios = [fila.anio_prueba] if fila.particion == "prueba" else range(2020, fila.anio_prueba)
        campo = "siniestros_con_flujo" if fila.cohorte == "con_contrato" else "siniestros_total"
        cerca(fila.siniestros, cobertura.loc[cobertura.anio.isin(anios), campo].sum(), f"Población {fila.modelo}")
        cerca(fila.observado_esperado, fila.siniestros / fila.esperados, "Observado/esperado")
        exigir(0 <= fila.captura5 <= fila.captura10 <= fila.captura20 <= 1 and 0 <= fila.captura5_turno <= 1,
               f"Captura fuera de rango/orden: {fila.modelo}")
        if fila.modelo == "M0":
            for c, valor in [("captura5", .05), ("captura10", .10), ("captura20", .20), ("captura5_turno", .05)]:
                cerca(getattr(fila, c), valor, f"M0 {c}")
    mensajes.append(f"{len(m)} filas de métricas completas: cohortes, población, escala, O/E y referencia M0 coherentes.")

    busqueda, seleccion = tablas["busqueda_temporal"], tablas["seleccion_temporal"]
    columnas = ["anio_prueba", "cohorte", "familia", "variante"]
    unico(busqueda, columnas + ["configuracion"], "búsqueda")
    unico(seleccion, columnas, "selección")
    combinaciones = {(anio, coh, f, v) for anio in (2022, 2023, 2024) for f in familias
                     for coh, vs in [("ruta_completa", ["clima"]), ("con_contrato", ["calendario", "clima", "clima_flujo"])] for v in vs}
    exigir(set(seleccion[columnas].itertuples(index=False, name=None)) == combinaciones, "Selección temporal incompleta")
    exigir(np.isfinite(busqueda.captura5).all() and busqueda.captura5.between(0, 1).all(), "Búsqueda con captura inválida")
    tolerancia = a["tolerancia_simplicidad_pp"] / 100
    claves_busqueda = set()
    for s in seleccion.itertuples(index=False):
        propios = busqueda.loc[busqueda.cohorte.eq(s.cohorte) & busqueda.familia.eq(s.familia)
                               & busqueda.variante.eq(s.variante)]
        previos = propios.loc[propios.anio_prueba.lt(s.anio_prueba)]
        anios = list(range(2022, s.anio_prueba))
        usados = [] if str(s.anios_usados_para_elegir).startswith("ninguno") else [int(x) for x in str(s.anios_usados_para_elegir).split(",")]
        exigir(usados == anios, f"Años de selección incorrectos/futuros: {s.familia} {s.anio_prueba}")
        if anios:
            requeridas = {(a0, c) for a0 in anios for c in range(len(a["grillas"][s.familia]))}
            exigir(set(previos[["anio_prueba", "configuracion"]].itertuples(index=False, name=None)) == requeridas,
                   "Falta evaluación previa de una configuración")
            medias = previos.groupby("configuracion").captura5.mean()
            elegida = int(medias[medias >= medias.max() - tolerancia].index.min())
        else:
            elegida = 0
        exigir(s.configuracion == elegida, f"Configuración temporal incoherente: {s.familia} {s.anio_prueba}")
        exigir(json.loads(s.parametros) == a["grillas"][s.familia][elegida], "Parámetros distintos de la configuración elegida")
        configs = range(len(a["grillas"][s.familia])) if s.anio_prueba < 2024 else [elegida]
        claves_busqueda.update((s.anio_prueba, s.cohorte, s.familia, s.variante, c) for c in configs)
        puntaje = propios.loc[propios.anio_prueba.eq(s.anio_prueba) & propios.configuracion.eq(elegida)]
        exigir(len(puntaje) == 1, "No está el resultado de la configuración elegida")
        cerca(puntaje.iloc[0].captura5, idx.loc[(s.anio_prueba, s.cohorte, f"{s.familia}_{s.variante}", "prueba"), "captura5"], "Captura seleccionada")
    exigir(set(busqueda[columnas + ["configuracion"]].itertuples(index=False, name=None)) == claves_busqueda,
           "La búsqueda contiene evaluaciones ausentes o adicionales al protocolo")
    cv = m.loc[m.anio_prueba.lt(2024) & m.particion.eq("prueba") & m.cohorte.ne("con_contrato") & m.modelo.ne("M0")]
    medias = cv.groupby("modelo").captura5.mean().to_dict()
    exigir(medias.keys() == a["captura5_media_cv_ruta_completa"].keys(), "Candidatos de CV distintos")
    for nombre, valor in medias.items():
        cerca(valor, a["captura5_media_cv_ruta_completa"][nombre], f"CV {nombre}")
    orden = ["M1"] + [f"{f}_clima" for f in familias] + [f"Hibrido_{f}_{v}" for v in ("clima", "clima_flujo") for f in familias]
    candidata = next(n for n in orden if medias[n] >= max(medias.values()) - tolerancia)
    exigir(candidata == a["modelo_candidato_por_cv_pre2024"] == r["modelo"], "Candidata distinta de la selección pre-2024")
    exigir(all(x.get("convergio", True) for x in a["ajustes"] + r["ajustes"]), "Ajuste sin convergencia")
    mensajes.append(f"{len(seleccion)} selecciones y {len(busqueda)} búsquedas verificadas; candidata: {candidata}.")

    b = tablas["bootstrap"]
    unico(b, ["anio_prueba", "cohorte", "modelo", "referencia"], "bootstrap")
    claves_boot = {(y, coh, n, "M1") for y in (2022, 2023, 2024) for coh, ns in casos.items()
                   for n in ns if n not in ("M0", "M1")}
    claves_boot.update((y, "con_contrato", f"{f}_{con}", f"{f}_{sin}") for y in (2022, 2023, 2024)
                       for f in familias for con, sin in [("clima", "calendario"), ("clima_flujo", "clima")])
    claves_boot.update((y, "hibrido_ruta_completa", f"Hibrido_{f}_clima_flujo", f"Hibrido_{f}_clima")
                       for y in (2022, 2023, 2024) for f in familias)
    exigir(set(b[["anio_prueba", "cohorte", "modelo", "referencia"]].itertuples(index=False, name=None)) == claves_boot,
           "Bootstrap incompleto o con comparaciones distintas")
    exigir(np.isfinite(b[["diferencia_pp", "ic95_inf_pp", "ic95_sup_pp"]]).all().all(), "IC no finito")
    exigir((b.ic95_inf_pp <= b.ic95_sup_pp).all(), "IC invertido")
    for x in b.itertuples(index=False):
        coh_ref = "ruta_completa" if x.cohorte == "hibrido_ruta_completa" and x.referencia == "M1" else x.cohorte
        dif = idx.loc[(x.anio_prueba, x.cohorte, x.modelo, "prueba"), "captura5"] - idx.loc[(x.anio_prueba, coh_ref, x.referencia, "prueba"), "captura5"]
        cerca(x.diferencia_pp, 100 * dif, "Diferencia bootstrap")
        exigir(x.replicas_validas == a["replicas_bootstrap"], "Número de réplicas distinto")
    cal = tablas["calibracion"]
    unico(cal, ["anio_prueba", "cohorte", "modelo", "decil"], "calibración")
    exigir(np.isfinite(cal[["observados", "esperados", "observado_esperado"]]).all().all()
           and (cal.observados >= 0).all() and (cal.esperados > 0).all(), "Calibración no finita o inválida")
    grupos_cal = list(cal.groupby(["anio_prueba", "cohorte", "modelo"]))
    esperado_cal = {(s.anio_prueba, s.cohorte, f"{s.familia}_{s.variante}") for s in seleccion.itertuples(index=False)}
    exigir({k for k, _ in grupos_cal} == esperado_cal, "Calibración incompleta")
    for k, grupo in grupos_cal:
        exigir(set(grupo.decil) == set(range(10)), f"Deciles incompletos: {k}")
        fila = idx.loc[(*k, "prueba")]
        cerca(grupo.observados.sum(), fila.siniestros, "Observados en deciles")
        cerca(grupo.esperados.sum(), fila.esperados, "Esperados en deciles")
        for c in grupo.itertuples(index=False):
            cerca(c.observado_esperado, c.observados / c.esperados, "O/E del decil")
    mensajes.append(f"{len(b)} diferencias de captura e IC coherentes; {len(cal)} deciles concilian con sus cohortes.")

    rc = tablas["recalibracion_candidato"]
    unico(rc, ["anio_prueba", "ajuste"], "recalibración")
    exigir(np.isfinite(rc[numericas + ["factor"]]).all().all() and (rc[numericas] >= 0).all().all()
           and (rc.factor > 0).all(), "Recalibración no finita o negativa")
    exigir(set(rc[["anio_prueba", "ajuste"]].itertuples(index=False, name=None)) ==
           {(y, v) for y in [2023, 2024] for v in ["original", "recalibrado"]}, "Recalibración incompleta")
    coh = "hibrido_ruta_completa" if candidata.startswith("Hibrido_") else "ruta_completa"
    for x in rc.itertuples(index=False):
        exigir(x.modelo == candidata, "Recalibración de otra candidata")
        base = idx.loc[(x.anio_prueba, coh, candidata, "prueba")]
        if x.ajuste == "recalibrado":
            exigir(x.anio_factor == x.anio_prueba - 1, "Recalibración usa un año incorrecto/futuro")
            factor = idx.loc[(x.anio_prueba - 1, coh, candidata, "prueba"), "observado_esperado"]
        else:
            factor = 1
            exigir(pd.isna(x.anio_factor), "Variante original con año de factor")
            for metrica in numericas:
                cerca(getattr(x, metrica), base[metrica], f"Recalibración original {metrica}")
        cerca(x.factor, factor, "Factor de recalibración")
        for metrica in ["siniestros", "captura5", "captura10", "captura20", "captura5_turno"]:
            cerca(getattr(x, metrica), base[metrica], f"Recalibración {metrica}")
        cerca(x.esperados, base.esperados * factor, "Conteo recalibrado")
        cerca(x.observado_esperado, base.observado_esperado / factor, "O/E recalibrado")
    for metrica, valor in r["metricas_artefacto_evaluado2024_reproducidas"].items():
        cerca(valor, idx.loc[(2024, coh, candidata, "prueba"), metrica], f"Manifiesto reajuste {metrica}")
    mensajes.append("Recalibración coherente con factores del año anterior; manifiesto de reajuste conciliado.")
    return mensajes, a, r, tablas


def verificar_artefactos(raiz, a, r, tablas):
    # El contrato comprobado aquí es la candidata publicada de esta entrega.
    exigir(a["modelo_candidato_por_cv_pre2024"] == "Poisson_clima", "Actualizar el verificador de artefactos si cambia la candidata")
    from datos_modelado import preparar_experimento, agrupar_modelado, atributos, expandir_prediccion
    from validar_ruta5 import resumen
    import joblib
    from threadpoolctl import threadpool_limits

    eda = json.loads((raiz / "resultados/eda/auditoria.json").read_text())
    calendario = next(f["sha256"] for f in eda["fuentes"] if f["archivo"] == "feriados.json")
    insumos = {"feriados.json": calendario, "clima_ruta5.npz": a["datos"]["clima_cache_sha256"],
               **{f"data/fuentes/dgc/anexo_{v}.xls": h for v, h in a["datos"]["fuentes_flujo_sha256"].items()},
               r["artefacto"]: r["sha256"], r["artefacto_recalibrado"]: r["sha256_recalibrado"]}
    for archivo, digest in insumos.items():
        comprobar_hash(raiz, archivo, digest)
    modelos = raiz / "resultados/modelos/artefactos"
    mensajes = ["Clima, calendario, anexos DGC y artefactos finales coinciden con sus hashes."]
    with threadpool_limits(limits=2):
        datos = preparar_experimento()
        exigir(datos["metadata"]["registros_modelado"] == a["datos"]["registros_modelado"], "Población reconstruida diferente")
        exigir(datos["metadata"]["cobertura"] == a["datos"]["cobertura"], "Cobertura reconstruida diferente")
        filas = np.arange(len(datos["tramos"]))
        for anio in (2023, 2024):
            archivo = modelos / f"ruta_completa_Poisson_clima_{anio}.joblib"
            exigir(archivo.is_file(), f"Falta {archivo.name}; regenerar o recuperar del equipo")
            modelo = joblib.load(archivo)
            claves = agrupar_modelado(datos, filas, anio)[0]
            f = atributos(claves, datos)
            mu, y, e = expandir_prediccion(claves, modelo.predict_rate(f), datos, filas, [anio])
            rc = tablas["recalibracion_candidato"]
            for ajuste in ("original", "recalibrado"):
                esperada = rc.loc[rc.anio_prueba.eq(anio) & rc.ajuste.eq(ajuste)].iloc[0]
                actual = resumen(y, mu * esperada.factor, e)
                for metrica, valor in actual.items():
                    cerca(valor, esperada[metrica], f"Artefacto {anio} {ajuste} {metrica}")
            mensajes.append(f"Predicciones {anio} originales y recalibradas reproducen las 9 métricas (rtol=1e-9, atol=1e-10).")
            mensajes.append(f"SHA256 evaluado {anio}: {sha256(archivo)}")
        muestra = f[np.linspace(0, len(f) - 1, 1000, dtype=int)]
        final = joblib.load(raiz / r["artefacto"])
        calibrado = joblib.load(raiz / r["artefacto_recalibrado"])
        p = final.predict_rate(muestra)
        exigir(np.isfinite(p).all() and (p > 0).all(), "Predicciones finales inválidas")
        exigir(np.array_equal(p, joblib.load(raiz / r["artefacto"]).predict_rate(muestra)), "Cambio al recargar modelo")
        exigir(np.allclose(calibrado.predict_rate(muestra), p * r["factor_recalibracion_final"], rtol=1e-12), "Escala final distinta")
        exigir(calibrado.anio_factor == r["anio_factor_final"], "Año del factor final distinto")
        mensajes.append("Reajuste 2020-2024: 1.000 predicciones válidas y persistencia idéntica; sin evaluación futura.")
    return mensajes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--con-artefactos", action="store_true")
    p.add_argument("--salida", type=Path, help="Guardar informe Markdown (sin modificar resultados/modelos)")
    args = p.parse_args()
    if args.salida is not None and args.salida.suffix != ".md":
        p.error("--salida debe ser un archivo .md")
    raiz = Path(__file__).resolve().parent
    if Path.cwd().resolve() != raiz:
        p.error("Ejecutar desde la raíz del repositorio")
    mensajes = []
    error = None
    try:
        mensajes, a, r, tablas = verificar_tablas(raiz)
        if args.con_artefactos:
            mensajes += verificar_artefactos(raiz, a, r, tablas)
    except (OSError, ValueError, KeyError, AssertionError, ImportError, StopIteration) as exc:
        error = f"{type(exc).__name__}: {exc}"
    modo = "tablas y artefactos locales" if args.con_artefactos else "solo tablas publicadas"
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "sin Git"
    cambios = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    texto = (f"# Verificación de cierre\n\nFecha UTC: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n\n"
             f"Modo: {modo}. Estado: {'ERROR' if error else 'CORRECTO'}.\n\n"
             f"Commit de entrada: `{commit}`. Cambios locales al registrar: {'sí' if cambios else 'no'}.\n\n"
             f"Verificador SHA256: `{sha256(Path(__file__))}`.\n\n"
             f"Python: {platform.python_version()} ({platform.system()} {platform.machine()}).\n\n")
    for nombre in ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "joblib", "threadpoolctl", "xlrd"]:
        try:
            version = importlib.metadata.version(nombre)
        except importlib.metadata.PackageNotFoundError:
            version = "no instalado"
        texto += f"- {nombre}: {version}\n"
    texto += "\n## Comprobaciones\n\n" + "\n".join(f"- {x}" for x in mensajes) + "\n"
    if error:
        texto += f"\nError: {error}\n"
    texto += ("\nNo descarga, reentrena ni modifica las fuentes o resultados de modelado. "
              "No sustituye las pruebas unitarias ni valida pronósticos futuros. "
              "El modo de tablas comprueba coherencia interna, no recalcula predicciones ni intervalos.\n")
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto)
    print(texto)
    return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(main())
