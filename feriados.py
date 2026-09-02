#!/usr/bin/env python3
"""
Extrae el calendario de feriados de Chile desde la capa `base_feriados` de CONASET.

Ventaja sobre reimplementar las reglas legales: la capa marca el fin de semana largo
completo, distinguiendo `Inicio` / `Intermedio` / `final`. Esa distinción importa —
el día de salida concentra el flujo hacia el sur, y no es el mismo día que el feriado.

Cubre 2019-2024, que es el período con campo `Ruta` poblado en la base de siniestros.
"""
import collections, json, urllib.parse, urllib.request

URL = ("https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services"
       "/base_feriados/FeatureServer/0/query")


def calendario():
    """{'YYYY-MM-DD': {'feriado': nombre, 'dia': 'inicio'|'intermedio'|'final'}}"""
    p = urllib.parse.urlencode({
        "where": "1=1", "outFields": "Fecha,Feriado,Dia_del_feriado",
        "returnGeometry": "false", "returnDistinctValues": "true",
        "resultRecordCount": 4000, "f": "json"})
    d = json.load(urllib.request.urlopen(f"{URL}?{p}", timeout=120))
    cal = {}
    for x in d["features"]:
        a = x["attributes"]
        if not a.get("Fecha"):
            continue
        dd, mm, yy = a["Fecha"].split("-")
        cal[f"{yy}-{mm}-{dd}"] = {
            "feriado": (a.get("Feriado") or "").strip(),
            "dia": (a.get("Dia_del_feriado") or "").strip().lower(),
        }
    return cal


if __name__ == "__main__":
    cal = calendario()
    json.dump(cal, open("feriados.json", "w"), ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{len(cal)} fechas, {min(cal)} -> {max(cal)}")
    print("por año:", dict(sorted(collections.Counter(f[:4] for f in cal).items())))
    print("por posición:", dict(collections.Counter(v["dia"] for v in cal.values())))
    print("feriados distintos:", len({v["feriado"] for v in cal.values()}))
