# Verificación de cierre

Fecha UTC: 2026-11-13T22:52:26.090290+00:00

Modo: tablas y artefactos locales. Estado: CORRECTO.

Commit de entrada: `0c5e42c76357edbee167dbe4074ab0d9a8ca358b`. Cambios locales al registrar: sí.

Verificador SHA256: `e005a8df55eb3f1f5705ee57b84cb938f00a91de4a5851d1c390a030012de1ed`.

Python: 3.12.14 (Linux x86_64).

- numpy: 2.2.3
- pandas: 2.2.3
- scipy: 1.14.1
- scikit-learn: 1.6.1
- matplotlib: 3.9.4
- joblib: 1.6.0
- threadpoolctl: 3.8.0
- xlrd: 2.0.1

## Comprobaciones

- Código de modelado y fuente de siniestros coinciden con los hashes de la corrida.
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
