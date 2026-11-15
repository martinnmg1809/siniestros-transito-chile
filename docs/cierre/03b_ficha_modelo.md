# Ficha del modelo: Poisson_clima

Ficha de una página para la presentación (Máximo) y el notebook. El detalle y la
justificación están en [03_modelo_final.md](03_modelo_final.md). Todas las cifras
proceden del experimento en `resultados/modelos/` (base `0c5e42c`) y de los
contrastes de Martín. La [integración](integracion_martin.md) verificó los
artefactos originales y conserva ambas reproducciones.

## Qué es

| | |
|---|---|
| **Pregunta que responde** | ¿En qué tramos de 5 km de la Ruta 5 Sur y en qué horas se esperan más siniestros? |
| **Salida** | Conteo esperado de siniestros por tramo y hora local. Sirve para ordenar dónde y cuándo priorizar. |
| **No es** | Riesgo por vehículo-km, probabilidad de accidente por conductor ni efecto causal de la lluvia. |
| **Tipo** | Regresión de Poisson log-lineal con exposición horaria como offset y penalización L2 (`l2 = 0,3`). Sin interacciones. |
| **Atributos** | Tramo (255 tramos de 5 km), hora (24), día de la semana (7), mes (12), posición de feriado (no / inicio / intermedio / final), lluvia ERA5 en 3 niveles (<0,1, 0,1 ≤ p < 0,5 y ≥0,5 mm/h) y tendencia anual numérica. **Sin flujo vehicular.** |
| **Población** | 14.420 siniestros de 2020–2024 tras poner en cuarentena 5 registros con ubicación incompatible. No se imputa su ubicación. |
| **Código** | `modelos_conteo.py` (modelo), `datos_modelado.py` (atributos), `entrenar_comparacion.py` (evaluación), `reajustar_candidato.py` (reajuste). |

## Versiones

| Versión | Datos de ajuste | Uso |
|---|---|---|
| **Evaluado 2024** | 2020–2023 (11.815 siniestros) | Es la fuente de **todas las cifras de desempeño**. |
| Reajustado | 2020–2024 (14.420 siniestros) | Artefacto de investigación para un horizonte posterior. **No tiene prueba propia.** |

Las dos versiones tienen variantes recalibradas con un factor global: × 0,6687 (O/E de
2023) y × 0,7720 (O/E de 2024). El factor cambia la escala de los conteos, no el orden de
priorización. Ningún artefacto reemplaza al prototipo de la página web.
El factor del reajustado (× 0,7720) no se presenta como calibración validada: corrige un
sesgo de tendencia que el reajustado ya casi no tiene (× 1,002/año frente a × 1,054/año).

## Cómo se eligió

Se comparó la captura promedio de 2022 y 2023, con entrenamiento anterior a cada año y
**sin usar 2024**. Se eligió la solución más simple a ≤0,1 pp de la mejor.
Poisson_clima obtuvo 19,09 % y Gradient Boosting, 19,11 %.

## Desempeño (prueba histórica 2024, 255 tramos)

| Métrica | Poisson_clima | M1 (solo tramo) | Lectura |
|---|---|---|---|
| Captura al 5 % | **19,00 %** | 14,89 % | Con el 5 % de las horas-tramo se habrían cubierto el 19 % de los siniestros. |
| Diferencia frente a M1 | **+4,11 pp** [2,10; 6,08] | — | Ventaja similar en 2022 (+3,78) y 2023 (+4,11). |
| Captura por turno (5 %, 12 h) | 15,84 % | 14,89 % | Tramos fijos durante cada turno de 12 h de reloj local. |
| Observado/esperado | 0,77 | 0,88 | Sobreestima el total. Recalibrado con 2023: 1,15 (subestima). |
| MAE por turno | 1,97 (recalibrado: 1,68) | 1,86 | Error del **total de la ruta** por turno, no por tramo. |

## Advertencias para presentar

1. **2024 no es una prueba intacta.** Ya se había inspeccionado en entregas anteriores; es
   una evaluación histórica reutilizada.
2. **Gradient Boosting rindió mejor en 2024** (captura 20,00 %, O/E 0,87). No se cambia la
   elección porque 2024 no es un año de selección.
3. **La lluvia es de reanálisis** (ERA5), no de pronósticos emitidos antes de cada turno.
   El desempeño operativo con pronósticos no está medido.
4. **La captura no es igual a accidentes evitados.** Mide cuántos siniestros históricos
   caían en las horas-tramo priorizadas.
5. **Los intervalos** (2.000 remuestreos semanales) dejan fijas las predicciones. No
   incluyen la incertidumbre del reentrenamiento ni corrigen comparaciones múltiples.
6. **La extrapolación temporal contribuye al diagnóstico del sesgo.** El total de
   2020 es menor que los posteriores y la tendencia proyecta un aumento. Una
   aproximación de tendencia sola reproduce
   el O/E de 2022–2024 (0,71/0,67/0,76 frente a 0,69/0,67/0,77); en el modelo, × 1,054/año. Esto afecta la escala,
   no el orden de priorización (`tendencia_anual.py`).
7. **El flujo vehicular no se incluye.** El proxy DGC cubre 153 de 255 tramos y no mostró
   una mejora clara.

## Interpretación (razones de tasas, mismo tramo, día y mes)

| Condición | Frente a | El modelo espera |
|---|---|---|
| Lluvia ≥0,5 mm/h | seco | **× 2,11** siniestros por hora |
| Llovizna 0,1 ≤ p < 0,5 mm/h | seco | × 1,28 |
| 18:00 (hora más alta) | 12:00 | × 1,41 (08:00: × 1,38) |
| 02:00 (hora más baja) | 12:00 | × 0,44 |
| Inicio de feriado largo | día normal | × 1,18 (regreso: × 1,12; días intermedios: × 0,93) |

Son asociaciones del modelo, no causas. Las asociaciones horarias y de
feriados pueden incluir diferencias de circulación, cuya contribución no se midió;
la lluvia es de reanálisis. Las cifras no tienen intervalos de
confianza. La versión reajustada con 2020–2024 da razones casi iguales. Detalle y
reproducción en `03_modelo_final.md`, sección 4.
