"""Datos del experimento: cuarentena espacial, ERA5, calendario y flujo rezagado."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from datos_ruta5 import cargar_eventos, referencia_entrenamiento, grilla_civil, exposicion_civil
from clima_utc import cargar_cache
from integrar_flujo import asignar_contratos, limites_documentados, serie_flujo, flujo_rezagado
from validar_ruta5 import codificar


def cuarentena_espacial(eventos, umbral_km=25):
    ref = referencia_entrenamiento(eventos).set_index("tramo").reindex(eventos.tramo)
    lat1, lat2 = np.deg2rad(eventos.Latitud), np.deg2rad(ref.lat.to_numpy())
    dl = np.deg2rad(eventos.longitud - ref.lon.to_numpy())
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dl / 2) ** 2
    dist = 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    bandera = dist > umbral_km
    q = eventos.loc[bandera].copy()
    q["distancia_referencia_km"] = np.asarray(dist)[bandera]
    q["motivo"] = "Kilometraje y coordenadas incompatibles; ubicación no imputada"
    return eventos.loc[~bandera].copy(), q


def preparar_experimento(salida=None):
    eventos, auditoria = cargar_eventos()
    eventos, cuarentena = cuarentena_espacial(eventos)
    ref = referencia_entrenamiento(eventos)
    tramos = ref.tramo.to_numpy()
    t, y, fuera = grilla_civil(eventos, tramos)
    e = exposicion_civil(t)
    z = cargar_cache()
    if not np.array_equal(t.to_numpy(dtype="datetime64[h]"), z["tiempo"]):
        raise ValueError("Serie climática incompatible con fechas")
    # Reusar solo si las celdas solicitadas por la referencia limpia están en caché.
    celdas = {tuple(c): i for i, c in enumerate(z["celdas"])}
    solicitadas = np.round(ref[["lat", "lon"]].to_numpy() / .25) * .25
    if any(tuple(c) not in celdas for c in solicitadas):
        raise ValueError("La depuración requiere una celda meteorológica no descargada")
    idx = np.array([celdas[tuple(c)] for c in solicitadas])
    if not np.array_equal(e, z["exposicion_tiempo"]) or not np.isfinite(z["precip"][idx][:, e > 0]).all():
        raise ValueError("Exposición/precipitación inválida")
    lluvia = np.digitize(z["precip"][idx], [.1, .5]).astype(np.int8)
    lluvia[:, e == 0] = 0
    fer = json.loads(Path("feriados.json").read_text())
    cod, dims = codificar(tramos, t, fer, lluvia)
    periodos = pd.period_range("2020Q1", "2024Q4", freq="Q")
    ip = ((t.year - 2020) * 4 + (t.month - 1) // 3).to_numpy()
    codigo = cod.astype(np.int64) * len(periodos) + ip
    dims = dims + (len(periodos),)
    asignacion = asignar_contratos(tramos)
    flujo = flujo_rezagado(asignacion, periodos, serie_flujo())
    valores = flujo.pivot(index="tramo", columns="periodo_objetivo", values="proxy_pasadas_por_punto_dia").reindex(index=tramos, columns=periodos).to_numpy()
    puntos = flujo.pivot(index="tramo", columns="periodo_objetivo", values="puntos_implicitos").reindex(index=tramos, columns=periodos).to_numpy()
    cubiertos = np.isfinite(valores).all(axis=1) & np.isfinite(puntos).all(axis=1)
    excluidos_dst = int(y[:, e == 0].sum())
    y[:, e == 0] = 0
    cobertura = []
    for anio in range(2020, 2025):
        d = eventos.loc[eventos.anio.eq(anio)]
        n = int(d.tramo.isin(tramos[cubiertos]).sum())
        cobertura.append({"anio": anio, "tramos_con_flujo": int(cubiertos.sum()), "tramos_total": len(tramos),
                          "siniestros_con_flujo": n, "siniestros_total": len(d), "porcentaje_eventos": 100 * n / len(d)})
    metadata = {"fuente_siniestros": auditoria, "registros_modelado": len(eventos),
                "ids_cuarentena": cuarentena.ID.astype(int).tolist(), "umbral_cuarentena_km": 25,
                "eventos_dst_excluidos": excluidos_dst, "eventos_fuera_dominio": fuera,
                "referencia_hasta": 2021, "era5": json.loads(str(z["metadatos"])),
                "flujo": "Proxy DGC por contrato, rezagado dos trimestres, con puntos de cobro rezagados",
                "publicacion_historica_acreditada": False,
                "cobertura": cobertura, "prediccion": "Conteos por hora, no riesgo por vehículo-km",
                "asociacion_contrato": "Intervalos interiores documentados, margen 1 km; no homogeneidad de tráfico acreditada"}
    metadata["fuentes_flujo_sha256"] = {v: hashlib.sha256(Path(f"data/fuentes/dgc/anexo_{v}.xls").read_bytes()).hexdigest()
                                       for v in ("2023_4t", "2024_4t")}
    metadata["clima_cache_sha256"] = hashlib.sha256(Path("clima_ruta5.npz").read_bytes()).hexdigest()
    if salida is not None:
        salida = Path(salida); salida.mkdir(parents=True, exist_ok=True)
        cuarentena.to_csv(salida / "cuarentena_espacial.csv", index=False)
        ref.to_csv(salida / "referencia_limpia.csv", index=False)
        asignacion.to_csv(salida / "asignacion_contratos.csv", index=False)
        limites_documentados().to_csv(salida / "limites_documentados.csv", index=False)
        flujo.to_csv(salida / "flujo_rezagado.csv", index=False)
        pd.DataFrame(cobertura).to_csv(salida / "cobertura_flujo.csv", index=False)
    return {"tiempo": t, "y": y, "expo": e, "codigo": codigo, "dims": dims,
            "proxy": valores, "puntos": puntos, "cubiertos": cubiertos,
            "tramos": tramos, "metadata": metadata}


def agrupar_modelado(datos, filas, anio):
    cols = np.flatnonzero(datos["tiempo"].year == anio)
    cod = datos["codigo"][np.ix_(filas, cols)].ravel()
    e = np.broadcast_to(datos["expo"][cols], (len(filas), len(cols))).ravel()
    y = datos["y"][np.ix_(filas, cols)].ravel()
    validas = e > 0
    claves, inversa = np.unique(cod[validas], return_inverse=True)
    return claves, np.bincount(inversa, weights=y[validas]), np.bincount(inversa, weights=e[validas])


def atributos(claves, datos):
    resto = claves.copy(); comp = []
    for dim in reversed(datos["dims"]):
        comp.append(resto % dim); resto //= dim
    comp.reverse()
    f = np.column_stack(comp).astype(np.float64)
    tramo, periodo = comp[0], comp[-1]
    # Se conserva el orden: tramo, hora, día, mes, feriado, lluvia, tendencia,
    # log(proxy rezagado), log(puntos rezagados).
    f[:, -1] = periodo // 4
    with np.errstate(invalid="ignore"):
        f = np.column_stack([f, np.log(datos["proxy"][tramo, periodo]), np.log(datos["puntos"][tramo, periodo])])
    return f


def expandir_prediccion(claves, tasa, datos, filas, anios):
    cols = np.flatnonzero(np.isin(datos["tiempo"].year, anios))
    cod = datos["codigo"][np.ix_(filas, cols)]
    e = np.broadcast_to(datos["expo"][cols], cod.shape)
    valida = e > 0
    indices = np.searchsorted(claves, cod[valida])
    if (indices >= len(claves)).any() or not np.array_equal(claves[indices], cod[valida]):
        raise ValueError("Predicción sin clave de evaluación")
    mu = np.zeros(cod.shape, float)
    mu[valida] = tasa[indices] * e[valida]
    return mu, datos["y"][np.ix_(filas, cols)].astype(float), datos["expo"][cols]
