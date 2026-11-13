# Comprobaciones de la tarea de Diego

Fecha: 13 de noviembre de 2026. Código de entrada: `0c5e42c` más los cambios
de Diego publicados junto con esta ficha. Python aislado: 3.12.14, Linux x86_64.

| Comprobación ejecutada | Resultado |
|---|---|
| Instalación de dependencias sin paquetes del sistema | Correcta; restricciones fijadas en `requirements-reproduccion.txt` |
| Instalación original exacta con Matplotlib 3.8.3 y NumPy 2.2.3 | Conflicto reproducible: Matplotlib exige NumPy <2 |
| Instalación con Matplotlib 3.9.4 y NumPy 2.2.3 | Correcta |
| `python -m pip check` en el entorno aislado | `No broken requirements found.` |
| `python -m unittest discover -s tests -v`, con fuentes locales | 40 pruebas, todas aprobadas, ninguna omitida |
| La misma suite en copia independiente sin fuentes excluidas de Git | 40 descubiertas: 39 aprobadas y una omitida por ausencia del anexo DGC real |
| `python verificar_cierre.py`, en la copia independiente | Correcto; no requiere caché meteorológico ni artefactos |
| `python verificar_cierre.py --con-artefactos`, con fuentes originales | Correcto; nueve métricas reproducidas en 2023 y 2024, antes/después de recalibrar |
| Persistencia del reajuste 2020-2024 | 1.000 predicciones válidas e idénticas al recargar |
| `python resumir_modelos.py --salida <carpeta temporal>` | Tres PNG generados; Markdown idéntico al publicado |
| `git diff --check` | Sin errores |

En los comandos científicos se fijaron `OMP_NUM_THREADS=2` y
`OPENBLAS_NUM_THREADS=2`. Para gráficos, `MPLCONFIGDIR=/tmp/siniestros-matplotlib`.
No se ejecutaron descargas de fuentes ni ajustes de modelos en este trabajo.
El detalle de hashes, versiones y alcance está en
[verificacion_local.md](verificacion_local.md).

Las comprobaciones automáticas no acreditan la revisión humana de Martín;
esa revisión cruzada y la integración de los otros integrantes siguen pendientes.
