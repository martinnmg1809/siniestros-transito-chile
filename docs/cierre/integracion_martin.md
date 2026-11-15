# Integración y revisión del aporte de Martín

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.
Integración: 14/11/2026, Diego con asistencia de Codex.

## Material recibido

Se incorporó por fast-forward la rama
`claude/planning-pending-work-asvuvw`, hasta `df3f6df`. Conserva seis commits de
Martín (`125ebbb`, `b4483bb`, `d2341c4`, `d757ef0`, `c28e749`, `df3f6df`) y el
merge de main `79b32d8`. La solicitud #1 estaba cerrada sin fusionar; esta
integración utiliza sus commits publicados sin reescribirlos.

Incluye las fichas [03](03_modelo_final.md) y [03b](03b_ficha_modelo.md),
`contrastes_poisson`, `tendencia_anual`, siete pruebas y cuatro salidas en
`resultados/cierre`: contrastes, ejemplo de turno, diagnóstico de tendencia e
inventario de versiones. El historial conserva la asistencia de Claude declarada
por Martín. Las precisiones documentales de esta revisión se atribuyen a la
integración de Diego con Codex.

## Selección y reproducción comprobadas

Se recalcularon los promedios 2022/2023 desde las métricas originales: GB obtiene
19,114 % y Poisson 19,089 %, separados por 0,025 puntos, dentro de la tolerancia
prefijada de 0,1 pp. Poisson se mantiene por la regla de sencillez. La configuración
L2=0,3 de 2024 procede de los años anteriores, aunque las predicciones empleadas
para seleccionar la familia usaban L2=3 en 2022/2023. No se usa 2024 para cambiar
la elección. La tabla de selección comprobada está en
[seleccion_comprobada.csv](../../resultados/cierre/martin_originales/seleccion_comprobada.csv).

La reproducción independiente de Martín fue recibida como tal: reajustó los modelos
sin los joblib originales y documentó diferencias numéricas pequeñas. Durante la
integración se ejecutó `contrastes_poisson` usando los **artefactos originales**,
con salida temporal. No descargó ni volvió a entrenar modelos. Se ejecutó además
`tendencia_anual` y `verificar_cierre --con-artefactos`.

- Las nueve métricas de 2024 del artefacto original cumplen la tolerancia relativa
  de 1e-10 del script; el mayor desvío relativo es del orden de 3e-15.
- El verificador completo reproduce las nueve métricas originales y recalibradas
  de 2023/2024 y confirma la persistencia del reajuste final sobre 1.000 filas.
- Los 56 contrastes conservan exactamente los mismos números de pares observados
  que la reproducción de Martín. La diferencia absoluta máxima de razón es
  0,000120, compatible con los ajustes numéricamente próximos. No se afirma
  identidad de coeficientes ni de las salidas completas.
- El diagnóstico agregado de tendencia coincide a rtol=1e-9 y atol=1e-10.
- Pasan **85 pruebas, sin omisiones**, incluyendo las nuevas pruebas de Martín
  y las de sensibilidad e insumos del piloto realizadas antes de esta integración.

## Dos registros que deben distinguirse

| Ubicación | Qué identifica |
|---|---|
| resultados/cierre/version_modelo.json y CSV originales de Martín | Reproducción independiente con modelos reajustados por Martín |
| resultados/cierre/martin_originales/ | Contrastes y turno usando los joblib originales de Diego; selección cotejada y auditoría de integración |

Los cuatro archivos recibidos se conservan intactos. La nueva
[auditoría](../../resultados/cierre/martin_originales/auditoria.json) registra sus
hashes, el inventario de seis artefactos originales, el código, las diferencias y
las huellas de las salidas. El informe del verificador completo se conserva en
[verificacion_cierre.md](../../resultados/cierre/martin_originales/verificacion_cierre.md).
Los joblib permanecen locales y excluidos de Git.

Con el modelo evaluado original, la razón lluvia/seco es aproximadamente 2,11;
llovizna/seco, 1,28. La tendencia anual es ×1,05363 para el evaluado y ×1,00191
para el reajustado. El turno histórico del 12/07/2024 12:00–24:00 tiene 6,344
esperados originales, 4,243 en la variante recalibrada y 5 observados. El reajuste
independiente daba 6,35 al redondear: ambos resultados tienen su procedencia
identificada. Un turno no acredita el desempeño general del modelo.

## Precisiones de interpretación

Se ajustó la redacción de las fichas para distinguir diagnóstico y causalidad.
La semejanza entre un modelo agregado de tendencia y el O/E de Poisson, junto con
su coeficiente anual, respalda una explicación por extrapolación temporal. No es
una intervención que aísle toda la causa del sesgo ni acredita el efecto de la
pandemia sobre los totales. Tampoco se atribuyen las razones horarias principalmente
al volumen de vehículos sin medirlo.

El factor recalibrado de referencia del reajuste final procede del modelo evaluado,
con tendencia distinta. No tiene validación futura; el piloto ya lo muestra aparte
de la candidata original. Se conserva la especificación científica actual. Las
sensibilidades urbana y de lluvia son evidencia complementaria, documentada en
[su informe](../sensibilidad.md), sin reselección de familia o cortes.

## Reproducción de la revisión

```bash
# Escribir en una carpeta nueva para conservar las salidas de ambas reproducciones.
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python proyecto.py contrastes_poisson --salida /tmp/martin_originales_nuevo
.venv/bin/python proyecto.py tendencia_anual --salida /tmp/martin_originales_nuevo
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python proyecto.py verificar_cierre --con-artefactos
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python -m unittest discover -s tests -v
```

La parte técnica de Martín y la comprobación solicitada a Diego quedan integradas.
Las fichas no equivalen a una firma del acta: el equipo debe leer y aprobar su texto
antes de registrarla. Quedan el notebook documentado, la presentación y su revisión
conjunta. La evaluación observada del piloto requiere una fuente completa aún no
acreditada; 2025 sigue excluido por falta de ubicación vial comparable.
