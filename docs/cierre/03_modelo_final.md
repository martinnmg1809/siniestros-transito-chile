# Cierre técnico 3/4: modelo final

**Responsable:** Martín · **Revisor:** Diego (reproducción) · **Cifras:** Cristóbal
**Base:** commit `0c5e42c` (los hashes de código coinciden con `resultados/modelos/auditoria.json`)
**Estado al 13/11/2026:** borrador del Día 1. La auditoría de la selección, el inventario
de versiones y la recalibración están completos y se verificaron con las salidas versionadas.
Los contrastes del modelo tienen script y pruebas, pero **todavía no tienen resultados**
(véase [Bloqueo](#bloqueo-y-cómo-completar-los-contrastes)).

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
transformador. Esa huella no depende de la serialización de joblib, así que permite
confirmar que dos ajustes son el mismo modelo aunque el archivo cambie.

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
  **no tiene prueba**.
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
- Es una reconstrucción aproximada, sin L2 ni el resto de los atributos. La cifra exacta
  del modelo real (`razon_tasa_por_anio_tendencia`) la registra `contrastes_poisson.py`.
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
"¿cuánto cambia la tasa esperada si cambia solo un atributo?":

- **Pares observados, no combinaciones inventadas.** Toma las combinaciones observadas en
  2024 (tramo, hora, día, mes, feriado, lluvia, trimestre) y forma pares que difieren
  solo en el atributo contrastado. Usa el mismo constructor `datos_modelado.atributos`
  que el entrenamiento y no modifica atributos con reglas paralelas.
- **Contrastes definidos antes de ver resultados:**
  - lluvia: llovizna (0,1–0,5 mm/h) y lluvia (≥0,5 mm/h) frente a seco (<0,1 mm/h);
  - feriado: inicio, día intermedio y último día frente a día no feriado;
  - hora: cada hora frente a las 12:00.
- **Qué se informa:**
  - el número de pares y la razón de tasas (mediana, mínimo y máximo);
  - un ejemplo con tramo (km), fechas reales de 2024, horas de exposición y tasa por
    hora de cada lado.

  El ejemplo es el par con más horas de exposición. Se elige sin mirar siniestros.
- **Cómo leer las razones:**
  - el modelo es log-lineal y no tiene interacciones, así que la razón debe ser igual en
    todos los pares (mínimo = máximo). Las pruebas lo verifican;
  - una razón de 1,3 para la lluvia significa que el modelo espera 30 % más siniestros
    por hora que con seco, en el mismo tramo, hora, día y mes;
  - es una **asociación del modelo**, no un efecto causal, no es riesgo por vehículo-km
    y puede reflejar cambios de exposición no medidos, como un menor tráfico con lluvia;
  - la penalización L2 acerca las razones a 1;
  - solo se interpretan **diferencias entre categorías**, nunca un coeficiente aislado de
    la codificación completa.
- **Ejemplo por turno**, en `ejemplo_turno_poisson.csv`:
  - turno fijado a priori: viernes 12/07/2024, de 12:00 a 24:00, hora local;
  - incluye los tramos que entran en el presupuesto del 5 %, con sus conteos esperados
    original y recalibrado (× 0,6687, factor de 2023) y lo observado;
  - la última fila es el agregado de la ruta.

  Es un ejemplo histórico. Un solo turno no mide precisión por tramo. El MAE registrado
  es el error del total de la ruta por turno, no un error por tramo.

## Bloqueo y cómo completar los contrastes

Para reconstruir el modelo se necesitan `clima_ruta5.npz` (ERA5), `feriados.json` y los
anexos DGC, y ninguno de ellos está en Git. En esta sesión:

- `feriados.json` se descargó y su sha256 `1240f908…7b19` coincide con
  `resultados/eda/auditoria.json`;
- los anexos DGC 2023-4T y 2024-4T coinciden con los hashes de `auditoria.json`;
- **ERA5 quedó bloqueado:** Open‑Meteo respondió *"Daily API request limit exceeded"*.

Hay dos formas de completarlo:

1. **Recomendada:** Diego, que tiene `clima_ruta5.npz` y `resultados/modelos/artefactos/`,
   ejecuta:
   ```
   .venv/bin/python contrastes_poisson.py
   ```
   Con los artefactos, el script verifica las métricas de 2024 con tolerancia 1e-10 y
   registra el sha256 de cada archivo. Así se cumple también la comprobación de recarga
   acordada con Diego.
2. Sin artefactos, el script reajusta las dos versiones con la configuración ya elegida
   (alrededor de 1 minuto cada una) y se detiene en dos casos:
   - si el evaluado no reproduce `metricas.csv` de 2024 (tolerancia 1e-6);
   - si el reajustado no reproduce el objetivo de `reajuste.json`.

   Antes hay que regenerar ERA5 con `python clima_utc.py` cuando la API lo permita, y
   comprobar que el hash del caché sea igual a `clima_cache_sha256` en `auditoria.json`.
   `version_modelo.json` registra ambos hashes.

Salidas: `resultados/cierre/contrastes_poisson.csv`, `ejemplo_turno_poisson.csv` y
`version_modelo.json`. Pruebas: `tests/test_contrastes.py`, con 5 casos sobre datos
sintéticos que verifican el emparejamiento, la constancia de las razones, la invariancia
ante recalibración y el presupuesto del turno.

## 5. Borrador del acta (para firmar el Día 2 con la tabla de Cristóbal)

> El modelo principal para priorizar tramos y horas es **Poisson_clima** (`l2 = 0,3`).
> Se eligió con la captura global al 5 % promediada en 2022 y 2023, con preferencia por
> la solución más simple a ≤0,1 pp del mejor promedio. El año 2024 no se usó para elegir.
> En la evaluación histórica de 2024 captura 19,00 %, frente a 14,89 % de M1
> (+4,11 pp, IC 95 % [2,10; 6,08]). En ese año, Gradient Boosting obtuvo mejores
> métricas, lo que no cambia la elección. Los conteos esperados requieren recalibración
> con el O/E del año anterior. La recalibración cambia la escala, no el orden. Su
> resultado en 2024 pasó de sobreestimar a subestimar. El artefacto reajustado con
> 2020–2024 no tiene prueba futura y queda como artefacto de investigación. El modelo
> predice conteos por hora con lluvia de reanálisis (no pronósticos emitidos) y no
> estima riesgo por vehículo-km.

## Pendientes

- [ ] Ejecutar `contrastes_poisson.py` (Diego o tras regenerar ERA5) e incorporar cifras
      a la sección 4.
- [x] Hipótesis de tendencia respaldada con `tendencia_anual.py`. Falta registrar la cifra exacta del modelo (`razon_tasa_por_anio_tendencia`).
- [ ] Cristóbal: verificar las cifras de las secciones 1 y 3 contra su tabla maestra.
- [ ] Día 2: firmar el acta (sección 5) y registrar el sha256 de los artefactos evaluados.
