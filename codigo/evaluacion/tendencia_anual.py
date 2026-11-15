#!/usr/bin/env python3
"""¿Explica la tendencia anual la sobreestimación de Poisson_clima?

python proyecto.py tendencia_anual

Ajusta, para cada año de prueba, un Poisson con solo intercepto y tendencia
lineal anual (offset de horas del año) sobre los totales de entrenamiento,
y compara su O/E extrapolado con el registrado en metricas.csv. Usa solo
salidas versionadas: no necesita ERA5 ni artefactos. Es una aproximación
(sin L2 ni otros atributos), no el coeficiente del modelo real; ese lo
registra contrastes_poisson.py en version_modelo.json.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize


def ajustar_tendencia(anios, conteos, horas):
    """Devuelve (intercepto, pendiente) del Poisson log(mu) = a + b*(anio-2020) + log(horas)."""
    x = np.asarray(anios, float) - 2020
    y, e = np.asarray(conteos, float), np.asarray(horas, float)

    def nll(b):
        eta = b[0] + b[1] * x
        return np.sum(np.exp(eta) * e - y * eta)

    def grad(b):
        r = np.exp(b[0] + b[1] * x) * e - y
        return np.array([r.sum(), (r * x).sum()])

    res = minimize(nll, [np.log(y.sum() / e.sum()), 0.], jac=grad, method="BFGS")
    # Convergencia relativa: gradiente pequeño frente al total de siniestros.
    if not np.isfinite(res.x).all() or np.abs(grad(res.x)).max() > 1e-6 * y.sum():
        raise RuntimeError(f"Ajuste de tendencia sin converger: {res.message}")
    return res.x


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--modelos", type=Path, default=Path("resultados/modelos"))
    p.add_argument("--salida", type=Path, default=Path("resultados/cierre"))
    args = p.parse_args()
    auditoria = json.loads((args.modelos / "auditoria.json").read_text())
    n = {c["anio"]: c["siniestros_total"] for c in auditoria["datos"]["cobertura"]}
    if sum(n.values()) != auditoria["datos"]["registros_modelado"]:
        raise ValueError("Los totales anuales no suman la población del experimento")
    horas = {a: len(pd.date_range(f"{a}-01-01", f"{a}-12-31 23:00", freq="h")) for a in n}
    metricas = pd.read_csv(args.modelos / "metricas.csv")
    filas = []
    for prueba in (2022, 2023, 2024):
        tr = [a for a in sorted(n) if a < prueba]
        a, b = ajustar_tendencia(tr, [n[t] for t in tr], [horas[t] for t in tr])
        esperado = float(np.exp(a + b * (prueba - 2020)) * horas[prueba])
        for modelo in ("Poisson_clima", "GradientBoosting_clima", "M1"):
            r = metricas.loc[metricas.anio_prueba.eq(prueba) & metricas.cohorte.eq("ruta_completa")
                             & metricas.modelo.eq(modelo) & metricas.particion.eq("prueba")].iloc[0]
            filas.append({"anio_prueba": prueba, "anios_entrenamiento": f"{tr[0]}-{tr[-1]}",
                          "razon_por_anio_tendencia": float(np.exp(b)), "observados": n[prueba],
                          "esperado_solo_tendencia": esperado, "oe_solo_tendencia": n[prueba] / esperado,
                          "modelo_registrado": modelo, "esperado_registrado": float(r.esperados),
                          "oe_registrado": float(r.observado_esperado)})
    d = pd.DataFrame(filas)
    args.salida.mkdir(parents=True, exist_ok=True)
    d.to_csv(args.salida / "tendencia_anual.csv", index=False)
    print(d.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
