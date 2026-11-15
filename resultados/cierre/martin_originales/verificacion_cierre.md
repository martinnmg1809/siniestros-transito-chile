# Verificación de cierre

Fecha UTC: 2026-11-15T02:19:57.890477+00:00

Modo: tablas y artefactos locales. Estado: CORRECTO.

Commit de entrada: `df3f6df29c93ef01144cdfc79d377cfe0a00375e`. Cambios locales al registrar: sí.

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

## Comprobaciones

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
