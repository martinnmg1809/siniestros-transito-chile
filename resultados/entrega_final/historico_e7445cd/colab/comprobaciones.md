# Comprobación del paquete para Colab

14/11/2026. El enlace de Drive/Colab no estuvo accesible al conector ni al navegador
remoto. No se editó ni ejecutó el notebook de la cuenta de Diego.

Se generaron un ZIP local (304 archivos) y una copia del notebook final con dos
celdas iniciales: carga/verificación y dependencias. Las 58 celdas científicas
posteriores coinciden exactamente con las del notebook original; solo se vacían
sus salidas en la copia preparada para Colab.

Prueba en un directorio temporal aislado:

- La primera celda recibió una interfaz de subida simulada y extrajo el ZIP a una
  carpeta temporal, sustituyendo únicamente el destino /content en la prueba.
- Se comprobó SHA256 de los 304 archivos contra el manifiesto interno.
- La instalación pip fue simulada: el entorno ya tenía las versiones científicas
  necesarias. No se afirma instalación ni ejecución en un runtime hospedado de Colab.
- Se ejecutaron con kernel real las 28 celdas de código: las dos de preparación y
  las 26 originales. Sin errores; predicciones 2023/2024, persistencia final,
  bootstrap 2024 y captura histórica del piloto reproducidos.
- Se probó aparte el caso de NumPy cargado con una versión anterior: la celda exige
  reiniciar Python tras la instalación, evitando continuar con módulos desactualizados.
- Tras precisar la redacción del README, se regeneró y extrajo el ZIP final. Todos
  sus hashes concuerdan, y el código, datos y resultados coinciden byte por byte
  con los de la ejecución aislada anterior.
- El ZIP está excluido de Git; se conserva disponible localmente para subirlo a
  Colab. Los archivos científicos originales y sus auditorías no se modificaron.

`auditoria.json` contiene hash del ZIP, del notebook y de sus archivos.
`prueba_local/auditoria.json` registra la ejecución de la prueba simulada.
La dependencia del ZIP es explícita; guardar o compartir solo el `.ipynb` no
incluye los archivos de la máquina temporal de Colab.
