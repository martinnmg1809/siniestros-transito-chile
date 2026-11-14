# Organización del repositorio

Reorganización del 14/11/2026, a partir del commit `974c8cd`.
La finalidad es facilitar navegación, reproducción y colaboración mientras se
completan las fichas del equipo. No se editaron notebook, presentación, datos
originales ni parámetros científicos.

## Dónde buscar cada cosa

| Necesidad | Ubicación |
|---|---|
| Entender el estado actual y los pendientes | README de la raíz y docs/cierre/00_estado_entrega3.md |
| Consultar las tablas y conclusiones vigentes | docs/resultados.md y resultados/modelos/ |
| Revisar la exploración de datos | docs/eda.md y resultados/eda/ |
| Trabajar con fuentes, clima, calendario o flujo | codigo/datos/ |
| Ajustar o comparar modelos | codigo/modelos/ |
| Calcular métricas, ejecutar EDA o comprobar el cierre | codigo/evaluacion/ |
| Regenerar figuras y resumen | codigo/visualizacion/ |
| Consultar scripts del prototipo anterior | codigo/historico/ |
| Encontrar CSV de CONASET | data/siniestros/ |
| Guardar fuentes descargadas | data/fuentes/ (local, fuera de Git) |
| Guardar calendario y matrices | data/calendario/ y data/cache/ (locales) |
| Guardar salidas del prototipo anterior | resultados/prototipo/ (local) |
| Consultar el informe de la primera entrega | docs/historico/entrega1/ |
| Consultar planificación del equipo | docs/planificacion/ |
| Incorporar el notebook final | notebooks/ |

Los resultados se separan por experimento. La carpeta `resultados/flujo/` conserva
el diagnóstico de exposición candidata y `resultados/modelos/` la población
depurada posterior. Mover carpetas no vuelve comparables universos distintos.

## Ejecutar y migrar comandos anteriores

En lugar de `.venv/bin/python verificar_cierre.py`, usar:

```bash
.venv/bin/python proyecto.py verificar_cierre
.venv/bin/python proyecto.py cierre_flujo --comprobar
.venv/bin/python proyecto.py entrenar_comparacion --help
.venv/bin/python proyecto.py --listar
```

El lanzador prepara rutas de importación de las cinco áreas y fija el directorio
de trabajo en la raíz. Puede invocarse por ruta absoluta desde otra carpeta.
Todos los argumentos posteriores al nombre del comando se pasan al script.
Las rutas relativas de salida se interpretan desde la raíz, como en las corridas
anteriores. Las opciones explícitas de salida siguen permitiendo carpetas temporales.

`resumir_modelos --actualizar-readme` actualiza ahora el bloque de `docs/resultados.md`;
`explorar_datos --actualizar-readme`, el de `docs/eda.md`. Se conserva el nombre de
la opción por compatibilidad. Así el README principal sigue siendo un índice corto.
No se ejecutan estos análisis al listar comandos o importar el lanzador.

La portada HTML se mantiene en la raíz para conservar la URL existente de GitHub
Pages. Sigue siendo un prototipo histórico, sin actualización de sus coeficientes
ni acreditación de operación para la nueva candidata.

## Auditorías y modelos guardados

Los módulos mantienen sus nombres (`modelos_conteo`, `calibracion_modelos`, etc.).
Los artefactos joblib existentes pueden encontrarlos después de `import proyecto`
o de ejecutar el lanzador. No se reserializan ni se vuelven a ajustar por mover código.

Las auditorías de resultados conservan las rutas y hashes de sus corridas originales.
[El registro de migración](../config/migracion_estructura.csv) relaciona ubicación
anterior, ubicación nueva y hashes antes/después. Los cambios de código son de
ubicación, lectura/escritura de archivos e integración de rutas. La excepción que
permite comprobar hashes antiguos es explícita: acepta el original o la pareja
registrada; una modificación posterior sigue fallando. No afirma identidad binaria
entre ambas versiones ni sustituye las comprobaciones de predicción.

El entrenamiento futuro registra el hash del código situado en las nuevas carpetas.
El script de repetición de flujo también compara las fuentes sin exigir que la ruta
absoluta del mismo CSV siga siendo la antigua; sí exige el resto de sus metadatos.

## Equipo y avances

Actualizar la copia con `git pull --ff-only` antes de integrar trabajo. Si una rama
conserva nombres anteriores, consultar el registro y trasladar sus cambios a los
archivos actuales; no volver a crear los scripts en la raíz. No se eliminó ningún
avance del equipo. El plan de Vicente conserva su autoría en docs/planificacion/.

La historia de comprobaciones se conserva en resultados/cierre/. Los documentos
históricos pueden mencionar los comandos anteriores: se interpretan con esta guía,
no como instrucciones de ejecución vigentes.

La evidencia de esta reorganización está en
[reorganizacion.md](../resultados/cierre/reorganizacion.md).
