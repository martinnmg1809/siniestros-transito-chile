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
La carpeta `data/fuentes/piloto/<emision_UTC>/` y su carpeta de salida deben
permanecer juntas y sin alteraciones.

La auditoría acredita que la respuesta meteorológica se capturó antes de emitir,
pero no la inicialización del modelo numérico. No se infiere su hora a partir de
`generationtime_ms`. Para evaluar la corrida, se necesitan registros observados con
fecha, hora, ruta, ubicación y cobertura acreditadas para todo el horizonte. Se
completa la plantilla de observaciones solo después de esa verificación, sin alterar
las predicciones congeladas. Hasta entonces no se calculan métricas de acierto.
