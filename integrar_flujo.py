"""Asociación documentada contrato–tramo y predictores de flujo rezagado.

Las pasadas por punto de cobro son un proxy trimestral, no exposición medida
vehículo-km. Los anexos actuales no permiten certificar un backtest as-of.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from flujo_concesiones import FUENTES, extraer

RED = "https://vialidad.mop.gob.cl/uploads/sites/9/2024/11/Red-Vial-Nacional-Dimensionamiento-y-Caracteristicas-Ano-2024.pdf"
TALCA = "https://concesiones.mop.gob.cl/uploads/sites/4/2025/02/Diptico_TACHI_2024_06.pdf"
RIO = "https://concesiones.mop.gob.cl/uploads/sites/4/2025/03/Diptico_RBPM_2019_03.pdf"


def normalizar_puntos(valores, tolerancia=1e-6):
    """Eliminar ruido de división próximo a entero sin truncar fracciones reales.

    El resultado sigue siendo una cantidad inferida, no un censo físico de plazas.
    Evita que los árboles separen 4 y 4+1e-9 como niveles de composición distintos.
    """
    valores = np.asarray(valores, float)
    enteros = np.rint(valores)
    return np.where(np.abs(valores - enteros) <= tolerancia, enteros, valores)


def limites_documentados():
    """Interiores comunes y conservadores; no decidir límites por accidentes.

    Collipulli: se omite la frontera 570–580, discrepante entre documentos de
    contratos sucesivos. Temuco: no se asigna el bypass con kilometraje propio.
    Río Bueno: intersección conservadora del troncal de 2019 y catálogo 2023.
    """
    filas = [
        ("Talca-Chillán", 219.490, 412.800, TALCA, 1, "Troncal; baipás futuro excluido"),
        ("Chillán-Collipulli", 412.800, 570.000, RED, 409, "Límite superior restringido a interior común"),
        ("Collipulli-Temuco", 580.000, 659.520, RED, 409, "Frontera Collipulli excluida; antes de bypass"),
        ("Collipulli-Temuco", 680.840, 718.335, RED, 409, "Troncal posterior a bypass"),
        ("Temuco-Río Bueno", 718.335, 890.000, RED, 409, "Troncal Ruta 5"),
        ("Río Bueno-Puerto Montt", 895.450, 1020.637, RIO, 1, "Interior común con catálogo Vialidad 2023, p.409"),
        ("Puerto Montt-Pargua", 1023.573, 1079.027, RED, 409, "No incluye variante Pargua de kilometraje propio"),
    ]
    d = pd.DataFrame(filas, columns=["contrato", "km_inicio", "km_fin", "fuente", "pagina_pdf", "criterio"])
    d["margen_km"] = 1.0
    d["alcance"] = "Asociación de contexto por contrato, no flujo homogéneo acreditado por tramo"
    return d


def asignar_contratos(tramos, limites=None, tramo_km=5):
    limites = limites_documentados() if limites is None else limites
    salida = pd.DataFrame({"tramo": np.asarray(tramos, int), "contrato": ""})
    for r in limites.itertuples():
        mask = salida.tramo.ge(r.km_inicio + r.margen_km) & (salida.tramo + tramo_km).le(r.km_fin - r.margen_km)
        if salida.loc[mask, "contrato"].ne("").any():
            raise ValueError("Intervalos de contratos superpuestos")
        salida.loc[mask, "contrato"] = r.contrato
    salida["tiene_contrato"] = salida.contrato.ne("")
    return salida


def serie_flujo(carpeta=Path("data/fuentes/dgc")):
    # 2018–2019 permiten rezagar desde el inicio del período 2020; no se inventan.
    versiones = pd.concat([extraer(Path(carpeta) / f"anexo_{v}.xls", v, u, anio_minimo=2018)
                           for v, u in FUENTES.items()], ignore_index=True)
    claves = ["contrato", "anio", "trimestre"]
    if versiones.duplicated(["version_anexo"] + claves).any():
        raise ValueError("Contrato/período duplicado dentro de un anexo")
    d = versiones.sort_values("version_anexo").drop_duplicates(claves, keep="last").copy()
    d["periodo"] = pd.PeriodIndex.from_fields(year=d.anio, quarter=d.trimestre, freq="Q")
    d["puntos_implicitos_crudos"] = d.transacciones_trimestre / (3 * d.pasadas_promedio_por_punto_mes)
    d["puntos_implicitos"] = normalizar_puntos(d.puntos_implicitos_crudos)
    if not np.isfinite(d[["proxy_pasadas_por_punto_dia", "puntos_implicitos"]]).all().all():
        raise ValueError("Flujo no finito")
    if (d[["proxy_pasadas_por_punto_dia", "puntos_implicitos"]] <= 0).any().any():
        raise ValueError("Flujo/puntos no positivos")
    return d.sort_values(claves).reset_index(drop=True)


def flujo_rezagado(asignacion, periodos, serie, rezago=2):
    """Una fila por tramo/período objetivo, unión exacta al trimestre objetivo−2.

    Nunca usa el total del trimestre que se intenta predecir. Dos trimestres de
    rezago dejan al menos un trimestre completo desde el cierre de medición.
    Es una regla retrospectiva, no prueba de fecha histórica de publicación.
    """
    if rezago < 1:
        raise ValueError("Se requiere un rezago positivo")
    periodos = pd.PeriodIndex(periodos, freq="Q")
    base = pd.MultiIndex.from_product([asignacion.tramo, periodos], names=["tramo", "periodo_objetivo"]).to_frame(index=False)
    base = base.merge(asignacion[["tramo", "contrato"]], on="tramo", validate="many_to_one")
    base["periodo_medicion"] = base.periodo_objetivo - rezago
    columnas = ["contrato", "periodo", "proxy_pasadas_por_punto_dia", "puntos_implicitos", "version_anexo",
                "fuente", "celda_promedio", "celda_total"]
    columnas += [n for n in ["puntos_implicitos_crudos"] if n in serie]
    base = base.merge(serie[columnas].rename(columns={"periodo": "periodo_medicion"}),
                      on=["contrato", "periodo_medicion"], how="left", validate="many_to_one")
    base["fin_medicion"] = base.periodo_medicion.dt.end_time.dt.normalize()
    base["inicio_objetivo"] = base.periodo_objetivo.dt.start_time
    base["dias_desde_cierre"] = (base.inicio_objetivo - base.fin_medicion).dt.days
    base["flujo_disponible"] = base.proxy_pasadas_por_punto_dia.notna()
    base["disponibilidad_publicacion_acreditada"] = False
    if not base.fin_medicion.lt(base.inicio_objetivo).all():
        raise ValueError("Flujo contemporáneo o futuro en el predictor")
    return base
