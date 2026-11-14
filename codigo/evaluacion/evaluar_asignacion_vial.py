"""Comprobar asignación espacial contra etiquetas históricas, sin entrenar modelos."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform

os.environ.setdefault("MPLCONFIGDIR", "/tmp/siniestros-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyproj
import shapely

from descargar_eje_mop import cargar_geometria
from explorar_conaset_2025 import cargar_instantanea
from ubicacion_vial import IndiceVial, decidir, es_ruta5_sur, normalizar


def wilson(aciertos, total):
    if not total:
        return np.nan, np.nan
    z = 1.959963984540054
    p = aciertos / total
    den = 1 + z * z / total
    medio = (p + z * z / (2 * total)) / den
    radio = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return medio - radio, medio + radio


def etiquetar(rutas):
    """Ruta vacía, genérica o múltiple no se convierte en negativo conocido."""
    r = rutas.map(normalizar)
    r = r.where(rutas.notna(), "")
    positivo = r.eq("RUTA 5 SUR")
    ambiguo = r.eq("") | r.isin(["RUTA 5", "5", "S/R", "S/ROL", "-", "0"])
    ambiguo |= r.str.contains("RUTA 5 SUR", regex=False) & ~positivo
    ambiguo |= r.str.contains("RUTA 5", regex=False) & ~positivo & ~r.eq("RUTA 5 NORTE")
    return pd.Series(np.where(positivo, "ruta5sur", np.where(ambiguo, "desconocida", "otra_via")), index=r.index)


def metricas(d, estados, distancia):
    asignado = np.asarray(estados) == "candidato_asignable"
    positivo, negativo = d.etiqueta.eq("ruta5sur").to_numpy(), d.etiqueta.eq("otra_via").to_numpy()
    tp, fp, fn, tn = int((asignado & positivo).sum()), int((asignado & negativo).sum()), int((~asignado & positivo).sum()), int((~asignado & negativo).sum())
    error = (d.km_estimado - d["Ubicación"]).abs()
    verdaderos = asignado & positivo
    coincide = (np.floor(d.km_estimado / 5) == np.floor(d["Ubicación"] / 5)).to_numpy()
    correctos = int((verdaderos & coincide).sum())
    desconocidos_asignados = int((asignado & ~positivo & ~negativo).sum())
    todos_asignados = int(asignado.sum())
    p_lo, p_hi = wilson(tp, tp + fp)
    s_lo, s_hi = wilson(tp, tp + fn)
    t_lo, t_hi = wilson(correctos, tp)
    return {"distancia_max_m": distancia, "verdaderos_positivos": tp, "falsos_positivos": fp,
            "falsos_negativos": fn, "verdaderos_negativos": tn,
            "precision_etiquetados": tp / (tp + fp) if tp + fp else np.nan,
            "precision_ic95_inf": p_lo, "precision_ic95_sup": p_hi,
            "sensibilidad_etiquetados": tp / (tp + fn) if tp + fn else np.nan,
            "sensibilidad_ic95_inf": s_lo, "sensibilidad_ic95_sup": s_hi,
            "tramo_correcto_condicional": correctos / tp if tp else np.nan,
            "tramo_correcto_ic95_inf": t_lo, "tramo_correcto_ic95_sup": t_hi,
            "tramo_correcto_sobre_todos_positivos": correctos / (tp + fn) if tp + fn else np.nan,
            "km_error_mediano_positivos_asignados": error.loc[verdaderos].median(),
            "km_error_p90_positivos_asignados": error.loc[verdaderos].quantile(.9),
            "asignables_total": todos_asignados,
            "asignables_sin_etiqueta": desconocidos_asignados,
            "precision_cota_desconocidos_todos_otras_vias": tp / todos_asignados if todos_asignados else np.nan,
            "precision_cota_desconocidos_todos_ruta5sur": (tp + desconocidos_asignados) / todos_asignados if todos_asignados else np.nan,
            "total_sin_etiqueta": int((~positivo & ~negativo).sum())}


def auditar_geometria(features):
    filas = []
    for f in features:
        a, g = f["attributes"], f.get("geometry") or {}
        partes = g.get("paths", [])
        vertices = [v for p in partes for v in p]
        medidas = [v[2] if len(v) == 3 and v[2] is not None else np.nan for v in vertices]
        filas.append({**a, "ruta5sur_candidata": es_ruta5_sur(a), "partes": len(partes),
                      "vertices": len(vertices), "vertices_m_faltante": int((~np.isfinite(medidas)).sum()),
                      "m_inicial": medidas[0] if medidas else np.nan,
                      "m_final": medidas[-1] if medidas else np.nan})
    return pd.DataFrame(filas)


def generar_candidatos(df, indice, radio):
    # Solo coordenadas válidas; las inválidas quedan explícitas, sin asignación.
    valido = (df.Latitud.between(-56, -17) & df.longitud.between(-76, -66) &
              np.isfinite(df.Latitud) & np.isfinite(df.longitud))
    resultados = [{"distancia_ruta5_m": np.inf, "distancia_otra_m": np.inf,
                   "km_estimado": np.nan, "objectid_eje": -1, "alternativas": []} for _ in range(len(df))]
    coords = df.loc[valido]
    candidatos = indice.candidatos(coords.longitud, coords.Latitud, radio)
    for i, candidato in zip(np.flatnonzero(valido.to_numpy()), candidatos):
        resultados[i] = candidato
    return resultados


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--geometria", type=Path, required=True)
    p.add_argument("--conaset", type=Path, required=True)
    p.add_argument("--protocolo", type=Path, default=Path("config/protocolo_asignacion_vial.json"))
    p.add_argument("--salida", type=Path, default=Path("resultados/asignacion_vial"))
    p.add_argument("--derivados", type=Path, default=Path("data/fuentes/mop/derivados_asignacion_20261114"))
    a = p.parse_args()
    if (a.derivados / "propuestas_2025.csv.gz").exists():
        raise ValueError("Ya existen propuestas de 2025; usar otra carpeta --derivados para no mezclar revisiones")
    protocolo = json.loads(a.protocolo.read_text())
    features, manifiesto = cargar_geometria(a.geometria, a.protocolo)
    qa = auditar_geometria(features)
    indice = IndiceVial(features, protocolo["crs_calculo"])
    print(f"Índice: {len(indice.ix_sur)} segmentos sur, {len(indice.ix_otras)} competidores", flush=True)
    nacional, m_conaset = cargar_instantanea(a.conaset)
    # Se carga la instantánea comprobada, pero solo 2024 entra al ensayo.
    d = nacional.loc[nacional["AÑO"].eq(protocolo["anio_comprobacion"])].copy().reset_index(drop=True)
    d["etiqueta"] = etiquetar(d.Ruta)
    cuarentena = pd.read_csv("resultados/modelos/cuarentena_espacial.csv")
    d["en_cuarentena_historica"] = d.ID.isin(cuarentena.ID)
    candidatos = generar_candidatos(d, indice, max(protocolo["sensibilidad_distancias_m"]))
    d = pd.concat([d, pd.DataFrame([{k: v for k, v in c.items() if k != "alternativas"} for c in candidatos])], axis=1)
    estados = [decidir(c, protocolo) for c in candidatos]
    d["estado"] = estados
    filas = []
    para_metricas = ~d.en_cuarentena_historica
    for distancia in protocolo["sensibilidad_distancias_m"]:
        e = [decidir(c, protocolo, distancia) for c in candidatos]
        filas.append(metricas(d.loc[para_metricas], np.asarray(e)[para_metricas], distancia))
    sensibilidad = pd.DataFrame(filas)
    principal = sensibilidad.loc[sensibilidad.distancia_max_m.eq(protocolo["distancia_max_m"])].iloc[0]
    por_region, por_tramo = [], []
    for region, g in d.loc[para_metricas].groupby("REGION"):
        por_region.append({"region": region, **metricas(g, g.estado, protocolo["distancia_max_m"])})
    positivos = d.loc[d.etiqueta.eq("ruta5sur") & para_metricas].copy()
    positivos["tramo_original"] = (positivos["Ubicación"] // 5 * 5).astype(int)
    for tramo, g in positivos.groupby("tramo_original"):
        por_tramo.append({"tramo_original": tramo, "eventos": len(g),
                          "asignables": int(g.estado.eq("candidato_asignable").sum()),
                          "tramo_correcto_y_asignable": int((g.estado.eq("candidato_asignable") &
                              (g.km_estimado // 5 * 5).eq(tramo)).sum())})
    # Confirmación empírica de escala con 2020–2021, sin ajustar offsets o reglas.
    h = pd.read_csv("data/siniestros/ruta5_2020_2024.csv.gz")
    h = h.loc[h["AÑO"].isin(protocolo["anios_control_medidas"]) & h.Ruta.eq("RUTA 5 SUR") &
              h["Ubicación"].gt(0) & ~h.ID.isin(cuarentena.ID)].copy().reset_index(drop=True)
    ch = generar_candidatos(h, indice, max(protocolo["sensibilidad_distancias_m"]))
    h["km_estimado"] = [c["km_estimado"] for c in ch]
    h["distancia_ruta5_m"] = [c["distancia_ruta5_m"] for c in ch]
    control_escala = []
    for factor in (1, 1000):
        err = (h.km_estimado * 1000 / factor - h["Ubicación"]).abs()
        control_escala.append({"divisor_de_M": factor, "eventos_control": len(h),
                               "con_candidato_m_finita": int(err.notna().sum()),
                               "error_km_mediano": err.median(), "error_km_p90": err.quantile(.9)})
    criterios = protocolo["criterios_propuestos_no_rubrica"]
    decisiones = {
        "precision_etiquetados": bool(principal.precision_ic95_inf >= criterios["limite_inferior_wilson95_precision"]),
        "sensibilidad_etiquetados": bool(principal.sensibilidad_ic95_inf >= criterios["limite_inferior_wilson95_sensibilidad"]),
        "tramo_correcto": bool(principal.tramo_correcto_ic95_inf >= criterios["limite_inferior_wilson95_tramo_correcto"]),
        "vigencia_cartografica": criterios["vigencia_cartografica_acreditada"],
        "competidoras_urbanas": criterios["cobertura_competidoras_urbanas_acreditada"]}
    admisible = all(decisiones.values())
    a.salida.mkdir(parents=True, exist_ok=True)
    a.derivados.mkdir(parents=True, exist_ok=True)
    d.to_csv(a.derivados / "candidatos_2024.csv.gz", index=False)
    h.to_csv(a.derivados / "control_medidas_2020_2021.csv.gz", index=False)
    asignaciones_2025 = 0
    if admisible:
        nuevo = nacional.loc[nacional["AÑO"].eq(2025)].copy().reset_index(drop=True)
        cn = generar_candidatos(nuevo, indice, max(protocolo["sensibilidad_distancias_m"]))
        nuevo = pd.concat([nuevo, pd.DataFrame([{k: v for k, v in c.items() if k != "alternativas"} for c in cn])], axis=1)
        nuevo["estado"] = [decidir(c, protocolo) for c in cn]
        nuevo["metodo_version"] = protocolo["version"]
        nuevo["fuente_cartografia"] = manifiesto["fuente"]
        nuevo.to_csv(a.derivados / "propuestas_2025.csv.gz", index=False)
        asignaciones_2025 = int(nuevo.estado.eq("candidato_asignable").sum())
    tablas = {"cartografia": qa, "sensibilidad": sensibilidad,
              "por_region": pd.DataFrame(por_region), "por_tramo": pd.DataFrame(por_tramo),
              "control_escala": pd.DataFrame(control_escala),
              "estados": d.groupby(["etiqueta", "estado"]).size().rename("eventos").reset_index()}
    for nombre, tabla in tablas.items():
        # El MOP contiene algún nombre con CRLF interno; publicar CSV con LF.
        # Los originales conservan sus bytes y hashes sin modificación.
        csv = tabla.to_csv(index=False).replace("\r\n", "\n").replace("\r", "\n")
        (a.salida / (nombre + ".csv")).write_text(csv)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    ax[0].plot(sensibilidad.distancia_max_m, sensibilidad.precision_etiquetados, "o-", label="Precisión en etiquetados")
    ax[0].plot(sensibilidad.distancia_max_m, sensibilidad.sensibilidad_etiquetados, "o-", label="Sensibilidad en etiquetados")
    ax[0].plot(sensibilidad.distancia_max_m, sensibilidad.tramo_correcto_condicional, "o-", label="Tramo correcto entre TP")
    ax[0].set(xlabel="Distancia máxima al eje (m)", ylabel="Proporción", ylim=(0, 1.05), title="Sensibilidad; no selección de umbral")
    ax[0].legend(fontsize=8)
    r = pd.DataFrame(por_tramo)
    ax[1].scatter(r.tramo_original, r.asignables / r.eventos, s=12)
    ax[1].set(xlabel="Tramo original CONASET (km)", ylabel="Proporción candidata asignable", ylim=(0, 1.05), title="Cobertura de positivos conocidos 2024")
    fig.suptitle("Ensayo de ubicación vial: reglas congeladas; no evaluación del modelo predictivo")
    fig.savefig(a.salida / "validacion.png", dpi=160)
    plt.close(fig)
    def hashfile(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    auditoria = {"protocolo": protocolo, "protocolo_sha256": hashfile(a.protocolo),
                 "fuente_cartografia": manifiesto["fuente"], "consulta_cartografia_utc": manifiesto["consulta_utc"],
                 "manifiesto_cartografia_sha256": hashfile(a.geometria / "manifiesto.json"),
                 "fuente_conaset": m_conaset["url"], "manifiesto_conaset_sha256": hashfile(a.conaset / "manifiesto.json"),
                 "historico_sha256": hashfile("data/siniestros/ruta5_2020_2024.csv.gz"),
                 "cuarentena_sha256": hashfile("resultados/modelos/cuarentena_espacial.csv"),
                 "versiones": {"python": platform.python_version(), "numpy": np.__version__,
                               "pandas": pd.__version__, "shapely": shapely.__version__, "pyproj": pyproj.__version__},
                 "codigo_sha256": {str(f): hashfile(f) for f in
                     ["codigo/datos/ubicacion_vial.py", "codigo/datos/descargar_eje_mop.py", "codigo/evaluacion/evaluar_asignacion_vial.py"]},
                 "criterios_superados": decisiones, "admisible_para_asignacion_2025": admisible,
                 "integrado_al_modelo": False,
                 "segmentos_sur": len(indice.ix_sur), "segmentos_competidores": len(indice.ix_otras),
                 "segmentos_sur_medida_invalida": int((~indice.medida_valida & indice.sur).sum()),
                 "eventos_2024": len(d), "asignaciones_2025": asignaciones_2025,
                 "decision": ("Propuestas 2025 separadas; aún falta validar los demás insumos antes del modelo." if admisible else
                              "No se asigna 2025; revisar cartografía/etiquetas y cobertura antes de otra iteración."),
                 "limite_intervalos": "Wilson marginal por registro, sin independencia espacial/temporal acreditada; no garantiza calidad en desconocidos.",
                 "originales_cartografia": [{k: ar[k] for k in ["archivo", "sha256_respuesta", "registros"]} for ar in manifiesto["archivos"]],
                 "derivados_locales_sha256": {f.name: hashfile(f) for f in sorted(a.derivados.glob("*.csv.gz"))}}
    (a.salida / "auditoria.json").write_text(json.dumps(auditoria, ensure_ascii=False, indent=2) + "\n")
    print(principal.to_string())
    print("Criterios:", decisiones)
    print(f"Se conservan modelos; propuestas 2025 asignables: {asignaciones_2025}. Salidas:", a.salida)


if __name__ == "__main__":
    main()
