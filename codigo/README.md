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

Para el ensayo de ubicación vial, instalar `requirements-espacial.txt` y usar
`descargar_eje_mop` y `evaluar_asignacion_vial`; `ubicacion_vial` contiene la
geometría común. [Protocolo, comandos y resultado](../docs/validacion_ubicacion_vial.md).
La aplicación a 2025 está condicionada a superar la comprobación; el ensayo actual
no la supera y conserva los modelos existentes.

`descargar_direcciones_conaset` obtiene el complemento textual y
`examinar_ambiguedades` reproduce el diagnóstico adicional. No genera etiquetas
aprobadas ni datos de entrenamiento: [cierre de la ampliación](../docs/cierre_ubicacion_2025.md).

Para reproducir las tablas y figuras recibidas de Cristóbal, ejecutar en este orden:

```bash
.venv/bin/python proyecto.py construir_comparacion_final
.venv/bin/python proyecto.py construir_aporte_lluvia_flujo
MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python proyecto.py construir_generalizacion
MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python proyecto.py construir_calibracion
```

Estas órdenes regeneran los resúmenes en `resultados/cierre` desde las tablas
existentes; no entrenan modelos. [Revisión de integración](../docs/cierre/integracion_cristobal.md).


`sensibilidad` ejecuta el diagnóstico urbano de ranking fijo y dos alternativas
prefijadas de cortes de lluvia. `sensibilidad_urbana_ajuste` excluye los eventos
etiquetados urbanos del entrenamiento para un objetivo rural exploratorio.
Ambos exigen una carpeta de salida nueva y no reemplazan modelos originales.
`resumir_sensibilidad` genera la figura desde las tablas; `revisar_piloto`
reproduce emisiones locales y genera un panel fechado sin descargar ni emitir.
[Protocolos, comandos y resultados](../docs/sensibilidad.md).


`contrastes_poisson` genera contrastes e inventario de Poisson_clima con los
artefactos disponibles, y reajusta si faltan. Para cotejar los originales sin
sobrescribir la reproducción de Martín, proporcionar otra carpeta `--salida`.
`tendencia_anual` genera el diagnóstico agregado desde tablas existentes.
[Integración, evidencia y comandos](../docs/cierre/integracion_martin.md).
