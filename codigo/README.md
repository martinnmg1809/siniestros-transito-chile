# Catálogo de código

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.

Ejecutar desde la raíz con `python proyecto.py <nombre> [opciones]`.
`python proyecto.py --listar` muestra el catálogo completo. Para importar desde
un notebook ejecutado en la raíz, hacer primero `import proyecto`; después pueden
usarse los nombres de módulos existentes, por ejemplo `from modelos_conteo import ModeloConteo`.

| Carpeta | Contenido y entradas principales |
|---|---|
| datos | CONASET (`descargar_conaset`, `json_a_csv`), calendario (`feriados`), ERA5 (`clima`), DGC/PNCV (`flujo_concesiones`, `flujo_vehicular`), preparación común (`datos_ruta5`, `datos_modelado`, `integrar_flujo`) |
| modelos | `entrenar_comparacion`, `reajustar_candidato`, `reentrenar_flujo`; implementaciones `modelo`, `modelos_conteo`, `calibracion_modelos` |
| evaluacion | `explorar_datos`, `verificar_cierre`, `cierre_flujo`, `validar_ruta5` y métricas en `evaluacion` |
| visualizacion | `resumir_modelos`: figuras, tablas y resumen desde salidas existentes |
| historico | Prototipo multirruta, generadores HTML y experimentos anteriores. Se conservan como antecedentes; no representan la candidata nueva |

Algunos módulos de datos y métricas son bibliotecas, no tareas que deban ejecutarse.
Los nombres cortos se conservan deliberadamente: los modelos serializados con joblib
los necesitan al recargarse. El lanzador prepara sus rutas sin modificar los modelos.

Para revisar CONASET 2025 antes de incorporarlo: `descargar_revision_conaset`
conserva una instantánea nacional 2024/2025 comprobada y `explorar_conaset_2025`
produce el EDA aislado. [Uso, evidencia y condiciones](../docs/eda_conaset_2025.md).
Estos comandos no alimentan el entrenamiento ni asignan kilómetros a los eventos.
