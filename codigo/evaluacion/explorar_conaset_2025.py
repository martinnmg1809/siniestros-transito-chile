"""EDA nacional separado: comprueba instantánea, calidad y comparabilidad 2024/25.

No asigna puntos a carreteras, no modifica la base histórica y no entrena modelos.
FECHA se lee como etiqueta de calendario del servicio, sin desplazarla a Santiago.
La semántica/zona de Hora debe acreditarse antes de construir exposición UTC/DST.
"""
import argparse
import calendar
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import unicodedata

os.environ.setdefault("MPLCONFIGDIR", "/tmp/siniestros-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from descargar_revision_conaset import CAMPOS, validar_ids, validar_lote


def cargar_instantanea(carpeta):
    m = json.loads((carpeta / "manifiesto.json").read_text())
    if not m.get("verificacion_completa"):
        raise ValueError("La instantánea no completó la verificación")
    filas = []
    ids = {}
    metadatos = {}
    for archivo in m["archivos"]:
        crudo = gzip.decompress((carpeta / archivo["archivo"]).read_bytes())
        if hashlib.sha256(crudo).hexdigest() != archivo["sha256_respuesta"]:
            raise ValueError(f"Hash distinto: {archivo['archivo']}")
        datos = json.loads(crudo)
        nombre = archivo["archivo"]
        if nombre.startswith("eventos_"):
            esperados = [int(i) for i in archivo["parametros"]["objectIds"].split(",")]
            lote = validar_lote(datos, esperados)
            anio = int(archivo["parametros"]["where"].split("=")[1])
            if any(f["AÑO"] != anio for f in lote):
                raise ValueError("Un lote mezcla años fuera de su consulta")
            filas.extend(lote)
        elif nombre.startswith("ids_"):
            anio = nombre.split("_")[-1].split(".")[0]
            ids[nombre] = validar_ids(datos, m["anios"][anio])
        elif nombre.startswith("metadatos_"):
            metadatos[nombre] = datos
    if len(metadatos) != 2:
        raise ValueError("Falta verificar metadatos iniciales/finales")
    antes, despues = metadatos["metadatos_antes.json.gz"], metadatos["metadatos_despues.json.gz"]
    if antes.get("editingInfo") != despues.get("editingInfo") or antes["fields"] != despues["fields"]:
        raise ValueError("La instantánea mezcla revisiones de la fuente")
    df = pd.DataFrame(filas, columns=CAMPOS)
    if df.FID.duplicated().any() or set(df["AÑO"].unique()) != {2024, 2025}:
        raise ValueError("Años incorrectos o FID duplicados en la instantánea")
    for anio in (2024, 2025):
        inicial = ids[f"ids_{anio}.json.gz"]
        final = ids[f"ids_finales_{anio}.json.gz"]
        if inicial != final or set(df.loc[df["AÑO"].eq(anio), "FID"]) != set(inicial):
            raise ValueError("Instantánea incompleta o cambiante")
    return df, m


def texto(s):
    return s.astype("string").str.strip()


def normalizar(s):
    return texto(s).str.lower().map(lambda x: "".join(
        c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn")
        if pd.notna(x) else x)


def controles(df):
    fecha = pd.to_datetime(df.FECHA, unit="ms", utc=True, errors="coerce").dt.tz_localize(None)
    hora = texto(df.Hora)
    valida = hora.str.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d:[0-5]\d", na=False)
    h = pd.to_numeric(hora.str.split(":").str[0].where(valida), errors="coerce")
    lat, lon = pd.to_numeric(df.Latitud, errors="coerce"), pd.to_numeric(df.longitud, errors="coerce")
    coord = np.isfinite(lat) & np.isfinite(lon) & lat.between(-90, 90) & lon.between(-180, 180)
    coord &= lat.ne(0) & lon.ne(0)
    # Este recuadro no es una frontera oficial y excluye territorios insulares.
    continente = lat.between(-56, -17) & lon.between(-76, -66)
    dias = {n: i for i, n in enumerate(["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"])}
    meses = {n: i + 1 for i, n in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio",
                                          "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"])}
    dia_fuente, mes_fuente = normalizar(df.Dia_semana).map(dias), normalizar(df.Mes).map(meses)
    km = pd.to_numeric(df["Ubicación"], errors="coerce")
    ruta = texto(df.Ruta)
    lesiones = df[["TOTAL_LESI", "GRAVES", "MENOS_GRAV", "LEVES"]].apply(pd.to_numeric, errors="coerce")
    completos = lesiones.notna().all(axis=1)
    c = pd.DataFrame({"fecha_invalida": fecha.isna(),
                      "anio_no_coincide": fecha.notna() & fecha.dt.year.ne(df["AÑO"]),
                      "fecha_no_medianoche": fecha.notna() & fecha.ne(fecha.dt.normalize()),
                      "hora_invalida": ~valida,
                      "hora_aprox_no_coincide": valida & pd.to_numeric(df.Hora_aprox, errors="coerce").ne(h),
                      "dia_semana_no_interpretable": dia_fuente.isna(),
                      "dia_semana_no_coincide": dia_fuente.notna() & fecha.notna() & dia_fuente.ne(fecha.dt.dayofweek),
                      "mes_no_interpretable": mes_fuente.isna(),
                      "mes_no_coincide": mes_fuente.notna() & fecha.notna() & mes_fuente.ne(fecha.dt.month),
                      "coordenada_invalida_o_cero": ~coord,
                      "fuera_recuadro_continental": coord & ~continente,
                      "ruta_ausente": ruta.isna() | ruta.eq(""),
                      "km_ausente_cero_o_negativo": km.isna() | ~np.isfinite(km) | km.le(0),
                      "lesiones_incompletas": ~completos,
                      "lesiones_no_suman": completos & lesiones.TOTAL_LESI.ne(lesiones[["GRAVES", "MENOS_GRAV", "LEVES"]].sum(axis=1)),
                      "consecuencias_negativas": df[["FALLECIDOS", "TOTAL_LESI", "GRAVES", "MENOS_GRAV", "LEVES"]].lt(0).any(axis=1),
                      "id_duplicado_en_anio": df.duplicated(["AÑO", "ID"], keep=False),
                      "fid_duplicado": df.FID.duplicated(keep=False)})
    return c.fillna(False), fecha, h, coord


def resumir(df):
    c, fecha, hora, coord = controles(df)
    calidad, campos, resumen, repetidos = [], [], [], []
    for anio, grupo in df.groupby("AÑO"):
        ix = grupo.index
        for control in c:
            n = int(c.loc[ix, control].sum())
            calidad.append({"anio": anio, "control": control, "registros": n, "total": len(ix), "porcentaje": 100 * n / len(ix)})
        for campo in CAMPOS:
            s = grupo[campo]
            campos.append({"anio": anio, "campo": campo, "nulos": int(s.isna().sum()),
                           "blancos": int((s.notna() & texto(s).eq("")).sum()),
                           "ceros": int(s.eq(0).sum()), "distintos_no_nulos": s.nunique()})
        pares = grupo.loc[coord.loc[ix], ["Latitud", "longitud"]].value_counts()
        # Una coordenada repetida o un registro parecido no prueba duplicación.
        repetidos.append({"anio": anio, "coordenadas_distintas": len(pares),
                          "filas_en_coordenadas_repetidas": int(pares.loc[pares.gt(1)].sum()),
                          "maximo_eventos_misma_coordenada": int(pares.max()),
                          "filas_clave_fecha_hora_coord_repetida": int(grupo.duplicated(
                              ["FECHA", "Hora", "Latitud", "longitud"], keep=False).sum()),
                          "filas_iguales_sin_identificadores": int(grupo.duplicated(
                              [c for c in CAMPOS if c not in ("FID", "ID")], keep=False).sum())})
        resumen.append({"anio": anio, "registros": len(grupo),
                        "primera_fecha": str(fecha.loc[ix].min().date()), "ultima_fecha": str(fecha.loc[ix].max().date()),
                        "dias_con_eventos": fecha.loc[ix].dt.normalize().nunique(),
                        "dias_calendario": 366 if calendar.isleap(anio) else 365,
                        "ruta5sur_etiquetada": int(texto(grupo.Ruta).eq("RUTA 5 SUR").sum()),
                        "fallecidos_en_capa": int(grupo.FALLECIDOS.sum()),
                        "lesionados_en_capa": int(grupo.TOTAL_LESI.sum())})
    minuto = pd.to_numeric(texto(df.Hora).str.split(":").str[1], errors="coerce").where(~c.hora_invalida)
    temporal = pd.DataFrame({"anio": df["AÑO"], "mes": fecha.dt.month, "hora": hora, "minuto": minuto,
                             "dia_semana": fecha.dt.dayofweek})
    mensuales = temporal.groupby(["anio", "mes"]).size().rename("registros").reset_index()
    mensuales["dias_mes"] = [calendar.monthrange(int(a), int(m))[1] for a, m in zip(mensuales.anio, mensuales.mes)]
    mensuales["registros_por_dia"] = mensuales.registros / mensuales.dias_mes
    tablas = {"resumen": pd.DataFrame(resumen), "calidad": pd.DataFrame(calidad),
              "campos": pd.DataFrame(campos), "repeticiones": pd.DataFrame(repetidos), "mensuales": mensuales}
    for columna in ("hora", "minuto", "dia_semana"):
        tabla = temporal.groupby(["anio", columna]).size().rename("registros").reset_index()
        tabla["porcentaje_del_anio"] = 100 * tabla.registros / tabla.anio.map(df["AÑO"].value_counts())
        tablas[columna] = tabla
    for campo in ("REGION", "ZONA", "TIPO_SINIE", "Ruta"):
        etiquetas = texto(df[campo]).fillna("[NULO]").replace("", "[BLANCO]")
        tabla = df.groupby([df["AÑO"].rename("anio"), etiquetas.rename("categoria")]).size().rename("registros").reset_index()
        tabla["porcentaje_del_anio"] = 100 * tabla.registros / tabla.anio.map(df["AÑO"].value_counts())
        tablas[campo.lower()] = tabla
    fuera = df.loc[c.fuera_recuadro_continental]
    tablas["fuera_recuadro"] = fuera.groupby(["AÑO", "REGION", "COMUNA"]).size().rename("registros").reset_index()
    return tablas


def comparar_historico(df, archivo):
    anterior = pd.read_csv(archivo)
    anterior = anterior.loc[anterior["AÑO"].eq(2024) & anterior.Ruta.eq("RUTA 5 SUR")].set_index("ID")
    actual = df.loc[df["AÑO"].eq(2024) & df.Ruta.eq("RUTA 5 SUR")].set_index("ID")
    if anterior.index.has_duplicates or actual.index.has_duplicates:
        raise ValueError("No se puede contrastar el histórico: ID no único en Ruta 5 Sur 2024")
    comun = anterior.index.intersection(actual.index)
    filas = [{"control": "id_solo_en_historico", "registros": len(anterior.index.difference(actual.index))},
             {"control": "id_solo_en_descarga", "registros": len(actual.index.difference(anterior.index))},
             {"control": "id_en_ambas_versiones", "registros": len(comun)}]
    for campo in CAMPOS:
        if campo in ("FID", "ID"):
            continue
        x, y = anterior.loc[comun, campo], actual.loc[comun, campo]
        if campo == "FECHA":
            iguales = pd.to_datetime(x).eq(pd.to_datetime(y, unit="ms"))
        elif pd.api.types.is_numeric_dtype(x):
            iguales = pd.Series(np.isclose(x, y, rtol=0, atol=1e-9, equal_nan=True), index=comun)
        else:
            iguales = x.eq(y) | (x.isna() & y.isna())
        filas.append({"control": "diferencias_" + campo, "registros": int((~iguales).sum())})
    return pd.DataFrame(filas)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fuente", type=Path, required=True)
    p.add_argument("--salida", type=Path, default=Path("resultados/eda_2025"))
    p.add_argument("--historico", type=Path, default=Path("data/siniestros/ruta5_2020_2024.csv.gz"))
    a = p.parse_args()
    df, m = cargar_instantanea(a.fuente)
    tablas = resumir(df)
    tablas["contraste_historico_2024"] = comparar_historico(df, a.historico)
    a.salida.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in tablas.items():
        tabla.to_csv(a.salida / (nombre + ".csv"), index=False)
    fig, ejes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for anio in (2024, 2025):
        t = tablas["mensuales"].query("anio == @anio")
        ejes[0, 0].plot(t.mes, t.registros_por_dia, marker="o", label=str(anio))
        t = tablas["hora"].query("anio == @anio")
        ejes[0, 1].plot(t.hora, t.porcentaje_del_anio, label=str(anio))
        t = tablas["dia_semana"].query("anio == @anio")
        ejes[1, 0].plot(t.dia_semana, t.porcentaje_del_anio, marker="o", label=str(anio))
    controles_grafico = ["ruta_ausente", "km_ausente_cero_o_negativo"]
    for n, anio in enumerate((2024, 2025)):
        t = tablas["calidad"].query("anio == @anio").set_index("control").loc[controles_grafico]
        ejes[1, 1].bar(np.arange(2) + n * .35, t.porcentaje, width=.35, label=str(anio))
    ejes[0, 0].set(xlabel="Mes", ylabel="Registros / día del mes", title="Frecuencia nacional en la capa")
    ejes[0, 1].set(xlabel="Hora declarada", ylabel="% de registros del año", title="Distribución por hora")
    ejes[1, 0].set(xticks=range(7), xticklabels=["L", "M", "X", "J", "V", "S", "D"],
                   ylabel="% de registros del año", title="Día de la semana calculado de FECHA")
    ejes[1, 1].set(xticks=np.arange(2) + .175, xticklabels=["Ruta ausente", "Km ausente/≤0"],
                   ylabel="% de registros", ylim=(0, 110), title="Identificación vial no utilizable")
    for eje in ejes.flat:
        eje.legend()
        eje.grid(alpha=.2)
    fig.suptitle("CONASET: diagnóstico nacional 2024–2025\nNo equivale a evolución de Ruta 5 Sur ni a riesgo por vehículo")
    fig.savefig(a.salida / "diagnostico.png", dpi=160)
    plt.close(fig)
    ids24 = set(df.loc[df["AÑO"].eq(2024), "ID"].dropna())
    ids25 = set(df.loc[df["AÑO"].eq(2025), "ID"].dropna())
    auditoria = {"fuente": m["url"], "consulta_utc": m["consulta_utc"], "anios": m["anios"],
                 "campos": m["campos"], "editingInfo": m["editingInfo"],
                 "dateFieldsTimeReference": m["dateFieldsTimeReference"],
                 "verificacion_completa": True,
                 "manifiesto_sha256": hashlib.sha256((a.fuente / "manifiesto.json").read_bytes()).hexdigest(),
                 "id_compartidos_2024_2025": len(ids24 & ids25),
                 "filas_crudas_publicadas": False, "integrado_al_modelo": False,
                 "historico_sha256": hashlib.sha256(a.historico.read_bytes()).hexdigest(),
                 "versiones": {"python": platform.python_version(), "pandas": pd.__version__,
                               "numpy": np.__version__, "matplotlib": matplotlib.__version__},
                 "codigo_sha256": {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in
                                    (Path("codigo/datos/descargar_revision_conaset.py"),
                                     Path("codigo/evaluacion/explorar_conaset_2025.py"))},
                 "archivos": [{k: f[k] for k in ("archivo", "sha256_respuesta", "registros")} for f in m["archivos"]]}
    (a.salida / "auditoria.json").write_text(json.dumps(auditoria, ensure_ascii=False, indent=2) + "\n")
    print(tablas["resumen"].to_string(index=False))
    print(f"EDA aislado -> {a.salida}; no se integraron datos ni se entrenó.")


if __name__ == "__main__":
    main()
