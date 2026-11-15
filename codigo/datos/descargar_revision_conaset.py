"""Instantánea nacional 2024–2025 para EDA aislado; no alimenta el entrenamiento.

Consulta por identificadores, verifica todos los lotes y conserva respuestas crudas.
No desactiva TLS ni interpreta una página incompleta como descarga terminada.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

URL = ("https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services/"
       "Base_SINIESTROS_2020_2025/FeatureServer/0")
CAMPOS = ["FID", "ID", "AÑO", "FECHA", "Dia_semana", "Mes", "Hora", "Hora_aprox",
          "REGION", "COMUNA", "TIPO_SINIE", "ZONA", "Ruta", "Ubicación",
          "FALLECIDOS", "TOTAL_LESI", "GRAVES", "MENOS_GRAV", "LEVES", "Latitud", "longitud"]


def consultar(url, parametros=None):
    consulta = urllib.parse.urlencode({"f": "json", **(parametros or {})})
    # Algunos servidores intermedios rechazan URL largas; /query admite POST.
    peticion = (urllib.request.Request(url, data=consulta.encode("utf-8"))
                if len(consulta) > 1800 else f"{url}?{consulta}")
    for intento in range(3):
        try:
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                crudo = respuesta.read()
            datos = json.loads(crudo)
            if "error" in datos:
                raise ValueError(f"Error ArcGIS: {datos['error']}")
            return datos, crudo
        except (TimeoutError, urllib.error.URLError):
            if intento == 2:
                raise
            time.sleep(1 + intento)


def validar_lote(datos, esperados):
    if datos.get("exceededTransferLimit"):
        raise ValueError("Lote truncado por ArcGIS")
    filas = [f["attributes"] for f in datos["features"]]
    ids = [f["FID"] for f in filas]
    if len(ids) != len(set(ids)) or set(ids) != set(esperados):
        raise ValueError("El lote no coincide con los FID solicitados")
    if any(set(CAMPOS) - set(fila) for fila in filas):
        raise ValueError("Faltan campos solicitados en un registro")
    return filas


def validar_ids(datos, conteo):
    ids = datos.get("objectIds")
    if (datos.get("exceededTransferLimit") or ids is None or len(ids) != conteo
            or len(ids) != len(set(ids))):
        raise ValueError("La lista de identificadores no concuerda con el conteo")
    return sorted(ids)


def guardar_crudo(carpeta, nombre, crudo, parametros, registros):
    nombre = nombre + ".json.gz"
    (carpeta / nombre).write_bytes(gzip.compress(crudo, mtime=0))
    return {"archivo": nombre, "sha256_respuesta": hashlib.sha256(crudo).hexdigest(),
            "parametros": parametros, "registros": registros}


def descargar(carpeta):
    carpeta.mkdir(parents=True, exist_ok=False)
    antes, crudo = consultar(URL)
    if antes.get("objectIdField") != "FID":
        raise ValueError("Cambió el campo OID de la fuente")
    archivos = [guardar_crudo(carpeta, "metadatos_antes", crudo, {}, None)]
    anos = {}
    for anio in (2024, 2025):
        base = {"where": f"AÑO={anio}"}
        count_params = {**base, "returnCountOnly": "true"}
        conteo, crudo = consultar(URL + "/query", count_params)
        archivos.append(guardar_crudo(carpeta, f"conteo_{anio}", crudo, count_params, conteo["count"]))
        id_params = {**base, "returnIdsOnly": "true"}
        datos, crudo = consultar(URL + "/query", id_params)
        ids = validar_ids(datos, conteo["count"])
        archivos.append(guardar_crudo(carpeta, f"ids_{anio}", crudo, id_params, len(ids)))
        lotes = [ids[i:i + 500] for i in range(0, len(ids), 500)]

        def obtener(item):
            n, lote = item
            params = {**base, "objectIds": ",".join(map(str, lote)),
                      "outFields": ",".join(CAMPOS), "returnGeometry": "false",
                      "orderByFields": "FID"}
            datos, crudo = consultar(URL + "/query", params)
            filas = validar_lote(datos, lote)
            archivo = guardar_crudo(carpeta, f"eventos_{anio}_{n:03d}", crudo, params, len(filas))
            return archivo

        with ThreadPoolExecutor(max_workers=4) as pool:
            for n, archivo in enumerate(pool.map(obtener, enumerate(lotes)), 1):
                archivos.append(archivo)
                if n % 20 == 0 or n == len(lotes):
                    print(f"{anio}: {n}/{len(lotes)} lotes comprobados", flush=True)
        # Reconsultar identificadores detecta inserciones/borrados durante la lectura.
        datos, crudo = consultar(URL + "/query", id_params)
        if validar_ids(datos, len(ids)) != ids:
            raise ValueError("La lista de eventos cambió durante la descarga")
        archivos.append(guardar_crudo(carpeta, f"ids_finales_{anio}", crudo, id_params, len(ids)))
        anos[str(anio)] = len(ids)
    despues, crudo = consultar(URL)
    archivos.append(guardar_crudo(carpeta, "metadatos_despues", crudo, {}, None))
    if antes.get("editingInfo") != despues.get("editingInfo") or antes["fields"] != despues["fields"]:
        raise ValueError("La fuente cambió durante la descarga; instantánea no aceptada")
    manifiesto = {"url": URL, "consulta_utc": datetime.now(timezone.utc).isoformat(),
                  "anios": anos, "campos": CAMPOS, "editingInfo": antes.get("editingInfo"),
                  "dateFieldsTimeReference": antes.get("dateFieldsTimeReference"),
                  "verificacion_completa": True, "archivos": archivos}
    (carpeta / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n")
    return manifiesto


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=Path("data/fuentes/conaset") /
                   ("eda_2025_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    a = p.parse_args()
    m = descargar(a.salida)
    print(f"Instantánea comprobada: {m['anios']} -> {a.salida}")
