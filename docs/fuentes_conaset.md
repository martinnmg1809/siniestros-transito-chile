# Revisión de fuentes CONASET para ampliar y evaluar la predicción

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.

Consulta: 14 de noviembre de 2026. Se revisaron páginas oficiales y se consultaron
directamente metadatos, conteos, fechas extremas y valores distintos de capas REST.
No se descargaron las bases completas ni se alteró el experimento 2020–2024.

## Hallazgos principales

| Fuente oficial | Comprobado | Utilidad y condición |
|---|---|---|
| Base_SINIESTROS_2020_2025 | 436.521 registros; 68.994 de 2025, con fechas entre 01/01 y 31/12. Los 68.994 tienen coordenadas no nulas/no cero. La única ruta distinta encontrada en 2025 es un espacio y el único valor de Ubicación es 0. No hay registros de 2026 en esta capa. | Candidata para estudiar un período más reciente, pero requiere resolver ruta y kilometraje antes de asignar tramos. No permite filtrar directamente Ruta 5 Sur en 2025. |
| rutas_con_indicador | Geometría de polilínea, 2.359 filas, campo ROL. Existe una entidad ROL='Ruta 5 Sur'. No contiene kilometraje de referencia. | Fuente candidata para estudiar la correspondencia espacial; no basta para asignar kilómetros ni para aceptar todos los puntos cercanos. |
| Reporte_diario_2026 | 702 filas, fechas 01/01–13/07/2026. Tiene Fallecidos, fecha y región; no tiene hora, ruta, kilómetro ni coordenadas. | Contexto de mortalidad; no es el objetivo de todos los siniestros por tramo/hora y no permite validar las próximas 12 horas. El nombre del servicio no acredita actualización diaria. |
| Reporte_diario_2025 | 1.287 filas, fechas 01/01–31/12/2025; mismo problema de campos para nuestro objetivo. | Contexto anual, no sustituto de microdatos de siniestros. |
| base_feriados y fechas_feriado | La primera clasifica 49.016 registros y la segunda contiene 65 períodos. Los años de feriado son 2020–2024. | Apoyan la codificación histórica; no resuelven el calendario de predicción de 2026. |
| Base_de_siniestros_2 | 385.399 filas; rango de Año 2020–2024. Tiene fecha y hora, sin ruta, kilómetro ni coordenadas. | No es una base nueva de 2025/2026 para el modelo espacial. |
| base_para_2024 | 475.382 filas; años 2019–2024; no contiene fecha de evento, hora, ruta o kilómetro. | Estadística descriptiva; no puede reemplazar la grilla del modelo. |

El [inventario de capas](../resultados/conaset/capas_consultadas.csv) conserva
esquemas y enlaces. Las [consultas y respuestas resumidas](../resultados/conaset/auditoria.json)
incluyen parámetros, conteos y hashes de las respuestas originales guardadas localmente.

## Lo nuevo de 2025 y su límite

La [base geográfica oficial](https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services/Base_SINIESTROS_2020_2025/FeatureServer/0)
contiene fecha, hora y coordenadas en 2025. Las consultas de valores distintos
confirmaron Ruta=' ' y Ubicación=0 para ese año, sin truncamiento en esas respuestas.
La ausencia de etiqueta de ruta no se corrige rellenando ceros o escogiendo la
carretera más cercana por defecto.

La presencia de coordenadas no acredita por sí sola precisión: 73 puntos de 2025
quedan fuera del rectángulo continental usado en una consulta auxiliar
([-56,-17] de latitud y [-76,-66] de longitud). No se clasifican como errores:
ese rectángulo tampoco cubre todos los territorios insulares de Chile.

El [Observatorio de CONASET](https://www.conaset.cl/programa/observatorio-datos-estadistica/)
anuncia el informe nacional de 2025 e informa 73.081 siniestros. La capa geográfica
consultada contiene 68.994: son universos que no deben tratarse como idénticos sin
conciliar cobertura, revisiones y geocodificación. La diferencia no prueba su causa
ni justifica recalibrar Ruta 5 Sur con una proporción nacional.

## Dos formas de información reciente que no son equivalentes

La [página del reporte diario](https://www.conaset.cl/reporte-diario/) aparece
actualizada hasta el 12/11/2026 en el contenido oficial indexado y advierte que
2026 está sujeto a validación de Carabineros. La [capa REST de 2026](https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services/Reporte_diario_2026/FeatureServer/0)
consultada directamente llega al 13/07/2026. No se debe trasladar la frescura de
una página a otra capa por tener nombres parecidos.

Además, ambas fuentes se refieren a fallecidos. Nuestro objetivo son conteos de
siniestros, incluidos los que no tienen fallecidos, por tramo y hora. La cifra
nacional diaria de víctimas no permite obtener esos eventos ni sus ubicaciones.
No se encontró, entre las capas examinadas, un suministro de todos los siniestros
recientes que satisfaga esa resolución; no se afirma que no exista ninguna otra fuente.

## Qué puede aportar la cartografía de rutas

La [capa de rutas](https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services/rutas_con_indicador/FeatureServer/0)
contiene una entidad para Ruta 5 Sur, con extensión aproximada de latitudes
-43,12 a -33,45. Es un punto de partida para revisar geometría, no una validación
de sus kilómetros ni de la correspondencia con la fuente de siniestros.

Una futura asignación de eventos de 2025 necesitaría:

1. Verificar el eje y obtener referencias kilométricas fiables, por ejemplo de Vialidad.
2. Definir correspondencia que distinga Ruta 5, calles paralelas, enlaces y baipases.
3. Contrastar la asignación con eventos 2020–2024 que sí tienen ruta y kilómetro;
   documentar errores y casos ambiguos sin ajustar reglas para favorecer al modelo.
4. Mantener fuera los casos sin asignación defendible y medir cuánto cambia el universo.
5. Congelar el modelo antes de evaluar 2025; solo después decidir si procede actualizarlo.

La disponibilidad histórica del eje también debe documentarse. Esta propuesta no
se ejecutó y no garantiza que la nueva asignación sea viable dentro de los dos días.

## Recomendación para el proyecto

- **Para esta entrega:** conservar el experimento verificado 2020–2024 y explicar
  estos hallazgos como diagnóstico de actualización. No declarar 2025 integrado.
- **Para una evaluación adicional:** priorizar recuperar ruta/kilómetro de 2025
  mediante una fuente acreditada o solicitar a CONASET/Carabineros los microdatos
  correspondientes. No se envió ninguna solicitud en esta investigación.
- **Para el piloto de 12 horas:** obtener un calendario 2026 de una fuente oficial
  adecuada y pronósticos meteorológicos; CONASET aporta resultados observados,
  no una solución automática a esos dos insumos.
- **Para evaluar el piloto:** conseguir todos los siniestros observados del período,
  con fecha, hora, ruta y ubicación, y documentar demoras de publicación. Los
  fallecidos nacionales diarios no sustituyen esa comprobación.

También existe la [capa de puntos críticos](https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services/Puntos_criticos_2020_2025/FeatureServer/0),
con 283.971 filas y campos de año, ubicación y consecuencias. Su unidad y agregación
no se validaron aquí. Podría servir como referencia cartográfica; no debe usarse
como predictor o comparador histórico sin comprobar que excluye información futura.

## Reproducción y límites de la consulta

Las respuestas pequeñas y los scripts de consulta se guardaron en
`data/fuentes/conaset/revision_2026_11_14/`, fuera de Git. El archivo de auditoría
versionado contiene URL, parámetros y resultados suficientes para repetir las
consultas: serializar `outStatistics` como JSON al enviarlo a `/query` y usar
`f=json`. Las muestras de eventos individuales no se publicaron.

Las fechas de edición del servicio no acreditan primera publicación. Una consulta
agrupada de Base_de_siniestros_2 agotó el tiempo; se obtuvo después su rango de
años con mínimo/máximo, sin inferir la distribución anual. No se presupone que
las cifras de otras capas sean completas por coincidir con el nombre del servicio.

La lectura directa de las páginas web de CONASET falló en esta sesión; sus títulos
y cifras citados se revisaron mediante contenido oficial indexado por el buscador.
No se descargó ni analizó el PDF nacional de 2025. Las comprobaciones REST sí
provienen de respuestas directas del servidor oficial, sin desactivar la validación TLS.
