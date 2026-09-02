#!/usr/bin/env python3
"""
Genera la página de riesgo de la Ruta 5 Sur: una sola página autocontenida, sin
servidor ni base de datos. Pensada para correr por cron cada hora.

    0 * * * * cd /ruta/al/repo && python3 generar_pagina.py

Muestra conteos ESPERADOS y riesgo relativo, nunca "probabilidad de accidente":
con una tasa base de 0,13 % por tramo-hora, un porcentaje por tramo no le sirve
a nadie.
"""
import collections, csv, datetime, gzip, html, json

import numpy as np

from riesgo import calcular

BANDA = 25          # km por fila de la tira
POS_FERIADO = {"inicio": "salida a feriado", "final": "regreso de feriado",
               "intermedio": "feriado"}
MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def regiones_por_banda():
    reg = collections.defaultdict(collections.Counter)
    with gzip.open("ruta5_2020_2024.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Ruta"] != "RUTA 5 SUR":
                continue
            try:
                km = float(r["Ubicación"])
            except (TypeError, ValueError):
                continue
            if 0 < km < 2200:
                reg[int(km // BANDA) * BANDA][r["REGION"]] += 1
    corto = {"Metropolitana de Santiago": "R. Metropolitana",
             "Libertador General Bernardo O'Higgins": "O'Higgins"}
    return {b: corto.get(c.most_common(1)[0][0], c.most_common(1)[0][0])
            for b, c in reg.items()}


def construir():
    modelo = json.load(open("modelo_final.json"))
    fer = json.load(open("feriados.json"))
    r = calcular(modelo, fer, horas=12)

    mu = np.array(r["mu"])
    lluvia = np.array(r["lluvia"])
    precip = np.array(r["precip"])
    tramos = np.array(r["tramos"])
    coef = modelo["coef"]

    # colapsar tramos de 5 km en bandas de 25 km
    bandas = sorted({int(t // BANDA) * BANDA for t in tramos})
    ix = {b: [i for i, t in enumerate(tramos) if int(t // BANDA) * BANDA == b]
          for b in bandas}
    M = np.array([mu[ix[b]].sum(0) for b in bandas])
    LL = np.array([precip[ix[b]].max(0) for b in bandas])
    regs = regiones_por_banda()

    # el basal de cada banda: mismo modelo, sin lluvia y en hora/día promedio
    base_tr = np.exp(np.array(coef["tramo"]) + coef["intercepto"]
                     + np.mean(coef["hora"]) + np.mean(coef["dow"])
                     + np.mean(coef["mes"]) + coef["feriado"][0]
                     + coef["lluvia"][0])
    B = np.array([base_tr[ix[b]].sum() for b in bandas])

    # atribución: qué factor domina en cada tramo-hora del top
    tot = mu.sum(1)
    orden = np.argsort(-tot)[:8]
    top = []
    for i in orden:
        j = int(np.argmax(mu[i]))
        dt = datetime.datetime.fromisoformat(r["horas"][j])
        motivos = []
        if lluvia[i, j] == 2:
            motivos.append(("lluvia", np.exp(coef["lluvia"][2] - coef["lluvia"][0])))
        elif lluvia[i, j] == 1:
            motivos.append(("llovizna", np.exp(coef["lluvia"][1] - coef["lluvia"][0])))
        motivos.append((f"{dt.hour:02d}:00",
                        np.exp(coef["hora"][dt.hour] - np.mean(coef["hora"]))))
        f = r["feriado"][r["horas"][j]]
        if f in POS_FERIADO:
            motivos.append((POS_FERIADO[f],
                            np.exp(coef["feriado"][["no", "inicio", "intermedio",
                                                    "final"].index(f)]
                                   - coef["feriado"][0])))
        # solo los factores que ELEVAN el riesgo; uno de 0,78x no es un "motivo"
        motivos = [(n, v) for n, v in motivos if v > 1.05]
        motivos.sort(key=lambda x: -x[1])
        top.append({
            "km": int(tramos[i]), "region": regs[int(tramos[i] // BANDA) * BANDA],
            # relativo al tramo promedio de esta misma ventana: responde
            # "cuánto peor es este tramo que los demás", que es lo accionable
            "mult": float(tot[i] / (tot.mean())),
            "vs_propio": float(tot[i] / (base_tr[i] * 12)),
            "hora": dt.strftime("%H:%M"),
            "motivos": [(n, float(v)) for n, v in motivos[:2]],
        })

    horas = [datetime.datetime.fromisoformat(t) for t in r["horas"]]
    return {
        "generado": datetime.datetime.now(),
        "horas": horas,
        "bandas": bandas,
        "regiones": [regs[b] for b in bandas],
        "M": M, "B": B, "LL": LL,
        "total": r["total"], "basal": r["basal"],
        "por_hora": M.sum(0), "basal_hora": B.sum(),
        "top": top,
        "feriados": {t: r["feriado"][t] for t in r["horas"]},
        "n_lluvia": int((lluvia.max(1) > 0).sum()), "n_tramos": len(tramos),
    }


# ------------------------------------------------------------------ render

CSS = """
:root{
  --ground:#E9EBE6; --surface:#F6F7F4; --sunk:#DFE2DC;
  --ink:#161A1B; --ink-2:#4A5350; --ink-3:#7C8681;
  --line:#CFD4CC; --accent:#0F5C43; --accent-soft:#DCE7E1;
  --rain:#3D7FA8;
  --q0:#9AA6A0; --q1:#C9942A; --q2:#B33A22;
  --shadow:0 1px 2px rgba(22,26,27,.06),0 8px 24px -16px rgba(22,26,27,.28);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#101315; --surface:#181C1E; --sunk:#0B0E0F;
    --ink:#E8EBE7; --ink-2:#A2ADA8; --ink-3:#6C7772;
    --line:#2A3134; --accent:#4FBF95; --accent-soft:#17302A;
    --rain:#5FA3CC; --q0:#5D6B66; --q1:#D9A63C; --q2:#D0553A;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"]{
  --ground:#101315; --surface:#181C1E; --sunk:#0B0E0F;
  --ink:#E8EBE7; --ink-2:#A2ADA8; --ink-3:#6C7772;
  --line:#2A3134; --accent:#4FBF95; --accent-soft:#17302A;
  --rain:#5FA3CC; --q0:#5D6B66; --q1:#D9A63C; --q2:#D0553A;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.7);
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:"Archivo",system-ui,-apple-system,sans-serif;
  font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1040px;margin:0 auto;padding:40px 24px 72px}
.mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  font-variant-numeric:tabular-nums}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-3);font-weight:600}

header{border-bottom:2px solid var(--ink);padding-bottom:18px;margin-bottom:28px}
h1{font-size:clamp(30px,5vw,44px);font-weight:700;letter-spacing:-.025em;
  margin:6px 0 8px;text-wrap:balance;line-height:1.05}
.sub{color:var(--ink-2);font-size:14px;margin:0}

.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  gap:14px;margin-bottom:34px}
.metric{background:var(--surface);border:1px solid var(--line);border-radius:3px;
  padding:16px 18px;box-shadow:var(--shadow)}
.metric .v{font-size:34px;font-weight:700;letter-spacing:-.02em;line-height:1.05;
  display:block;margin:4px 0 2px}
.metric .n{font-size:12.5px;color:var(--ink-2);line-height:1.4}
.pill{display:inline-block;padding:2px 9px;border-radius:2px;font-size:12px;
  font-weight:600;letter-spacing:.02em}

section{margin-bottom:40px}
h2{font-size:13px;letter-spacing:.13em;text-transform:uppercase;font-weight:600;
  color:var(--ink-2);margin:0 0 4px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.hint{font-size:13px;color:var(--ink-3);margin:10px 0 16px;max-width:64ch}

/* tira kilométrica */
.strip{overflow-x:auto;padding-bottom:4px}
.grid{display:grid;grid-template-columns:148px repeat(12,minmax(30px,1fr));
  gap:2px;min-width:640px}
.grid .hd{font-size:11px;color:var(--ink-3);text-align:center;padding-bottom:6px;
  font-weight:600}
.grid .hd.now{color:var(--accent)}
.rowlab{font-size:11.5px;color:var(--ink-2);display:flex;align-items:center;
  justify-content:flex-end;gap:7px;padding-right:9px;white-space:nowrap;
  border-right:1px solid var(--line)}
.rowlab .rg{color:var(--ink-2);font-size:9.5px;letter-spacing:.05em;
  text-transform:uppercase;font-weight:600}
.rowlab.nueva{border-top:1px solid var(--ink-3)}
.cell{height:15px;border-radius:1px;position:relative}
.cell[data-rain="1"]::after{content:"";position:absolute;inset:auto 0 0 0;height:2px;
  background:var(--rain)}
.legend{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-top:14px;
  font-size:12px;color:var(--ink-2)}
.ramp{display:flex;gap:2px}
.ramp i{width:22px;height:9px;border-radius:1px;display:block}

table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-3);font-weight:600;padding:0 10px 8px 0;border-bottom:1px solid var(--line)}
td{padding:11px 10px 11px 0;border-bottom:1px solid var(--line);vertical-align:baseline}
tr:last-child td{border-bottom:none}
.tag{font-size:11.5px;padding:2px 7px;border-radius:2px;margin-right:5px;
  white-space:nowrap;display:inline-block}
.tag.rain{background:var(--rain);color:#fff}
.tag.other{background:var(--sunk);color:var(--ink-2);border:1px solid var(--line)}

.notes{font-family:"Source Serif 4",Georgia,serif;font-size:15.5px;line-height:1.65;
  color:var(--ink-2);max-width:66ch}
.notes p{margin:0 0 13px}
.notes strong{color:var(--ink);font-weight:600}
.notes code{font-family:"IBM Plex Mono",monospace;font-size:13px;
  background:var(--sunk);padding:1px 5px;border-radius:2px}
footer{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--ink-3)}
a{color:var(--accent)}
@media (prefers-reduced-motion:no-preference){
  .cell{transition:outline-color .12s}
}
.cell:hover{outline:2px solid var(--ink);outline-offset:1px}
"""


def color(v, vmax):
    """Rampa de riesgo: apagado -> ámbar -> señal. Separada del verde de identidad."""
    t = min(v / vmax, 1.0) ** 1.25 if vmax > 0 else 0
    if t < 0.5:
        a, b, u = (0x7E, 0x8C, 0x88), (0xC9, 0x94, 0x2A), t / 0.5
    else:
        a, b, u = (0xC9, 0x94, 0x2A), (0xB3, 0x3A, 0x22), (t - 0.5) / 0.5
    c = [int(a[i] + (b[i] - a[i]) * u) for i in range(3)]
    op = 0.14 + 0.86 * t
    return f"rgba({c[0]},{c[1]},{c[2]},{op:.2f})"


def render(d):
    hs = d["horas"]
    ratio = d["total"] / d["basal"]
    up = ratio >= 1
    vmax = float(np.percentile(d["M"], 99.2))

    dt0 = hs[0]
    fecha = f"{DIAS[dt0.weekday()]} {dt0.day} de {MESES[dt0.month-1]}"
    fer_act = {v for v in d["feriados"].values() if v != "no"}

    cab = "".join(
        f'<div class="hd mono{" now" if i == 0 else ""}">{h.strftime("%H")}</div>'
        for i, h in enumerate(hs))

    prom = float(d["M"].mean())
    filas = []
    for bi, b in enumerate(d["bandas"]):
        celdas = "".join(
            f'<div class="cell" data-rain="{1 if d["LL"][bi][j] >= 0.1 else 0}" '
            f'title="km {b}-{b+BANDA} · {hs[j].strftime("%H:%M")} · '
            f'{d["M"][bi][j]/max(d["B"][bi],1e-9):.1f}x el basal'
            f'{" · lluvia " + format(d["LL"][bi][j], ".1f") + " mm/h" if d["LL"][bi][j] >= 0.1 else ""}" '
            f'style="background:{color(d["M"][bi][j], vmax)}"></div>'
            for j in range(len(hs)))
        cambia = bi == 0 or d["regiones"][bi] != d["regiones"][bi - 1]
        rg = (f'<span class="rg">{html.escape(d["regiones"][bi])}</span>'
              if cambia else '')
        filas.append(
            f'<div class="rowlab{" nueva" if cambia else ""}">{rg}'
            f'<span class="mono">{b}</span></div>{celdas}')

    tt = []
    for t in d["top"]:
        tags = "".join(
            f'<span class="tag {"rain" if n in ("lluvia","llovizna") else "other"}">'
            f'{html.escape(n)} {v:.2f}x</span>' for n, v in t["motivos"])
        tt.append(
            f'<tr><td class="mono"><strong>km {t["km"]}–{t["km"]+5}</strong></td>'
            f'<td style="color:var(--ink-3)">{html.escape(t["region"])}</td>'
            f'<td class="mono"><strong>{t["mult"]:.1f}x</strong></td>'
            f'<td class="mono">{t["hora"]}</td>'
            f'<td>{tags if tags else "<span style=\'color:var(--ink-3)\'>—</span>"}</td></tr>')

    barras = "".join(
        f'<div class="hd mono" style="color:var(--ink-2)">{v:.2f}</div>'
        for v in d["por_hora"])

    pill_bg = "var(--q2)" if ratio >= 1.15 else ("var(--q1)" if up else "var(--accent-soft)")
    pill_fg = "#fff" if ratio >= 1 else "var(--accent)"

    return f"""<title>Riesgo Ruta 5 Sur</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header>
  <div class="eyebrow">Ruta 5 Sur · Santiago – Puerto Montt · próximas 12 horas</div>
  <h1>Riesgo de siniestros</h1>
  <p class="sub mono">{fecha}, {hs[0].strftime('%H:%M')} – {hs[-1].strftime('%H:%M')}
    · generado {d['generado'].strftime('%d-%m-%Y %H:%M')}</p>
</header>

<div class="metrics">
  <div class="metric">
    <div class="eyebrow">Siniestros esperados</div>
    <span class="v mono">{d['total']:.1f}</span>
    <div class="n">en los {d['n_tramos']} tramos de la ruta, próximas 12 h</div>
  </div>
  <div class="metric">
    <div class="eyebrow">Contra un día normal</div>
    <span class="v mono">{ratio:.2f}x</span>
    <div class="n"><span class="pill" style="background:{pill_bg};color:{pill_fg}">
      {'+' if up else ''}{(ratio-1)*100:.0f}%</span>
      basal {d['basal']:.1f} siniestros</div>
  </div>
  <div class="metric">
    <div class="eyebrow">Lluvia pronosticada</div>
    <span class="v mono" style="color:var(--rain)">{d['n_lluvia']}</span>
    <div class="n">de {d['n_tramos']} tramos con precipitación en la ventana
      {'· ' + ', '.join(sorted(fer_act)) if fer_act else ''}</div>
  </div>
</div>

<section>
  <h2>Kilómetro por hora</h2>
  <p class="hint">Cada fila es un tramo de {BANDA} km, de norte (Santiago, km 0) a sur
    (Los Lagos, km {d['bandas'][-1]}). El color es el número de siniestros esperados en
    esa celda: las bandas oscuras son las que menos concentran riesgo, no las que están
    «mejor de lo normal». La línea azul inferior marca las horas con lluvia pronosticada.</p>
  <div class="strip">
    <div class="grid">
      <div></div>{cab}
      {''.join(filas)}
      <div class="rowlab" style="border:none;padding-top:7px">
        <span class="rg">esperados</span></div>
      {barras}
    </div>
  </div>
  <div class="legend">
    <span>menor</span>
    <span class="ramp">{''.join(f'<i style="background:{color(vmax*k/8, vmax)}"></i>' for k in range(1,9))}</span>
    <span>mayor</span>
    <span style="margin-left:8px"><i style="display:inline-block;width:14px;height:3px;
      background:var(--rain);vertical-align:middle"></i> lluvia</span>
  </div>
</section>

<section>
  <h2>Dónde y por qué</h2>
  <p class="hint">Los ocho tramos de 5 km con mayor riesgo acumulado en la ventana, con la
    hora peak y los factores que más pesan en ella.</p>
  <table>
    <thead><tr><th>Tramo</th><th>Región</th><th>vs tramo promedio</th><th>Hora peak</th>
      <th>Factores dominantes</th></tr></thead>
    <tbody>{''.join(tt)}</tbody>
  </table>
</section>

<section>
  <h2>Cómo leer esto</h2>
  <div class="notes">
    <p><strong>Esto no dice dónde habrá un accidente.</strong> La tasa base es de
    <code>0,13 %</code> por tramo-hora: en toda la Ruta 5 Sur se esperan
    <code>3,95</code> siniestros en 12 horas repartidos en 1.275 km. Cualquier sistema que
    prometa señalar el kilómetro y la hora exactos está sobrevendiendo. Lo que sí se puede
    afirmar es cuántos siniestros esperar en la ruta completa y qué tramos concentran el
    riesgo.</p>

    <p><strong>El mapa fijo hace casi todo el trabajo.</strong> En validación temporal
    (entrena 2020–2023, prueba 2024), vigilar el 5 % de las horas-tramo más riesgosas
    cubre el 15,0 % de los siniestros reales usando solo la ubicación, y el 19,2 %
    sumando hora, día, feriado y clima. La capa dinámica aporta un 28 % relativo: es
    real, no es transformadora.</p>

    <p><strong>La lluvia es el factor más fuerte del modelo</strong> (2,12x sobre calzada
    seca), por encima de la hora punta de las 18:00 (1,70x). Y probablemente esté
    subestimada: la precipitación viene del reanálisis ERA5, que promedia sobre celdas de
    25 km y se pierde casi la mitad de las lluvias que registra Carabineros en terreno
    (kappa 0,26). El error de medición atenúa el coeficiente hacia 1.</p>

    <p><strong>Lo que falta.</strong> No hay flujo vehicular horario: el censo del MOP
    entrega un promedio anual por punto, así que el modelo no puede separar «hay más
    autos» de «conducir a esta hora es más peligroso por auto». Los datos son de
    Carabineros y subregistran los siniestros sin lesionados. El campo de ruta solo está
    poblado hasta 2024.</p>
  </div>
</section>

<footer>
  Siniestros: CONASET / Carabineros de Chile, 14.425 registros 2020–2024 en la Ruta 5 Sur.
  Pronóstico: Open-Meteo. Feriados: CONASET.
  Modelo Poisson sobre 11,2 millones de celdas tramo × hora.
</footer>
</div>
"""


if __name__ == "__main__":
    d = construir()
    open("pagina.html", "w").write(render(d))
    print(f"pagina.html generada — {d['total']:.2f} siniestros esperados "
          f"({d['total']/d['basal']:.2f}x el basal)")
