# Ejecutar la entrega en Google Colab

Se necesita el código y las tablas además del `.ipynb`. Abrir un notebook de Drive
no incorpora los archivos de la máquina donde se construyó. La sesión remota del
enlace de Diego no estuvo accesible a la conexión de Drive ni al navegador del
agente: no se afirmó haber ejecutado o modificado esa copia.

## Opción preparada: un notebook y un ZIP

1. Descargar `EntregaFinal_Proyecto_DS_Colab.ipynb` y el archivo local
   `resultados/entrega_final/colab/Siniestros_Colab_Completo.zip` que entrega Diego.
2. Abrir o subir el notebook para Colab. Usar CPU: el proyecto no necesita GPU.
3. Ejecutar la primera celda de código y subir únicamente el ZIP cuando lo solicite.
4. Ejecutar la segunda celda, que instala las versiones científicas del proyecto.
   Si detecta módulos antiguos ya cargados, pide reiniciar Python. Reiniciar la
   sesión de Python, sin elegir «Desconectar y eliminar entorno», y volver a ejecutar
   desde arriba. El ZIP se conserva en esa misma máquina mientras no se elimine.
5. Continuar con todas las celdas. Deben aparecer las nueve métricas reproducidas,
   bootstrap coincidente y `CIERRE_NOTEBOOK_CORRECTO` en la última celda.

La celda valida el manifiesto y cambia el directorio a `/content/siniestros_colab`.
Así la primera celda del notebook científico encuentra `proyecto.py` y sus módulos.
No hace falta montar Google Drive ni subir CSV y joblib uno por uno. El paquete
contiene los archivos de Git, ERA5, calendario, los dos anexos DGC, cuatro joblib
originales y la emisión/capturas de ejemplo. El ZIP queda fuera de Git, igual que
sus fuentes locales; puede regenerarse con `python proyecto.py preparar_colab`.

## Si se conserva el notebook de Drive ya abierto

Copiar las dos celdas iniciales del notebook preparado **antes de la celda que
empieza con `from pathlib import Path`** (`entrega-final-004`). Ejecutarlas y continuar
desde esa celda. No se necesita sustituir el contenido científico del notebook.
Guardar primero una copia si se ha añadido trabajo propio.

## Alternativa con solo GitHub

Clonar el repositorio en la máquina de Colab y situarse en su raíz permite ejecutar
el modo público. Este modo funciona sin los joblib/fuentes locales, pero informa
que no reconstruye esas predicciones. Para el modo completo se necesita el ZIP
anterior o copias originales del equipo en las rutas documentadas.

## Comprobaciones y límites

La extracción y el notebook preparado se comprobaron en un directorio aislado local
con los paquetes científicos acordados. Las celdas de carga e instalación se ejercitaron
con una interfaz de subida simulada; no se usó una cuenta de Colab ni se simuló haber
conectado con su kernel remoto. La versión de Python compatible es 3.11–3.13; se
comprobó localmente Python 3.13.3. La disponibilidad de cada versión de entorno
hospedado depende de Colab.

La prueba no activa entrenamiento completo ni nuevos pronósticos. La emisión del
piloto sigue siendo un ejemplo histórico congelado sin observaciones para medir
aciertos. Conservar el ZIP descargado: los archivos de la máquina temporal de Colab
no quedan incorporados por compartir o guardar solamente el notebook.

Referencia: [FAQ oficial de Colab: archivos, bibliotecas y sesión de ejecución](https://research.google.com/colaboratory/faq.html).
