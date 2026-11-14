# Predicción de siniestros en la Ruta 5 Sur

Proyecto de Ciencia de Datos para estimar conteos de siniestros por tramo y hora
y apoyar la priorización de vigilancia en ventanas de 12 horas.

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
- [Plan del equipo para dos días](docs/planificacion/Plan_cierre_tecnico_2_dias.pdf).

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

- Se corrigieron captura con empates/presupuesto, cuarentena espacial, UTC/DST,
  selección temporal y tratamiento de faltantes. Hay modelos con y sin flujo.
- 2024 ya fue explorado en entregas anteriores; se informa como evaluación histórica
  reutilizada. El clima es reanálisis; falta validar con pronósticos emitidos.
- La exposición vehicular real y las fechas de publicación histórica DGC siguen
  sin acreditarse. Un proxy trimestral no permite estimar riesgo por conductor.
- Las fichas de selección e interpretación de Martín y Cristóbal y las revisiones
  humanas indicadas en el estado de entrega siguen pendientes.
- Notebook y presentación se preparan al estabilizar código y resultados; Máximo
  tiene a cargo la presentación. El prototipo HTML anterior usa otra versión.

## Bitácora y colaboración

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
