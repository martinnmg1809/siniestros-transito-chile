#!/usr/bin/env python3
"""EDA de siniestros, PNCV, Concesiones y ERA5 antes de seleccionar modelos.

No descarga, entrena, recalibra ni publica modelos. Lee las fuentes originales
locales, conserva sus versiones y genera tablas, figuras y un resumen en README.
Uso: .venv/bin/python explorar_datos.py --actualizar-readme
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/siniestros-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from clima_utc import cargar_cache
from datos_ruta5 import cargar_eventos, referencia_entrenamiento, grilla_civil, exposicion_civil
from flujo_concesiones import FUENTES, extraer
from flujo_vehicular import normalizar_ramas, proyectar_estaciones, clasificar_rol

ANIOS_CAPA = {0: {2024, 2025}, 1: {2022, 2023}, 2: {2020, 2021},
              3: {2018, 2019}, 4: {2016, 2017}, 5: {2014, 2015}}
MARCAS = ("<!-- INICIO_EDA_ENTREGA3 -->", "<!-- FIN_EDA_ENTREGA3 -->")


def guardar(tabla, carpeta, nombre):
    tabla.to_csv(carpeta / f"{nombre}.csv", index=False)


def perfil_numerico(valores):
    """Separar faltante, cero, negativo e infinito antes de describir positivos."""
    x = pd.to_numeric(pd.Series(valores), errors="coerce")
    finito = np.isfinite(x)
    positivos = x.loc[finito & x.gt(0)]
    q = positivos.quantile([.01, .25, .5, .75, .95, .99])
    return {"filas": len(x), "faltantes": int(x.isna().sum()),
            "infinitos": int((x.notna() & ~finito).sum()), "ceros": int(x.eq(0).sum()),
            "negativos": int(x.lt(0).sum()), "positivos": len(positivos),
            "min_positivo": positivos.min(), "media_positivos": positivos.mean(),
            "p01": q.get(.01), "q25": q.get(.25), "mediana": q.get(.5),
            "q75": q.get(.75), "p95": q.get(.95), "p99": q.get(.99),
            "max": positivos.max(), "asimetria_positivos": positivos.skew()}


def comparar_versiones(dgc):
    """Cada versión conserva una sola fila por contrato/período; nunca sumarlas."""
    claves = ["contrato", "anio", "trimestre"]
    if dgc.duplicated(["version_anexo"] + claves).any():
        raise ValueError("La fuente tiene contratos/períodos duplicados dentro de una versión")
    versiones = sorted(dgc.version_anexo.unique())
    if len(versiones) != 2:
        raise ValueError("Esta comparación espera los dos anexos documentados")
    antigua, nueva = versiones
    campos = ["transacciones_trimestre", "pasadas_promedio_por_punto_mes"]
    a = dgc.loc[dgc.version_anexo.eq(antigua), claves + campos]
    b = dgc.loc[dgc.version_anexo.eq(nueva), claves + campos]
    revision = a.merge(b, on=claves, suffixes=("_anterior", "_actual"), validate="one_to_one")
    for campo in campos:
        revision[f"diferencia_{campo}"] = revision[f"{campo}_actual"] - revision[f"{campo}_anterior"]
        revision[f"cambio_{campo}"] = ~np.isclose(revision[f"{campo}_actual"], revision[f"{campo}_anterior"],
                                                  rtol=1e-10, atol=1e-6)
    # Vista descriptiva actual: preservar qué anexo aporta cada fila.
    canon = (dgc.sort_values("version_anexo").drop_duplicates(claves, keep="last")
             .sort_values(claves).reset_index(drop=True))
    canon["periodo"] = canon.anio.astype(str) + "T" + canon.trimestre.astype(str)
    canon["puntos_cobro_implicitos"] = canon.transacciones_trimestre / (3 * canon.pasadas_promedio_por_punto_mes)
    canon["puntos_cerca_entero"] = np.isclose(canon.puntos_cobro_implicitos, canon.puntos_cobro_implicitos.round(), atol=1e-6)
    canon["cambio_puntos"] = canon.groupby("contrato").puntos_cobro_implicitos.diff().abs().gt(1e-6)
    return canon, revision


def cobertura_espacial(candidatos, referencia, eventos):
    """Sensibilidad a distancia y antigüedad, sin acreditar una exposición válida."""
    filas = []
    for anio in (2022, 2023, 2024):
        test = eventos.loc[eventos.anio.eq(anio)]
        for edad_max in (2, 4, 10, None):
            c = candidatos.loc[candidatos.distancia_eje_km.le(2) & candidatos.anio_medicion.lt(anio)].copy()
            if edad_max is not None:
                c = c.loc[(anio - c.anio_medicion).le(edad_max)]
            # Repetir una rama en dos capas no crea dos estaciones nuevas.
            c = c.drop_duplicates(["estacion", "anio_medicion", "lat", "lon"])
            for alcance in (5, 10, 25):
                dist = (np.min(abs(referencia.tramo.to_numpy()[:, None] + 2.5
                                  - c.km_proyectado.to_numpy()), axis=1)
                        if len(c) else np.full(len(referencia), np.inf))
                mask = dist <= alcance
                tramos = referencia.loc[mask, "tramo"]
                filas.append({"anio": anio, "antiguedad_max_anios": edad_max if edad_max else "sin_limite",
                              "alcance_longitudinal_km": alcance, "distancia_max_eje_km": 2,
                              "estaciones_candidatas": c.estacion.nunique(), "tramos_candidatos": int(mask.sum()),
                              "tramos_total": len(referencia), "porcentaje_tramos": 100 * mask.mean(),
                              "siniestros_candidatos": int(test.tramo.isin(tramos).sum()), "siniestros_total": len(test),
                              "porcentaje_siniestros": 100 * test.tramo.isin(tramos).mean(),
                              "disponibilidad_historica_acreditada": False})
    return pd.DataFrame(filas)


def discordancias_espaciales(eventos, referencia):
    """Distancia al punto histórico del mismo tramo: bandera, no nueva ubicación.

    Umbrales de 5/10/25 km se usan para sensibilidad. La referencia aproximada no
    permite decidir por sí sola si está mal el kilómetro, la ruta o la coordenada.
    """
    ref = referencia.set_index("tramo").reindex(eventos.tramo)
    d = eventos[["ID", "FECHA", "Ruta", "REGION", "COMUNA", "km", "tramo", "Latitud", "longitud"]].copy()
    d["lat_referencia"] = ref.lat.to_numpy()
    d["lon_referencia"] = ref.lon.to_numpy()
    # Haversine para evitar depender de una proyección plana sobre todo Chile.
    lat1, lat2 = np.deg2rad(d.Latitud), np.deg2rad(d.lat_referencia)
    dl = np.deg2rad(d.longitud - d.lon_referencia)
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dl / 2) ** 2
    d["distancia_referencia_km"] = 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    for umbral in (5, 10, 25):
        d[f"bandera_mayor_{umbral}km"] = d.distancia_referencia_km.gt(umbral)
    return d


def analizar_eventos(eventos, raw, salida):
    criticos = ["ID", "FECHA", "Hora_aprox", "Ubicación", "Latitud", "longitud"]
    calidad = pd.DataFrame({"campo": criticos,
                           "faltantes": [int(raw[c].isna().sum()) for c in criticos]})
    guardar(calidad, salida, "siniestros_faltantes")
    anual = eventos.groupby("anio").agg(siniestros=("ID", "size"), fallecidos=("FALLECIDOS", "sum"),
                                         lesionados=("TOTAL_LESI", "sum"), tramos_con_eventos=("tramo", "nunique")).reset_index()
    guardar(anual, salida, "siniestros_anuales")
    diario = eventos.groupby("fecha").size().reindex(pd.date_range("2020-01-01", "2024-12-31"), fill_value=0)
    guardar(diario.rename("siniestros").rename_axis("fecha").reset_index(), salida, "siniestros_diarios")
    por_tramo = eventos.groupby("tramo").agg(siniestros=("ID", "size"), fallecidos=("FALLECIDOS", "sum"),
                                             urbanos=("ZONA", lambda s: s.eq("URBANA").sum())).reset_index()
    guardar(por_tramo, salida, "siniestros_por_tramo")
    perfiles = [{"variable": c, **perfil_numerico(eventos[c])} for c in ["km", "FALLECIDOS", "TOTAL_LESI"]]
    guardar(pd.DataFrame(perfiles), salida, "siniestros_distribuciones")
    banderas = discordancias_espaciales(eventos, referencia_entrenamiento(eventos))
    guardar(banderas.loc[banderas.bandera_mayor_5km].sort_values("distancia_referencia_km", ascending=False),
            salida, "siniestros_discordancia_km_coordenadas")
    excluidos = raw.loc[~pd.to_numeric(raw["Ubicación"], errors="coerce").between(0, 2200, inclusive="neither")]
    guardar(excluidos, salida, "siniestros_excluidos_por_km")
    guardar(banderas.groupby("FECHA").bandera_mayor_10km.sum().loc[lambda s: s > 0].rename("banderas").reset_index(),
            salida, "siniestros_fechas_con_discordancia")
    minutos = pd.to_datetime(raw.Hora, format="%H:%M:%S", errors="coerce").dt.minute
    resumen = {"ids_duplicados": int(raw.ID.duplicated().sum()),
               "filas_duplicadas_completas": int(raw.duplicated().sum()),
               "faltantes_criticos": int(calidad.faltantes.sum()),
               "hora_invalida": int(pd.to_datetime(raw.Hora, format="%H:%M:%S", errors="coerce").isna().sum()),
               "minutos_multiplos_5_pct": float(100 * minutos.mod(5).eq(0).mean()),
               "km_enteros_pct": float(100 * eventos.km.mod(1).eq(0).mean()),
               "dias_sin_eventos": int(diario.eq(0).sum()), "max_diario": int(diario.max()),
               "rho_km_latitud": float(spearmanr(eventos.km, eventos.Latitud).statistic),
               "severidad_negativa": int((eventos[["FALLECIDOS", "TOTAL_LESI", "GRAVES", "MENOS_GRAV", "LEVES"]] < 0).any(axis=1).sum()),
               "lesionados_incoherentes": int(eventos.TOTAL_LESI.ne(eventos.GRAVES + eventos.MENOS_GRAV + eventos.LEVES).sum()),
               "urbanos_pct": float(100 * eventos.ZONA.eq("URBANA").mean()),
               "top_tramos_n": int(np.ceil(.1 * len(por_tramo))), "tramos_total": len(por_tramo),
               "discordantes_mas_5km": int(banderas.bandera_mayor_5km.sum()),
               "discordantes_mas_10km": int(banderas.bandera_mayor_10km.sum()),
               "discordantes_mas_25km": int(banderas.bandera_mayor_25km.sum()),
               "discordancia_max_km": float(banderas.distancia_referencia_km.max()),
               "top10pct_tramos_concentracion_pct": float(100 * por_tramo.siniestros.nlargest(int(np.ceil(.1 * len(por_tramo)))).sum() / len(eventos))}
    return anual, por_tramo, resumen


def analizar_mop(ramas, carpeta, salida):
    ramas = ramas.copy()
    ramas["tipo_rol"] = ramas.rol.map(clasificar_rol)
    ramas["estado_tmda"] = np.select([ramas.tmda.isna(), ~np.isfinite(ramas.tmda), ramas.tmda.lt(0), ramas.tmda.eq(0)],
                                     ["faltante", "no_finito", "negativo", "cero"], default="positivo")
    guardar(ramas.groupby(["tipo_rol", "estado_tmda"]).size().rename("filas").reset_index(), salida, "mop_cruce_rol_tmda")
    # Perfil sin inflar frecuencias por copias idénticas entre capas.
    claves = ["estacion", "rama", "anio_medicion", "rol"]
    duplicados = ramas.groupby(claves, dropna=False).agg(filas=("capa", "size"),
                    capas=("capa", lambda x: ",".join(map(str, sorted(x.unique())))),
                    tmda_distintos=("tmda", lambda x: x.nunique(dropna=False))).reset_index()
    guardar(duplicados.loc[duplicados.filas.gt(1)], salida, "mop_duplicados_entre_capas")
    unicas = ramas.sort_values("capa").drop_duplicates(claves).copy()
    unicas["tmda_categoria"] = np.select([unicas.tmda.isna(), ~np.isfinite(unicas.tmda), unicas.tmda.lt(0), unicas.tmda.eq(0)],
                                         ["faltante", "no_finito", "negativo", "cero_sin_interpretar"], default="positivo")
    perfil = []
    for nombre, d in [("todas_filas", ramas), ("claves_unicas", unicas),
                       ("rol_identificado_claves_unicas", unicas.loc[unicas.tipo_rol.eq("identificado")]),
                       ("ruta5_claves_unicas", unicas.loc[unicas.ruta5])]:
        perfil.append({"poblacion": nombre, **perfil_numerico(d.tmda)})
    guardar(pd.DataFrame(perfil), salida, "mop_distribucion_tmda")
    guardar(unicas.groupby(["anio_medicion", "tmda_categoria"]).size().rename("filas").reset_index(), salida, "mop_calidad_por_anio")
    capas = []
    slots = []
    for capa in range(6):
        meta = json.loads((carpeta / f"capa_{capa}_metadata.json").read_text())
        fuente = json.loads((carpeta / f"capa_{capa}.json").read_text())
        r = ramas.loc[ramas.capa.eq(capa)]
        for f in fuente["features"]:
            a = f["attributes"]
            for k in range(1, 5):
                rol = str(a.get(f"ROL_RAMA_{k}") or "").strip()
                v = pd.to_numeric(a.get(f"TMDA_RAMA_{k}"), errors="coerce")
                slots.append({"capa": capa, "objectid": a.get("OBJECTID"), "rama": k,
                              "estacion": a.get("ESTACION_DE_CONTROL"), "anio_medicion": a.get("AÑO", a.get("ANO")),
                              "rol_original": rol, "tipo_rol": clasificar_rol(rol), "tmda": v,
                              "rol_vacio": not bool(rol), "tmda_positivo_sin_rol": not bool(rol) and pd.notna(v) and v > 0})
        capas.append({"capa": capa, "titulo": meta["name"], "estaciones_en_fuente": len(fuente["features"]),
                      "ramas_con_rol": len(r), "anios_observados": ",".join(map(str, sorted(r.anio_medicion.unique()))),
                      "filas_fuera_anios_titulo": int((~r.anio_medicion.isin(ANIOS_CAPA[capa])).sum()),
                      "tmda_cero": int(r.tmda.eq(0).sum()), "tmda_faltante": int(r.tmda.isna().sum())})
    capas = pd.DataFrame(capas)
    guardar(capas, salida, "mop_capas_y_anios")
    guardar(pd.DataFrame(slots).groupby("capa").agg(slots=("rama", "size"), rol_vacio=("rol_vacio", "sum"),
                                                        tmda_positivo_sin_rol=("tmda_positivo_sin_rol", "sum")).reset_index(), salida, "mop_ramas_sin_rol")
    slots = pd.DataFrame(slots)
    guardar(slots.loc[slots.tipo_rol.ne("identificado") & slots.tmda.gt(0)], salida, "mop_tmda_positivos_sin_codigo_vial")
    coords_invalidas = ~(np.isfinite(ramas.lat) & np.isfinite(ramas.lon)
                         & ramas.lat.between(-56, -17) & ramas.lon.between(-76, -66))
    ruta = unicas.loc[unicas.ruta5].copy()
    guardar(ruta, salida, "mop_ruta5_claves_unicas")
    # Valores extremos se identifican, no se eliminan: no hay evidencia de error.
    positivos = unicas.loc[unicas.tmda.gt(0) & np.isfinite(unicas.tmda)]
    guardar(positivos.nlargest(20, "tmda"), salida, "mop_tmda_mayores_20")
    resumen = {"filas_ramas": len(ramas), "claves_unicas": len(unicas), "ruta5_claves_unicas": len(ruta),
               "claves_repetidas": int(duplicados.filas.gt(1).sum()),
               "claves_repetidas_con_conflicto": int((duplicados.filas.gt(1) & duplicados.tmda_distintos.gt(1)).sum()),
               "filas_ruta5_2020": int(ruta.anio_medicion.eq(2020).sum()),
               "coordenadas_invalidas": int(coords_invalidas.sum()),
               "slots_tmda_positivo_sin_rol": int(pd.DataFrame(slots).tmda_positivo_sin_rol.sum()),
               "tmda_cero": int(ramas.tmda.eq(0).sum()), "tmda_faltante": int(ramas.tmda.isna().sum()),
               "ruta5_tmda_faltantes": int(ruta.tmda.isna().sum()),
               "ceros_con_rol_marcador": int((ramas.tmda.eq(0) & ramas.tipo_rol.eq("marcador")).sum()),
               "fecha_disponibilidad_faltante": int(ramas.disponible_desde.fillna("").eq("").sum())}
    return unicas, capas, resumen


def analizar_clima(eventos, ref, salida, archivo):
    z = cargar_cache(archivo)
    t, y, fuera = grilla_civil(eventos, ref.tramo.to_numpy())
    if not np.array_equal(t.to_numpy(dtype="datetime64[h]"), z["tiempo"]) or not np.array_equal(ref.tramo, z["tramos"]):
        raise ValueError("Caché y referencia de EDA incompatibles")
    e = exposicion_civil(t)
    if not np.array_equal(e, z["exposicion_tiempo"]):
        raise ValueError("Exposición meteorológica incompatible con calendario chileno")
    p = z["precip"]
    ptr = p[z["idx_celda"]]
    real = e > 0
    datos = ptr[:, real].ravel()
    perfil = {"unidad": "mm/h", **perfil_numerico(datos)}
    guardar(pd.DataFrame([perfil]), salida, "clima_distribucion_tramo_hora")
    filas = []
    cat = np.digitize(ptr, [.1, .5])
    for anio in (2020, 2021, 2022, 2023, 2024):
        columnas = (t.year == anio) & real
        for k, nombre in enumerate(["seco (<0.1)", "llovizna [0.1,0.5)", "lluvia (>=0.5)"]):
            mask = cat[:, columnas] == k
            expo = (mask * e[columnas]).sum()
            cuenta = y[:, columnas][mask].sum()
            filas.append({"anio": anio, "categoria": nombre, "exposicion_tramo_horas": expo,
                          "siniestros": int(cuenta), "siniestros_por_1000_tramo_horas": 1000 * cuenta / expo,
                          "nota": "Tasa cruda sin ajuste de calendario, ubicación ni flujo vehicular"})
    tab = pd.DataFrame(filas)
    guardar(tab, salida, "clima_siniestros_crudo_por_anio")
    hist = pd.Series(y[:, real].ravel()).value_counts().sort_index().rename_axis("siniestros_en_celda").rename("celdas").reset_index()
    guardar(hist, salida, "siniestros_distribucion_celda")
    resumen = {"celdas_era5": len(p), "tramos": len(ref), "etiquetas_civiles": len(t),
               "etiquetas_inexistentes_dst": int((e == 0).sum()), "etiquetas_repetidas_dst": int((e == 2).sum()),
               "nan_estructurales_era5": int(np.isnan(p[:, ~real]).sum()),
               "faltantes_horas_existentes": int((~np.isfinite(p[:, real])).sum()),
               "precipitacion_negativa": int((p[:, real] < 0).sum()),
               "pct_0mm_tramo_etiqueta": float(100 * (datos == 0).mean()),
               "max_mm_h": float(np.nanmax(p)), "celdas_sin_eventos_pct": float(100 * (y[:, real] == 0).mean()),
               "siniestros_hora_inexistente": int(y[:, ~real].sum()), "fuera_dominio": fuera,
               "limites": "Duplicación de valores al mapear ERA5 a tramos; las celdas no son mediciones meteorológicas independientes. Tasa cruda, no efecto causal ni por vehículo."}
    return tab, hist, resumen


def analizar_calendario(eventos, archivo, salida):
    fer = json.loads(archivo.read_text())
    fechas = pd.date_range("2020-01-01", "2024-12-31")
    conteos = eventos.groupby("fecha").size().reindex(fechas, fill_value=0)
    filas = []
    for fecha, n in conteos.items():
        valor = fer.get(fecha.date().isoformat(), {})
        pos = valor.get("dia", "no")
        if pos not in ("no", "inicio", "intermedio", "final"):
            raise ValueError("Posición desconocida en calendario")
        filas.append({"fecha": fecha.date().isoformat(), "anio": fecha.year, "posicion": pos, "siniestros": int(n)})
    tabla = pd.DataFrame(filas)
    resumen_dias = tabla.groupby(["anio", "posicion"]).agg(dias=("fecha", "size"),
                    siniestros=("siniestros", "sum"), media_diaria=("siniestros", "mean")).reset_index()
    resumen_dias["nota"] = "Comparación cruda; sin ajuste por flujo, hora, época del año o ubicación"
    guardar(resumen_dias, salida, "feriados_descriptivo_por_anio")
    dentro = [f for f in fer if "2020-01-01" <= f <= "2024-12-31"]
    return {"fechas_en_fuente": len(fer), "fechas_en_periodo": len(dentro),
            "min_fecha_marcada": min(fer), "max_fecha_marcada": max(fer),
            "nota": "Calendario histórico derivado de CONASET; ausencia de una fecha no acredita día no feriado fuera de cobertura. No se verificó exhaustividad legal."}


def figuras(eventos, anual, tramo, unicas, capas, candidatos, ref, cobertura, dgc, clima, hist, salida):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    color = "#28658a"
    def fin(fig, nombre, rect=None):
        fig.tight_layout(rect=rect)
        fig.savefig(salida / f"{nombre}.png", dpi=160, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    ax[0, 0].bar(anual.anio.astype(str), anual.siniestros, color=color)
    ax[0, 0].set(title="Siniestros por año", ylabel="Registros")
    ax[0, 1].bar(tramo.tramo, tramo.siniestros, width=5, color=color)
    ax[0, 1].set(title="Concentración espacial", xlabel="Inicio del tramo (km)", ylabel="Siniestros 2020–2024")
    h = pd.crosstab(eventos.fecha.dt.dayofweek, eventos.hora).reindex(index=range(7), columns=range(24), fill_value=0)
    im = ax[1, 0].imshow(h, aspect="auto", cmap="YlOrRd")
    ax[1, 0].set(title="Calendario de siniestros", xlabel="Hora local", yticks=range(7), yticklabels=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"])
    fig.colorbar(im, ax=ax[1, 0], label="Registros")
    ax[1, 1].scatter(eventos.km, eventos.Latitud, s=2, alpha=.12, color=color, rasterized=True)
    banderas = discordancias_espaciales(eventos, ref)
    malas = banderas.loc[banderas.bandera_mayor_10km]
    ax[1, 1].scatter(malas.km, malas.Latitud, marker="x", color="#b54548", s=50,
                     label=f"{len(malas)} discordancias para revisar")
    ax[1, 1].set(title="Consistencia del kilometraje y latitud", xlabel="Kilometraje declarado", ylabel="Latitud")
    ax[1, 1].legend(fontsize=8)
    fin(fig, "01_siniestros")

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    positivo = unicas.loc[unicas.tipo_rol.eq("identificado") & unicas.tmda.gt(0) & np.isfinite(unicas.tmda), "tmda"]
    ax[0].hist(positivo, bins=np.geomspace(positivo.min(), positivo.max(), 40), color=color)
    ax[0].set(xscale="log", title="TMDA positivos: rol identificado, claves únicas", xlabel="Vehículos/día (escala log)", ylabel="Ramas")
    matriz = unicas.groupby(["anio_medicion"]).tmda.agg(positivo=lambda x: (x > 0).sum(), cero=lambda x: (x == 0).sum(), faltante=lambda x: x.isna().sum())
    matriz.plot.bar(stacked=True, ax=ax[1], color=[color, "#ca8b2c", "#b54548"])
    ax[1].set(title="Calidad por año medido\n(incluye roles sin identificar)", xlabel="Año del registro", ylabel="Ramas únicas")
    fin(fig, "02_mop_distribucion_calidad")

    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    cerca = candidatos.loc[candidatos.distancia_eje_km.le(2)].drop_duplicates(["estacion", "anio_medicion"])
    for anio, g in cerca.groupby("anio_medicion"):
        ax[0].scatter(g.km_proyectado, np.repeat(anio, len(g)), label=str(anio), s=32)
    ax[0].set(xlim=(0, 1275), title="Estaciones candidatas a ≤2 km del eje aproximado", xlabel="Km proyectado (no kilometraje oficial)", ylabel="Año de medición")
    cc = cobertura.loc[cobertura.anio.eq(2024)]
    for edad, g in cc.groupby("antiguedad_max_anios", sort=False):
        etiqueta = "sin límite" if edad == "sin_limite" else str(edad)
        estilo = "--" if edad in (4, "sin_limite") else "-"
        ax[1].plot(g.alcance_longitudinal_km, g.porcentaje_tramos, marker="o", linestyle=estilo,
                   label=f"Antigüedad: {etiqueta}")
    ax[1].set(title="Cobertura candidata 2024 según supuestos", xlabel="Alcance longitudinal supuesto (km)", ylabel="% de tramos", ylim=(0, 100))
    ax[1].legend(fontsize=8)
    fin(fig, "03_mop_cobertura_antiguedad")

    fig, ax = plt.subplots(figsize=(6, 8))
    ax.plot(ref.lon, ref.lat, color="#999999", lw=1.5, label="Eje aproximado, referencia 2020–2021")
    reciente = cerca.loc[cerca.anio_medicion.isin([2022, 2024])]
    antigua = cerca.loc[cerca.anio_medicion.eq(2014)]
    ax.scatter(antigua.lon, antigua.lat, marker="x", color="#ca8b2c", label="Candidatas de 2014")
    ax.scatter(reciente.lon, reciente.lat, s=28, color=color, label="Candidatas de 2022/2024")
    ax.set(title="Cobertura espacial: no uniforme a lo largo de Ruta 5 Sur", xlabel="Longitud", ylabel="Latitud")
    ax.legend(loc="upper left", fontsize=8)
    fin(fig, "04_mop_cobertura_espacial")

    fig, ax = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    for nombre, g in dgc.groupby("contrato"):
        g = g.sort_values(["anio", "trimestre"])
        ax[0].plot(np.arange(len(g)), g.proxy_pasadas_por_punto_dia, marker=".", label=nombre)
        ax[1].step(np.arange(len(g)), g.puntos_cobro_implicitos, where="mid", label=nombre)
    etiquetas = dgc.drop_duplicates(["anio", "trimestre"]).sort_values(["anio", "trimestre"]).periodo
    ax[0].set(title="DGC: promedio de pasadas por punto y día (proxy)", ylabel="Pasadas/punto/día")
    handles, labels = ax[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, .005), fontsize=8, ncol=2, frameon=False)
    ax[1].set(title="Cantidad implícita de puntos de cobro: cambios de composición", ylabel="Puntos implícitos", xticks=np.arange(len(etiquetas)), xticklabels=etiquetas)
    ax[1].tick_params(axis="x", labelrotation=60)
    fin(fig, "05_dgc_series_y_puntos_cobro", rect=(0, .12, 1, 1))

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for cat, g in clima.groupby("categoria", sort=False):
        ax[0].plot(g.anio, g.siniestros_por_1000_tramo_horas, marker="o", label=cat)
    ax[0].set(title="Lluvia y siniestros: comparación cruda", xlabel="Año", ylabel="Siniestros / 1.000 tramo-horas", xticks=range(2020, 2025))
    ax[0].legend(fontsize=8)
    ax[1].bar(hist.siniestros_en_celda.astype(str), hist.celdas, color=color)
    ax[1].set(yscale="log", title="Distribución de siniestros por celda", xlabel="Siniestros en tramo y hora", ylabel="Etiquetas tramo-hora (escala log)")
    fin(fig, "06_clima_y_conteos")


def bloque_readme(resumen, capas, cobertura, revision, cambios, dgc_anual):
    s, m, d, c = (resumen[k] for k in ["siniestros", "mop", "dgc", "clima"])
    f = resumen["calendario"]
    def numero(x, dec=0):
        return f"{x:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    tabla_capas = "\n".join(f"| {r.capa} | {r.titulo} | {r.anios_observados} | {numero(r.filas_fuera_anios_titulo)} |" for r in capas.itertuples())
    cov = cobertura.loc[cobertura.anio.eq(2024) & cobertura.alcance_longitudinal_km.eq(10)]
    tabla_cov = "\n".join(f"| {r.antiguedad_max_anios} | {r.tramos_candidatos}/255 | {numero(r.porcentaje_tramos, 1)} % | {numero(r.porcentaje_siniestros, 1)} % |" for r in cov.itertuples())
    cambios_txt = "\n".join(f"- {r.contrato}: {r.periodo}, {numero(r.puntos_cobro_implicitos, 0)} puntos implícitos (cambia respecto al trimestre anterior)." for r in cambios.itertuples())
    return f'''{MARCAS[0]}
### Bitácora del EDA previo al entrenamiento

**Fase exploratoria: 12 de noviembre de 2026.** Esta sección conserva el diagnóstico
y las decisiones al cerrar el EDA, antes de la comparación posterior de modelos.
Las corridas anteriores se conservan como comprobación de las correcciones de código.
No se entrenaron modelos durante este EDA; su código tampoco ejecuta el entrenamiento.

El análisis se reproduce sin red con:

```bash
.venv/bin/python explorar_datos.py --actualizar-readme
```

Requiere las fuentes ya descargadas. Su código está en [explorar_datos.py](explorar_datos.py)
y las tablas y figuras en [resultados/eda](resultados/eda/). Se lee cada versión original,
se registran hashes y no se modifican las fuentes ni las salidas de los modelos.

#### 1. Siniestros: población y calidad

- Ruta 5 Sur: 14.430 registros; se conservan 14.425 tras excluir cinco con km inválido.
  El filtro `km > 0` conserva la decisión anterior de tratar cero como ubicación desconocida;
  no demuestra que todo cero de kilometraje sea físicamente imposible.
- {s['ids_duplicados']} IDs duplicados, {s['faltantes_criticos']} faltantes en campos críticos,
  {s['lesionados_incoherentes']} discrepancias entre lesionados totales y su desglose, y
  {s['severidad_negativa']} registros con severidad negativa. Campos completos no prueban
  exhaustividad del registro ni ausencia de subregistro.
- La hora está redondeada: {numero(s['minutos_multiplos_5_pct'], 1)} % de minutos son múltiplos de cinco;
  {numero(s['km_enteros_pct'], 1)} % de kilómetros son enteros. Se mantiene resolución horaria y de 5 km.
- {numero(s['urbanos_pct'], 1)} % de eventos se etiquetan urbanos. El {numero(100 * s['top_tramos_n'] / s['tramos_total'], 1)} %
  de tramos con más eventos concentra {numero(s['top10pct_tramos_concentracion_pct'], 1)} % del total
  ({s['top_tramos_n']} tramos de {s['tramos_total']}). No se eliminan eventos graves ni tramos extremos por ser infrecuentes.
- **Se detectan {s['discordantes_mas_10km']} discordancias importantes entre kilómetro y coordenadas.**
  Se obtienen las mismas cinco banderas con umbrales de 5, 10 y 25 km respecto del punto
  histórico del tramo; la distancia máxima es {numero(s['discordancia_max_km'], 0)} km.
  Una correlación global alta no detectaba este problema. Las filas están identificadas
  en [siniestros_discordancia_km_coordenadas.csv](resultados/eda/siniestros_discordancia_km_coordenadas.csv).
  No se cambian kilómetros, rutas ni coordenadas por suposición y no se borran del conjunto
  principal durante este EDA: requieren revisar el registro de origen antes de reentrenar.
- La referencia espacial usa exclusivamente 2020–2021; es una aproximación de medianas e
  interpolaciones, no un eje vial oficial. Se usa para explorar cobertura, no para certificar
  la pertenencia de una estación a una rama concreta.

![Distribución de siniestros](resultados/eda/01_siniestros.png)

#### 2. PNCV del MOP: año medido, ceros y duplicaciones

- Se obtuvieron {numero(m['filas_ramas'])} filas con texto no vacío en rol a partir de seis capas
  (incluye marcadores y códigos sin identificar, no solo rutas identificadas).
  Son {numero(m['claves_unicas'])} claves distintas estación–rama–año–rol; las versiones
  no se suman como mediciones independientes.
- Hay {numero(m['tmda_cero'])} TMDA iguales a cero y {numero(m['tmda_faltante'])} faltantes
  en las filas originales con rol. Cero se conserva como **valor sin interpretar**, no se
  equipara automáticamente a ausencia de circulación ni se reemplaza por un flujo positivo.
- De esos ceros, {numero(m['ceros_con_rol_marcador'])} tienen rol marcador, principalmente `-`:
  no se deben tratar como mediciones de carreteras identificadas sin tráfico. Se cruzan
  estado de rol y TMDA antes de describir la distribución. Ruta 5 tiene
  {m['ruta5_tmda_faltantes']} faltantes en sus claves únicas.
- Se detectan {numero(m['claves_repetidas'])} claves repetidas entre capas,
  {numero(m['claves_repetidas_con_conflicto'])} con TMDA contradictorio en esas claves.
  Los resúmenes de distribución usan claves únicas; se conserva la procedencia original.
- {numero(m['coordenadas_invalidas'])} coordenadas fuera del rango de comprobación y
  {numero(m['slots_tmda_positivo_sin_rol'])} ramas con TMDA positivo pero rol vacío.
  Estar dentro del rango de Chile no valida la posición exacta en la carretera.
- **No hay registros con año de medición 2020 en esta descarga.** La capa titulada
  `2020 Sur - 2021 Norte` contiene 2021 y 2022; no se cambian esos registros a 2020.
  El problema está en la correspondencia título/contenido de la fuente y queda documentado.

| Capa | Título publicado | Años en los registros | Filas fuera de años del título |
|---|---|---|---:|
{tabla_capas}

TMDA tiene asimetría y extremos: se inspeccionan positivos en escala logarítmica y se
guardan los 20 mayores para revisión. Un extremo no se elimina sin evidencia de error.

![Distribución y calidad del TMDA](resultados/eda/02_mop_distribucion_calidad.png)

#### 3. Cobertura espacial y antigüedad: no basta con encontrar una estación cercana

La exploración mantiene solo estaciones a un máximo de 2 km del eje aproximado y prueba
alcances longitudinales de 5, 10 y 25 km, con antigüedades máximas de 2, 4 y 10 años y
sin límite. Son supuestos de sensibilidad, no radios acreditados de representatividad.
La geometría de referencia es la misma para todas las comparaciones.

Ejemplo para 2024, con alcance longitudinal supuesto de 10 km:

| Antigüedad máxima (años) | Tramos candidatos | % de tramos | % de siniestros de 2024 en ellos |
|---|---:|---:|---:|
{tabla_cov}

Las estaciones recientes cercanas se concentran en la parte sur del corredor; parte de
la cobertura aparente del resto proviene de mediciones antiguas. Los resultados no se
deben extrapolar a todos los tramos ni a la hora punta. Año de medición anterior al evento
no acredita que el dato estuviera publicado antes de predecir. Las fechas de disponibilidad
siguen sin acreditarse en las {numero(m['fecha_disponibilidad_faltante'])} filas de ramas.

![Cobertura y antigüedad](resultados/eda/03_mop_cobertura_antiguedad.png)
![Cobertura espacial](resultados/eda/04_mop_cobertura_espacial.png)

#### 4. Concesiones: versiones, períodos y unidades

- Los anexos 2023T4 y 2024T4 aportan {d['filas_versionadas']} filas de siete contratos del
  sur. Se solapan en {d['periodos_solapados']} contrato-trimestres; sumarlos duplicaría esos períodos.
- En el solapamiento se detectaron {d['revisiones_transacciones']} revisiones de transacciones
  y {d['revisiones_promedio']} revisiones de promedios por punto. Que estas dos versiones coincidan no
  acredita disponibilidad histórica ni descarta revisiones en otras versiones.
- Para descripción se conserva la versión más reciente por contrato y trimestre:
  {d['periodos_unicos']} observaciones (7 contratos × 20 trimestres, 2020–2024),
  {d['periodos_faltantes']} períodos faltantes. La versión usada queda en cada fila.
- Se distinguen **pasadas trimestrales** y **promedio mensual por punto de cobro**.
  `promedio mensual × 3 / días del trimestre` es un proxy diario por punto, no TMDA
  por tramo ni número de vehículos únicos. No se suman los promedios de siete contratos
  para inventar un tránsito medio de toda la ruta.
- `pasadas trimestrales / (3 × promedio mensual por punto)` permite revisar la cantidad
  implícita de puntos. Cambia en dos contratos; puede alterar las comparaciones de totales:

{cambios_txt}

Estas cantidades son inferidas algebraicamente de los anexos, no una verificación física
de apertura/cierre de plazas. Los crecimientos interanuales se entregan junto con los
cambios de puntos para no atribuirlos automáticamente a circulación.

Santiago–Talca incluye Acceso Sur. Los contratos del sur disponibles no equivalen por sí
solos al universo de 255 tramos, que también incluye Chiloé. No se correlacionaron conteos
por tramo con flujo por contrato sin una correspondencia vial comprobada.

![Series de Concesiones](resultados/eda/05_dgc_series_y_puntos_cobro.png)

#### 5. Clima nuevo y variable de conteo

- ERA5 explícito: {c['celdas_era5']} celdas para 255 tramos; {numero(c['etiquetas_civiles'])}
  etiquetas horarias de 2020–2024. Se comprobaron alineación temporal y exposición DST.
- Hay {c['etiquetas_inexistentes_dst']} etiquetas de hora inexistente y
  {c['etiquetas_repetidas_dst']} repetidas. Los {c['nan_estructurales_era5']} NaN
  estructurales de ERA5 corresponden a las horas inexistentes en sus celdas;
  {c['faltantes_horas_existentes']} faltantes en horas que sí existen y
  {c['siniestros_hora_inexistente']} siniestros registrados en horas inexistentes.
- {numero(c['pct_0mm_tramo_etiqueta'], 1)} % de las etiquetas tramo-hora existentes tienen
  0 mm; máximo {numero(c['max_mm_h'], 1)} mm/h. Se conservan los extremos.
- Los umbrales implementados con `np.digitize` son exactamente: seco `<0,1`, llovizna
  `0,1 ≤ p < 0,5`, lluvia `p ≥ 0,5` mm/h. El texto anterior `>0,5` no describía
  exactamente la frontera del código; la categoría de 0,5 se aclara sin cambiar el corte.
- {numero(c['celdas_sin_eventos_pct'], 2)} % de celdas sin siniestros. Los ceros abundantes
  no bastan para elegir una familia probabilística. El perfil crudo por lluvia se entrega
  sin ajuste espacial, de calendario o de flujo y no prueba un efecto causal.
- El reanálisis describe condiciones históricas; no certifica una predicción con el
  pronóstico que habría estado disponible 12 horas antes. Varios tramos comparten celda
  ERA5: repetirla no agrega observaciones meteorológicas independientes.
- Calendario: {f['fechas_en_fuente']} fechas marcadas en la fuente, {f['fechas_en_periodo']}
  dentro de 2020–2024. Se describen días y siniestros por posición en feriado, incluyendo
  días sin eventos. La primera fecha marcada es {f['min_fecha_marcada']} y la última
  {f['max_fecha_marcada']}; esos extremos no prueban exhaustividad de los feriados legales.
  No se extrapola el calendario a 2026.

![Clima y conteos](resultados/eda/06_clima_y_conteos.png)

#### Decisiones y pendientes registrados al cerrar el EDA

1. Mantener PNCV y DGC separados: unidad estación/rama/año versus contrato/trimestre.
2. Revisar los cinco siniestros con discordancia espacial y resolver su tratamiento;
   los filtros originales de kilometraje no bastaban para comprobar ubicación.
3. Resolver el año faltante 2020 y documentar antigüedad/fechas de publicación antes de
   proponer exposición histórica. No renombrar mediciones para completar una serie.
4. Construir o conseguir una correspondencia documentada estación/rama o contrato →
   tramo. La cercanía y los límites de una concesión no prueban un flujo homogéneo.
5. Aclarar los ceros de TMDA y los cambios de puntos de cobro; mantener faltantes como tales.
6. Mantener vacía la tabla de exposición validada mientras estas cuestiones sigan abiertas.
   No se ha estimado todavía riesgo por vehículo-km ni se declara validado un modelo final.
7. Después, retomar el protocolo temporal, comparación GB/RF e interpretación. El EDA
   inspecciona también 2024, por lo que ese año no se debe presentar como una prueba intacta.

#### Registro de avances y cambios

| Fase | Avance | Estado al cerrar el EDA |
|---|---|---|
| Revisión inicial | Cruce de propuesta, presentación, rúbrica y retroalimentación; plan de Entrega 3 | Documentado |
| Correcciones de código | Captura con empates/presupuesto, convergencia, limpieza común, referencia desde pasado, UTC/DST y calendario | Implementadas y comprobadas |
| Comprobación técnica anterior | Corridas M0/M1/M2/M3, train/prueba, bootstrap de lluvia, turnos y recalibración con año previo | Diagnóstico previo; no selección final |
| Descarga y preparación | Seis capas PNCV, dos anexos DGC y ERA5; procedencia y versiones preservadas | Completadas |
| EDA actual | Calidad, duplicaciones, años, antigüedad, cobertura, unidades, cambios de composición y clima | Ejecutado; limitaciones abiertas descritas arriba |
| Exposición vehicular | Correspondencia por tramo, representatividad y disponibilidad histórica | Pendiente de resolver |
| Comparación y elección de modelos | GB/RF y evaluación final según el plan | En espera del análisis de datos |
| Comunicación | Notebook y presentación | Para el final, por indicación del equipo |

El EDA no modificó el notebook, la presentación, las fuentes descargadas ni los artefactos
de ajuste. Los resultados anteriores se conservan sin convertirlos en evidencia nueva.
{MARCAS[1]}
'''


def actualizar_readme(archivo, bloque):
    contenido = archivo.read_text()
    inicio, fin = MARCAS
    if inicio in contenido and fin in contenido:
        a, resto = contenido.split(inicio, 1)
        _, b = resto.split(fin, 1)
        contenido = a + bloque.rstrip() + b
    elif inicio in contenido or fin in contenido:
        raise ValueError("Marcadores incompletos en README; no se sobrescribe")
    else:
        titulo = "## Desarrollo de la Entrega 3\n"
        if titulo not in contenido:
            raise ValueError("No se encuentra el punto de inserción de EDA en README")
        contenido = contenido.replace(titulo, titulo + "\n" + bloque + "\n", 1)
    archivo.write_text(contenido)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=Path("resultados/eda"))
    p.add_argument("--actualizar-readme", action="store_true")
    args = p.parse_args()
    salida = args.salida
    salida.mkdir(parents=True, exist_ok=True)
    eventos, auditoria = cargar_eventos()
    raw = pd.read_csv("ruta5_2020_2024.csv.gz").query("Ruta == 'RUTA 5 SUR'")
    ref = referencia_entrenamiento(eventos)
    anual, tramo, se = analizar_eventos(eventos, raw, salida)
    ramas = normalizar_ramas("data/fuentes/mop")
    unicas, capas, sm = analizar_mop(ramas, Path("data/fuentes/mop"), salida)
    candidatos = proyectar_estaciones(ramas, ref)
    cov = cobertura_espacial(candidatos, ref, eventos)
    guardar(cov, salida, "mop_cobertura_antiguedad")
    cerca = candidatos.loc[candidatos.distancia_eje_km.le(2)].drop_duplicates(["estacion", "anio_medicion"])
    guardar(cerca, salida, "mop_estaciones_cercanas_por_anio")
    archivos_dgc = [Path(f"data/fuentes/dgc/anexo_{version}.xls") for version in FUENTES]
    versionados = pd.concat([extraer(a, v, FUENTES[v]) for a, v in zip(archivos_dgc, FUENTES)], ignore_index=True)
    versionados = versionados.loc[versionados.ruta5_sur].copy()
    dgc, revision = comparar_versiones(versionados)
    cambios = dgc.loc[dgc.cambio_puntos].copy()
    guardar(dgc, salida, "dgc_serie_descriptiva_sin_duplicar")
    guardar(revision, salida, "dgc_comparacion_versiones")
    guardar(cambios, salida, "dgc_cambios_puntos_cobro")
    dgc["variacion_interanual_pasadas_pct"] = dgc.groupby("contrato").transacciones_trimestre.pct_change(4) * 100
    dgc["variacion_interanual_proxy_pct"] = dgc.groupby("contrato").proxy_pasadas_por_punto_dia.pct_change(4) * 100
    guardar(dgc, salida, "dgc_variaciones_interanuales")
    anual_dgc = dgc.groupby(["contrato", "anio"]).agg(transacciones_anuales=("transacciones_trimestre", "sum"),
                       dias=("dias", "sum"), puntos_min=("puntos_cobro_implicitos", "min"),
                       puntos_max=("puntos_cobro_implicitos", "max"), trimestres=("trimestre", "nunique")).reset_index()
    proxy_anual = dgc.assign(pasadas_promedio_punto_trimestre=3 * dgc.pasadas_promedio_por_punto_mes).groupby(
        ["contrato", "anio"]).pasadas_promedio_punto_trimestre.sum().rename("pasadas_promedio_punto_anio").reset_index()
    anual_dgc = anual_dgc.merge(proxy_anual, on=["contrato", "anio"], validate="one_to_one")
    anual_dgc["proxy_pasadas_punto_dia_ponderado"] = anual_dgc.pasadas_promedio_punto_anio / anual_dgc.dias
    guardar(anual_dgc, salida, "dgc_anuales_por_contrato")
    esperado = pd.MultiIndex.from_product([sorted(dgc.contrato.unique()), range(2020, 2025), range(1, 5)])
    observados = pd.MultiIndex.from_frame(dgc[["contrato", "anio", "trimestre"]])
    sd = {"filas_versionadas": len(versionados), "periodos_unicos": len(dgc), "periodos_solapados": len(revision),
          "periodos_faltantes": len(esperado.difference(observados)),
          "revisiones_transacciones": int(revision.cambio_transacciones_trimestre.sum()),
          "revisiones_promedio": int(revision.cambio_pasadas_promedio_por_punto_mes.sum()),
          "puntos_no_enteros": int((~dgc.puntos_cerca_entero).sum()),
          "contratos_con_cambio_puntos": cambios.contrato.nunique()}
    clima, hist, sc = analizar_clima(eventos, ref, salida, "clima_ruta5.npz")
    calendario = analizar_calendario(eventos, Path("feriados.json"), salida)
    resumen = {"siniestros": se, "mop": sm, "dgc": sd, "clima": sc, "calendario": calendario}
    figuras(eventos, anual, tramo, unicas, capas, candidatos, ref, cov, dgc, clima, hist, salida)
    entradas = [Path("ruta5_2020_2024.csv.gz"), Path("clima_ruta5.npz"), Path("feriados.json"), *archivos_dgc,
                *sorted(Path("data/fuentes/mop").glob("capa_*.json"))]
    manifiesto = {"fecha_revision": "2026-11-12", "tipo": "EDA descriptivo; sin ajuste de modelos",
                  "auditoria_eventos": auditoria, "resumen": resumen,
                  "fuentes": [{"archivo": str(a), "sha256": hashlib.sha256(a.read_bytes()).hexdigest()} for a in entradas],
                  "versiones": {n: importlib.metadata.version(n) for n in ["numpy", "pandas", "scipy", "matplotlib", "xlrd"]},
                  "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (salida / "auditoria.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, allow_nan=False))
    if args.actualizar_readme:
        if salida != Path("resultados/eda"):
            raise ValueError("Para actualizar enlaces de README usar la salida predeterminada")
        actualizar_readme(Path("README.md"), bloque_readme(resumen, capas, cov, revision, cambios, anual_dgc))
    print(json.dumps(resumen, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
