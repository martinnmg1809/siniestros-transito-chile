# Cómo resolver la ubicación vial de 2025

Proyecto: **Predicción dinámica de siniestros en carreteras chilenas**.
Consulta de fuentes: 14/11/2026. Investigación posterior al [EDA nacional](eda_conaset_2025.md).

**Actualización:** el procedimiento ya se implementó y se probó con la alternativa
REST oficial, sin mezclar fuentes. El [informe de ejecución](validacion_ubicacion_vial.md)
documenta el 78,04 % de sensibilidad, las ambigüedades y la decisión de no asignar
2025. Lo siguiente conserva la investigación y el procedimiento iniciales.

**Hay una vía técnica para investigarlo:** relacionar cada coordenada con una
carretera oficial que tenga medidas de recorrido. Primero hay que validar tanto
la pertenencia a Ruta 5 Sur como el kilometraje. No se han asignado eventos de
2025 ni se ha demostrado todavía que el procedimiento alcance calidad suficiente.

## Fuente encontrada y comprobación realizada

El [portal UGIT de Vialidad](https://mapasvialidad.mop.gob.cl/) publica cartografía
de la red caminera. La [página de descargas](https://mapasvialidad.mop.gob.cl/descargas/)
enlaza los ZIP GDB/SHP con nombre fechado 05/08/2026 y un servicio REST
`VIALIDAD/Red_Vial_Chile/MapServer`, **sin guion bajo final**.
También aparece indexado otro servicio, `Red_Vial_Chile_`. No son intercambiables.
No se descargaron los ZIP nacionales.

Se consultaron la capa 3, conteos, listas de OBJECTID, atributos de toda Ruta 5 y
una geometría de muestra por servicio. Se comprobaron los identificadores y que
la respuesta de atributos no estuviera truncada.

| Comprobación | Servicio enlazado por Descargas | Alternativa indexada con `_` |
|---|---:|---:|
| Entidades con ROL_LABEL='5' | 71 | 79 |
| Con ORIENTACION='SUR' | 10 | 26 |
| Con KM_I=KM_F=0 | 0 | 7 |
| Capa declara geometría con medida M | Sí | Sí |
| OBJECTID de la muestra geométrica | 150586 | 5078 |
| Vértices de la muestra con M numérica | 1.324 / 1.324 | 4.113 / 4.113 |

Las entidades son piezas de cartografía; no representan nuestros tramos de 5 km.
Los atributos incluyen ROL, CALZADA, ORIENTACION, KM_I y KM_F. Al solicitar
`returnM=true`, `returnZ=false` y `outSR=4326`, las muestras devolvieron vértices
`[longitud, latitud, M]`. M es una medida a lo largo de la carretera, distinta de
la distancia perpendicular del evento a ella.

En la muestra de La Araucanía del servicio enlazado, M va de 681155,9244 a
715216,1867 y KM_I/KM_F son 681156/715216. La escala es compatible con metros,
pero **la unidad y su correspondencia con el kilómetro CONASET aún deben
confirmarse** mediante metadatos y contraste de eventos conocidos. No se convirtió
ningún evento basándose solo en esa apariencia.

No se debe filtrar únicamente ORIENTACION='SUR': hay piezas de Ruta 5 en
La Araucanía con orientación `-` y con medidas de recorrido. Tampoco `ROL='5'`
es el filtro correcto en estos servicios: los atributos consultados usan
`ROL='Ruta 5'`; se comprobó el filtro `ROL_LABEL='5'`.

**La vigencia sigue pendiente.** La descripción del servicio enlazado menciona
actualizaciones de 2015/2017; el nombre del ZIP lleva fecha de 2026. Ese nombre
no demuestra que el REST tenga igual versión ni que todos los trazados sean de
2025. Debemos escoger y conservar una versión, comprobar fecha de referencia y
revisar variantes, baipases, obras y discontinuidades. No mezclar geometrías o
medidas de ambos servicios para rellenar huecos sin una conciliación explícita.

Evidencia: [resumen](../resultados/ubicacion_vial/fuentes.csv),
[atributos del servicio enlazado](../resultados/ubicacion_vial/enlace_descargas_ruta5.csv),
[atributos de la alternativa](../resultados/ubicacion_vial/alternativa_indexada_ruta5.csv)
y [auditoría de consultas y hashes](../resultados/ubicacion_vial/auditoria.json).
Originales locales: `data/fuentes/mop/revision_ubicacion_20261114/`, fuera de Git.

## Procedimiento que se debe implementar y validar

1. **Fijar la cartografía de referencia.** Obtener geometría completa de las vías
   del corredor y sus competidoras, comprobar medidas M, unidades, calzadas y
   continuidad. No basta con descargar exclusivamente Ruta 5: hace falta detectar
   calles o caminos paralelos y cruces que puedan generar una falsa asignación.
   Conservar versión, filtros y hashes. No se ha completado esta descarga ni su QA.
2. **Proponer candidatos por coordenada.** Trabajar con una transformación
   geográfica documentada y distancias métricas. Para cada punto, conservar las
   vías próximas, distancia al eje y alternativas. La vía más cercana es un
   candidato, no una etiqueta verdadera; un punto aislado tampoco aporta rumbo.
3. **Calcular el recorrido solo en candidatos válidos.** Proyectar el punto sobre
   un segmento de la polilínea e interpolar sus M entre vértices, después de
   verificar que sean válidas. No repartir KM_I–KM_F proporcionalmente sobre toda
   una entidad sin comprobar su medida interna, ni unir extremos de partes
   separadas. Confirmada la unidad, convertir a km y aplicar la misma convención
   histórica de tramos de 5 km. Mantener en revisión los casos próximos a bordes,
   enlaces, vías alternativas o medidas discontinuas.
4. **Medir el error con etiquetas conocidas.** Fijar reglas con datos anteriores y
   comprobarlas sobre 2024 sin retocarlas para favorecer el resultado. Hacen falta
   eventos de Ruta 5 Sur y de otras vías con etiqueta conocida; los eventos con
   ruta vacía son desconocidos, no negativos. Si faltan controles previos para
   fijar reglas, recuperarlos antes de cerrar el procedimiento. La cuarentena
   histórica se conserva y sus casos se informan por separado.
5. **Informar calidad y cobertura juntas.** Medir precisión de pertenencia vial,
   sensibilidad, error absoluto de km y porcentaje de tramo de 5 km correcto.
   Informar denominadores, proporción asignada/rechazada/ambigua, resultados por
   zona y sensibilidad a distancia. Una precisión alta en pocos puntos no acredita
   cobertura completa. Establecer tolerancias antes de aceptar una regla; no se
   ha declarado ningún umbral como validado.
6. **Aplicar a 2025 solo si supera la comprobación.** Guardar un derivado separado
   con ruta y km **inferidos**, fuente cartográfica, versión del método, distancias,
   alternativas y motivo de aceptación/revisión/rechazo. Conservar intactos Ruta
   y Ubicación originales. Si se retienen solo algunos eventos, no convertir los
   excluidos en ausencia de siniestros en la grilla ni comparar esa cohorte parcial
   con todo el histórico sin cuantificar el cambio de cobertura.

La referencia espacial y los modelos actuales no se modifican. Si se reconstruyen
ubicaciones antiguas usando una cartografía posterior, debe declararse como
reconstrucción retrospectiva y comprobar trazados; no se presenta esa cartografía
como información disponible al emitir un pronóstico histórico.

## Resultado posible y siguiente paso

El siguiente trabajo es la descarga acotada y la validación del eje con medidas,
antes de programar la incorporación de 2025. La existencia de M facilita estimar
kilómetros; no elimina la ambigüedad de pertenencia a una vía.

Si el método falla en ciertas zonas, se dejan sin resolver y se busca otra versión
o microdatos con ruta/km originales. No se envió ninguna solicitud a CONASET o MOP.
Si solo resulta fiable una parte del corredor, cualquier evaluación quedaría
limitada a esa cohorte documentada, sin redefinir automáticamente el alcance del
modelo actual. Entrenamiento, validación temporal y piloto quedan condicionados a
esa decisión de calidad.
