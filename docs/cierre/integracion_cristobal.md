# Integración del aporte de Cristóbal

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.
Revisión de integración: Diego con asistencia de Codex, 14/11/2026.
Las tablas, figuras y generadores originales son el aporte de Cristóbal; esta nota
documenta la comprobación y una lectura técnica de integración, sin atribuirle
una aprobación humana ni reemplazar su ficha narrativa.

## Material recibido y comprobado

Se incorporaron por fast-forward tres commits publicados por
`cristobalrivera2-create`: `07df973` (comparación y lluvia), `dbe7ef7`
(generalización) y `3963bd3` (calibración). No hay cambios de entrenamiento.

| Archivo en resultados/cierre | Filas | Contenido |
|---|---:|---|
| comparacion_final.csv | 114 | Métricas originales con familia, variante, entrenamiento y tamaño de cohorte |
| aporte_lluvia_flujo.csv | 18 | Contrastes pareados sobre los mismos 153 tramos con contrato |
| generalizacion.csv | 60 | Captura de entrenamiento y prueba y brecha en puntos porcentuales |
| estabilidad_temporal.csv | 20 | Resumen descriptivo de las pruebas 2022–2024 |
| calibracion_resumen.csv | 48 | O/E, desvianza y MAE por año, modelo y cohorte |
| recalibracion_resumen.csv | 2 | Candidata original y recalibrada con el año anterior |

Los cuatro generadores se ejecutaron en un directorio temporal con copia de las
tablas fuente. **Los seis CSV resultantes coinciden byte por byte con los recibidos.**
Además, las columnas comunes de la comparación maestra se cotejaron contra
`resultados/modelos/metricas.csv`, con tolerancia absoluta de 0,00000051 por el
redondeo a seis decimales. No se sobrescribieron resultados científicos originales.

Se inspeccionaron visualmente `fig_train_prueba.png` y `fig_calibracion.png`.
Los generadores reproducen sus dimensiones, pero las imágenes regeneradas no son
idénticas píxel por píxel en este entorno; se conservaron las figuras recibidas.
No se afirma identidad binaria de las figuras. Los valores representados proceden
de las tablas comprobadas y las escalas incluyen sus valores.

Los generadores se trasladaron de `resultados/cierre` a `codigo/evaluacion` y sus
instrucciones de uso se adaptaron al lanzador. Se retiró un import sin uso; no
cambió el cálculo. Pasaron las 71 pruebas existentes y la verificación de cierre.

## Lectura para la entrega

En la **ruta completa de 255 tramos**, Poisson_clima captura aproximadamente
19,56 %, 18,62 % y 19,00 % al presupuesto global del 5 % en 2022, 2023 y 2024.
Gradient Boosting obtiene 19,50 %, 18,73 % y 20,00 %. Su brecha media entre
entrenamiento y prueba es 8,91 puntos porcentuales, frente a 3,93 de Poisson.
Las brechas describen pérdida de desempeño fuera del entrenamiento; por sí solas
no separan sobreajuste de cambios entre años. La media y desviación de tres años
son descriptivas, no una nueva validación ni un criterio para elegir con 2024.
La candidata permanece Poisson_clima según la selección temporal ya fijada.

El **aporte de lluvia y flujo se contrasta en 153 tramos**, no en toda la ruta.
Para Poisson, el incremento de captura por lluvia es 0,855, 1,522 y 1,140 puntos
en 2022–2024, con intervalos que incluyen cero. Para GB, la lluvia en 2023 aporta
3,361 puntos, IC95 % [1,352; 5,520]. El flujo de GB mejora 0,374 puntos en 2022,
IC95 % [0,056; 0,737], pero sus intervalos incluyen cero en 2023 y 2024.
No se observa una mejora consistente del flujo a través de los tres años.
Son comparaciones predictivas con predicciones fijas y bootstrap semanal pareado;
no prueban causalidad y los intervalos individuales no tienen ajuste por múltiples
comparaciones. Un intervalo que incluye cero no demuestra ausencia de efecto.

En **2024, ruta completa**, Poisson original tiene O/E de 0,772: el total predicho
es mayor que el observado. La recalibración con factor de 2023 lleva O/E a 1,154
y reduce el MAE por turno de 1,970 a 1,684. Cambia el nivel de los conteos y mantiene
la captura de 19,00 %. El MAE corresponde al **total de la cohorte por turno de
12 horas**, no a cada tramo. M1 sin recalibrar tiene MAE 1,861; este contraste no
evalúa una versión de M1 recalibrada bajo el mismo procedimiento.

La etiqueta «cercano a 1» de calibracion_resumen usa el intervalo descriptivo
[0,95; 1,05], definido por el generador. No representa un intervalo de confianza
ni un umbral validado para despliegue. La figura por deciles muestra O/E para la
candidata original; el «riesgo predicho» del eje se refiere a conteo esperado por
tramo/hora, no a riesgo por conductor. Las brechas de entrenamiento de los modelos
híbridos quedan vacías porque no se entregó esa partición; no significan cero.

## Reproducción y cierre documental

Desde la raíz del proyecto, ejecutar en este orden:

```bash
.venv/bin/python proyecto.py construir_comparacion_final
.venv/bin/python proyecto.py construir_aporte_lluvia_flujo
MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python proyecto.py construir_generalizacion
MPLCONFIGDIR=/tmp/siniestros-matplotlib .venv/bin/python proyecto.py construir_calibracion
```

Estas órdenes escriben los resúmenes y figuras en `resultados/cierre`. Para cotejar
sin alterar las salidas recibidas, ejecutarlos en una copia temporal del proyecto.
Las tablas de modelado son la fuente de precisión completa; los resúmenes tienen
redondeo para comunicación. No usar la media 2022–2024 para reseleccionar el modelo.

Diego informó que Cristóbal terminó su parte. Los commits recibidos no contienen
la ficha narrativa 04 ni constancia de revisión de la ficha 02 de Vicente. Queda
registrado el aporte técnico como recibido e integrado; queda incorporar esos
documentos si se realizaron aparte. Esta nota aporta una lectura verificable para
su defensa y para la preparación posterior del notebook y la presentación.


Actualización posterior: a petición de Diego se completaron la
[ficha 04](04_interpretacion.md) y la revisión técnica de la
[ficha 02](02_datos_flujo.md), con asistencia de Codex. El párrafo anterior describe
el estado al recibir los commits; esos dos documentos ya están incorporados.
