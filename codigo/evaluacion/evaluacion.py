"""Evaluación con presupuesto exacto e igual tratamiento de tasas empatadas.

Los pesos fraccionarios representan selección aleatoria uniforme dentro de un
empate. No se usa el resultado observado para desempatar. La captura mide
cobertura retrospectiva, no siniestros evitados.
"""
import numpy as np


def _vectores(y, mu, expo):
    y, mu, expo = (np.asarray(a, dtype=float) for a in (y, mu, expo))
    if y.ndim != 1 or y.size == 0 or y.shape != mu.shape or y.shape != expo.shape:
        raise ValueError("Se requieren vectores no vacíos de igual tamaño")
    if not all(np.isfinite(a).all() for a in (y, mu, expo)):
        raise ValueError("Las observaciones, predicciones y exposiciones deben ser finitas")
    if (y < 0).any() or (mu < 0).any() or (expo <= 0).any():
        raise ValueError("Conteos y predicciones no negativos; exposición estrictamente positiva")
    return y, mu, expo


def _grupos(mu, expo):
    _, mu, expo = _vectores(np.zeros_like(mu), mu, expo)
    tasa = mu / expo
    orden = np.argsort(-tasa, kind="stable")
    tasas = tasa[orden]
    # Agrupar también discrepancias de redondeo de una misma tasa (exp/log).
    inicio = np.r_[0, np.flatnonzero(~np.isclose(tasas[1:], tasas[:-1],
                                               rtol=1e-10, atol=0.0)) + 1]
    grupo = np.repeat(np.arange(len(inicio)), np.diff(np.r_[inicio, len(mu)]))
    return orden, inicio, grupo


def pesos_seleccion(mu, expo, fraccion):
    """Peso [0,1] por fila; sum(peso*expo) = fraccion*sum(expo).

    Una fila agrupada puede representar varias horas. Toda tasa empatada recibe
    la misma fracción, incluso cuando el empate cruza la frontera del presupuesto.
    """
    if not np.isfinite(fraccion) or not 0 <= fraccion <= 1:
        raise ValueError("La fracción debe estar entre 0 y 1")
    expo = np.asarray(expo, float)
    orden, inicio, grupo = _grupos(mu, expo)
    eg = np.add.reduceat(expo[orden], inicio)
    antes = np.r_[0.0, np.cumsum(eg)[:-1]]
    peso_grupo = np.clip((fraccion * expo.sum() - antes) / eg, 0, 1)
    pesos = np.empty(len(expo), float)
    pesos[orden] = peso_grupo[grupo]
    return pesos


def curva_captura(y, mu, expo):
    """Vértices de la curva; interpolación lineal dentro de cada tasa empatada."""
    y, mu, expo = _vectores(y, mu, expo)
    orden, inicio, _ = _grupos(mu, expo)
    cx = np.r_[0.0, np.cumsum(np.add.reduceat(expo[orden], inicio)) / expo.sum()]
    cy = (np.r_[0.0, np.cumsum(np.add.reduceat(y[orden], inicio)) / y.sum()]
          if y.sum() else np.full(len(cx), np.nan))
    return cx, cy


def captura(y, mu, expo, fracs=(0.05, 0.10, 0.20)):
    """Lista (presupuesto, captura); sin eventos, captura es NaN."""
    y, mu, expo = _vectores(y, mu, expo)
    fracs = np.asarray(fracs, float)
    if not np.isfinite(fracs).all() or ((fracs < 0) | (fracs > 1)).any():
        raise ValueError("Las fracciones deben estar entre 0 y 1")
    cx, cy = curva_captura(y, mu, expo)
    return list(zip(fracs.tolist(), np.interp(fracs, cx, cy).tolist()))


def desvianza(y, mu):
    y, mu, _ = _vectores(y, mu, np.ones_like(y))
    if ((mu == 0) & (y > 0)).any():
        return float("inf")
    positivo = y > 0
    return float(2 * ((y[positivo] * np.log(y[positivo] / mu[positivo])).sum()
                      - y.sum() + mu.sum()))


def captura_turnos(y, mu, fraccion=0.05, horas=12):
    """Vigilar los mismos tramos durante cada turno, presupuesto fijo por turno.

    Filas=tramos; columnas=horas ordenadas. No impone restricciones de traslado.
    Las ventanas comienzan en la primera hora proporcionada, sin solapamiento.
    """
    y, mu = np.asarray(y, float), np.asarray(mu, float)
    if y.ndim != 2 or y.shape != mu.shape or y.shape[0] == 0:
        raise ValueError("Se requieren matrices tramo x hora del mismo tamaño")
    if horas < 1 or y.shape[1] % horas:
        raise ValueError("La cantidad de horas debe ser divisible por la duración del turno")
    _vectores(y.ravel(), mu.ravel(), np.ones(y.size))
    yt = y.reshape(y.shape[0], -1, horas).sum(axis=2)
    mt = mu.reshape(mu.shape[0], -1, horas).sum(axis=2)
    cubiertos = np.array([pesos_seleccion(mt[:, j], np.ones(y.shape[0]), fraccion)
                         @ yt[:, j] for j in range(yt.shape[1])])
    return {"cubiertos": cubiertos, "observados": yt.sum(axis=0),
            "esperados": mt.sum(axis=0)}


def bootstrap_pareado(y, predicciones, bloques, fraccion=0.05,
                      replicas=2000, semilla=42, expo=None):
    """IC percentil de diferencias de captura, predicciones y selección fijas.

    El remuestreo conserva juntas todas las filas del mismo bloque temporal.
    No incluye incertidumbre de reentrenamiento ni valida IC de coeficientes.
    Se compara cada candidato con la primera entrada de predicciones.
    """
    y, bloques = np.asarray(y, float).ravel(), np.asarray(bloques).ravel()
    expo = np.ones_like(y) if expo is None else np.asarray(expo, float).ravel()
    if bloques.shape != y.shape or replicas < 2 or not predicciones:
        raise ValueError("Bloques incompatibles, sin modelos o réplicas insuficientes")
    _, ib = np.unique(bloques, return_inverse=True)
    total = np.bincount(ib, weights=y)
    if len(total) < 2 or total.sum() <= 0:
        raise ValueError("Bootstrap requiere al menos dos bloques y eventos")
    dentro = {}
    for nombre, mu in predicciones.items():
        mu = np.asarray(mu, float).ravel()
        _vectores(y, mu, expo)
        pesos = pesos_seleccion(mu, expo, fraccion)
        dentro[nombre] = np.bincount(ib, weights=y * pesos, minlength=len(total))
    idx = np.random.default_rng(semilla).integers(0, len(total), (replicas, len(total)))
    den = total[idx].sum(axis=1)
    valido = den > 0
    base = next(iter(dentro))
    salida = {}
    for nombre, valores in dentro.items():
        if nombre == base:
            continue
        dif = (valores - dentro[base])[idx].sum(axis=1)[valido] / den[valido]
        lo, hi = np.quantile(dif, [.025, .975])
        salida[nombre] = {"referencia": base,
                          "diferencia_pp": float(100 * (valores - dentro[base]).sum() / total.sum()),
                          "ic95_inf_pp": float(100 * lo), "ic95_sup_pp": float(100 * hi),
                          "replicas_validas": int(valido.sum())}
    return salida
