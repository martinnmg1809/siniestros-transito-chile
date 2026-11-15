# Extensión exploratoria de sensibilidad urbana: población rural

14/11/2026, después del diagnóstico inicial y antes del ajuste rural.
El diagnóstico de ZONA encuentra urbanos únicamente en 2020–2021, y ninguno en
2022–2024. El contraste urbano con ranking congelado no es identificable en prueba.

Se completa la exclusión urbana solicitada con un objetivo exploratorio distinto:
conteos de eventos etiquetados RURAL, sin inferir la zona física de ningún tramo.
Se mantienen los 255 tramos, referencia 2020–2021 original, calendario, lluvia
original (0,1/0,5), exposición UTC/DST y años de entrenamiento/prueba. La referencia
no se reconstruye con eventos de prueba ni con la población filtrada.

- Ajustar Poisson_clima rural en 2020–2021, 2020–2022, 2020–2023.
- Mantener L2 previamente fijado por fold (3; 3; 0,3), sin nueva selección.
- Reconstruir M1 con eventos rurales del entrenamiento y L2=1, mismo dominio.
- Comparar con resultados originales sobre la misma prueba, solo después de
  comprobar igualdad exacta de conteos de prueba rural y original en 2022–2024.
- Reportar captura, O/E, MAE, desvianza y tamaño de entrenamiento. No reemplazar
  candidata ni interpretar como prueba de robustez geográfica urbana independiente.
- Una alteración de la distribución de etiquetas puede modificar la tendencia
  ajustada; no se atribuirán causalmente cambios a la urbanización física.
