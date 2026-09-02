#!/usr/bin/env python3
"""
Valida la reconstrucción del clima contra el dato real de Carabineros.

El informe propone reconstruir el clima de cada siniestro (2020-2025) desde
Open-Meteo, porque CONASET solo publica `Estado_Atm` para 2023. Este script
comprueba si esa reconstrucción es fiel: toma los siniestros de 2023 donde SÍ
existe el dato observado en terreno y lo contrasta con lo que dice el reanálisis
para esa misma zona y hora.

Detalle importante: ERA5 tiene resolución de ~25 km, así que las coordenadas se
redondean a una grilla de 0,25° antes de consultar. No se pierde información
(el modelo no la tiene) y el número de consultas cae en un orden de magnitud,
que es lo que mantiene el script dentro de la cuota gratuita de la API.

Uso:  python3 validar_clima.py [n_dias_muestra]
"""
import collections, datetime, json, os, random, sys, time, urllib.error, urllib.parse, urllib.request

CONASET = ("https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services"
           "/SIniestros_individuales_REGION_DEL_BIO_BIO_2023/FeatureServer/0/query")
OPENMETEO = "https://archive-api.open-meteo.com/v1/archive"
BASE_HORA = datetime.datetime(1899, 12, 30, tzinfo=datetime.timezone.utc)

GRILLA = 0.25     # grados; resolución nativa de ERA5
UMBRAL_MM = 0.1   # mm/h desde los que el reanálisis declara precipitación
CACHE = "cache_clima.json"
N_DIAS = int(sys.argv[1]) if len(sys.argv) > 1 else 30


def bajar_siniestros():
    filas, off = [], 0
    while True:
        p = urllib.parse.urlencode({
            "where": "Estado_Atm IS NOT NULL",
            "outFields": "Fecha,Hora,Latitude,Longitude,Estado_Atm",
            "returnGeometry": "false", "resultOffset": off,
            "resultRecordCount": 2000, "orderByFields": "FID", "f": "json"})
        d = json.load(urllib.request.urlopen(f"{CONASET}?{p}", timeout=120))
        lote = d.get("features", [])
        if not lote:
            break
        filas += [x["attributes"] for x in lote]
        off += len(lote)
        if len(lote) < 2000:
            break
    return filas


def fecha_hora(fila):
    """ArcGIS entrega Fecha como epoch ms y Hora como offset desde 1899-12-30."""
    f = datetime.datetime.fromtimestamp(fila["Fecha"] / 1000, datetime.timezone.utc)
    h = datetime.datetime.fromtimestamp(fila["Hora"] / 1000, datetime.timezone.utc)
    return f.date(), (h - BASE_HORA).seconds // 3600


def celda(lat, lon):
    return (round(lat / GRILLA) * GRILLA, round(lon / GRILLA) * GRILLA)


def pedir(url, intentos=6):
    """GET con reintento exponencial: la cuota gratuita responde 429 al saturarse."""
    for i in range(intentos):
        try:
            return json.load(urllib.request.urlopen(url, timeout=120))
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == intentos - 1:
                raise
            espera = 2 ** i * 5
            print(f"\n  429: esperando {espera}s...", end="", flush=True)
            time.sleep(espera)


def series_precipitacion(pares):
    """pares = [(celda, dia)]. Devuelve {(celda, dia): [24 valores]} con caché en disco."""
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    faltan = [p for p in pares if f"{p[0][0]},{p[0][1]},{p[1]}" not in cache]
    print(f"{len(pares)} pares (celda, día) únicos; {len(faltan)} por consultar")

    # Una sola llamada por día, con todas las celdas de ese día juntas
    por_dia = collections.defaultdict(list)
    for c, dia in faltan:
        por_dia[dia].append(c)

    for i, (dia, celdas) in enumerate(sorted(por_dia.items()), 1):
        p = urllib.parse.urlencode({
            "latitude": ",".join(f"{c[0]:.2f}" for c in celdas),
            "longitude": ",".join(f"{c[1]:.2f}" for c in celdas),
            "start_date": dia, "end_date": dia,
            "hourly": "precipitation", "timezone": "America/Santiago"})
        d = pedir(f"{OPENMETEO}?{p}")
        if isinstance(d, dict):
            d = [d]
        for c, resp in zip(celdas, d):
            cache[f"{c[0]},{c[1]},{dia}"] = resp["hourly"]["precipitation"]
        print(f"\r  día {i}/{len(por_dia)}", end="", flush=True)
        json.dump(cache, open(CACHE, "w"))
    print()
    return cache


if __name__ == "__main__":
    print("Descargando siniestros de Biobío 2023 con clima observado...")
    filas = bajar_siniestros()

    eventos = []
    for f in filas:
        if f["Latitude"] and f["Longitude"]:
            dia, hora = fecha_hora(f)
            eventos.append((celda(f["Latitude"], f["Longitude"]),
                            dia.isoformat(), hora, f["Estado_Atm"]))

    random.seed(42)
    dias = set(random.sample(sorted({e[1] for e in eventos}), N_DIAS))
    muestra = [e for e in eventos if e[1] in dias]
    print(f"{len(filas)} siniestros con clima observado; "
          f"muestra de {len(dias)} días -> {len(muestra)} siniestros")

    cache = series_precipitacion(sorted({(e[0], e[1]) for e in muestra}))

    matriz = collections.Counter()
    for c, dia, hora, obs in muestra:
        serie = cache[f"{c[0]},{c[1]},{dia}"]
        mm = serie[hora] if hora < len(serie) and serie[hora] is not None else 0.0
        matriz[(obs in ("LLUVIA", "LLOVIZNA"), mm >= UMBRAL_MM)] += 1

    vp, fn = matriz[(True, True)], matriz[(True, False)]
    fp, vn = matriz[(False, True)], matriz[(False, False)]
    n = vp + fn + fp + vn

    print(f"\nContraste sobre {n} siniestros\n")
    print(f"{'':<26}{'ERA5: lluvia':>16}{'ERA5: seco':>14}")
    print(f"{'Carabineros: lluvia':<26}{vp:>16}{fn:>14}")
    print(f"{'Carabineros: seco':<26}{fp:>16}{vn:>14}\n")

    exact = (vp + vn) / n
    po, pe = exact, (((vp+fn)*(vp+fp)) + ((fp+vn)*(fn+vn))) / n**2
    print(f"  Acuerdo global      {exact:6.1%}")
    print(f"  Sensibilidad        {vp/(vp+fn):6.1%}   (lluvias reales detectadas)")
    print(f"  Especificidad       {vn/(vn+fp):6.1%}   (secos vistos como secos)")
    print(f"  Precisión           {vp/(vp+fp):6.1%}   (aciertos entre lluvias predichas)")
    print(f"  Kappa de Cohen      {(po-pe)/(1-pe):6.3f}   (acuerdo corregido por azar)")
