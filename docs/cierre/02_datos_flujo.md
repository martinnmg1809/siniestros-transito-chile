# Datos y flujo · ficha de cierre

Versión: base `a65a02d` (rama `cierre/vicente-flujo`) · 14 de noviembre de 2026 · Autor: Vicente (con asistencia de Claude) ·
Revisor: Cristóbal (pendiente) · Población: 14.420 eventos / 255 tramos de 5 km.
Estado: borrador para revisión; nada de esta ficha se ha firmado por el revisor.

## 1. Resumen en cinco líneas

1. El "flujo" del modelo es un **proxy de circulación**: pasadas por punto de cobro y día, por contrato de concesión y trimestre.
2. Cubre **153 de 255 tramos** (50,1 % a 57,2 % de los eventos según el año); los otros 102 no tienen contrato utilizable.
3. Entra con rezago de dos trimestres. Ese rezago **no demuestra** que el dato estuviera publicado a tiempo (§5).
4. Con este proxy no hay mejora consistente de la captura: solo un intervalo (GB 2022) excluye cero y el signo se invierte en 2024.
5. No hay exposición vehicular validada (TMDA o vehículo-km): `exposicion_validada.csv` sigue vacía.

## 2. Qué es el flujo que usa el modelo

- **Fuente:** anexos trimestrales de la DGC (`2023_4t` y `2024_4t`; URL y sha256 en `resultados/flujo/fuentes_dgc.json`).
  Se usa la versión más reciente por contrato y trimestre (`serie_flujo`, `drop_duplicates(keep="last")`).
- **Fórmula:** `proxy = promedio mensual de pasadas por punto × 3 / días del trimestre`
  → **pasadas por punto de cobro y día** (`flujo_concesiones.py`).
- **Puntos implícitos:** `transacciones del trimestre / (3 × promedio mensual por punto)`. Se infiere por álgebra; **no es un censo de plazas**.
- **Granularidad:** contrato × trimestre. Todos los tramos de un contrato reciben el mismo valor.
- **Rezago:** trimestre objetivo − 2 (`flujo_rezagado`). Falla con `ValueError` si el trimestre medido termina después del inicio del objetivo.
- **Entrada al modelo:** `log(proxy)` y `log(puntos implícitos)` del trimestre rezagado.
- **Regla de cobertura:** un tramo cuenta solo si tiene proxy y puntos finitos en los 20 trimestres de 2020 a 2024.
- **Qué no mide:** vehículos únicos (un vehículo genera varias pasadas), flujo horario por tramo, vehículo-km, ni homogeneidad dentro del contrato.

Detalle por fuente: `resultados/cierre/fuentes_flujo.csv`.

## 3. Cobertura

Tabla completa en `resultados/cierre/cobertura_flujo_detalle.csv` (regenerable con `python cierre_flujo.py`).

| Año | Tramos con flujo | Siniestros con flujo / total | % eventos |
|---|---|---|---|
| 2020 | 153/255 | 1.149 / 2.295 | 50,07 % |
| 2021 | 153/255 | 1.669 / 3.288 | 50,76 % |
| 2022 | 153/255 | 1.872 / 3.369 | 55,57 % |
| 2023 | 153/255 | 1.577 / 2.863 | 55,08 % |
| 2024 | 153/255 | 1.491 / 2.605 | 57,24 % |

**Con contrato (153 tramos, seis contratos, siete intervalos):** Talca–Chillán 37, Chillán–Collipulli 30, Collipulli–Temuco 20
(dos intervalos por el bypass de Temuco: 585–650 y 685–710), Temuco–Río Bueno 33, Río Bueno–Puerto Montt 23, Puerto Montt–Pargua 10.

**Sin contrato (102 tramos).** Los cortes se derivan de `limites_documentados()`, no de constantes. Resultado del script, con eventos 2020–2024:

| Grupo | Tramos | Eventos (2020–2024) | Por qué |
|---|---|---|---|
| `antes_primer_contrato` (km 0–210) | 43 | 4.433 | Santiago–Talca existe en DGC, pero su fila agrega Acceso Sur a Santiago y no es separable; se excluye. |
| `despues_ultimo_contrato` (km 1080–1270) | 39 | 950 | Posterior a Puerto Montt–Pargua; incluye Chiloé, sin contrato en los anexos usados. |
| `frontera_bypass_margen` | 20 | 1.279 | Tramos 215 y 220 (margen de 1 km con Talca–Chillán), 410, 565–580 (frontera Collipulli discrepante entre documentos), 655–680 (bypass de Temuco con kilometraje propio), 715, 885–895, 1015–1020 y 1075. |

El plan de trabajo estimaba 45/40/17. La diferencia es de clasificación (215, 220 y 1075 caen en la frontera según los límites del código); el total de 102 coincide.

## 4. Supuestos y cómo se garantizan

Comprobaciones hechas el 14/11/2026 sobre `resultados/modelos/flujo_rezagado.csv` (5.100 filas = 255 tramos × 20 trimestres).

| Supuesto | Código o prueba | Comprobación |
|---|---|---|
| Faltantes no se rellenan con cero | `flujo_rezagado` (`how="left"`, `flujo_disponible`); `test_bordes_bypass_y_zonas_sin_flujo_no_se_rellenan` | 2.040 filas sin flujo (102 tramos × 20), 0 con proxy, 0 con proxy igual a 0 |
| Nunca entra el trimestre objetivo | `ValueError` en `flujo_rezagado`; `test_flujo_del_trimestre_objetivo_no_entra` | `fin_medicion < inicio_objetivo` en todas las filas; mínimo 91 días de diferencia |
| Se conserva el valor crudo | columna `puntos_implicitos_crudos` | presente en las 3.060 filas con flujo |
| La normalización solo corrige residuos | `normalizar_puntos` (tol. 1e-6); `test_residuos_no_crean_puntos_de_cobro_distintos` | residuo máximo 7,3e-9; 1.143 filas con residuo distinto de cero; 0 filas con cambio > 1e-6; 0 fracciones no enteras |
| PNCV separado de DGC | `exposicion_validada.csv`; `datos_modelado.py` no lo usa | archivo con solo encabezado |
| Las versiones no se suman | `serie_flujo`; `resultados/eda/dgc_comparacion_versiones.csv` | 112 contrato-trimestres solapados, 0 revisiones |
| Cohortes comparables | `metricas.csv` | `*_clima` y `*_clima_flujo` tienen igual `siniestros` por año y partición en las tres familias (cohorte `con_contrato`) |

Pruebas ejecutadas: `python -m unittest tests.test_modelado -v` → 7 pruebas, todas aprobadas.
Los puntos implícitos por contrato son constantes salvo Puerto Montt–Pargua (4 a 5) y Talca–Chillán (16 a 18).

## 5. Disponibilidad histórica

Consulta del 14/11/2026, con límite de tiempo. La lectura de la página la hizo una herramienta de resumen de páginas web; conviene verificarla a mano antes de citarla.

| Pregunta | Qué se buscó | Fuente | Hallazgo | ¿Acredita? | Qué falta |
|---|---|---|---|---|---|
| ¿Estaba el anexo de t−2 publicado antes de t? | Lista de anexos y ruta de subida | https://concesiones.mop.gob.cl/publicaciones/ | La página no muestra fechas de publicación. Los anexos de 2018 a 2023 y los tres primeros de 2024 tienen ruta `uploads/sites/4/2024/12/`; el 4T 2024 está en `2025/03`. Se subieron en bloque en diciembre de 2024. | **No** | Un documento con fecha o una copia archivada (por ejemplo Wayback Machine) de la página en 2020–2024. |
| ¿Cambian los valores entre versiones? | Comparación 2023_4t vs 2024_4t | `dgc_comparacion_versiones.csv` | 0 revisiones en 112 contrato-trimestres. | **Parcial** | Solo dos versiones; no descarta revisiones en otras. No se descargaron anexos adicionales. |
| ¿Hay pronósticos archivados con hora de emisión para 2020–2024 en Chile? | Documentación de Open-Meteo | https://open-meteo.com/en/docs/previous-runs-api y https://open-meteo.com/en/docs/historical-forecast-api | "Previous runs" parte en enero de 2024 para la mayoría de modelos (GFS temperatura a 2 m desde marzo de 2021). La Historical Forecast API une las primeras horas de cada corrida y no expone la hora de emisión. | **No** para 2020–2023; **parcial** para 2024 | Una corrida nueva solo con 2024; no era parte de este trabajo. |

**Conclusión:** la disponibilidad histórica **no está acreditada**. El rezago de dos trimestres es una regla de construcción, no una prueba de que el dato existiera en ese momento. Los resultados con flujo son un backtest retrospectivo.

## 6. Qué se puede concluir

### 6.1 Resultado retrospectivo con y sin flujo

Cohorte `con_contrato` (153 tramos), captura al 5 %, diferencia entre clima+flujo y clima en puntos porcentuales, IC 95 % por bootstrap semanal pareado (2.000 réplicas). Fuente: `resultados/modelos/bootstrap.csv`.

| Año | Poisson | Gradient Boosting | Random Forest |
|---|---|---|---|
| 2022 | −0,32 [−1,01; 0,31] | +0,37 [0,06; 0,74] | +0,11 [−1,90; 2,05] |
| 2023 | −0,32 [−0,75; 0,06] | +0,13 [−0,76; 1,03] | +0,38 [−2,54; 3,82] |
| 2024 | −0,13 [−0,58; 0,34] | −0,40 [−1,01; 0,21] | −0,34 [−2,42; 1,86] |

Solo GB 2022 excluye cero, y en 2024 el signo es negativo. En la ruta completa (255 tramos), con respaldo híbrido, la captura al 5 % con flujo queda por debajo de la de clima en 7 de los 9 pares familia–año (`metricas.csv`, cohorte `hibrido_ruta_completa`); las diferencias van de −0,5 a +0,35 pp y no se les calculó intervalo en esta ficha.
**Lectura acotada:** este proxy, a esta resolución, no aporta señal estable. No es evidencia de que el flujo real no importe.

### 6.2 Qué es el proxy y qué no es

Es circulación trimestral por contrato, por punto de cobro y día. No es exposición por tramo ni por conductor.

### 6.3 Exposición vehicular: estado y qué falta

El TMDA del MOP (PNCV) no se usa. Motivos: ningún registro con año de medición 2020, 5.603 valores TMDA iguales a 0 sin interpretar (5.538 con rol marcador), correspondencia rama–tramo no acreditada y fechas de publicación no acreditadas. La cobertura candidata de 2024 (estación a 2 km del eje, alcance 10 km) es de 68/255 tramos. Para cerrarlo hace falta una tabla `exposicion_validada.csv` con `metodo='validado'` y `disponible_desde`.

### 6.4 Frases para la presentación

**Se puede decir**
- "Incorporamos un proxy de circulación por contrato y trimestre, con rezago de dos trimestres."
- "El proxy cubre 153 de 255 tramos y entre 50 % y 57 % de los siniestros."
- "No encontramos mejora consistente al agregarlo; solo un caso de nueve tiene un intervalo que excluye cero."
- "Poisson_clima y las variantes sin flujo no usan este dato."

**No se puede decir**
- "El modelo controla por tráfico" ni "por flujo vehicular".
- "El riesgo por vehículo es mayor en…", ni nada en vehículo-km o por conductor.
- "El flujo no importa" (solo que este proxy no mejora).
- "Probamos con información disponible en su momento" (no está acreditada).

## 7. Discrepancias registradas

1. **14.425 vs 14.420.** `resultados/flujo/auditoria.json` y `resultados/flujo/cobertura.csv` (PNCV candidata) usan 14.425 eventos (2021: 3.292; 2022: 3.370). `resultados/modelos/` usa 14.420 tras poner en cuarentena 5 IDs (4 en 2021 y 1 en 2022). Esta ficha y `cobertura_flujo_detalle.csv` usan 14.420; la cobertura PNCV es un diagnóstico histórico con 14.425.
2. **Seis contratos, siete filas** en `limites_documentados.csv`: Collipulli–Temuco tiene dos intervalos.
3. **`SUR` en `flujo_concesiones.py`** lista siete contratos; solo seis tienen límites. Santiago–Talca se excluye por agregar Acceso Sur a Santiago.
4. **Grupos sin contrato:** 43/39/20 aquí frente a 45/40/17 en el plan (§3).

## 8. Pendientes y responsables

| Pendiente | Responsable |
|---|---|
| Revisar esta ficha y la cohorte 153/255 | Cristóbal |
| Aporte de lluvia y estabilidad temporal (docs 03 y 04 no están en esta rama) | Cristóbal, Martín |
| Fecha de publicación DGC con evidencia fechada | Vicente |
| Validar TMDA como exposición | Vicente |
| Sensibilidad urbana y umbrales de lluvia (requieren corrida nueva) | Equipo |
| Párrafo para el README y decisión de integrar | Diego |

Matriz completa: `resultados/cierre/matriz_compromisos.csv`. Orígenes revisados: pauta del profesor, sección 10 del notebook de la Entrega 2 y diapositiva 14 de la Presentación 1. De esta última, "más rutas" se agregó como C11 sin verificar; el resto ya estaba cubierto.

## 9. Cómo reproducir

```bash
.venv/bin/python cierre_flujo.py
.venv/bin/python -m unittest tests.test_modelado -v
```

`cierre_flujo.py` lee `ruta5_2020_2024.csv.gz` y `resultados/modelos/`, no descarga ni entrena, y termina con código distinto de 0 si no concilia. Salida esperada: `OK: 14420 eventos, 255 tramos`.

## Fuentes

- `resultados/modelos/` (`cobertura_flujo.csv`, `asignacion_contratos.csv`, `limites_documentados.csv`, `flujo_rezagado.csv`, `metricas.csv`, `bootstrap.csv`, `auditoria.json`)
- `resultados/flujo/` (`fuentes_dgc.json`, `cobertura.csv`, `exposicion_validada.csv`, `auditoria.json`)
- `resultados/eda/dgc_comparacion_versiones.csv`
- Páginas de la DGC y de Open-Meteo citadas en §5, consultadas el 14/11/2026.
