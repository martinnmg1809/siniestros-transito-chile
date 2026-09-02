# Factibilidad: análisis y predicción de siniestros de tránsito en autopistas de Chile

Informe de factibilidad basado en **datos reales verificados el 2026-09-01** consultando
directamente las APIs públicas. Todas las cifras de este documento fueron obtenidas
ejecutando consultas contra los servicios, no de documentación.

---

## 1. Resumen ejecutivo

| Pregunta | Respuesta |
|---|---|
| ¿Hay datos suficientes? | **Sí.** 436.521 siniestros georreferenciados 2020–2025, acceso público sin API key. |
| ¿Autopista con más datos? | **Ruta 5 Sur** — 14.430 siniestros (2020–2024), 20.980 sumando Ruta 5 Norte y Ruta 57. |
| ¿Qué es más factible construir? | **Mapa de puntos calientes por kilómetro** (alta factibilidad, resultado garantizado). |
| ¿Predicción de accidentes? | **Factible con restricciones** — requiere generar casos negativos y datos de exposición (TMDA). Ver §5. |
| Cuello de botella principal | El clima (`Estado_Atm`) **solo existe para 2023**; hay que reconstruirlo desde una API meteorológica externa. |

**Recomendación:** construir un producto en dos capas sobre Ruta 5 Sur —
(1) mapa de calor por tramo de km, (2) modelo de *riesgo relativo* por hora × día × clima
como capa explicativa sobre ese mapa. Ver §6.

---

## 2. Fuente principal: ArcGIS Hub de CONASET

CONASET publica 106 servicios ArcGIS abiertos, sin autenticación, consultables por REST
(`f=json`, filtros SQL, paginación, `outStatistics`). Es la mejor fuente de Chile por lejos:
son los datos de Carabineros (SIEC 2) ya geocodificados.

- Portal: https://mapas-conaset.opendata.arcgis.com/
- Endpoint raíz: `https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services`

### Capa recomendada: `Base_SINIESTROS_2020_2025`

**436.521 registros.** Es la única capa que combina cobertura nacional multi-año,
coordenadas, kilometraje de ruta y variables temporales.

Distribución anual verificada:

| Año | Siniestros |
|---|---|
| 2020 | 58.823 |
| 2021 | 78.405 |
| 2022 | 82.953 |
| 2023 | 75.303 |
| 2024 | 72.043 |
| 2025 | 68.994 |

Zona: **RURAL 96.290** (carreteras) / **URBANA 340.231**.

Campos disponibles:

```
FID, ID, AÑO, FECHA, Dia_semana, Mes, Hora, Hora_aprox, REGION, PROVINCIA, COMUNA,
TIPO_SINIE, TIPO__CONA, ZONA, CAUSA_SINI, CAUSA_NUEV, UBICACION, Calle_Uno, Calle_Dos,
Número, Ruta, Ubicación, Dirección, FALLECIDOS, TOTAL_LESI, GRAVES, MENOS_GRAV, LEVES,
Siniestro, Latitud, longitud, Zonas_urb_, Atropello, Bicicleta, Motociclet, AM
```

Dos campos son la clave del proyecto:
- **`Ruta`** — nombre de la carretera (`RUTA 5 SUR`, `RUTA 68`, `RUTA 160`…)
- **`Ubicación`** — **el kilómetro exacto sobre la ruta** (ej. 191,5). Esto permite
  referenciación lineal, que es exactamente lo que se necesita para hotspots en autopista.

### Otras capas útiles

| Servicio | Registros | Para qué sirve |
|---|---|---|
| `base_feriados` | 49.016 | Siniestros con `Feriado`, `Nombreferiado`, `Dia_del_feriado`. **Resuelve el requisito "festividades" sin trabajo extra.** |
| `Puntos_criticos_2020_2025` | 283.971 | Puntos críticos ya agregados por CONASET (útil como *baseline* de validación). |
| `tramos_con_siniestro` | 95.523 | Polilíneas de tramos viales con indicador de siniestralidad. |
| `rutas_con_indicador` | 2.359 | Ejes de rutas por ROL, para dibujar la carretera en el mapa. |
| `Siniestros_individuales_REGION_*_2023` | por región | **Únicas capas con clima**: `Estado_Atm`, `Condición` (calzada), `Estado_Cal`, `Tipo_Calza`, `Intersecci`. |
| `Base_de_persona_vehiculo_4` | 770.414 | Nivel persona/vehículo: edad, sexo, calidad (conductor/pasajero/peatón). |
| `Rural_2020` … `Rural_2024` | ~15.800/año | Solo zona rural, limpio. |
| `Reporte_diario_2025`, `Reporte_diario_2026` | diario | Datos casi en tiempo real de fallecidos. |

---

## 3. La autopista con más datos: **Ruta 5**

Conteo verificado agrupando por el campo `Ruta` (2020–2024):

| Ruta | Siniestros |
|---|---|
| **RUTA 5 SUR** | **14.430** |
| RUTA 5 NORTE | 5.845 |
| RUTA 160 | 1.633 |
| RUTA 68 (Santiago–Valparaíso) | 1.387 |
| RUTA 60 CH | 1.251 |
| I-50 | 1.250 |
| RUTA 66 (Autopista del Sol) | 1.151 |
| RUTA 78 | 855 |
| RUTA 180 | 755 |

Ruta 5 Sur tiene **2,5× más datos que la siguiente** y 8,8× más que Ruta 68. No hay competencia.

### Calidad de los datos de Ruta 5 (extraídos y perfilados en este directorio)

Archivo: [`ruta5_2020_2024.csv.gz`](ruta5_2020_2024.csv.gz) — 20.980 registros (`Ruta LIKE 'RUTA 5%'`).

- **100 % tienen latitud/longitud** (20.980 de 20.980) — sin geocodificación pendiente.
- **99,97 % tienen kilómetro válido** (14.425 de 14.430 en Ruta 5 Sur, tras filtrar km > 2.200).
- 1.184 fallecidos, 17.982 lesionados, 1.008 siniestros fatales.
- Cobertura territorial: Maule 4.151, Coquimbo 2.548, Los Lagos 2.409, O'Higgins 2.353,
  La Araucanía 2.068, RM 1.541, Valparaíso 1.197, Ñuble 1.176.

Tipos: COLISION 8.022 · CHOQUE 7.975 · VOLCADURA 3.605 · ATROPELLO 583.
Causas: DISTRACCION 6.275 · VELOCIDAD IMPRUDENTE 4.364 · IMPRUDENCIA 3.502 ·
ALCOHOL 1.655 · FALLAS MECANICAS 1.276 · FATIGA 987.

### Prueba de concepto de hotspots ya ejecutada

Agrupando Ruta 5 Sur en tramos de 5 km (255 tramos con al menos un siniestro):

| Tramo (km) | Siniestros | Fallecidos |
|---|---|---|
| 190–195 | 302 | 8 |
| 220–225 | 220 | 2 |
| **270–275** | 219 | **17** |
| 195–200 | 213 | 6 |
| 185–190 | 196 | 4 |
| 245–250 | 186 | 9 |
| 105–110 | 176 | 5 |
| 95–100 | 176 | 7 |
| 250–255 | 176 | 12 |
| 255–260 | 171 | 13 |
| 1015–1020 | 170 | 4 |

El mapa de puntos calientes **ya funciona**: la señal es fuerte, concentrada y estable.
El tramo 270–275 (zona Talca/San Rafael) destaca por letalidad, no solo por frecuencia.

---

## 4. Estado de cada variable que quieres usar

| Variable | ¿Está? | Detalle |
|---|---|---|
| **Fecha** | ✅ Completa | `FECHA`, `AÑO`, `Mes`, `Dia_semana` en todos los registros. |
| **Hora** | ✅ Completa | `Hora` (hh:mm:ss) y `Hora_aprox` (0–23). |
| **Día de la semana** | ✅ Completa | Ya viene calculado. Viernes es el día peak (3.448 de 20.980). |
| **Festividades** | ✅ Vía `base_feriados` | 49.016 registros con nombre del feriado y día del fin de semana largo. Alternativa: generar el calendario de feriados legales de Chile. |
| **Ubicación** | ✅ Completa | Lat/lon + kilómetro de ruta. |
| **Clima** | ⚠️ **Parcial** | `Estado_Atm` (DESPEJADO / NUBLADO / LLUVIA / LLOVIZNA / NEBLINA) y `Condición` de calzada (SECO / MOJADO / HUMEDO) **solo en las capas regionales de 2023**. Para 2020–2025 hay que reconstruirlo. |
| **Flujo vehicular (exposición)** | ⚠️ Externa | No está en CONASET. Ver §5. |

### Solución para el clima: API de reanálisis horario

Verificado y funcionando: **Open-Meteo Historical Weather API** (ERA5, gratuita, sin API key,
resolución horaria, cobertura global desde 1940). Se hace *join* por `(lat, lon, fecha, hora)`:

```bash
curl "https://archive-api.open-meteo.com/v1/archive?latitude=-34.99&longitude=-71.23&start_date=2020-01-03&end_date=2020-01-03&hourly=temperature_2m,precipitation,visibility,wind_speed_10m&timezone=America/Santiago"
```

Devuelve temperatura, precipitación, visibilidad y viento hora a hora. Con esto se
reconstruye clima para los 20.980 siniestros de Ruta 5 y, más importante, **para las horas
en que NO hubo accidentes** — que es lo que un modelo predictivo necesita.

Alternativas nacionales (más fieles pero más trabajo): la
[API de Climatología de la DMC](https://climatologia.meteochile.gob.cl/) (estaciones EMA,
JSON) y el [Explorador Climático CR2](https://explorador.cr2.cl/). La DMC tiene menos
estaciones que puntos de la carretera, así que en la práctica hay que interpolar igual.

**Resultado de la validación (medido, no supuesto):** contrastando los 6.096 siniestros
de Biobío 2023 que sí traen `Estado_Atm` observado contra lo que dice ERA5 para esa misma
celda y hora:

| Métrica | Valor |
|---|---|
| Acuerdo global | 84,7 % |
| **Sensibilidad** | **47,2 %** |
| Precisión | 26,7 % |
| **Kappa de Cohen** | **0,262** |

**El reanálisis NO reproduce la observación de Carabineros.** Se pierde más de la mitad de
las lluvias registradas en terreno. La causa es estructural: ERA5 promedia sobre celdas de
~25 km y la lluvia en la zona centro-sur es localizada, así que un chubasco sobre la
carretera se diluye en la celda. Reproducir con esto el campo `Estado_Atm` para 2020-2025
**no es viable**.

Pero esa es una pregunta distinta a la que importa. Que ERA5 no reproduzca *la etiqueta*
no implica que la precipitación no *prediga siniestros*. Eso se midió por separado y la
respuesta fue la contraria — ver §6.

---

## 5. El problema difícil: exposición y casos negativos

Este es el punto donde la mayoría de estos proyectos falla, así que conviene tenerlo claro
desde el principio.

**Los datos de CONASET solo contienen accidentes.** No hay filas de "km 191, martes 3 a. m.,
lloviendo, no pasó nada". Un modelo entrenado solo con accidentes no puede predecir
accidentes: aprende *dónde se concentran*, que es descriptivo, no predictivo.

Hay dos caminos legítimos:

**A) Modelo de conteos por celda espacio-temporal (recomendado).**
Se construye una grilla: tramo de 5 km × hora × día. Ruta 5 Sur ≈ 255 tramos × 24 h × 1.826 días
≈ 11,2 millones de celdas, la gran mayoría con cero siniestros. Se ajusta una regresión de
Poisson o binomial negativa (o gradient boosting con objetivo Poisson) sobre el conteo.
Esto responde exactamente tu pregunta — *"probabilidad de accidente según clima, hora,
día, feriado"* — y es estadísticamente correcto.

**B) Caso-cruzado (case-crossover).** Cada accidente se compara consigo mismo en horas
"control" del mismo tramo (ej. la misma hora las 3 semanas previas). Controla automáticamente
todo lo que no cambia en el tramo (curva, pendiente, señalización) y aísla el efecto del
clima y la hora. Es el diseño estándar en epidemiología del tránsito y **no requiere datos
de flujo vehicular**, lo que lo hace muy atractivo aquí.

**Exposición (TMDA):** el MOP publica el Plan Nacional de Censos Viales — 863 puntos censales
con Tránsito Medio Diario Anual por rama y por ROL de ruta, en un MapServer abierto:

```
https://rest-sit.mop.gob.cl/arcgis/rest/services/VIALIDAD/Plan_Nacional_de_Censos/MapServer
```

Capas por período: `2024 Sur - 2025 Norte`, `2023 Norte`, `2022 Sur - 2021 Norte`, etc.
Campos: `ROL_RAMA_1..4`, `TMDA_RAMA_1..4`, `ESTACION_DE_CONTROL`, `COMUNA`, `REGION`, `ANO`.
Sirve para normalizar "accidentes por millón de vehículos-km" en vez de accidentes crudos.
Limitación: es un promedio anual, no un flujo horario — no captura la punta de un domingo
de fin de semana largo.

---

## 6. Resultados del modelo (medidos)

Modelo Poisson sobre la grilla tramo (5 km) × hora, 255 tramos × 43.848 horas =
**11,2 millones de celdas**. Validación **temporal**: entrena 2020-2023 (11.820 siniestros),
prueba 2024 (2.605). Nunca aleatoria — hay autocorrelación y una partición al azar infla
los resultados.

### ¿Predice?

La métrica es operativa: *si dedicas el N % de las horas-tramo disponibles a vigilar las de
mayor riesgo predicho, ¿qué porcentaje de los siniestros reales de 2024 cubres?*

| Modelo | Desvianza ↓ | top 5 % | top 10 % | top 20 % |
|---|---|---|---|---|
| Tasa constante | 0,0 % | 2,1 % | 5,7 % | 15,4 % |
| **Solo tramo** (mapa estático) | 4,1 % | **15,0 %** | 26,3 % | 43,5 % |
| + hora, día, mes, feriado | 4,7 % | 17,8 % | 29,4 % | 47,3 % |
| **+ clima** | **5,1 %** | **19,2 %** | **30,6 %** | 47,5 % |

**Lectura honesta: el componente espacial hace casi todo el trabajo.** El mapa estático ya
captura el 15 % de los siniestros en el 5 % del tiempo — tres veces mejor que el azar.
Agregar hora, día, feriado y clima lo sube a 19,2 %, una mejora relativa del 28 %. Es real
y vale la pena, pero no es transformadora: quien prometa que el modelo dinámico cambia el
juego respecto de un buen mapa de puntos calientes, está exagerando.

### Efectos estimados (multiplicadores sobre la celda promedio)

| Variable | Efecto |
|---|---|
| **Lluvia > 0,5 mm/h** | **2,12×** |
| Llovizna 0,1–0,5 mm/h | 1,31× |
| 18:00 | 1,70× |
| 09:00 / 15:00 | 1,29× |
| 03:00 | 0,54× |
| Día de salida de feriado (`inicio`) | 1,22× |
| Último día de feriado (`final`) | 1,17× |
| Día feriado intermedio | 0,93× |
| Viernes | 1,11× |

Tres hallazgos que no eran obvios:

1. **La lluvia es el factor más fuerte del modelo**, por encima de la hora punta. Y esto
   ocurre *pese* a que la medición del clima es ruidosa (§4) — el efecto real probablemente
   sea mayor, porque el error de medida atenúa los coeficientes hacia 1.
2. **El día de salida a un fin de semana largo es más peligroso que el feriado mismo**
   (1,22× vs 0,93×). Por eso conviene el campo `Dia_del_feriado` de CONASET, que marca el
   período completo, en vez de una lista de feriados legales.
3. **El día de la semana casi no aporta** (0,93–1,11×). La hora sí (3,1× entre las 03:00 y
   las 18:00). Si hay que elegir variables, la hora vale y el día no.

### Veredicto sobre qué construir

**🟢 Mapa de puntos calientes** — resuelto y validado. Es la base y aporta el grueso de la
señal.

**🟡 Capa dinámica de riesgo** — funciona, aporta un 28 % relativo sobre el mapa estático, y
su valor se concentra en los eventos de lluvia, que es justo cuando un panel alimentado por
pronóstico le gana a un mapa fijo.

**🔴 "Sistema que predice accidentes"** — sigue descartado, y ahora con números. La tasa base
es de **0,13 % por tramo-hora**; en toda la Ruta 5 Sur se esperan **3,95 siniestros en 12
horas**. Ningún modelo con estos datos dirá "mañana a las 15:20 en el km 193 habrá un
choque", y una interfaz que muestre "probabilidad: 1,5 %" por tramo no le sirve a nadie.
Lo que sí se puede mostrar es el conteo esperado de la ruta completa y el riesgo relativo
por tramo.

---

## 7. Plan de trabajo

1. **Extracción.** `python3 descargar_conaset.py` — ya funciona, ya bajó los 20.980 registros.
2. **Limpieza.** Filtrar km implausibles (hay valores como 93.800 en el campo `Ubicación`),
   normalizar nombres de ruta, deduplicar por `ID`.
3. **Hotspots.** Agregación por tramo + índice de severidad + mapa. **Aquí ya hay resultado.**
4. **Enriquecimiento.** Join con Open-Meteo (clima horario) + `base_feriados` + TMDA del MOP.
5. **Validación del clima.** Contrastar Open-Meteo contra `Estado_Atm` de las capas
   regionales 2023. Reportar el nivel de acuerdo.
6. **Modelo.** Grilla tramo × hora × día, Poisson/binomial negativa. Validación temporal
   (entrenar 2020–2023, probar 2024) — nunca aleatoria, porque hay autocorrelación.
7. **Visualización.** Mapa interactivo con las dos capas.

### Limitaciones que conviene declarar en el informe final

- El campo `Ruta` **solo está poblado hasta 2024**. Los 68.994 registros de 2025 existen
  (17.201 rurales) pero sin nombre de ruta; habría que asignarlos espacialmente por cercanía
  al eje vial (`rutas_con_indicador`).
- Los datos son de Carabineros: **subregistro conocido** de siniestros sin lesionados y de
  siniestros donde no concurrió personal policial.
- El clima que reporta Carabineros es una observación subjetiva en terreno; el reanálisis es
  una estimación de modelo. Ninguno de los dos es una medición en el punto exacto.
- El TMDA es anual y por punto censal, no por tramo-hora.

---

## Contenido del repositorio

| Archivo | Qué es |
|---|---|
| `README.md` | Este informe de factibilidad. |
| `descargar_conaset.py` | Descarga cualquier capa del ArcGIS Hub de CONASET, con paginación. Sin API key. |
| `json_a_csv.py` | Convierte la salida a CSV comprimido (fechas epoch → ISO). |
| `hotspots.py` | Agrega Ruta 5 Sur en tramos de N km y ordena por frecuencia y letalidad. |
| `feriados.py` | Calendario de feriados de Chile 2019–2024 (243 fechas), con fin de semana largo completo. |
| `validar_clima.py` | Contrasta la reconstrucción ERA5 contra el clima observado por Carabineros (§4). |
| `clima.py` | Serie horaria de precipitación 2020–2024 para las 60 celdas ERA5 de la Ruta 5. |
| `modelo.py` | Modelo Poisson tramo × hora con validación temporal (§6). |
| `modelo_clima.py` | Igual, con precipitación, para medir cuánto aporta el clima. |
| `entrenar.py` | Ajusta el modelo final sobre 2020–2024 y guarda `modelo_final.json`. |
| `riesgo.py` | Combina el modelo con el pronóstico de Open-Meteo: riesgo por tramo y hora. |
| `generar_pagina.py` | Genera `pagina.html`: snapshot estático, para correr por cron cada hora. |
| `generar_live.py` | Genera `index.html`: versión **en vivo**, recalcula en el navegador en cada visita. |
| `ruta5_2020_2024.csv.gz` | 20.980 siniestros de la Ruta 5 (2020–2024), 944 KB. |

### Cómo reproducir todo desde cero

```bash
python3 descargar_conaset.py --where "Ruta LIKE 'RUTA 5%'" --salida ruta5.json
python3 json_a_csv.py ruta5.json ruta5_2020_2024.csv.gz
python3 hotspots.py 5          # mapa estático
python3 feriados.py            # calendario -> feriados.json
python3 clima.py               # 60 llamadas, ~5 min -> clima_ruta5.npz
python3 modelo.py 5            # modelo y validación temporal
python3 modelo_clima.py        # cuánto aporta el clima

python3 entrenar.py            # modelo final -> modelo_final.json
python3 generar_pagina.py      # pronóstico + página -> pagina.html
```

Hay dos versiones de la página:

**`pagina.html`** — snapshot estático. Los números quedan horneados al generarla, así que
necesita un cron para mantenerse al día:

```
0 * * * * cd /ruta/al/repo && python3 generar_pagina.py
```

**`index.html`** — en vivo, y es la recomendada. Embebe los 306 coeficientes del modelo y
el calendario de feriados (33 KB en total); el navegador pide el pronóstico a Open-Meteo
y recalcula el riesgo en cada visita. Sin cron y sin servidor: siempre muestra las 12
horas siguientes al momento en que se abre.

Requiere un host estático donde el navegador pueda alcanzar `api.open-meteo.com`
(la API responde `access-control-allow-origin: *`). **No funciona embebida en un artifact
de claude.ai**, cuyo CSP bloquea todo host externo.

La extracción y los hotspots corren con la biblioteca estándar. El modelo necesita
`numpy` y `scipy`.
El `.json` crudo está en `.gitignore` porque es regenerable y pesa 16 MB.

---

## 8. Fuentes

- [CONASET — Portal de mapas (ArcGIS Hub)](https://mapas-conaset.opendata.arcgis.com/)
- [CONASET — Observatorio de datos y estadísticas](https://www.conaset.cl/programa/observatorio-datos-estadistica/)
- [CONASET — Informe Nacional de Siniestros de Tránsito 2024](https://conaset.cl/wp-content/uploads/2025/07/Informe-nacional-de-siniestros-en-Chile-2024.pdf)
- [MOP Vialidad — Plan Nacional de Censos (REST)](https://rest-sit.mop.gob.cl/arcgis/rest/services/VIALIDAD/Plan_Nacional_de_Censos/MapServer)
- [MOP Vialidad — Plan Nacional de Censo Vial](https://vialidad.mop.gob.cl/plan-nacional-de-censo-vial/)
- [Open-Meteo — Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
- [DMC — Portal de Servicios Climáticos](https://climatologia.meteochile.gob.cl/)
- [Explorador Climático CR2](https://explorador.cr2.cl/)
- [Portal de Datos Abiertos de Chile](https://datos.gob.cl/dataset?tags=tr%C3%A1nsito)
- [Carabineros — Anuario de Tránsito](https://www.carabineros.cl/secciones/anuarioTransito/)
