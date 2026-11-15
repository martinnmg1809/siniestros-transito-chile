"""Construye el notebook final documentado sin descargar, entrenar ni ejecutarlo."""
import argparse
from pathlib import Path
import nbformat as nbf
from proyecto import RAIZ


def construir():
    celdas = []

    def md(texto):
        celdas.append(nbf.v4.new_markdown_cell(texto.strip()))

    def code(texto):
        celdas.append(nbf.v4.new_code_cell(texto.strip()))

    md(r'''
# Predicción dinámica de siniestros en carreteras chilenas
## Entrega III · Notebook técnico final

**Caso validado:** Ruta 5 Sur · 2020–2024 · tramos de 5 km y resolución horaria.

**Equipo:** Diego, Vicente, Martín, Cristóbal y Máximo. Integración técnica: Diego;
datos y flujo: Vicente; selección e interpretación del modelo: Martín;
evaluación comparativa: Cristóbal; presentación: Máximo. El historial del repositorio
conserva las contribuciones y la asistencia de Codex/Claude declarada en ellas.
La redacción de cierre de las fichas 02/04 se completó por encargo de Diego con Codex.

**Base científica integrada:** `5d80f40`. Este documento consolida las correcciones,
los modelos, su validación y la interpretación. La evaluación es **retrospectiva**;
2024 ya se exploró en etapas anteriores y se declara evaluación histórica reutilizada.

> Resultado principal: Poisson_clima fue seleccionado con 2022/2023 y una regla de
> sencillez fijada. La integración del proxy vehicular se evaluó y no mostró una
> mejora consistente. El piloto de 12 horas tiene una emisión experimental; todavía
> carece de evaluación con observaciones completas.
''')
    md('''
## Contenido y relación con la rúbrica

| Sección | Evidencia para la entrega |
|---|---|
| 1–3 | Problema, ejecución reproducible, fuentes y calidad del dato |
| 4–6 | EDA, calendario/clima, incorporación y límites del flujo |
| 7–9 | Iteraciones, modelos, particiones y selección final |
| 10–12 | Comparación, generalización, lluvia/flujo y calibración |
| 13–14 | Interpretación y reproducción de predicciones del modelo |
| 15–16 | Sensibilidades e investigación de ampliación a 2025 |
| 17 | Piloto de las siguientes 12 horas y límites de su evaluación |
| 18–19 | Reproducción del entrenamiento, conclusiones y trazabilidad |

Ejecutar de arriba abajo con **Reiniciar kernel y ejecutar todo**. Las celdas muestran
las cifras desde sus archivos de evidencia y verifican relaciones clave.
''')
    md('''
## 1. Problema y objetivo

Los mapas de concentración histórica no describen cómo cambia la frecuencia de
siniestros según la hora, el calendario y la lluvia. El proyecto estima **conteos
esperados por tramo y hora** para apoyar la priorización de vigilancia y el análisis
de cuántos eventos esperar en un turno.

La decisión estudiada destina una fracción limitada de las horas-tramo a vigilancia.
Se distinguen un ranking global y un plan con tramos fijos durante cada turno de
12 horas. La captura mide concentración retrospectiva; no mide siniestros evitados.
Sin exposición vehicular acreditada no se estima riesgo por conductor o vehículo-km.
El nombre general del proyecto no extiende la validación a todas las carreteras.
''')
    md('''
## 2. Preparación y niveles de reproducción

Este notebook requiere el repositorio completo: el `.ipynb` es el relato ejecutable
y los módulos de `codigo/` contienen la implementación. Instalar el entorno del
proyecto y `requirements-notebook.txt` según `notebooks/README.md`.

**Con archivos de Git:** se reproducen limpieza, EDA del histórico, cobertura del
proxy, selección, comparaciones y lectura de auditorías. **Con fuentes y joblib
originales locales:** se reconstruyen además predicciones, métricas e intervalos
seleccionados. El notebook anuncia qué nivel está disponible; un insumo presente
con hash incorrecto provoca error.

La ejecución ordinaria no descarga datos ni reentrena. La sección 18 permite
solicitar explícitamente otra corrida en una carpeta nueva. Los resultados anteriores
no se sustituyen por una ejecución de este documento.
''')
    code('''
from pathlib import Path
import os, sys, json, hashlib, platform, subprocess, importlib.metadata as metadata

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/siniestros-matplotlib")
candidatos_raiz = [Path.cwd(), *Path.cwd().parents]
RAIZ = next((p for p in candidatos_raiz
             if (p / "proyecto.py").is_file()
             and (p / "config/migracion_estructura.csv").is_file()), None)
if RAIZ is None:
    raise RuntimeError("Abrir el notebook dentro del repositorio completo.")
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)
import proyecto
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from IPython.display import display, Markdown, Image, JSON
from io import BytesIO
from threadpoolctl import threadpool_limits

pd.set_option("display.max_columns", 16)
pd.set_option("display.max_rows", 25)
EVIDENCIA = {}

def registrar(nombre):
    p = RAIZ / nombre
    EVIDENCIA[nombre] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p

def csv(nombre):
    return pd.read_csv(registrar(nombre))

def leer_json(nombre):
    return json.loads(registrar(nombre).read_text())

def figura(nombre):
    display(Image(filename=str(registrar(nombre)), width=1000))

def mostrar_figura(fig):
    imagen = BytesIO()
    fig.savefig(imagen, format="png", dpi=130, bbox_inches="tight")
    display(Image(data=imagen.getvalue()))
    plt.close(fig)

versiones = {n: metadata.version(n) for n in
             ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "joblib", "nbformat", "ipykernel"]}
display(pd.Series(versiones, name="Versión ejecutada").to_frame())
print("Python:", platform.python_version())
''')
    code('''
from verificar_cierre import verificar_tablas
mensajes, auditoria, reajuste, tablas = verificar_tablas(RAIZ)
for mensaje in mensajes:
    print("✓", mensaje)
for nombre in ["resultados/modelos/auditoria.json", "resultados/modelos/reajuste.json",
               "config/migracion_estructura.csv"]:
    registrar(nombre)
metricas = csv("resultados/modelos/metricas.csv")
bootstrap = csv("resultados/modelos/bootstrap.csv")
seleccion = csv("resultados/modelos/seleccion_temporal.csv")
busqueda = csv("resultados/modelos/busqueda_temporal.csv")
assert auditoria["modelo_candidato_por_cv_pre2024"] == "Poisson_clima"
print("Candidata registrada:", auditoria["modelo_candidato_por_cv_pre2024"])
''')
    md('''
## 3. Fuentes, población y correcciones

| Fuente | Granularidad | Uso y límite |
|---|---|---|
| CONASET, histórico versionado | Evento con fecha/hora, ruta, km y coordenadas | Objetivo de conteo; hora aproximada y cobertura no equivalente a exhaustividad |
| ERA5 vía Open-Meteo | Precipitación horaria por celda | Reanálisis histórico; no es un pronóstico emitido antes de decidir |
| Calendario histórico del equipo | Fecha y posición de período festivo | Cobertura 2020–2024; no extrapolar a un año nuevo |
| Anexos DGC 2023T4/2024T4 | Contrato y trimestre, series históricas | Proxy de circulación, sin exposición vehicular ni publicación histórica acreditada |
| PNCV MOP | Estación/rama y año medido | EDA de posible exposición; no admitido como denominador |

Las URL, unidades y hashes se conservan en los manifiestos del repositorio y en la
ficha de datos. Se preservan originales y versiones; no se suman revisiones.
La siguiente celda reconstruye la población a partir del CSV versionado.
''')
    code('''
from datos_ruta5 import cargar_eventos, referencia_entrenamiento, grilla_civil, exposicion_civil
from datos_modelado import cuarentena_espacial

crudos = csv("data/siniestros/ruta5_2020_2024.csv.gz")
antes_km = crudos.loc[crudos.Ruta.eq("RUTA 5 SUR")].copy()
eventos_km, auditoria_fuente = cargar_eventos()
eventos, cuarentena = cuarentena_espacial(eventos_km)
referencia = referencia_entrenamiento(eventos)
assert auditoria_fuente["sha256"] == auditoria["datos"]["fuente_siniestros"]["sha256"]
assert len(eventos) == auditoria["datos"]["registros_modelado"] == 14420
assert len(referencia) == 255
assert set(cuarentena.ID.astype(int)) == set(auditoria["datos"]["ids_cuarentena"])
display(pd.DataFrame({"Etapa": ["Ruta 5 Sur original", "Km válido", "Tras cuarentena espacial"],
                      "Eventos": [len(antes_km), len(eventos_km), len(eventos)]}))
display(cuarentena[["ID", "anio", "km", "tramo", "distancia_referencia_km", "motivo"]].round(2))
''')
    md('''
Se pasa de **14.430** eventos a **14.425** por cinco kilómetros inválidos y luego a
**14.420** por cinco discordancias entre km y coordenadas. La cuarentena usa 25 km
respecto de la referencia aproximada; los diagnósticos de 5 y 10 km señalaban los
mismos cinco casos. No se imputó su ubicación. El EDA anterior a la cuarentena usa
14.425: sus agregados se identifican como diagnóstico previo, no como población final.
La referencia espacial se construye con 2020–2021, sin ampliar dominio con años de prueba.
''')
    code('''
campos = ["ID", "FECHA", "Hora_aprox", "Ruta", "Ubicación", "Latitud", "longitud"]
calidad = pd.DataFrame({"faltantes": eventos[campos].isna().sum()})
assert calidad.faltantes.sum() == 0
assert eventos.ID.is_unique
assert eventos.hora.between(0, 23).all()
lesiones = eventos[["GRAVES", "MENOS_GRAV", "LEVES"]].sum(axis=1)
assert (eventos.TOTAL_LESI == lesiones).all()
display(calidad)
print("IDs duplicados:", eventos.ID.duplicated().sum())
print("Lesionados coherentes con su desglose:", bool((eventos.TOTAL_LESI == lesiones).all()))
''')
    md('''
## 4. EDA del histórico limpio

Se observan conteos por año, hora y tramo antes de interpretar modelos. La
concentración espacial justifica una referencia como M1; el patrón horario por sí
solo no separa exposición al tráfico de peligrosidad por conductor. Los extremos
se conservan salvo evidencia de error. Tener campos completos no demuestra ausencia
de subregistro ni precisión física de las coordenadas.
''')
    code('''
anuales = eventos.groupby("anio").size().rename("siniestros")
assert anuales.to_dict() == {2020: 2295, 2021: 3288, 2022: 3369, 2023: 2863, 2024: 2605}
display(anuales.to_frame())
fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
anuales.plot.bar(ax=axes[0], color="#267a91", rot=0)
eventos.groupby("hora").size().reindex(range(24), fill_value=0).plot(ax=axes[1], marker="o", color="#267a91")
eventos.groupby("tramo").size().reindex(referencia.tramo, fill_value=0).plot(ax=axes[2], color="#d28828")
for ax, titulo in zip(axes, ["Conteos anuales", "Hora aproximada", "Concentración por tramo"]):
    ax.set_title(titulo); ax.set_ylabel("Siniestros")
axes[2].set_xlabel("Km inicial del tramo")
mostrar_figura(fig)
''')
    code('''
tiempo, y_limpio, fuera = grilla_civil(eventos, referencia.tramo.to_numpy())
exposicion = exposicion_civil(tiempo)
validas = exposicion > 0
assert fuera == 0 and y_limpio[:, ~validas].sum() == 0
assert y_limpio.sum() == len(eventos)
display(pd.Series({"Tramos": len(referencia), "Etiquetas civiles": len(tiempo),
    "Horas inexistentes DST": int((exposicion == 0).sum()),
    "Horas repetidas DST": int((exposicion == 2).sum()),
    "% celdas existentes sin siniestros": 100 * (y_limpio[:, validas] == 0).mean()},
    name="Diagnóstico final").to_frame())
''')
    md(r'''
## 5. Calendario, precipitación y horario de verano

La grilla tiene 24 etiquetas civiles por día. Se conserva una exposición horaria
$e_t\in\{0,1,2\}$: cero en una hora inexistente y dos en una repetida por DST.
CONASET no distingue cuál repetición de la hora corresponde al evento. La
precipitación promediada durante la hora repetida es una aproximación documentada.
Los NaN estructurales de horas inexistentes no se interpretan como observaciones secas.

Los cortes implementados son **seco $p<0,1$; llovizna $0,1\le p<0,5$; lluvia
$p\ge0,5$ mm/h**. Hay 59 celdas meteorológicas para 255 tramos: compartir una celda
no crea mediciones meteorológicas independientes. La sensibilidad a los cortes se
presenta en la sección 15.
''')
    code('''
clima_descriptivo = csv("resultados/eda/clima_distribucion_tramo_hora.csv")
display(clima_descriptivo[["unidad", "filas", "faltantes", "ceros", "positivos", "max"]])
print("La distribución climática publicada es el diagnóstico de EDA previo; la comprobación local reconstruye el conjunto final.")
figura("resultados/eda/06_clima_y_conteos.png")
''')
    md('''
## 6. Incorporación del flujo vehicular y descarte de exposición no validada

Se evaluó PNCV antes de integrarlo: falta el año medido 2020, hay ceros sin
interpretar y no se acredita correspondencia rama–tramo ni disponibilidad histórica.
Por ello `exposicion_validada.csv` permanece sin filas.

DGC permite construir un **proxy**: promedio mensual por punto × 3 / días del
trimestre, en pasadas por punto de cobro y día. Se usan `log(proxy)` y `log(puntos
implícitos)` del trimestre objetivo menos dos. Los puntos se infieren algebraicamente;
no son un censo físico de plazas. Todos los tramos de un contrato comparten valor.
Un vehículo puede generar varias pasadas y el proxy no es vehículo-km.
''')
    code('''
display(csv("resultados/eda/mop_capas_y_anios.csv")[["capa", "titulo", "anios_observados", "tmda_cero", "tmda_faltante"]])
display(csv("resultados/eda/mop_cruce_rol_tmda.csv"))
assert csv("resultados/flujo/exposicion_validada.csv").empty
cobertura = csv("resultados/modelos/cobertura_flujo.csv")
display(cobertura)
assert cobertura.tramos_con_flujo.eq(153).all()
''')
    code('''
# Se comprueban directamente las invariantes sin regenerar la tabla publicada.
flujo = csv("resultados/modelos/flujo_rezagado.csv")
assert len(flujo) == 255 * 20
assert (pd.PeriodIndex(flujo.periodo_objetivo, freq="Q") - 2 ==
        pd.PeriodIndex(flujo.periodo_medicion, freq="Q")).all()
assert (pd.to_datetime(flujo.fin_medicion) < pd.to_datetime(flujo.inicio_objetivo)).all()
assert flujo.loc[~flujo.flujo_disponible, ["proxy_pasadas_por_punto_dia", "puntos_implicitos"]].isna().all().all()
assert not flujo.disponibilidad_publicacion_acreditada.any()
display(pd.Series({"Filas tramo-trimestre": len(flujo),
    "Con flujo": int(flujo.flujo_disponible.sum()),
    "Sin flujo": int((~flujo.flujo_disponible).sum()),
    "Días mínimos desde cierre medido": int(flujo.dias_desde_cierre.min())}).to_frame("Valor"))
''')
    md('''
La cobertura es **153/255 tramos** (60 %), con 1.491 de 2.605 eventos en 2024.
Los otros 102 tramos quedan fuera de la comparación directa con flujo; el híbrido
usa respaldo sin flujo. Se excluye Santiago–Talca porque su fila agrega Acceso Sur
sin separación, además de fronteras, baipases y sectores sin contrato utilizable.
El rezago prueba separación de períodos medidos; **no acredita publicación a tiempo**.
Las fechas en la URL del anexo no prueban primera disponibilidad.
''')
    md('''
## 7. Iteraciones respecto de la entrega anterior

Se corrigieron la captura con empates y presupuesto, la cuarentena espacial,
la alineación UTC/DST, la selección temporal y el tratamiento de faltantes. Se
compararon tres familias y variantes con y sin flujo en cohortes equivalentes.
Posteriormente se añadieron calibración, contrastes, sensibilidades y el piloto.
La matriz distingue cambios realizados, límites y compromisos no cumplidos;
completar una ficha no convierte una limitación científica en un resultado validado.
''')
    code('''
compromisos = csv("resultados/cierre/matriz_compromisos.csv")
display(compromisos[["id", "compromiso_u_observacion", "estado", "pendiente_concreto"]])
''')
    md(r'''
## 8. Modelos y validación temporal

- **M0:** tasa uniforme; **M1:** referencia espacial por tramo.
- **Poisson:** modelo log-lineal de conteos con penalización L2 y exposición horaria.
- **Gradient Boosting:** pérdida Poisson y categorías nativas.
- **Random Forest:** criterio Poisson, 80 árboles y muestreo sobre filas agrupadas.

En Poisson, $Y_{s,t}\sim\mathrm{Poisson}(e_t\lambda_{s,t})$ y
$\log\lambda_{s,t}=\beta_0+f(\mathrm{tramo,hora,día,mes,feriado,lluvia})+
\beta_a(\mathrm{año}-2020)$. Los efectos son aditivos, sin interacciones.
El offset $e_t$ representa horas reales, no exposición de vehículos.

En la ruta completa se comparan los modelos de clima con M0/M1. En los 153 tramos
cubiertos se compara calendario → clima → clima+flujo con los mismos eventos.
El híbrido tiene otro universo de entrenamiento; se compara por separado.
Las transformaciones se aprenden en entrenamiento. Se usa una ventana expansiva:
''')
    code('''
folds = pd.DataFrame({"Prueba": [2022, 2023, 2024],
    "Entrenamiento": ["2020–2021", "2020–2022", "2020–2023"],
    "Años para elegir hiperparámetros": ["Ninguno: configuración simple prefijada", "2022", "2022 y 2023"]})
display(folds)
from modelos_conteo import GRILLAS
display(pd.DataFrame([{"Familia": fam, "Configuración": i, "Parámetros": json.dumps(p)}
                      for fam, opciones in GRILLAS.items() for i, p in enumerate(opciones)]))
display(seleccion[(seleccion.cohorte == "ruta_completa") & (seleccion.familia == "Poisson")])
''')
    md('''
## 9. Selección final: evidencia anterior a 2024

El criterio principal es captura global al 5 % media en 2022/2023. Entre soluciones
a ≤0,1 puntos porcentuales de la mejor se prefiere sencillez en el orden registrado:
M1, Poisson, GB, RF e híbridos. La regla se reproduce abajo, sin utilizar 2024.
La configuración L2=3 fue la vigente en las pruebas 2022/2023; el artefacto evaluado
2024 usa L2=0,3, elegida con los años anteriores. Seleccionar la familia y su
configuración temporal son decisiones relacionadas pero distintas.
''')
    code('''
cv = metricas[(metricas.anio_prueba < 2024) & metricas.particion.eq("prueba") &
              metricas.cohorte.ne("con_contrato") & metricas.modelo.ne("M0")]
medias = cv.groupby("modelo").captura5.mean()
tolerancia = auditoria["tolerancia_simplicidad_pp"] / 100
familias = list(auditoria["grillas"])
preferencia = (["M1"] + [f"{f}_clima" for f in familias] +
              [f"Hibrido_{f}_{v}" for v in ["clima", "clima_flujo"] for f in familias])
candidata = next(n for n in preferencia if medias[n] >= medias.max() - tolerancia)
assert candidata == auditoria["modelo_candidato_por_cv_pre2024"] == "Poisson_clima"
seleccion_final = pd.DataFrame({"captura_media_pct": medias * 100,
    "distancia_mejor_pp": (medias.max() - medias) * 100,
    "equivalente": medias >= medias.max() - tolerancia}).sort_values("captura_media_pct", ascending=False)
display(seleccion_final.round(4))
print("Modelo seleccionado:", candidata)
''')
    md('''
GB obtiene **19,114 %** y Poisson **19,089 %**, una distancia de 0,025 puntos,
dentro de la tolerancia. Se selecciona Poisson_clima por la regla prefijada.
Su estructura y cobertura sin flujo facilitan la interpretación. GB puede obtener
mejores resultados en 2024 sin que corresponda reseleccionar con ese año.
''')
    md('''
## 10. Métricas, comparación y generalización

| Métrica | Lectura y unidad |
|---|---|
| Captura al 5/10/20 % | Fracción de siniestros concentrada con ese presupuesto de horas-tramo |
| Captura por turno | Misma ubicación durante 12 horas de reloj local, presupuesto por turno |
| O/E | Total observado / total esperado; menor que 1 implica sobreestimación agregada |
| MAE por turno | Error absoluto medio del **total de la cohorte** por turno, en siniestros |
| Desvianza por hora | Pérdida de conteos normalizada por exposición; comparar dentro del mismo universo |

La selección fraccionaria en empates representa priorización uniforme dentro del
empate y conserva el presupuesto. No se usan observaciones para desempatar.
La captura no es accuracy ni probabilidad de accidente. O/E agregado cercano a 1
no garantiza calibración por tramo. La precisión se muestra sin mezclar cohortes.
''')
    code('''
prueba_ruta = metricas[metricas.cohorte.eq("ruta_completa") & metricas.particion.eq("prueba")]
columnas_metricas = ["modelo", "siniestros", "captura5", "captura5_turno", "observado_esperado", "mae_12h_calendario", "desvianza_por_hora"]
comparacion2024 = prueba_ruta.loc[prueba_ruta.anio_prueba.eq(2024), columnas_metricas].copy()
comparacion2024[["captura5", "captura5_turno"]] *= 100
comparacion2024 = comparacion2024.rename(columns={"captura5": "captura5_pct", "captura5_turno": "captura5_turno_pct"})
display(comparacion2024.round(4))
figura("resultados/modelos/01_captura_temporal.png")
''')
    md('''
En 2024 Poisson captura **19,00 %** global frente a **14,89 %** de M1. Con tramos
fijos por turno, captura **15,84 %**: la mejora respecto de M1 es menor que en la
selección global. GB alcanza 20,00 % y 17,26 %, respectivamente. Poisson original
sobreestima el total (O/E 0,772) y tiene MAE de 1,970 siniestros por turno en toda
la ruta. Las cifras favorables de ranking no resuelven la escala de conteos.
''')
    code('''
generalizacion = csv("resultados/cierre/generalizacion.csv")
display(generalizacion[generalizacion.cohorte.eq("ruta_completa")][
    ["anio_prueba", "modelo", "captura5_train", "captura5_prueba", "brecha_train_prueba_pp"]].round(4))
figura("resultados/cierre/fig_train_prueba.png")
ventaja = bootstrap[bootstrap.cohorte.eq("ruta_completa") & bootstrap.modelo.eq("Poisson_clima") & bootstrap.referencia.eq("M1")]
display(ventaja[["anio_prueba", "diferencia_pp", "ic95_inf_pp", "ic95_sup_pp", "replicas_validas"]].round(3))
''')
    md('''
La brecha media train–prueba de captura es aproximadamente 3,93 pp en Poisson y
8,91 pp en GB. Describe pérdida fuera del entrenamiento; por sí sola no distingue
sobreajuste de cambios de frecuencia entre años. Los IC usan 2.000 remuestreos
semanales pareados con predicciones y selección fijas. No incluyen incertidumbre
del reentrenamiento ni corrigen múltiples comparaciones. Tres años de prueba
histórica no acreditan desempeño operativo futuro.
''')
    md('''
## 11. Aporte específico de lluvia y del proxy de circulación

Lluvia se contrasta como **clima menos calendario**; flujo como **clima+flujo menos
clima**. Ambos contrastes se hacen sobre los mismos 153 tramos cubiertos. No se
compara un modelo de 153 tramos con otro de 255 como si tuvieran la misma población.
''')
    code('''
aportes = csv("resultados/cierre/aporte_lluvia_flujo.csv")
assert aportes.n_tramos.eq(153).all()
display(aportes[["aporte", "familia", "anio_prueba", "diferencia_captura5_pp", "ic95_inf_pp", "ic95_sup_pp", "ic_incluye_cero"]])
figura("resultados/modelos/02_aporte_flujo.png")
''')
    md('''
La lluvia tiene incrementos puntuales positivos en Poisson, con intervalos que
incluyen cero en los tres años. En GB 2023, el incremento por lluvia es 3,361 pp
[1,352; 5,520]. El proxy de flujo solo muestra un intervalo positivo en GB 2022;
el signo puntual cambia en 2024. **No hay mejora consistente del proxy** a esta
resolución. Esto no demuestra que el tráfico real no importe. Un IC que incluye
cero tampoco prueba igualdad ni ausencia de asociación.
''')
    md('''
## 12. Calibración: separar orden y cantidad

Un factor global positivo conserva el ranking; corrige la escala de conteos.
La variante de prueba usa el O/E fuera de muestra del año anterior: 2023 con 2022,
2024 con 2023. El factor de 2023 proviene del modelo L2=3 y se aplica al de 2024
L2=0,3; no usa resultados del año objetivo, pero tampoco es exactamente el mismo ajuste.
''')
    code('''
recalibracion = csv("resultados/modelos/recalibracion_candidato.csv")
display(recalibracion[["anio_prueba", "ajuste", "anio_factor", "factor", "observado_esperado", "mae_12h_calendario", "captura5"]].round(5))
for anio in [2023, 2024]:
    d = recalibracion[recalibracion.anio_prueba.eq(anio)].set_index("ajuste")
    assert d.loc["recalibrado", "anio_factor"] == anio - 1
    np.testing.assert_allclose(d.loc["original", "captura5"], d.loc["recalibrado", "captura5"])
figura("resultados/cierre/fig_calibracion.png")
''')
    md('''
En 2024 la recalibración reduce MAE de **1,970 a 1,684**, pero pasa de O/E 0,772
a **1,154**: de sobreestimar a subestimar el total. No se presenta la calibración
como resuelta. La captura sigue en 19,00 %. No se ha comparado aquí con un M1
recalibrado mediante el mismo procedimiento.

El término anual del modelo evaluado es aproximadamente ×1,054/año. El diagnóstico
agregado de tendencia reproduce de cerca el O/E, lo que respalda una explicación por
extrapolación temporal; no aísla causalmente todos los factores del sesgo.
''')
    code('''
tendencia = csv("resultados/cierre/martin_originales/tendencia_anual.csv")
display(tendencia[tendencia.modelo_registrado.eq("Poisson_clima")][
    ["anio_prueba", "anios_entrenamiento", "razon_por_anio_tendencia", "oe_solo_tendencia", "oe_registrado"]].round(4))
audit_originales = leer_json("resultados/cierre/martin_originales/auditoria.json")
versiones_modelo = audit_originales["versiones_originales"]
display(pd.DataFrame([{"Versión": k, "Origen": versiones_modelo[k]["origen"],
    "Factor anual": versiones_modelo[k]["razon_tasa_por_anio_tendencia"],
    "SHA256 joblib": versiones_modelo[k]["sha256_archivo"]}
    for k in ["evaluado2024", "reajustado2020_2024"]]))
''')
    md('''
El evaluado de 2024 se ajustó hasta 2023; su desempeño se puede medir en 2024.
El reajustado con 2020–2024 incorpora todos los eventos y **no tiene prueba futura**.
Su tendencia es aproximadamente ×1,002/año; aplicar el factor 0,772 del modelo
evaluado no acredita calibración del reajustado. Se mantiene su variante original
como principal y la recalibrada como referencia separada en el piloto.
''')
    md('''
## 13. Interpretación del modelo y ejemplo de turno

Los contrastes usan pares de combinaciones observadas que difieren solo en lluvia,
hora o posición festiva. En un modelo log-lineal aditivo sin interacciones, las
razones de tasas son constantes para esos pares. Son asociaciones predictivas;
no identifican efecto causal ni riesgo individual. La circulación no observada
puede contribuir a las asociaciones de hora y calendario.

Se conserva el reajuste independiente de Martín y se distingue la comprobación con
joblib originales. Aquí se utiliza la salida de los **artefactos originales**.
''')
    code('''
contrastes = csv("resultados/cierre/martin_originales/contrastes_poisson.csv")
foco = contrastes.version.eq("evaluado2024") & (contrastes.contraste.isin(["lluvia", "feriado"]) |
       (contrastes.contraste.eq("hora") & contrastes.comparado.isin(["02:00", "08:00", "18:00"])))
display(contrastes.loc[foco, ["contraste", "referencia", "comparado", "pares", "razon_mediana"]].round(4))
turno = csv("resultados/cierre/martin_originales/ejemplo_turno_poisson.csv")
display(turno[["turno_inicio", "tramo_km", "rango", "peso_presupuesto_5pct", "esperado_original", "esperado_recalibrado", "observado"]].round(4))
''')
    md('''
La razón lluvia/seco es aproximadamente **2,11**; llovizna/seco, **1,28**. A las
18:00 es ×1,41 frente a las 12:00. No tienen intervalos de confianza y no se
reutilizan los del prototipo antiguo.

El turno ilustrativo se fijó para el 12/07/2024 12:00–24:00. El total de la ruta es
**6,344 esperados**, 4,243 con la variante recalibrada y 5 observados. El presupuesto
fraccionario al 5 % equivale a 12,75 tramos; no es el plan entero de 12 tramos del
piloto. Un solo turno no estima la precisión general del modelo.
''')
    md('''
## 14. Reconstrucción de predicciones e intervalos con originales locales

La siguiente celda detecta los insumos necesarios. Si están completos, verifica sus
hashes, carga la candidata de 2024 y reconstruye predicciones, nueve métricas y el
IC de captura frente a M1. Si faltan, informa cuáles; las tablas anteriores siguen
siendo evidencia publicada comprobada, pero no se afirma haber reproducido los
joblib en esa ejecución. No se solicitan descargas ni se ajusta el modelo aquí.
''')
    code('''
requeridos_locales = ["data/cache/clima_ruta5.npz", "data/calendario/feriados.json",
    "data/fuentes/dgc/anexo_2023_4t.xls", "data/fuentes/dgc/anexo_2024_4t.xls",
    "resultados/modelos/artefactos/ruta_completa_Poisson_clima_2023.joblib",
    "resultados/modelos/artefactos/ruta_completa_Poisson_clima_2024.joblib",
    "resultados/modelos/artefactos/candidato_reajustado2020_2024.joblib",
    "resultados/modelos/artefactos/candidato_reajustado2020_2024_recalibrado_con2024.joblib"]
faltantes_locales = [n for n in requeridos_locales if not (RAIZ / n).is_file()]
CON_ORIGINALES = not faltantes_locales
ESTADO_REPRODUCCION = {"tablas": "comprobadas", "artefactos": "pendiente por falta de insumos",
                        "bootstrap_2024": "no recalculado"}
if CON_ORIGINALES:
    from verificar_cierre import verificar_artefactos
    with threadpool_limits(limits=2):
        for mensaje in verificar_artefactos(RAIZ, auditoria, reajuste, tablas):
            print("✓", mensaje)
    for nombre in requeridos_locales:
        registrar(nombre)
    ESTADO_REPRODUCCION["artefactos"] = "predicciones 2023/2024 y persistencia final comprobadas"
else:
    display(Markdown("**Modo de archivos públicos:** no se reconstruyen los artefactos locales."))
    display(pd.DataFrame({"Insumo local ausente": faltantes_locales}))
''')
    code('''
if CON_ORIGINALES:
    import joblib
    from datos_modelado import preparar_experimento, agrupar_modelado, atributos, expandir_prediccion
    from validar_ruta5 import resumen
    from evaluacion import bootstrap_pareado
    with threadpool_limits(limits=2):
        datos_locales = preparar_experimento()
        filas = np.arange(len(datos_locales["tramos"]))
        claves = agrupar_modelado(datos_locales, filas, 2024)[0]
        f = atributos(claves, datos_locales)
        modelo = joblib.load(RAIZ / "resultados/modelos/artefactos/ruta_completa_Poisson_clima_2024.joblib")
        mu, yy, ee = expandir_prediccion(claves, modelo.predict_rate(f), datos_locales, filas, [2024])
        metricas_recalculadas = resumen(yy, mu, ee)
    esperadas = prueba_ruta[prueba_ruta.anio_prueba.eq(2024) & prueba_ruta.modelo.eq("Poisson_clima")].iloc[0]
    for k, v in metricas_recalculadas.items():
        np.testing.assert_allclose(v, esperadas[k], rtol=1e-9, atol=1e-10)
    display(pd.DataFrame({"Recalculado": metricas_recalculadas,
                          "Registrado": {k: esperadas[k] for k in metricas_recalculadas}}))
    # M1 es constante dentro de cada tramo. Su escala no cambia el ranking.
    train = datos_locales["tiempo"].year < 2024
    orden_m1 = datos_locales["y"][:, train].sum(axis=1).astype(float)
    m1_para_ranking = np.broadcast_to(orden_m1[:, None], yy.shape) * ee
    ef = np.broadcast_to(ee, yy.shape)
    valido = ef.ravel() > 0
    bloques = np.broadcast_to(np.arange(yy.shape[1]) // 168, yy.shape).ravel()[valido]
    ic = bootstrap_pareado(yy.ravel()[valido],
        {"M1": m1_para_ranking.ravel()[valido], "Poisson_clima": mu.ravel()[valido]},
        bloques, replicas=2000, expo=ef.ravel()[valido])["Poisson_clima"]
    registrado = ventaja[ventaja.anio_prueba.eq(2024)].iloc[0]
    for k in ["diferencia_pp", "ic95_inf_pp", "ic95_sup_pp"]:
        np.testing.assert_allclose(ic[k], registrado[k], rtol=1e-9, atol=1e-10)
    display(pd.Series(ic, name="Bootstrap 2024 recalculado").to_frame())
    ESTADO_REPRODUCCION["bootstrap_2024"] = "2000 réplicas; coincide con la tabla original"
    del datos_locales, f, mu, yy, ee, ef, bloques, m1_para_ranking
else:
    print("Predicciones y bootstrap local no recalculados: ver faltantes de la celda anterior.")
''')
    md('''
## 15. Sensibilidades urbana y de umbrales de lluvia

El protocolo se fijó antes de ejecutar cada análisis. Se conservaron dominio,
referencia espacial, exposición y parámetros por partición; no se eligieron cortes
por resultados de 2024. Los scripts y sus comandos están en la sección 18.

**Hallazgo de calidad:** los 975 eventos etiquetados URBANA están en 2020–2021.
Desde 2022 todos aparecen RURAL. No acredita que desaparecieran zonas urbanas;
la causa de la discontinuidad no está resuelta. Con ranking congelado no hay casos
urbanos de prueba y la captura rural es necesariamente igual a la total.
''')
    code('''
poblacion_zona = csv("resultados/sensibilidad/poblacion_zona.csv")
display(poblacion_zona.pivot(index="anio", columns="zona", values="registros"))
assert poblacion_zona.loc[(poblacion_zona.anio >= 2022) & poblacion_zona.zona.eq("URBANA"), "registros"].sum() == 0
sens_lluvia = csv("resultados/sensibilidad/lluvia.csv")
sens_rural = csv("resultados/sensibilidad/ajuste_rural/metricas.csv")
display(sens_rural[sens_rural.modelo.eq("Poisson_clima_rural")][
    ["anio", "urbanos_excluidos_train", "captura5", "observado_esperado", "mae_12h_calendario"]].round(5))
display(sens_lluvia[["anio", "escenario", "captura5", "captura5_turno", "observado_esperado", "mae_12h_calendario"]].round(5))
figura("resultados/sensibilidad/sensibilidad.png")
''')
    md('''
La exclusión de urbanos del entrenamiento define un objetivo rural exploratorio,
no un mapa de tramos rurales. La captura cambia poco, pero el MAE empeora en
2023/2024. No hay mejora uniforme ni validación urbana física independiente.

Para lluvia se reajustó únicamente Poisson con cortes **A: 0,05/0,5** y **B: 0,1/1,0**,
aplicados a entrenamiento y prueba. A apenas modifica categorías y conserva captura
al 5 %. B cambia la captura global −0,327, −0,070 y +0,307 pp según el año.
No hay mejora estable; se conservan los cortes originales. La coincidencia media de
los 12 tramos prioritarios supera 96 %, con turnos donde solo coinciden 8 de 12.
No se calcularon IC de diferencias para estos reajustes ni se reseleccionó la candidata.
''')
    code('''
# Verificar las salidas de sensibilidad y la integridad del código registrado.
for nombre in ["resultados/sensibilidad/auditoria.json", "resultados/sensibilidad/ajuste_rural/auditoria.json"]:
    a = leer_json(nombre)
    carpeta = Path(nombre).parent
    for archivo, digest in a["fuentes_sha256"].items():
        if (RAIZ / archivo).is_file():
            assert hashlib.sha256((RAIZ / archivo).read_bytes()).hexdigest() == digest, archivo
    for archivo, digest in a.get("salidas_sha256", {}).items():
        assert hashlib.sha256(registrar(str(carpeta / archivo)).read_bytes()).hexdigest() == digest
    if "metricas_sha256" in a:
        assert hashlib.sha256(registrar(str(carpeta / "metricas.csv")).read_bytes()).hexdigest() == a["metricas_sha256"]
print("Tablas de sensibilidad íntegras. Las fuentes locales ausentes no se declaran verificadas.")
''')
    md('''
## 16. Investigación de CONASET 2025 y decisión de alcance

Se auditó la instantánea nacional geográfica 2025 (68.994 registros). Los campos
ruta/km no son utilizables para reconstruir el objetivo tramo/hora comparable.
Se ensayaron medidas de cartografía MOP, vías competidoras, controles 2024 y
referencias textuales. La cercanía geográfica no certifica pertenencia vial.

Los ajustes de borde y el texto recuperaron información parcial, pero no acreditaron
una cohorte comparable ni vigencia/cobertura suficiente. Las referencias numéricas
no tienen unidad de kilometraje acreditada. **2025 no se integró**: la decisión
se debe a calidad y comparabilidad de ubicación, no a una demostración de data leakage.
No se incorporó una selección parcial como si fuera todo el año.
''')
    code('''
a2025 = leer_json("resultados/eda_2025/auditoria.json")
cierre2025 = leer_json("resultados/cierre_ubicacion_2025/auditoria.json")
assert a2025["integrado_al_modelo"] is False
assert cierre2025["integrado_2025"] is False and cierre2025["modelos_alterados"] is False
display(csv("resultados/cierre_ubicacion_2025/estados_texto_2025.csv"))
assert eventos.anio.max() == 2024
print("Se conserva el experimento 2020–2024. No hay cohorte 2025 en el modelo.")
''')
    md('''
## 17. Piloto experimental de las siguientes 12 horas

El piloto usa el **reajustado original 2020–2024** y captura meteorología antes de
emitir. Conserva el instante, insumos, modelo, predicciones y prioridades. El
horizonte inicia en la siguiente hora completa y dura 12 horas reales en UTC,
mostradas en hora local. Se seleccionan 12 de 255 tramos enteros (4,71 %), fijos
para toda la ventana, con desempate por km ascendente.

El archivo siguiente resume una emisión **histórica y congelada**. No es una alerta
vigente ni evidencia de acierto. En una copia pública se puede inspeccionar su
registro documentado; reproducir sus tablas requiere las capturas locales originales.
''')
    code('''
piloto_doc = csv("resultados/entrega_final/piloto_documentado.csv")
display(piloto_doc[["emision_utc", "inicio_local", "fin_local", "esperados_total", "esperados_total_recalibrados_referencia", "tramos_seleccionados", "evaluacion_observada"]])
from modelo_piloto import cargar as cargar_portable
config_piloto = leer_json("config/piloto_12h.json")
portable = cargar_portable(config_piloto)
registrar(config_piloto["artefacto_portable"])
assert portable["modelo"] == "Poisson_clima" and portable["ajuste_hasta"] == 2024
carpeta_emision = RAIZ / piloto_doc.iloc[0].carpeta_emision
capturas_disponibles = (RAIZ / piloto_doc.iloc[0].carpeta_capturas).is_dir()
ESTADO_REPRODUCCION["piloto"] = "registro documentado; capturas locales ausentes"
if (carpeta_emision / "auditoria.json").is_file() and capturas_disponibles:
    from piloto_12h import reproducir
    assert hashlib.sha256((carpeta_emision / "auditoria.json").read_bytes()).hexdigest() == piloto_doc.iloc[0].sha256_auditoria_local
    reproducir(carpeta_emision)
    ESTADO_REPRODUCCION["piloto"] = "tablas de emisión reproducidas sin red; sin evaluación observada"
else:
    print("Registro histórico documentado. No se reproducen capturas ausentes ni se emite un pronóstico nuevo.")
''')
    md('''
El piloto comprueba fallos de clima faltante/incompleto, captura posterior o antigua,
calendario fuera de cobertura y caída del proveedor. El calendario manual está
acotado al 4–30/11/2026; no resuelve períodos festivos nuevos automáticamente.
La API acredita una captura previa, pero aquí no su inicialización numérica.

Persisten dos cambios de dominio: **pronóstico en lugar de reanálisis** y
**extrapolación temporal a 2026**. La variante recalibrada se muestra como referencia,
sin acreditarla superior. Para evaluar se necesitan todos los siniestros observados
del horizonte, con ubicación, instante y completitud comprobables. Un reporte de
fallecidos o ausencia de noticias no sustituye ese conjunto. No se imputan ceros
por ausencia de reportes; sin eventos observados la captura es indefinida.

El módulo `revisar_piloto` genera un panel local fechado y reproduce emisiones.
Que una ventana termine no significa que haya sido evaluada. Todavía no se acredita
un servicio operativo ni un efecto de la vigilancia sobre los siniestros.
''')
    md('''
## 18. Código necesario para repetir entrenamiento y experimentos

La comparación original se implementa en `entrenar_comparacion`; cada familia
llama `ModeloConteo.fit` con las claves/atributos de entrenamiento y exposición.
La búsqueda respeta las ventanas previas, luego genera métricas y bootstrap.
No se copia otra implementación en este notebook: se invoca el mismo código que
produjo las auditorías. Los hashes se comprueban en la sección 2.

La siguiente celda está **desactivada por defecto** para no repetir entrenamientos
al leer la entrega. Para una reproducción completa hay que disponer de fuentes
originales locales, activar la variable y elegir una carpeta que no exista.
La corrida no cambia las tablas de referencia que usa el resto del notebook.
''')
    code('''
REENTRENAR_DESDE_CERO = False
SALIDA_NUEVA = RAIZ / "resultados/reproduccion_notebook_nueva"
if REENTRENAR_DESDE_CERO:
    if not all((RAIZ / n).is_file() for n in requeridos_locales[:4]):
        raise RuntimeError("Recuperar clima, calendario y anexos originales antes de entrenar.")
    eda_auditoria = leer_json("resultados/eda/auditoria.json")
    hash_calendario = next(f["sha256"] for f in eda_auditoria["fuentes"]
                          if Path(f["archivo"]).name == "feriados.json")
    hashes_entrenamiento = {"data/cache/clima_ruta5.npz": auditoria["datos"]["clima_cache_sha256"],
        "data/calendario/feriados.json": hash_calendario,
        **{f"data/fuentes/dgc/anexo_{v}.xls": h
           for v, h in auditoria["datos"]["fuentes_flujo_sha256"].items()}}
    for archivo, digest in hashes_entrenamiento.items():
        assert hashlib.sha256((RAIZ / archivo).read_bytes()).hexdigest() == digest, archivo
    if SALIDA_NUEVA.exists():
        raise FileExistsError("Elegir otra SALIDA_NUEVA para preservar resultados existentes.")
    entorno = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
    for comando in ["entrenar_comparacion", "reajustar_candidato", "resumir_modelos"]:
        subprocess.run([sys.executable, "proyecto.py", comando, "--salida", str(SALIDA_NUEVA)],
                       cwd=RAIZ, env=entorno, check=True)
else:
    print("Entrenamiento completo no solicitado. Se usan modelos existentes y evidencia auditada.")

# Otras reproducciones autorizadas: ejecutar manualmente con una salida nueva.
comandos = pd.DataFrame({"Análisis": ["EDA original", "Lluvia y ranking por zona", "Exclusión urbana", "Contrastes", "Tendencia", "Panel de emisiones"],
    "Comando": ["proyecto.py explorar_datos --salida /tmp/eda_nueva",
                "proyecto.py sensibilidad --salida /tmp/sensibilidad_nueva",
                "proyecto.py sensibilidad_urbana_ajuste --salida /tmp/rural_nuevo",
                "proyecto.py contrastes_poisson --salida /tmp/contrastes_nuevos",
                "proyecto.py tendencia_anual --salida /tmp/tendencia_nueva",
                "proyecto.py revisar_piloto"]})
display(comandos)
''')
    md('''
## 19. Conclusiones, limitaciones y trazabilidad

1. **El proyecto responde a la priorización retrospectiva:** Poisson_clima concentra
   más siniestros que M1 con el mismo presupuesto global histórico. La ganancia es
   menor cuando los tramos permanecen fijos por turno; se presentan ambas decisiones.
2. **La selección tiene justificación temporal:** se compararon tres familias y se
   eligió con 2022/2023 y sencillez. 2024 se mantiene como evaluación histórica reutilizada.
3. **Incorporar una variable no garantiza utilidad:** el proxy DGC fue integrado y
   evaluado en cohortes comparables, sin mejora consistente. No se dispone de
   exposición real por vehículo-km ni de publicación histórica acreditada.
4. **Orden y cantidad requieren interpretaciones distintas:** el ranking de Poisson
   es útil en el estudio, mientras que el nivel de conteos muestra sesgo. La
   recalibración mejora algunos errores y no demuestra calibración futura.
5. **Las sensibilidades no justifican cambiar la candidata:** el ajuste rural no
   mejora uniformemente y la discontinuidad de etiquetas limita el análisis urbano;
   los cortes alternativos de lluvia no aportan mejora estable entre años.
6. **El piloto acredita una implementación reproducible:** todavía requiere
   evaluación con eventos posteriores completos y pronósticos emitidos.

Quedan como trabajo futuro una exposición vehicular acreditada, etiquetas urbanas
comparables, validación con otro año correctamente ubicado y evaluación prospectiva
con fuentes disponibles al decidir. No se reclaman relaciones causales ni accidentes
evitados. La presentación y la lectura del acta por el equipo son tareas de cierre
académico; este notebook no registra su aprobación ni un envío al profesor.

La última celda resume el nivel **realmente ejecutado** y las huellas de los archivos
leídos. Las auditorías originales permanecen inalteradas. Fuentes y explicación
ampliada: [ficha de datos](../docs/cierre/02_datos_flujo.md),
[modelo final](../docs/cierre/03_modelo_final.md),
[interpretación](../docs/cierre/04_interpretacion.md),
[sensibilidad](../docs/sensibilidad.md) y [piloto](../docs/piloto_12h.md).
''')
    code('''
# Confirmar que ningún archivo leído cambió durante la ejecución.
for archivo, digest in EVIDENCIA.items():
    assert hashlib.sha256((RAIZ / archivo).read_bytes()).hexdigest() == digest, archivo
display(pd.Series(ESTADO_REPRODUCCION, name="Estado de esta ejecución").to_frame())
display(JSON(ESTADO_REPRODUCCION))
display(pd.DataFrame([{"Archivo": nombre, "SHA256": digest}
                      for nombre, digest in sorted(EVIDENCIA.items())]))
print("CIERRE_NOTEBOOK_CORRECTO: conclusiones y evidencia conciliadas.")
''')
    for i, celda in enumerate(celdas):
        celda["id"] = f"entrega-final-{i:03d}"
    return nbf.v4.new_notebook(cells=celdas, metadata={
        "kernelspec": {"display_name": "Python 3 (proyecto de siniestros)", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13.3"},
        "proyecto": {"titulo": "Predicción dinámica de siniestros en carreteras chilenas",
                     "base_cientifica": "5d80f400c9ea05efb9603a0427b399cb0ba31453", "entrega": "III"}})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=RAIZ / "notebooks/EntregaFinal_Proyecto_DS.ipynb")
    args = p.parse_args()
    nb = construir()
    nbf.validate(nb)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, args.salida)
    print(f"Notebook construido: {args.salida} · {len(nb.cells)} celdas")

if __name__ == "__main__":
    main()
