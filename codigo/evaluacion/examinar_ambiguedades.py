"""Último diagnóstico de ubicación 2025: texto publicado y escenarios numéricos.

No asigna rutas/km definitivos ni prepara una grilla con falsos ceros. Las pruebas
de redondeo son post hoc y no sustituyen la comprobación congelada anterior.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd
from descargar_direcciones_conaset import cargar


def normalizar(valor):
    if pd.isna(valor):
        return ""
    return " ".join("".join(c for c in unicodedata.normalize("NFD", str(valor).upper())
                              if unicodedata.category(c) != "Mn").split())


PATRON = re.compile(r"^RUTA 5 SUR\s+(\d+(?:[,.]\d+)?)\s*,\s*(.+)$")


def examinar_direccion(direccion, comuna):
    """Extrae número explícito sin convertir numeración de dirección en km."""
    texto = normalizar(direccion)
    if "RUTA 5 SUR" not in texto:
        return {"estado_texto": "sin_mencion_literal", "numero_textual": np.nan}
    if any(t in texto for t in ("CALETERA", "LATERAL", "VIA DE SERVICIO")):
        return {"estado_texto": "caletera_o_servicio", "numero_textual": np.nan}
    if "&" in texto:
        return {"estado_texto": "interseccion", "numero_textual": np.nan}
    m = PATRON.fullmatch(texto)
    if not m:
        return {"estado_texto": "mencion_sin_numero_interpretable", "numero_textual": np.nan}
    if normalizar(m[2]) != normalizar(comuna):
        return {"estado_texto": "comuna_no_coincide", "numero_textual": np.nan}
    return {"estado_texto": "referencia_con_numero_sin_unidad_acreditada",
            "numero_textual": float(m[1].replace(",", "."))}


def escenario_bordes(d, tolerancia_m):
    """Solo diagnostica casos antes rechazados por borde; no modifica el original."""
    out = d.copy()
    km = pd.to_numeric(out.km_estimado, errors="coerce")
    borde = (km / 5).round() * 5
    recuperado = out.estado.eq("borde_tramo") & (borde - km).abs().mul(1000).le(tolerancia_m)
    out.loc[recuperado, "km_estimado"] = borde.loc[recuperado]
    out.loc[recuperado, "estado"] = "candidato_asignable"
    return out, recuperado


def resumir_escenario(d, tolerancia):
    out, cambiados = escenario_bordes(d, tolerancia)
    p = out.etiqueta.eq("ruta5sur")
    n = out.etiqueta.eq("otra_via")
    asignado = out.estado.eq("candidato_asignable")
    tp, fp = int((asignado & p).sum()), int((asignado & n).sum())
    return {"tolerancia_numerica_m": tolerancia, "bordes_reclasificados_total": int(cambiados.sum()),
            "bordes_positivos_reclasificados": int((cambiados & p).sum()),
            "tp_exploratorios": tp, "fp_exploratorios": fp,
            "sensibilidad_exploratoria": tp / p.sum(), "precision_solo_etiquetados": tp / (tp + fp),
            "tramos_correctos_entre_tp": int((asignado & p & (out.km_estimado // 5).eq(out["Ubicación"] // 5)).sum()),
            "asignables_desconocidos": int((asignado & ~p & ~n).sum()),
            "uso": "Diagnóstico post hoc; no método aprobado para 2025"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fuente", type=Path, required=True)
    p.add_argument("--salida", type=Path, default=Path("resultados/cierre_ubicacion_2025"))
    p.add_argument("--derivados", type=Path, default=Path("data/fuentes/conaset/diagnostico_textual_20261114"))
    p.add_argument("--catalogo", type=Path, default=Path("data/fuentes/conaset/fuentes_adicionales_20261114"))
    a = p.parse_args()
    d, m = cargar(a.fuente)
    referencia_eda = Path("data/fuentes/conaset/eda_2025_20261114_completa/manifiesto.json")
    if json.loads(referencia_eda.read_text())["editingInfo"] != m["editingInfo"]:
        raise ValueError("El complemento corresponde a otra edición: no mezclarlo con el diagnóstico previo")
    texto = pd.DataFrame([examinar_direccion(r["Dirección"], r["COMUNA"]) for r in d.to_dict("records")])
    d = pd.concat([d.reset_index(drop=True), texto], axis=1)
    a.salida.mkdir(parents=True, exist_ok=True)
    a.derivados.mkdir(parents=True, exist_ok=True)
    controles = []
    for anio, g in d.loc[d["AÑO"].isin([2023, 2024])].groupby("AÑO"):
        parse = g.numero_textual.notna()
        positivo = g.Ruta.eq("RUTA 5 SUR")
        conocido_otro = g.Ruta.fillna("").str.strip().ne("") & ~positivo
        delta = (g.numero_textual - g["Ubicación"]).abs()
        controles.append({"anio": anio, "registros": len(g), "positivos_registrados": int(positivo.sum()),
                          "positivos_con_numero_textual": int((positivo & parse).sum()),
                          "otras_rutas_etiquetadas_con_patron": int((conocido_otro & parse).sum()),
                          "sin_ruta_etiquetada_con_patron": int((~positivo & ~conocido_otro & parse).sum()),
                          "positivos_con_diferencia_numero_km": int((positivo & parse & delta.gt(1e-6)).sum()),
                          "positivos_con_tramo_distinto_sin_redondear": int((positivo & parse &
                              (g.numero_textual // 5).ne(g["Ubicación"] // 5)).sum())})
    nuevo = d.loc[d["AÑO"].eq(2025)].copy()
    if (not nuevo.Ruta.fillna("").str.strip().eq("").all() or not nuevo["Ubicación"].fillna(0).eq(0).all()):
        raise ValueError("La fuente 2025 ya contiene ruta/km; hay que revisar la decisión con esa información nueva")
    nuevo["numero_coincide_campo_Numero"] = np.isclose(nuevo.numero_textual, nuevo["Número"], rtol=0, atol=1e-6)
    nuevo["fuera_dominio_si_fuera_km"] = nuevo.numero_textual.notna() & ~nuevo.numero_textual.between(0, 1275, inclusive="neither")
    # 2020–2024 sirve para caracterizar representación, no como prueba ciega nueva.
    h = pd.read_csv("data/siniestros/ruta5_2020_2024.csv.gz")
    ht = pd.DataFrame([examinar_direccion(r["Dirección"], r["COMUNA"]) for r in h.to_dict("records")])
    historico = []
    for anio in sorted(h["AÑO"].unique()):
        ix = h["AÑO"].eq(anio) & h.Ruta.eq("RUTA 5 SUR")
        n = ht.loc[ix, "numero_textual"]
        k = h.loc[ix, "Ubicación"]
        historico.append({"anio": anio, "ruta5sur": int(ix.sum()), "con_patron_numerico": int(n.notna().sum()),
                          "numero_diferente_km": int((n - k).abs().gt(1e-6).sum()),
                          "numero_mayor_1275": int(n.gt(1275).sum()),
                          "tramo_distinto_sin_correccion": int((n // 5).ne(k // 5).sum())})
    previos_path = Path("data/fuentes/mop/derivados_asignacion_20261114/candidatos_2024.csv.gz")
    previos = pd.read_csv(previos_path)
    escenarios = pd.DataFrame([resumir_escenario(previos, t) for t in (.001, .01, .1, 1)])
    # QA geométrica adicional, solo de referencias explícitas; no se asigna el resto.
    from descargar_eje_mop import cargar_geometria
    from ubicacion_vial import IndiceVial
    carpeta_mop = Path("data/fuentes/mop/asignacion_vial_alternativa_20261114")
    protocolo_mop = Path("config/protocolo_asignacion_vial_alternativa.json")
    fs, mm = cargar_geometria(carpeta_mop, protocolo_mop)
    indice = IndiceVial(fs)
    g = nuevo.loc[nuevo.numero_textual.notna()].copy()
    cn = indice.candidatos(g.longitud, g.Latitud, 200)
    g["km_mop_diagnostico"] = [c["km_estimado"] for c in cn]
    g["distancia_mop_m"] = [c["distancia_ruta5_m"] for c in cn]
    g["diferencia_numero_medida_km"] = (g.numero_textual - g.km_mop_diagnostico).abs()
    geografia = []
    v = previos.loc[previos.etiqueta.eq("ruta5sur")]
    for anio, dist, error, total in [
        (2024, v.distancia_ruta5_m, (v.km_estimado - v["Ubicación"]).abs(), len(v)),
        (2025, g.distancia_mop_m, g.diferencia_numero_medida_km, len(g))]:
        finitas = dist.replace([np.inf, -np.inf], np.nan)
        geografia.append({"anio": anio, "referencias": total, "con_candidato_m_finita": int(error.notna().sum()),
                          "distancia_mediana_m": finitas.median(), "distancia_p90_m": finitas.quantile(.9),
                          "error_km_mediano": error.median(), "error_km_p90": error.quantile(.9),
                          "diferencia_numero_km_mayor_01": int(error.gt(.1).sum()),
                          "nota": "2024: km registrado; 2025: número de dirección de unidad no acreditada"})
    tablas = {"control_nacional": pd.DataFrame(controles), "control_historico": pd.DataFrame(historico),
              "estados_texto_2025": nuevo.groupby("estado_texto").size().rename("registros").reset_index(),
              "escenarios_bordes": escenarios, "comparacion_geografica": pd.DataFrame(geografia),
              "perfil_referencias_2025": pd.DataFrame([{
                  "referencias_con_numero": len(g), "numero_coincide_campo_Numero": int(g.numero_coincide_campo_Numero.sum()),
                  "fuera_dominio_si_fuera_km": int(g.fuera_dominio_si_fuera_km.sum()),
                  "numeros_entre_0_y_1275": int(g.numero_textual.between(0, 1275, inclusive="neither").sum()),
                  "con_candidato_m_finita": int(g.km_mop_diagnostico.notna().sum())}])}
    adicionales = a.catalogo
    catalogo = json.loads((adicionales / "resumen.json").read_text())
    otras_fuentes = []
    for servicio in catalogo:
        for capa in servicio.get("capas", []):
            rango = capa.get("rango")
            rango = rango[0] if isinstance(rango, list) and rango else {}
            otras_fuentes.append({"servicio": servicio["servicio"], "capa": capa["capa"],
                                  "url": m["fuente"].split("/Base_SINIESTROS_")[0] + "/" + servicio["servicio"] + "/FeatureServer/" + str(capa["capa"]),
                                  "min_anio": rango.get("min_anio"), "max_anio": rango.get("max_anio"),
                                  "campos": ";".join(capa["campos"])})
    tablas["fuentes_adicionales"] = pd.DataFrame(otras_fuentes)
    direcciones_normalizadas = nuevo["Dirección"].map(normalizar)
    tablas["alias_sin_mencion_literal_2025"] = pd.DataFrame([
        {"referencia": alias, "registros": int((direcciones_normalizadas.str.contains(alias, regex=False) &
            ~direcciones_normalizadas.str.contains("RUTA 5 SUR", regex=False)).sum()),
         "nota": "Referencias a revisar; no acreditan pertenencia a Ruta 5 Sur. Categorías no excluyentes."}
        for alias in ["PANAMERICANA", "PANAMERICANA SUR", "AUTOPISTA CENTRAL", "RUTA TRAVESIA"]])
    for nombre, t in tablas.items():
        t.to_csv(a.salida / (nombre + ".csv"), index=False)
    nuevo.to_csv(a.derivados / "referencias_textuales_2025.csv.gz", index=False)
    g.to_csv(a.derivados / "qa_referencias_textuales_2025.csv.gz", index=False)
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/siniestros-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    ax[0].plot(escenarios.tolerancia_numerica_m, escenarios.sensibilidad_exploratoria, "o-")
    ax[0].set(xscale="log", xlabel="Tolerancia numérica al borde (m)", ylabel="Sensibilidad en positivos 2024",
              title="Escenarios post hoc; no validación nueva", ylim=(0, 1))
    ax[1].bar(["2024 registrado", "2025 texto"], [r["distancia_mediana_m"] for r in geografia])
    ax[1].set(yscale="log", ylabel="Distancia mediana al eje MOP (m)", title="La concordancia geométrica cambia")
    fig.suptitle("Diagnóstico adicional: no se integra 2025")
    fig.savefig(a.salida / "diagnostico.png", dpi=160)
    plt.close(fig)
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    auditoria = {"fuente": m["fuente"], "consulta_utc": m["consulta_utc"], "anios": m["anios"],
                 "manifiesto_direcciones_sha256": sha(a.fuente / "manifiesto.json"),
                 "manifiesto_mop_sha256": sha(carpeta_mop / "manifiesto.json"),
                 "base_historica_sha256": sha("data/siniestros/ruta5_2020_2024.csv.gz"),
                 "candidatos_previos_sha256": sha(previos_path),
                 "edicion_coincide_eda_previo": True,
                 "manifiesto_eda_previo_sha256": sha(referencia_eda),
                 "consultas_adicionales_originales_sha256": {f.name: sha(f) for f in sorted(adicionales.glob("*.json"))},
                 "codigo_sha256": {f: sha(f) for f in ["codigo/datos/descargar_direcciones_conaset.py", "codigo/evaluacion/examinar_ambiguedades.py"]},
                 "decision_entrega_actual": "Conservar 2020–2024; ampliación 2025 no acreditada",
                 "motivos": ["Número textual no equivale universalmente a km: diferencias y unidades en el histórico",
                             "Intersecciones/caleteras y registros sin ruta de referencia no resuelven la pertenencia vial",
                             "Cambió la concordancia de coordenadas; no se acreditó el proceso de geocodificación 2025",
                             "Mejorar el redondeo post hoc no valida rutas/km faltantes ni la cohorte completa"],
                 "integrado_2025": False, "modelos_alterados": False,
                 "originales": [{k: f[k] for k in ["archivo", "sha256_respuesta", "registros"]} for f in m["archivos"]],
                 "derivados_locales_sha256": {f.name: sha(f) for f in [a.derivados / "referencias_textuales_2025.csv.gz", a.derivados / "qa_referencias_textuales_2025.csv.gz"]}}
    (a.salida / "auditoria.json").write_text(json.dumps(auditoria, ensure_ascii=False, indent=2) + "\n")
    print(tablas["estados_texto_2025"].to_string(index=False))
    print(escenarios.to_string(index=False))
    print("Decisión:", auditoria["decision_entrega_actual"])


if __name__ == "__main__":
    main()
