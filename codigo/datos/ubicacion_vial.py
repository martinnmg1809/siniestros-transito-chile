"""Geometría y medidas M para un ensayo aislado de correspondencia vial.

Nunca usa la ruta o el kilómetro del evento al proponer una asignación.
Las etiquetas históricas se reservan para comprobar el resultado.
"""
import unicodedata
import numpy as np
from pyproj import Transformer
import shapely
from shapely import STRtree


def normalizar(valor):
    return "".join(c for c in unicodedata.normalize("NFD", ("" if valor is None else str(valor)).upper())
                   if unicodedata.category(c) != "Mn").strip()


def es_ruta5_sur(a):
    return (str(a.get("ROL_LABEL", "")).strip() == "5" and
            (normalizar(a.get("ORIENTACION")) == "SUR" or
             normalizar(a.get("NOMBRE_CAMINO")).startswith("LONGITUDINAL SUR")))


def segmentos_entidad(feature, transformador):
    """Cada parte se trata por separado. M faltante no se inventa desde extremos."""
    a = feature["attributes"]
    partes = (feature.get("geometry") or {}).get("paths", [])
    salida = []
    for parte, vertices in enumerate(partes):
        if len(vertices) < 2:
            continue
        v = np.asarray([[p[0], p[1], p[2] if len(p) == 3 and p[2] is not None else np.nan]
                        for p in vertices], dtype=float)
        x, y = transformador.transform(v[:, 0], v[:, 1])
        xy = np.column_stack([x, y])
        for i in range(len(v) - 1):
            if not np.isfinite(xy[i:i + 2]).all() or np.linalg.norm(xy[i + 1] - xy[i]) < 1e-6:
                continue
            salida.append((xy[i], xy[i + 1], v[i, 2], v[i + 1, 2],
                           int(a["OBJECTID"]), parte, es_ruta5_sur(a)))
    return salida


def proyectar_segmentos(punto, inicios, finales, m0, m1):
    vector = finales - inicios
    t = np.clip(np.sum((punto - inicios) * vector, axis=1) / np.sum(vector ** 2, axis=1), 0, 1)
    distancia = np.linalg.norm(punto - (inicios + t[:, None] * vector), axis=1)
    return distancia, m0 + t * (m1 - m0)


class IndiceVial:
    def __init__(self, features, crs="EPSG:32719"):
        self.transformador = Transformer.from_crs(4326, crs, always_xy=True)
        filas = [r for f in features for r in segmentos_entidad(f, self.transformador)]
        if not filas:
            raise ValueError("Cartografía sin segmentos válidos")
        self.inicios = np.array([r[0] for r in filas])
        self.finales = np.array([r[1] for r in filas])
        self.m0, self.m1 = np.array([r[2] for r in filas]), np.array([r[3] for r in filas])
        longitud = np.linalg.norm(self.finales - self.inicios, axis=1)
        incremento = np.abs(self.m1 - self.m0)
        # Saltos o medidas constantes sobre arcos largos no producen km inferidos.
        self.medida_valida = (np.isfinite(self.m0) & np.isfinite(self.m1) &
                              ((longitud <= 20) | ((incremento >= .5 * longitud) &
                                                   (incremento <= 2 * longitud))))
        self.m0 = np.where(self.medida_valida, self.m0, np.nan)
        self.m1 = np.where(self.medida_valida, self.m1, np.nan)
        self.oid = np.array([r[4] for r in filas])
        self.sur = np.array([r[6] for r in filas], dtype=bool)
        lineas = shapely.linestrings(np.stack([self.inicios, self.finales], axis=1))
        self.ix_sur, self.ix_otras = np.flatnonzero(self.sur), np.flatnonzero(~self.sur)
        if not len(self.ix_sur) or not len(self.ix_otras):
            raise ValueError("Se necesitan Ruta 5 Sur y vías competidoras")
        self.sur_tree, self.otras_tree = STRtree(lineas[self.ix_sur]), STRtree(lineas[self.ix_otras])

    def candidatos(self, lon, lat, radio_m=200):
        """Vecinos métricos y M; conserva alternativas y descarta lazos ambiguos."""
        x, y = self.transformador.transform(np.asarray(lon).tolist(), np.asarray(lat).tolist())
        puntos = shapely.points(x, y)
        otros = self.otras_tree.query_nearest(puntos, all_matches=False, return_distance=True)
        dist_otras = np.full(len(puntos), np.inf)
        dist_otras[otros[0][0]] = otros[1]
        cercanos = self.sur_tree.query(puntos, predicate="dwithin", distance=radio_m)
        orden = np.argsort(cercanos[0], kind="stable")
        punto_ix, seg_ix = cercanos[0][orden], self.ix_sur[cercanos[1][orden]]
        resultado = []
        pos = np.searchsorted(punto_ix, np.arange(len(puntos) + 1))
        for i in range(len(puntos)):
            s = seg_ix[pos[i]:pos[i + 1]]
            if not len(s):
                resultado.append({"distancia_ruta5_m": np.inf, "distancia_otra_m": dist_otras[i],
                                  "km_estimado": np.nan, "objectid_eje": -1,
                                  "alternativas": []})
                continue
            dist, m = proyectar_segmentos(np.array([x[i], y[i]]), self.inicios[s], self.finales[s], self.m0[s], self.m1[s])
            # Desempate estable por OID; discrepancias de M quedan en alternativas.
            j = np.lexsort((s, self.oid[s], dist))[0]
            resultado.append({"distancia_ruta5_m": dist[j], "distancia_otra_m": dist_otras[i],
                              "km_estimado": m[j] / 1000, "objectid_eje": self.oid[s[j]],
                              "alternativas": list(zip(dist.tolist(), (m / 1000).tolist()))})
        return resultado


def decidir(c, protocolo, distancia_max=None):
    dmax = distancia_max if distancia_max is not None else protocolo["distancia_max_m"]
    km = c["km_estimado"]
    if c["distancia_ruta5_m"] > dmax:
        return "fuera_distancia"
    if c["distancia_otra_m"] - c["distancia_ruta5_m"] < protocolo["margen_competidora_m"]:
        return "via_ambigua"
    if not np.isfinite(km):
        return "medida_ausente"
    if not protocolo["km_min"] < km < protocolo["km_max_exclusivo"]:
        return "fuera_dominio"
    # Comparar todos los segmentos suficientemente cercanos, incluidas calzadas.
    alternativas = [m for d, m in c["alternativas"] if d <= min(dmax, c["distancia_ruta5_m"] + 30)]
    if any(not np.isfinite(m) or abs(m - km) * 1000 > protocolo["tolerancia_alternativas_ruta5_m"] for m in alternativas):
        return "medida_ambigua"
    borde = (km % protocolo["tramo_km"]) * 1000
    if min(borde, protocolo["tramo_km"] * 1000 - borde) <= protocolo["distancia_borde_tramo_m"]:
        return "borde_tramo"
    return "candidato_asignable"
