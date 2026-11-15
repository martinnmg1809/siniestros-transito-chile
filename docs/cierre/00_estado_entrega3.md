# Estado de la Entrega III y siguiente integración

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.

Actualización: 14 de noviembre de 2026. Responsable de integración: Diego.
Referencia docente: anuncio de la Presentación Técnica Final copiado por Diego en
el chat el 14/11/2026; complementa la rúbrica y las observaciones anteriores.
El anuncio exige presentación PPT/PDF y notebooks documentados, con evidencia,
interpretación y coherencia con el código. Los repartos y decisiones de organización
que siguen son acuerdos del equipo, no nuevas exigencias atribuidas al profesor.

## Correspondencia con el anuncio

| Requisito mínimo | Evidencia disponible | Trabajo necesario para la entrega final |
|---|---|---|
| Iteraciones y correcciones | README; matriz_compromisos.csv; cuarentena, captura con empates, UTC/DST y revisión de fuentes | Diego integra la matriz y las comprobaciones; Máximo utiliza sus conclusiones en la presentación |
| Comparación de modelos | metricas.csv, busqueda_temporal.csv y bootstrap.csv en resultados/modelos; Poisson, GB y RF, con/sin flujo | Tablas, figuras y ficha 04 completas; llevar sus conclusiones al notebook y presentación |
| Selección del modelo final | auditoria.json: candidata Poisson_clima, elegida con 2022/2023 y regla de simplicidad; reajuste.json | Fichas 03/03b integradas y comprobadas con artefactos originales; llevar la justificación a los entregables y revisar el acta |
| Validación y generalización | Ventanas expansivas; train/prueba; IC semanales; verificar_cierre.py; pruebas automatizadas | Ficha 04 explica estabilidad, brechas y límites; la ficha 03 integrada justifica elección y versiones |
| Interpretación | Fichas 02/04, diferencias e IC; calibración, MAE y ejemplos interpretativos | Ficha 04 completada; integrar su interpretación en los entregables y preparar la defensa del equipo |
| Conexión con el problema | Conteos por tramo/hora y priorización de vigilancia, captura global y por turno de 12 h | Explicar por separado dónde priorizar y cuántos eventos esperar; MAE actual agregado por cohorte/turno no acredita error por tramo |

Los nombres de tablas de la segunda columna se refieren a `resultados/modelos/`,
salvo la matriz de compromisos, situada en `resultados/cierre/`.

## Integración recibida de Vicente

Se incorporaron por avance directo los seis commits de `cierre/vicente-flujo`,
desde `d5dd8e5` hasta `a7b8e01`, conservando su autoría. La rama parte de `a65a02d`.
Incluye `cierre_flujo.py`, la ficha 02, cobertura por contrato, inventario de fuentes,
matriz de compromisos y el plan de trabajo que Vicente conservó como antecedente.

Diego comprobó que la tabla regenerada es idéntica a la recibida: 14.420 siniestros,
255 tramos; 153 con contrato y 102 sin contrato utilizable, desglosados en 43 antes
del primero, 39 después del último y 20 en fronteras/baipases/márgenes. La coincidencia
con resultados/modelos no acredita homogeneidad real de tráfico por tramo.

Se añadió `cierre_flujo.py --comprobar`: verifica la tabla sin sobrescribirla y falla
si falta o fue alterada. Tres pruebas de integración verifican ese comportamiento.
Los detalles del entorno y de las comprobaciones están en
[integracion_vicente.md](../../resultados/cierre/integracion_vicente.md).

Se precisó el lenguaje sobre fechas de publicación y archivos meteorológicos en
la ficha 02 y la matriz. Consultar los enlaces primarios de su sección 5; una fecha
en la ruta de una URL no acredita primera publicación. La búsqueda Wayback descrita
por Vicente no adjunta un resultado archivístico verificable. Las limitaciones
continúan abiertas y no se han sustituido datos ni repetido entrenamientos.

## Integración recibida de Cristóbal

Se sincronizaron los commits `07df973`, `dbe7ef7` y `3963bd3` de `origin/main`
conservando autoría. Incluyen seis tablas, dos figuras y cuatro generadores de
comparación, aporte de lluvia/flujo, generalización y calibración. Las seis tablas
se reprodujeron exactamente en una carpeta temporal; los generadores pasan a
`codigo/evaluacion` según la organización acordada. Se conserva el contenido de
las tablas y figuras recibido. Consultar la [revisión de integración](integracion_cristobal.md).

Al recibir esos commits aún faltaban la ficha narrativa 04 y la revisión de la
ficha 02. Por encargo posterior de Diego, se completaron ambas con asistencia de
Codex. El cierre se documenta en la [ficha 04](04_interpretacion.md) y el
[registro de revisión de datos](../../resultados/cierre/revision_vicente.md).
No se atribuye esa revisión a los integrantes originales.

## Integración recibida de Martín

Se incorporó por fast-forward `claude/planning-pending-work-asvuvw` hasta `df3f6df`,
con seis commits de Martín y el merge de main ya incluido en su rama. Se recibieron
fichas 03/03b, contrastes, ejemplo de turno, diagnóstico temporal, reproducción
independiente y siete pruebas. La revisión solicitada a Diego se completó con los
joblib originales: nueve métricas de 2024 a tolerancia 1e-10; el verificador con
artefactos y las 85 pruebas pasan. Se conservan intactos los archivos recibidos y
se añade evidencia identificada de la reproducción con originales. Ver
[integración de Martín](integracion_martin.md). La firma del acta corresponde al equipo.

## Pendientes reales y responsables

- **Diego:** fichas 02, 03 y 04 integradas y revisadas. Notebook final construido
  y ejecutado; comprobar con el equipo su coherencia con la presentación y el paquete final.
- **Vicente:** aporte de datos y flujo completado y revisado técnicamente por
  encargo de Diego. Exposición vehicular y publicación histórica permanecen como
  limitaciones documentadas; no se exige resolverlas para afirmar este cierre.
- **Martín:** ficha 03/03b y reproducción independiente recibidas. La integración
  cotejó su evidencia con los artefactos originales; preparar con el equipo la
  lectura y firma del acta, sin registrarla como realizada anticipadamente.
- **Cristóbal:** aporte técnico integrado y ficha narrativa 04 completada por
  encargo de Diego. La interpretación y revisión de la ficha 02 están documentadas.
  Corresponde al equipo leer las conclusiones y preparar su defensa.
- **Máximo:** preparar la presentación con las tablas, figuras y conclusiones
  verificadas. No se ha modificado su presentación.

La [sensibilidad urbana y de lluvia](../sensibilidad.md) ya se ejecutó con protocolos
separados, sin reseleccionar la candidata. La etiqueta urbana solo aparece en
2020–2021; el ajuste rural exploratorio no acredita generalización urbana física.
La evaluación observada del piloto sigue pendiente de una fuente completa.

El [único notebook final](../../notebooks/EntregaFinal_Proyecto_DS.ipynb) incorpora
sus datos y código, entrena el protocolo completo y calcula métricas y conclusiones
durante la ejecución. Se retiró la copia separada de Colab. Incluye una evaluación
binaria auxiliar (accuracy, precision, recall, F1, ROC y PR), identificada como tal,
sin cambiar la selección por captura de conteos. El [HTML](../../notebooks/EntregaFinal_Proyecto_DS.html)
y la [guía](../../notebooks/README.md) acompañan al archivo. Queda la revisión
conjunta con la presentación y la lectura del acta por el equipo.
La comprobación del 15/11 ejecutó 54 celdas (24 de código) sin errores y pasó
88 pruebas. Las [evidencias de la ejecución autocontenida](../../resultados/entrega_final/ejecucion_autocontenida/comprobaciones.md)
se guardan aparte de los experimentos originales.
La carga final es grupal y la realiza una sola persona. No se ha realizado ningún
envío académico desde esta integración.

## Alcance y criterios de cierre

La ampliación a 2025 se investigó por geometría, direcciones y capas adicionales,
y se cerró para esta entrega por falta de ubicación vial comparable acreditada.
Se mantiene **2020–2024**; no hay que integrar una cohorte parcial de 2025 como si
fuera el año completo ni repetir entrenamientos por este intento. La
[decisión y evidencia](../cierre_ubicacion_2025.md) se incorporan a las limitaciones
que explicará el equipo. Solo se reabre con información nueva que resuelva ese punto.

Se mantiene Ruta 5 Sur como alcance principal. Extensión a otras rutas y actualización
del prototipo quedan para después de resolver este caso. Se estudian conteos y
priorización retrospectiva; se implementó una emisión reproducible del piloto en
modo sombra, pero no se acredita un servicio operativo ni riesgo por vehículo-km.
Su evaluación con siniestros observados sigue pendiente. Las sensibilidades
retrospectivas urbana y de umbrales están documentadas con sus límites. La
ampliación 2025 se cerró por falta de ubicación comparable, no por data leakage; la separación temporal de entrenamiento y evaluación se mantiene.

Antes de enviar, Diego debe comprobar que cada cifra tiene tabla, población, año y
unidad, que la candidata coincide con el artefacto citado y que las fichas aprobadas,
README, notebook ejecutado y presentación dicen lo mismo. Las pruebas automáticas
no sustituyen la interpretación ni las aprobaciones humanas pendientes.
