# Integración técnica del trabajo de Vicente

Fecha: 14/11/2026. Integración por Diego con asistencia de Codex.
Base de Diego: a65a02d. Rama recibida: cierre/vicente-flujo, punta a7b8e01.
Se conservaron sus seis commits mediante avance directo de main.

## Comprobaciones ejecutadas

- La regeneración original con `cierre_flujo.py` produjo un CSV idéntico al recibido.
- El nuevo `cierre_flujo.py --comprobar` concilia la tabla sin escribir archivos.
- La suite completa pasó: 43 pruebas, ninguna omitida con las fuentes locales.
- Tres pruebas nuevas detectan una tabla alterada o ausente y verifican que la
  comprobación no sobrescribe los archivos.
- La tabla de bootstrap confirma nueve comparaciones de flujo en 153 tramos;
  solo GB 2022 tiene un IC que excluye cero. Se comprobaron siete diferencias
  negativas de nueve en los híbridos, como registra la ficha de Vicente.
- Se contrastaron afirmaciones de disponibilidad con las páginas oficiales DGC
  y Open-Meteo; se precisó el alcance, sin descargar nuevas fuentes de modelado.
- `git diff --check` sin errores. No se entrenaron modelos ni se modificaron
  fuentes, filtros, parámetros, particiones o métricas.

Entorno utilizado hoy: .venv de trabajo, Python 3.13.3 y paquetes del sistema.
No es una nueva comprobación de instalación aislada; esa evidencia del 13/11
se conserva en la ficha de Diego. Los detalles de predicción siguen abajo.

## Archivos incorporados y comprobados

- `cierre_flujo.py`: SHA256 `4180f57c712043de226b794112c619ec8759f3b7107f473b0fe7f575bae98471`.
- `docs/cierre/02_datos_flujo.md`: SHA256 `ad0782152b3278ddb483278ff71204f0e8d6ad8ca939accfe26af9301cca7820`.
- `resultados/cierre/cobertura_flujo_detalle.csv`: SHA256 `5d932935cf5a09363017f189185c93adbd228b342ce5c3e928edd137155bef3d`.
- `resultados/cierre/fuentes_flujo.csv`: SHA256 `7a4d250ab903f253a8da42b1bbd0a5f1a70c554311146a443e5b9c1456b1b619`.
- `resultados/cierre/matriz_compromisos.csv`: SHA256 `1c6321d903ab62a9f5887919bbfea68e984010efdbf3bd82236b02150f2fa61e`.

## Reproducción de modelos posterior a la integración

### Verificación de cierre

Fecha UTC: 2026-11-14T16:20:07.152853+00:00

Modo: tablas y artefactos locales. Estado: CORRECTO.

Commit de entrada: `a7b8e011e2004464bbe0b04efb9771bfaaa90017`. Cambios locales al registrar: sí.

Verificador SHA256: `e005a8df55eb3f1f5705ee57b84cb938f00a91de4a5851d1c390a030012de1ed`.

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

## Pendientes humanos y entregables

Cristóbal debe revisar la ficha 02 y entregar su interpretación; Martín debe
cerrar la ficha del modelo y revisar la reproducción de Diego. Se actualizaron
README y docs/cierre/00_estado_entrega3.md según el anuncio docente recibido.
Notebook documentado y presentación siguen pendientes de la etapa final.
No se ha hecho un envío académico ni se ha marcado una revisión humana como aprobada.
