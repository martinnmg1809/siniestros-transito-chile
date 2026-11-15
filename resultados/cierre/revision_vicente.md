# Revisión de la ficha de datos y flujo

14/11/2026 · Base `72b2c98` · Realizada por encargo de Diego con asistencia de Codex.
Revisa el aporte de Vicente; no representa una firma personal de Cristóbal.

| Comprobación ejecutada | Resultado |
|---|---|
| cierre_flujo --comprobar, sin escritura | 14.420 eventos; 255 tramos; cobertura 153; exclusiones 43/39/20 |
| Tabla de flujo | 5.100 filas; 3.060 con flujo y 2.040 sin proxy ni puntos |
| Rezago | período medido = objetivo − 2 trimestres; cierre anterior al objetivo en todas las filas; mínimo 91 días |
| Puntos implícitos | 1.143 residuos no nulos; máximo absoluto 7,2953e−9 |
| Cohortes | Igual conteo de eventos entre clima y clima+flujo por familia/año/partición en con_contrato |
| Híbridos | 7/9 diferencias de captura con flujo negativas; rango −0,49904 a +0,34928 pp |
| Exposición validada | Tabla vacía; no se validó TMDA ni vehículo-km |
| Publicación acreditada | Falsa en todas las filas; el rezago no acredita disponibilidad histórica |
| Anexos DGC locales | Los dos hashes coinciden con fuentes_dgc.json |
| Código de extracción | Fórmula promedio mensual × 3 / días del trimestre; unidades por punto/contrato, no vehículo-km |
| Pruebas pertinentes | 7 pruebas de test_modelado.py aprobadas |
| verificar_cierre | CORRECTO: integridad, 114 métricas, 36 selecciones, 60 búsquedas, 81 IC, 360 deciles y recalibración |

No se descargaron fuentes ni se reentrenó. La consulta de disponibilidad histórica
de §5 de la ficha se conserva como antecedente, no como una investigación nueva.
Esta revisión comprueba los archivos y transformaciones disponibles; no acredita
geometría adicional, metadatos de publicación ausentes ni validación operativa.
Los seis resúmenes de Cristóbal ya se regeneraron exactamente en la integración
anterior; véase docs/cierre/integracion_cristobal.md.

## Huellas de la evidencia revisada

| Archivo | SHA256 |
|---|---|
| resultados/modelos/flujo_rezagado.csv | `29d362156d8f2dcd28d0f3227f95aa4e765618dc5af1a6f8085e923009f12822` |
| resultados/cierre/cobertura_flujo_detalle.csv | `5d932935cf5a09363017f189185c93adbd228b342ce5c3e928edd137155bef3d` |
| resultados/modelos/metricas.csv | `a00a2e20e833c8869dcff2e73634918db2846e6db89a57484c09be6d1d154e07` |
| resultados/modelos/bootstrap.csv | `189f690468eb4917e9c1d9831c39c630045642902249ef5872db60c17d51a83d` |
| resultados/flujo/fuentes_dgc.json | `f60a0018abc9f4b6184747e36fe37bee39196378ec66303a634ed7375e3d0143` |
| resultados/flujo/exposicion_validada.csv | `af4b866286fce1db9a84f22ad4f69582d94270cd157cf2d0efe202e69e680a9b` |
