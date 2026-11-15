# Notebook que se entrega al profesor

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.

El repositorio contiene un único notebook: [EntregaFinal_Proyecto_DS.ipynb](EntregaFinal_Proyecto_DS.ipynb).
La [versión HTML](EntregaFinal_Proyecto_DS.html) permite leer sus resultados sin iniciar Python.

## Ejecución en Colab o Jupyter

1. Abrir o subir el `.ipynb`. No se necesitan ZIP adicional, clon de GitHub,
   rutas personales ni modelos preajustados: los datos y módulos están incorporados.
2. Ejecutar la primera celda de preparación. Usa CPU y comprueba hashes.
   Si hay que actualizar bibliotecas que ya estaban cargadas, reiniciar Python
   cuando lo indique y ejecutar de nuevo desde arriba. Requiere Python 3.11–3.13.
3. Ejecutar todas las celdas. La comparación completa entrena 60 configuraciones
   de búsqueda/validación y el reajuste final; puede tardar decenas de minutos.
   No se carga una tabla precalculada en lugar de entrenar.
4. Revisar las tablas, gráficos y conclusiones generados por esa misma corrida.
   El cierre debe mostrar `CIERRE_NOTEBOOK_CORRECTO` y entrenamiento completo.

La preparación instala versiones científicas si faltan; esa instalación requiere
internet. Los datos de análisis ya están dentro del archivo y no se descargan de
APIs que pudieran cambiar o limitar las consultas. Cada ejecución crea una carpeta
temporal nueva y conserva intactos los experimentos anteriores del repositorio.

## Contenido

El documento explica problema y CRISP-DM, preparación, EDA, flujo, modelos,
validación temporal, selección, calibración, interpretación, sensibilidades y
limitaciones del piloto. La comparación y las conclusiones se calculan con los
modelos entrenados en esa ejecución.

La evaluación principal utiliza captura, IC, MAE, RMSE, O/E y desvianza. Como
análisis auxiliar se evalúa `conteo > 0` con accuracy, precision, recall, F1,
especificidad, balanced accuracy, ROC-AUC y average precision/curva PR. Su umbral
procede del entrenamiento y no cambia la selección del modelo de conteos.

El bloque compacto inicial incorpora fuentes y código, sin joblib. Puede desplegarse
para inspección; los módulos extraídos también quedan legibles en `codigo/` dentro
de la carpeta temporal. El bloque se pliega en la lectura HTML para mantener el
relato legible, sin retirar el código de ajuste o análisis.

## Mantenimiento de la entrega

El generador `codigo/visualizacion/construir_notebook_final.py` incorpora las copias
originales del equipo. Generar una copia nueva con:

```bash
.venv/bin/python -m pip install -r requirements-notebook.txt
.venv/bin/python -m ipykernel install --user --name siniestros-ds --display-name "Python (siniestros-ds)"
.venv/bin/python proyecto.py construir_notebook_final --salida /tmp/EntregaFinal_nuevo.ipynb
```

Para ejecutar desde una carpeta vacía con un kernel preparado:

```bash
.venv/bin/python proyecto.py ejecutar_notebook_final --trabajo /tmp/ejecucion_entrega --kernel siniestros-ds
```

El ejecutor aborta ante errores, exige 60 configuraciones y cierre correcto,
exporta HTML y registra las tablas generadas en
`resultados/entrega_final/ejecucion_autocontenida/`. Los archivos científicos de
`resultados/modelos/` conservan la corrida original; la nueva ejecución se identifica
por separado. Las versiones anteriores del notebook quedan en el historial de Git.
