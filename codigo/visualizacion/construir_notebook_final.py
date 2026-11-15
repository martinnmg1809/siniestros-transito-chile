"""Construye el único notebook de entrega con fuentes y datos incorporados.

La copia entregada no necesita ZIP externo, rutas personales ni modelos preajustados.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile
import nbformat as nbf
from proyecto import RAIZ


def paquete():
    archivos = ['proyecto.py', 'config/migracion_estructura.csv', 'requirements-colab.txt',
        'data/siniestros/ruta5_2020_2024.csv.gz', 'data/cache/clima_ruta5.npz',
        'data/calendario/feriados.json', 'data/fuentes/dgc/anexo_2023_4t.xls',
        'data/fuentes/dgc/anexo_2024_4t.xls']
    archivos += ['codigo/datos/'+n+'.py' for n in ['fuentes','datos_ruta5','datos_modelado','clima_utc','flujo_concesiones','integrar_flujo']]
    archivos += ['codigo/modelos/'+n+'.py' for n in ['modelo','modelos_conteo','entrenar_comparacion','reajustar_candidato','calibracion_modelos']]
    archivos += ['codigo/evaluacion/'+n+'.py' for n in ['evaluacion','validar_ruta5','metricas_entrega','experimento_entrega']]
    archivos += ['resultados/eda/'+n+'.csv' for n in ['mop_capas_y_anios','mop_cruce_rol_tmda']]
    archivos += ['resultados/cierre_ubicacion_2025/estados_texto_2025.csv']
    buf=io.BytesIO()
    hashes={}
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for nombre in sorted(archivos):
            datos=(RAIZ/nombre).read_bytes();hashes[nombre]=hashlib.sha256(datos).hexdigest()
            info=zipfile.ZipInfo(nombre,(2026,11,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,datos)
        info=zipfile.ZipInfo('MANIFIESTO_ENTREGA.json',(2026,11,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,json.dumps({'archivos_sha256':hashes,'incluye_modelos_preajustados':False},ensure_ascii=False,sort_keys=True))
    datos=buf.getvalue()
    return base64.b64encode(datos).decode(),hashlib.sha256(datos).hexdigest()


def prefijo():
    c=[]
    def md(s):c.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):c.append(nbf.v4.new_code_cell(s.strip()))
    md('''
# Predicción dinámica de siniestros en carreteras chilenas
## Presentación Técnica Final · Etapa III

**Integrantes:** Diego Franco, Vicente González, Martín Mora, Cristóbal Rivera y Máximo Urrutia.
**Profesor:** Andrés Jiménez B. · **Asignatura:** Ciencia de Datos · **Fecha:** noviembre de 2026.

Nuestro proyecto estudia cómo cambia la frecuencia de siniestros a lo largo de la
Ruta 5 Sur según la ubicación, el horario, el calendario y la lluvia. Queremos
estimar cuántos eventos esperar y evaluar si esa información ayuda a priorizar la
vigilancia mejor que un mapa histórico fijo.

El notebook recorre preparación, exploración, entrenamiento, validación temporal,
comparación e interpretación. Todas las tablas de evaluación y las conclusiones
finales se calculan con los modelos entrenados durante esta ejecución. Los datos
se mantienen en 2020–2024; el año 2024 se declara evaluación histórica reutilizada,
pues ya se había inspeccionado en etapas anteriores.
''')
    md('''
### Cómo ejecutar la entrega

El archivo incorpora el código y las fuentes necesarias. No requiere clonar GitHub,
subir un ZIP adicional ni disponer de nuestros modelos guardados. La primera celda
prepara una carpeta temporal y verifica sus archivos. Se necesita Python 3.11–3.13
y CPU; la instalación inicial de bibliotecas requiere internet si faltan versiones.

En Colab, ejecutar primero esa celda. Si solicita reiniciar Python después de
instalar dependencias, reiniciar la sesión sin eliminar la máquina y volver a ejecutar
desde arriba. Después, usar **Ejecutar todas**. La comparación completa realiza
60 ajustes de búsqueda/validación más el reajuste final y puede tardar decenas de
minutos, según los recursos de la sesión. No se sustituye ese entrenamiento por tablas
precargadas. Las salidas quedan dentro de la carpeta temporal de esta ejecución.

El bloque compacto de preparación contiene fuentes y datos comprimidos, sin joblib
preajustados. El código extraído es legible dentro de `codigo/`. En las secciones
siguientes explicamos y utilizamos sus funciones. El historial del repositorio
conserva las contribuciones del equipo y la asistencia de herramientas declarada.
''')
    b64,digest=paquete()
    code('''#@title Preparar los datos y el código de la entrega
import base64, hashlib, io, json, os, sys, tempfile, zipfile, subprocess
from pathlib import Path
import importlib.metadata as metadata
PAQUETE_B64 = "'''+b64+'''"
paquete = base64.b64decode(PAQUETE_B64)
assert hashlib.sha256(paquete).hexdigest() == "'''+digest+'''"
RAIZ = Path(tempfile.mkdtemp(prefix="siniestros_entrega_"))
with zipfile.ZipFile(io.BytesIO(paquete)) as archivo:
    for nombre in archivo.namelist():
        if Path(nombre).is_absolute() or ".." in Path(nombre).parts:
            raise ValueError("Ruta no admitida en el paquete")
    archivo.extractall(RAIZ)
manifest = json.loads((RAIZ / "MANIFIESTO_ENTREGA.json").read_text())
for nombre, sha in manifest["archivos_sha256"].items():
    assert hashlib.sha256((RAIZ / nombre).read_bytes()).hexdigest() == sha, nombre
assert manifest["incluye_modelos_preajustados"] is False
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ))
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ.setdefault("MPLCONFIGDIR", "/tmp/siniestros-matplotlib")
if not (3, 11) <= sys.version_info[:2] <= (3, 13):
    raise RuntimeError("Seleccionar Python 3.11–3.13 para las versiones de esta entrega")
esperadas = {"numpy": ("numpy", "2.2.3"), "pandas": ("pandas", "2.2.3"),
    "scipy": ("scipy", "1.14.1"), "scikit-learn": ("sklearn", "1.6.1"),
    "matplotlib": ("matplotlib", "3.9.4"), "joblib": ("joblib", "1.6.0"), "xlrd": ("xlrd", "2.0.1")}
cambios=[]
for nombre,(modulo,version) in esperadas.items():
    try: actual=metadata.version(nombre)
    except metadata.PackageNotFoundError: actual=None
    if actual != version: cambios.append((nombre,modulo))
if cambios:
    cargados=[m for _,m in cambios if m in sys.modules]
    subprocess.run([sys.executable,"-m","pip","install","--quiet","-r","requirements-colab.txt"],check=True)
    if cargados:
        raise RuntimeError("Dependencias instaladas. Reinicia Python sin eliminar la sesión y vuelve a ejecutar desde arriba.")
print("Fuentes verificadas:",len(manifest["archivos_sha256"]),"· modelos precargados: ninguno")
print("Directorio de esta ejecución:",RAIZ)
''')
    c[-1].metadata={'jupyter':{'source_hidden':True},'cellView':'form','tags':['hide-input']}
    md('''
## 1. Pregunta y enfoque metodológico

La pregunta es: **¿qué tramos y horas concentran más siniestros esperados y cuánto
mejora su priorización al incorporar contexto temporal, lluvia y circulación?**
La unidad de análisis es un tramo de 5 km durante una hora civil. La respuesta es
un conteo, que puede valer cero, uno o más.

Seguimos las etapas de comprensión del problema, comprensión y preparación de los
datos, modelado y evaluación de CRISP-DM. Elegimos regresión de conteos para conservar
la pregunta de cantidad y evaluamos también la capacidad de ordenar tramos. Una
segunda evaluación convierte los conteos en “al menos un siniestro” para interpretar
accuracy, precisión, recall, F1 y las curvas ROC/PR; ese diagnóstico auxiliar no
cambia el objetivo principal ni el criterio de selección.
''')
    code('''
import proyecto
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from IPython.display import display, Markdown, Image, JSON
from io import BytesIO
from threadpoolctl import threadpool_limits
from datos_ruta5 import cargar_eventos, referencia_entrenamiento, grilla_civil, exposicion_civil
from datos_modelado import cuarentena_espacial

def mostrar(fig):
    b=BytesIO();fig.savefig(b,format="png",dpi=130,bbox_inches="tight")
    display(Image(data=b.getvalue()));plt.close(fig)

eventos_km, audit_fuente = cargar_eventos()
eventos, cuarentena = cuarentena_espacial(eventos_km)
referencia = referencia_entrenamiento(eventos)
tiempo, y_base, fuera = grilla_civil(eventos,referencia.tramo.to_numpy())
expo = exposicion_civil(tiempo)
assert len(eventos)==14420 and len(referencia)==255 and fuera==0
assert y_base[:,expo==0].sum()==0
print("Población preparada:",len(eventos),"eventos;",len(referencia),"tramos")
''')
    md('''
## 2. Diseño de la comparación y entrenamiento

Entrenamos Poisson, Gradient Boosting y Random Forest. M0 (tasa uniforme) y M1
(mapa espacial) son nuestras referencias. Cada familia incorpora calendario y lluvia;
en los 153 tramos cubiertos se añade el proxy DGC para medir su aporte en la misma
población. Los híbridos usan respaldo sin flujo donde no hay información.

La validación respeta el orden del tiempo: entrenamiento 2020–2021/prueba 2022;
2020–2022/prueba 2023; 2020–2023/prueba 2024. En 2022 usamos una configuración simple
prefijada; para 2023 elegimos con 2022 y para 2024 con 2022/2023. El modelo final se
selecciona con captura global al 5 % promediada en 2022/2023 y preferencia por sencillez
a 0,1 puntos porcentuales del mejor promedio. No se elige usando F1 o resultados de 2024.

La celda siguiente ejecuta el entrenamiento completo. Se muestran los ajustes y sus
resultados conforme terminan; cada llamada del entrenador utiliza
`ModeloConteo(familia, variante, parametros).fit(atributos_train, conteos_train, exposicion_train)`.
Los parámetros, años usados y diagnósticos quedan registrados en los archivos de esta corrida.
''')
    code('''
# Ajustar todos los modelos y evaluar con el protocolo temporal descrito.
# No se cargan joblib ni métricas de entregas anteriores.
from time import perf_counter
SALIDA = RAIZ / "resultados/ejecucion_notebook"
inicio_ajuste = perf_counter()
proceso = subprocess.Popen([sys.executable,"proyecto.py","experimento_entrega","--salida",str(SALIDA)],
    cwd=RAIZ,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
for linea in proceso.stdout:
    print(linea,end="",flush=True)
if proceso.wait()!=0:
    raise RuntimeError("El entrenamiento no terminó correctamente; revisar el último mensaje")
minutos_ajuste = (perf_counter()-inicio_ajuste)/60
metricas = pd.read_csv(SALIDA/"metricas.csv")
bootstrap = pd.read_csv(SALIDA/"bootstrap.csv")
seleccion = pd.read_csv(SALIDA/"seleccion_temporal.csv")
busqueda = pd.read_csv(SALIDA/"busqueda_temporal.csv")
conteo_extra = pd.read_csv(SALIDA/"metricas_conteo_adicionales.csv")
binarias = pd.read_csv(SALIDA/"metricas_binarias.csv")
curvas_binarias = pd.read_csv(SALIDA/"curvas_binarias.csv")
auditoria = json.loads((SALIDA/"auditoria.json").read_text())
reajuste = json.loads((SALIDA/"reajuste.json").read_text())
recalibracion = pd.read_csv(SALIDA/"recalibracion_candidato.csv")
assert len(metricas)==114 and len(busqueda)==60 and len(seleccion)==36
print(f"Entrenamiento y evaluación completados en {minutos_ajuste:.1f} minutos.")
''')
    for i,x in enumerate(c):x['id']=f'entrega-definitiva-{i:03d}'
    return c


def agregar_analisis(c):
    def md(s):c.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):c.append(nbf.v4.new_code_cell(s.strip()))
    md('''
## 3. Datos utilizados y correcciones de calidad

Volvemos sobre los datos de entrada para interpretar qué aprendieron los modelos.
CONASET aporta los siniestros; ERA5, la precipitación horaria; el calendario indica
la posición dentro de períodos festivos, y los anexos DGC describen circulación por
contrato y trimestre. Conservamos las unidades de cada fuente y verificamos sus
hashes al preparar el notebook.

El archivo de CONASET contiene otras variantes de Ruta 5. Nuestro filtro conserva
exclusivamente `RUTA 5 SUR`, descarta cinco kilómetros no utilizables y pone en
cuarentena cinco discordancias importantes entre kilometraje y coordenadas.
No corregimos esas ubicaciones por suposición. La referencia espacial se construye
solo con 2020–2021 y permanece fija para los años de prueba.
''')
    code('''
display(pd.DataFrame({"Etapa":["Ruta 5 Sur en la fuente","Después del filtro de km","Después de cuarentena"],
    "Eventos":[audit_fuente["registros_ruta"],len(eventos_km),len(eventos)]}))
display(cuarentena[["ID","anio","km","distancia_referencia_km","motivo"]].round(2))
campos=["ID","FECHA","Hora_aprox","Ruta","Ubicación","Latitud","longitud"]
display(eventos[campos].isna().sum().rename("Faltantes en campos críticos").to_frame())
assert eventos.ID.is_unique and eventos.hora.between(0,23).all()
assert (eventos.TOTAL_LESI==eventos[["GRAVES","MENOS_GRAV","LEVES"]].sum(axis=1)).all()
print("No se eliminan eventos graves por ser extremos: se conservan los conteos legítimos.")
''')
    md('''
Tener campos completos no demuestra que todos los siniestros estén registrados ni
que cada coordenada tenga precisión vial. La cuarentena resuelve los casos
incompatibles detectados; no certifica la geometría restante. La resolución horaria
y los tramos de 5 km son coherentes con la hora aproximada y el redondeo del km.
''')
    md('''
## 4. Exploración de frecuencia, ubicación y horario

Primero observamos cómo se distribuyen los eventos. Los conteos anuales no son
estables y algunos tramos concentran más siniestros. Por eso necesitamos comparar
con una referencia espacial y validar en años posteriores, en lugar de separar
filas al azar. Las diferencias por hora pueden incluir cambios de circulación;
no deben interpretarse directamente como peligrosidad por conductor.
''')
    code('''
anuales=eventos.groupby("anio").size().rename("Siniestros")
display(anuales.to_frame())
fig,ax=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
anuales.plot.bar(ax=ax[0],rot=0,color="#267a91")
eventos.groupby("hora").size().reindex(range(24),fill_value=0).plot(ax=ax[1],marker="o",color="#267a91")
eventos.groupby("tramo").size().reindex(referencia.tramo,fill_value=0).plot(ax=ax[2],color="#ca862e")
for a,t in zip(ax,["Conteos por año","Conteos por hora aproximada","Conteos por tramo"]):
    a.set_title(t);a.set_ylabel("Siniestros")
ax[2].set_xlabel("Km inicial");mostrar(fig)
print(f"El {(y_base[:,expo>0]==0).mean():.2%} de las celdas civiles existentes no tiene siniestros.")
print("Horas civiles inexistentes/repetidas:",int((expo==0).sum()),int((expo==2).sum()))
''')
    md('''
La gran proporción de ceros vuelve poco informativa una accuracy aislada: predecir
siempre ausencia de siniestro ya acierta en casi todas las celdas. Para el objetivo
principal necesitamos evaluar tanto el orden de priorización como la cantidad
esperada. Más adelante cuantificamos esa comparación con las mismas observaciones.
''')
    md('''
## 5. Clima, calendario y exposición horaria

ERA5 describe las condiciones históricas de precipitación en celdas de 0,25°.
Las categorías son seco (<0,1), llovizna (0,1 ≤ p < 0,5) y lluvia (p ≥0,5 mm/h).
No confundimos este reanálisis con un pronóstico emitido antes de decidir.

La exposición del modelo representa horas reales: 0, 1 o 2 según el cambio de
horario. No es exposición vehicular. CONASET no diferencia las dos ocurrencias
de una hora repetida, por lo que se usa una aproximación explícita de conteo conjunto
y precipitación media. Los NaN de horas inexistentes no se toman como observaciones secas.
''')
    code('''
from datos_modelado import preparar_experimento, agrupar_modelado, atributos, expandir_prediccion
from clima_utc import cargar_cache
from integrar_flujo import serie_flujo, limites_documentados
import joblib

datos=preparar_experimento()
clima=cargar_cache()
assert np.array_equal(datos["y"],y_base)
p=clima["precip"][:,clima["exposicion_tiempo"]>0]
assert np.isfinite(p).all() and (p>=0).all()
display(pd.Series({"Celdas ERA5":len(clima["celdas"]),"Tramos":len(datos["tramos"]),
    "Etiquetas civiles":len(datos["tiempo"]),"Precipitación máxima mm/h":float(p.max()),
    "Fracción de mediciones de celda con 0 mm":float((p==0).mean())},name="Diagnóstico").to_frame())
calendario=json.loads((RAIZ/"data/calendario/feriados.json").read_text())
display(pd.Series({"Fechas marcadas en el calendario":len(calendario),
    "Primera fecha":min(calendario),"Última fecha":max(calendario)},name="Calendario histórico").to_frame())
''')
    md('''
Varios tramos comparten una celda meteorológica; repetir su dato no genera
observaciones independientes. La codificación del calendario distingue inicio,
día intermedio y final de período festivo. Su cobertura es histórica y no se
extrapola automáticamente a otros años.
''')
    md('''
## 6. Incorporación del flujo vehicular

El profesor observó que un tramo puede tener más siniestros porque circulan más
vehículos. Investigamos esa limitación e incorporamos un proxy de la DGC:
**promedio mensual de pasadas por punto × 3 / días del trimestre**. Se añaden su
logaritmo y el logaritmo de los puntos implícitos, rezagados dos trimestres.

Se usan seis contratos y siete intervalos interiores conservadores. El proxy
se aplica por contrato y trimestre; no mide vehículos únicos ni el flujo horario
real de cada tramo. La cercanía a una concesión no acredita homogeneidad de tráfico.
''')
    code('''
flujo=pd.read_csv(SALIDA/"flujo_rezagado.csv")
cobertura=pd.read_csv(SALIDA/"cobertura_flujo.csv")
display(cobertura)
display(limites_documentados()[["contrato","km_inicio","km_fin","margen_km"]])
assert (pd.PeriodIndex(flujo.periodo_objetivo,freq="Q")-2==pd.PeriodIndex(flujo.periodo_medicion,freq="Q")).all()
assert (pd.to_datetime(flujo.fin_medicion)<pd.to_datetime(flujo.inicio_objetivo)).all()
assert flujo.loc[~flujo.flujo_disponible,["proxy_pasadas_por_punto_dia","puntos_implicitos"]].isna().all().all()
print("Tramos cubiertos:",int(datos["cubiertos"].sum()),"de",len(referencia))
print("Filas con/sin flujo:",int(flujo.flujo_disponible.sum()),int((~flujo.flujo_disponible).sum()))
''')
    md('''
El rezago mantiene separados los períodos medidos y predichos, pero no acredita
que cada anexo estuviera publicado en la fecha de decisión. Los resultados con
flujo son, por tanto, retrospectivos. Los 102 tramos sin serie completa no se
rellenan con cero; los híbridos utilizan un respaldo sin flujo.

También revisamos el TMDA del PNCV: faltan mediciones de 2020, existen ceros sin
interpretar y no se acreditó la correspondencia entre ramas y tramos. Se conserva
como diagnóstico de fuente y no se convierte en denominador vehículo-km.
''')
    code('''
display(pd.read_csv(RAIZ/"resultados/eda/mop_capas_y_anios.csv")[["capa","titulo","anios_observados","tmda_cero","tmda_faltante"]])
display(pd.read_csv(RAIZ/"resultados/eda/mop_cruce_rol_tmda.csv"))
print("Estas tablas describen la auditoría de la fuente PNCV; no son resultados de los modelos recién entrenados.")
''')
    md(r'''
## 7. Cómo se ajustan los modelos y se elige la solución

En Poisson modelamos $Y_{s,t}\sim Poisson(e_t\lambda_{s,t})$. El logaritmo de la tasa
incluye efectos aditivos de tramo, hora, día de semana, mes, posición festiva,
lluvia y tendencia anual. La penalización L2 reduce la inestabilidad de los
coeficientes. GB y RF permiten relaciones más flexibles; se ajustan con pérdida o
criterio Poisson y peso de exposición, usando las mismas particiones.

Las configuraciones de búsqueda son pequeñas y se mantienen como en el protocolo
del proyecto. No ampliamos la grilla para mejorar retrospectivamente 2024. El RF
usa 80 árboles y hasta 80.000 filas agrupadas por árbol; sus hojas operan sobre
combinaciones de atributos, no sobre cada hora individual.
''')
    code('''
from modelos_conteo import GRILLAS
from IPython.display import Code
import inspect
from modelos_conteo import ModeloConteo

display(pd.DataFrame([{"Familia":f,"Configuración":i,"Parámetros":str(p)}
    for f,lista in GRILLAS.items() for i,p in enumerate(lista)]))
display(seleccion[(seleccion.cohorte=="ruta_completa")][["anio_prueba","familia","configuracion","anios_usados_para_elegir","parametros"]])
# Implementación utilizada por el entrenamiento que acaba de ejecutarse.
display(Code(inspect.getsource(ModeloConteo.fit),language="python"))
''')
    md('''
La separación temporal busca medir generalización a un año posterior. Los resultados
de 2022/2023 sirven para elegir; 2024 se reserva de esa selección, aunque su
inspección previa obliga a llamarlo evaluación histórica reutilizada. Las
transformaciones de atributos se ajustan con entrenamiento. La tabla siguiente
reproduce la elección usando únicamente los resultados de esta corrida.
''')
    code('''
cv=metricas[(metricas.particion=="prueba")&(metricas.anio_prueba<2024)&
    metricas.cohorte.isin(["ruta_completa","hibrido_ruta_completa"])&(metricas.modelo!="M0")]
medias=cv.groupby("modelo").captura5.mean()
preferencia=["M1"]+[f"{f}_clima" for f in GRILLAS]+[f"Hibrido_{f}_{v}" for v in ["clima","clima_flujo"] for f in GRILLAS]
candidata=next(n for n in preferencia if medias[n]>=medias.max()-.001)
assert candidata==auditoria["modelo_candidato_por_cv_pre2024"]
display(pd.DataFrame({"Captura media 2022/2023 (%)":medias*100,
    "Distancia al mejor (pp)":(medias.max()-medias)*100,
    "Dentro de tolerancia":medias>=medias.max()-.001}).sort_values("Captura media 2022/2023 (%)",ascending=False).round(4))
display(Markdown(f"La regla temporal selecciona **{candidata}**. Su captura media anterior a 2024 es **{medias[candidata]*100:.3f} %**, "
    f"frente a **{medias.max()*100:.3f} %** del mejor promedio. La distancia es **{(medias.max()-medias[candidata])*100:.3f} puntos porcentuales**."))
''')
    md('''
## 8. Qué métricas responden a cada pregunta

Como la respuesta es un conteo, evaluamos tanto la cantidad esperada como la
priorización de tramos. Complementamos ese análisis con un diagnóstico de celdas
con o sin siniestros, que permite interpretar accuracy, F1 y las curvas ROC/PR.
Cada grupo de métricas responde a una pregunta distinta:

| Pregunta | Métricas | Unidad y alcance |
|---|---|---|
| ¿Dónde priorizar con un presupuesto limitado? | Captura 5/10/20 % e IC por bloques | Fracción de siniestros históricos concentrados; no accidentes evitados |
| ¿Qué ocurre si los tramos permanecen fijos? | Captura por turno de 12 h | Misma ubicación durante el turno; presupuesto fraccionario al 5 % |
| ¿Cuántos siniestros esperar? | MAE, RMSE, desvianza de Poisson y O/E | Conteos por celda o total de la cohorte por turno, identificados por separado |
| ¿Cómo se separan celdas con/sin evento? | Accuracy, precision, recall, F1, balanced accuracy, ROC-AUC, PR-AUC/AP y matriz de confusión | Diagnóstico binario auxiliar con etiqueta `conteo > 0` |

La captura global permite cambiar de tramo cada hora; por turno los tramos se
mantienen fijos. MAE y RMSE del total por turno no son errores por tramo. O/E menor
que 1 indica sobreestimación agregada, y mayor que 1, subestimación. La desvianza
compara conteos dentro de la misma población. El R² se muestra como diagnóstico
adicional del error frente a una media, sin utilizarlo para seleccionar el modelo.
MAE resume el error absoluto medio; RMSE penaliza con mayor fuerza los errores
grandes. Un R² negativo indica que, para ese error cuadrático y esa agregación,
la predicción es peor que utilizar la media observada de referencia; no equivale
por sí solo a una evaluación del ranking de vigilancia.
No usamos MAPE porque la gran cantidad de ceros vuelve problemática su interpretación.
''')
    md('''
## 9. Comparación de modelos en la ruta completa

La siguiente tabla utiliza exclusivamente prueba 2024 y los mismos 255 tramos.
Las métricas fueron calculadas al predecir con los modelos entrenados hasta 2023.
Mostramos las referencias junto con las tres familias para separar cuánto aporta
el mapa espacial de lo que agrega el contexto dinámico.
''')
    code('''
prueba=metricas[(metricas.particion=="prueba")&(metricas.cohorte=="ruta_completa")]
tabla2024=prueba[prueba.anio_prueba==2024].copy()
extras2024=conteo_extra[(conteo_extra.anio_prueba==2024)&(conteo_extra.cohorte=="ruta_completa")&(conteo_extra.particion=="prueba")]
comparacion=tabla2024.merge(extras2024,on=["anio_prueba","cohorte","modelo","particion"],validate="one_to_one")
comparacion["captura5_pct"]=comparacion.captura5*100
comparacion["captura10_pct"]=comparacion.captura10*100
comparacion["captura20_pct"]=comparacion.captura20*100
comparacion["captura_turno_pct"]=comparacion.captura5_turno*100
muestra2024=y_base[:,tiempo.year==2024]
valida2024=expo[tiempo.year==2024]>0
var_celda=muestra2024[:,valida2024].var()
var_turno=muestra2024.reshape(len(referencia),-1,12).sum(axis=(0,2)).var()
comparacion["r2_celda"]=1-comparacion.rmse_celda**2/var_celda
comparacion["r2_total_turno"]=1-comparacion.rmse_total_turno**2/var_turno
display(Markdown("**Priorización: captura de siniestros con el mismo presupuesto.**"))
display(comparacion[["modelo","captura5_pct","captura10_pct","captura20_pct","captura_turno_pct"]].round(4))
display(Markdown("**Conteos: calibración y error en la misma población de prueba.**"))
display(comparacion[["modelo","observado_esperado","mae_celda","rmse_celda","mae_12h_calendario","rmse_total_turno","r2_total_turno","desvianza_por_hora"]].round(5))
cohorte_candidata="hibrido_ruta_completa" if candidata.startswith("Hibrido_") else "ruta_completa"
c2024=metricas[(metricas.anio_prueba==2024)&(metricas.particion=="prueba")&
    (metricas.cohorte==cohorte_candidata)&(metricas.modelo==candidata)].iloc[0]
base2024=tabla2024[tabla2024.modelo=="M1"].iloc[0]
display(Markdown(f"En esta ejecución, **{candidata}** captura **{c2024.captura5:.2%}** de los eventos con el 5 % del presupuesto global, "
    f"frente a **{base2024.captura5:.2%}** de M1. Con tramos fijos por turno, su captura es **{c2024.captura5_turno:.2%}**. "
    f"El MAE del total por turno es **{c2024.mae_12h_calendario:.3f}** siniestros y O/E es **{c2024.observado_esperado:.3f}**. "
    "Estas cifras permiten evaluar por separado priorización y cantidad."))
''')
    code('''
fig,ax=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
for nombre in ["M1","Poisson_clima","GradientBoosting_clima","RandomForest_clima"]:
    d=prueba[prueba.modelo==nombre].sort_values("anio_prueba")
    ax[0].plot(d.anio_prueba,d.captura5*100,"o-",label=nombre)
    ax[1].plot(d.anio_prueba,d.captura5_turno*100,"o-",label=nombre)
for a,t in zip(ax,["Priorización global","Tramos fijos por turno de 12 horas"]):
    a.set(title=t,xlabel="Año de prueba",ylabel="Captura con presupuesto del 5 % (%)",xticks=[2022,2023,2024],ylim=(0,30))
    a.grid(alpha=.2);a.legend(fontsize=8)
mostrar(fig)
''')
    md('''
Una captura favorable no resuelve automáticamente la calibración. Además, un modelo
puede ganar en 2024 y no ser el seleccionado, porque la decisión se tomó con los
años anteriores. La comparación debe conservar ambos resultados en lugar de cambiar
la regla después de mirar la prueba.
''')
    md('''
## 10. Validación temporal e incertidumbre

Comparamos entrenamiento y prueba con la misma métrica. Una brecha grande puede
reflejar sobreajuste y cambios temporales; por sí sola no identifica la causa.
Los intervalos siguientes usan 2.000 remuestreos semanales pareados, manteniendo
predicciones y selección fijas. No incorporan incertidumbre del reentrenamiento ni
corrigen múltiples comparaciones.
''')
    code('''
brecha=metricas[(metricas.cohorte=="ruta_completa")&metricas.modelo.isin(["Poisson_clima","GradientBoosting_clima","RandomForest_clima"])].pivot(index=["anio_prueba","modelo"],columns="particion",values="captura5").reset_index()
brecha["brecha_pp"]=(brecha["train"]-brecha["prueba"])*100
display(brecha.round(5))
ventaja=bootstrap[(bootstrap.cohorte==cohorte_candidata)&(bootstrap.modelo==candidata)&(bootstrap.referencia=="M1")]
display(ventaja[["anio_prueba","diferencia_pp","ic95_inf_pp","ic95_sup_pp","replicas_validas"]].round(4))
intervalo2024=ventaja[ventaja.anio_prueba==2024].iloc[0]
display(Markdown(f"La diferencia de captura de la candidata frente a M1 en 2024 es **{intervalo2024.diferencia_pp:.2f} pp**, "
    f"con IC95 % **[{intervalo2024.ic95_inf_pp:.2f}; {intervalo2024.ic95_sup_pp:.2f}] pp**. "
    "Un intervalo que incluya cero se debe comunicar como evidencia insuficiente para distinguir la mejora en ese año, no como igualdad demostrada."))
''')
    md('''
## 11. Cuánto aportan la lluvia y el proxy de circulación

La lluvia se compara como clima menos calendario, y el flujo como clima+flujo menos
clima. Son contrastes distintos sobre los mismos 153 tramos, con idénticos eventos
y presupuesto. El híbrido de toda la ruta se informa aparte, porque también cambia
la escala relativa entre el especialista y el respaldo.
''')
    code('''
aportes=bootstrap[(bootstrap.cohorte=="con_contrato")&
    (bootstrap.referencia==bootstrap.modelo.str.replace("_clima_flujo","_clima",regex=False))].copy()
lluvia=bootstrap[(bootstrap.cohorte=="con_contrato")&bootstrap.modelo.str.endswith("_clima")&
    (bootstrap.referencia==bootstrap.modelo.str.replace("_clima","_calendario",regex=False))].copy()
aportes["aporte"]="flujo";lluvia["aporte"]="lluvia"
aportes=pd.concat([lluvia,aportes],ignore_index=True)
display(aportes[["aporte","anio_prueba","modelo","referencia","diferencia_pp","ic95_inf_pp","ic95_sup_pp"]].round(4))
fig,ax=plt.subplots(figsize=(9,4),constrained_layout=True)
for i,fam in enumerate(GRILLAS):
    d=aportes[(aportes.aporte=="flujo")&(aportes.modelo==fam+"_clima_flujo")].sort_values("anio_prueba")
    ax.errorbar(d.anio_prueba+(i-1)*.12,d.diferencia_pp,
        yerr=np.maximum(0,np.array([d.diferencia_pp-d.ic95_inf_pp,d.ic95_sup_pp-d.diferencia_pp])),fmt="o",capsize=3,label=fam)
ax.axhline(0,color="gray",ls="--");ax.set(xticks=[2022,2023,2024],ylabel="Cambio de captura (pp)",title="Aporte del proxy de flujo · mismos 153 tramos")
ax.legend();mostrar(fig)
flujo_pos=aportes[(aportes.aporte=="flujo")&(aportes.ic95_inf_pp>0)]
display(Markdown(f"De los **{sum(aportes.aporte=='flujo')}** contrastes de flujo, **{len(flujo_pos)}** tienen un intervalo completamente positivo. "
    "La utilidad se juzga por consistencia entre años, signo y magnitud. Un resultado débil de este proxy agregado no prueba que el tráfico real no importe."))
''')
    md('''
## 12. Evaluación binaria auxiliar: accuracy, F1, ROC y precisión–recall

Para responder también la pregunta “¿hubo al menos un siniestro?”, definimos la
etiqueta binaria como `y > 0` en cada celda civil existente. El score es el conteo
esperado por el modelo. Esto evalúa discriminación sobre otra representación de la
respuesta; no transforma la regresión entrenada en un clasificador ni sustituye
las métricas principales.

El umbral se fija como el percentil 95 de las predicciones de **entrenamiento**, con
regla estricta `score > umbral`. No se optimiza F1 ni se usa el año de prueba para
escogerlo. El porcentaje alertado en prueba puede diferir de 5 % por los empates y
los cambios entre años. Los híbridos no tienen una partición train en este protocolo,
por lo que no se inventa un umbral para ellos.

- **Accuracy:** fracción de celdas correctamente clasificadas; puede ser alta por los ceros.
- **Precision:** fracción de alertas que coincide con una celda positiva.
- **Recall:** fracción de celdas positivas detectadas; no es exactamente captura de conteos cuando hay varios eventos en una celda.
- **F1:** media armónica de precision y recall para este umbral concreto.
- **ROC-AUC:** capacidad de ordenar positivos frente a negativos a través de umbrales.
- **PR-AUC/AP:** average precision, resumen de precisión–recall especialmente útil ante positivos raros; se compara con la prevalencia.

También mostramos balanced accuracy y especificidad. Si no hay predicciones
positivas, precision y F1 se informan como cero por convención explícita. ROC-AUC
queda indefinida si solo existe una clase. Las áreas se calcularon con todos los
scores, aunque las curvas se dibujan con un subconjunto de puntos para aligerar el archivo.
Average precision no es el área trapezoidal por interpolación lineal; se identifica
como AP para mantener explícita esa definición.
''')
    code('''
b2024=binarias[(binarias.anio_prueba==2024)&(binarias.cohorte=="ruta_completa")].copy()
columnas_bin=["modelo","prevalencia","umbral_train_p95","fraccion_alertada","accuracy","precision","recall","f1","balanced_accuracy","roc_auc","pr_auc_ap"]
display(b2024[columnas_bin].round(6))
display(Markdown("**Generalización temporal del diagnóstico auxiliar: tres años de prueba.**"))
display(binarias[(binarias.cohorte=="ruta_completa")&binarias.modelo.isin(
    ["Poisson_clima","GradientBoosting_clima","RandomForest_clima"])][
    ["anio_prueba","modelo","accuracy","precision","recall","f1","roc_auc","pr_auc_ap"]].round(6))
nombre_aux=candidata if candidata in set(b2024.modelo) else "Poisson_clima"
bc=b2024[b2024.modelo==nombre_aux].iloc[0]
matriz=pd.DataFrame([[int(bc.tn),int(bc.fp)],[int(bc.fn),int(bc.tp)]],
    index=["Real: ningún siniestro","Real: al menos uno"],columns=["Predicho: ningún siniestro","Predicho: al menos uno"])
display(Markdown(f"**Matriz de confusión: {nombre_aux}, prueba 2024.**"));display(matriz)
display(Markdown(f"La prevalencia observada es **{bc.prevalencia:.3%}**. Predecir siempre cero obtiene accuracy **{bc.accuracy_siempre_cero:.3%}**, "
    "pero recall y F1 iguales a cero. "
    f"Para **{nombre_aux}**, con el umbral fijado en entrenamiento, accuracy es **{bc.accuracy:.3%}**, precision **{bc.precision:.3%}**, "
    f"recall **{bc.recall:.3%}** y F1 **{bc.f1:.4f}**. ROC-AUC es **{bc.roc_auc:.4f}** y average precision **{bc.pr_auc_ap:.5f}**. "
    "La accuracy aislada favorecería una solución que no identifica eventos; por eso no se utiliza para seleccionar el modelo de conteos."))
''')
    code('''
fig,ax=plt.subplots(1,2,figsize=(12,4.6),constrained_layout=True)
for nombre in ["M1","Poisson_clima","GradientBoosting_clima","RandomForest_clima"]:
    bm=b2024[b2024.modelo==nombre].iloc[0]
    for j,tipo in enumerate(["ROC","PR"]):
        d=curvas_binarias[(curvas_binarias.modelo==nombre)&(curvas_binarias.curva==tipo)]
        if tipo=="ROC":ax[j].plot(d.x,d.y,label=f"{nombre} · AUC {bm.roc_auc:.3f}")
        else:
            d=d[d.y>0];ax[j].plot(d.x,d.y,label=f"{nombre} · AP {bm.pr_auc_ap:.4f}")
ax[0].plot([0,1],[0,1],"--",color="gray",label="Score sin discriminación")
ax[0].set(title="ROC · prueba 2024",xlabel="Tasa de falsos positivos",ylabel="Recall",xlim=(0,1),ylim=(0,1))
ax[1].axhline(bc.prevalencia,ls="--",color="gray",label="Prevalencia de positivos")
ax[1].set(title="Precisión–recall · prueba 2024",xlabel="Recall",ylabel="Precision (escala logarítmica)",xlim=(0,1),yscale="log",ylim=(1e-5,1))
for a in ax:a.legend(fontsize=7);a.grid(alpha=.2)
mostrar(fig)
print("En la gráfica PR logarítmica se omiten los puntos de precisión cero; las áreas usan todos los datos.")
''')
    md('''
La curva ROC puede parecer favorable aun cuando la precisión de las alertas sea
baja, porque los negativos dominan. La curva PR y la prevalencia permiten ver ese
problema. Estas métricas describen celdas con/sin evento, mientras que captura y
MAE responden a la priorización y a los conteos. Ninguna de ellas demuestra por sí
sola que el sistema permita prevenir un siniestro individual.
''')
    md('''
## 13. Calibración de conteos y efecto de la tendencia

El ranking y la escala de los conteos son problemas distintos. Evaluamos una
variante que multiplica las predicciones por el O/E fuera de muestra del año anterior.
El factor de 2023 procede de 2022, y el de 2024 de 2023. Así evitamos corregir una
predicción utilizando el resultado que intentamos predecir.

Un factor global positivo conserva el orden y la captura. Puede mejorar MAE y,
aun así, desplazar el sesgo al otro lado de O/E=1. La tendencia anual también
extrapola fuera del entrenamiento; observamos su coeficiente, sin atribuirle
causalmente toda la diferencia entre años.
''')
    code('''
display(recalibracion[["anio_prueba","ajuste","anio_factor","factor","observado_esperado","mae_12h_calendario","captura5"]].round(5))
for anio in [2023,2024]:
    d=recalibracion[recalibracion.anio_prueba==anio].set_index("ajuste")
    assert d.loc["recalibrado","anio_factor"]==anio-1
    np.testing.assert_allclose(d.loc["original","captura5"],d.loc["recalibrado","captura5"])
cal=pd.read_csv(SALIDA/"calibracion.csv")
fig,ax=plt.subplots(figsize=(7,4.5),constrained_layout=True)
for fam in GRILLAS:
    d=cal[(cal.anio_prueba==2024)&(cal.cohorte=="ruta_completa")&(cal.modelo==fam+"_clima")]
    ax.plot(d.esperados,d.observados,"o-",label=fam)
maximo=cal[(cal.anio_prueba==2024)&(cal.cohorte=="ruta_completa")][["esperados","observados"]].to_numpy().max()
ax.plot([0,maximo],[0,maximo],"--",color="gray",label="Igualdad observado/esperado")
ax.set(xlabel="Esperados por decil",ylabel="Observados por decil",title="Calibración por deciles · 2024")
ax.legend();mostrar(fig)
rc2024=recalibracion[(recalibracion.anio_prueba==2024)&(recalibracion.ajuste=="recalibrado")].iloc[0]
display(Markdown(f"La variante recalibrada de 2024 obtiene O/E **{rc2024.observado_esperado:.3f}** y MAE del total por turno **{rc2024.mae_12h_calendario:.3f}**. "
    "El resultado se compara con la variante original, sin elegir entre ambas mirando este año de prueba."))
''')
    md('''
## 14. Interpretación del modelo y ejemplo de turno

Para interpretar Poisson comparamos combinaciones observadas de 2024 que solo
difieren en un atributo. Como el modelo es aditivo y log-lineal, una categoría
multiplica la tasa por el mismo factor en todas esas combinaciones. Son asociaciones
condicionales del modelo; no son efectos causales y no tienen intervalos de
confianza de coeficientes en esta entrega.

El artefacto evaluado en 2024 se ajustó hasta 2023. El reajustado con 2020–2024
incorpora todos los eventos y no tiene una prueba futura. Mantener esas versiones
separadas evita presentar un ajuste sobre todos los datos como validación.
''')
    code('''
modelo_poisson=joblib.load(SALIDA/"artefactos/ruta_completa_Poisson_clima_2024.joblib")
k24=agrupar_modelado(datos,np.arange(len(referencia)),2024)[0]
f24=atributos(k24,datos)
coefs=modelo_poisson.coef
cats=modelo_poisson.transformador.named_transformers_["categorias"].categories_
valores={};offset=0
for columna,categorias in enumerate(cats):
    valores[columna]=dict(zip(categorias,coefs[offset:offset+len(categorias)]));offset+=len(categorias)
filas_contraste=[]
for j,nombre,ref,alternativas in [(5,"Lluvia",0,[1,2]),(4,"Posición festiva",0,[1,2,3]),(1,"Hora",12,[2,8,18])]:
    for nivel in alternativas:
        filas_contraste.append({"Variable":nombre,"Referencia":ref,"Comparado":nivel,
            "Razón de tasas":float(np.exp(valores[j][nivel]-valores[j][ref]))})
display(pd.DataFrame(filas_contraste).round(4))
mu24,yy24,e24=expandir_prediccion(k24,modelo_poisson.predict_rate(f24),datos,np.arange(len(referencia)),[2024])
from evaluacion import pesos_seleccion
horas24=datos["tiempo"][datos["tiempo"].year==2024]
j=int(np.flatnonzero(horas24==pd.Timestamp("2024-07-12 12:00"))[0])
mu_turno=mu24[:,j:j+12].sum(axis=1);y_turno=yy24[:,j:j+12].sum(axis=1)
peso=pesos_seleccion(mu_turno,np.ones(len(referencia)),.05)
ejemplo=pd.DataFrame({"km_inicio":referencia.tramo,"esperados_12h":mu_turno,"observados_12h":y_turno,"peso_presupuesto":peso})
display(ejemplo[ejemplo.peso_presupuesto>0].sort_values("esperados_12h",ascending=False).round(5))
print(f"Turno ilustrativo 12/07/2024 12:00–24:00: {mu_turno.sum():.3f} esperados y {int(y_turno.sum())} observados en toda la ruta.")
''')
    md('''
La lluvia de categoría 2 corresponde a ≥0,5 mm/h; la categoría 1, a 0,1–0,5 con
límite superior excluido. Las posiciones festivas 1, 2 y 3 son inicio, intermedio
y final. Una razón mayor que uno indica un conteo esperado mayor que la referencia,
no mayor riesgo por conductor. La circulación no observada puede contribuir a los
patrones horarios y festivos.

El turno anterior es ilustrativo, no una estimación de precisión basada en un caso.
Su presupuesto admite 12 tramos completos y parte de otro; un plan real de 12
tramos enteros tiene un presupuesto ligeramente menor y debe evaluarse como tal.
''')
    md('''
## 15. Sensibilidad urbana y de los umbrales de lluvia

La primera comprobación es descriptiva: observamos la etiqueta urbana por año antes
de excluirla. En este histórico los urbanos aparecen solo en el entrenamiento
inicial. Esa discontinuidad impide medir generalización urbana en los años de prueba;
no significa que desaparezcan las zonas urbanas físicas de la ruta.

A continuación repetimos ajustes exploratorios de Poisson: excluimos los eventos
etiquetados urbanos del entrenamiento y probamos cortes de lluvia A (0,05/0,5) y
B (0,1/1,0). Los cortes originales son 0,1/0,5 mm/h. Se mantienen dominio, referencia,
particiones y penalización elegida en cada fold. No se elige el escenario que mejor
resulte en 2024 ni se cambia la candidata del experimento principal.
''')
    code('''
zonas=eventos.ZONA.fillna("DESCONOCIDA").str.strip().str.upper()
display(pd.crosstab(eventos.anio,zonas))
from modelos_conteo import ModeloConteo
from validar_ruta5 import resumen
_,y_rural,_=grilla_civil(eventos[zonas=="RURAL"],referencia.tramo.to_numpy())
y_rural[:,datos["expo"]==0]=0
celdas={tuple(v):i for i,v in enumerate(clima["celdas"])}
idx=[celdas[tuple(v)] for v in np.round(referencia[["lat","lon"]].to_numpy()/.25)*.25]
p_tramo=clima["precip"][idx]

def datos_con_cortes(cortes):
    lluvia=np.digitize(p_tramo,cortes);lluvia[:,datos["expo"]==0]=0
    n_periodos=datos["dims"][-1]
    anterior=(datos["codigo"]//n_periodos)%3
    return dict(datos,codigo=datos["codigo"]+(lluvia-anterior)*n_periodos)

def ajustar_sensibilidad(d,anio,parametros):
    filas=np.arange(len(referencia))
    grupos=[agrupar_modelado(d,filas,a) for a in range(2020,anio)]
    k,y,e=(np.concatenate([g[i] for g in grupos]) for i in range(3))
    orden=np.argsort(k);k,y,e=k[orden],y[orden],e[orden]
    with threadpool_limits(limits=2):
        m=ModeloConteo("Poisson","clima",parametros).fit(atributos(k,d),y,e)
        kt=agrupar_modelado(d,filas,anio)[0]
        mu,yt,et=expandir_prediccion(kt,m.predict_rate(atributos(kt,d)),d,filas,[anio])
    return resumen(yt,mu,et)

sensibilidad_filas=[]
for anio in [2022,2023,2024]:
    fila=seleccion[(seleccion.anio_prueba==anio)&(seleccion.cohorte=="ruta_completa")&
        (seleccion.familia=="Poisson")&(seleccion.variante=="clima")].iloc[0]
    params=json.loads(fila.parametros)
    base=prueba[(prueba.anio_prueba==anio)&(prueba.modelo=="Poisson_clima")].iloc[0]
    sensibilidad_filas.append({"anio":anio,"escenario":"Original",**{k:base[k] for k in ["captura5","captura5_turno","observado_esperado","mae_12h_calendario"]}})
    for nombre,d in [("A: 0,05/0,5",datos_con_cortes([.05,.5])),
                     ("B: 0,1/1,0",datos_con_cortes([.1,1.])),
                     ("Objetivo rural",dict(datos,y=y_rural))]:
        print("Ajustando sensibilidad:",anio,nombre,flush=True)
        r=ajustar_sensibilidad(d,anio,params)
        sensibilidad_filas.append({"anio":anio,"escenario":nombre,**r})
sensibilidad=pd.DataFrame(sensibilidad_filas)
sensibilidad.to_csv(SALIDA/"sensibilidad.csv",index=False)
display(sensibilidad[["anio","escenario","captura5","captura5_turno","observado_esperado","mae_12h_calendario"]].round(5))
''')
    code('''
fig,ax=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
for nombre,d in sensibilidad.groupby("escenario",sort=False):
    ax[0].plot(d.anio,d.captura5*100,"o-",label=nombre)
    ax[1].plot(d.anio,d.mae_12h_calendario,"o-",label=nombre)
ax[0].set(title="Sensibilidad de la captura global",ylabel="Captura al 5 % (%)",xticks=[2022,2023,2024])
ax[1].set(title="Sensibilidad del conteo total",ylabel="MAE total por turno",xticks=[2022,2023,2024])
for a in ax:a.set_xlabel("Año de prueba");a.legend(fontsize=8);a.grid(alpha=.2)
mostrar(fig)
base_s=sensibilidad[sensibilidad.escenario=="Original"].set_index("anio")
b_s=sensibilidad[sensibilidad.escenario=="B: 0,1/1,0"].set_index("anio")
diferencia_s=(b_s.captura5-base_s.captura5)*100
r_s=sensibilidad[sensibilidad.escenario=="Objetivo rural"].set_index("anio")
display(Markdown("La alternativa B cambia la captura global en **"+", ".join(f"{a}: {v:+.3f} pp" for a,v in diferencia_s.items())+"**. "
    "Estos resultados son descriptivos, sin IC para los reajustes de sensibilidad. El objetivo rural cambia la población de entrenamiento; "
    "no permite atribuir los cambios al carácter urbano físico del tramo ni sustituye la validación principal."))
''')
    md('''
## 16. Ampliación investigada a 2025

Se revisaron fuentes CONASET 2025 y se intentó recuperar la pertenencia vial y el
kilometraje mediante geometría MOP, controles de 2024 y direcciones textuales.
La información recuperada no permitió acreditar una cohorte comparable a Ruta 5 Sur.
Una referencia numérica en la dirección no demuestra que su unidad sea km, y una
vía cercana no prueba que el siniestro pertenezca a ella.

Por ello conservamos 2020–2024. No se incorporó una selección parcial de 2025 como
si fuera el año completo. La siguiente tabla resume el diagnóstico de fuentes
realizado durante el proyecto; no participa en el entrenamiento ni en la evaluación
anterior. Esta limitación es de ubicación/comparabilidad, no una demostración de fuga
de información por el mero hecho de usar datos de otro año.
''')
    code('''
display(pd.read_csv(RAIZ/"resultados/cierre_ubicacion_2025/estados_texto_2025.csv"))
assert eventos.anio.max()==2024
print("Los modelos de esta ejecución utilizan exclusivamente 2020–2024.")
''')
    md('''
## 17. Ejemplo de aplicación a una ventana de 12 horas

La salida del modelo permite sumar tasas horarias por tramo y priorizar una ventana.
A modo de demostración reproducible, usamos las primeras 12 horas de un turno
histórico de prueba y mantenemos 12 tramos enteros. Ese presupuesto es 12/255 =
4,71 %, ligeramente menor que el 5 % fraccionario de las métricas principales.
No se interpreta este ejemplo como una emisión operativa nueva.

El proyecto también implementó un piloto experimental con pronóstico capturado
antes de emitir. Su evaluación futura requiere todos los siniestros observados del
horizonte, con ubicación y hora verificables. No contar con reportes no autoriza a
suponer cero eventos. El notebook acredita modelado retrospectivo y funcionamiento
del mecanismo de priorización, no un servicio operativo validado.
''')
    code('''
plan12=ejemplo.sort_values(["esperados_12h","km_inicio"],ascending=[False,True]).head(12).copy()
plan12["prioridad"]=np.arange(1,13)
display(plan12[["prioridad","km_inicio","esperados_12h","observados_12h"]].round(5))
print(f"Presupuesto entero: {12/len(referencia):.2%} de los tramos.")
print(f"Conteo esperado de toda la ruta: {mu_turno.sum():.3f}; total observado: {int(y_turno.sum())}.")
''')
    md('''
Para pasar de este ejemplo histórico al piloto de las próximas horas hay que
construir el calendario vigente, capturar un pronóstico meteorológico antes de
emitir y congelar predicciones y prioridades. Cambiar reanálisis por pronóstico y
extrapolar a un año nuevo puede alterar el desempeño; ambas cosas requieren
validación propia. La referencia espacial aproximada tampoco define puntos físicos
de despliegue ni restricciones de traslado del patrullaje.
''')
    md('''
## 18. Conclusiones calculadas con los resultados de esta ejecución

Las conclusiones siguientes se generan después de entrenar, evaluar y comparar.
Si cambian los resultados al repetir el notebook, el texto numérico cambia con ellos.
La regla de selección y las limitaciones metodológicas permanecen explícitas.
''')
    code('''
fc=aportes[aportes.aporte=="flujo"]
familias_consistentes=[]
for fam in GRILLAS:
    d=fc[fc.modelo==fam+"_clima_flujo"]
    if len(d)==3 and (d.ic95_inf_pp>0).all():familias_consistentes.append(fam)
texto_flujo=("Ninguna familia tiene un intervalo de aporte del flujo completamente positivo en los tres años."
             if not familias_consistentes else "Las familias con mejora positiva en los tres años son: "+", ".join(familias_consistentes)+".")
texto_sesgo=("sobreestima" if c2024.observado_esperado<1 else "subestima")
conclusiones=f''' + '"""' + '''
1. **Priorización histórica.** La regla temporal seleccionó **{candidata}**. En 2024 su captura global fue **{c2024.captura5:.2%}**, frente a **{base2024.captura5:.2%}** de M1. La diferencia fue **{intervalo2024.diferencia_pp:.2f} pp**, IC95 % **[{intervalo2024.ic95_inf_pp:.2f}; {intervalo2024.ic95_sup_pp:.2f}]**.
2. **Decisión por turno.** Con ubicación fija durante 12 horas, la candidata capturó **{c2024.captura5_turno:.2%}**. La ganancia global no equivale a la de un patrullaje fijo.
3. **Cantidad esperada.** O/E fue **{c2024.observado_esperado:.3f}**: el modelo {texto_sesgo} el total de ese año. MAE fue **{c2024.mae_12h_calendario:.3f}** siniestros por turno en toda la cohorte. La variante recalibrada obtuvo O/E **{rc2024.observado_esperado:.3f}** y MAE **{rc2024.mae_12h_calendario:.3f}**, sin modificar el ranking.
4. **Circulación.** {texto_flujo} El proxy cubre **{int(datos['cubiertos'].sum())}/{len(referencia)}** tramos; no permite estimar riesgo por vehículo-km ni acreditar disponibilidad histórica de los anexos.
5. **Diagnóstico binario.** Para **{nombre_aux}**, ROC-AUC fue **{bc.roc_auc:.4f}**, AP **{bc.pr_auc_ap:.5f}** y F1 **{bc.f1:.4f}** con umbral de entrenamiento. La referencia siempre-cero tiene accuracy **{bc.accuracy_siempre_cero:.3%}** y recall cero; por eso la accuracy no resume la utilidad para detectar eventos.
6. **Robustez y alcance.** Las sensibilidades se muestran con sus métricas y no se usan para reseleccionar con 2024. La discontinuidad de etiquetas urbanas limita su interpretación. Los resultados describen Ruta 5 Sur 2020–2024; no validan otras rutas, 2025 ni un servicio predictivo operativo.
''' + '"""' + '''
display(Markdown(conclusiones))
''')
    md('''
### Limitaciones y próximos pasos

El reanálisis meteorológico no acredita un pronóstico disponible en la fecha de
decisión. El proxy de circulación no reemplaza la exposición real. Las etiquetas
urbanas cambian entre períodos y la asignación vial de 2025 no quedó resuelta.
La evaluación de 2024 es histórica reutilizada, no una prueba intacta. Los intervalos
mantienen fijas las predicciones y no corrigen múltiples comparaciones.

El siguiente paso científico es evaluar con un año nuevo correctamente ubicado y
con fuentes disponibles antes de decidir, incluyendo exposición vehicular acreditada.
Para el despliegue se necesitan observaciones completas, calendario actualizado,
pronósticos emitidos y evaluación prospectiva. No se deducen causalidad, riesgo
individual ni siniestros evitados de estos resultados.

### Referencias y reproducibilidad

- CONASET: Observatorio de Datos y Estadística y registros geográficos de siniestros.
- Open-Meteo: ERA5 Historical Weather API, precipitación horaria.
- Dirección General de Concesiones: anexos trimestrales 2023T4 y 2024T4.
- MOP/Vialidad: Plan Nacional de Censos Viales y límites de contratos citados en el código.
- Pauta del curso, **Proyecto Semestral de Data Science**, Etapa III: comparación,
  selección, validación con métricas apropiadas, interpretación y conexión con el problema.
- Documentación de scikit-learn: [evaluación de modelos](https://scikit-learn.org/stable/modules/model_evaluation.html).

Los archivos incorporados tienen sus hashes en `MANIFIESTO_ENTREGA.json`; la corrida
registra parámetros, búsqueda, selección, diagnósticos, versiones y artefactos.
El código y los datos extraídos se pueden inspeccionar sin credenciales personales.
Para repetir todo el trabajo, reiniciar el kernel y ejecutar el notebook completo.
''')
    code('''
for nombre,sha in manifest["archivos_sha256"].items():
    assert hashlib.sha256((RAIZ/nombre).read_bytes()).hexdigest()==sha,nombre
assert len(busqueda)==60 and len(metricas)==114 and len(seleccion)==36
assert candidata==reajuste["modelo"]
assert all(a.get("convergio",True) for a in auditoria["ajustes"]+reajuste["ajustes"])
reproduccion={"entrenamiento_completo":True,"configuraciones_ajustadas":len(busqueda),
    "familias":list(GRILLAS),"metricas_calculadas":len(metricas),"modelo_seleccionado":candidata,
    "reajuste_final_sin_prueba_futura":True,"datos_incorporados_verificados":True,
    "minutos_entrenamiento":round(minutos_ajuste,2),
    "directorio_resultados":str(SALIDA),"fecha_ejecucion_utc":pd.Timestamp.now(tz="UTC").isoformat(),
    "modelos_preajustados_incorporados":False,"sha256_paquete":hashlib.sha256(paquete).hexdigest(),
    "versiones":{n:metadata.version(n) for n in ["numpy","pandas","scipy","scikit-learn","matplotlib","joblib"]}}
(SALIDA/"resumen_ejecucion.json").write_text(json.dumps(reproduccion,ensure_ascii=False,indent=2)+"\\n")
display(JSON(reproduccion))
print("CIERRE_NOTEBOOK_CORRECTO: modelos entrenados, comparaciones y conclusiones calculadas.")
''')
    for i,x in enumerate(c):x['id']=f'entrega-definitiva-{i:03d}'
    return c


def construir():
    return nbf.v4.new_notebook(cells=agregar_analisis(prefijo()),metadata={
        'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'language_info':{'name':'python'},'proyecto':{'tipo':'Entrega autocontenida con entrenamiento completo'}})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,default=RAIZ/'notebooks/EntregaFinal_Proyecto_DS.ipynb')
    a=p.parse_args();nb=construir();nbf.validate(nb);nbf.write(nb,a.salida)
    print('Notebook generado:',a.salida,len(nb.cells),'celdas')

if __name__=='__main__':main()
