# Predicción dinámica de siniestros en carreteras chilenas

Proyecto de Ciencia de Datos para estimar conteos de siniestros por tramo y hora
y apoyar la priorización de vigilancia en ventanas de 12 horas.

**Problemática:** conocer los puntos con más siniestros históricos ayuda a ubicar
zonas prioritarias, pero no describe cómo cambia su frecuencia según la hora,
el calendario y la lluvia. El proyecto estudia esa variación para orientar dónde
concentrar recursos de vigilancia y cuántos siniestros esperar en una ventana.

**Alcance actual:** el proyecto tiene un nombre general para carreteras chilenas;
la evaluación técnica de la Entrega III se concentra en **Ruta 5 Sur**. El prototipo
multirruta es un antecedente y no amplía por sí solo el alcance validado.

La Entrega III compara Poisson, Gradient Boosting y Random Forest con calendario,
lluvia y un proxy de circulación. El experimento actual utiliza **14.420 siniestros,
255 tramos de 5 km y datos de 2020–2024**. La candidata seleccionada con validación
anterior a 2024 es **Poisson_clima**. El flujo disponible cubre 153 tramos y no
constituye exposición por vehículo-km. La evaluación es retrospectiva.

## Empezar aquí

- [Estado de la entrega, responsables y pendientes](docs/cierre/00_estado_entrega3.md).
- [Resultados, comparación de modelos y limitaciones](docs/resultados.md).
- [EDA y decisiones de calidad de datos](docs/eda.md).
- [Guía de reproducción de Diego](docs/cierre/01_reproducibilidad.md).
- [Ficha de datos y flujo de Vicente](docs/cierre/02_datos_flujo.md).
- [Fuentes CONASET para actualizar datos y evaluar el piloto](docs/fuentes_conaset.md).
- [EDA separado de CONASET 2025 y condiciones de incorporación](docs/eda_conaset_2025.md).
- [Ubicación vial: ensayo ejecutado, resultados y decisión sobre 2025](docs/validacion_ubicacion_vial.md).
- [Cierre de la ampliación 2025 y alcance final 2020–2024](docs/cierre_ubicacion_2025.md).
- [Piloto de 12 horas en modo sombra, primera emisión y límites](docs/piloto_12h.md).
- [Plan del equipo para dos días](docs/planificacion/Plan_cierre_tecnico_2_dias.pdf).

[Nombre oficial y estado del cambio en GitHub](docs/identidad_proyecto.md).

## Organización

```text
codigo/             Código organizado por función
  datos/            Fuentes, limpieza, calendario, clima y flujo
  modelos/          Modelos de conteo, entrenamiento y reajuste
  evaluacion/       Métricas, EDA y verificaciones de cierre
  visualizacion/    Tablas, figuras y resúmenes
  historico/        Scripts del prototipo y experimentos anteriores
data/               Siniestros, fuentes originales, calendario y cachés
resultados/         Tablas, figuras, auditorías y modelos locales
docs/               Fichas del equipo, resultados, planificación y antecedentes
notebooks/          Espacio para el notebook final documentado
tests/              Pruebas de datos, modelos, métricas e integración
config/             Trazabilidad de la reorganización
proyecto.py         Punto de entrada para ejecutar el código
index.html          Prototipo histórico conservado para GitHub Pages
```

[Guía de carpetas y migración](docs/estructura.md) · [Catálogo del código](codigo/README.md).

## Instalación

Entorno comprobado: Python 3.12.14 en Linux. Si ya existe un entorno de trabajo,
conservarlo y crear el nuevo en otra carpeta; no mezclar paquetes del sistema.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-reproduccion.txt
.venv/bin/python -m pip check
```

`requirements.txt` define rangos generales; `requirements-reproduccion.txt` fija
las versiones del entorno verificado. La guía de Diego explica los insumos locales
que no incluye Git y cómo recuperarlos sin mezclar revisiones.

## Ejecución

Todos los comandos pasan por `proyecto.py`, que resuelve el código y trabaja desde
la raíz del repositorio. Los módulos conservan sus nombres para cargar los modelos
guardados anteriormente. No es necesario instalar un paquete Python adicional.

```bash
.venv/bin/python proyecto.py --listar
.venv/bin/python proyecto.py verificar_cierre
.venv/bin/python proyecto.py cierre_flujo --comprobar
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python -m unittest discover -s tests -v
```

Con las fuentes originales y los artefactos locales:

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python proyecto.py verificar_cierre --con-artefactos
```

Para entrenamiento o regeneración, consultar la guía de reproducción. No hace
falta reentrenar para verificar tablas, cobertura o modelos existentes.

## Estado y límites

- La ampliación 2025 se investigó y se cierra para esta entrega: redondeo y texto
  recuperan información parcial, sin acreditar una cohorte vial comparable. No fue
  una decisión por data leakage; se conserva 2020–2024 y no se reabre sin evidencia nueva.
- Se corrigieron captura con empates/presupuesto, cuarentena espacial, UTC/DST,
  selección temporal y tratamiento de faltantes. Hay modelos con y sin flujo.
- 2024 ya fue explorado en entregas anteriores; se informa como evaluación histórica
  reutilizada. Se emitió un piloto de sombra 2026 con pronóstico meteorológico real,
  pero aún falta contrastarlo con siniestros observados y evaluar su desempeño.
- La exposición vehicular real y las fechas de publicación histórica DGC siguen
  sin acreditarse. Un proxy trimestral no permite estimar riesgo por conductor.
- Las fichas de selección e interpretación de Martín y Cristóbal y las revisiones
  humanas indicadas en el estado de entrega siguen pendientes.
- Notebook y presentación se preparan al estabilizar código y resultados; Máximo
  tiene a cargo la presentación. El prototipo HTML anterior usa otra versión.

## Bitácora y colaboración

El **14/11/2026** se emitió una primera corrida experimental del [piloto de 12 horas](docs/piloto_12h.md)
para la ventana local 14/11 19:00–15/11 07:00. Se usó la candidata Poisson_clima,
sin reentrenar, con 2020–2024 y precipitación pronosticada. Priorizó 12 de 255
tramos y estimó 2,615 siniestros esperados en la ruta. Se conservaron localmente
captura, tablas, visualización y auditoría; la reproducción da tablas idénticas. Esto
es una corrida en modo sombra, sin observaciones para medir aciertos, no un piloto
operativo validado. La integración 2025 sigue cerrada por ubicación vial no
comparable acreditada; no por fuga temporal. Cuatro pruebas nuevas cubren la ventana,
atributos, predicción portable, presupuesto y desempates.

El **14/11/2026**, siguiendo la alternativa indicada por Diego, se cerró la
[investigación adicional de 2025](docs/cierre_ubicacion_2025.md) y se conserva
2020–2024 para la entrega. Los escenarios numéricos recuperan los 433 positivos
de borde y llegan a 94,66 % de sensibilidad exploratoria en 2024, sin constituir
otra validación. Se comprobaron direcciones de 2023–2025: hay 2.791 referencias
numéricas concordantes en comuna en 2025, además de caleteras, intersecciones,
unidades no acreditadas y nombres alternativos. La concordancia geográfica cambia;
otras seis capas oficiales no resolvieron los atributos faltantes. No se integró
2025 ni se modificaron modelos, cuarentena o particiones. Quedan código, tablas,
figura y auditoría; pasan 67 pruebas y el cierre anterior. No repetir esta
ampliación sin fuentes o metadatos nuevos que permitan resolver sus límites.

El **14/11/2026** se implementó y ejecutó el [ensayo espacial](docs/validacion_ubicacion_vial.md)
con reglas previas, geometría MOP con medidas M y vías competidoras. El servicio
preferido falló; se usó una instantánea separada de la alternativa oficial: 79
entidades de Ruta 5 y 1.218 de otras vías. Sobre 2024 se recuperan 2.033/2.605
positivos conocidos (78,04 %) y la precisión en etiquetados es 96,95 %, con 64
falsos positivos y 512 propuestas sin etiqueta verificable. Predominan los 433
casos ambiguos por borde de tramo. La concordancia casi exacta de km no acredita
precisión física ni independencia de geocodificación. **No se admite la asignación
de 2025**: falla la sensibilidad fijada y faltan vigencia/cobertura urbana. Se
conservan fuentes, cuarentena y modelos. Hay código reproducible, nueve pruebas
espaciales nuevas, tablas, figura y auditoría; pasan 60 pruebas con el complemento
espacial y la verificación de cierre, sin reentrenar.

El **14/11/2026** se investigó cómo recuperar la ubicación vial de 2025. Se
comprobaron dos servicios MOP distintos: el enlazado desde Descargas devuelve
71 entidades de Ruta 5 y la alternativa indexada, 79. Sus muestras geométricas
incluyen medidas M por vértice. Se conservaron atributos completos, consultas y
hashes; no se asumió vigencia, unidad o pertenencia vial por cercanía. El
[procedimiento propuesto](docs/ubicacion_vial_2025.md) separa identificación de
carretera y kilometraje, exige controles con etiquetas conocidas y mantiene los
ambiguos fuera de una asignación automática. Quedan pendientes geometría completa,
versión, unidades y validación espacial; no se asignaron eventos ni cambiaron modelos.

El **14/11/2026** se descargaron instantáneas nacionales comprobadas de CONASET
2024 (72.043 filas) y 2025 (68.994), conservando originales fuera de Git. El
[EDA separado](docs/eda_conaset_2025.md) incluye calidad, cobertura, calendario,
repeticiones, distribuciones y contraste con el histórico: coinciden los 2.605
eventos de Ruta 5 Sur 2024 en los 19 campos comparados. En 2025 todos carecen de
ruta/kilómetro utilizable; los 73 puntos fuera del recuadro continental están
etiquetados Isla de Pascua. La diferencia con el total nacional publicado es de
4.087 siniestros y no se imputó su causa. **2025 no se incorporó al modelo.** Se
añadieron descargador, EDA reproducible, agregados, figura y auditoría; se mantienen
los resultados 2020–2024 y los pendientes operativos del piloto. Pasan 51 pruebas,
incluidas seis nuevas, y la verificación del cierre existente, sin reentrenar.

El **14/11/2026** se revisaron fuentes oficiales de CONASET mediante búsqueda y
consultas REST pequeñas: se confirmó que hay 68.994 registros geográficos de 2025,
pero con ruta en blanco y kilómetro 0. La cartografía de Ruta 5 Sur es una fuente
candidata para investigar su asignación; no se integró 2025 al modelo. La capa
Reporte_diario_2026 llega al 13/07/2026 y carece de la resolución tramo/hora de nuestro
objetivo. Las capas de feriados consultadas abarcan 2020–2024. Se conservaron
[hallazgos, límites y consultas reproducibles](docs/fuentes_conaset.md), sin
descargar bases completas, reentrenar ni modificar datos o resultados vigentes.

El **14/11/2026** se adoptó el nombre oficial **Predicción dinámica de siniestros en
carreteras chilenas** en la documentación vigente, el plan PDF y los títulos del
prototipo y sus generadores. El cambio del identificador y la descripción de GitHub
queda pendiente del propietario: la cuenta conectada tiene escritura, sin administración.
Se mantienen los enlaces actuales hasta completar ese cambio.

El **14/11/2026** se reorganizaron código, datos y documentos por función. Se añadió
el lanzador, se actualizaron rutas y se conservaron las auditorías originales y
la compatibilidad de los modelos. [Detalle y comprobaciones](docs/estructura.md).
Se comprobaron **45 pruebas** con fuentes locales y 18 evaluaciones de modelos de
2024, reproduciendo sus nueve métricas sin reentrenar. En una copia pública pasan
44 pruebas y se omite una por falta del anexo DGC original.

El trabajo anterior se conserva en las [fichas de cierre](docs/cierre/00_estado_entrega3.md)
y en el [README histórico](docs/historico/README_anterior.md), con las cifras y
conclusiones de sus respectivas etapas. No deben mezclarse universos históricos.

El mantenimiento automático autorizado revisa problemas concretos cada cuatro horas
y publica cambios verificados en `main`; sus instrucciones están en [AGENTS.md](AGENTS.md).
Antes de integrar avances del equipo, sincronizar con `git pull --ff-only` y comprobar
el estado local. Los archivos actuales deben colocarse según la guía de carpetas.

Los commits asistidos por Codex conservan la identidad del integrante e incluyen
`Co-authored-by: Codex <noreply@openai.com>` cuando corresponde. Se conserva el historial
publicado y la autoría de los aportes de los integrantes.
