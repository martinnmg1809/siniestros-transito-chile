"""Descarga auditable de fuentes públicas; no altera respuestas crudas."""
import datetime
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


def obtener_json(url, parametros=None, intentos=3):
    if parametros:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(parametros)
    for i in range(intentos):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                d = json.load(r)
            if isinstance(d, dict) and d.get("error"):
                raise ValueError(f"Error de la fuente {url}: {d['error']}")
            return d
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == intentos - 1:
                raise
            time.sleep(min(2 ** (i + 1), 30))


def descargar_capa(url, carpeta, nombre):
    """Descarga por OBJECTID: no presupone que el límite alcance para la capa."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    meta = obtener_json(url, {"f": "json"})
    ids = obtener_json(url + "/query", {"where": "1=1", "returnIdsOnly": "true", "f": "json"})
    lista = sorted(ids["objectIds"] or [])
    features = []
    # IIS puede rechazar URLs largas como 404; mantener lotes bajo ese límite.
    for i in range(0, len(lista), 100):
        d = obtener_json(url + "/query", {"objectIds": ",".join(map(str, lista[i:i + 100])),
                          "outFields": "*", "returnGeometry": "true", "outSR": 4326, "f": "json"})
        if d.get("exceededTransferLimit"):
            raise ValueError("Respuesta truncada; reducir tamaño de lote")
        features.extend(d["features"])
    oid = ids["objectIdFieldName"]
    if sorted(f["attributes"][oid] for f in features) != lista:
        raise ValueError("Descarga incompleta o duplicada")
    datos = {"features": features, "spatialReference": {"wkid": 4326}}
    contenido = json.dumps(datos, ensure_ascii=False).encode()
    (carpeta / f"{nombre}.json").write_bytes(contenido)
    (carpeta / f"{nombre}_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    manifiesto = {"url": url, "descargado_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "registros": len(features), "sha256": hashlib.sha256(contenido).hexdigest(),
                  "nota": "Fecha de descarga actual; no acredita publicación histórica"}
    (carpeta / f"{nombre}_descarga.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2))
    return datos
