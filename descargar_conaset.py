#!/usr/bin/env python3
"""
Descarga datos de siniestros de tránsito desde el ArcGIS Hub público de CONASET.
No requiere API key ni autenticación.

Uso:
    python3 descargar_conaset.py                      # Ruta 5 completa 2020-2024
    python3 descargar_conaset.py --where "AÑO=2024"   # filtro ArcGIS SQL libre
    python3 descargar_conaset.py --servicio Rural_2024 --where "1=1"
"""
import argparse, json, urllib.parse, urllib.request

HOST = "https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services"
PAGE = 2000


def descargar(servicio, where, capa=0):
    url = f"{HOST}/{servicio}/FeatureServer/{capa}/query"
    filas, offset = [], 0
    while True:
        params = urllib.parse.urlencode({
            "where": where, "outFields": "*", "returnGeometry": "false",
            "resultOffset": offset, "resultRecordCount": PAGE,
            "orderByFields": "FID", "f": "json",
        })
        with urllib.request.urlopen(f"{url}?{params}", timeout=120) as r:
            data = json.load(r)
        if "error" in data:
            raise SystemExit(data["error"])
        lote = data.get("features", [])
        if not lote:
            break
        filas += [f["attributes"] for f in lote]
        offset += len(lote)
        print(f"  {offset} registros...", flush=True)
        if len(lote) < PAGE:
            break
    return filas


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--servicio", default="Base_SINIESTROS_2020_2025")
    p.add_argument("--where", default="Ruta LIKE 'RUTA 5%'")
    p.add_argument("--salida", default="siniestros.json")
    a = p.parse_args()
    filas = descargar(a.servicio, a.where)
    json.dump(filas, open(a.salida, "w"), ensure_ascii=False)
    print(f"OK: {len(filas)} registros -> {a.salida}")
