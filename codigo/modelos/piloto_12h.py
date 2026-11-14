"""Piloto trazable de 12 h con la candidata vigente y pronósticos disponibles.

Sin argumentos emite una corrida nueva. --reproducir DIR verifica una anterior
sin descargar ni sobrescribir datos. No modifica modelos ni resultados históricos.
"""
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd
from modelo import POS_FERIADO
from modelo_piloto import cargar, predecir
from insumos_piloto import (sha256, utc, ventana, capturar, verificar_corte,
                           alinear_pronostico, calendario)

CODIGO = ["codigo/modelos/piloto_12h.py", "codigo/modelos/modelo_piloto.py", "codigo/datos/insumos_piloto.py"]


def referencia(config):
    if sha256(config["referencia"]) != config["sha256_referencia"]:
        raise ValueError("La referencia no corresponde a la candidata")
    r = pd.read_csv(config["referencia"])
    if len(r) != 255 or not np.array_equal(r.tramo.to_numpy(), np.arange(0, 1275, 5)):
        raise ValueError("Dominio o orden de tramos inesperado")
    if not np.isfinite(r[["lat", "lon"]]).all().all() or not r.ultimo_anio_referencia.eq(2021).all():
        raise ValueError("Referencia espacial inválida o construida con años posteriores")
    return r


def celdas_referencia(r, paso=.25):
    por_tramo = [(float(round(lat / paso) * paso), float(round(lon / paso) * paso))
                 for lat, lon in r[["lat", "lon"]].itertuples(index=False, name=None)]
    celdas = sorted(set(por_tramo))
    return celdas, np.array([celdas.index(c) for c in por_tramo])


def atributos_piloto(tiempos, lluvia_mm, posiciones, config):
    t = tiempos.tz_convert(config["zona"])
    p = np.asarray(lluvia_mm, dtype=float)
    if p.ndim != 2 or p.shape[1] != len(t) or len(posiciones) != len(t):
        raise ValueError("Dimensiones del horizonte incompatibles")
    if not np.isfinite(p).all() or (p < 0).any():
        raise ValueError("Lluvia faltante o negativa")
    if any(pos not in POS_FERIADO for pos in posiciones):
        raise ValueError("Posición de calendario desconocida")
    n, h = p.shape
    f = np.full((n * h, 9), np.nan)
    f[:, 0] = np.repeat(np.arange(n), h)
    f[:, 1] = np.tile(t.hour, n)
    f[:, 2] = np.tile(t.dayofweek, n)
    f[:, 3] = np.tile(t.month - 1, n)
    f[:, 4] = np.tile([POS_FERIADO.index(pos) for pos in posiciones], n)
    f[:, 5] = np.digitize(p, config["cortes_precipitacion_mm"]).ravel()
    f[:, 6] = np.tile(t.year - config["ajuste_desde"], n)
    # 7/8 permanecen faltantes: la candidata no usa flujo, no se inventan offsets.
    return f


def construir(config, modelo, r, tiempos, p, posiciones):
    f = atributos_piloto(tiempos, p, posiciones, config)
    n, h = p.shape
    mu = predecir(modelo, f).reshape(n, h)
    cal = mu * modelo["factor_recalibracion_referencia"]
    plan = r[["tramo", "lat", "lon"]].copy()
    plan["km_fin"] = plan.tramo + 5
    plan["esperados_12h"] = mu.sum(axis=1)
    plan["esperados_12h_recalibrados_referencia"] = cal.sum(axis=1)
    plan = plan.sort_values(["esperados_12h", "tramo"], ascending=[False, True], kind="stable")
    plan["prioridad"] = np.arange(1, len(plan) + 1)
    max_tramos = int(np.floor(len(plan) * config["presupuesto_maximo"] + 1e-10))
    plan["seleccionado_12h"] = plan.prioridad.le(max_tramos)
    seleccion = set(plan.loc[plan.seleccionado_12h, "tramo"])
    local = tiempos.tz_convert(config["zona"])
    largo = pd.DataFrame({"tramo": np.repeat(r.tramo.to_numpy(), h),
                          "inicio_utc": np.tile([v.isoformat() for v in tiempos], n),
                          "fin_utc": np.tile([(v + pd.Timedelta(hours=1)).isoformat() for v in tiempos], n),
                          "inicio_local": np.tile([v.isoformat() for v in local], n),
                          "precipitacion_mm_hora_previa": p.ravel(), "categoria_lluvia": f[:, 5].astype(int),
                          "posicion_calendario": np.tile(posiciones, n), "tendencia_anio_menos_2020": f[:, 6].astype(int),
                          "esperados": mu.ravel(), "esperados_recalibrados_referencia": cal.ravel()})
    largo["seleccionado_12h"] = largo.tramo.isin(seleccion)
    horas = largo.groupby(["inicio_utc", "inicio_local"], sort=True).agg(
        esperados=("esperados", "sum"),
        esperados_recalibrados_referencia=("esperados_recalibrados_referencia", "sum")).reset_index()
    return largo, plan.reset_index(drop=True), horas


def escribir_reporte(carpeta, auditoria, plan, horas):
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/siniestros-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    top = plan.loc[plan.seleccionado_12h].copy()
    fig, ax = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    etiquetas = [pd.Timestamp(t).strftime("%d/%m %H:%M") for t in horas.inicio_local]
    ax[0].plot(range(len(horas)), horas.esperados, "o-", label="Candidata original")
    ax[0].plot(range(len(horas)), horas.esperados_recalibrados_referencia, "o--", label="Variante recalibrada de referencia")
    ax[0].set(xticks=range(0, len(horas), 2), xticklabels=etiquetas[::2], ylabel="Siniestros esperados en toda la ruta",
              xlabel="Inicio de hora local", title="Próximas 12 horas reales")
    ax[0].tick_params(axis="x", rotation=30)
    ax[0].legend(fontsize=8)
    ax[1].barh([f"{int(x)}–{int(x)+5}" for x in top.tramo][::-1], top.esperados_12h.to_numpy()[::-1])
    ax[1].set(xlabel="Siniestros esperados en 12 h", ylabel="Tramo (km)", title="Prioridades fijas para toda la ventana")
    fig.suptitle("Piloto del proyecto · pronóstico sin evaluación operativa todavía")
    fig.savefig(carpeta / "pronostico.png", dpi=160)
    plt.close(fig)
    a = auditoria
    lineas = ["# Piloto de 12 horas — Ruta 5 Sur", "", "Estado: piloto en modo sombra; observaciones y evaluación pendientes.", "",
              f"Emisión UTC: {a['emision_utc']}. Ventana: [{a['inicio_utc']}, {a['fin_utc']}).", "",
              f"Conteo esperado principal: **{a['esperados_total']:.3f}**. Variante recalibrada de referencia: **{a['esperados_total_recalibrados_referencia']:.3f}**.", "",
              f"Plan fijo: {a['tramos_seleccionados']} tramos, {a['presupuesto_real']:.2%} de los tramos-hora disponibles. Desempate por km ascendente.", "",
              "Son conteos esperados, no siniestros confirmados ni riesgo individual. El nivel recalibrado no es una nueva selección de modelo.", "",
              "Modelo ajustado con 2020–2024; tendencia aplicada al año actual, fuera del período de ajuste. Pronóstico ECMWF/Open-Meteo en lugar de reanálisis ERA5: desempeño operativo sin acreditar.", "",
              "La posición en el mapa corresponde a una referencia histórica aproximada; no define puntos físicos de despliegue.", "",
              "| Prioridad | Km inicial | Km final | Esperados 12 h |", "|---|---|---|---|"]
    lineas += [f"| {v.prioridad} | {v.tramo} | {v.km_fin} | {v.esperados_12h:.4f} |" for v in top.itertuples()]
    lineas += ["", "![Pronóstico](pronostico.png)", "", "Pronóstico: [Open-Meteo](https://open-meteo.com/) / ECMWF. Datos meteorológicos CC BY 4.0.",
               "", "Las predicciones quedan congeladas. Para evaluarlas se requieren eventos observados con ubicación, instante UTC y cobertura completa acreditada.", ""]
    (carpeta / "resumen.md").write_text("\n".join(lineas))
    tabla = plan[["prioridad", "tramo", "km_fin", "esperados_12h", "seleccionado_12h"]].to_html(index=False, float_format=lambda x: f"{x:.4f}", classes="tabla")
    contenido = f"""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Piloto de 12 horas · Ruta 5 Sur</title><style>body{{font:16px system-ui;max-width:1150px;margin:32px auto;padding:0 20px;color:#183245}}h1{{font-size:28px}}.estado{{background:#fff2cb;padding:12px;border-radius:8px}}.datos{{display:flex;gap:30px;flex-wrap:wrap}}strong{{font-size:26px}}img{{width:100%;margin:20px 0}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:right;padding:8px;border-bottom:1px solid #ddd}}th{{background:#eaf0f4}}small{{color:#526778}}input{{padding:10px;margin:15px 0}}footer{{margin:25px 0}}</style>
<h1>Predicción dinámica de siniestros en carreteras chilenas</h1><h2>Piloto de 12 horas · Ruta 5 Sur</h2>
<p class="estado">Piloto en modo sombra · evaluación con siniestros observados pendiente</p>
<p>Emisión: {html.escape(a['emision_local'])}<br>Ventana: {html.escape(a['inicio_local'])} → {html.escape(a['fin_local'])}</p>
<div class="datos"><p>Esperados, candidata original<br><strong>{a['esperados_total']:.3f}</strong></p><p>Variante recalibrada de referencia<br><strong>{a['esperados_total_recalibrados_referencia']:.3f}</strong></p><p>Plan fijo<br><strong>{a['tramos_seleccionados']} tramos</strong><br>{a['presupuesto_real']:.2%} del presupuesto tramo-hora</p></div>
<p>Conteos esperados; los siniestros reales aún no se conocen. El modelo usa 2020–2024 y extrapola su tendencia al año actual. Su comportamiento con pronósticos emitidos está pendiente de evaluación.</p>
<img src="pronostico.png" alt="Conteos horarios esperados y prioridades por tramo">
<h2>Prioridades por tramo</h2><small>La selección permanece fija durante las doce horas. Las coordenadas históricas son aproximadas; no definen puntos de despliegue.</small><br><input id="buscar" placeholder="Filtrar por kilómetro o prioridad" aria-label="Filtrar tabla">{tabla}
<footer>Fuente meteorológica: <a href="https://open-meteo.com/">Open-Meteo / ECMWF</a>, CC BY 4.0. La captura y el modelo quedan identificados en auditoria.json.</footer>
<script>document.getElementById('buscar').addEventListener('input',e=>{{for(const r of document.querySelectorAll('tbody tr'))r.hidden=!r.textContent.toLowerCase().includes(e.target.value.toLowerCase())}});</script></html>"""
    (carpeta / "reporte.html").write_text(contenido)


def calcular_desde_captura(config, modelo, ref, carpeta, capturas, emision, calendario_copia):
    t = ventana(emision, config["horizonte_horas"])
    verificar_corte(capturas["pronosticos"] + capturas["feriados"], emision, config["antiguedad_max_captura_minutos"])
    celdas, ix = celdas_referencia(ref, config["grilla_grados"])
    p = alinear_pronostico(carpeta, capturas["pronosticos"], celdas, t)
    pos = calendario(carpeta, capturas["feriados"], calendario_copia, t, config)
    return t, construir(config, modelo, ref, t, p[ix], pos)


def reproducir(carpeta):
    a = json.loads((carpeta / "auditoria.json").read_text())
    for f, h in a["hashes_codigo"].items():
        if sha256(f) != h:
            raise ValueError("Código distinto de la emisión; recuperar la versión indicada")
    for nombre, digest in a["salidas_sha256"].items():
        if sha256(carpeta / nombre) != digest:
            raise ValueError("Una salida congelada fue alterada")
    c = a["config"]
    modelo, ref = cargar(c), referencia(c)
    fuente = Path(a["carpeta_capturas"])
    cal = fuente / "calendario.csv"
    if sha256(cal) != a["calendario_sha256"]:
        raise ValueError("Calendario capturado alterado")
    _, tablas = calcular_desde_captura(c, modelo, ref, fuente, a["capturas"], a["emision_utc"], cal)
    for nombre, tabla in zip(["predicciones.csv", "plan_tramos.csv", "por_hora.csv"], tablas):
        pd.testing.assert_frame_equal(pd.read_csv(carpeta / nombre), tabla, check_dtype=False, rtol=1e-12, atol=1e-14)
    print("Reproducción CORRECTA: doce horas, tablas idénticas; sin red ni sobrescritura.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=Path("config/piloto_12h.json"))
    p.add_argument("--salida", type=Path, default=Path("resultados/piloto"))
    p.add_argument("--fuentes", type=Path, default=Path("data/fuentes/piloto"))
    p.add_argument("--reproducir", type=Path)
    a = p.parse_args()
    if a.reproducir:
        reproducir(a.reproducir)
        return
    c = json.loads(a.config.read_text())
    modelo, ref = cargar(c), referencia(c)
    captura_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    fuente = a.fuentes / captura_id
    celdas, _ = celdas_referencia(ref, c["grilla_grados"])
    capturas = capturar(fuente, celdas, c)
    (fuente / "calendario.csv").write_bytes(Path(c["calendario"]).read_bytes())
    emision = pd.Timestamp.now(tz="UTC")
    t, (largo, plan, horas) = calcular_desde_captura(c, modelo, ref, fuente, capturas, emision, fuente / "calendario.csv")
    salida = a.salida / emision.strftime("%Y%m%dT%H%M%S%fZ")
    salida.mkdir(parents=True, exist_ok=False)
    for nombre, tabla in [("predicciones.csv", largo), ("plan_tramos.csv", plan), ("por_hora.csv", horas)]:
        tabla.to_csv(salida / nombre, index=False)
    pd.DataFrame(columns=["id", "instante_utc", "tramo", "fuente"]).to_csv(salida / "plantilla_observaciones.csv", index=False)
    ultimo = t[-1] + pd.Timedelta(hours=1)
    auditoria = {"estado": "Emitido; evaluación observada pendiente", "config": c,
                 "config_sha256": sha256(a.config), "emision_utc": emision.isoformat(),
                 "emision_local": emision.tz_convert(c["zona"]).isoformat(),
                 "inicio_utc": t[0].isoformat(), "fin_utc": ultimo.isoformat(),
                 "inicio_local": t[0].tz_convert(c["zona"]).isoformat(), "fin_local": ultimo.tz_convert(c["zona"]).isoformat(),
                 "carpeta_capturas": str(fuente), "capturas": capturas,
                 "calendario_sha256": sha256(fuente / "calendario.csv"),
                 "esperados_total": float(largo.esperados.sum()),
                 "esperados_total_recalibrados_referencia": float(largo.esperados_recalibrados_referencia.sum()),
                 "tramos": len(ref), "horas_reales": len(t), "celdas_meteorologicas": len(celdas),
                 "tramos_seleccionados": int(plan.seleccionado_12h.sum()),
                 "presupuesto_real": float(plan.seleccionado_12h.mean()),
                 "tendencia_fuera_periodo_ajuste": bool(t.tz_convert(c["zona"]).year.max() > c["ajuste_hasta"]),
                 "inicializacion_modelo_meteorologico_utc": None,
                 "limite_meteorologia": "La API no acredita aquí inicialización; se acredita captura antes de emitir, no fecha por generationtime_ms.",
                 "evaluacion_futura_modelo": False, "observaciones_reales_disponibles": False,
                 "hashes_codigo": {f: sha256(f) for f in CODIGO},
                 "versiones": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
                 "commit_entrada": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                 "checkout_con_cambios": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())}
    escribir_reporte(salida, auditoria, plan, horas)
    auditoria["salidas_sha256"] = {f.name: sha256(f) for f in sorted(salida.iterdir())}
    (salida / "auditoria.json").write_text(json.dumps(auditoria, ensure_ascii=False, indent=2) + "\n")
    print(f"Piloto emitido -> {salida}")
    print(f"Ventana: {auditoria['inicio_local']} a {auditoria['fin_local']}")
    print(f"Esperados originales: {auditoria['esperados_total']:.4f}; recalibrados de referencia: {auditoria['esperados_total_recalibrados_referencia']:.4f}")
    print("Evaluación observada: pendiente. Ningún modelo fue reentrenado.")


if __name__ == "__main__":
    main()
