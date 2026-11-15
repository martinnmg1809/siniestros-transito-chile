"""Extrae flujo trimestral oficial de contratos Ruta 5, preservando unidades.

No es un denominador vehículo-km: una pasada es una transacción de cobro y un
vehículo puede producir varias. Santiago-Talca incluye Acceso Sur. Los valores
se conservan por versión del anexo; no prueban disponibilidad histórica as-of.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import pandas as pd
import xlrd

FUENTES = {
    "2024_4t": "https://concesiones.mop.gob.cl/uploads/sites/4/2025/03/2024_Anexo_4T.xls",
    "2023_4t": "https://concesiones.mop.gob.cl/uploads/sites/4/2024/12/2023_Anexo_4T_Informe_Trimestral_oct_dic.xls",
}
SUR = {"Santiago-Talca y Acceso Sur a Santiago", "Talca-Chillán", "Chillán-Collipulli",
       "Collipulli-Temuco", "Temuco-Río Bueno", "Río Bueno-Puerto Montt", "Puerto Montt-Pargua"}


def columna_excel(i):
    s = ""
    while i >= 0:
        s = chr(i % 26 + 65) + s
        i = i // 26 - 1
    return s


def extraer(archivo, version, url, anio_minimo=2020):
    libro = xlrd.open_workbook(archivo)
    total = libro.sheet_by_name("Transacciones_Viales")
    promedio = libro.sheet_by_name("Transacciones_portico_mes")
    posiciones = [(r, c) for r in range(total.nrows) for c in range(total.ncols)
                  if str(total.cell_value(r, c)).startswith("Total Ruta 5")]
    if len(posiciones) != 1:
        raise ValueError("No se identifica una única sección Total Ruta 5")
    r0, c0 = posiciones[0]
    # Encabezados combinados: año a la izquierda de cada grupo de cuatro trimestres.
    columnas, anio = [], None
    for c in range(c0 + 1, total.ncols):
        v = total.cell_value(r0 + 1, c)
        if isinstance(v, (int, float)) and 2000 <= v <= 2100:
            anio = int(v)
        q = total.cell_value(r0 + 2, c)
        if anio is not None and q in ("I", "II", "III", "IV"):
            columnas.append((c, anio, ("I", "II", "III", "IV").index(q) + 1))
    filas = []
    for r in range(r0 + 3, total.nrows):
        contrato = str(total.cell_value(r, c0)).strip()
        if contrato.lower().startswith("total general"):
            break
        if not contrato:
            continue
        for c, anio, trimestre in columnas:
            if anio < anio_minimo:
                continue
            valor = total.cell_value(r, c)
            if valor == "":
                continue
            if not isinstance(valor, (int, float)) or valor < 0:
                raise ValueError(f"Transacciones inválidas: {contrato}, {anio}T{trimestre}")
            # Las tres secciones usan el mismo ancho y orden de años/trimestres.
            ancho = (c0 - 1) // 2
            livianos, pesados = total.cell_value(r, c - 2 * ancho), total.cell_value(r, c - ancho)
            if abs(livianos + pesados - valor) > .5:
                raise ValueError(f"Livianos + pesados no concilia con total: fila {r + 1}")
            # Buscar por contrato porque los anexos pueden agregar o reordenar filas.
            rp = [i for i in range(promedio.nrows)
                  if "".join(str(promedio.cell_value(i, c0)).split()) == "".join(contrato.split())]
            if len(rp) != 1:
                raise ValueError(f"Contrato no único en hoja de promedio: {contrato}")
            vm = promedio.cell_value(rp[0], c)
            if not isinstance(vm, (int, float)) or vm <= 0:
                raise ValueError("Promedio por pórtico ausente o no positivo")
            inicio = pd.Timestamp(anio, 3 * (trimestre - 1) + 1, 1)
            fin = inicio + pd.DateOffset(months=3)
            dias = (fin - inicio).days
            filas.append({"version_anexo": version, "contrato": contrato,
                          "ruta5_sur": contrato in SUR, "anio": anio,
                          "trimestre": trimestre, "inicio": inicio.date().isoformat(),
                          "fin_exclusivo": fin.date().isoformat(), "dias": dias,
                          "transacciones_trimestre": valor,
                          "pasadas_promedio_por_punto_mes": vm,
                          "proxy_pasadas_por_punto_dia": vm * 3 / dias,
                          "fuente": url, "hoja_total": total.name,
                          "celda_total": f"{columna_excel(c)}{r + 1}",
                          "hoja_promedio": promedio.name,
                          "celda_promedio": f"{columna_excel(c)}{rp[0] + 1}",
                          "disponibilidad_historica_acreditada": False,
                          "nota": "Transacciones de cobro, no vehículos-km; no usar como offset horario validado"})
    return pd.DataFrame(filas)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--descargar", action="store_true")
    p.add_argument("--fuentes", type=Path, default=Path("data/fuentes/dgc"))
    p.add_argument("--salida", type=Path, default=Path("resultados/flujo"))
    args = p.parse_args()
    args.fuentes.mkdir(parents=True, exist_ok=True)
    args.salida.mkdir(parents=True, exist_ok=True)
    tablas, manifiesto = [], []
    for version, url in FUENTES.items():
        archivo = args.fuentes / f"anexo_{version}.xls"
        if args.descargar:
            with urllib.request.urlopen(url, timeout=60) as r:
                archivo.write_bytes(r.read())
        tablas.append(extraer(archivo, version, url))
        manifiesto.append({"version": version, "url": url,
                           "sha256": hashlib.sha256(archivo.read_bytes()).hexdigest()})
    datos = pd.concat(tablas, ignore_index=True)
    datos.to_csv(args.salida / "transacciones_concesiones.csv", index=False)
    datos.loc[datos.ruta5_sur].to_csv(args.salida / "transacciones_ruta5_sur.csv", index=False)
    (args.salida / "fuentes_dgc.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2))
    print(datos.loc[datos.ruta5_sur].groupby(["version_anexo", "contrato"]).size().to_string())


if __name__ == "__main__":
    main()
