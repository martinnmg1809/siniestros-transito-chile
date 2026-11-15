# Google Colab: una sola entrega autocontenida

Abrir `notebooks/EntregaFinal_Proyecto_DS.ipynb` o subir ese archivo a Colab.
Es el único notebook vigente del repositorio. No se necesita el antiguo ZIP ni
la antigua copia con sufijo `_Colab`.

La primera celda extrae los datos y el código incorporados a una carpeta temporal,
verifica sus hashes y prepara dependencias. Si detecta una biblioteca antigua ya
cargada, solicita reiniciar Python después de instalarla. Reiniciar Python y volver
a ejecutar desde arriba, sin eliminar la sesión. Después, **Ejecutar todas**.

CPU es suficiente; el entrenamiento completo tarda decenas de minutos. Las celdas
muestran los ajustes realizados. Al finalizar se calculan las tablas comparativas,
las métricas de conteo y el diagnóstico binario auxiliar, las sensibilidades y las
conclusiones. El marcador final es `CIERRE_NOTEBOOK_CORRECTO`.

Se necesita internet únicamente para instalar bibliotecas que falten. Los datos,
clima y anexos DGC de esta entrega ya están dentro del notebook; no dependen de
carpetas de Drive de los integrantes. No se cargan modelos preajustados.

La comprobación del equipo incluye una ejecución completa con kernel local real
y una prueba adicional de preparación desde una carpeta vacía y un kernel nuevo.
No se accedió al kernel remoto de la cuenta de Diego. Los límites de validación
operativa del piloto permanecen explícitos dentro del documento.
