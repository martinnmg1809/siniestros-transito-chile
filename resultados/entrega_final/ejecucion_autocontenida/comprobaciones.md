# Ejecución del notebook autocontenido · 15/11/2026

**Estado: correcto.** Se ejecutaron las 54 celdas del documento (24 de código)
con un kernel Python real, sin errores, en 2.237,49 segundos (37,29 minutos).
La comparación y el reajuste ocuparon 34,68 minutos; el resto incluye preparación,
EDA, nueve ajustes de sensibilidad, tablas, gráficos y conclusiones.

Se usó Python 3.13.3, numpy 2.2.3, pandas 2.2.3+dfsg, scipy 1.14.1,
scikit-learn 1.6.1, Matplotlib 3.9.4 y joblib 1.6.0. El kernel estuvo en un
entorno temporal separado de la `.venv` de trabajo, con dos hilos para los ajustes.

## Qué se comprobó

- Las fuentes de todas las celdas ejecutadas coinciden con el generador del notebook.
- El paquete incorpora 26 archivos con hashes verificados, sin joblib preajustados
  ni tablas de métricas de modelos anteriores. Solo las pequeñas tablas de diagnóstico
  de PNCV y ubicación 2025 son antecedentes identificados como tales.
- Se entrenaron 60 configuraciones, se registraron 36 selecciones temporales y
  114 filas de métricas; se reajustó la candidata con 2020–2024. Poisson_clima fue
  seleccionada con la regla previa a 2024, sin cambiar grillas ni particiones.
- Las nueve métricas originales coinciden en las 114 filas con tolerancias
  relativa y absoluta de 1e-10. La diferencia máxima es 4,55e-13 en conteos esperados.
  La [conciliación](conciliacion_historica.csv) conserva el detalle.
- Se calcularon 48 diagnósticos binarios con umbral p95 de entrenamiento y regla
  estricta `score > umbral`; los híbridos sin train no reciben un umbral inventado.
  Las áreas ROC/AP usan todos los scores; solo los puntos de dibujo se reducen.
- Se revisaron visualmente las seis figuras: EDA, comparación temporal, aporte del
  flujo, ROC/PR, calibración y sensibilidades. Las conclusiones muestran valores de
  la corrida, incluidos los resultados desfavorables del diagnóstico binario.
- El cierre informa `CIERRE_NOTEBOOK_CORRECTO`. El HTML oculta únicamente el código
  compacto de preparación; conserva el código de entrenamiento y análisis legible.
- Otra prueba inició un kernel nuevo en una carpeta vacía: preparó los 14.420
  eventos y 255 tramos desde el archivo incorporado, sin modelos anteriores.
  Su [auditoría](preparacion_vacia/auditoria.json) distingue este alcance del
  entrenamiento completo, cuyo kernel comenzó en la raíz del proyecto y extrajo
  los insumos a una carpeta temporal nueva.
- Pasaron las 88 pruebas de `unittest discover -s tests -v`, incluida la exclusión
  de horas inexistentes, el tratamiento de empates y la distinción conteo/etiqueta.
  También pasó `proyecto.py verificar_cierre` y `git diff --check`.

## Trazabilidad

[auditoria.json](auditoria.json) registra hashes del notebook, HTML y tablas, junto
con el cierre estructurado. [protocolo/auditoria.json](protocolo/auditoria.json)
conserva el registro del entrenador original; [complemento/auditoria.json](complemento/auditoria.json)
identifica las métricas añadidas. [reajuste.json](reajuste.json) distingue los
artefactos evaluados y el reajustado sin prueba futura. Los joblib se generan
localmente y no se versionan.

No se accedió al kernel remoto de Colab. La instalación de dependencias requiere
internet y puede pedir un reinicio de Python si ya había bibliotecas cargadas.
Las próximas ejecuciones calculan sus propios resultados y tiempos. El piloto
continúa sin evaluación prospectiva observada; 2024 es evaluación histórica
reutilizada y el flujo trimestral sigue siendo un proxy, no exposición vehículo-km.
