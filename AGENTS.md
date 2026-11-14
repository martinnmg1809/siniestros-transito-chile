# Autoría de los commits

- Mantener la identidad de Git configurada para el usuario y usarla como committer.
- Por defecto, mantener al usuario como autor principal. Si solicita atribuir un commit
  realizado por Codex a la cuenta Codex, usar únicamente para ese commit
  `--author="Codex <noreply@openai.com>"` y añadir al usuario como coautor con su identidad
  real de Git. No cambiar `user.name` ni `user.email` para lograr esa atribución.
- En los commits con autor principal humano que incluyan trabajo realizado con Codex,
  añadir al final del mensaje,
  separado del cuerpo por una línea en blanco:

  ```text
  Co-authored-by: Codex <noreply@openai.com>
  ```

- Aplicar esta atribución solo cuando Codex haya contribuido al contenido del commit;
  no atribuirle cambios ajenos o realizados íntegramente por una persona.
- Conservar la autoría y el historial de los commits publicados. Esta configuración se
  aplica a commits nuevos; no requiere reescribir el historial ni hacer force-push.

## Organización y ejecución

- El código vive en `codigo/datos`, `codigo/modelos`, `codigo/evaluacion`,
  `codigo/visualizacion` y `codigo/historico`. No volver a crear scripts en la raíz.
- Ejecutar tareas con `.venv/bin/python proyecto.py <comando> [opciones]`.
  El lanzador prepara los módulos y el directorio de trabajo; `--listar` muestra el catálogo.
- Conservar nombres de módulos y clases para cargar los modelos joblib anteriores.
- Los CSV CONASET están en `data/siniestros`, el calendario en `data/calendario`
  y los cachés en `data/cache`. Los dos últimos son insumos locales excluidos de Git.
- El README principal es un índice. Resultados y EDA se documentan en
  `docs/resultados.md` y `docs/eda.md`; los generadores mantienen allí sus bloques.
- Las auditorías originales conservan sus hashes. `config/migracion_estructura.csv`
  registra exclusivamente la reorganización. No actualizarlo para eludir cambios
  científicos o aceptar código alterado: esos cambios requieren validar y auditar
  el experimento correspondiente.

## Mantenimiento programado

- El usuario autorizó revisiones cada cuatro horas con correcciones, comprobación y
  publicación directa en `origin/main`. La tarea programada está asociada al chat del
  proyecto y se administra desde la aplicación; este archivo no inicia un proceso.
- Leer el README y los cambios recientes. Priorizar errores reproducibles y documentación
  que ayude al proyecto. Hacer una mejora acotada por ejecución y registrar la evidencia
  en el README; si no hay una mejora justificada, informar sin crear commits de relleno.
- Trabajar sobre `main` con un checkout limpio. Si hay cambios ajenos, otra rama activa
  o divergencia, conservar ese trabajo e informar. Sincronizar solo mediante fast-forward.
- Publicar únicamente cambios propios que pasen las comprobaciones pertinentes. Para
  documentación revisar coherencia, enlaces y `git diff --check`; para código ejecutar
  pruebas relacionadas. Comunicar el enlace al commit o el motivo concreto de un bloqueo.
- Mantener notebook y presentación para la fase final. Conservar las fuentes originales,
  la cuarentena, UTC/DST, la separación temporal y el criterio de selección acordado.
  No cambiar el objetivo científico ni interpretar el proxy trimestral como vehículo-km.
- No repetir entrenamientos completos o descargas grandes por rutina. Si una corrección
  invalida resultados, actualizar la evidencia con el protocolo existente y documentarlo.
