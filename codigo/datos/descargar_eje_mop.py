"""Descarga acotada de Ruta 5 y vías del corredor, con originales e IDs comprobados."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from descargar_revision_conaset import consultar, guardar_crudo, validar_ids
from ubicacion_vial import es_ruta5_sur

CAMPOS = "OBJECTID,ROL,ROL_LABEL,NOMBRE_CAMINO,ORIENTACION,CALZADA,KM_I,KM_F,REGION"


def validar_geolote(d, ids):
    fs = d.get("features", [])
    obtenidos = [f["attributes"]["OBJECTID"] for f in fs]
    if d.get("exceededTransferLimit") or len(set(obtenidos)) != len(obtenidos) or set(obtenidos) != set(ids):
        raise ValueError("Lote geométrico incompleto, repetido o truncado")
    if d.get("spatialReference", {}).get("wkid") != 4326 or not d.get("hasM"):
        raise ValueError("La respuesta debe usar WGS84 con M y sin Z")
    if d.get("hasZ"):
        raise ValueError("Respuesta con Z inesperada; no confundir Z con M")
    return fs


def descargar(carpeta, protocolo_path):
    carpeta.mkdir(parents=True, exist_ok=False)
    protocolo = json.loads(protocolo_path.read_text())
    base = protocolo["fuente_mop"]
    archivos, grupos = [], {}

    def consulta(sufijo, params, nombre):
        d, crudo = consultar(base + sufijo, params)
        archivos.append(guardar_crudo(carpeta, nombre, crudo, params, len(d.get("features", []))))
        return d

    antes = consulta("", {}, "metadatos_antes")

    def grupo(nombre, filtros):
        conteo = consulta("/query", {**filtros, "returnCountOnly": "true"}, nombre + "_conteo")["count"]
        id_params = {**filtros, "returnIdsOnly": "true"}
        ids = validar_ids(consulta("/query", id_params, nombre + "_ids"), conteo)
        lotes = [ids[i:i + 15] for i in range(0, len(ids), 15)]

        def lote(item):
            i, ids_lote = item
            params = {"objectIds": ",".join(map(str, ids_lote)), "outFields": CAMPOS,
                      "returnGeometry": "true", "returnM": "true", "returnZ": "false", "outSR": 4326}
            d, crudo = consultar(base + "/query", params)
            fs = validar_geolote(d, ids_lote)
            ar = guardar_crudo(carpeta, f"{nombre}_geometria_{i:04d}", crudo, params, len(fs))
            return ar, fs

        salida = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            for i, (ar, fs) in enumerate(pool.map(lote, enumerate(lotes)), 1):
                archivos.append(ar)
                salida.extend(fs)
                if i % 20 == 0 or i == len(lotes):
                    print(f"{nombre}: {i}/{len(lotes)} lotes", flush=True)
        finales = validar_ids(consulta("/query", id_params, nombre + "_ids_finales"), conteo)
        if finales != ids:
            raise ValueError("Cambió la selección espacial durante la descarga")
        grupos[nombre] = {"conteo": conteo, "filtros": filtros}
        return salida

    rutas = grupo("ruta5", {"where": "ROL_LABEL='5'"})
    transformador = Transformer.from_crs(4326, protocolo["crs_calculo"], always_xy=True)
    lineas = []
    for f in rutas:
        if es_ruta5_sur(f["attributes"]):
            for path in (f.get("geometry") or {}).get("paths", []):
                if len(path) >= 2:
                    x, y = transformador.transform([v[0] for v in path], [v[1] for v in path])
                    lineas.append(LineString(zip(x, y)))
    if not lineas:
        raise ValueError("No se encontró el corredor sur")
    corredor = unary_union(lineas).buffer(protocolo["buffer_competidoras_m"]).simplify(100)
    poligonos = [corredor] if corredor.geom_type == "Polygon" else list(corredor.geoms)
    # Incluir el exterior completo es conservador: puede traer vías adicionales.
    rings = [list(orient(p, sign=-1).exterior.coords) for p in poligonos]
    geometria = {"rings": rings, "spatialReference": {"wkid": int(protocolo["crs_calculo"].split(":")[1])}}
    otras = grupo("competidoras", {"where": "ROL_LABEL <> '5' OR ROL_LABEL IS NULL",
                  "geometry": json.dumps(geometria), "geometryType": "esriGeometryPolygon",
                  "inSR": geometria["spatialReference"]["wkid"], "spatialRel": "esriSpatialRelIntersects"})
    despues = consulta("", {}, "metadatos_despues")
    if antes != despues:
        raise ValueError("Metadatos de la cartografía cambiaron durante la descarga")
    m = {"fuente": base, "consulta_utc": datetime.now(timezone.utc).isoformat(),
         "protocolo_sha256": hashlib.sha256(protocolo_path.read_bytes()).hexdigest(),
         "grupos": grupos, "archivos": archivos, "verificacion_completa": True,
         "limite": "El servicio no acredita fecha efectiva ni ausencia de ediciones de atributos durante la consulta."}
    (carpeta / "manifiesto.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
    print(f"Fuente comprobada: {len(rutas)} Ruta 5 y {len(otras)} competidoras -> {carpeta}")


def cargar_geometria(carpeta, protocolo_path):
    m = json.loads((carpeta / "manifiesto.json").read_text())
    if not m.get("verificacion_completa") or m["protocolo_sha256"] != hashlib.sha256(protocolo_path.read_bytes()).hexdigest():
        raise ValueError("Instantánea incompleta o protocolo modificado")
    fs, vistos = [], set()
    for a in m["archivos"]:
        crudo = gzip.decompress((carpeta / a["archivo"]).read_bytes())
        if hashlib.sha256(crudo).hexdigest() != a["sha256_respuesta"]:
            raise ValueError("Hash distinto en la cartografía")
        if "_geometria_" not in a["archivo"]:
            continue
        ids = list(map(int, a["parametros"]["objectIds"].split(",")))
        if vistos.intersection(ids):
            raise ValueError("OBJECTID repetido entre lotes")
        fs.extend(validar_geolote(json.loads(crudo), ids))
        vistos.update(ids)
    if len(fs) != sum(g["conteo"] for g in m["grupos"].values()):
        raise ValueError("Faltan entidades de la cartografía")
    return fs, m


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--protocolo", type=Path, default=Path("config/protocolo_asignacion_vial.json"))
    a = p.parse_args()
    descargar(a.salida, a.protocolo)
