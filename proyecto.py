#!/usr/bin/env python3
"""Entrada única y rutas del proyecto. Ejemplo: python proyecto.py verificar_cierre.

Los módulos conservan sus nombres para poder cargar los modelos joblib existentes.
No se instala nada ni se descarga información al preparar estas rutas.
"""
import csv
import hashlib
from pathlib import Path
import os
import runpy
import sys

RAIZ = Path(__file__).resolve().parent
CARPETAS = ("datos", "modelos", "evaluacion", "visualizacion", "historico")


def configurar():
    for carpeta in reversed(CARPETAS):
        directorio = str(RAIZ / "codigo" / carpeta)
        if directorio not in sys.path:
            sys.path.insert(0, directorio)


def movimientos(raiz=RAIZ):
    with (Path(raiz) / "config/migracion_estructura.csv").open(newline="") as f:
        return {r["origen"]: r for r in csv.DictReader(f)}


def ruta(nombre, raiz=RAIZ):
    """Resolver nombres anteriores y rutas actuales, sin crear enlaces simbólicos."""
    nombre = str(nombre)
    entrada = movimientos().get(nombre)
    return Path(raiz) / (entrada["destino"] if entrada else nombre)


def integridad(raiz, nombre, esperado):
    """Verificar el hash de la corrida o la migración explícita de su código.

    Las auditorías originales se conservan. Solo las parejas de hashes registradas
    en la migración permiten verificar código con cambios de rutas; otras ediciones
    requieren otra revisión. No afirma identidad binaria con el código anterior.
    """
    archivo = ruta(nombre, raiz)
    if not archivo.is_file():
        raise ValueError(f"Falta {nombre}; consultar docs/cierre/01_reproducibilidad.md")
    with archivo.open("rb") as f:
        actual = hashlib.file_digest(f, "sha256").hexdigest()
    if actual == esperado:
        return
    entrada = movimientos(raiz).get(str(nombre), {})
    if entrada.get("sha256_antes") == esperado and entrada.get("sha256_despues") == actual:
        return
    raise ValueError(f"Hash distinto: {nombre}; no mezclar versiones de evidencia")


def main():
    configurar()
    comandos = {p.stem: p for carpeta in CARPETAS for p in (RAIZ / "codigo" / carpeta).glob("*.py")
                if p.name != "__init__.py"}
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "--listar"):
        print("Uso: python proyecto.py <comando> [opciones]\n")
        for carpeta in CARPETAS:
            print(carpeta + ": " + ", ".join(sorted(n for n, p in comandos.items() if p.parent.name == carpeta)))
        return 0
    nombre = sys.argv[1].removesuffix(".py")
    if nombre not in comandos:
        print(f"Comando desconocido: {nombre}. Usar --listar.", file=sys.stderr)
        return 2
    archivo = comandos[nombre]
    sys.argv = [str(archivo), *sys.argv[2:]]
    # Los parámetros de salida siguen siendo relativos a la raíz, como en las corridas.
    os.chdir(RAIZ)
    runpy.run_path(str(archivo), run_name="__main__")
    return 0


configurar()

if __name__ == "__main__":
    raise SystemExit(main())
