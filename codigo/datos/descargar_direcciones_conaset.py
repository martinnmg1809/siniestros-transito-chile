"""Complemento de direcciones para recuperar atributos explícitos, no inferir vías.

Conserva originales 2023–2025 con comprobación de IDs; no altera las fuentes previas.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

from descargar_revision_conaset import URL, consultar, guardar_crudo, validar_ids

CAMPOS = ["FID", "ID", "AÑO", "FECHA", "Ruta", "Ubicación", "REGION", "COMUNA",
          "Latitud", "longitud", "Calle_Uno", "Calle_Dos", "Número", "Dirección", "UBICACION"]


def consultar_catalogo(carpeta):
    """Solo esquemas/rangos: no descarga los eventos de estas seis capas."""
    carpeta.mkdir(parents=True, exist_ok=False)
    base = URL.split("/Base_SINIESTROS_")[0]
    nombres = ["siniestros_2", "siniestros2020_2024", "puntos_siniestros",
               "tramos_con_siniestro", "redvialdisol", "Reporte_mensual_siniestros"]
    resumen = []
    for nombre in nombres:
        u = base + "/" + nombre + "/FeatureServer"
        servicio, crudo = consultar(u)
        (carpeta / (nombre + "_servicio.json")).write_bytes(crudo)
        capas = []
        for capa in servicio.get("layers", []) + servicio.get("tables", []):
            m, crudo = consultar(u + "/" + str(capa["id"]))
            stem = nombre + "_" + str(capa["id"])
            (carpeta / (stem + ".json")).write_bytes(crudo)
            campos = [f["name"] for f in m.get("fields", [])]
            anio = next((f for f in campos if f.upper() in ["AÑO", "ANO", "ANIO", "YEAR"]), None)
            rango = None
            if anio:
                estadisticas = [{"statisticType": t, "onStatisticField": anio,
                                  "outStatisticFieldName": t + "_anio"} for t in ["min", "max"]]
                d, crudo = consultar(u + "/" + str(capa["id"]) + "/query", {
                    "where": "1=1", "returnGeometry": "false", "outStatistics": json.dumps(estadisticas)})
                (carpeta / (stem + "_rango.json")).write_bytes(crudo)
                rango = [f["attributes"] for f in d.get("features", [])]
            capas.append({"capa": capa["id"], "campos": campos, "rango": rango})
        resumen.append({"servicio": nombre, "capas": capas})
    _, crudo = consultar(base + "/Reporte_mensual_siniestros/FeatureServer/0/query", {
        "where": "Año=2025", "outFields": "SECTOR", "returnGeometry": "false", "returnDistinctValues": "true"})
    (carpeta / "reporte_mensual_sector_2025.json").write_bytes(crudo)
    (carpeta / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n")
    print("Metadatos y rangos consultados:", carpeta)


def validar(d, ids, anio):
    fs = [f["attributes"] for f in d.get("features", [])]
    obtenidos = [f["FID"] for f in fs]
    if (d.get("exceededTransferLimit") or len(set(obtenidos)) != len(obtenidos) or
            set(obtenidos) != set(ids) or any(f["AÑO"] != anio for f in fs) or
            any(set(CAMPOS) - set(f) for f in fs)):
        raise ValueError("Complemento incompleto, truncado o de otro año")
    return fs


def descargar(carpeta):
    carpeta.mkdir(parents=True, exist_ok=False)
    archivos, conteos = [], {}
    antes, crudo = consultar(URL)
    archivos.append(guardar_crudo(carpeta, "metadatos_antes", crudo, {}, None))
    for anio in (2023, 2024, 2025):
        base = {"where": f"AÑO={anio}"}
        d, crudo = consultar(URL + "/query", {**base, "returnCountOnly": "true"})
        count = d["count"]
        archivos.append(guardar_crudo(carpeta, f"conteo_{anio}", crudo, {**base, "returnCountOnly": "true"}, count))
        params_ids = {**base, "returnIdsOnly": "true"}
        d, crudo = consultar(URL + "/query", params_ids)
        ids = validar_ids(d, count)
        archivos.append(guardar_crudo(carpeta, f"ids_{anio}", crudo, params_ids, count))
        lotes = [ids[i:i + 500] for i in range(0, count, 500)]

        def obtener(item):
            n, lote = item
            params = {**base, "objectIds": ",".join(map(str, lote)), "outFields": ",".join(CAMPOS),
                      "returnGeometry": "false", "orderByFields": "FID"}
            d, crudo = consultar(URL + "/query", params)
            fs = validar(d, lote, anio)
            return guardar_crudo(carpeta, f"direcciones_{anio}_{n:03d}", crudo, params, len(fs))

        with ThreadPoolExecutor(max_workers=4) as pool:
            for n, archivo in enumerate(pool.map(obtener, enumerate(lotes)), 1):
                archivos.append(archivo)
                if n % 40 == 0 or n == len(lotes):
                    print(f"{anio}: {n}/{len(lotes)} lotes comprobados", flush=True)
        d, crudo = consultar(URL + "/query", params_ids)
        if validar_ids(d, count) != ids:
            raise ValueError("La lista de eventos cambió durante la descarga")
        archivos.append(guardar_crudo(carpeta, f"ids_finales_{anio}", crudo, params_ids, count))
        conteos[str(anio)] = count
    despues, crudo = consultar(URL)
    archivos.append(guardar_crudo(carpeta, "metadatos_despues", crudo, {}, None))
    if antes.get("editingInfo") != despues.get("editingInfo") or antes["fields"] != despues["fields"]:
        raise ValueError("La fuente cambió durante la descarga")
    m = {"fuente": URL, "consulta_utc": datetime.now(timezone.utc).isoformat(), "anios": conteos,
         "campos": CAMPOS, "editingInfo": antes.get("editingInfo"),
         "verificacion_completa": True, "archivos": archivos}
    (carpeta / "manifiesto.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
    print("Complemento comprobado:", conteos)


def cargar(carpeta):
    m = json.loads((carpeta / "manifiesto.json").read_text())
    if not m.get("verificacion_completa"):
        raise ValueError("Complemento sin comprobar")
    filas, ids = [], {}
    for a in m["archivos"]:
        crudo = gzip.decompress((carpeta / a["archivo"]).read_bytes())
        if hashlib.sha256(crudo).hexdigest() != a["sha256_respuesta"]:
            raise ValueError("Original alterado")
        d = json.loads(crudo)
        if a["archivo"].startswith("direcciones_"):
            anio = int(a["parametros"]["where"].split("=")[1])
            filas.extend(validar(d, list(map(int, a["parametros"]["objectIds"].split(","))), anio))
        elif a["archivo"].startswith("ids_"):
            anio = a["archivo"].split("_")[-1].split(".")[0]
            ids[a["archivo"]] = validar_ids(d, m["anios"][anio])
    import pandas as pd
    df = pd.DataFrame(filas)
    if df.FID.duplicated().any():
        raise ValueError("FID duplicados entre lotes")
    for anio, conteo in m["anios"].items():
        f = df.loc[df["AÑO"].eq(int(anio))]
        if len(f) != conteo or set(f.FID) != set(ids[f"ids_{anio}.json.gz"]) or ids[f"ids_{anio}.json.gz"] != ids[f"ids_finales_{anio}.json.gz"]:
            raise ValueError("Complemento incompleto o mezclado")
    return df, m


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--solo-catalogo", action="store_true", help="Consultar solo las seis fuentes adicionales")
    a = p.parse_args()
    if a.solo_catalogo:
        consultar_catalogo(a.salida)
    else:
        descargar(a.salida)
