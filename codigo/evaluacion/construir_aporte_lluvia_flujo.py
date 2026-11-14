"""Aporte de lluvia y de flujo (Cristóbal, tarea 2 del Día 1).
Lluvia = clima - calendario. Flujo = clima+flujo - clima. Cohorte con_contrato (153 tramos).
Lee resultados/modelos/bootstrap.csv (IC pareados, 2.000 remuestreos semanales, predicciones fijas).
"""
import pandas as pd

b = pd.read_csv("resultados/modelos/bootstrap.csv")
b = b[b.cohorte == "con_contrato"]
rows = []
for fam in ["Poisson", "GradientBoosting", "RandomForest"]:
    for aporte, mod, ref in [("lluvia", f"{fam}_clima", f"{fam}_calendario"),
                             ("flujo", f"{fam}_clima_flujo", f"{fam}_clima")]:
        s = b[(b.modelo == mod) & (b.referencia == ref)]
        for _, r in s.iterrows():
            rows.append(dict(aporte=aporte, familia=fam, anio_prueba=r.anio_prueba,
                cohorte="con_contrato", n_tramos=153, modelo=mod, referencia=ref,
                diferencia_captura5_pp=round(r.diferencia_pp, 3),
                ic95_inf_pp=round(r.ic95_inf_pp, 3), ic95_sup_pp=round(r.ic95_sup_pp, 3),
                ic_incluye_cero=bool(r.ic95_inf_pp <= 0 <= r.ic95_sup_pp),
                replicas_validas=int(r.replicas_validas),
                fuente="resultados/modelos/bootstrap.csv"))
o = pd.DataFrame(rows).sort_values(["aporte", "familia", "anio_prueba"])
o.to_csv("resultados/cierre/aporte_lluvia_flujo.csv", index=False)
pd.set_option("display.width", 250)
print(o.drop(columns=["cohorte", "n_tramos", "referencia", "replicas_validas", "fuente"]).to_string(index=False))
