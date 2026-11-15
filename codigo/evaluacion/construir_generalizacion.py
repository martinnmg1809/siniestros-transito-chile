"""Generalización train/prueba y estabilidad entre años (Cristóbal, tarea 3 del Día 1).
Lee resultados/cierre/comparacion_final.csv. Cohortes híbridas no tienen partición train.
Uso: python proyecto.py construir_generalizacion
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = pd.read_csv("resultados/cierre/comparacion_final.csv")
d = d[d.modelo != "M0"]
w = d.pivot_table(index=["cohorte", "familia", "variante", "modelo", "anio_prueba", "anios_entrenamiento"],
                  columns="particion", values="captura5").reset_index()
if "train" not in w:
    w["train"] = float("nan")
w = w.rename(columns={"train": "captura5_train", "prueba": "captura5_prueba"})
w["brecha_train_prueba_pp"] = (w.captura5_train - w.captura5_prueba) * 100
w["fuente"] = "resultados/cierre/comparacion_final.csv"
w.to_csv("resultados/cierre/generalizacion.csv", index=False, float_format="%.6f")

est = w.groupby(["cohorte", "modelo"]).agg(
    prueba_media=("captura5_prueba", "mean"), prueba_sd=("captura5_prueba", "std"),
    prueba_min=("captura5_prueba", "min"), prueba_max=("captura5_prueba", "max"),
    brecha_media_pp=("brecha_train_prueba_pp", "mean")).reset_index()
est.to_csv("resultados/cierre/estabilidad_temporal.csv", index=False, float_format="%.6f")

# Figura: ruta completa, train vs prueba por año
r = w[w.cohorte == "ruta_completa"]
modelos = ["M1", "Poisson_clima", "GradientBoosting_clima", "RandomForest_clima"]
fig, ax = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
for a, y in zip(ax, [2022, 2023, 2024]):
    s = r[r.anio_prueba == y].set_index("modelo").loc[modelos]
    x = range(len(modelos))
    a.bar([i - 0.2 for i in x], s.captura5_train * 100, 0.4, label="Train", color="#9aa5b1")
    a.bar([i + 0.2 for i in x], s.captura5_prueba * 100, 0.4, label="Prueba", color="#1f6feb")
    a.set_xticks(list(x)); a.set_xticklabels(["M1", "Poisson", "GB", "RF"])
    a.set_title(f"Prueba {y} (train {s.anios_entrenamiento.iloc[0]})")
a_ = ax[0]; a_.set_ylabel("Captura al 5 % (%)"); a_.legend()
fig.suptitle("Captura al 5 %: entrenamiento vs prueba, ruta completa (255 tramos)")
fig.tight_layout()
fig.savefig("resultados/cierre/fig_train_prueba.png", dpi=150)
print(est[est.cohorte == "ruta_completa"].round(4).to_string(index=False))
