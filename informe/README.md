# Informe Etapa I

`etapa1.md` es la fuente. El PDF se regenera con:

```bash
pandoc etapa1.md -o etapa1.docx --reference-doc=plantilla-referencia.docx && libreoffice --headless --convert-to pdf etapa1.docx --outdir .
```

`plantilla-referencia.docx` es la plantilla por defecto de pandoc con un pie de página
de numeración inyectado: pandoc no la genera con footer y LibreOffice no la agrega sola.

Pendiente antes de entregar: completar los integrantes del equipo en la portada.
