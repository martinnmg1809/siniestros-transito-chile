# Predicción dinámica de siniestros en carreteras chilenas

Nombre oficial indicado por Diego el 14 de noviembre de 2026. Debe utilizarse
en documentos vigentes, notebook final, presentación y comunicaciones del proyecto.

## Problema y propósito

El proyecto estudia cómo cambia el conteo esperado de siniestros por tramo y hora
según la ubicación, el calendario y las condiciones meteorológicas, para orientar
la priorización de vigilancia durante ventanas de 12 horas. El historial por lugar
es una referencia; los modelos incorporan contexto temporal y evalúan si mejora
esa referencia. No prometen anticipar cada siniestro ni demostrar prevención causal.

El nombre tiene alcance general, pero la evaluación técnica actual se concentra
en **Ruta 5 Sur**, con datos 2020–2024. El prototipo multirruta es un antecedente;
no implica validación de la nueva candidata en todas las carreteras chilenas.

## Identificación en GitHub

- Repositorio actual: [martinnmg1809/siniestros-transito-chile](https://github.com/martinnmg1809/siniestros-transito-chile).
- Identificador propuesto: `prediccion-dinamica-de-siniestros-en-carreteras-chilenas`.
- Título visible: **Predicción dinámica de siniestros en carreteras chilenas**.
- Descripción propuesta: «Predicción dinámica de siniestros en carreteras chilenas.
  Estimación de conteos por tramo y hora para priorizar vigilancia; validación
  retrospectiva en Ruta 5 Sur con calendario, lluvia y proxy de circulación».

Estado: **cambio administrativo pendiente**. La cuenta conectada `diegofranco1`
puede publicar código (`push: true`), pero no administrar el repositorio
(`admin: false`, `maintain: false`). El intento autorizado de cambiar nombre y
descripción mediante la API recibió HTTP 404. No se cambió el remoto local ni
se sustituyeron enlaces por direcciones que todavía no existen.

## Paso del propietario

Martín, desde la cuenta propietaria `martinnmg1809`, o alguien con administración:

1. Abrir [Settings del repositorio actual](https://github.com/martinnmg1809/siniestros-transito-chile/settings).
2. En **Repository name**, introducir
   `prediccion-dinamica-de-siniestros-en-carreteras-chilenas` y pulsar **Rename**.
3. Actualizar la descripción de **About** con el texto anterior.
4. Comunicar el cambio al equipo para actualizar enlaces, remotos y la tarea
   automática. La carpeta local puede conservar su nombre hasta ajustar esas rutas.

GitHub requiere propiedad de organización o permiso de administración para
renombrar. Las operaciones Git se redirigen, pero las URL de sitios de proyecto
GitHub Pages son una excepción. Por tanto, comprobar la nueva dirección del
prototipo y sus enlaces después del cambio. Referencia:
[renombrar un repositorio, documentación oficial](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository).

Cuando el cambio exista, el remoto previsto será:

```bash
git remote set-url origin https://github.com/martinnmg1809/prediccion-dinamica-de-siniestros-en-carreteras-chilenas.git
```

Este comando es una instrucción posterior al cambio; no se ejecutó durante esta
actualización de identidad. No se creó otro repositorio ni se perdió el historial.

## Material actualizado y antecedentes

Se aplicó el nombre al README, fichas vigentes y documentos de navegación,
planificación PDF, título/encabezado/descripción del prototipo HTML y sus generadores.
Las tablas científicas, auditorías, pesos y reglas de evaluación conservan sus datos.
Los documentos entregados anteriormente se mantienen como antecedentes en
`docs/historico/`; su título original identifica la versión efectivamente elaborada.
El notebook y la presentación finales deben llevar el nombre oficial al prepararlos.
