# Estado de la Entrega III y siguiente integración

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.

Actualización: 14 de noviembre de 2026. Responsable de integración: Diego.
Referencia docente: anuncio de la Presentación Técnica Final copiado por Diego en
el chat el 14/11/2026; complementa la rúbrica y las observaciones anteriores.
El anuncio exige presentación PPT/PDF y notebooks documentados, con evidencia,
interpretación y coherencia con el código. Los repartos y decisiones de organización
que siguen son acuerdos del equipo, no nuevas exigencias atribuidas al profesor.

## Correspondencia con el anuncio

| Requisito mínimo | Evidencia disponible | Trabajo necesario para la entrega final |
|---|---|---|
| Iteraciones y correcciones | README; matriz_compromisos.csv; cuarentena, captura con empates, UTC/DST y revisión de fuentes | Diego integra la matriz y las comprobaciones; Máximo utiliza sus conclusiones en la presentación |
| Comparación de modelos | metricas.csv, busqueda_temporal.csv y bootstrap.csv en resultados/modelos; Poisson, GB y RF, con/sin flujo | Tablas y figuras de Cristóbal recibidas y comprobadas; incorporar su lectura en la ficha narrativa 04 |
| Selección del modelo final | auditoria.json: candidata Poisson_clima, elegida con 2022/2023 y regla de simplicidad; reajuste.json | Martín entrega la ficha 03 y justifica elección, variantes de calibración y artefacto; no elegir retrospectivamente con 2024 |
| Validación y generalización | Ventanas expansivas; train/prueba; IC semanales; verificar_cierre.py; pruebas automatizadas | Cristóbal/Martín explican estabilidad, brechas y límites; 2024 se declara evaluación histórica reutilizada |
| Interpretación | Ficha de Vicente, diferencias e IC; calibración, MAE y ejemplos por elaborar | Cristóbal cierra ficha 04; Martín aporta contrastes del modelo; evitar causalidad y confusión entre conteos y riesgo por vehículo |
| Conexión con el problema | Conteos por tramo/hora y priorización de vigilancia, captura global y por turno de 12 h | Explicar por separado dónde priorizar y cuántos eventos esperar; MAE actual agregado por cohorte/turno no acredita error por tramo |

Los nombres de tablas de la segunda columna se refieren a `resultados/modelos/`,
salvo la matriz de compromisos, situada en `resultados/cierre/`.

## Integración recibida de Vicente

Se incorporaron por avance directo los seis commits de `cierre/vicente-flujo`,
desde `d5dd8e5` hasta `a7b8e01`, conservando su autoría. La rama parte de `a65a02d`.
Incluye `cierre_flujo.py`, la ficha 02, cobertura por contrato, inventario de fuentes,
matriz de compromisos y el plan de trabajo que Vicente conservó como antecedente.

Diego comprobó que la tabla regenerada es idéntica a la recibida: 14.420 siniestros,
255 tramos; 153 con contrato y 102 sin contrato utilizable, desglosados en 43 antes
del primero, 39 después del último y 20 en fronteras/baipases/márgenes. La coincidencia
con resultados/modelos no acredita homogeneidad real de tráfico por tramo.

Se añadió `cierre_flujo.py --comprobar`: verifica la tabla sin sobrescribirla y falla
si falta o fue alterada. Tres pruebas de integración verifican ese comportamiento.
Los detalles del entorno y de las comprobaciones están en
[integracion_vicente.md](../../resultados/cierre/integracion_vicente.md).

Se precisó el lenguaje sobre fechas de publicación y archivos meteorológicos en
la ficha 02 y la matriz. Consultar los enlaces primarios de su sección 5; una fecha
en la ruta de una URL no acredita primera publicación. La búsqueda Wayback descrita
por Vicente no adjunta un resultado archivístico verificable. Las limitaciones
continúan abiertas y no se han sustituido datos ni repetido entrenamientos.

## Integración recibida de Cristóbal

Se sincronizaron los commits `07df973`, `dbe7ef7` y `3963bd3` de `origin/main`
conservando autoría. Incluyen seis tablas, dos figuras y cuatro generadores de
comparación, aporte de lluvia/flujo, generalización y calibración. Las seis tablas
se reprodujeron exactamente en una carpeta temporal; los generadores pasan a
`codigo/evaluacion` según la organización acordada. Se conserva el contenido de
las tablas y figuras recibido. Consultar la [revisión de integración](integracion_cristobal.md).

Diego informó que Cristóbal terminó su parte. En los commits recibidos todavía no
aparecen la ficha narrativa 04 ni una constancia de revisión de la ficha 02. El
aporte técnico queda recibido e integrado; esa ausencia documental no significa
que Cristóbal no haya realizado la revisión fuera del repositorio.

## Pendientes reales y responsables

- **Diego:** integraciones técnicas de Vicente y Cristóbal realizadas; recibir las fichas
  03 y 04, comprobar su coherencia y repetir las verificaciones tras esos cambios.
- **Vicente:** trabajo recibido e integrado; la revisión de contenido de Cristóbal
  sigue pendiente. Exposición vehicular y publicación histórica quedan como límites,
  no como requisitos supuestamente cumplidos por incluir un proxy.
- **Martín:** ficha de modelo final e interpretación de artefactos. Sigue pendiente
  su revisión cruzada humana de la reproducción de Diego.
- **Cristóbal:** tablas, figuras y generadores recibidos y comprobados. Queda por
  incorporar al repositorio la ficha narrativa 04 y la constancia de revisión de
  la ficha 02; la lectura técnica de integración ya está disponible como apoyo.
- **Máximo:** presentación. Recibe tablas, figuras y conclusiones verificadas; esta
  integración no modifica la presentación.

El notebook anotado sigue siendo obligatorio. Se prepara después de estabilizar
código y resultados, como acordó el equipo, y debe poder ejecutar las conclusiones.
La carga final es grupal y la realiza una sola persona. No se ha realizado ningún
envío académico desde esta integración.

## Alcance y criterios de cierre

La ampliación a 2025 se investigó por geometría, direcciones y capas adicionales,
y se cerró para esta entrega por falta de ubicación vial comparable acreditada.
Se mantiene **2020–2024**; no hay que integrar una cohorte parcial de 2025 como si
fuera el año completo ni repetir entrenamientos por este intento. La
[decisión y evidencia](../cierre_ubicacion_2025.md) se incorporan a las limitaciones
que explicará el equipo. Solo se reabre con información nueva que resuelva ese punto.

Se mantiene Ruta 5 Sur como alcance principal. Extensión a otras rutas y actualización
del prototipo quedan para después de resolver este caso. Se estudian conteos y
priorización retrospectiva; se implementó una emisión reproducible del piloto en
modo sombra, pero no se acredita un servicio operativo ni riesgo por vehículo-km.
Su evaluación con siniestros observados, sensibilidad urbana y umbrales sigue
pendiente. La ampliación 2025 se cerró por falta de ubicación comparable, no por
data leakage; la separación temporal de entrenamiento y evaluación se mantiene.

Antes de enviar, Diego debe comprobar que cada cifra tiene tabla, población, año y
unidad, que la candidata coincide con el artefacto citado y que las fichas aprobadas,
README, notebook ejecutado y presentación dicen lo mismo. Las pruebas automáticas
no sustituyen la interpretación ni las aprobaciones humanas pendientes.
