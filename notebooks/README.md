# Notebook final de la Entrega III

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.

- [EntregaFinal_Proyecto_DS.ipynb](EntregaFinal_Proyecto_DS.ipynb): notebook ejecutado,
  con 19 secciones, 58 celdas y resultados incorporados.
- [Versión HTML de lectura](EntregaFinal_Proyecto_DS.html): código, tablas y siete
  figuras incorporadas; permite revisar el documento sin iniciar Jupyter.

El notebook consolida EDA, correcciones, flujo, comparación, selección temporal,
calibración, interpretación, sensibilidades, decisión sobre 2025 y piloto.
Las ramas del equipo están integradas en la base científica `5d80f40`.
La presentación y la lectura/firma del acta del equipo siguen fuera de este archivo.

## Abrir y ejecutar

Conservar la estructura del repositorio completo. El notebook encuentra la raíz
si se abre desde `notebooks/` o desde la raíz. No mover únicamente el `.ipynb` a
una carpeta sin el código y las tablas.

En un entorno científico preparado según la guía de reproducción:

```bash
.venv/bin/python -m pip install -r requirements-notebook.txt
.venv/bin/python -m ipykernel install --user --name siniestros-ds --display-name "Python (siniestros DS)"
```

Abrirlo en Jupyter o VS Code y elegir ese kernel. Seleccionar **Reiniciar kernel y
ejecutar todo**. El registro de versiones se muestra dentro del notebook. El
servidor/editor de Jupyter puede estar instalado aparte; la lista adicional incluye
el kernel y las herramientas de ejecución/exportación, no una interfaz de JupyterLab.
No reutilizar el Matplotlib 3.8.3 del sistema con IPython reciente; el entorno
científico fijado utiliza Matplotlib 3.9.4.

## Qué se reproduce

| Nivel | Insumos | Alcance |
|---|---|---|
| Copia pública | Código, CSV de siniestros, tablas, figuras, auditorías y modelo portátil de Git | Limpieza, EDA del histórico limpio, cobertura/rezago, selección y conciliación de evidencia publicada |
| Con originales | Además ERA5, calendario, dos anexos DGC y joblib locales originales | Predicciones 2023/2024, nueve métricas, persistencia final y bootstrap pareado 2024 |
| Piloto local | Además carpeta de emisión y sus capturas originales | Reproducción sin red de la emisión guardada; no evaluación de aciertos |

Un archivo local presente con hash equivocado provoca error cuando se verifica;
la ausencia de insumos se informa y no se presenta como reproducción de artefactos.
Las conclusiones del modo público proceden de evidencia publicada identificada,
no de un reentrenamiento de modelos en esa ejecución.

El registro `resultados/entrega_final/piloto_documentado.csv` es un resumen fechado
de una emisión real congelada y conserva el hash de su auditoría local. Su publicación
sirve para documentar el ejemplo académico; no es una alerta vigente ni contiene
observaciones completas para evaluar el piloto.

## Construcción y ejecución por CLI

Para regenerar el documento desde su fuente de contenido (borra las salidas del
notebook objetivo; elegir `--salida` diferente para preservar una versión):

```bash
.venv/bin/python proyecto.py construir_notebook_final --salida /tmp/EntregaFinal_nuevo.ipynb
```

Para ejecutar y exportar con un kernel real:

```bash
.venv/bin/python proyecto.py ejecutar_notebook_final --notebook notebooks/EntregaFinal_Proyecto_DS.ipynb --kernel siniestros-ds
```

El ejecutor aborta ante errores, exige ejecución de todas las celdas de código y
el marcador final de cierre, verifica que la evidencia no cambie y registra hashes,
versiones y nivel efectivo de reproducción en `resultados/entrega_final/auditoria.json`.
`--salida`, `--html` y `--auditoria` permiten conservar otra ejecución.

El entrenamiento completo está desactivado en la sección 18. Activarlo requiere
fuentes originales verificadas y una carpeta nueva; no depende de que ya existan
joblib. Invoca los módulos del proyecto con su protocolo original. Las sensibilidades
se reproducen con sus propios scripts y tampoco se ejecutan por rutina al leer.

## Comprobación de esta entrega

Se ejecutó de arriba abajo con kernel real tanto con fuentes/modelos locales como
en una copia de solo archivos versionados sin fuentes ni joblib locales. Las dos
corridas completaron las 26 celdas de código sin errores; el modo público informa
sus límites. Las salidas de ambas ejecuciones se conservaron separadas durante la
comprobación; se publica el notebook con la ejecución local completa y las dos
auditorías en `resultados/entrega_final/` y `resultados/entrega_final/publico/`.

La ejecución local usó un entorno temporal de herramientas Jupyter con Python 3.13.3,
los paquetes científicos originales (numpy 2.2.3, pandas 2.2.3+dfsg, scikit-learn 1.6.1)
y Matplotlib 3.9.4. No se reemplazó la `.venv` del proyecto ni se modificaron modelos,
fuentes, particiones o auditorías científicas. La guía científica conserva el entorno
fijado de Python 3.12.14, y cada ejecución del notebook informa sus versiones reales.
