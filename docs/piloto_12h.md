# Piloto de 12 horas en modo sombra

## Qué se implementó

Se generó una primera emisión reproducible para **Ruta 5 Sur**. Usa la candidata
Poisson_clima seleccionada antes de evaluar 2024, reajustada con los datos
2020–2024 que ya estaban disponibles. No entrena ni selecciona un modelo con esta
emisión. Se dejó fuera el proxy de flujo porque la candidata vigente no lo utiliza.

La emisión se realiza una vez y deja congelados el pronóstico, la prioridad por
tramo, las capturas de insumos, el reporte y sus hashes. Las capturas originales
quedan en `data/fuentes/piloto/` (directorio local excluido de Git); las salidas se
guardan localmente en `resultados/piloto/<emision_UTC>/`, directorio excluido de Git
porque es un pronóstico fechado que expira. La carpeta de insumos debe conservarse
junto a la salida para poder reproducirla. La primera corrida se guardó en el espacio
de trabajo; sus valores son evidencia de una emisión, no resultados generales del
modelo.

## Primera emisión

Emitida el 14 de noviembre de 2026 a las 21:36:41 UTC. La ventana local fue del
**14/11 19:00 al 15/11 07:00**, doce horas reales, con 255 tramos de 5 km y 59
localidades meteorológicas de referencia. Se priorizaron 12 tramos (4,71 % de la
red). La candidata original estimó 2,615 siniestros en toda la ruta; una variante
recalibrada con el factor de referencia de 2024 estimó 2,019. Se muestra solo como
contraste de nivel, no como modelo elegido. El detalle local de la corrida está en
`resultados/piloto/20261114T213641650756Z/`.

## Interpretación, evidencia y límites

La ampliación 2025 no se descartó por data leakage: se cerró porque no fue posible
acreditar una asignación vial comparable. El riesgo de fuga de información se
aborda por separado mediante particiones temporales en las evaluaciones históricas.
El piloto actual no incorpora datos 2025.

Esta es una **emisión experimental en modo sombra**, no un piloto operativo oficial,
una alerta o una recomendación de despliegue. Sus cifras no se han comparado con
siniestros observados. El ranking y los conteos todavía no demuestran capacidad
predictiva en operación.

Hay dos cambios de dominio por evaluar: la tendencia temporal se extiende de 2024 a
2026 y el pronóstico ECMWF distribuido por Open-Meteo sustituye el reanálisis ERA5
usado en el entrenamiento. El proveedor meteorológico devuelve coordenadas de
grilla; pueden diferir de las solicitadas y se mantienen sus respuestas originales
para auditoría. Las posiciones de los tramos proceden de la referencia 2020–2021,
son aproximadas y no definen puntos físicos de despliegue.

La predicción principal usa la candidata original. Se presenta aparte una serie
con el factor de referencia de 2024, sin seleccionar ni afirmar que sea superior.
El uso de ese factor no constituye una validación independiente.

## Reproducir o emitir

Desde la raíz del repositorio, después de instalar el entorno fijado:

```bash
.venv/bin/python proyecto.py modelo_piloto --config config/piloto_12h.json --salida resultados/piloto/modelo_poisson.json
.venv/bin/python proyecto.py piloto_12h --config config/piloto_12h.json --salida resultados/piloto --fuentes data/fuentes/piloto
.venv/bin/python proyecto.py piloto_12h --reproducir resultados/piloto/<emision_UTC>
```

La exportación verifica los dos artefactos locales, la referencia espacial y el
cierre de tablas; compara 2.048 predicciones con ambos modelos originales y no
reentrena. La emisión nueva necesita conexión a internet y nunca sobrescribe una
corrida previa. La reproducción verifica hashes y tablas sin red ni escritura.
La ruta exacta de insumos está en `carpeta_capturas` dentro de `auditoria.json`.
Su identificador corresponde al inicio de la captura y es distinto del de emisión;
conservar esa carpeta y la salida en las rutas registradas.

La auditoría acredita que la respuesta meteorológica se capturó antes de emitir,
pero no la inicialización del modelo numérico. No se infiere su hora a partir de
`generationtime_ms`. Para evaluar la corrida, se necesitan registros observados con
fecha, hora, ruta, ubicación y cobertura acreditadas para todo el horizonte. Se
completa la plantilla de observaciones solo después de esa verificación, sin alterar
las predicciones congeladas. Hasta entonces no se calculan métricas de acierto.


## Panel local y controles de insumos

```bash
.venv/bin/python proyecto.py revisar_piloto
```

Esta orden reproduce las emisiones locales, valida sus hashes y crea
`resultados/piloto/panel/index.html` y `registro.csv`. El panel es estático y muestra
el instante de revisión; ejecutarlo de nuevo actualiza el estado temporal.
Una ventana terminada no equivale a una emisión evaluada. Los enlaces llevan a
reportes fechados, no a alertas vigentes. El panel y las capturas permanecen locales.
No se inicia una programación automática ni se emite un pronóstico nuevo.

Los controles ensayados rechazan capturas posteriores a la emisión o demasiado
antiguas, lluvia nula/incompleta, fechas fuera de calendario y cercanía a feriados
sin posición validada; una caída del proveedor se propaga como error. La cobertura
manual actual es del 4 al 30/11/2026. Ampliar fechas exige revisar el calendario.
Las variantes experimentales de sensibilidad no sustituyen el modelo del piloto.

## Protocolo para una futura evaluación observada

1. Conservar emisión, modelo, pronóstico y prioridades antes de conocer resultados.
   Si se incorpora M1 como comparador operativo, congelar también su versión y
   prioridades en la emisión; el panel actual no produce ese comparador.
2. Acreditar una fuente de todos los siniestros, cobertura de los 255 tramos y
   ventana completa, ruta, kilómetro y fecha/hora, junto con demora y revisión de
   publicación. Una noticia aislada o un reporte de fallecidos no acredita el total.
3. Validar IDs únicos, dominio vial y zona horaria; tratar horas ambiguas por DST
   explícitamente. No completar observaciones faltantes con cero ni editar las
   predicciones para coincidir con eventos conocidos.
4. Cerrar la observación solo cuando la fuente permita acreditar completitud.
   Evaluar conteo total, error absoluto por ventana, O/E agregado sobre varias
   ventanas y captura con los 12 tramos realmente seleccionados (4,71 %).
   La captura es indefinida si no hubo siniestros. Un MAE exige varias ventanas.
5. Si hay emisiones solapadas, declarar el esquema de evaluación por anticipado;
   no tratar ventanas correlacionadas como observaciones independientes para IC.
   Comparar modelos solo con las mismas ventanas, población y presupuesto.

Esta evaluación no se ejecutó: faltan observaciones completas y verificables del
horizonte. La emisión y su reproducción acreditan funcionamiento técnico, no
capacidad predictiva operativa ni validez de la extrapolación temporal a 2026.
