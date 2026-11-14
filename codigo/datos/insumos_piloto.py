"""Captura meteorológica real y calendario acotado antes de emitir el piloto."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

FORECAST = "https://api.open-meteo.com/v1/forecast"
FERIADOS = "https://date.nager.at/api/v3/PublicHolidays/{anio}/CL"


def sha256(archivo):
    return hashlib.sha256(Path(archivo).read_bytes()).hexdigest()


def utc(valor):
    t = pd.Timestamp(valor)
    if t.tzinfo is None:
        raise ValueError("El instante debe incluir zona/offset; no se infiere UTC")
    return t.tz_convert("UTC")


def ventana(emision, horas=12):
    if horas != 12:
        raise ValueError("Este protocolo fija doce horas reales")
    inicio = utc(emision).floor("h") + pd.Timedelta(hours=1)
    return pd.date_range(inicio, periods=horas, freq="h")


def pedir(url, params, archivo):
    consulta = urllib.parse.urlencode(params)
    solicitud = url + ("?" + consulta if consulta else "")
    comienzo = datetime.now(timezone.utc).isoformat()
    with urllib.request.urlopen(solicitud, timeout=60) as r:
        crudo = r.read()
        fecha_http = r.headers.get("Date")
    fin = datetime.now(timezone.utc).isoformat()
    d = json.loads(crudo)
    if isinstance(d, dict) and d.get("error"):
        raise ValueError(f"Error del proveedor: {d.get('reason', d['error'])}")
    archivo.write_bytes(gzip.compress(crudo, mtime=0))
    return {"url": url, "parametros": params, "archivo": archivo.name,
            "sha256_respuesta": hashlib.sha256(crudo).hexdigest(),
            "captura_inicio_utc": comienzo, "captura_fin_utc": fin, "fecha_http": fecha_http}


def leer(carpeta, registro):
    nombre = registro["archivo"]
    if Path(nombre).name != nombre:
        raise ValueError("Nombre de archivo de captura inválido")
    crudo = gzip.decompress((carpeta / nombre).read_bytes())
    if hashlib.sha256(crudo).hexdigest() != registro["sha256_respuesta"]:
        raise ValueError("La captura original fue alterada")
    return json.loads(crudo)


def capturar(carpeta, celdas, config):
    carpeta.mkdir(parents=True, exist_ok=False)
    ahora = pd.Timestamp.now(tz="UTC")
    comienzo, fin = ahora.floor("h"), ahora.floor("h") + pd.Timedelta(hours=36)
    lotes = [celdas[i:i + 10] for i in range(0, len(celdas), 10)]

    def lote(item):
        n, c = item
        params = {"latitude": ",".join(str(p[0]) for p in c),
                  "longitude": ",".join(str(p[1]) for p in c),
                  "hourly": "precipitation", "timezone": "GMT", "models": config["meteorologia"],
                  "start_hour": comienzo.strftime("%Y-%m-%dT%H:%M"),
                  "end_hour": fin.strftime("%Y-%m-%dT%H:%M")}
        r = pedir(FORECAST, params, carpeta / f"pronostico_{n:02d}.json.gz")
        r["celdas_solicitadas"] = c
        return r

    with ThreadPoolExecutor(max_workers=3) as pool:
        pronosticos = list(pool.map(lote, enumerate(lotes)))
    # Incluir años vecinos cubre un horizonte próximo al cambio de año sin asumir calendario.
    local = ahora.tz_convert(config["zona"])
    anios = sorted({local.year, (local + pd.Timedelta(days=2)).year})
    feriados = []
    for anio in anios:
        r = pedir(FERIADOS.format(anio=anio), {}, carpeta / f"feriados_{anio}.json.gz")
        r["anio"] = anio
        feriados.append(r)
    return {"pronosticos": pronosticos, "feriados": feriados}


def verificar_corte(registros, emision, max_edad_minutos):
    t = utc(emision)
    for r in registros:
        ini, fin = utc(r["captura_inicio_utc"]), utc(r["captura_fin_utc"])
        if ini > fin or fin > t or t - ini > pd.Timedelta(minutes=max_edad_minutos):
            raise ValueError("Captura posterior a emisión, desordenada o demasiado antigua")


def alinear_pronostico(carpeta, registros, celdas, objetivo):
    """Conserva la etiqueta del proveedor: precipitación acumulada de la hora anterior."""
    objetivo = pd.DatetimeIndex(objetivo)
    if objetivo.tz is None or objetivo.has_duplicates or not objetivo.is_monotonic_increasing:
        raise ValueError("Horizonte UTC inválido")
    filas, obtenidas = [], []
    for r in registros:
        d = leer(carpeta, r)
        d = d if isinstance(d, list) else [d]
        solicitadas = r["celdas_solicitadas"]
        if len(d) != len(solicitadas):
            raise ValueError("Faltan localidades en el pronóstico")
        for respuesta, celda in zip(d, solicitadas):
            if respuesta.get("error") or respuesta.get("utc_offset_seconds") != 0:
                raise ValueError("Pronóstico con error o zona distinta de UTC")
            if respuesta.get("hourly_units", {}).get("precipitation") != "mm":
                raise ValueError("Unidad de precipitación inesperada")
            if max(abs(respuesta["latitude"] - celda[0]), abs(respuesta["longitude"] - celda[1])) > .26:
                raise ValueError("La celda devuelta no corresponde a la solicitada")
            h = respuesta["hourly"]
            t = pd.to_datetime(h["time"], utc=True)
            p = np.asarray(h["precipitation"], dtype=float)
            if len(t) != len(p) or t.has_duplicates or not t.is_monotonic_increasing:
                raise ValueError("Serie meteorológica duplicada, desordenada o inconsistente")
            if len(t) > 1 and not (np.diff(t.asi8) == 3_600_000_000_000).all():
                raise ValueError("Faltan horas en el pronóstico")
            ix = t.get_indexer(objetivo)
            if (ix < 0).any():
                raise ValueError("El pronóstico no cubre las doce horas")
            seleccion = p[ix]
            if not np.isfinite(seleccion).all() or (seleccion < 0).any():
                raise ValueError("Precipitación faltante o negativa; no se imputa seco")
            filas.append(seleccion)
            obtenidas.append(tuple(celda))
    if obtenidas != [tuple(c) for c in celdas]:
        raise ValueError("El orden de las celdas no coincide con la referencia")
    return np.asarray(filas)


def calendario(carpeta, registros, csv, tiempos, config):
    local = tiempos.tz_convert(config["zona"])
    fechas = sorted(set(local.date))
    tabla = pd.read_csv(csv, keep_default_na=False)
    if tabla.fecha.duplicated().any() or not tabla.dia.isin(["no", "inicio", "intermedio", "final"]).all():
        raise ValueError("Calendario duplicado o con posiciones desconocidas")
    ix = tabla.set_index("fecha")
    if any(str(f) not in ix.index for f in fechas):
        raise ValueError("Fecha fuera de la cobertura revisada del calendario piloto")
    if not config["periodos_festivos_validados"] and any(ix.loc[str(f), "dia"] != "no" for f in fechas):
        raise ValueError("Las posiciones de períodos festivos no están validadas para el piloto")
    feriados = []
    for r in registros:
        d = leer(carpeta, r)
        if not isinstance(d, list) or not d:
            raise ValueError("Respuesta de feriados vacía o inválida")
        for fila in d:
            if fila.get("countryCode") != "CL":
                raise ValueError("Calendario de otro país")
            fecha = pd.Timestamp(fila["date"]).date()
            if fecha.year != r["anio"]:
                raise ValueError("La respuesta de feriados no corresponde al año consultado")
            feriados.append(fecha)
    if not config["periodos_festivos_validados"]:
        margen = config["margen_dias_feriado"]
        if any(abs((f - festivo).days) <= margen for f in fechas for festivo in feriados):
            raise ValueError("Horizonte cercano a un feriado: falta validar el período CONASET equivalente")
    return [ix.loc[str(f), "dia"] for f in local.date]
