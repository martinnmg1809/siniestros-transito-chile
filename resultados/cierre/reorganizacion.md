# Comprobación de la reorganización

Fecha: 14/11/2026. Commit de partida: `974c8cd8d8e24c3a23bb0c0e8729e2731cd431d2`.
Trabajo de organización realizado para Diego con asistencia de Codex.

## Estructura y compatibilidad

- Se movieron 35 módulos a cinco áreas de codigo/; el lanzador proyecto.py
  configura sus importaciones y el directorio de trabajo.
- Los CSV CONASET están en data/siniestros; cachés y calendario locales se
  trasladaron a data/cache y data/calendario. Salidas antiguas: resultados/prototipo.
- Se trasladaron el informe de Etapa I y la planificación a docs/.
- El README es un índice; resultados y EDA están en documentos separados.
- Se conservaron index.html y su contenido para la URL del prototipo existente.
- Los 45 artefactos joblib locales conservaron exactamente sus bytes.
- CSV científicos, auditorías JSON, figuras, documentos binarios trasladados y
  portada conservaron sus hashes. Solo se actualizaron rutas en documentos de resultados.
- No se reentrenó, reserializó ni descargó información científica.

## Comprobaciones ejecutadas

| Comprobación | Resultado |
|---|---|
| Suite completa con fuentes locales | 45 pruebas aprobadas |
| Copia pública sin fuentes ni modelos ignorados | 45 descubiertas: 44 aprobadas y una omitida por falta del anexo DGC |
| Verificación de tablas y cobertura en copia pública | Correcta con el nuevo lanzador |
| Comando desde otro directorio | Correcto; prueba de integración incluida |
| Comando inexistente | Rechazado con código 2; prueba incluida |
| JSON a CSV en carpeta temporal | Correcto; sin modificar fuentes originales |
| Regeneración de resumen y figuras | Correcta; mantiene el README corto y actualiza docs/resultados.md |
| Sintaxis, enlaces vigentes y git diff --check | Correctos |
| Modelos 2024 | 18 evaluaciones, nueve métricas reproducidas en cada una |
| Candidata 2023/2024 y persistencia | Correctas; detalle abajo |

Las 18 evaluaciones abarcan tres familias en ruta completa, nueve variantes en
la cohorte cubierta y seis híbridos. Se compararon con metricas.csv, usando
rtol=1e-9 y atol=1e-10. Las constantes numéricas del código científico se conservaron;
el generador solo añade índices 0/1 para resolver enlaces.

Entorno de esta comprobación: Python 3.13.3, .venv de trabajo. La prueba pública
verifica ausencia de dependencias en fuentes locales; no es una nueva instalación
limpia de paquetes. El entorno aislado documentado el 13/11 se conserva como evidencia
anterior. No se editaron notebook ni presentación y no se certificó operación futura.

## Trazabilidad

El registro config/migracion_estructura.csv conserva ubicación y hashes antes/después.
Las auditorías originales se mantienen. El verificador distingue integridad de
archivos originales de compatibilidad con los cambios de organización registrados;
no describe ambos códigos como binariamente idénticos.

## Detalle de la candidata

### Verificación de cierre

Fecha UTC: 2026-11-14T16:34:35.660824+00:00

Modo: tablas y artefactos locales. Estado: CORRECTO.

Commit de entrada: `974c8cd8d8e24c3a23bb0c0e8729e2731cd431d2`. Cambios locales al registrar: sí.

Verificador SHA256: `a120dc8647dc3366b20f9e015ecaa0f627156902c85eee89af5b257b9ff99ccd`.

Python: 3.13.3 (Linux x86_64).

- numpy: 2.2.3
- pandas: 2.2.3+dfsg
- scipy: 1.14.1
- scikit-learn: 1.6.1
- matplotlib: 3.8.3
- joblib: 1.6.0
- threadpoolctl: 3.8.0
- xlrd: 2.0.1

### Comprobaciones

- Integridad de código y siniestros comprobada; cambios de rutas trazados en config/migracion_estructura.csv. Las auditorías originales se conservan.
- 114 filas de métricas completas: cohortes, población, escala, O/E y referencia M0 coherentes.
- 36 selecciones y 60 búsquedas verificadas; candidata: Poisson_clima.
- 81 diferencias de captura e IC coherentes; 360 deciles concilian con sus cohortes.
- Recalibración coherente con factores del año anterior; manifiesto de reajuste conciliado.
- Clima, calendario, anexos DGC y artefactos finales coinciden con sus hashes.
- Predicciones 2023 originales y recalibradas reproducen las 9 métricas (rtol=1e-9, atol=1e-10).
- SHA256 evaluado 2023: 4313503dbdc59af570aa6225ea565f9f916a854e7e629e530ede8a01f8cc1390
- Predicciones 2024 originales y recalibradas reproducen las 9 métricas (rtol=1e-9, atol=1e-10).
- SHA256 evaluado 2024: 2d7fb99f790c7e29f5c7de90e63cf658a7fbb17694367e6d19c700b040dbca36
- Reajuste 2020-2024: 1.000 predicciones válidas y persistencia idéntica; sin evaluación futura.

No descarga, reentrena ni modifica las fuentes o resultados de modelado. No sustituye las pruebas unitarias ni valida pronósticos futuros. El modo de tablas comprueba coherencia interna, no recalcula predicciones ni intervalos.
