"""Descarga ERA5 en UTC y une por fecha/hora local, sin imputar lluvia como seco."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from datos_ruta5 import cargar_eventos, referencia_entrenamiento, INICIO, FIN
from fuentes import obtener_json

GRILLA = 0.25
URL = "https://archive-api.open-meteo.com/v1/archive"


def celdas_por_tramo():
    d, _ = cargar_eventos()
    ref = referencia_entrenamiento(d)
    return {int(r.tramo): (round(r.lat / GRILLA) * GRILLA,
                           round(r.lon / GRILLA) * GRILLA) for r in ref.itertuples()}


def alinear_utc(respuesta, inicio=INICIO, fin=FIN):
    """Repetición DST: conteo conjunto, precipitación media, exposición de 2 h.

    CONASET no distingue el offset UTC del evento. Promediar lluvia durante la
    hora repetida es una aproximación. Etiquetas inexistentes: e=0, lluvia=NaN.
    """
    h = respuesta["hourly"]
    t = pd.to_datetime(h["time"], utc=True)
    valores = np.asarray(h["precipitation"], dtype=float)
    if len(t) != len(valores) or not t.is_monotonic_increasing or t.has_duplicates:
        raise ValueError("Serie meteorológica desordenada, duplicada o de tamaño incorrecto")
    if len(t) > 1 and not (np.diff(t.asi8) == 3_600_000_000_000).all():
        raise ValueError("Faltan horas en la serie UTC")
    local = t.tz_convert("America/Santiago").tz_localize(None)
    objetivo = pd.date_range(inicio, fin + " 23:00", freq="h")
    dentro = (local >= objetivo[0]) & (local <= objetivo[-1])
    if not np.isfinite(valores[dentro]).all() or (valores[dentro] < 0).any():
        raise ValueError("Precipitación faltante o negativa; no se imputa como seco")
    comienzo = pd.Timestamp(inicio).tz_localize("America/Santiago", nonexistent="shift_forward", ambiguous=True)
    termino = (pd.Timestamp(fin) + pd.DateOffset(days=1)).tz_localize(
        "America/Santiago", nonexistent="shift_forward", ambiguous=True)
    esperado = pd.date_range(comienzo, termino,
                            freq="h", inclusive="left").tz_convert("UTC")
    if not t[dentro].equals(esperado):
        raise ValueError("La serie UTC no cubre exactamente el período local solicitado")
    s = pd.Series(valores[dentro], index=local[dentro])
    media = s.groupby(level=0).mean().reindex(objetivo)
    exposicion = s.groupby(level=0).size().reindex(objetivo, fill_value=0)
    return objetivo, media.to_numpy(np.float32), exposicion.to_numpy(np.int8)


def pedir(lat, lon):
    return obtener_json(URL, {"latitude": lat, "longitude": lon,
                         "start_date": INICIO,
                         "end_date": (datetime.date.fromisoformat(FIN) + datetime.timedelta(days=1)).isoformat(),
                         "hourly": "precipitation", "timezone": "GMT", "models": "era5"})


def cargar_cache(archivo="clima_ruta5.npz"):
    with np.load(archivo, allow_pickle=False) as z:
        if "version" not in z or int(z["version"]) != 2:
            raise ValueError("Caché antiguo sin alineación UTC; regenerar con clima.py")
        return {k: z[k].copy() for k in z.files}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=Path("clima_ruta5.npz"))
    p.add_argument("--cache-parcial", type=Path, default=Path("data/fuentes/era5"))
    args = p.parse_args()
    t2c = celdas_por_tramo()
    celdas = sorted(set(t2c.values()))
    args.cache_parcial.mkdir(parents=True, exist_ok=True)
    series, exposicion, objetivo = [], None, None
    for i, (lat, lon) in enumerate(celdas, 1):
        cache = args.cache_parcial / f"era5_utc_{lat:.2f}_{lon:.2f}_2020_2024.json"
        if cache.exists():
            respuesta = json.loads(cache.read_text())
        else:
            respuesta = pedir(lat, lon)
            cache.write_text(json.dumps(respuesta, ensure_ascii=False))
        objetivo, v, e = alinear_utc(respuesta)
        if exposicion is not None and not np.array_equal(e, exposicion):
            raise ValueError("Celdas con calendarios incompatibles")
        exposicion = e
        series.append(v)
        print(f"ERA5 UTC {i}/{len(celdas)}", flush=True)
    ref = referencia_entrenamiento(cargar_eventos()[0])
    metadatos = {"version": 2, "modelo": "era5", "zona": "America/Santiago",
                 "descarga_zona": "GMT", "referencia_hasta": 2021,
                 "fuente": URL, "inicio": INICIO, "fin": FIN,
                 "referencia_sha256": hashlib.sha256(ref.to_csv(index=False).encode()).hexdigest(),
                 "hora_repetida": "conteo conjunto y precipitación promedio; aproximación",
                 "hora_inexistente": "exposición cero; eventos incompatibles se auditan y excluyen"}
    tramos = sorted(t2c)
    np.savez_compressed(args.salida, version=np.array(2), precip=np.array(series),
                        celdas=np.array(celdas), tiempo=objetivo.to_numpy(dtype="datetime64[h]"),
                        exposicion_tiempo=exposicion, tramos=np.array(tramos),
                        idx_celda=np.array([celdas.index(t2c[t]) for t in tramos]),
                        metadatos=np.array(json.dumps(metadatos, ensure_ascii=False)))
    print(f"Guardado {args.salida}: {len(celdas)} celdas, {len(objetivo)} etiquetas horarias")


if __name__ == "__main__":
    main()
