# Registro de migración

`migracion_estructura.csv` registra la ubicación anterior y actual de los archivos
reorganizados y sus hashes antes/después. Los caminos relativos se interpretan desde
la raíz del proyecto. Algunas filas incluyen salidas locales opcionales no versionadas.

Las auditorías científicas originales no se reescribieron. El verificador acepta
el hash original o la pareja explícita registrada en esta migración, y rechaza
cualquier edición posterior no registrada. Registrar la reorganización no equivale
a ejecutar de nuevo entrenamientos: su compatibilidad se comprueba con pruebas y
predicciones de los artefactos existentes.
