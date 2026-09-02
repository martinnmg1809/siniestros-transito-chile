#!/usr/bin/env python3
"""
Genera index.html: la versión EN VIVO de la página de riesgo.

Diferencia con generar_pagina.py: aquí no se hornea ningún número. Se embeben los
306 coeficientes del modelo y el calendario de feriados (20 KB en total), y la
página pide el pronóstico a Open-Meteo y recalcula el riesgo en el navegador cada
vez que alguien la abre. Sin cron y sin servidor: siempre muestra las próximas 12
horas contadas desde el momento de la visita.

Open-Meteo responde `access-control-allow-origin: *`, así que la llamada desde el
navegador está permitida. Esto NO funciona dentro de un artifact de claude.ai,
cuyo CSP bloquea cualquier host externo: necesita un host estático (GitHub Pages,
Netlify, Cloudflare Pages).
"""
import collections, json

from generar_pagina import BANDA, CSS, regiones_por_banda

JS = r"""
const B = DATA.banda_km, CORTES = DATA.cortes, C = DATA.coef;
const MESES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
const DIAS = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"];
const POS = ["no","inicio","intermedio","final"];
const NOMPOS = {inicio:"salida a feriado", final:"regreso de feriado", intermedio:"feriado"};
const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* Rampa de riesgo: apagado -> ámbar -> señal. Separada del verde de identidad. */
function color(v, vmax){
  const t = vmax > 0 ? Math.pow(Math.min(v / vmax, 1), 1.25) : 0;
  const [a, b, u] = t < .5
    ? [[0x7E,0x8C,0x88],[0xC9,0x94,0x2A], t/.5]
    : [[0xC9,0x94,0x2A],[0xB3,0x3A,0x22], (t-.5)/.5];
  const c = a.map((x,i) => Math.round(x + (b[i]-x)*u));
  return `rgba(${c[0]},${c[1]},${c[2]},${(0.14+0.86*t).toFixed(2)})`;
}

/* "Ahora" en hora de Chile, sin importar dónde esté el navegador. */
function ahoraChile(){
  return new Date().toLocaleString("sv-SE", {timeZone:"America/Santiago"}).replace(" ","T");
}

async function main(){
  const lat = DATA.celdas.map(c => c[0].toFixed(2)).join(",");
  const lon = DATA.celdas.map(c => c[1].toFixed(2)).join(",");
  const url = "https://api.open-meteo.com/v1/forecast?latitude=" + lat +
              "&longitude=" + lon + "&hourly=precipitation&forecast_days=2" +
              "&timezone=America%2FSantiago";
  let arr;
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error("HTTP " + r.status);
    const j = await r.json();
    arr = Array.isArray(j) ? j : [j];
  } catch (e) {
    document.getElementById("app").innerHTML =
      '<div class="aviso"><strong>No se pudo obtener el pronóstico.</strong> ' +
      'La página necesita alcanzar api.open-meteo.com para calcular el riesgo. ' +
      esc(String(e.message || e)) + '</div>';
    return;
  }

  const times = arr[0].hourly.time;
  const ahora = ahoraChile().slice(0, 13);
  let i0 = times.findIndex(t => t.slice(0, 13) >= ahora);
  if (i0 < 0) i0 = 0;
  const H = times.slice(i0, i0 + 12);
  if (!H.length){ document.getElementById("app").innerHTML =
    '<div class="aviso">El pronóstico no cubre las próximas horas.</div>'; return; }

  const nT = DATA.tramos.length, nH = H.length;
  const mu = [], lluv = [];
  const ctx = H.map(t => {
    const [y, m, d] = t.slice(0,10).split("-").map(Number);
    const h = +t.slice(11,13);
    const dow = (new Date(y, m-1, d).getDay() + 6) % 7;      // 0 = lunes
    const f = DATA.feriados[t.slice(0,10)] || "no";
    return {h, dow, mes:m-1, fer:POS.indexOf(f), fecha:t.slice(0,10), f};
  });

  for (let s = 0; s < nT; s++){
    const serie = arr[DATA.tramo_celda[s]].hourly.precipitation;
    const fila = [], filaL = [];
    for (let j = 0; j < nH; j++){
      const p = serie[i0 + j] ?? 0;
      const cat = p >= CORTES[1] ? 2 : (p >= CORTES[0] ? 1 : 0);
      const k = ctx[j];
      fila.push(Math.exp(C.tramo[s] + C.intercepto + C.hora[k.h] + C.dow[k.dow]
                         + C.mes[k.mes] + C.feriado[k.fer] + C.lluvia[cat]));
      filaL.push(p);
    }
    mu.push(fila); lluv.push(filaL);
  }

  /* colapsar tramos de 5 km en bandas */
  const nB = DATA.bandas.length;
  const M = Array.from({length:nB}, () => new Array(nH).fill(0));
  const LL = Array.from({length:nB}, () => new Array(nH).fill(0));
  for (let s = 0; s < nT; s++){
    const b = DATA.banda_ix[s];
    for (let j = 0; j < nH; j++){ M[b][j] += mu[s][j]; LL[b][j] = Math.max(LL[b][j], lluv[s][j]); }
  }

  const total = mu.flat().reduce((a,b) => a+b, 0);
  const basal = DATA.basal_hora * nH;
  const ratio = total / basal;
  const nLluvia = lluv.filter(f => f.some(p => p >= CORTES[0])).length;
  const plano = M.flat().slice().sort((a,b) => a-b);
  const vmax = plano[Math.floor(plano.length * 0.992)];
  const prom = total / (nB * nH);

  /* tramos top, con los factores que ELEVAN el riesgo en su hora peak */
  const tot = mu.map(f => f.reduce((a,b) => a+b, 0));
  const top = tot.map((v,i) => [v,i]).sort((a,b) => b[0]-a[0]).slice(0,8).map(([v,i]) => {
    let j = 0; for (let q = 1; q < nH; q++) if (mu[i][q] > mu[i][j]) j = q;
    const k = ctx[j], p = lluv[i][j], cat = p >= CORTES[1] ? 2 : (p >= CORTES[0] ? 1 : 0);
    const mHora = Math.exp(C.hora[k.h] - C.hora.reduce((a,b)=>a+b,0)/24);
    let mot = [];
    if (cat) mot.push([cat === 2 ? "lluvia" : "llovizna", Math.exp(C.lluvia[cat]-C.lluvia[0])]);
    mot.push([String(k.h).padStart(2,"0") + ":00", mHora]);
    if (k.f !== "no") mot.push([NOMPOS[k.f], Math.exp(C.feriado[k.fer]-C.feriado[0])]);
    mot = mot.filter(m => m[1] > 1.05).sort((a,b) => b[1]-a[1]).slice(0,2);
    return {km: DATA.tramos[i], region: DATA.regiones[DATA.banda_ix[i]],
            mult: v / (tot.reduce((a,b)=>a+b,0)/nT),
            hora: String(k.h).padStart(2,"0") + ":00", mot};
  });

  /* ---- render ---- */
  const d0 = ctx[0], dObj = new Date(...d0.fecha.split("-").map((x,i) => i===1 ? x-1 : +x));
  const fecha = `${DIAS[d0.dow]} ${dObj.getDate()} de ${MESES[d0.mes]}`;
  const fers = [...new Set(ctx.map(k => k.f).filter(f => f !== "no").map(f => NOMPOS[f]))];
  const pillBg = ratio >= 1.15 ? "var(--q2)" : (ratio >= 1 ? "var(--q1)" : "var(--accent-soft)");
  const pillFg = ratio >= 1 ? "#fff" : "var(--accent)";

  const cab = H.map((t,i) => `<div class="hd mono${i===0?" now":""}">${t.slice(11,13)}</div>`).join("");
  const filas = DATA.bandas.map((b,bi) => {
    const nueva = bi === 0 || DATA.regiones[bi] !== DATA.regiones[bi-1];
    const celdas = H.map((t,j) =>
      `<div class="cell" data-rain="${LL[bi][j] >= CORTES[0] ? 1 : 0}" title="km ${b}-${b+B} · ${t.slice(11,16)} · ${M[bi][j].toFixed(4)} esperados · ${(M[bi][j]/prom).toFixed(1)}x la banda promedio${LL[bi][j] >= CORTES[0] ? " · lluvia " + LL[bi][j].toFixed(1) + " mm/h" : ""}" style="background:${color(M[bi][j], vmax)}"></div>`).join("");
    return `<div class="rowlab${nueva?" nueva":""}">${nueva?`<span class="rg">${esc(DATA.regiones[bi])}</span>`:""}<span class="mono">${b}</span></div>${celdas}`;
  }).join("");
  const barras = H.map((_,j) => {
    let s = 0; for (let bi = 0; bi < nB; bi++) s += M[bi][j];
    return `<div class="hd mono" style="color:var(--ink-2)">${s.toFixed(2)}</div>`;
  }).join("");
  const tt = top.map(t => `<tr><td class="mono"><strong>km ${t.km}–${t.km+5}</strong></td>
    <td style="color:var(--ink-3)">${esc(t.region)}</td>
    <td class="mono"><strong>${t.mult.toFixed(1)}x</strong></td>
    <td class="mono">${t.hora}</td>
    <td>${t.mot.length ? t.mot.map(m => `<span class="tag ${["lluvia","llovizna"].includes(m[0])?"rain":"other"}">${esc(m[0])} ${m[1].toFixed(2)}x</span>`).join("") : '<span style="color:var(--ink-3)">—</span>'}</td></tr>`).join("");

  document.getElementById("app").innerHTML = `
<header>
  <div class="eyebrow">Ruta 5 Sur · Santiago – Puerto Montt · próximas 12 horas</div>
  <h1>Riesgo de siniestros</h1>
  <p class="sub mono">${fecha}, ${H[0].slice(11,16)} – ${H[nH-1].slice(11,16)}
    · <span class="vivo">calculado ahora</span> · hora de Chile</p>
</header>
<div class="metrics">
  <div class="metric"><div class="eyebrow">Siniestros esperados</div>
    <span class="v mono">${total.toFixed(1)}</span>
    <div class="n">en los ${nT} tramos de la ruta, próximas ${nH} h</div></div>
  <div class="metric"><div class="eyebrow">Contra un día normal</div>
    <span class="v mono">${ratio.toFixed(2)}x</span>
    <div class="n"><span class="pill" style="background:${pillBg};color:${pillFg}">${ratio>=1?"+":""}${((ratio-1)*100).toFixed(0)}%</span> basal ${basal.toFixed(1)} siniestros</div></div>
  <div class="metric"><div class="eyebrow">Lluvia pronosticada</div>
    <span class="v mono" style="color:var(--rain)">${nLluvia}</span>
    <div class="n">de ${nT} tramos con precipitación en la ventana${fers.length?" · "+esc(fers.join(", ")):""}</div></div>
</div>
<section>
  <h2>Kilómetro por hora</h2>
  <p class="hint">Cada fila es un tramo de ${B} km, de norte (Santiago, km 0) a sur
    (Los Lagos, km ${DATA.bandas[nB-1]}). El color es el número de siniestros esperados en
    esa celda: las bandas oscuras son las que menos concentran riesgo, no las que están
    «mejor de lo normal». La línea azul inferior marca las horas con lluvia pronosticada.</p>
  <div class="strip"><div class="grid"><div></div>${cab}${filas}
    <div class="rowlab" style="border:none;padding-top:7px"><span class="rg">esperados</span></div>${barras}
  </div></div>
  <div class="legend"><span>menor</span><span class="ramp">${
    [1,2,3,4,5,6,7,8].map(k => `<i style="background:${color(vmax*k/8, vmax)}"></i>`).join("")
  }</span><span>mayor</span>
  <span style="margin-left:8px"><i style="display:inline-block;width:14px;height:3px;background:var(--rain);vertical-align:middle"></i> lluvia</span></div>
</section>
<section>
  <h2>Dónde y por qué</h2>
  <p class="hint">Los ocho tramos de 5 km con mayor riesgo acumulado en la ventana.
    «vs tramo promedio» compara contra el tramo medio de la ruta en esta misma ventana:
    es concentración espacial, no elevación temporal. Los factores listados son solo los
    que <em>elevan</em> el riesgo en la hora peak.</p>
  <table><thead><tr><th>Tramo</th><th>Región</th><th>vs tramo promedio</th>
    <th>Hora peak</th><th>Factores dominantes</th></tr></thead><tbody>${tt}</tbody></table>
</section>
` + document.getElementById("notas").innerHTML;
}
main();
"""

NOTAS = """
<section>
  <h2>Cómo leer esto</h2>
  <div class="notes">
    <p><strong>Esto no dice dónde habrá un accidente.</strong> La tasa base es de
    <code>0,13&nbsp;%</code> por tramo-hora: en toda la Ruta 5 Sur se esperan
    <code>3,95</code> siniestros en 12 horas repartidos en 1.275 km. Cualquier sistema que
    prometa señalar el kilómetro y la hora exactos está sobrevendiendo. Lo que sí se puede
    afirmar es cuántos siniestros esperar en la ruta completa y qué tramos concentran el
    riesgo.</p>

    <p><strong>El mapa fijo hace casi todo el trabajo.</strong> En validación temporal
    (entrena 2020–2023, prueba 2024), vigilar el 5&nbsp;% de las horas-tramo más riesgosas
    cubre el 15,0&nbsp;% de los siniestros reales usando solo la ubicación, y el 19,2&nbsp;%
    sumando hora, día, feriado y clima. La capa dinámica aporta un 28&nbsp;% relativo: es
    real, no es transformadora.</p>

    <p><strong>La lluvia es el factor más fuerte del modelo</strong> (2,12x sobre calzada
    seca), por encima de la hora punta de las 18:00 (1,70x). Y probablemente esté
    subestimada: la precipitación viene del reanálisis ERA5, que promedia sobre celdas de
    25&nbsp;km y se pierde casi la mitad de las lluvias que registra Carabineros en terreno
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
  Pronóstico: <a href="https://open-meteo.com">Open-Meteo</a>, consultado por tu navegador
  al abrir esta página. Feriados: CONASET.
  Modelo Poisson sobre 11,2 millones de celdas tramo × hora.
  <a href="https://github.com/martinnmg1809/siniestros-transito-chile">Código y datos</a>.
</footer>
"""

EXTRA_CSS = """
.aviso{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--q2);
  border-radius:3px;padding:18px 20px;color:var(--ink-2);font-size:14.5px}
.vivo{color:var(--accent);font-weight:600}
.vivo::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;
  background:var(--accent);margin-right:6px;vertical-align:middle}
.cargando{color:var(--ink-3);font-size:14px;padding:60px 0;text-align:center}
"""


def main():
    m = json.load(open("modelo_final.json"))
    fer = json.load(open("feriados.json"))
    tramos = m["tramos"]
    regs = regiones_por_banda()
    bandas = sorted({int(t // BANDA) * BANDA for t in tramos})
    bix = {b: i for i, b in enumerate(bandas)}

    datos = {
        "banda_km": BANDA,
        "cortes": m["cortes_lluvia"],
        "coef": m["coef"],
        "tramos": tramos,
        "banda_ix": [bix[int(t // BANDA) * BANDA] for t in tramos],
        "bandas": bandas,
        "regiones": [regs[b] for b in bandas],
        "tramo_celda": m["tramo_celda"],
        "celdas": m["celdas"],
        "basal_hora": m["basal_ruta_hora"],
        "feriados": {k: v["dia"] for k, v in fer.items() if v["dia"] in
                     ("inicio", "intermedio", "final")},
    }

    html = f"""<meta charset="utf-8">
<title>Riesgo Ruta 5 Sur</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Riesgo de siniestros por tramo y hora en la Ruta 5 Sur, recalculado en vivo con el pronóstico de lluvia.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}{EXTRA_CSS}</style>
<div class="wrap">
  <div id="app"><p class="cargando">Consultando el pronóstico y calculando el riesgo…</p></div>
  <div id="notas" hidden>{NOTAS}</div>
</div>
<script>
const DATA = {json.dumps(datos, ensure_ascii=False, separators=(",", ":"))};
{JS}
</script>
"""
    open("index.html", "w").write(html)
    print(f"index.html generada — {len(html)/1024:.0f} KB, "
          f"{len(tramos)} tramos, {len(datos['celdas'])} celdas, "
          f"{len(datos['feriados'])} feriados")


if __name__ == "__main__":
    main()
