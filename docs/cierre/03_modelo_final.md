# Cierre técnico 3/4: modelo final

**Responsable:** Martín · **Revisor:** Diego (reproducción) · **Cifras:** Cristóbal
**Base:** commit `0c5e42c` (los hashes de código coinciden con `resultados/modelos/auditoria.json`)
**Estado al 14/11/2026:** completo para revisión. La selección, las versiones, la
recalibración y los contrastes están verificados. Faltan la firma del acta y la revisión
cruzada del Día 2 (véase [Pendientes](#pendientes)).

Resumen de una página para la presentación: [03b_ficha_modelo.md](03b_ficha_modelo.md).

Este documento no cambia modelos, datos ni métricas. No vuelve a elegir modelo ni amplía la grilla.

## 1. La decisión: `Poisson_clima`, elegido sin usar 2024

### Regla aplicada

[`entrenar_comparacion.py`](../../entrenar_comparacion.py) aplica la regla registrada en
`auditoria.json`:

1. Para cada solución de toda la ruta se promedia la captura global al 5 % de las pruebas
   **2022 y 2023**. M0 queda fuera y 2024 no interviene.
2. Se consideran equivalentes las soluciones a ≤0,1 pp del mejor promedio.
3. Entre las equivalentes se elige la primera de este orden de sencillez:
   M1 → Poisson → Gradient Boosting → Random Forest (sin flujo) → híbridos sin flujo
   → híbridos con flujo.

### Verificación (recalculada desde `metricas.csv`)

| Solución | 2022 | 2023 | Promedio | ¿A ≤0,1 pp del mejor? |
|---|---|---|---|---|
| GradientBoosting_clima | 19,50 % | 18,73 % | **19,114 %** (mejor) | sí |
| Poisson_clima | 19,56 % | 18,62 % | 19,089 % | **sí (−0,025 pp)** |
| Hibrido_Poisson_clima | 19,50 % | 18,65 % | 19,077 % | sí (−0,038 pp) |
| Hibrido_GradientBoosting_clima_flujo | 19,12 % | 18,58 % | 18,849 % | no |
| Hibrido_GradientBoosting_clima | 19,32 % | 18,30 % | 18,813 % | no |
| Hibrido_Poisson_clima_flujo | 19,15 % | 18,41 % | 18,776 % | no |
| RandomForest_clima y sus híbridos | | | 15,4–15,9 % | no |
| M1 | 15,78 % | 14,50 % | 15,144 % | no |

El umbral es 19,014 %. Hay tres soluciones equivalentes y, según el orden de sencillez,
la elegida es **Poisson_clima**. El híbrido Poisson no se prefiere porque añade un
especialista sin mejorar el criterio. Además, ninguna variante con flujo alcanza el umbral.

### Parámetros: por qué el artefacto usa `l2 = 0,3`

La regularización se elige dentro de la familia con la misma regla. La configuración 0
(`l2 = 3,0`, penalización más fuerte) es la más simple.

| Prueba | Captura `l2=3,0` | Captura `l2=0,3` | Elegida con | Configuración usada |
|---|---|---|---|---|
| 2022 | 19,56 % | 19,59 % | prefijada | `l2 = 3,0` |
| 2023 | 18,62 % | 18,86 % | 2022 (diferencia 0,03 pp ≤ 0,1) | `l2 = 3,0` |
| 2024 | — | 19,00 % | promedio 2022/2023: 19,089 % frente a 19,226 % (0,137 pp > 0,1) | **`l2 = 0,3`** |

El 19,09 % que justifica el **nombre** del modelo se obtuvo con `l2 = 3,0`, que era la
configuración vigente en esos años. El modelo evaluado en 2024 y el reajustado usan
`l2 = 0,3`, elegida con 2022/2023 antes de mirar 2024. Ambas cosas son coherentes con el
protocolo, pero hay que explicarlas para que no parezca un cambio de parámetros sin motivo.

### Lo que la elección no afirma

- **Poisson no gana en todas las métricas.** En 2024, Gradient Boosting supera a Poisson
  en captura global (20,00 % frente a 19,00 %), captura por turno (17,26 % frente a
  15,84 %), O/E (0,87 frente a 0,77) y MAE por turno (1,75 frente a 1,97). Ese resultado
  **no puede cambiar la elección de forma retroactiva**: 2024 es la evaluación histórica,
  no un año de selección.
- **La debilidad de Poisson en calibración ya se veía antes de 2024.** En 2022 y 2023, su
  O/E fue 0,69 y 0,67, frente a 1,02 y 0,85 de GB, y su MAE por turno fue 2,92 y 2,54,
  frente a 2,02 y 1,87. El criterio principal es la capacidad de ordenar tramos (captura),
  por eso estas cifras no cambian la elección. Sí obligan a tratar la escala de los
  conteos por separado (sección 3).
- **Argumentos a favor de la sencillez, sin usarlos como criterio a posteriori:**
  - la brecha entre train y prueba es menor que la de GB en los tres años (5,0/4,1/2,7 pp
    frente a 11,8/8,9/6,0 pp);
  - la estructura log-lineal se interpreta como razones de tasas;
  - el modelo no necesita flujo, así que cubre los 255 tramos.
- La ventaja frente a M1 se mantiene en los tres años: +3,78 pp [1,41; 6,09],
  +4,11 pp [1,97; 6,12] y +4,11 pp [2,10; 6,08], según `bootstrap.csv`. Esos intervalos
  mantienen fijas las predicciones y la selección.

## 2. Inventario de versiones

| Versión | Ajuste | Parámetros | Recalibración | Evidencia fuera de muestra | Archivo y huella |
|---|---|---|---|---|---|
| Pruebas 2022 / 2023 | 2020–2021 / 2020–2022 | `l2 = 3,0` | no | sí: 2022 y 2023 (selección) | `ruta_completa_Poisson_clima_{2022,2023}.joblib`; sin hash registrado |
| **Evaluado 2024** | 2020–2023 | `l2 = 0,3` | no | **sí: 2024 (histórica reutilizada)** | `ruta_completa_Poisson_clima_2024.joblib`; sin hash registrado |
| Evaluado 2024 recalibrado | 2020–2023 | `l2 = 0,3` | × 0,6687 (O/E de 2023) | sí: 2024 | `candidato_evaluado2024_recalibrado_con2023.joblib`; sin hash registrado |
| Reajustado | 2020–2024 | `l2 = 0,3` | no | **ninguna** | `candidato_reajustado2020_2024.joblib`, sha256 `6a4e9ed2…6e48`; 175 iteraciones, objetivo 91 903,604 |
| Reajustado recalibrado | 2020–2024 | `l2 = 0,3` | × 0,7720 (O/E de 2024) | **ninguna** | `candidato_reajustado2020_2024_recalibrado_con2024.joblib`, sha256 `0cb2dfd3…7d55` |

Los artefactos están en `resultados/modelos/artefactos/`, que Git excluye. Según
`reajuste.json`, el artefacto evaluado reproduce las métricas de 2024 con tolerancia
1e-10 y el reajustado devuelve predicciones idénticas al recargarse (1.000 filas).

**Qué versión se entrega y para qué:**
- Las cifras de desempeño y la interpretación corresponden al **evaluado 2024**, porque es
  la única versión `l2 = 0,3` con prueba fuera de muestra.
- El **reajustado 2020–2024** es un artefacto de investigación para un horizonte
  posterior. No tiene evaluación propia y no reemplaza al prototipo operativo de la página.

**Brecha detectada:** el repositorio no registra el sha256 de los artefactos evaluados
(2022–2024). [`contrastes_poisson.py`](../../contrastes_poisson.py) agrega a
`resultados/cierre/version_modelo.json` una huella de los coeficientes y del
transformador. Esa huella no depende de la serialización de joblib.

**Reproducción independiente (14/11/2026).** Sin los artefactos originales, ambas
versiones se reajustaron desde cero con:
- el código versionado (hashes iguales a los de `auditoria.json`);
- el caché ERA5 regenerado, cuyo sha256 `6dbd686c…ff4c` es **idéntico** al registrado;
- las versiones de bibliotecas de la auditoría: numpy 2.2.3, scipy 1.14.1, pandas 2.2.3
  y scikit-learn 1.6.1.

| Versión | Objetivo registrado | Objetivo reajustado | Desvío relativo | Iteraciones (reg. / local) |
|---|---|---|---|---|
| Evaluado 2024 | 74 822,81131 | 74 822,81113 | 2,4e-9 | 179 / 198 |
| Reajustado 2020–2024 | 91 903,60439 | 91 903,60430 | 9,7e-9 | 175 / 182 |

Los dos ajustes alcanzan el mismo óptimo; el local queda incluso marginalmente más abajo.
L-BFGS se detiene en otro punto de una región casi plana según el orden de las
operaciones de punto flotante. Por eso las métricas de 2024 del evaluado reajustado
coinciden así con `metricas.csv`:
- captura al 5 % y por turno: idénticas (desvío ~3e-16);
- captura al 20 %: idéntica;
- esperados, O/E y MAE: desvío ≤1,8e-4 relativo (3.374,80 frente a 3.374,25 esperados);
- captura al 10 %: desvío 3,2e-4.

El script exige el objetivo a 1e-8, la captura al 5 % a 1e-6 y el resto a 1e-3. Con los
artefactos originales exige 1e-10 en todas las métricas. Las huellas locales son
`7d491358…05b9` (evaluado) y `daa05dae…3d30` (reajustado). No equivalen a las de los
archivos de Diego.

## 3. Recalibración: escala de conteos, separada del ranking

Las cifras provienen de `recalibracion_candidato.csv`:

| Año evaluado | Factor (año) | O/E original → recalibrado | MAE/turno original → recalibrado | Captura 5 % |
|---|---|---|---|---|
| 2023 | 0,6932 (2022) | 0,669 → 0,965 | 2,536 → 1,784 | 18,62 % (sin cambio) |
| 2024 | 0,6687 (2023) | 0,772 → 1,154 | 1,970 → 1,684 | 19,00 % (sin cambio) |

- Un factor global positivo **cambia la magnitud, no el orden**: captura global, captura
  por turno y curva de captura quedan iguales.
- El factor de 2024 (0,6687) es el O/E del modelo de **2023, ajustado con `l2 = 3,0`**, y se aplica al modelo de 2024 con `l2 = 0,3`. No filtra información de 2024, pero proviene de otra configuración. Dado que la escala la domina la tendencia anual (ver más abajo), el efecto de `l2` sobre el factor debería ser menor. No está medido.
- El factor se toma **del año anterior**. Si se calculara con el año que se quiere
  predecir, se usaría el resultado para corregir la predicción.
- En 2024, la recalibración baja el MAE, pero pasa de sobreestimar (O/E 0,77) a
  subestimar (O/E 1,15). Por eso no debe presentarse como una calibración resuelta.
- El factor 0,7720 del artefacto reajustado está pensado para un año posterior a 2024 y
  **no tiene prueba**. Además, ese factor corrige el sesgo del modelo *evaluado*, cuya
  tendencia era ×1,054/año. El reajustado casi no tiene tendencia (×1,002/año), así que
  hereda una corrección pensada para otro sesgo (véase la subsección siguiente).
- No se reutiliza el multiplicador de lluvia del prototipo antiguo ni sus intervalos.

### Por qué Poisson sobreestima: la tendencia anual aprende de 2020

En los tres años de prueba, O/E ≈ 1 en entrenamiento y O/E < 1 en prueba. El modelo
incluye una tendencia anual numérica, y 2020 (pandemia, 2.295 siniestros) deprime el
inicio de la serie. El modelo aprende un "aumento" y lo proyecta hacia años en que los
siniestros bajaron: 3.369 en 2022, 2.863 en 2023 y 2.605 en 2024.

[`tendencia_anual.py`](../../tendencia_anual.py) lo comprueba solo con salidas versionadas.
Para cada año de prueba ajusta un Poisson con **solo intercepto y tendencia** sobre los
totales de entrenamiento y compara su O/E extrapolado con el registrado
(`resultados/cierre/tendencia_anual.csv`):

| Prueba | Entrenamiento | Factor anual ajustado | O/E solo tendencia | O/E Poisson_clima | O/E GB | O/E M1 |
|---|---|---|---|---|---|---|
| 2022 | 2020–2021 | × 1,44 | 0,71 | 0,69 | 1,02 | 1,21 |
| 2023 | 2020–2022 | × 1,20 | 0,67 | 0,67 | 0,85 | 0,96 |
| 2024 | 2020–2023 | × 1,06 | 0,76 | 0,77 | 0,87 | 0,88 |

La extrapolación de la tendencia por sí sola reproduce casi exactamente la sobreestimación
registrada en los tres años. Gradient Boosting no extrapola: sus árboles mantienen el
último nivel aprendido, y por eso su O/E es mejor. M1 usa la tasa media de los años de
entrenamiento, sin tendencia.

Alcance de esta evidencia:
- **Confirmado con el modelo real:** `version_modelo.json` registra una tendencia de
  **×1,054/año** en el evaluado 2024; la aproximación daba ×1,063.
- **Al incluir 2024, la tendencia casi desaparece:** el reajustado 2020–2024 tiene
  ×1,002/año. Con una tendencia plana, el modelo promedia los cinco años. La
  aproximación de solo tendencia con 2020–2024 deja su nivel de 2024 en 2.928 esperados
  frente a 2.605 observados (O/E ≈ 0,89 dentro de muestra) y proyecta unos 2.940 para
  2025. Si 2025 se pareciera a 2024, el factor 0,7720 llevaría O/E de ≈0,89 a ≈1,15.
  Es el mismo patrón de corrección excesiva de 2023 y 2024. Es una aproximación, no una
  prueba, pero basta para **no presentar el reajustado recalibrado como calibrado**.
- **No afecta la elección:** el término de tendencia multiplica por igual a todas las
  filas de un mismo año, así que no cambia el orden de priorización ni la captura.
  Afecta solo la escala de los conteos, que es lo que corrige la recalibración.
- Explica por qué la recalibración con el año anterior **corrige de más** en los dos
  años con prueba (O/E recalibrado 0,965 en 2023 y 1,154 en 2024). El factor hereda el
  sesgo de un ajuste con una tendencia distinta. Por la misma razón, el factor 0,7720 del
  reajustado 2020–2024 no debe tomarse como calibración validada.
- **No se modifica el modelo ahora:** cambiar la tendencia sería una nueva
  especificación elegida después de ver 2024. Queda como trabajo futuro, por ejemplo con
  un año categórico de referencia o excluyendo 2020 de la tendencia, evaluado con un
  año nuevo.

## 4. Interpretación: contrastes de predicción

[`contrastes_poisson.py`](../../contrastes_poisson.py) responde preguntas del tipo
"¿cuánto cambia la tasa esperada si cambia solo un atributo?". Sus resultados están en
`resultados/cierre/contrastes_poisson.csv`.

**Método:**
- **Pares observados, no combinaciones inventadas.** Toma las combinaciones observadas en
  2024 (tramo, hora, día, mes, feriado, lluvia, trimestre) y forma pares que difieren
  solo en el atributo contrastado. Usa el mismo constructor `datos_modelado.atributos`
  que el entrenamiento.
- **Contrastes fijados antes de ver resultados:** lluvia frente a seco, cada posición de
  feriado frente a día no feriado y cada hora frente a las 12:00.
- **Razón constante, como se esperaba:** en todos los contrastes la razón es idéntica en
  todos los pares (mínimo = máximo), porque el modelo es log-lineal sin interacciones.
  Por eso una sola cifra resume cada contraste para cualquier tramo y fecha.

### Resultados (evaluado 2024; entre paréntesis, reajustado 2020–2024)

| Contraste | Referencia | Razón de tasas | Pares observados | Lectura |
|---|---|---|---|---|
| Llovizna (0,1–0,5 mm/h) | seco | **× 1,28** (1,30) | 175.689 | 28 % más siniestros esperados por hora |
| Lluvia (≥0,5 mm/h) | seco | **× 2,11** (2,10) | 120.365 | el doble de siniestros esperados por hora |
| Inicio de feriado largo | día no feriado | **× 1,18** (1,19) | 61.679 | más alto el día de salida |
| Día intermedio de feriado | día no feriado | **× 0,93** (0,93) | 97.045 | algo más bajo |
| Último día de feriado | día no feriado | **× 1,12** (1,16) | 67.649 | más alto el día de regreso |
| 02:00–05:00 | 12:00 | **× 0,44–0,48** | ~37.000 por hora | la mitad que a mediodía |
| 08:00 | 12:00 | **× 1,38** | 38.846 | punta de la mañana |
| 18:00 | 12:00 | **× 1,41** | 38.313 | punta de la tarde, la hora más alta |

Perfil horario completo frente a las 12:00 (evaluado):
- madrugada: 00 h ×0,56, 01 h ×0,51, 02 h ×0,44, 03 h ×0,46, 04 h ×0,48, 05 h ×0,47,
  06 h ×0,66;
- mañana: 07 h ×1,06, 08 h ×1,38, 09 h ×1,09, 10 h ×1,01, 11 h ×1,00;
- tarde: 13 h ×1,01, 14 h ×1,05, 15 h ×1,06, 16 h ×1,17, 17 h ×1,25, 18 h ×1,41,
  19 h ×1,27;
- noche: 20 h ×1,01, 21 h ×0,86, 22 h ×0,71, 23 h ×0,58.

Las dos versiones dan razones casi iguales (diferencias ≤0,04): la interpretación no
depende de si se incluye 2024.

**Ejemplo concreto (lluvia).** Tramo km 0–5, viernes de agosto de 2024 a las 03:00:
- seco (09/08): 0,00084 siniestros esperados por hora;
- lluvia ≥0,5 mm/h (02/08): 0,00176.

Los valores absolutos son pequeños porque un tramo de 5 km en una hora rara vez tiene un
siniestro. La utilidad está en sumar y ordenar muchas horas-tramo, no en predecir una sola.

**Cómo leer y cómo no leer estas cifras:**
- Son **asociaciones del modelo**, no efectos causales. El modelo predice conteos, no
  riesgo por vehículo-km.
- Lluvia, hora y feriado también cambian cuánto tráfico hay. Por ejemplo, ×0,44 a las
  02:00 refleja sobre todo menos vehículos, no conducción más segura. Las puntas de
  08:00 y 18:00 coinciden con los desplazamientos diarios. En feriados, el aumento al
  inicio y al final y la baja en los días intermedios coinciden con el patrón de salida
  y regreso.
- La lluvia es de reanálisis ERA5 en celdas de 0,25°, no la medida en la carretera ni un
  pronóstico emitido antes del turno.
- La penalización L2 acerca las razones a 1, así que pueden estar levemente atenuadas.
- Las cifras **no tienen intervalos de confianza**: no se reutilizan los intervalos del
  multiplicador de lluvia del prototipo antiguo.

### Ejemplo de turno y agregado de la ruta

El archivo es `resultados/cierre/ejemplo_turno_poisson.csv`. El turno se fijó a priori:
viernes 12/07/2024, de 12:00 a 24:00, hora local, con el modelo evaluado.

- **Presupuesto del 5 %:** 12,75 tramos (12 completos y el 13.º al 75 %). Encabezan
  km 190, 270, 220, 195 y 185, con 0,09–0,14 siniestros esperados en el turno.
- **En los tramos priorizados:** ocurrieron 2 de los 5 siniestros del turno (km 190 y
  km 95).
- **Agregado de la ruta:** 6,35 esperados (4,24 recalibrados con ×0,6687) frente a 5
  observados.

Es un ejemplo histórico ilustrativo: un turno no mide la precisión del modelo. El MAE
registrado (1,97; 1,68 recalibrado) es el error del **total de la ruta** por turno en
2024, no un error por tramo.

### Cómo se reprodujo

```
python feriados.py                     # sha256 igual a resultados/eda/auditoria.json
python flujo_concesiones.py --descargar  # anexos DGC con hashes de auditoria.json
python clima_utc.py                    # ERA5; sha256 igual a auditoria.json
python contrastes_poisson.py           # ~2 min; reajusta y verifica si no hay artefactos
python tendencia_anual.py              # solo usa salidas versionadas
```

Open‑Meteo limita las descargas: el 13/11 se agotó el cupo diario y la descarga se
completó el 14/11 con reintentos espaciados. Pruebas: `tests/test_contrastes.py` y
`tests/test_tendencia.py`, con datos sintéticos.

## 5. Borrador del acta (para firmar el Día 2 con la tabla de Cristóbal)

> El modelo principal para priorizar tramos y horas es **Poisson_clima** (`l2 = 0,3`).
> Se eligió con la captura global al 5 % promediada en 2022 y 2023, con preferencia por
> la solución más simple a ≤0,1 pp del mejor promedio. El año 2024 no se usó para elegir.
> En la evaluación histórica de 2024 captura 19,00 %, frente a 14,89 % de M1
> (+4,11 pp, IC 95 % [2,10; 6,08]). En ese año, Gradient Boosting obtuvo mejores
> métricas, lo que no cambia la elección. Los conteos esperados requieren recalibración
> con el O/E del año anterior. La recalibración cambia la escala, no el orden. Su
> resultado en 2024 pasó de sobreestimar a subestimar. La sobreestimación se explica por
> la tendencia anual aprendida desde 2020 (×1,054/año), sin efecto sobre el orden. El
> artefacto reajustado con 2020–2024 no tiene prueba futura y queda como artefacto de
> investigación; su factor de recalibración no se presenta como calibración validada.
> Asociaciones del modelo: lluvia ≥0,5 mm/h ×2,11 frente a seco; 18:00 ×1,41 y 02:00
> ×0,44 frente a las 12:00; inicio de feriado largo ×1,18. El modelo
> predice conteos por hora con lluvia de reanálisis (no pronósticos emitidos) y no
> estima riesgo por vehículo-km.

## Pendientes

- [x] Contrastes calculados y verificados (sección 4).
- [x] Tendencia confirmada con el modelo real (×1,054/año evaluado; ×1,002/año reajustado).
- [ ] Cristóbal: verificar las cifras de las secciones 1, 3 y 4 contra su tabla maestra.
- [ ] Diego: si conserva los artefactos originales, ejecutar `contrastes_poisson.py` con
      ellos (verificación a 1e-10) y registrar su sha256.
- [ ] Día 2: firmar el acta (sección 5).
