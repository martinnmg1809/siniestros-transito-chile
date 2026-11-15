# Comprobaciones del notebook final

14/11/2026 · Base científica `5d80f40`. Construcción e integración de Diego con
asistencia de Codex. La autoría de los aportes del equipo se conserva en el historial.

- Integraciones: las ramas remotas de Vicente y Martín son antecesoras de main;
  no había solicitudes abiertas al construir el notebook.
- Esquema nbformat válido; 58 celdas, 26 de código, contadores 1–26, sin errores.
- Ejecución con originales: predicciones 2023/2024 y persistencia final comprobadas;
  nueve métricas de 2024 e IC de captura Poisson frente a M1 reproducidos;
  emisión histórica del piloto reproducida sin red.
- Ejecución pública: copia de solo archivos versionados, sin caché ERA5, anexos
  DGC, joblib o capturas del piloto. Completa las mismas 26 celdas y anuncia los
  insumos faltantes. No se declara reconstrucción de modelos en esa corrida.
- Las fuentes de todas las celdas son idénticas en ambas ejecuciones. Las auditorías
  conservan hashes, nivel real y versión del ejecutor; no se publicó otra versión
  del notebook con salidas públicas para evitar confundir ambas corridas.
- HTML: 26 celdas de código, siete imágenes PNG incorporadas como data URI,
  marcador final presente y sin salidas de error. No necesita imágenes externas
  para leer las figuras.
- Enlaces locales de README, guía, estado y Markdown del notebook comprobados.
- Suite del proyecto: 85 pruebas aprobadas, sin omisiones.
- No se repitió entrenamiento completo, no se descargaron fuentes ni se modificaron
  modelos, datos o auditorías científicas. Se verificó git diff --check.

Las auditorías ejecutadas son `auditoria.json` y `publico/auditoria.json` en esta
carpeta. El entorno temporal Jupyter usó los paquetes científicos del entorno
original y Matplotlib 3.9.4. La `.venv` del proyecto se conservó.

Para repetir la validación, seguir `notebooks/README.md`. El notebook necesita el
repositorio completo; los modelos y fuentes locales no forman parte de Git.
Presentación y lectura del acta por el equipo siguen pendientes. El piloto todavía
carece de observaciones completas para evaluar aciertos.
