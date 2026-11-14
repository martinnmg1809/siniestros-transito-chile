# Informe Etapa I

## `etapa1.tex` — fuente principal

Compilar (dos veces, para que cuadre el índice):

```bash
pdflatex etapa1.tex && pdflatex etapa1.tex
```

Paquetes: `geometry`, `babel`, `booktabs`, `longtable`, `array`, `amsmath`,
`hyperref`, `enumitem`, `xcolor`, `titlesec`, `fancyhdr`. Todos vienen en
`texlive-latex-recommended` y `texlive-latex-extra`.

**En esta máquina no hay LaTeX instalado**, así que el `.tex` no se compiló aquí.
Se revisó con un linter (llaves, `$`, `begin`/`end`, `\ref`/`\label`, número de
columnas de cada tabla, caracteres especiales sin escapar) pero eso no sustituye
una compilación. Para compilarlo sin instalar nada, subir el `.tex` a Overleaf.

Instalación local si se prefiere:

```bash
sudo apt install texlive-latex-recommended texlive-latex-extra texlive-lang-spanish
```

## `etapa1.md` — versión alternativa

Genera el mismo contenido sin necesidad de LaTeX, usando pandoc y LibreOffice:

```bash
pandoc etapa1.md -o etapa1.docx --reference-doc=plantilla-referencia.docx
libreoffice --headless --convert-to pdf etapa1.docx --outdir .
```

`plantilla-referencia.docx` es la plantilla por defecto de pandoc con un pie de
página de numeración inyectado a mano: pandoc no la genera con footer y
LibreOffice no lo agrega solo.

Este camino sí se ejecutó y produjo `etapa1.pdf`.

## Pendiente antes de entregar

Completar los integrantes del equipo en la portada (`.tex`, línea con el
comentario `COMPLETAR AQUÍ`).
