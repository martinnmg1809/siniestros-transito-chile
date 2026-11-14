"""Regenera la cobertura del proxy de flujo por año y grupo de tramos.

Solo lee archivos versionados (sin descargas ni entrenamiento) y falla si algo no
concilia con resultados/modelos. Salida: resultados/cierre/cobertura_flujo_detalle.csv
"""
import json
import sys
from pathlib import Path
import pandas as pd
from datos_ruta5 import cargar_eventos
from integrar_flujo import asignar_contratos, limites_documentados

RAIZ = Path(__file__).resolve().parent
MODELOS = RAIZ / "resultados" / "modelos"
SALIDA = RAIZ / "resultados" / "cierre" / "cobertura_flujo_detalle.csv"
POBLACION, TRAMOS = 14420, 255


def exigir(condicion, mensaje):
    if not condicion:
        sys.exit(f"NO CONCILIA: {mensaje}")


def grupo_sin_contrato(tramo, limites):
    if tramo + 5 <= limites.km_inicio.min():
        return "antes_primer_contrato"
    if tramo >= limites.km_fin.max():
        return "despues_ultimo_contrato"
    return "frontera_bypass_margen"


def main():
    limites = limites_documentados()
    guardada = pd.read_csv(MODELOS / "asignacion_contratos.csv").fillna({"contrato": ""})
    asignacion = asignar_contratos(guardada.tramo, limites)
    exigir(asignacion.contrato.tolist() == guardada.contrato.tolist(),
           "asignacion_contratos.csv difiere de asignar_contratos(limites_documentados())")
    exigir(len(asignacion) == TRAMOS, f"se esperaban {TRAMOS} tramos")
    asignacion["grupo"] = [c and "con_contrato" or grupo_sin_contrato(t, limites)
                           for t, c in zip(asignacion.tramo, asignacion.contrato)]

    ids = set(json.load(open(MODELOS / "auditoria.json"))["datos"]["ids_cuarentena"])
    eventos, _ = cargar_eventos()
    eventos = eventos.loc[~eventos.ID.isin(ids)]
    exigir(len(eventos) == POBLACION, f"{len(eventos)} eventos, se esperaban {POBLACION}")
    eventos = eventos.merge(asignacion[["tramo", "contrato", "grupo"]], on="tramo", how="left", validate="m:1")
    exigir(eventos.grupo.notna().all(), "hay eventos en tramos fuera de la grilla de 255")

    totales = eventos.groupby("anio").size()
    tramos = asignacion.groupby(["grupo", "contrato"]).size()
    filas = []
    for (anio, grupo, contrato), n in eventos.groupby(["anio", "grupo", "contrato"]).size().items():
        filas.append(dict(anio=anio, grupo=grupo, contrato=contrato or "(sin contrato)",
                          tramos=int(tramos[(grupo, contrato)]), siniestros=int(n),
                          siniestros_total_anio=int(totales[anio]),
                          porcentaje_eventos=round(100 * n / totales[anio], 2),
                          poblacion=POBLACION,
                          fuente="ruta5_2020_2024.csv.gz sin ids_cuarentena; asignacion_contratos.csv"))
    detalle = pd.DataFrame(filas).sort_values(["anio", "grupo", "contrato"]).reset_index(drop=True)

    con = detalle.loc[detalle.grupo.eq("con_contrato")].groupby("anio").siniestros.sum()
    ref = pd.read_csv(MODELOS / "cobertura_flujo.csv").set_index("anio")
    exigir(int(asignacion.grupo.eq("con_contrato").sum()) == int(ref.tramos_con_flujo.iloc[0]),
           "tramos con contrato != tramos_con_flujo")
    exigir(con.to_dict() == ref.siniestros_con_flujo.to_dict(), "siniestros con contrato != cobertura_flujo.csv")
    exigir(totales.to_dict() == ref.siniestros_total.to_dict(), "totales anuales != cobertura_flujo.csv")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    detalle.to_csv(SALIDA, index=False)
    print(asignacion.groupby("grupo").size().to_string())
    print(con.to_string())
    print(f"OK: {POBLACION} eventos, {TRAMOS} tramos; escrito {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
