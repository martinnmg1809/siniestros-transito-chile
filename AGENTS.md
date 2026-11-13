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
