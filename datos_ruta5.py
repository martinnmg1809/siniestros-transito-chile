"""Filtros únicos y referencias espaciales construidas solo con entrenamiento."""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

ARCHIVO = Path(__file__).resolve().parent / "ruta5_2020_2024.csv.gz"
INICIO, FIN = "2020-01-01", "2024-12-31"
TRAMO_KM = 5


def cargar_eventos(archivo=ARCHIVO, tramo_km=TRAMO_KM):
    d = pd.read_csv(archivo)
    d = d.loc[d["Ruta"].eq("RUTA 5 SUR")].copy()
    inicial = len(d)
    d["km"] = pd.to_numeric(d["Ubicación"], errors="coerce")
    invalido = ~d["km"].between(0, 2200, inclusive="neither")
    d = d.loc[~invalido].copy()
    d["fecha"] = pd.to_datetime(d["FECHA"], errors="raise")
    d["hora"] = pd.to_numeric(d["Hora_aprox"], errors="raise")
    if (not d["hora"].between(0, 23).all() or (d["hora"] % 1 != 0).any()
            or not d["fecha"].between(INICIO, FIN).all()
            or not d["Latitud"].between(-56, -17).all()
            or not d["longitud"].between(-76, -66).all()
            or d["ID"].duplicated().any()):
        raise ValueError("Fecha, hora, coordenadas o IDs inválidos; revisar fuente")
    d["hora"] = d["hora"].astype(int)
    d["anio"] = d["fecha"].dt.year
    if not d["anio"].eq(d["AÑO"]).all():
        raise ValueError("AÑO no coincide con FECHA")
    d["tramo"] = (d["km"] // tramo_km * tramo_km).astype(int)
    d["instante_civil"] = d["fecha"] + pd.to_timedelta(d["hora"], unit="h")
    return d, {"fuente": str(Path(archivo).resolve()),
               "sha256": hashlib.sha256(Path(archivo).read_bytes()).hexdigest(),
               "registros_ruta": inicial, "km_excluidos": int(invalido.sum()),
               "registros_validos": len(d), "tramo_km": tramo_km,
               "por_anio": {str(k): int(v) for k, v in d.groupby("anio").size().items()}}


def referencia_entrenamiento(d, anios=(2020, 2021), tramo_km=TRAMO_KM):
    """Universo continuo entre extremos del pasado; interpola huecos interiores.

    La geometría es aproximada (medianas de registros históricos), no un eje vial
    oficial. No extiende el dominio usando los eventos del año de prueba.
    """
    pasado = d.loc[d["anio"].isin(anios)]
    if pasado.empty:
        raise ValueError("Entrenamiento sin registros")
    g = pasado.groupby("tramo").agg(lat=("Latitud", "median"),
                                     lon=("longitud", "median"), n=("ID", "size"))
    tramos = np.arange(g.index.min(), g.index.max() + tramo_km, tramo_km)
    ref = pd.DataFrame({"tramo": tramos})
    for col in ("lat", "lon"):
        ref[col] = np.interp(tramos, g.index, g[col])
    ref["eventos_referencia"] = g["n"].reindex(tramos, fill_value=0).to_numpy()
    ref["geometria_interpolada"] = ref["eventos_referencia"].eq(0)
    ref["ultimo_anio_referencia"] = max(anios)
    return ref


def grilla_civil(d, tramos):
    """Conteos por etiqueta local fecha/hora, misma resolución que CONASET.

    Convención explícita de 24 etiquetas por fecha. La fuente no distingue las
    dos ocurrencias de una hora repetida por DST; no supone instantes UTC exactos.
    """
    tiempo = pd.date_range(INICIO, FIN + " 23:00", freq="h")
    dentro = d["tramo"].isin(tramos)
    ix = pd.Index(tramos).get_indexer(d.loc[dentro, "tramo"])
    it = tiempo.get_indexer(d.loc[dentro, "instante_civil"])
    if (it < 0).any():
        raise ValueError("Eventos fuera de la grilla")
    y = np.zeros((len(tramos), len(tiempo)), dtype=np.int16)
    np.add.at(y, (ix, it), 1)
    return tiempo, y, int((~dentro).sum())


def exposicion_civil(tiempo):
    """Horas reales representadas por cada etiqueta local (0, 1 o 2 por DST)."""
    tiempo = pd.DatetimeIndex(tiempo)
    comienzo = tiempo[0].tz_localize("America/Santiago", nonexistent="shift_forward", ambiguous=True)
    fin = (tiempo[-1] + pd.Timedelta(hours=1)).tz_localize(
        "America/Santiago", nonexistent="shift_forward", ambiguous=True)
    real = pd.date_range(comienzo, fin, freq="h", inclusive="left").tz_localize(None)
    return pd.Series(1, index=real).groupby(level=0).sum().reindex(tiempo, fill_value=0).to_numpy(float)
