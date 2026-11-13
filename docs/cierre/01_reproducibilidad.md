# Diego: reproducción e integración técnica

Estado al 13 de noviembre de 2026. Versión de entrada: `0c5e42c`.
Esta ficha registra trabajo ejecutado por Diego con asistencia de Codex.
La revisión cruzada de Martín y la integración de las entregas de los demás
integrantes siguen pendientes; no se firma todavía el cierre de todo el equipo.

## Lo comprobado

- Las 33 pruebas originales pasan en el entorno de trabajo.
- Se creó un entorno aislado con Python 3.12.14, Linux x86_64, sin paquetes del sistema.
  Se instalaron las dependencias y `pip check` confirmó que no hay conflictos.
- Se detectó que Matplotlib 3.8.3 exige NumPy <2 en su distribución de PyPI,
  incompatible con NumPy 2.2.3 de la corrida. La instalación de Ubuntu permitía
  usarlos, pero copiar sus versiones a un entorno limpio fallaba. Para reproducir
  se usa Matplotlib 3.9.4 y se elevó el mínimo general a 3.9.
- Se añadieron siete pruebas que detectan mezcla de poblaciones, uso del año objetivo
  para seleccionar/recalibrar, duplicados, código diferente y sustitución de una
  comparación de lluvia. Las 40 pruebas pasan con todas las fuentes locales.
- El verificador concilia 114 filas de métricas, 60 de búsqueda, 36 selecciones,
  81 comparaciones con IC y 360 deciles.
- En el entorno aislado se reconstruyeron las predicciones de la candidata de
  2023 y 2024, originales y recalibradas: coinciden las nueve métricas con
  `rtol=1e-9` y `atol=1e-10`. El reajuste final pasa una comprobación de 1.000
  predicciones válidas e idénticas al recargar. Esto no es una prueba futura.

Evidencia generada: [verificación local](../../resultados/cierre/verificacion_local.md).
Se comprobó además una copia independiente formada solo por archivos que se
publicarán en Git: el verificador pasa y la suite descubre 40 pruebas, con 39
aprobadas y una omitida por ausencia del XLS DGC. La regeneración en una carpeta
temporal produjo los tres PNG y un `resumen.md` idéntico al publicado.
El registro de comandos está en [comprobaciones](../../resultados/cierre/comprobaciones.md).

## Instalación para otro integrante

Desde la raíz del repositorio, usar Python 3.12 (probado con 3.12.14):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-reproduccion.txt
.venv/bin/python -m pip check
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python verificar_cierre.py
```

Si ya hay una `.venv` con paquetes del sistema, crear otra carpeta de entorno
fuera del repositorio y sustituir `.venv/bin/python` por su ejecutable. No borrar
la instalación anterior. `requirements-reproduccion.txt` fija los 19 paquetes
del entorno comprobado y conserva las restricciones de `requirements.txt`.
No se garantiza instalación idéntica en otros sistemas o versiones de Python.
En el equipo de Diego, el Python 3.12 utilizado está también disponible en
`/home/diego/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`;
puede sustituir a `python3.12` en la creación del entorno. La comprobación usó
un entorno temporal; no reemplazó la `.venv` anterior ni los paquetes de Ubuntu.

Una copia de Git contiene código, siniestros CSV y tablas publicadas. Permite
verificar su coherencia sin clima, modelos ni conexión a las fuentes.
La prueba del anexo real DGC se omite explícitamente si ese XLS no está descargado:
en esa situación se esperan 40 pruebas descubiertas, 39 aprobadas y una omitida.

## Fuentes y modelos que Git no contiene

| Insumo local | Procedencia y recuperación | Control de versión |
|---|---|---|
| `ruta5_2020_2024.csv.gz` | Ya versionado en Git; evitar reemplazarlo por una descarga nueva durante la reproducción | SHA256 en `resultados/modelos/auditoria.json` |
| `feriados.json` | Copia original del equipo o `python feriados.py` | SHA256 en `resultados/eda/auditoria.json`; cobertura histórica 2020-2024 |
| `clima_ruta5.npz` | Copia v2 original; alternativamente `python clima.py` reconstruye el caché desde respuestas ERA5 parciales o la API | SHA256 en auditoría de modelos; 59 celdas, alineación UTC/DST |
| `data/fuentes/dgc/anexo_2023_4t.xls` y `anexo_2024_4t.xls` | Copias originales; alternativamente `python flujo_concesiones.py --descargar` | URL y SHA256 en `resultados/flujo/fuentes_dgc.json` y auditoría de modelos |
| `resultados/modelos/artefactos/*.joblib` | Copias locales de confianza del equipo o regeneración con los scripts de entrenamiento | Dos hashes finales en `reajuste.json`; hashes de los evaluados 2023/2024 en el informe local |

Las respuestas parciales ERA5 se guardan en `data/fuentes/era5/`; conservarlas con
sus metadatos permite reconstruir el caché sin red. Para repetir el EDA completo
también hacen falta las seis capas PNCV y sus metadatos en `data/fuentes/mop/`;
se descargan mediante `python flujo_vehicular.py --descargar`. La lista y hashes
originales están en `resultados/eda/auditoria.json`.

Descargar hoy puede devolver otra revisión. Si un hash cambia, no modificar el
manifiesto para ocultarlo: recuperar la copia original o abrir un experimento nuevo
documentado, manteniendo el protocolo. Los comandos de descarga no se ejecutaron
en esta verificación. Los modelos serializados se cargan solo desde copias del equipo.

## Comprobación con las fuentes originales disponibles

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python verificar_cierre.py --con-artefactos --salida resultados/cierre/verificacion_local.md
```

El comando devuelve código 0 si pasa o 1 si encuentra inconsistencia. No descarga
ni entrena. Por defecto comprueba tablas, selección temporal, hashes del código
de modelado y CSV de siniestros; `--con-artefactos` añade fuentes y predicciones
de la candidata actual `Poisson_clima`. Si cambia la candidata, revisar esa parte
del verificador antes de declarar una nueva validación. Los IC se concilian con
las comparaciones guardadas; el bootstrap no se recalcula.

## Regenerar figuras sin tocar los resultados vigentes

Copiar a una carpeta temporal `auditoria.json`, `metricas.csv`, `bootstrap.csv`,
`calibracion.csv`, `reajuste.json` y `recalibracion_candidato.csv` de
`resultados/modelos/`. Ejecutar:

```bash
MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python resumir_modelos.py --salida /ruta/temporal
```

Esto genera tres PNG y `resumen.md` desde las tablas. Sin `--actualizar-readme`
no modifica el README. Diferencias de Matplotlib/fuentes tipográficas pueden
cambiar los bytes de las imágenes; las tablas numéricas y el texto deben coincidir.

## Regeneración completa, solo si es necesaria

Con insumos verificados, primero guardar las salidas existentes y usar otra carpeta:

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python entrenar_comparacion.py --salida resultados/nueva_corrida
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python reajustar_candidato.py --salida resultados/nueva_corrida
MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python resumir_modelos.py --salida resultados/nueva_corrida
```

No se repitió el entrenamiento durante este cierre. El modelo evaluado en 2024
está entrenado hasta 2023; el reajuste 2020-2024 conserva los parámetros elegidos
antes de 2024 y carece de evaluación posterior. El prototipo HTML anterior tiene
otro universo y no se ha sincronizado con estos artefactos.

## Lo que debes hacer tú, Diego, para completar la revisión del equipo

1. Leer esta ficha y ejecutar pruebas y verificador en tu equipo; confirmar que
   puedes explicar la diferencia entre tablas publicadas y fuentes locales.
2. Pedir a Martín la revisión cruzada: que reproduzca una tabla, cargue la candidata
   y compruebe el artefacto correcto siguiendo estas instrucciones. No se registra
   esa revisión como realizada hasta recibir su resultado.
3. Integrar las fichas de Vicente, Martín y Cristóbal cuando estén revisadas;
   cotejar sus cifras con el mismo universo y actualizar el README.
4. Al cerrar el Día 2, ejecutar las pruebas de nuevo después de esa integración,
   registrar el commit y entregar el paquete a Máximo. El notebook se prepara después.

No presentar la interfaz antigua como resultado de la nueva comparación. Quedan
abiertas la disponibilidad histórica DGC, la exposición vehicular real y la
evaluación con pronósticos meteorológicos emitidos antes de decidir.
