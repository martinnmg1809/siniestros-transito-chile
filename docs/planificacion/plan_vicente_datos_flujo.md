# Plan de trabajo · Vicente · Datos y flujo (cierre técnico Ruta 5 Sur)

> **Para quién es este documento.** Lo lee primero un modelo intermedio (Sonnet) para entender el encargo y,
> después, lo ejecuta un agente de código (Claude Code) en otra sesión sobre el repositorio
> `siniestros-transito-chile`. Está escrito para que se pueda seguir **sin contexto adicional**.
> Todas las cifras de la sección 3 ya se verificaron contra los archivos del repositorio el 14/11/2026;
> el ejecutor debe volver a comprobarlas antes de citarlas (pueden haber cambiado con commits posteriores).

---

## 1. Encargo en una frase

Responder la observación más débil del profesor sobre los datos: **qué es exactamente el "flujo" que usa el modelo,
a qué tramos cubre, con qué rezago y unidades, qué no mide, y qué se puede (y no se puede) concluir de él**,
dejando cada afirmación respaldada por un archivo, o marcada como "no verificada".

- **Responsable:** Vicente. **Revisor:** Cristóbal (cohortes y conclusiones).
- **Plazos:** tabla de cobertura Día 1 a las 12:00 · ficha final Día 2 a las 12:30.
- **Capacidad:** ~14 h en total (7 h por día). Búsqueda de disponibilidad: **máximo 90 min**.

### Entregables (rutas propuestas por el plan del equipo)

| # | Archivo | Contenido |
|---|---|---|
| E1 | `docs/cierre/02_datos_flujo.md` | Ficha de flujo y límites de uso (estructura en §7). |
| E2 | `resultados/cierre/cobertura_flujo_detalle.csv` | Cobertura por año × grupo de tramos (con y sin contrato). |
| E3 | `resultados/cierre/fuentes_flujo.csv` | Tabla breve fuente / unidad / granularidad / rezago / cobertura / disponibilidad. |
| E4 | `resultados/cierre/matriz_compromisos.csv` | Observación o compromiso / cambio / evidencia / estado / pendiente. |
| E5 | `cierre_flujo.py` (raíz del repo) | Script corto que **regenera E2** desde salidas ya versionadas, sin entrenar ni descargar. |

Criterio global de aceptación: **cada restricción tiene evidencia o se identifica como no verificada; ningún texto afirma
que el modelo controla riesgo por conductor, por vehículo o por vehículo-km.**

---

## 2. Reglas que no se negocian

1. **No reentrenar, no ampliar grillas, no añadir familias de modelos.** Este trabajo es de trazabilidad y redacción.
   Solo se lee lo que ya existe en `resultados/` y el código.
2. **No editar `README.md`** (lo integra Diego), **ni el notebook, ni la presentación.**
3. **No interpretar el proxy DGC como vehículo-km, TMDA, vehículos únicos ni flujo horario por tramo.**
4. **Faltantes no se rellenan con cero.** `resultados/flujo/exposicion_validada.csv` **debe seguir vacía** (solo encabezado).
5. **PNCV (TMDA del MOP) y DGC (concesiones) se mantienen separados**: unidades distintas (estación/rama/año vs. contrato/trimestre).
6. **El rezago de dos trimestres no demuestra disponibilidad histórica.** Solo un documento con fecha lo haría.
7. **Sensibilidad urbana y umbrales de lluvia no figuran como resueltos** si no hay una corrida nueva que lo sustente
   (y esa corrida no es tarea de este plan).
8. **Una sola población de referencia:** 14.420 siniestros / 255 tramos. Cualquier tabla con 14.425 se etiqueta como histórica.
9. Seguir `AGENTS.md`: checkout limpio, no reescribir historial, sincronizar solo por fast-forward, preservar trabajo ajeno.
   Hay una **automatización que publica en `origin/main` cada 4 horas**: trabajar en una rama propia y entregar a Diego.
10. Reutilizar funciones del repo (`integrar_flujo.limites_documentados`, `asignar_contratos`, etc.).
    **No reconstruir reglas paralelas** (por ejemplo, no reescribir a mano los límites km de los contratos).

---

## 3. Estado verificado del repositorio (punto de partida)

### 3.1 Archivos clave

| Archivo | Qué contiene |
|---|---|
| `flujo_concesiones.py` | Extrae de los anexos XLS de DGC: transacciones trimestrales por contrato (livianos+pesados=total, conciliado) y promedio mensual por punto de cobro. Calcula `proxy_pasadas_por_punto_dia = promedio_mes × 3 / días_trimestre`. Marca `disponibilidad_historica_acreditada = False`. |
| `integrar_flujo.py` | `limites_documentados()` (intervalos km por contrato, con fuente y página PDF), `asignar_contratos()` (margen 1 km), `serie_flujo()` (deduplica versiones, conserva la más reciente), `normalizar_puntos()` (tolerancia 1e-6), `flujo_rezagado()` (unión exacta al trimestre objetivo − 2; falla si el predictor es contemporáneo o futuro). |
| `flujo_vehicular.py` | PNCV/TMDA: normaliza ramas de 6 capas, proyecta estaciones al eje, mide cobertura **candidata** (no validada). `exposicion_vehiculo_km()` exige `metodo='validado'` y `disponible_desde ≤ fecha_corte`. |
| `datos_modelado.py` | Arma el experimento: cobertura = tramos con proxy y puntos finitos en **todos** los períodos; features `log(proxy rezagado)` y `log(puntos rezagados)`. |
| `reentrenar_flujo.py` | Repite solo las variantes con flujo tras la normalización de puntos, verificando hashes. **No ejecutar.** |
| `tests/test_modelado.py` | Pruebas de fronteras/bypass sin relleno, rezago (el trimestre objetivo no entra), residuos de puntos, respaldo del híbrido. |
| `resultados/modelos/` | `cobertura_flujo.csv`, `limites_documentados.csv`, `asignacion_contratos.csv`, `flujo_rezagado.csv`, `metricas.csv`, `bootstrap.csv`, `resumen.md`, `auditoria.json`. |
| `resultados/flujo/` | `fuentes_dgc.json` (URLs + sha256 de los 2 anexos), `cobertura.csv` (PNCV candidata), `exposicion_validada.csv` (vacía), `auditoria.json` (descargas PNCV). |
| `resultados/eda/` | `dgc_cambios_puntos_cobro.csv`, `dgc_comparacion_versiones.csv`, figura `05_dgc_series_y_puntos_cobro.png`. |

### 3.2 Cifras ya comprobadas

**Cobertura del proxy (población 14.420, `resultados/modelos/cobertura_flujo.csv`):**

| Año | Tramos con flujo | Siniestros con flujo / total | % eventos |
|---|---|---|---|
| 2020 | 153/255 | 1.149 / 2.295 | 50,07 % |
| 2021 | 153/255 | 1.669 / 3.288 | 50,76 % |
| 2022 | 153/255 | 1.872 / 3.369 | 55,57 % |
| 2023 | 153/255 | 1.577 / 2.863 | 55,08 % |
| 2024 | 153/255 | 1.491 / 2.605 | 57,24 % |

**Asignación por contrato (`asignacion_contratos.csv`): seis contratos, siete intervalos** (Collipulli–Temuco se parte en
dos por el bypass de Temuco):

| Contrato | Tramos | km (inicio de tramo) |
|---|---|---|
| Talca–Chillán | 37 | 225–405 |
| Chillán–Collipulli | 30 | 415–560 |
| Collipulli–Temuco | 20 | 585–710 (dos intervalos: 585–650 y 685–710) |
| Temuco–Río Bueno | 33 | 720–880 |
| Río Bueno–Puerto Montt | 23 | 900–1010 |
| Puerto Montt–Pargua | 10 | 1025–1070 |
| **Total con contrato** | **153** | |

**102 tramos sin contrato**, en tres grupos (verificar con el script E5):

- **45 tramos km 0–220**: zona de Santiago–Talca. El contrato existe en DGC pero, según el README y el docstring de `flujo_concesiones.py`, **queda fuera porque su fila agrega
  Acceso Sur a Santiago** (no es separable). El tramo 220 cae además en el margen de 1 km de Talca–Chillán.
- **40 tramos km 1075–1270**: después de Puerto Montt–Pargua, incluye Chiloé (sin contrato DGC en los anexos usados).
- **17 tramos de fronteras, bypass y márgenes**: 410; 565–580 (frontera Collipulli discrepante entre documentos);
  655–680 (bypass Temuco con kilometraje propio); 715; 885–895 (Temuco–Río Bueno / Río Bueno–Puerto Montt); 1015–1020.

**Unidades y construcción del proxy:**

- Fuente: anexos trimestrales DGC (`2023_4t` y `2024_4t`, URLs y sha256 en `resultados/flujo/fuentes_dgc.json`).
- Se solapan en 112 contrato-trimestres con **0 revisiones** de transacciones y de promedios (eso no descarta revisiones en otras versiones).
- Se usa la versión más reciente por contrato y trimestre; 2018–2019 se extraen solo para tener rezagos reales desde 2020.
- `proxy = promedio mensual por punto × 3 / días del trimestre` → **pasadas por punto de cobro y día**.
- `puntos_implicitos = transacciones_trimestre / (3 × promedio mensual por punto)` → control de composición, inferido
  algebraicamente, **no** censo físico de plazas. Residuo numérico máximo encontrado: 7,3e-9 (tolerancia 1e-6);
  se conserva `puntos_implicitos_crudos`.
- Cambios de puntos implícitos detectados: Puerto Montt–Pargua 2021T1 (5) y 2022T1 (4); Talca–Chillán 2020T4 (17) y 2022T1 (16).
- Entra al modelo como `log(proxy)` y `log(puntos)` del **trimestre objetivo − 2**.

**Resultado con/sin flujo** (`resumen.md`, `bootstrap.csv`, cohorte `con_contrato`, 153 tramos, captura al 5 %,
diferencia clima+flujo − clima, IC 95 % bootstrap semanal pareado de 2.000 réplicas):

| Año | Poisson | Gradient Boosting | Random Forest |
|---|---|---|---|
| 2022 | −0,32 [−1,01; 0,31] | +0,37 [0,06; 0,74] | +0,11 [−1,90; 2,05] |
| 2023 | −0,32 [−0,75; 0,06] | +0,13 [−0,76; 1,03] | +0,38 [−2,54; 3,82] |
| 2024 | −0,13 [−0,58; 0,34] | −0,40 [−1,01; 0,21] | −0,34 [−2,42; 1,86] |

Solo GB 2022 tiene un IC que excluye cero, y se invierte en 2024. Lectura defendible: **no hay evidencia de mejora
consistente por agregar el proxy.**

**PNCV / TMDA:** 6 capas (863 puntos), 18.289 filas de ramas, 406 de Ruta 5; **ningún registro con año de medición 2020**
(la capa "2020 Sur – 2021 Norte" contiene 2021–2022); 5.603 TMDA = 0 (5.538 con rol marcador). Cobertura candidata 2024
con estación ≤2 km del eje y alcance 10 km: 68/255 tramos. `exposicion_validada.csv` vacía. Fechas de publicación no acreditadas.

### 3.3 Discrepancias detectadas (hay que documentarlas, no "arreglarlas" en silencio)

1. **Dos poblaciones en `resultados/`.** `resultados/flujo/auditoria.json` (y por tanto `resultados/flujo/cobertura.csv`)
   se generó con **14.425** eventos (2021: 3.292; 2022: 3.370). `resultados/modelos/` usa **14.420** tras poner en cuarentena
   5 IDs (`auditoria.json → datos.ids_cuarentena`): 4 en 2021 y 1 en 2022. 2024 coincide (2.605). La ficha debe decir
   qué tabla usa cada población; la cobertura PNCV candidata se informa como diagnóstico histórico con 14.425.
2. **"Seis contratos" vs. siete filas** en `limites_documentados.csv`: es correcto (Collipulli–Temuco tiene dos intervalos);
   hay que explicarlo en la ficha para que nadie lo cuente como error.
3. **`SUR` en `flujo_concesiones.py` incluye siete contratos** (con Santiago–Talca y Acceso Sur), pero solo seis tienen límites.
   Explicar la exclusión.
4. **En la copia local de Vicente no existen `data/` (fuentes crudas) ni `.venv/`.** `serie_flujo()` y
   `preparar_experimento()` no corren sin `data/fuentes/dgc/*.xls`. Todo E2 debe salir de CSV ya versionados.

---

## 4. Bloque 0 · Preparación (30 min, Día 1 09:00–09:30)

1. Confirmar con el equipo el commit base (el plan cita `4533870`). Registrar `git rev-parse HEAD` y `git status` en la ficha.
2. Crear rama: `git switch -c cierre/vicente-flujo` (no trabajar sobre `main`; hay automatización).
3. Entorno: si no hay `.venv`, `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
   (si no hay red, usar el Python del sistema solo con `pandas`/`numpy` y anotarlo).
4. Ejecutar solo las pruebas relacionadas y guardar la salida:
   `.venv/bin/python -m unittest tests.test_modelado -v`
   (si fallan por falta de `data/`, registrar cuáles y por qué; no "arreglarlas").
5. Preguntar a Vicente por insumos que **no están en el repo** y se necesitan para la matriz de compromisos (E4):
   `Entrega2_Proyecto_DS.ipynb` (sección 10), `Presentacion1_Proyecto_DS (1).pdf` (diap. 14) y las fotografías de evaluación
   del profesor. Si no aparecen, la matriz se arma con README/resumen y se marca la fuente como "no revisada".

---

## 5. Día 1 · Cerrar la trazabilidad

### T1 · Conciliar poblaciones y cobertura (09:30–11:00) → E2, E5

- Escribir `cierre_flujo.py` (≤120 líneas) que:
  - lea `resultados/modelos/asignacion_contratos.csv` y compruebe que coincide con
    `integrar_flujo.asignar_contratos(tramos)` usando `limites_documentados()` (si difiere: detenerse y avisar);
  - clasifique los tramos sin contrato en `antes_primer_contrato` / `despues_ultimo_contrato` / `frontera_bypass_margen`,
    **derivando los cortes de `limites_documentados()`** (mín. `km_inicio` y máx. `km_fin`), no de constantes escritas a mano;
  - cuente eventos por año y grupo con la población **14.420**: cargar `ruta5_2020_2024.csv.gz` con el cargador existente
    (`datos_ruta5.cargar_eventos`, revisar su firma) y excluir `ids_cuarentena` de `resultados/modelos/auditoria.json`;
  - escriba `resultados/cierre/cobertura_flujo_detalle.csv` con columnas
    `anio, grupo, contrato, tramos, siniestros, siniestros_total_anio, porcentaje_eventos, poblacion, fuente`;
  - **verifique** que la suma de grupos con contrato reproduce `resultados/modelos/cobertura_flujo.csv`
    (153 tramos; 1.149 / 1.669 / 1.872 / 1.577 / 1.491) y que el total es 255 tramos y 14.420 eventos; si no cuadra, fallar con mensaje claro.
- No descargar nada, no entrenar, no tocar `resultados/modelos/`.
- **Aceptación:** el script corre en < 1 min, reproduce las cifras de §3.2 y termina con código ≠ 0 si algo no concilia.

### T2 · Qué mide el flujo (11:00–12:00) → borrador de E1 §2 y E3

- Redactar la definición operativa con fórmula, unidad, granularidad (contrato × trimestre), rezago (2 trimestres), forma
  en que entra al modelo (dos features log) y la regla de cobertura (tramo cubierto solo si tiene proxy y puntos finitos en
  todos los períodos).
- Llenar E3 con una fila por fuente: `DGC anexos trimestrales`, `PNCV TMDA`, `ERA5 (solo para referencia de disponibilidad)`.
  Columnas: `fuente, url_o_archivo, sha256, unidad, granularidad_espacial, granularidad_temporal, rezago_usado,
  tramos_cubiertos, uso_en_modelo, disponibilidad_historica_acreditada, nota`.
- Dejar explícito qué **no** mide: vehículos únicos (un vehículo genera varias pasadas), flujo horario por tramo, vehículo-km,
  homogeneidad dentro del contrato.
- **12:00 · Entregar a Cristóbal** la tabla de cobertura (E2) y la definición, porque él la necesita para separar el aporte del flujo.

### T3 · Revisar los supuestos difíciles (14:00–15:00) → E1 §4

Para cada supuesto, citar la línea de código o prueba que lo garantiza:

| Supuesto | Dónde comprobarlo |
|---|---|
| Faltantes no se rellenan con cero | `flujo_rezagado` (merge `how="left"`, `flujo_disponible`), `test_bordes_bypass_y_zonas_sin_flujo_no_se_rellenan` |
| Nunca se usa el trimestre objetivo | `flujo_rezagado` (`ValueError` si `fin_medicion ≥ inicio_objetivo`), `test_flujo_del_trimestre_objetivo_no_entra` |
| Se conserva el valor crudo de puntos | columna `puntos_implicitos_crudos` en `resultados/modelos/flujo_rezagado.csv` |
| La normalización solo corrige residuos | `normalizar_puntos` (tolerancia 1e-6), `test_residuos_no_crean_puntos_de_cobro_distintos`; comprobar en `flujo_rezagado.csv` que `abs(crudos − normalizados) ≤ 1e-6` y que ninguna fracción real se redondeó |
| PNCV separado | `exposicion_validada.csv` vacía; `datos_modelado.py` no lo usa |
| Versiones no se suman | `serie_flujo` (`drop_duplicates(keep="last")`); `dgc_comparacion_versiones.csv` |

Hacer esas comprobaciones con lecturas de CSV en un bloque corto; pegar el resultado (número de filas, máximo residuo) en la ficha.

### T4 · Disponibilidad histórica, **máximo 90 min** (15:00–16:00 + 30 min de holgura) → E1 §5

Preguntas concretas, en orden:

1. **Anexos DGC.** En `concesiones.mop.gob.cl/publicaciones/` buscar la lista de anexos trimestrales (no solo los 4T usados) y
   registrar para cada uno: nombre, URL, y la ruta de subida `uploads/sites/4/AAAA/MM/` (indicio de mes de carga, **no** prueba
   de fecha de publicación ni de que el valor no se revisó después). Pistas ya visibles: el anexo 2023T4 está en `…/2024/12/` y el
   2024T4 en `…/2025/03/`. Lo crítico para el rezago de 2 trimestres: ¿el anexo del trimestre *t−2* estaba publicado antes del inicio
   del trimestre *t*? Probar al menos 2–3 casos (p. ej. medición 2023T2 → objetivo 2023T4).
2. **Revisiones.** ¿Los valores de un trimestre cambian entre anexos sucesivos? Ya hay 0 revisiones entre 2023T4 y 2024T4; si
   se consigue otro anexo, comparar solo si el costo es bajo (descarga de un XLS pequeño, sin reentrenar).
3. **Meteorología con hora de emisión.** Verificar si existe una fuente de pronósticos archivados con hora de emisión para
   2020–2024 en Chile (por ejemplo, revisar si Open-Meteo ofrece pronósticos históricos o "previous runs" y desde qué año).
   **Solo documentar si existe y qué cubre; no descargar ni reevaluar.**

Salida: tabla `pregunta | qué se buscó | URL | fecha de consulta | hallazgo | ¿acredita? (sí/no/parcial) | qué falta`.
Si a los 90 min no hay evidencia, registrar exactamente qué faltó y cerrar. **El rezago por sí solo no demuestra disponibilidad.**

### T5 · Revisión cruzada y cierre del día (16:00–17:30)

- Con Cristóbal: revisar que sus tablas usan la misma cohorte (153) para la comparación con/sin flujo y la ruta completa (255)
  para el híbrido; comprobar en `metricas.csv` que `Poisson_clima` y `Poisson_clima_flujo` en `con_contrato` tienen el mismo
  `siniestros` por año y partición (idem GB y RF).
- 17:00: dejar borrador de E1 con secciones 1–5 completas y lista de pendientes para Diego.

---

## 6. Día 2 · Redactar lo que sí se puede concluir

### T6 · Ficha de flujo con tres niveles (09:30–11:00) → E1 §6

Separar explícitamente:

1. **Resultado retrospectivo**: qué mostró el experimento (tabla de §3.2 con 2022/2023/2024 y las tres familias, más la
   comparación del híbrido en 255 tramos). Conclusión acotada: el proxy no mejora de forma consistente la captura; no es evidencia
   de que el flujo no importe, sino de que **este proxy, a esta resolución, no aporta señal estable**.
2. **Proxy de circulación**: lo que el dato es (pasadas por punto de cobro y día, por contrato y trimestre, con rezago).
3. **Exposición vehicular pendiente**: TMDA/vehículo-km por tramo no está disponible de forma validada; razones (sin año 2020,
   ceros sin interpretar, correspondencia rama→tramo no acreditada, fechas de publicación no acreditadas). Qué haría falta para
   cerrarlo (tabla `exposicion_validada.csv` con `metodo='validado'` y `disponible_desde`).

Incluir 3–5 frases "**lo que se puede decir / lo que no se puede decir**", listas para que Máximo las use en la presentación.
Ejemplo de lo que no se puede decir: "el modelo controla por tráfico", "el riesgo por vehículo es mayor en…".

### T7 · Matriz de compromisos y observaciones (11:00–11:30) → E4

Columnas: `id, origen (profesor / Entrega 2 §10 / Presentación 1 diap. 14), compromiso_u_observacion, cambio_realizado,
evidencia (archivo y sección), estado (resuelto / parcial / pendiente / no verificado), pendiente_concreto, responsable`.

Filas mínimas:

| Compromiso | Estado esperado | Evidencia |
|---|---|---|
| Revisar flujo (observación del profesor) | parcial | E1, E2, `bootstrap.csv` |
| Tendencia anual | resuelto | feature de tendencia numérica anual (`resumen.md`, protocolo) |
| Comparación de familias | resuelto | `metricas.csv`, `seleccion_temporal.csv` |
| Aporte específico de lluvia | lo cierra Cristóbal | referencia a `docs/cierre/04_interpretacion.md` |
| Estabilidad temporal | lo cierran Cristóbal y Martín | referencia a 03/04 |
| TMDA como exposición | pendiente | `exposicion_validada.csv` vacía, §3.2 PNCV |
| Validación con pronósticos emitidos | pendiente | `auditoria.json → limites` |
| Sensibilidad urbana | pendiente (salvo corrida nueva) | 6,8 % de eventos urbanos; no ejecutada |
| Umbrales de lluvia | pendiente (salvo corrida nueva) | cortes `<0,1 / 0,1–0,5 / ≥0,5` mm/h sin sensibilidad |
| Fecha de publicación DGC | según T4 | tabla de T4 |

Verificar el estado de cada fila con el archivo citado antes de escribirlo; si no se encuentra evidencia, poner "no verificado".

### T8 · Revisión 2, entrega e integración (11:30–12:30)

- Revisión de trazabilidad con el equipo: cada cifra de E1 enlaza a un CSV o a una línea de código.
- Correr `cierre_flujo.py` una vez más y las pruebas relacionadas; pegar salida en la ficha.
- `git diff --check`; commit en `cierre/vicente-flujo` solo con E1–E5 (nada de README, notebook ni `resultados/modelos/`).
- Entregar a Diego la rama y un párrafo de 5 líneas para el README (él decide si lo integra).
- 12:30: ficha final a Cristóbal.

Tarde del Día 2 (agenda común): participar en la decisión conjunta (14:00), revisar el resumen final del README (15:00) y,
en la defensa breve (17:00), explicar **una decisión** (p. ej. excluir Santiago–Talca por mezclar Acceso Sur) y **una limitación**
(el proxy no es exposición).

---

## 7. Esqueleto de `docs/cierre/02_datos_flujo.md`

```markdown
# Datos y flujo · ficha de cierre
Versión: commit <hash> · Fecha · Autor: Vicente · Revisor: Cristóbal · Población: 14.420 / 255

## 1. Resumen en cinco líneas
## 2. Qué es el flujo que usa el modelo (fórmula, unidad, granularidad, rezago, cómo entra al modelo)
## 3. Cobertura (tabla E2 resumida + los tres grupos sin contrato + por qué)
## 4. Supuestos y cómo se garantizan (tabla de T3 con resultados de las comprobaciones)
## 5. Disponibilidad histórica (tabla de T4; conclusión: acreditada / no acreditada / parcial)
## 6. Qué se puede concluir
### 6.1 Resultado retrospectivo con/sin flujo (2022–2024, tres familias, IC)
### 6.2 Qué es el proxy y qué no es
### 6.3 Exposición vehicular: estado y qué falta
### 6.4 Frases para la presentación: se puede decir / no se puede decir
## 7. Discrepancias registradas (14.425 vs 14.420, seis contratos / siete intervalos, etc.)
## 8. Pendientes explícitos y responsables
## 9. Cómo reproducir (comandos, archivos de entrada, salida esperada)
## Fuentes
```

---

## 8. Dependencias y coordinación

- **Vicente → Cristóbal:** definición del flujo y cobertura (Día 1, 12:00); ficha final (Día 2, 12:30). Cristóbal no debería
  interpretar el aporte del flujo antes de recibirlas.
- **Vicente → Diego:** rama con E1–E5 y párrafo para el README. Diego es el único que integra en `main`.
- **Vicente ↔ Martín:** solo si Martín menciona flujo en la ficha del modelo final (Poisson_clima **no** usa flujo; aclararlo).
- **Vicente → Máximo (vía Diego):** frases de §6.4 y la tabla de cobertura.

---

## 9. Lista de cierre (marcar antes de entregar)

- [ ] E2 reproduce 153/255 y 1.149 / 1.669 / 1.872 / 1.577 / 1.491 con la población 14.420.
- [ ] Los 102 tramos sin contrato están clasificados y explicados en tres grupos.
- [ ] Se explican seis contratos con siete intervalos y la exclusión de Santiago–Talca/Acceso Sur.
- [ ] Fórmula, unidad, granularidad y rezago del proxy escritos sin ambigüedad.
- [ ] Cada supuesto de T3 tiene una línea de código o prueba y una comprobación numérica.
- [ ] Disponibilidad histórica: tabla de T4 con conclusión explícita (lo más probable: no acreditada).
- [ ] La ficha separa resultado retrospectivo / proxy / exposición pendiente.
- [ ] La discrepancia 14.425 vs 14.420 está documentada.
- [ ] Matriz de compromisos sin ningún "resuelto" sin evidencia.
- [ ] Ninguna frase dice "vehículo-km", "riesgo por conductor" o "controla por tráfico" como algo logrado.
- [ ] `exposicion_validada.csv` sigue vacía; nada en `resultados/modelos/` cambió.
- [ ] Rama `cierre/vicente-flujo` con commit limpio entregada a Diego.

---

## 10. Si no alcanza el tiempo

Orden de recorte: primero T4 punto 3 (meteorología), luego T4 punto 2 (revisiones), luego E5 se reduce a verificación sin
clasificación de grupos. **Nunca** se recorta: definición del proxy, cobertura conciliada, separación de los tres niveles y
la matriz con estados honestos. Si algo P0 falla, conservar el último resultado válido y documentar el bloqueo.
