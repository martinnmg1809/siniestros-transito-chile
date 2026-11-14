"""Exportación portátil de la candidata existente, comprobada contra sus joblib.

No ajusta coeficientes. Permite reproducir el piloto desde Git sin los cachés ERA5.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from insumos_piloto import sha256


def predecir(modelo, atributos):
    f = np.asarray(atributos, dtype=float)
    if f.ndim != 2 or f.shape[1] != 9 or not np.isfinite(f[:, :7]).all():
        raise ValueError("Atributos del piloto inválidos")
    eta = np.full(len(f), modelo["intercepto"], dtype=float)
    for columna, categorias, coef in zip(range(6), modelo["categorias"], modelo["coef_categorias"]):
        cats = np.asarray(categorias)
        ix = np.searchsorted(cats, f[:, columna])
        if (ix >= len(cats)).any() or not np.array_equal(cats[ix], f[:, columna]):
            raise ValueError("Categoría fuera del dominio del modelo")
        eta += np.asarray(coef)[ix]
    eta += (f[:, 6] - modelo["tendencia_media"]) / modelo["tendencia_escala"] * modelo["coef_tendencia"]
    tasas = np.maximum(np.exp(eta), 1e-12)
    if not np.isfinite(tasas).all():
        raise ValueError("Predicción no finita")
    return tasas


def cargar(config):
    archivo = Path(config["artefacto_portable"])
    if sha256(archivo) != config["sha256_portable"]:
        raise ValueError("El modelo portátil no coincide con el protocolo")
    m = json.loads(archivo.read_text())
    if (m["modelo"] != "Poisson_clima" or m["sha256_joblib"] != config["sha256_modelo"] or
            m["sha256_joblib_recalibrado"] != config["sha256_recalibrado"] or m["ajuste_hasta"] != 2024):
        raise ValueError("Artefacto de otra candidata o período")
    return m


def exportar(config, salida):
    import joblib
    from proyecto import RAIZ
    from verificar_cierre import verificar_tablas
    verificar_tablas(RAIZ)
    for campo, digest in [("artefacto", "sha256_modelo"), ("artefacto_recalibrado", "sha256_recalibrado")]:
        if sha256(config[campo]) != config[digest]:
            raise ValueError("El joblib no corresponde a la candidata documentada")
    m = joblib.load(config["artefacto"])
    cal = joblib.load(config["artefacto_recalibrado"])
    if (m.familia != "Poisson" or m.variante != "clima" or m.columnas != list(range(7)) or
            cal.anio_factor != 2024):
        raise ValueError("Este piloto solo admite la candidata clima, sin flujo")
    cats = m.transformador.named_transformers_["categorias"].categories_
    estandar = m.transformador.named_transformers_["numericas"]
    coef, k = [], 0
    for c in cats:
        coef.append(m.coef[k:k + len(c)].tolist())
        k += len(c)
    if len(m.coef) != k + 2:
        raise ValueError("Orden de coeficientes inesperado")
    portable = {"modelo": "Poisson_clima", "ajuste_desde": 2020, "ajuste_hasta": 2024,
                "sha256_joblib": config["sha256_modelo"], "sha256_joblib_recalibrado": config["sha256_recalibrado"],
                "columnas": ["tramo_indice", "hora", "dia_semana", "mes_0", "feriado", "lluvia", "tendencia", "log_flujo_no_usado", "log_puntos_no_usado"],
                "categorias": [c.tolist() for c in cats], "coef_categorias": coef,
                "intercepto": float(m.coef[-1]), "coef_tendencia": float(m.coef[-2]),
                "tendencia_media": float(estandar.mean_[0]), "tendencia_escala": float(estandar.scale_[0]),
                "factor_recalibracion_referencia": cal.factor, "anio_factor": cal.anio_factor,
                "parametros": m.parametros, "evaluacion_futura": False}
    rng = np.random.default_rng(42)
    f = np.full((2048, 9), np.nan)
    for i, c in enumerate(cats):
        f[:, i] = rng.choice(c, len(f))
    f[:, 6] = rng.integers(0, 8, len(f))
    np.testing.assert_allclose(predecir(portable, f), m.predict_rate(f), rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(predecir(portable, f) * cal.factor, cal.predict_rate(f), rtol=1e-12, atol=1e-14)
    portable["comprobacion_exportacion"] = {"filas": len(f), "incluye_tendencias_futuras": True,
                                            "coincide_original_y_recalibrado": True, "rtol": 1e-12, "atol": 1e-14}
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(portable, ensure_ascii=False, indent=2) + "\n")
    return sha256(salida)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=Path("config/piloto_12h.json"))
    p.add_argument("--salida", type=Path, default=Path("resultados/piloto/modelo_poisson.json"))
    a = p.parse_args()
    c = json.loads(a.config.read_text())
    digest = exportar(c, a.salida)
    print("Modelo exportado sin entrenar:", a.salida, "SHA256:", digest)
