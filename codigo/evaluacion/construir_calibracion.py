"""Calibración y recalibración (Cristóbal, tarea 4 del Día 1).
Lee comparacion_final.csv, calibracion.csv y recalibracion_candidato.csv.
MAE = error absoluto medio del TOTAL de la cohorte por turno de 12 h (no por tramo).
Uso: python proyecto.py construir_calibracion
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = pd.read_csv("resultados/cierre/comparacion_final.csv")
t = d[(d.particion == "prueba") & (d.cohorte != "hibrido_ruta_completa")]
res = t[["cohorte", "n_tramos", "anio_prueba", "modelo", "siniestros", "esperados",
         "observado_esperado", "desvianza_por_hora", "mae_12h_calendario"]].copy()
res["sesgo_nivel"] = res.observado_esperado.apply(
    lambda x: "sobreestima" if x < 0.95 else ("subestima" if x > 1.05 else "cercano a 1"))
res["fuente"] = "resultados/cierre/comparacion_final.csv"
res.to_csv("resultados/cierre/calibracion_resumen.csv", index=False, float_format="%.6f")

r = pd.read_csv("resultados/modelos/recalibracion_candidato.csv")
o = r[r.ajuste == "original"].set_index("anio_prueba")
n = r[r.ajuste == "recalibrado"].set_index("anio_prueba")
m1 = d[(d.modelo == "M1") & (d.cohorte == "ruta_completa") & (d.particion == "prueba")].set_index("anio_prueba")
rec = pd.DataFrame({
    "factor": n.factor, "anio_factor": n.anio_factor,
    "oe_original": o.observado_esperado, "oe_recalibrado": n.observado_esperado,
    "mae_original": o.mae_12h_calendario, "mae_recalibrado": n.mae_12h_calendario,
    "mae_M1_sin_recalibrar": m1.mae_12h_calendario,
    "desvianza_original": o.desvianza_por_hora, "desvianza_recalibrada": n.desvianza_por_hora,
    "captura5_original": o.captura5, "captura5_recalibrada": n.captura5}).reset_index()
rec = rec[rec.factor.notna()].copy()
rec["captura5_cambia"] = (rec.captura5_original - rec.captura5_recalibrada).abs() > 1e-12
rec["fuente"] = "resultados/modelos/recalibracion_candidato.csv"
rec.to_csv("resultados/cierre/recalibracion_resumen.csv", index=False, float_format="%.6f")

c = pd.read_csv("resultados/modelos/calibracion.csv")
c = c[(c.cohorte == "ruta_completa") & (c.modelo == "Poisson_clima")]
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for y, col in zip([2022, 2023, 2024], ["#9aa5b1", "#6a8fd8", "#1f6feb"]):
    s = c[c.anio_prueba == y]
    ax[0].plot(s.decil + 1, s.observado_esperado, marker="o", label=str(y), color=col)
ax[0].axhline(1, color="k", lw=0.8, ls="--")
ax[0].set_xlabel("Decil de riesgo predicho (1 = menor)"); ax[0].set_ylabel("Observado / esperado")
ax[0].set_title("Poisson_clima: calibración por deciles"); ax[0].set_ylim(0, 1.3); ax[0].legend()
p = d[(d.particion == "prueba") & (d.cohorte == "ruta_completa") & (d.modelo != "M0")]
p = p.pivot(index="modelo", columns="anio_prueba", values="observado_esperado").loc[
    ["M1", "Poisson_clima", "GradientBoosting_clima", "RandomForest_clima"]]
p.index = ["M1", "Poisson", "GB", "RF"]
p.plot.bar(ax=ax[1], rot=0, color=["#9aa5b1", "#6a8fd8", "#1f6feb"])
ax[1].axhline(1, color="k", lw=0.8, ls="--"); ax[1].set_ylabel("Observado / esperado")
ax[1].set_title("O/E total por modelo y año (ruta completa)"); ax[1].set_ylim(0, 1.45); ax[1].legend(title="Prueba", ncol=3, loc="upper right")
fig.tight_layout(); fig.savefig("resultados/cierre/fig_calibracion.png", dpi=150)
print(rec.round(4).T.to_string())
