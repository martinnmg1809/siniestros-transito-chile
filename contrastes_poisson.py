#!/usr/bin/env python3
"""Contrastes de predicción e inventario de versiones del modelo Poisson_clima.

python contrastes_poisson.py

Usa los artefactos de resultados/modelos/artefactos si existen. Si no, reajusta
la configuración ya elegida antes de 2024, con el mismo código y los mismos
atributos, y exige que reproduzca las cifras registradas antes de escribir
resultados. No elige modelos ni parámetros ni modifica salidas de modelos/.

Los contrastes comparan pares de combinaciones observadas en 2024 que difieren
en un solo atributo (lluvia, hora o posición de feriado) y conservan el tramo,
el resto del calendario y el trimestre. Son asociaciones del modelo, no efectos
causales ni riesgo por vehículo.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

NOMBRE = "Poisson_clima"
# Orden de atributos de datos_modelado.atributos.
COLUMNAS = ["tramo", "hora", "dia_semana", "mes", "feriado", "lluvia", "tendencia"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
ETIQUETAS = {
    "lluvia": {0: "seco (<0,1 mm/h)", 1: "llovizna (0,1-0,5 mm/h)", 2: "lluvia (≥0,5 mm/h)"},
    "feriado": {0: "día no feriado", 1: "inicio de feriado largo",
                2: "día intermedio de feriado", 3: "último día de feriado"},
    "hora": {h: f"{h:02d}:00" for h in range(24)},
}
# Referencias fijadas antes de mirar los resultados.
CONTRASTES = ([("lluvia", 0, b) for b in (1, 2)]
              + [("feriado", 0, b) for b in (1, 2, 3)]
              + [("hora", 12, h) for h in range(24) if h != 12])


def pares_contraste(f, columna, ref, comp):
    """Índices (i_ref, i_comp) de filas iguales salvo en `columna`.

    `f` contiene combinaciones únicas observadas; no se crean combinaciones
    nuevas modificando atributos.
    """
    j = COLUMNAS.index(columna)
    otras = [c for c in range(len(COLUMNAS)) if c != j]
    tabla = pd.DataFrame(np.asarray(f[:, :len(COLUMNAS)], float), columns=COLUMNAS)
    tabla["fila"] = np.arange(len(tabla))
    a = tabla.loc[tabla[columna].eq(ref), [COLUMNAS[c] for c in otras] + ["fila"]]
    b = tabla.loc[tabla[columna].eq(comp), [COLUMNAS[c] for c in otras] + ["fila"]]
    m = a.merge(b, on=[COLUMNAS[c] for c in otras], suffixes=("_ref", "_comp"), validate="one_to_one")
    return m.fila_ref.to_numpy(), m.fila_comp.to_numpy()


def contrastar(tasa, expo, f, columna, ref, comp):
    """Razón de tasas por par y un ejemplo con la combinación más frecuente."""
    i, k = pares_contraste(f, columna, ref, comp)
    if not len(i):
        raise ValueError(f"Sin pares observados para {columna} {ref}->{comp}")
    razon = tasa[k] / tasa[i]
    # Ejemplo: el par con más horas de exposición conjunta; no usa siniestros.
    e = int(np.argmax(np.minimum(expo[i], expo[k])))
    return {"pares": len(i), "razon_mediana": float(np.median(razon)),
            "razon_min": float(razon.min()), "razon_max": float(razon.max()),
            "ejemplo_ref": int(i[e]), "ejemplo_comp": int(k[e])}


def huella(modelo):
    """Hash de coeficientes y transformador: identifica el ajuste sin depender de joblib."""
    m = getattr(modelo, "modelo", modelo)
    h = hashlib.sha256(np.ascontiguousarray(m.coef, dtype=np.float64).tobytes())
    for _, t, _ in m.transformador.transformers_:
        for nombre in ("categories_", "mean_", "scale_"):
            valor = getattr(t, nombre, None)
            for v in (valor if isinstance(valor, list) else [] if valor is None else [valor]):
                h.update(np.ascontiguousarray(v, dtype=np.float64).tobytes())
    return h.hexdigest()


def razon_tendencia(modelo):
    """Razón de tasas por año del término numérico de tendencia (escala original).

    No se puede contrastar con pares de 2024 porque todas sus filas tienen el
    mismo año; es la parte del modelo que extrapola fuera del entrenamiento.
    """
    m = getattr(modelo, "modelo", modelo)
    cats = m.transformador.named_transformers_["categorias"]
    escala = m.transformador.named_transformers_["numericas"]
    n = sum(len(c) for c in cats.categories_)
    return float(np.exp(m.coef[n] / escala.scale_[0]))


def fecha_ejemplo(datos, clave, fila_tramo, anio):
    cols = np.flatnonzero(datos["tiempo"].year == anio)
    hit = cols[(datos["codigo"][fila_tramo, cols] == clave) & (datos["expo"][cols] > 0)]
    return datos["tiempo"][hit[0]].strftime("%Y-%m-%d %H:%M")


def cargar_o_reajustar(version, datos, carpeta, seleccion, reajuste):
    from datos_modelado import agrupar_modelado, atributos
    from modelos_conteo import ModeloConteo
    archivo = carpeta / "artefactos" / ("ruta_completa_Poisson_clima_2024.joblib" if version == "evaluado2024"
                                        else "candidato_reajustado2020_2024.joblib")
    fila = seleccion.loc[seleccion.anio_prueba.eq(2024) & seleccion.cohorte.eq("ruta_completa")
                         & seleccion.familia.eq("Poisson") & seleccion.variante.eq("clima")]
    if len(fila) != 1:
        raise ValueError("Selección de Poisson_clima para 2024 ausente o ambigua")
    parametros = json.loads(fila.iloc[0].parametros)
    if archivo.exists():
        return joblib.load(archivo), {"origen": "artefacto", "archivo": str(archivo),
                                      "sha256_archivo": hashlib.sha256(archivo.read_bytes()).hexdigest(),
                                      "parametros": parametros}
    filas = np.arange(len(datos["tramos"]))
    hasta = 2023 if version == "evaluado2024" else 2024
    grupos = [agrupar_modelado(datos, filas, a) for a in range(2020, hasta + 1)]
    c, y, e = (np.concatenate([g[i] for g in grupos]) for i in range(3))
    if version == "evaluado2024":
        # Mismo orden que entrenar_comparacion.py; reajustar_candidato.py no ordena.
        o = np.argsort(c)
        c, y, e = c[o], y[o], e[o]
    modelo = ModeloConteo("Poisson", "clima", parametros).fit(atributos(c, datos), y, e)
    meta = {"origen": "reajuste_local_con_codigo_versionado", "parametros": parametros,
            "ajuste": f"2020-{hasta}", "iteraciones": int(modelo.diagnostico["iteraciones"]),
            "objetivo": float(modelo.diagnostico["objetivo"])}
    if version == "reajustado2020_2024":
        ref = reajuste["ajustes"][0]
        meta["objetivo_registrado"] = ref["objetivo"]
        meta["iteraciones_registradas"] = ref["iteraciones"]
        if not np.isclose(meta["objetivo"], ref["objetivo"], rtol=1e-8, atol=0):
            raise RuntimeError("El reajuste local no reproduce el objetivo registrado en reajuste.json")
    return modelo, meta


def objetivo_registrado(auditoria):
    """Objetivo del ajuste Poisson_clima evaluado en 2024 según auditoria.json."""
    filas = [a for a in auditoria["ajustes"] if a.get("anio_prueba") == 2024
             and a.get("cohorte") == "ruta_completa" and a.get("modelo") == NOMBRE]
    if len(filas) != 1:
        raise ValueError("auditoria.json no registra un único ajuste Poisson_clima de 2024")
    return filas[0]


def verificar_evaluado(modelo, datos, metricas, meta, auditoria):
    """El modelo evaluado debe reproducir metricas.csv de 2024 antes de interpretarse.

    Artefacto original: todas las métricas a 1e-10. Reajuste local: el objetivo
    debe coincidir con el registrado (mismo óptimo, rtol 1e-8); L-BFGS puede
    detenerse en otro punto de una región plana según el orden de las operaciones
    de punto flotante, así que la captura al 5 % (criterio de selección) se exige
    a 1e-6 y el resto de métricas a 1e-3. Todos los desvíos quedan registrados.
    """
    from datos_modelado import agrupar_modelado, atributos, expandir_prediccion
    from validar_ruta5 import resumen
    filas = np.arange(len(datos["tramos"]))
    claves = agrupar_modelado(datos, filas, 2024)[0]
    mu, y, e = expandir_prediccion(claves, modelo.predict_rate(atributos(claves, datos)), datos, filas, [2024])
    obtenido = resumen(y, mu, e)
    fila = metricas.loc[metricas.anio_prueba.eq(2024) & metricas.cohorte.eq("ruta_completa")
                        & metricas.modelo.eq(NOMBRE) & metricas.particion.eq("prueba")].iloc[0]
    desvio = {k: float(abs(v - fila[k]) / max(abs(fila[k]), 1e-300)) for k, v in obtenido.items()}
    if meta["origen"] == "artefacto":
        tolerancias = {k: 1e-10 for k in desvio}
        verificacion = {}
    else:
        ref = objetivo_registrado(auditoria)
        verificacion = {"objetivo_registrado": ref["objetivo"], "iteraciones_registradas": ref["iteraciones"],
                        "desvio_relativo_objetivo": abs(meta["objetivo"] - ref["objetivo"]) / abs(ref["objetivo"])}
        if verificacion["desvio_relativo_objetivo"] > 1e-8:
            raise RuntimeError(f"El reajuste no alcanza el objetivo registrado: {verificacion}")
        tolerancias = {k: (1e-6 if k == "captura5" else 1e-3) for k in desvio}
    fuera = {k: v for k, v in desvio.items() if v > tolerancias[k]}
    if fuera:
        raise RuntimeError(f"El modelo no reproduce metricas.csv de 2024: {fuera}")
    verificacion.update({"tolerancias_relativas": tolerancias, "desvios_relativos": desvio})
    return mu, y, obtenido, verificacion


def tabla_contrastes(version, modelo, datos):
    from datos_modelado import agrupar_modelado, atributos
    filas = np.arange(len(datos["tramos"]))
    claves, _, expo = agrupar_modelado(datos, filas, 2024)
    f = atributos(claves, datos)
    tasa = modelo.predict_rate(f)
    salida = []
    for columna, ref, comp in CONTRASTES:
        r = contrastar(tasa, expo, f, columna, ref, comp)
        i, k = r.pop("ejemplo_ref"), r.pop("ejemplo_comp")
        tramo = int(f[i, 0])
        salida.append({
            "version": version, "contraste": columna,
            "referencia": ETIQUETAS[columna][ref], "comparado": ETIQUETAS[columna][comp], **r,
            "ejemplo_tramo_km": int(datos["tramos"][tramo]),
            "ejemplo_dia_semana": DIAS[int(f[i, 2])], "ejemplo_mes": int(f[i, 3]) + 1,
            "ejemplo_fecha_ref": fecha_ejemplo(datos, claves[i], tramo, 2024),
            "ejemplo_fecha_comp": fecha_ejemplo(datos, claves[k], tramo, 2024),
            "ejemplo_horas_ref": float(expo[i]), "ejemplo_horas_comp": float(expo[k]),
            "ejemplo_tasa_ref_por_hora": float(tasa[i]), "ejemplo_tasa_comp_por_hora": float(tasa[k]),
            "ejemplo_diferencia_por_hora": float(tasa[k] - tasa[i]),
        })
    return pd.DataFrame(salida)


def ejemplo_turno(mu, y, datos, inicio, factor, anio_factor):
    """Turno de 12 h de reloj local: tramos priorizados y agregado de la ruta."""
    from evaluacion import pesos_seleccion
    t = datos["tiempo"][datos["tiempo"].year == 2024]
    j = np.flatnonzero(t == pd.Timestamp(inicio))
    if len(j) != 1 or j[0] % 12:
        raise ValueError("El turno debe comenzar a las 00:00 o 12:00 de una fecha de 2024")
    sl = slice(j[0], j[0] + 12)
    esperado, observado = mu[:, sl].sum(axis=1), y[:, sl].sum(axis=1)
    peso = pesos_seleccion(esperado, np.ones(len(esperado)), .05)
    orden = np.argsort(-esperado, kind="stable")
    d = pd.DataFrame({"turno_inicio": inicio, "tramo_km": datos["tramos"][orden],
                      "rango": np.arange(1, len(orden) + 1), "peso_presupuesto_5pct": peso[orden],
                      "esperado_original": esperado[orden], "esperado_recalibrado": esperado[orden] * factor,
                      "observado": observado[orden]})
    d = d.loc[d.peso_presupuesto_5pct > 0]
    total = {"turno_inicio": inicio, "tramo_km": "RUTA (255 tramos)", "rango": np.nan,
             "peso_presupuesto_5pct": np.nan, "esperado_original": esperado.sum(),
             "esperado_recalibrado": esperado.sum() * factor, "observado": observado.sum()}
    d = pd.concat([d, pd.DataFrame([total])], ignore_index=True)
    d["factor_recalibracion"], d["anio_factor"] = factor, anio_factor
    return d


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--modelos", type=Path, default=Path("resultados/modelos"))
    p.add_argument("--salida", type=Path, default=Path("resultados/cierre"))
    p.add_argument("--turno", default="2024-07-12 12:00",
                   help="Inicio del turno de ejemplo (fijado a priori: viernes de invierno, 12:00-24:00)")
    args = p.parse_args()
    from datos_modelado import preparar_experimento
    auditoria = json.loads((args.modelos / "auditoria.json").read_text())
    if auditoria["modelo_candidato_por_cv_pre2024"] != NOMBRE:
        raise ValueError("La candidata registrada ya no es Poisson_clima; revisar antes de interpretar")
    seleccion = pd.read_csv(args.modelos / "seleccion_temporal.csv")
    metricas = pd.read_csv(args.modelos / "metricas.csv")
    recal = pd.read_csv(args.modelos / "recalibracion_candidato.csv")
    reajuste = json.loads((args.modelos / "reajuste.json").read_text())
    datos = preparar_experimento()
    args.salida.mkdir(parents=True, exist_ok=True)

    inventario, tablas = {}, []
    for version in ("evaluado2024", "reajustado2020_2024"):
        modelo, meta = cargar_o_reajustar(version, datos, args.modelos, seleccion, reajuste)
        meta["huella_coeficientes_sha256"] = huella(modelo)
        meta["razon_tasa_por_anio_tendencia"] = razon_tendencia(modelo)
        if version == "evaluado2024":
            mu, y, obtenido, meta["verificacion_2024"] = verificar_evaluado(modelo, datos, metricas, meta, auditoria)
            meta["metricas_2024"] = obtenido
            fila = recal.loc[recal.anio_prueba.eq(2024) & recal.ajuste.eq("recalibrado")].iloc[0]
            turno = ejemplo_turno(mu, y, datos, args.turno, float(fila.factor), int(fila.anio_factor))
            turno.to_csv(args.salida / "ejemplo_turno_poisson.csv", index=False)
            del mu, y
        tablas.append(tabla_contrastes(version, modelo, datos))
        inventario[version] = meta
    contrastes = pd.concat(tablas, ignore_index=True)
    contrastes.to_csv(args.salida / "contrastes_poisson.csv", index=False)
    inventario["codigo_sha256"] = {n: hashlib.sha256(Path(n).read_bytes()).hexdigest()
                                   for n in ["contrastes_poisson.py", "datos_modelado.py", "modelos_conteo.py"]}
    inventario["fuentes"] = {"clima_cache_sha256": datos["metadata"]["clima_cache_sha256"],
                             "clima_cache_registrado": auditoria["datos"]["clima_cache_sha256"],
                             "fuentes_flujo_sha256": datos["metadata"]["fuentes_flujo_sha256"]}
    (args.salida / "version_modelo.json").write_text(json.dumps(inventario, ensure_ascii=False, indent=2))
    with pd.option_context("display.width", 200, "display.max_columns", 8):
        print(contrastes[["version", "contraste", "referencia", "comparado", "pares", "razon_mediana",
                          "razon_min", "razon_max"]].to_string(index=False))


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
