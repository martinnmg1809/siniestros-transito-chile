---
title: "Riesgo de siniestros de tránsito en carreteras de Chile"
subtitle: "Etapa I — Propuesta y Definición del Problema"
author: "Proyecto Semestral de Data Science"
date: "11 de septiembre de 2026"
lang: es
---

**Integrantes del equipo:** _(completar: 4 a 5 integrantes)_

**Repositorio del proyecto:** `github.com/martinnmg1809/siniestros-transito-chile`

**Prototipo funcional:** `martinnmg1809.github.io/siniestros-transito-chile`

## Contenido

1. Resumen de la propuesta
2. Contexto del problema
3. Justificación
4. Definición del problema
5. Enfoque propuesto
6. Objetivos del proyecto
7. Evidencia preliminar de factibilidad
8. Datos, riesgos y limitaciones
9. Plan de trabajo
10. Fuentes

\newpage

# 1. Resumen de la propuesta

En Chile mueren cerca de 1.400 personas al año en siniestros de tránsito. La respuesta
institucional se apoya en mapas de puntos críticos que se publican una vez al año y que,
por construcción, describen **dónde** ocurrieron los siniestros pero no **cuándo** el
riesgo se eleva.

Este proyecto propone estimar el **número esperado de siniestros por tramo de carretera y
por hora**, combinando el registro histórico georreferenciado de Carabineros (publicado por
CONASET) con variables de contexto conocidas por anticipado: pronóstico de precipitación,
hora del día, día de la semana y calendario de feriados.

El problema se formula como una **regresión de conteos sobre datos espacio-temporales**, no
como una clasificación. Esa decisión es el eje conceptual de la propuesta y se justifica en
la sección 5: un siniestro en un tramo y hora concretos es un evento con probabilidad
cercana al 0,13 %, de modo que cualquier clasificador binario alcanzaría una exactitud
superior al 99 % prediciendo siempre "no habrá siniestro", sin aportar información alguna.

El entregable final es doble: un modelo validado temporalmente y una interfaz que traduce
sus estimaciones a una decisión operativa concreta — *qué tramos vigilar en las próximas
doce horas*.

\newpage

# 2. Contexto del problema

## 2.1 Dominio de aplicación

El proyecto se sitúa en la **seguridad vial interurbana chilena**, específicamente en la red
de carreteras y autopistas concesionadas administradas por el Ministerio de Obras Públicas
y fiscalizadas por Carabineros de Chile.

La magnitud del fenómeno es la siguiente, según los informes nacionales de CONASET:

| Año  | Siniestros | Fallecidos | Lesionados |
|:-----|-----------:|-----------:|-----------:|
| 2023 | 78.238     | 1.635      | 45.679     |
| 2024 | 75.653     | 1.439      | 42.400     |

La cifra de fallecidos ha bajado un 12 % entre 2023 y 2024, pero se mantiene en un orden de
magnitud que sitúa al tránsito entre las principales causas de muerte por causas externas
en el país.

## 2.2 Por qué la red interurbana

De los 436.521 siniestros georreferenciados que CONASET publica para el período 2020–2025,
96.290 ocurren en **zona rural** y 340.231 en zona urbana. Aunque la zona urbana concentra
más eventos, la red interurbana presenta tres características que la hacen un dominio más
tratable y más relevante para este proyecto:

1. **La letalidad es mayor.** Las velocidades de operación en carretera son sustancialmente
   más altas, de modo que un mismo número de siniestros produce más fallecidos.
2. **La geometría es unidimensional.** Una carretera se describe por su kilometraje, lo que
   permite una referenciación lineal precisa y una unidad de análisis natural: el tramo. En
   zona urbana el evento ocurre en una red de intersecciones cuya topología es mucho más
   compleja de modelar.
3. **La intervención es concentrable.** Un patrullaje o una señalización variable desplegada
   en un tramo específico de carretera cubre la totalidad del flujo que circula por él, algo
   que no ocurre en una malla urbana con múltiples rutas alternativas.

## 2.3 La problemática concreta

CONASET publica hoy capas de **puntos críticos** con periodicidad anual. Esta información es
valiosa pero tiene una limitación estructural: es **estática**. Un tramo aparece marcado como
crítico porque históricamente acumuló siniestros, y esa marca es la misma un martes a las
3 de la madrugada con la calzada seca que un viernes a las 18:00 bajo lluvia.

La consecuencia práctica es que la asignación de recursos de fiscalización no puede
priorizarse en el tiempo. Se sabe *dónde* mirar, pero no *cuándo* mirar con más atención.

Esta brecha existe pese a que las variables que modulan el riesgo son **conocidas con
antelación**: el pronóstico meteorológico está disponible con horas o días de anticipación,
y la hora, el día de la semana y el calendario de feriados son deterministas.

\newpage

# 3. Justificación

## 3.1 Relevancia

La justificación del proyecto no reside en predecir siniestros individuales — algo que la
sección 4 descarta explícitamente — sino en **mejorar la eficiencia con que se asignan
recursos escasos de fiscalización**.

El argumento es cuantificable. Si un cuerpo de fiscalización puede cubrir una fracción
limitada de la red en un turno determinado, la pregunta operativa es qué fracción de los
siniestros reales quedaría cubierta por esa asignación. Nuestra evidencia preliminar
(sección 7) indica que:

- Con la información estática actual — solo la ubicación histórica — vigilar el 5 % de las
  horas-tramo disponibles cubre el **14,9 %** de los siniestros reales del año siguiente.
- Incorporando hora, día, feriado y pronóstico de lluvia, esa cobertura sube al **19,2 %**.

La diferencia es una mejora relativa del 28 % en la eficiencia de cobertura, obtenida **sin
desplegar un solo recurso adicional**: únicamente reordenando cuándo se despliegan los que
ya existen.

## 3.2 Beneficiarios e impacto esperado

| Actor                                     | Uso concreto de la herramienta |
|:------------------------------------------|:-------------------------------|
| Carabineros (SIAT y unidades de tránsito) | Priorización temporal de patrullajes y controles preventivos |
| Concesionarias viales | Anticipación de despliegue de asistencia en ruta y señalización variable |
| CONASET / MOP | Complemento dinámico a los mapas anuales de puntos críticos |
| Conductores | Información de riesgo por tramo antes de emprender un viaje |

## 3.3 Por qué este proyecto es viable ahora

Tres condiciones habilitantes se cumplen simultáneamente, y ninguna de ellas era cierta hace
algunos años:

1. **Los datos están abiertos y georreferenciados.** CONASET publica los registros de
   Carabineros en servicios ArcGIS de acceso público, con coordenadas y kilometraje de ruta,
   sin necesidad de convenios ni credenciales.
2. **El clima histórico y pronosticado es accesible sin costo.** Existen APIs de reanálisis
   meteorológico con resolución horaria y cobertura global que permiten reconstruir las
   condiciones de cada siniestro pasado y consultar el pronóstico de las próximas horas.
3. **La entrega no requiere infraestructura.** El modelo, una vez ajustado, se reduce a un
   conjunto reducido de coeficientes, lo que permite publicar el resultado como una página
   estática sin servidor ni base de datos.

\newpage

# 4. Definición del problema

## 4.1 Pregunta central

> **¿Cuántos siniestros de tránsito se espera que ocurran en cada tramo de una carretera
> chilena durante las próximas doce horas, y qué tramos concentran el riesgo, dadas la hora,
> el día de la semana, el calendario de feriados y el pronóstico de precipitación?**

## 4.2 Unidad de análisis

La unidad de análisis es la **celda tramo × hora**: un segmento de carretera de longitud
fija (5 km como caso base) durante una hora calendario determinada. Para la Ruta 5 Sur, el
período 2020–2024 genera 251 tramos × 43.848 horas ≈ **11,0 millones de celdas**.

## 4.3 Qué se busca resolver, y qué no

Delimitar esto es esencial para la coherencia del proyecto, y constituye la principal
decisión conceptual de la propuesta.

**El proyecto SÍ busca responder:**

- Cuántos siniestros esperar en una ruta completa en una ventana de doce horas.
- Qué tramos concentran el riesgo dentro de esa ventana, y en qué proporción respecto del
  tramo promedio.
- Cuánto eleva el riesgo cada factor de contexto: lluvia, hora punta, día de salida a un
  fin de semana largo.

**El proyecto NO busca responder:**

- Si un tramo y hora específicos tendrán un siniestro. La tasa base es de **0,133 % por
  tramo-hora**; en toda la Ruta 5 Sur se esperan **4,0 siniestros en doce horas** repartidos
  a lo largo de 1.226 km. Una afirmación del tipo "mañana a las 15:20 en el km 193 habrá una
  colisión" no es alcanzable con estos datos, ni con ningún otro conjunto de datos
  observacionales de esta naturaleza.
- Las causas del siniestro. El registro contiene una causa asignada por el funcionario que
  concurrió al lugar, pero el diseño observacional no permite inferencia causal.

Esta delimitación no es una limitación del método, sino una propiedad del fenómeno: los
siniestros son eventos raros en el espacio-tiempo. Reconocerlo explícitamente es lo que
permite formular un objetivo que sí es alcanzable y verificable.

\newpage

# 5. Enfoque propuesto

## 5.1 Tipo de problema de Ciencia de Datos

El problema se formula como una **regresión de conteos sobre datos espacio-temporales**,
mediante un modelo lineal generalizado de Poisson con enlace logarítmico y término de
exposición (*offset*).

Formalmente, para la celda correspondiente al tramo $s$ y la hora $t$:

$$Y_{st} \sim \text{Poisson}(\lambda_{st}), \qquad
\log \lambda_{st} = \alpha_s + \beta_{h(t)} + \gamma_{d(t)} + \delta_{m(t)} + \phi_{f(t)} + \psi_{c(s,t)} + \log E_{st}$$

donde $\alpha_s$ es el efecto del tramo, $\beta$ la hora del día, $\gamma$ el día de la
semana, $\delta$ el mes, $\phi$ la posición respecto de un feriado, $\psi$ la categoría de
precipitación y $E_{st}$ la exposición en horas.

## 5.2 Justificación del enfoque, frente a las alternativas

**Por qué no clasificación binaria.** Sería el enfoque intuitivo — "¿habrá o no habrá
siniestro?" — y es el que descartamos con mayor convicción. Con una tasa base de 0,133 %,
un clasificador que responda siempre "no" alcanza un 99,87 % de exactitud y un AUC que
puede parecer razonable, sin contener información útil. Además, la clasificación descarta
información: dos celdas con riesgo esperado de 0,001 y 0,05 siniestros son ambas "clase
negativa", cuando su riesgo difiere en un factor de cincuenta. La magnitud es precisamente
lo que interesa a quien asigna recursos.

**Por qué no series de tiempo puras.** Un modelo ARIMA o similar sobre el conteo agregado de
la ruta capturaría la estacionalidad temporal pero **perdería la dimensión espacial**, que
es donde nuestra evidencia preliminar indica que reside la mayor parte de la señal. La
pregunta operativa no es cuántos siniestros habrá en la ruta, sino en qué tramo.

**Por qué no clustering.** Es un enfoque no supervisado y aquí sí existe una variable
respuesta observada — el conteo de siniestros. Puede ser útil como análisis exploratorio
complementario para agrupar tramos con perfiles de riesgo similares, pero no responde la
pregunta central.

**Por qué Poisson y no otra regresión.** La variable respuesta es un conteo entero no
negativo, con gran mayoría de ceros, y el término de exposición permite modelar celdas con
distinta cantidad de horas observadas. Se contrastará contra una **binomial negativa** para
evaluar sobredispersión, y contra un ***gradient boosting* con objetivo de Poisson** para
capturar interacciones no aditivas.

## 5.3 Marco metodológico

Se adopta **CRISP-DM**, por tres razones concretas:

1. Su primera fase es *Business Understanding*, que en este proyecto es la fase crítica: la
   decisión de formular el problema como conteos y no como clasificación es una decisión de
   entendimiento del dominio, no técnica.
2. Es **iterativo entre preparación de datos y modelado**, lo cual es necesario aquí: los
   problemas de calidad del kilometraje descritos en la sección 8 solo se hicieron visibles
   al intentar modelar.
3. Su fase de *Deployment* es un entregable explícito, coherente con que el resultado del
   proyecto sea una interfaz operativa y no solo un modelo.

## 5.4 Estrategia de validación

Dos decisiones metodológicas definen la validación:

**Partición temporal, no aleatoria.** Se entrena con 2020–2023 y se evalúa con 2024. Una
partición aleatoria sobre datos con autocorrelación espacio-temporal filtraría información
del futuro al conjunto de entrenamiento e inflaría artificialmente las métricas.

**Métrica operativa por sobre métrica estadística.** Además de la desvianza de Poisson, la
métrica principal es la **curva de captura**: *si se dedica el N % de las horas-tramo
disponibles a vigilar las de mayor riesgo estimado, qué porcentaje de los siniestros reales
del período de prueba queda cubierto*. Esta métrica traduce directamente el desempeño del
modelo a la decisión que se busca apoyar.

**El baseline exigente es el mapa estático.** No basta con superar al azar. El modelo debe
superar a un modelo que use **únicamente la ubicación del tramo**, porque ese es el estado
del arte actual — es lo que ya publica CONASET. Si añadir hora, clima y feriados no mejora
la captura fuera de muestra, esa capa está añadiendo ruido y no debe publicarse.

\newpage

# 6. Objetivos del proyecto

## 6.1 Objetivo general

Desarrollar y validar un sistema reproducible que estime el número esperado de siniestros de
tránsito por tramo y hora en carreteras de Chile, en función de variables de contexto
conocidas por anticipado, y comunicar sus estimaciones en una interfaz que apoye la
priorización temporal y espacial de recursos de fiscalización.

## 6.2 Objetivos específicos

Cada objetivo se acompaña de una **meta verificable** al cierre del proyecto.

| Objetivo específico                                        | Meta verificable al cierre del proyecto                     |
|:-----------------------------------------------------------|:------------------------------------------------------------|
| **OE1.** Consolidar un conjunto de datos reproducible de siniestros con ruta y kilometraje validados, a partir de las fuentes abiertas de CONASET. | Al menos 80.000 siniestros con ruta asignada; ≥ 95 % con coordenadas válidas; pipeline ejecutable de extremo a extremo con un solo comando. |
| **OE2.** Diagnosticar y corregir los problemas de calidad del campo de kilometraje, documentando el criterio aplicado. | Correlación ≥ 0,95 entre el kilometraje declarado y la posición geográfica proyectada, en toda ruta que se incorpore al modelo. |
| **OE3.** Cuantificar el efecto de las condiciones meteorológicas, la hora, el día de la semana y los feriados sobre la tasa de siniestros. | Efectos multiplicativos estimados con intervalo de confianza para cada variable, sobre la Ruta 5 Sur y al menos cuatro rutas adicionales. |
| **OE4.** Ajustar un modelo de conteos que supere de forma demostrable al baseline puramente espacial en validación temporal. | Captura en el 5 % superior de horas-tramo al menos 3 puntos porcentuales por encima del modelo de solo ubicación, evaluado sobre 2024. |
| **OE5.** Comparar al menos tres especificaciones de modelo y seleccionar una con criterio explícito. | Tabla comparativa Poisson / binomial negativa / *gradient boosting* con desvianza y curva de captura fuera de muestra. |
| **OE6.** Extender el análisis a múltiples rutas, aplicando el criterio de validación como filtro de publicación. | Al menos 5 rutas publicadas que superen el baseline estático, y documentación explícita de las rutas descartadas con su motivo. |
| **OE7.** Entregar una interfaz operativa que muestre el riesgo de las próximas 12 horas por tramo, en dos vistas complementarias. | Interfaz accesible públicamente, que se actualice con el pronóstico vigente y que degrade de forma controlada si la fuente meteorológica no responde. |
| **OE8.** Documentar de forma explícita las limitaciones del sistema y la incertidumbre de sus estimaciones. | Sección de limitaciones que aborde al menos: ausencia de flujo vehicular horario, subregistro del registro policial y error de medición de la variable meteorológica. |

\newpage

# 7. Evidencia preliminar de factibilidad

Se realizó una exploración inicial para verificar que los datos sostienen la propuesta antes
de comprometerse con ella. Los resultados de esta sección son **preliminares** y se
presentan como sustento de viabilidad, no como resultados finales del proyecto.

## 7.1 Disponibilidad de datos

| Fuente | Contenido verificado |
|:---|:---|
| CONASET — ArcGIS Hub | 436.521 siniestros georreferenciados 2020–2025, con fecha, hora, tipo, causa, ruta y kilometraje |
| CONASET — capa de feriados | Calendario 2019–2024, que distingue el día de salida, los días intermedios y el de regreso de cada fin de semana largo |
| CONASET — capas regionales 2023 | Estado atmosférico y condición de calzada observados en terreno |
| Open-Meteo | Precipitación horaria, histórica y pronosticada, sin credenciales |
| MOP — Plan Nacional de Censos | 863 puntos censales con Tránsito Medio Diario Anual por rol de ruta |

De los 82.026 siniestros con ruta asignada, la **Ruta 5 Sur** concentra 14.282 tras limpieza,
2,5 veces más que la siguiente ruta con más registros.

## 7.2 Resultados preliminares del modelo

Ajustando el modelo descrito en la sección 5 sobre la Ruta 5 Sur, con entrenamiento en
2020–2023 y prueba sobre los 2.585 siniestros de 2024:

| Modelo | Captura top 5 % | Captura top 10 % |
|:---|---:|---:|
| Tasa constante (azar) | 2,1 % | 5,7 % |
| Solo ubicación del tramo | 14,9 % | 26,3 % |
| **Modelo completo** | **19,2 %** | **30,6 %** |

**Efectos multiplicativos estimados** sobre la celda promedio:

| Variable | Efecto |
|:---|---:|
| Lluvia superior a 0,5 mm/h | **2,13×** |
| Llovizna (0,1 – 0,5 mm/h) | 1,31× |
| Hora punta (18:00) | 1,68× |
| Día de salida a un fin de semana largo | 1,19× |
| Día feriado intermedio | 0,93× |
| Madrugada (02:00) | 0,52× |
| Día de la semana (rango completo) | 0,93× – 1,10× |

Tres hallazgos preliminares orientan el trabajo restante:

1. **La componente espacial aporta la mayor parte de la señal.** El mapa estático ya
   alcanza el 14,9 % de captura. La capa dinámica añade 4,3 puntos. Es una mejora real y
   verificable, pero conviene declararla en su magnitud correcta y no sobrevenderla.
2. **La precipitación es el factor de contexto más fuerte**, por encima de la hora punta.
3. **El día de salida a un feriado es más riesgoso que el feriado mismo** (1,19× frente a
   0,93×), lo que sugiere que la variable relevante es el desplazamiento y no la fecha
   feriada en sí.

## 7.3 Una validación que arrojó resultado negativo

Se evaluó si el reanálisis meteorológico reproduce la observación de estado atmosférico
registrada por Carabineros, contrastando 6.096 siniestros de la Región del Biobío en 2023.
El acuerdo resultó **débil**: índice kappa de Cohen de 0,262 y sensibilidad de 47,2 %, es
decir, el reanálisis no detecta más de la mitad de las lluvias registradas en terreno. La
causa es estructural: el reanálisis promedia sobre celdas de aproximadamente 25 km, y la
precipitación en la zona centro-sur del país es localizada.

Este resultado obliga a una distinción conceptual que se incorpora al proyecto: **reproducir
la etiqueta observada y predecir el conteo de siniestros son dos preguntas distintas**. El
reanálisis falla en la primera y, sin embargo, la precipitación resulta el predictor más
fuerte del modelo. El error de medición atenúa el coeficiente estimado hacia 1, de modo que
el efecto real de la lluvia es probablemente mayor que el 2,13× estimado.

\newpage

# 8. Datos, riesgos y limitaciones

## 8.1 Problemas de calidad identificados

**Unidades mezcladas en el kilometraje.** En varias rutas una fracción de los registros
expresa la ubicación en metros: el valor 84.300 de la Ruta 68 corresponde en realidad al
km 84,3. Sin embargo, la Ruta 5 Sur alcanza legítimamente el km 1.226, por lo que una
corrección global destruiría sus datos. El criterio adoptado es **por ruta**: se elige la
transformación que maximiza la correlación entre el kilometraje declarado y la posición
geográfica proyectada sobre el eje de la ruta. En la Ruta 68 esa correlación pasa de 0,139
a 0,999; en la Ruta 5 Sur se mantiene en 0,998 sin transformar.

**Campo de ruta incompleto.** Los registros de 2025 existen en la base pero no tienen el
campo de ruta poblado, lo que limita el período utilizable a 2020–2024.

## 8.2 Limitaciones que se declararán en el resultado final

| Limitación | Consecuencia |
|:---|:---|
| **Ausencia de flujo vehicular horario.** El censo del MOP entrega un promedio anual por punto censal. | El modelo no puede separar "hay más vehículos a esta hora" de "conducir a esta hora es más peligroso por vehículo". Para priorizar recursos esto es indiferente; para una afirmación causal sobre el riesgo, no. |
| **Subregistro del registro policial.** La fuente son partes de Carabineros. | Los siniestros sin lesionados y aquellos donde no concurrió personal policial están subrepresentados. |
| **Error de medición de la variable meteorológica.** Sección 7.3. | Los coeficientes de precipitación están atenuados; el efecto real es probablemente mayor. |
| **Modelos no comparables entre rutas.** Cada ruta tiene su propio modelo y su propio nivel basal. | Un factor de "2,0×" en una ruta no equivale al mismo factor en otra. |

## 8.3 Riesgos del proyecto y mitigación

| Riesgo | Mitigación |
|:---|:---|
| Rutas con pocos datos producen modelos que son puro ruido | El criterio de publicación exige superar al baseline estático en validación temporal; las rutas que no lo cumplen se documentan pero no se publican |
| Dependencia de una API externa para el pronóstico | La interfaz calcula con calzada seca y lo advierte cuando la fuente no responde; el modelo sin clima conserva la mayor parte de su capacidad |
| Sobreajuste por número de parámetros de tramo | Regularización L2 sobre los efectos de tramo y validación estrictamente temporal |

\newpage

# 9. Plan de trabajo

El plan se alinea con las cuatro entregas de la asignatura y con las fases de CRISP-DM.

| Etapa | Fase CRISP-DM | Actividades principales |
|:---|:---|:---|
| **I** — Propuesta (11 sep) | *Business Understanding* | Definición del problema, formulación como regresión de conteos, objetivos medibles |
| **II** — Avance (22–26 oct) | *Data Understanding* y *Data Preparation* | Consolidación del dataset, corrección del kilometraje, análisis exploratorio, primer modelo Poisson con resultados preliminares |
| **III** — Presentación técnica (16–19 nov) | *Modeling* y *Evaluation* | Comparación Poisson / binomial negativa / *gradient boosting*, selección con criterio explícito, validación temporal, extensión a múltiples rutas |
| **IV** — Feria de Proyectos (2 dic) | *Deployment* | Interfaz operativa, póster, video resumen y comunicación a audiencia no especializada |

\newpage

# 10. Fuentes

- CONASET. *Portal de mapas y datos abiertos.* `mapas-conaset.opendata.arcgis.com`
- CONASET. *Informe Nacional de Siniestros de Tránsito en Chile 2024.*
- CONASET. *Informe Nacional de Siniestros de Tránsito en Chile 2023.*
- Carabineros de Chile. *Anuario Estadístico de Accidentes en el Tránsito* (sistema SIEC 2).
- Ministerio de Obras Públicas, Dirección de Vialidad. *Plan Nacional de Censos Viales.*
- Open-Meteo. *Historical Weather API* y *Forecast API* (reanálisis ERA5).
- Dirección Meteorológica de Chile. *Portal de Servicios Climáticos.*
