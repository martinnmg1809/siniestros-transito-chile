"""Tabla maestra de comparación (Cristóbal, tarea 1 del Día 1).
Lee resultados/modelos/metricas.csv sin recalcular nada y agrega columnas de contexto.
Uso desde la raíz del repo: python construir_comparacion_final.py
"""
import re
import pandas as pd

ENTRENA = {2022: "2020-2021", 2023: "2020-2022", 2024: "2020-2023"}
TRAMOS = {"ruta_completa": 255, "con_contrato": 153, "hibrido_ruta_completa": 255}

m = pd.read_csv("resultados/modelos/metricas.csv")

def descomponer(nombre):
    if nombre in ("M0", "M1"):
        return nombre, "base"
    h = nombre.startswith("Hibrido_")
    s = nombre.removeprefix("Hibrido_")
    fam, var = s.split("_", 1)
    return ("Hibrido_" if h else "") + fam, var

m[["familia", "variante"]] = m["modelo"].apply(lambda x: pd.Series(descomponer(x)))
m["anios_entrenamiento"] = m["anio_prueba"].map(ENTRENA)
m["n_tramos"] = m["cohorte"].map(TRAMOS)
cols = ["anio_prueba", "anios_entrenamiento", "cohorte", "n_tramos", "familia",
        "variante", "modelo", "particion", "siniestros", "esperados",
        "observado_esperado", "desvianza_por_hora", "captura5", "captura10",
        "captura20", "captura5_turno", "mae_12h_calendario"]
m = m[cols].sort_values(["cohorte", "anio_prueba", "familia", "variante", "particion"])
m["fuente"] = "resultados/modelos/metricas.csv"
m.to_csv("resultados/cierre/comparacion_final.csv", index=False, float_format="%.6f")
print(len(m), "filas")
