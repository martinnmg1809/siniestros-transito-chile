# Autoría de los commits

- Mantener al usuario como autor y committer mediante la identidad de Git ya configurada.
- En los commits que incluyan trabajo realizado con Codex, añadir al final del mensaje,
  separado del cuerpo por una línea en blanco:

  ```text
  Co-authored-by: Codex <noreply@openai.com>
  ```

- Aplicar esta atribución solo cuando Codex haya contribuido al contenido del commit;
  no atribuirle cambios ajenos o realizados íntegramente por una persona.
- Conservar la autoría y el historial de los commits publicados. Esta configuración se
  aplica a commits nuevos; no requiere reescribir el historial ni hacer force-push.
