# Datos

- `siniestros/`: CSV comprimidos originales de CONASET versionados en Git.
- `fuentes/`: respuestas y anexos crudos descargados, con sus metadatos. Excluidos de Git.
- `calendario/`: `feriados.json` histórico; archivo local regenerable, excluido de Git.
- `cache/`: cachés ERA5 y matrices NumPy locales; excluidos de Git.

Los datos originales no se editan ni se reemplazan para hacer coincidir auditorías.
Los hashes históricos y la cuarentena están en `resultados/`. Consultar la ficha
`docs/cierre/01_reproducibilidad.md` para obtener versiones compatibles.
