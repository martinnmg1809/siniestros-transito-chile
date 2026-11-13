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
