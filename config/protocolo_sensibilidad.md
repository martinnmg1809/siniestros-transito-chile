# Protocolo de sensibilidad previo a las corridas

Fecha: 14/11/2026. Base: 67830c1. Autorizado por Diego en el chat.

- Objetivo principal, población de 255 tramos, cuarentena, UTC/DST y selección
  original se conservan. 2024 es evaluación histórica reutilizada.
- Urbana: ranking congelado Poisson_clima y M1 para 2022/2023/2024; evaluar captura
  de eventos ZONA=URBANA y RURAL por separado, conservando el presupuesto sobre
  todos los tramos-hora. Valores no reconocidos se informan como desconocidos.
  No se infiere zona de un tramo a partir de eventos ni se reentrena un objetivo rural.
- Lluvia: escenarios actual (0,1; 0,5), A (0,05; 0,5), B (0,1; 1,0) mm/h.
  Se ajusta nuevamente solo Poisson para A y B, con parámetros originales por fold:
  L2=3 para 2022/2023 y L2=0,3 para 2024. Sin búsqueda ni selección de escenario.
- Entrenamiento expansivo 2020 hasta el año anterior a prueba; semillas 42.
  Categorías alternativas se aplican tanto en entrenamiento como en prueba.
- Control: el escenario actual debe reproducir todas las métricas publicadas
  de Poisson y M1 (rtol=1e-8, atol=1e-10) antes de interpretar alternativas.
- Salidas: captura global y por turno, O/E, MAE total de cohorte por turno,
  desvianza, cambios en categorías y coincidencia de los 12 tramos prioritarios
  por turno con desempate por índice ascendente. Este último diagnóstico usa
  selección entera 12/255, diferente del presupuesto fraccionario al 5 %.
- IC urbanos: bootstrap semanal pareado, 2.000 réplicas, predicciones fijas;
  no mide incertidumbre del reentrenamiento ni corrige múltiples comparaciones.
  Alternativas de lluvia: comparación descriptiva sin declarar significancia.
- Las alternativas no reemplazan el modelo final ni se integran al piloto.
  Nuevas salidas en resultados/sensibilidad; fuentes y tablas originales intactas.
