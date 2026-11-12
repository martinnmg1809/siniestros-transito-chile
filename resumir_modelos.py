#!/usr/bin/env python3
"""Tablas, figuras y bitácora reproducibles a partir de los modelos ya evaluados."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MARCAS = ("<!-- INICIO_MODELOS_ENTREGA3 -->", "<!-- FIN_MODELOS_ENTREGA3 -->")
COLORES = {"Poisson": "#247a9e", "GradientBoosting": "#ce7628", "RandomForest": "#41804b"}


def tabla(d):
    """Markdown sin dependencia opcional tabulate."""
    return "\n".join(["| " + " | ".join(map(str, d.columns)) + " |",
                      "|" + "---|" * len(d.columns)] +
                     ["| " + " | ".join(map(str, r)) + " |" for r in d.itertuples(index=False, name=None)])


def numero(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


def figuras(m, b, cal, salida):
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), layout="constrained")
    for ax, metrica, titulo in zip(axs, ["captura5", "captura5_turno"],
                                  ["Priorización global de horas", "Patrullaje fijo por turno de 12 horas"]):
        for nombre in ["M1"] + [f"{f}_clima" for f in COLORES]:
            d = m.loc[m.cohorte.eq("ruta_completa") & m.particion.eq("prueba") & m.modelo.eq(nombre)]
            ax.plot(d.anio_prueba, d[metrica] * 100, marker="o", color=COLORES.get(nombre.split("_")[0], "#666666"),
                    label=nombre.replace("_clima", ""))
        ax.set(xticks=[2022, 2023, 2024], ylabel="Siniestros capturados (%)", title=titulo, xlabel="Año de prueba")
        ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle("Ruta completa · presupuesto del 5 % · entrenamiento con años anteriores")
    fig.savefig(salida / "01_captura_temporal.png", dpi=160); plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for ax, cohorte, titulo in zip(axs, ["con_contrato", "hibrido_ruta_completa"],
                                  ["153 tramos con proxy DGC", "255 tramos con respaldo sin flujo"]):
        for j, (familia, color) in enumerate(COLORES.items()):
            pref = "Hibrido_" if cohorte.startswith("hibrido") else ""
            d = b.loc[b.cohorte.eq(cohorte) & b.modelo.eq(f"{pref}{familia}_clima_flujo")
                      & b.referencia.eq(f"{pref}{familia}_clima")].sort_values("anio_prueba")
            ax.errorbar(d.anio_prueba + (j - 1) * .13, d.diferencia_pp,
                        yerr=np.maximum(0, np.vstack([d.diferencia_pp - d.ic95_inf_pp,
                                                       d.ic95_sup_pp - d.diferencia_pp])),
                        fmt="o", capsize=3, color=color, label=familia)
        ax.axhline(0, color="#555", linewidth=1)
        ax.set(xticks=[2022, 2023, 2024], xlabel="Año de prueba", title=titulo,
               ylabel="Cambio de captura al agregar flujo (pp)")
        ax.grid(axis="y", alpha=.2); ax.legend(fontsize=8)
    fig.suptitle("Aporte incremental del flujo rezagado · IC 95 % por bloques semanales\n"
                 "Mismos tramos, eventos y presupuesto; selección y predicciones fijas", fontsize=11)
    fig.savefig(salida / "02_aporte_flujo.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5), layout="constrained")
    maximo = 0
    for familia, color in COLORES.items():
        d = cal.loc[cal.anio_prueba.eq(2024) & cal.cohorte.eq("ruta_completa") & cal.modelo.eq(f"{familia}_clima")]
        ax.plot(d.esperados, d.observados, "o-", color=color, label=familia)
        maximo = max(maximo, d[["esperados", "observados"]].max().max())
    ax.plot([0, maximo], [0, maximo], "--", color="#777", label="Calibración ideal")
    ax.set(xlabel="Siniestros esperados por decil", ylabel="Siniestros observados por decil",
           title="Calibración 2024 · modelos generales sin flujo\nDeciles de conteos esperados por tramo y día")
    ax.legend(); ax.grid(alpha=.2)
    fig.savefig(salida / "03_calibracion_2024.png", dpi=160); plt.close(fig)


def bloque(a, m, b, salida):
    candidato = a["modelo_candidato_por_cv_pre2024"]
    cohorte = "hibrido_ruta_completa" if candidato.startswith("Hibrido_") else "ruta_completa"
    metrica_candidato = m.loc[m.anio_prueba.eq(2024) & m.particion.eq("prueba")
                             & m.cohorte.eq(cohorte) & m.modelo.eq(candidato)].iloc[0]
    base = m.loc[m.anio_prueba.eq(2024) & m.particion.eq("prueba") & m.cohorte.eq("ruta_completa") & m.modelo.eq("M1")].iloc[0]
    general = m.loc[m.anio_prueba.eq(2024) & m.particion.eq("prueba") & m.cohorte.eq("ruta_completa")]
    t = pd.DataFrame({"Modelo": general.modelo, "Captura 5 %": general.captura5.map(lambda x: numero(x * 100) + " %"),
                      "Captura por turno": general.captura5_turno.map(lambda x: numero(x * 100) + " %"),
                      "Observado/esperado": general.observado_esperado.map(numero),
                      "MAE por turno": general.mae_12h_calendario.map(lambda x: numero(x, 4))})
    flujo = b.loc[b.cohorte.eq("con_contrato") & b.modelo.str.endswith("_clima_flujo")
                  & b.referencia.eq(b.modelo.str.replace("_clima_flujo", "_clima", regex=False))]
    tf = pd.DataFrame({"Año": flujo.anio_prueba, "Familia": flujo.modelo.str.replace("_clima_flujo", "", regex=False),
                       "Cambio de captura (pp)": flujo.diferencia_pp.map(numero),
                       "IC 95 % (pp)": [f"[{numero(l)}; {numero(h)}]" for l, h in zip(flujo.ic95_inf_pp, flujo.ic95_sup_pp)]})
    filas = []
    for f in COLORES:
        sin = m.loc[m.anio_prueba.eq(2024) & m.cohorte.eq("con_contrato") & m.particion.eq("prueba") & m.modelo.eq(f + "_clima")].iloc[0]
        con = m.loc[m.anio_prueba.eq(2024) & m.cohorte.eq("con_contrato") & m.particion.eq("prueba") & m.modelo.eq(f + "_clima_flujo")].iloc[0]
        filas.append([f, numero(sin.captura5 * 100) + " %", numero(con.captura5 * 100) + " %",
                      numero(sin.captura5_turno * 100) + " %", numero(con.captura5_turno * 100) + " %"])
    flujo2024 = tabla(pd.DataFrame(filas, columns=["Familia", "Sin flujo", "Con flujo", "Turno sin flujo", "Turno con flujo"]))
    filas_h = []
    for f in COLORES:
        valores = []
        for coh, nom in [("ruta_completa", f + "_clima"),
                         ("hibrido_ruta_completa", "Hibrido_" + f + "_clima"),
                         ("hibrido_ruta_completa", "Hibrido_" + f + "_clima_flujo")]:
            v = m.loc[m.anio_prueba.eq(2024) & m.cohorte.eq(coh) & m.modelo.eq(nom) & m.particion.eq("prueba")].iloc[0]
            valores.append(numero(v.captura5 * 100) + " %")
        filas_h.append([f] + valores)
    hibridos2024 = tabla(pd.DataFrame(filas_h, columns=["Familia", "General sin flujo", "Híbrido sin flujo", "Híbrido con flujo"]))
    brechas = m.loc[m.anio_prueba.eq(2024) & m.cohorte.eq("ruta_completa")
                    & ~m.modelo.isin(["M0", "M1"])].pivot(index="modelo", columns="particion", values="captura5")
    tb = pd.DataFrame({"Modelo": brechas.index,
                       "Captura train (2020–2023)": [numero(x * 100) + " %" for x in brechas.train],
                       "Captura prueba (2024)": [numero(x * 100) + " %" for x in brechas.prueba],
                       "Brecha (pp)": [numero(x * 100) for x in brechas.train - brechas.prueba]})
    cv = pd.DataFrame({"Solución": list(a["captura5_media_cv_ruta_completa"]),
                       "Promedio captura 2022/2023": [numero(x * 100) + " %" for x in a["captura5_media_cv_ruta_completa"].values()]})
    ci = b.loc[b.anio_prueba.eq(2024) & b.cohorte.eq(cohorte) & b.modelo.eq(candidato) & b.referencia.eq("M1")]
    ci_txt = ""
    if len(ci):
        r = ci.iloc[0]
        ci_txt = (f"Diferencia frente a M1: {numero(r.diferencia_pp)} pp, IC 95 % "
                  f"[{numero(r.ic95_inf_pp)}; {numero(r.ic95_sup_pp)}] pp.\n")
    reajuste = ""
    recal = ""
    if (salida / "reajuste.json").exists():
        r = json.loads((salida / "reajuste.json").read_text())
        reajuste = f"""Se reajustó `{r['modelo']}` con 2020–2024, conservando la elección y parámetros
anteriores a 2024. Su artefacto está en `resultados/modelos/artefactos/candidato_reajustado2020_2024.joblib`;
se verificaron {r['filas_comprobacion_persistencia']} predicciones reales idénticas al recargarlo.
Este reajuste no tiene evaluación futura y no sustituye el modelo del prototipo.
Se conserva además una variante recalibrada con el O/E fuera de muestra de 2024
en `candidato_reajustado2020_2024_recalibrado_con2024.joblib`; tampoco tiene evaluación futura.
"""
        rc = pd.read_csv(salida / "recalibracion_candidato.csv")
        trc = pd.DataFrame({"Año": rc.anio_prueba, "Variante": rc.ajuste,
                            "Año del factor": ["—" if pd.isna(x) else str(int(x)) for x in rc.anio_factor],
                            "Factor": rc.factor.map(lambda x: numero(x, 4)),
                            "Observado/esperado": rc.observado_esperado.map(numero),
                            "MAE por turno": rc.mae_12h_calendario.map(lambda x: numero(x, 4))})
        recal = f"""#### Recalibración de conteos con información previa

Para la candidata seleccionada se evalúa también multiplicar todos los conteos por el
cociente observado/esperado fuera de muestra del año anterior. Se mantiene fijo el
protocolo: 2023 usa el factor de 2022 y 2024 el de 2023. No se elige entre original y
recalibrado mirando el año objetivo. Un factor global positivo conserva el ranking,
la captura global y la captura por turno; sí cambia el volumen esperado y su MAE.

{tabla(trc)}

El ajuste puede mejorar o empeorar según el año; no demuestra estabilidad operativa.
Esta comparación es retrospectiva para la candidata elegida con 2022/2023, y la fila de
2023 forma parte del período usado para elegirla. Resultados completos en
[recalibracion_candidato.csv](resultados/modelos/recalibracion_candidato.csv).

"""
    return f"""{MARCAS[0]}
### Entrenamiento posterior al EDA: modelos con flujo vehicular

**Actualización: 12 de noviembre de 2026.** Se completó la comparación de Poisson,
Gradient Boosting y Random Forest con datos depurados, ERA5, calendario y proxy de
flujo DGC rezagado. El notebook y la presentación quedan para la etapa final.
La población de este experimento es **14.420 siniestros y 255 tramos**: se mantienen las
fuentes originales y se ponen en cuarentena las cinco discordancias espaciales del EDA.
Se usa un umbral de 25 km respecto de la referencia histórica; los umbrales de 5 y
10 km del EDA señalaban los mismos cinco registros. No se corrige su ubicación por
suposición. Los experimentos anteriores de 14.425
registros se conservan; sus puntuaciones no son comparaciones directas con esta corrida.

#### Incorporación del flujo y cambios de código

- [integrar_flujo.py](integrar_flujo.py) documenta intervalos interiores de seis contratos
  de Ruta 5, excluye baipases de kilometraje propio, fronteras inciertas y aplica margen
  de 1 km. Fuentes y páginas están en [limites_documentados.csv](resultados/modelos/limites_documentados.csv).
  Es una asignación de contexto por contrato; no acredita flujo uniforme por tramo.
- Se incorporan dos atributos: logaritmo del proxy diario de pasadas por punto de cobro
  y logaritmo del número implícito de puntos, ambos de **dos trimestres antes**.
  El segundo controla parcialmente cambios de composición; no verifica físicamente las plazas.
  Se normalizan a entero únicamente residuos ≤`1e-6` en puntos inferidos: el error
  máximo encontrado fue `7,3e-9`. Se conserva `puntos_implicitos_crudos` y cualquier
  fracción real. Así los árboles no aprenden cortes artificiales entre 4 y 4+`1e-9`.
  Se extraen también 2018–2019 de los XLS originales para tener rezagos reales desde 2020.
  Nunca se usa el flujo del trimestre a predecir ni se completan huecos con cero.
- Hay serie completa para **153/255 tramos (60 %)**; en 2024 contienen **1.491/2.605
  siniestros (57,24 %)**. Santiago–Talca/Acceso Sur, Chiloé y las celdas excluidas quedan
  fuera del experimento directo con flujo. El modelo híbrido usa un especialista en los
  tramos cubiertos y un modelo general sin flujo en los demás, con respaldo si falta el dato.
- PNCV continúa separado: sus estaciones parciales, ceros sin interpretar y falta de año
  2020 no se convierten en una exposición completa. `exposicion_validada.csv` permanece
  vacía. **Se modelan conteos; no se estima riesgo por vehículo-km.**
- [datos_modelado.py](datos_modelado.py) alinea las fuentes, mantiene la referencia espacial
  de 2020–2021, verifica las celdas del caché ERA5 tras la cuarentena y conserva exposición
  horaria 0/1/2 por horario de verano. La agrupación conserva conteos y exposición.
- [modelos_conteo.py](modelos_conteo.py) implementa las tres familias con pérdida/criterio
  Poisson. La regresión incluye offset horario y penalización L2; GB usa categorías nativas;
  RF usa categorías codificadas, 80 árboles y un máximo de 80.000 filas agrupadas por árbol.
  GB/RF ajustan tasa con peso igual a exposición y luego recuperan el conteo esperado.
  Sus tamaños de hoja y muestreo operan sobre filas agrupadas, no sobre horas individuales.
  Se aplica un piso de tasa de `1e-12` para calcular desvianza finita en hojas con cero.

#### Protocolo temporal y selección

Se comparan M0 uniforme, M1 espacial y las familias propuestas. En la cohorte de flujo,
cada familia tiene calendario → calendario+lluvia → calendario+lluvia+flujo sobre las
mismas filas. Incluyen tramo, hora, día de semana, mes, posición de feriado y tendencia
numérica anual; las variantes agregan lluvia y flujo. Las transformaciones se ajustan
solo con entrenamiento. No se usa una categoría de año futuro sin aprender.

1. Prueba 2022: entrenamiento 2020–2021, configuración simple prefijada.
2. Prueba 2023: entrenamiento 2020–2022, configuración elegida con 2022.
3. Prueba 2024: entrenamiento 2020–2023, configuración elegida con 2022 y 2023.

Se evalúan dos configuraciones por familia en los años previos, con preferencia por la
más simple a ≤0,1 puntos de captura del mejor promedio. La elección entre soluciones
para toda la ruta también usa exclusivamente las puntuaciones de 2022/2023.
**Candidata resultante: `{candidato}`**. La grilla, parámetros elegidos, años usados,
diagnósticos, versiones y hashes están en [auditoria.json](resultados/modelos/auditoria.json).

{tabla(cv)}

2024 ya se había inspeccionado en las entregas y el EDA: se informa como evaluación
histórica reutilizada, no como prueba intacta. Los intervalos usan 2.000 remuestreos
semanales pareados, manteniendo fijas predicciones y selección; no incorporan incertidumbre
del reentrenamiento ni corrigen comparaciones múltiples.

#### Resultados: ruta completa, prueba histórica de 2024

{tabla(t)}

La candidata `{candidato}` captura **{numero(metrica_candidato.captura5 * 100)} %** de
los siniestros con el 5 % del presupuesto global, frente a **{numero(base.captura5 * 100)} %**
de M1. Su captura con patrullaje fijo por turno es **{numero(metrica_candidato.captura5_turno * 100)} %**.
Son decisiones distintas: la priorización global permite cambiar tramo cada hora;
la métrica por turno fija los tramos durante 12 horas de reloj local. Observado/esperado
cercano a 1 indica mejor calibración agregada; no garantiza calibración por segmento.
El MAE compara el total de siniestros de la cohorte por turno de 12 horas.
Las métricas train/prueba, captura al 5/10/20 %, desvianza y MAE se conservan completas en
[metricas.csv](resultados/modelos/metricas.csv).
{ci_txt}

Comparación train/prueba con la misma definición de captura:

{tabla(tb)}

La brecha es un diagnóstico de generalización, no una prueba aislada de sobreajuste:
también cambian las frecuencias entre años. La elección se basa en evaluación temporal,
no en la captura obtenida durante el entrenamiento.

![Captura temporal](resultados/modelos/01_captura_temporal.png)

#### Aporte específico del flujo

Comparación 2024 sobre los mismos 153 tramos cubiertos (captura global y por turno al 5 %):

{flujo2024}

La integración en toda la ruta tiene su propia comparación (255 tramos, captura al 5 %):

{hibridos2024}

El híbrido sin flujo controla el efecto de entrenar un especialista en la cohorte
cubierta. Una mejora dentro de los 153 tramos no garantiza una mejora del ranking
entre todos los tramos; también interviene la escala relativa de sus predicciones.

Diferencia **clima+flujo menos clima**, sin confundirla con el aporte de la lluvia:

{tabla(tf)}

Un intervalo que incluye cero no permite sostener una mejora clara en ese año.
No se da por útil el flujo solo por haberlo añadido; también puede reducir la captura.
Las comparaciones equivalentes para el híbrido de toda la ruta y contra M1 se guardan
en [bootstrap.csv](resultados/modelos/bootstrap.csv).

![Aporte incremental del flujo](resultados/modelos/02_aporte_flujo.png)
![Calibración](resultados/modelos/03_calibracion_2024.png)

{recal}
#### Artefactos, reproducción y límites pendientes

Se guardaron modelos por año, cohorte y variante en `resultados/modelos/artefactos/`
(archivos locales ignorados por Git). Los evaluados en 2024 solo se ajustaron hasta 2023.
{reajuste}
Con las fuentes descargadas, ejecutar desde la raíz del repositorio:

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python entrenar_comparacion.py
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python reajustar_candidato.py
MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python resumir_modelos.py --actualizar-readme
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python -m unittest discover -s tests -v
```

**Comprobación: 33 pruebas pasaron.** Incluyen captura con empates y presupuesto,
UTC/DST, calendario fuera de cobertura, calidad de fuentes, fronteras de contratos,
rezago temporal, selección sin usar el año de prueba y persistencia de las tres familias.
La prueba nueva comprueba que se eliminan residuos numéricos de puntos de cobro sin
redondear fracciones reales. Se repitieron las variantes de flujo después de esta
corrección con [reentrenar_flujo.py](reentrenar_flujo.py), verificando hashes antes de
conservar los ajustes sin flujo. La corrida completa desde cero ya incluye el arreglo.

Siguen abiertas la validación con pronósticos meteorológicos emitidos en el pasado,
la fecha real de disponibilidad de los anexos DGC y la exposición vehicular por tramo.
El rezago de dos trimestres deja un trimestre completo desde el cierre de medición,
pero no acredita cuándo se publicó cada dato; los anexos actuales pueden contener revisiones.
Estos modelos respaldan una evaluación retrospectiva de conteos, no un servicio operativo
validado ni una interpretación causal del flujo. El calendario y las fuentes deben
actualizarse antes de una predicción fuera de 2020–2024.

La bitácora del EDA que sigue conserva las decisiones y pendientes de esa etapa.
Esta sección documenta su tratamiento posterior. No se modificaron notebook ni presentación.
{MARCAS[1]}
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=Path("resultados/modelos"))
    p.add_argument("--actualizar-readme", action="store_true")
    args = p.parse_args()
    a = json.loads((args.salida / "auditoria.json").read_text())
    m, b, cal = (pd.read_csv(args.salida / n) for n in ["metricas.csv", "bootstrap.csv", "calibracion.csv"])
    figuras(m, b, cal, args.salida)
    texto = bloque(a, m, b, args.salida)
    resumen_local = texto.replace("](resultados/modelos/", "](")
    for n in ["integrar_flujo.py", "datos_modelado.py", "modelos_conteo.py", "reentrenar_flujo.py"]:
        resumen_local = resumen_local.replace(f"]({n})", f"](../../{n})")
    (args.salida / "resumen.md").write_text(resumen_local)
    if args.actualizar_readme:
        archivo = Path("README.md"); actual = archivo.read_text()
        if MARCAS[0] in actual:
            ini, resto = actual.split(MARCAS[0], 1)
            _, fin = resto.split(MARCAS[1], 1)
            nuevo = ini + texto.rstrip() + fin
        else:
            punto = "## Desarrollo de la Entrega 3\n"
            if punto not in actual:
                raise ValueError("No se encontró la sección de desarrollo del README")
            nuevo = actual.replace(punto, punto + "\n" + texto + "\n", 1)
        archivo.write_text(nuevo)
    print("Figuras, resumen y bitácora generados en", args.salida)


if __name__ == "__main__":
    main()
