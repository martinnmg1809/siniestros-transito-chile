"""Auditoría de TMDA por rama y cobertura espacial, sin imputar flujo desconocido.

python flujo_vehicular.py --descargar
python flujo_vehicular.py

La cercanía propone candidatos, no valida la rama ni su disponibilidad histórica.
Los offsets requieren una tabla de exposición explícitamente documentada.
"""
import argparse
import datetime
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from datos_ruta5 import cargar_eventos, referencia_entrenamiento
from fuentes import descargar_capa

BASE = "https://rest-sit.mop.gob.cl/arcgis/rest/services/VIALIDAD/Plan_Nacional_de_Censos/MapServer"


def clasificar_rol(valor):
    """Distinguir un código vial de un marcador o una rama sin rol informado."""
    if pd.isna(valor) or not str(valor).strip():
        return "ausente"
    texto = "".join(str(valor).upper().split())
    if re.fullmatch(r"[-–—]+", texto) or texto == "0":
        return "marcador"
    if texto in {"S/ROL", "S/R", "SINROL", "S/I", "SININFORMACIÓN", "SININFORMACION"}:
        return "sin_rol_identificado"
    return "identificado"


def normalizar_ramas(carpeta):
    filas = []
    for p in sorted(Path(carpeta).glob("capa_[0-9].json")):
        capa = int(p.stem.split("_")[-1])
        for f in json.loads(p.read_text())["features"]:
            a, g = f["attributes"], f.get("geometry") or {}
            anio = a.get("AÑO", a.get("ANO"))
            for rama in range(1, 5):
                rol = str(a.get(f"ROL_RAMA_{rama}") or "").strip().upper()
                if not rol:
                    continue
                tmda = pd.to_numeric(a.get(f"TMDA_RAMA_{rama}"), errors="coerce")
                filas.append({"capa": capa, "objectid": a.get("OBJECTID"),
                              "estacion": a.get("ESTACION_DE_CONTROL"), "rama": rama,
                              "rol": rol, "nombre_rama": a.get(f"NOMBRE_RAMA_{rama}"),
                              "anio_medicion": anio, "tmda": tmda,
                              "tmda_valido": bool(pd.notna(tmda) and tmda > 0),
                              "lat": g.get("y"), "lon": g.get("x"),
                              "region": a.get("REGIÓN", a.get("REGION")),
                              "fuente": f"{BASE}/{capa}",
                              "ruta5": bool(re.fullmatch(r"(?:RUTA\s*)?5", rol)),
                              "disponible_desde": ""})
    if not filas:
        raise ValueError("No hay capas; ejecutar primero --descargar")
    return pd.DataFrame(filas)


def proyectar_estaciones(ramas, referencia):
    """Proyección aproximada al eje histórico; solo diagnóstico de cobertura."""
    candidatos = ramas.loc[ramas.ruta5 & ramas.tmda_valido].copy()
    lat0 = np.deg2rad(referencia.lat.mean())
    escala = np.array([111.195 * np.cos(lat0), 111.195])
    puntos = referencia[["lon", "lat"]].to_numpy() * escala
    a, vector = puntos[:-1], np.diff(puntos, axis=0)
    den = (vector ** 2).sum(axis=1)
    if (den <= 0).any():
        raise ValueError("Geometría de referencia degenerada")
    km = referencia.tramo.to_numpy() + 2.5
    salida = []
    for r in candidatos.to_dict("records"):
        p = np.array([r["lon"], r["lat"]]) * escala
        t = np.clip(((p - a) * vector).sum(axis=1) / den, 0, 1)
        dist = np.sqrt(((p - (a + t[:, None] * vector)) ** 2).sum(axis=1))
        j = np.argmin(dist)
        salida.append({**r, "km_proyectado": km[j] + t[j] * (km[j + 1] - km[j]),
                       "distancia_eje_km": dist[j], "rama_validada": False})
    return pd.DataFrame(salida)


def exposicion_vehiculo_km(tabla, tiempos, tramos, fecha_corte, tramo_km=5):
    """Offsets de filas tramo/año documentadas, sin relleno de cobertura faltante.

    Columnas: tramo, anio_objetivo, tmda, disponible_desde, fuente, metodo.
    metodo='validado' acredita correspondencia vial por rama o tramo. Distribuir
    TMDA/24 es una aproximación uniforme; no controla variaciones horarias.
    La tabla debe usar valores publicados antes de fecha_corte.
    """
    requeridas = {"tramo", "anio_objetivo", "tmda", "disponible_desde", "fuente", "metodo"}
    if not requeridas <= set(tabla.columns):
        raise ValueError(f"Faltan columnas: {sorted(requeridas - set(tabla.columns))}")
    tabla = tabla.copy()
    if tabla.duplicated(["tramo", "anio_objetivo"]).any():
        raise ValueError("Exposiciones duplicadas para tramo/año")
    fechas = pd.to_datetime(tabla.disponible_desde, errors="coerce")
    tmda = pd.to_numeric(tabla.tmda, errors="coerce")
    valida = (fechas.notna() & fechas.le(pd.Timestamp(fecha_corte))
              & tabla.metodo.eq("validado") & tabla.fuente.fillna("").str.strip().ne("")
              & tmda.gt(0) & np.isfinite(tmda))
    if not valida.all():
        raise ValueError("TMDA sin validar, sin fuente, faltante o disponible después del corte")
    ix = tabla.set_index(["tramo", "anio_objetivo"])["tmda"]
    tiempos = pd.DatetimeIndex(tiempos)
    out = np.full((len(tramos), len(tiempos)), np.nan)
    for i, tramo in enumerate(tramos):
        for anio in np.unique(tiempos.year):
            if (tramo, anio) in ix.index:
                out[i, tiempos.year == anio] = float(ix.loc[(tramo, anio)]) * tramo_km / 24
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--descargar", action="store_true")
    p.add_argument("--fuentes", type=Path, default=Path("data/fuentes/mop"))
    p.add_argument("--salida", type=Path, default=Path("resultados/flujo"))
    args = p.parse_args()
    if args.descargar:
        for capa in range(6):
            descargar_capa(f"{BASE}/{capa}", args.fuentes, f"capa_{capa}")
            print(f"Capa {capa} descargada", flush=True)
    ramas = normalizar_ramas(args.fuentes)
    datos, auditoria = cargar_eventos()
    ref = referencia_entrenamiento(datos)
    candidatos = proyectar_estaciones(ramas, ref)
    args.salida.mkdir(parents=True, exist_ok=True)
    ramas.to_csv(args.salida / "ramas_mop.csv", index=False)
    candidatos.to_csv(args.salida / "candidatos_ruta5.csv", index=False)
    ref.to_csv(args.salida / "referencia_entrenamiento.csv", index=False)
    # No asignar flujo: reportar cuánto podría investigarse con umbrales explícitos.
    cobertura = []
    for anio in (2022, 2023, 2024):
        pasados = candidatos.loc[candidatos.anio_medicion.lt(anio)
                                & candidatos.distancia_eje_km.le(2)].copy()
        for alcance in (5, 10, 25):
            dist = (np.min(abs(ref.tramo.to_numpy()[:, None] + 2.5
                              - pasados.km_proyectado.to_numpy()), axis=1)
                    if len(pasados) else np.full(len(ref), np.inf))
            cubierto = dist <= alcance
            tramos = ref.loc[cubierto, "tramo"]
            test = datos.loc[datos.anio.eq(anio)]
            cobertura.append({"anio": anio, "alcance_longitudinal_km": alcance,
                              "distancia_max_eje_km": 2,
                              "tramos_candidatos": int(cubierto.sum()), "tramos_total": len(ref),
                              "siniestros_en_tramos_candidatos": int(test.tramo.isin(tramos).sum()),
                              "siniestros_total": len(test), "tramos_con_exposicion_validada": 0,
                              "nota": "Candidato espacial; no acredita rama, continuidad ni publicación previa"})
    pd.DataFrame(cobertura).to_csv(args.salida / "cobertura.csv", index=False)
    # Plantilla vacía deliberadamente: no convertir candidatos en denominadores.
    plantilla = args.salida / "exposicion_validada.csv"
    if not plantilla.exists():
        pd.DataFrame(columns=["tramo", "anio_objetivo", "tmda", "disponible_desde", "fuente", "metodo"]).to_csv(plantilla, index=False)
    descargas = [json.loads(p.read_text()) for p in sorted(args.fuentes.glob("capa_*_descarga.json"))]
    duplicados = ramas.loc[ramas.ruta5].groupby(["estacion", "rama", "anio_medicion"]).tmda.agg(["size", "nunique"])
    manifiesto = {"auditoria_eventos": auditoria, "generado_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "descargas": descargas,
                  "ramas": len(ramas), "ramas_ruta5": int(ramas.ruta5.sum()),
                  "claves_estacion_rama_anio_repetidas": int((duplicados["size"] > 1).sum()),
                  "claves_con_tmda_discrepante_entre_capas": int((duplicados["nunique"] > 1).sum()),
                  "nota": "No se suman ramas ni se deduce el año del nombre de la capa. Fechas de publicación histórica no acreditadas."}
    (args.salida / "auditoria.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2))
    print(pd.DataFrame(cobertura).to_string(index=False))


if __name__ == "__main__":
    main()
