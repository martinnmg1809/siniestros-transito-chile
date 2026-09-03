#!/usr/bin/env python3
"""
Genera index.html: página en vivo con TODAS las rutas validadas.

Cada ruta trae sus dos vistas (tira horaria y mapa) y su propio modelo. El
pronóstico se pide solo para la ruta que el visitante está mirando, y se cachea
por ruta y por hora: así el costo contra la cuota de Open-Meteo no crece con el
número de rutas publicadas.
"""
import json

from generar_pagina import CSS
from generar_live import EXTRA_CSS

CSS_MULTI = """
.selector{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 24px}
.selector label{font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);font-weight:600}
.selector select{font-family:"Archivo",system-ui,sans-serif;font-size:15px;font-weight:600;
  color:var(--ink);background:var(--surface);border:1px solid var(--line);
  border-radius:3px;padding:9px 13px;min-width:260px;cursor:pointer}
.selector select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.selector .meta{font-size:12.5px;color:var(--ink-3)}
.calidad{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;
  vertical-align:middle}
.rutainfo{font-size:13px;color:var(--ink-2);margin:0 0 26px;max-width:70ch;
  padding:12px 15px;background:var(--surface);border:1px solid var(--line);
  border-left:3px solid var(--accent);border-radius:3px}
.rutainfo strong{color:var(--ink)}
/* rutas norte-sur: limitar por alto. rutas este-oeste (la 78, la 68): por ancho,
   o el navegador las estiraría hasta deformarlas. */
.mapa.vertical{height:min(78vh,860px);width:auto;max-width:100%}
.mapa.horizontal{width:100%;height:auto;max-height:70vh}
"""

JS = r"""
const CORTES = [0.1, 0.5];
const MESES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
const DIAS = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"];
const POS = ["no","inicio","intermedio","final"];
const NOMPOS = {inicio:"salida a feriado", final:"regreso de feriado", intermedio:"feriado"};
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function color(v, vmax){
  const t = vmax > 0 ? Math.pow(Math.min(v / vmax, 1), 1.25) : 0;
  const [a, b, u] = t < .5
    ? [[0x7E,0x8C,0x88],[0xC9,0x94,0x2A], t/.5]
    : [[0xC9,0x94,0x2A],[0xB3,0x3A,0x22], (t-.5)/.5];
  const c = a.map((x,i) => Math.round(x + (b[i]-x)*u));
  return `rgba(${c[0]},${c[1]},${c[2]},${(0.14+0.86*t).toFixed(2)})`;
}
const ahoraChile = () =>
  new Date().toLocaleString("sv-SE", {timeZone:"America/Santiago"}).replace(" ","T");

/* ---------- pronóstico, por ruta y con caché horaria ---------- */
async function pronostico(d){
  const clave = "riesgo-pron-" + d.nombre + "-" + ahoraChile().slice(0,13);
  try {
    const c = JSON.parse(localStorage.getItem(clave) || "null");
    if (c) return {arr: c, cache: true};
  } catch (e) {}

  const url = "https://api.open-meteo.com/v1/forecast"
    + "?latitude=" + d.celdas.map(c => c[0].toFixed(2)).join(",")
    + "&longitude=" + d.celdas.map(c => c[1].toFixed(2)).join(",")
    + "&hourly=precipitation&forecast_days=2&timezone=America%2FSantiago";

  let fallo = null;
  for (let i = 0; i < 2; i++){
    try {
      if (i) await new Promise(r => setTimeout(r, 1500));
      const ctrl = new AbortController();
      const reloj = setTimeout(() => ctrl.abort(), 8000);
      const r = await fetch(url, {signal: ctrl.signal});
      clearTimeout(reloj);
      if (!r.ok) throw new Error("HTTP " + r.status);
      const j = await r.json();
      const arr = Array.isArray(j) ? j : [j];
      try { localStorage.removeItem(clave); localStorage.setItem(clave, JSON.stringify(arr)); } catch (e) {}
      return {arr, cache: false};
    } catch (e) { fallo = e; }
  }
  return {arr: null, fallo};
}

/* ---------- cálculo del riesgo ---------- */
function calcular(d, arr){
  const sinClima = !arr;
  if (sinClima){
    const hoy = ahoraChile().slice(0,10);
    const man = new Date(Date.now() + 864e5)
      .toLocaleString("sv-SE",{timeZone:"America/Santiago"}).slice(0,10);
    const ts = [];
    for (const dd of [hoy, man])
      for (let h = 0; h < 24; h++) ts.push(dd + "T" + String(h).padStart(2,"0") + ":00");
    arr = d.celdas.map(() => ({hourly:{time: ts, precipitation: ts.map(() => 0)}}));
  }
  const times = arr[0].hourly.time;
  const ahora = ahoraChile().slice(0,13);
  let i0 = times.findIndex(t => t.slice(0,13) >= ahora);
  if (i0 < 0) i0 = 0;
  const H = times.slice(i0, i0 + 12), nH = H.length, C = d.coef, nT = d.tramos.length;

  const ctx = H.map(t => {
    const [y,m,dd] = t.slice(0,10).split("-").map(Number);
    const f = DATA.feriados[t.slice(0,10)] || "no";
    return {h:+t.slice(11,13), dow:(new Date(y,m-1,dd).getDay()+6)%7,
            mes:m-1, fer:POS.indexOf(f), f, fecha:t.slice(0,10)};
  });

  const mu = [], lluv = [];
  for (let s = 0; s < nT; s++){
    const serie = arr[d.tramo_celda[s]].hourly.precipitation;
    const fm = [], fl = [];
    for (let j = 0; j < nH; j++){
      const p = serie[i0+j] ?? 0;
      const cat = p >= CORTES[1] ? 2 : (p >= CORTES[0] ? 1 : 0);
      const k = ctx[j];
      fm.push(Math.exp(C.tramo[s] + C.intercepto + C.hora[k.h] + C.dow[k.dow]
                       + C.mes[k.mes] + C.feriado[k.fer] + C.lluvia[cat]));
      fl.push(p);
    }
    mu.push(fm); lluv.push(fl);
  }

  const nB = d.bandas.length;
  const M = Array.from({length:nB}, () => new Array(nH).fill(0));
  const LL = Array.from({length:nB}, () => new Array(nH).fill(0));
  for (let s = 0; s < nT; s++){
    const b = d.banda_ix[s];
    for (let j = 0; j < nH; j++){ M[b][j] += mu[s][j]; LL[b][j] = Math.max(LL[b][j], lluv[s][j]); }
  }
  return {mu, lluv, M, LL, H, nH, nB, nT, ctx, sinClima};
}

/* ---------- vista tira ---------- */
function tira(d, R){
  const {M, LL, H, nH, nB} = R;
  const plano = M.flat().slice().sort((a,b)=>a-b);
  const vmax = plano[Math.floor(plano.length*0.992)] || 1;
  const prom = M.flat().reduce((a,b)=>a+b,0) / (nB*nH);
  const cab = H.map((t,i)=>`<div class="hd mono${i===0?" now":""}">${t.slice(11,13)}</div>`).join("");
  const filas = d.bandas.map((b,bi)=>{
    const nueva = bi===0 || d.regiones_banda[bi] !== d.regiones_banda[bi-1];
    const celdas = H.map((t,j)=>
      `<div class="cell" data-rain="${LL[bi][j]>=CORTES[0]?1:0}" title="km ${b}-${b+d.banda_km} · ${t.slice(11,16)} · ${M[bi][j].toFixed(4)} esperados · ${(M[bi][j]/prom).toFixed(1)}x la banda promedio${LL[bi][j]>=CORTES[0]?" · lluvia "+LL[bi][j].toFixed(1)+" mm/h":""}" style="background:${color(M[bi][j],vmax)}"></div>`).join("");
    return `<div class="rowlab${nueva?" nueva":""}">${nueva?`<span class="rg">${esc(d.regiones_banda[bi])}</span>`:""}<span class="mono">${b}</span></div>${celdas}`;
  }).join("");
  const barras = H.map((_,j)=>{
    let s=0; for(let bi=0;bi<nB;bi++) s+=M[bi][j];
    return `<div class="hd mono" style="color:var(--ink-2)">${s.toFixed(2)}</div>`;
  }).join("");
  return `<p class="hint">Cada fila es un tramo de ${d.banda_km} km a lo largo de la ruta.
    El color es el número de siniestros esperados en esa celda: las bandas oscuras son las
    que menos concentran riesgo, no las que están «mejor de lo normal». La línea azul
    inferior marca las horas con lluvia pronosticada.</p>
  <div class="strip"><div class="grid" style="grid-template-columns:148px repeat(${nH},minmax(30px,1fr))">
    <div></div>${cab}${filas}
    <div class="rowlab" style="border:none;padding-top:7px"><span class="rg">esperados</span></div>${barras}
  </div></div>
  <div class="legend"><span>menor</span><span class="ramp">${
    [1,2,3,4,5,6,7,8].map(k=>`<i style="background:${color(vmax*k/8,vmax)}"></i>`).join("")
  }</span><span>mayor</span>
  <span style="margin-left:8px"><i style="display:inline-block;width:14px;height:3px;background:var(--rain);vertical-align:middle"></i> lluvia</span></div>`;
}

/* ---------- vista mapa ---------- */
function proyector(d){
  const pts = d.tramos.map(k => d.geometria[k]);
  const lats = pts.map(p=>p[0]), lons = pts.map(p=>p[1]);
  const laMin=Math.min(...lats), laMax=Math.max(...lats);
  const loMin=Math.min(...lons), loMax=Math.max(...lons);
  const kx = Math.cos((laMin+laMax)/2*Math.PI/180);
  /* Se respeta la proporción geográfica real, pero con un mínimo: rutas muy
     rectas (la 78 es casi puro este-oeste) quedarían como una raya sin grosor. */
  const dLa = Math.max(laMax-laMin, 1e-4), dLo = Math.max((loMax-loMin)*kx, 1e-4);
  /* La dimensión más larga define la escala; la proyección es siempre geográfica
     (lon -> x, lat -> y), así que la forma real de la ruta se conserva. */
  const escala = 1000 / Math.max(dLa, dLo);
  return {pts, vertical: dLa >= dLo,
    ancho: dLo * escala, alto: dLa * escala,
    p: ll => [(ll[1]-loMin)*kx*escala, (laMax-ll[0])*escala]};
}

function svgMapa(d, mu, vmax, j){
  const P = proyector(d), n = d.tramos.length, MARGEN = 200;
  const vb = `-16 -20 ${P.ancho + MARGEN} ${P.alto + 44}`;
  let trazo = "";
  for (let i = 0; i < n-1; i++){
    const a = P.p(P.pts[i]), b = P.p(P.pts[i+1]);
    const gap = Math.hypot(a[0]-b[0], a[1]-b[1]);
    if (gap > P.alto * 0.25) continue;      // no unir saltos espurios
    trazo += `<line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${b[0].toFixed(1)}" y2="${b[1].toFixed(1)}" stroke="${color(mu[i][j], vmax)}" stroke-width="13" stroke-linecap="round"><title>km ${d.tramos[i]}–${d.tramos[i]+d.tramo_km} · ${mu[i][j].toFixed(4)} esperados</title></line>`;
  }
  let ciu = "";
  const usadas = [];
  for (const c of d.ciudades){
    const [x,y] = P.p([c.lat, c.lon]);
    let ly = y;
    while (usadas.some(v => Math.abs(v-ly) < 46)) ly += 46;   // evitar solapes
    usadas.push(ly);
    const lx = P.ancho + 32;
    ciu += `<line x1="${(x+10).toFixed(1)}" y1="${y.toFixed(1)}" x2="${lx-8}" y2="${ly.toFixed(1)}" class="guia"/>`
      + `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5" class="ciudad"/>`
      + `<text x="${lx}" y="${(ly+5).toFixed(1)}" class="etq">${esc(c.nombre)}</text>`
      + `<text x="${lx}" y="${(ly+23).toFixed(1)}" class="etqkm">km ${c.km}</text>`;
  }
  const clase = P.vertical ? "mapa vertical" : "mapa horizontal";
  return `<svg viewBox="${vb}" class="${clase}" role="img" aria-label="Mapa de ${esc(d.nombre)} coloreado por riesgo">${trazo}${ciu}</svg>`;
}

/* ---------- render principal ---------- */
let ESTADO = null;

function pintar(d, R, desdeCache, fallo){
  const {mu, M, H, nH, nB, nT, ctx, sinClima} = R;
  const total = mu.flat().reduce((a,b)=>a+b,0);
  const basal = d.basal_ruta_hora * nH, ratio = total/basal;
  const nLluvia = R.lluv.filter(f => f.some(p => p >= CORTES[0])).length;
  const d0 = ctx[0], dObj = new Date(...d0.fecha.split("-").map((x,i)=> i===1? x-1 : +x));
  const fers = [...new Set(ctx.map(k=>k.f).filter(f=>f!=="no").map(f=>NOMPOS[f]))];
  const pillBg = ratio>=1.15 ? "var(--q2)" : (ratio>=1 ? "var(--q1)" : "var(--accent-soft)");
  const pillFg = ratio>=1 ? "#fff" : "var(--accent)";
  const v = d.validacion;

  const banner = sinClima
    ? `<div class="aviso"><strong>Sin datos de lluvia.</strong> api.open-meteo.com no
       responde ahora mismo (${esc((fallo&&fallo.message)||"sin respuesta")}), así que el
       riesgo está calculado con calzada seca. La ubicación, la hora, el día y los feriados
       sí están considerados. Recarga en unos minutos para incluir el clima.</div>` : "";

  document.getElementById("vista").innerHTML = banner + `
<p class="sub mono" style="margin:0 0 18px">${DIAS[d0.dow]} ${dObj.getDate()} de ${MESES[d0.mes]},
  ${H[0].slice(11,16)} – ${H[nH-1].slice(11,16)}
  · <span class="vivo">${desdeCache?"recalculado":"calculado ahora"}</span> · hora de Chile</p>

<div class="rutainfo"><strong>${esc(d.nombre)}</strong> · ${d.n.toLocaleString("es-CL")}
  siniestros 2020–2024 en ${nT} tramos de ${d.tramo_km} km · ${esc(d.regiones.join(", "))}.
  En la validación sobre 2024 (${v.siniestros_2024} siniestros), vigilar el 5 % de las
  horas-tramo más riesgosas cubre el <strong>${(v.captura5*100).toFixed(1)} %</strong> de
  los siniestros reales; solo con la ubicación sería
  ${(v.captura5_estatico*100).toFixed(1)} %.</div>

<div class="metrics">
  <div class="metric"><div class="eyebrow">Siniestros esperados</div>
    <span class="v mono">${total.toFixed(total<1?2:1)}</span>
    <div class="n">en los ${nT} tramos, próximas ${nH} h</div></div>
  <div class="metric"><div class="eyebrow">Contra un día normal</div>
    <span class="v mono">${ratio.toFixed(2)}x</span>
    <div class="n"><span class="pill" style="background:${pillBg};color:${pillFg}">${ratio>=1?"+":""}${((ratio-1)*100).toFixed(0)}%</span> basal ${basal.toFixed(basal<1?2:1)}</div></div>
  <div class="metric"><div class="eyebrow">Lluvia pronosticada</div>
    <span class="v mono" style="color:${sinClima?"var(--ink-3)":"var(--rain)"}">${sinClima?"—":nLluvia}</span>
    <div class="n">${sinClima?"pronóstico no disponible":`de ${nT} tramos con precipitación`}${fers.length?" · "+esc(fers.join(", ")):""}</div></div>
</div>

<div class="tabs" role="tablist">
  <button class="tab activa" id="t-tira" role="tab" aria-selected="true">Tira horaria</button>
  <button class="tab" id="t-mapa" role="tab" aria-selected="false">Mapa</button>
</div>
<section id="sec-tira"><h2>Kilómetro por hora</h2>${tira(d, R)}</section>
<section id="sec-mapa" hidden>
  <h2>Mapa de la ruta</h2>
  <p class="hint">La ruta a escala real, coloreada por el riesgo de cada tramo de
    ${d.tramo_km} km en la hora seleccionada. La escala de color es la misma en las 12
    horas, así que los cambios que veas son cambios reales de riesgo.</p>
  <div class="ctrl"><label for="hora">Hora</label>
    <input type="range" id="hora" min="0" max="${nH-1}" value="0" step="1">
    <span class="mono" id="horaVal">${H[0].slice(11,16)}</span>
    <span class="mono" id="horaTot" style="color:var(--ink-3)"></span></div>
  <div class="mapawrap" id="mapa"></div>
</section>
<section><h2>Dónde y por qué</h2>${tabla(d, R)}</section>`;

  const planoMu = mu.flat().slice().sort((a,b)=>a-b);
  const vmaxMapa = planoMu[Math.floor(planoMu.length*0.995)] || 1;
  const pintarMapa = j => {
    document.getElementById("mapa").innerHTML = svgMapa(d, mu, vmaxMapa, j);
    document.getElementById("horaVal").textContent = H[j].slice(11,16);
    let s=0; for(let bi=0;bi<nB;bi++) s+=M[bi][j];
    document.getElementById("horaTot").textContent = `· ${s.toFixed(2)} esperados en la ruta`;
  };
  document.getElementById("hora").addEventListener("input", e => pintarMapa(+e.target.value));
  const secT = document.getElementById("sec-tira"), secM = document.getElementById("sec-mapa");
  const bT = document.getElementById("t-tira"), bM = document.getElementById("t-mapa");
  const ver = esMapa => {
    secT.hidden = esMapa; secM.hidden = !esMapa;
    bT.classList.toggle("activa", !esMapa); bM.classList.toggle("activa", esMapa);
    bT.setAttribute("aria-selected", String(!esMapa));
    bM.setAttribute("aria-selected", String(esMapa));
    if (esMapa && !secM.dataset.listo){ pintarMapa(+document.getElementById("hora").value); secM.dataset.listo="1"; }
  };
  bT.addEventListener("click", ()=>ver(false));
  bM.addEventListener("click", ()=>ver(true));
}

function tabla(d, R){
  const {mu, ctx, lluv, nH, nT} = R, C = d.coef;
  const tot = mu.map(f => f.reduce((a,b)=>a+b,0));
  const media = tot.reduce((a,b)=>a+b,0)/nT;
  const filas = tot.map((v,i)=>[v,i]).sort((a,b)=>b[0]-a[0]).slice(0, Math.min(8, nT)).map(([v,i])=>{
    let j=0; for(let q=1;q<nH;q++) if (mu[i][q] > mu[i][j]) j=q;
    const k = ctx[j], p = lluv[i][j], cat = p>=CORTES[1]?2:(p>=CORTES[0]?1:0);
    const mediaHora = C.hora.reduce((a,b)=>a+b,0)/24;
    let mot = [];
    if (cat) mot.push([cat===2?"lluvia":"llovizna", Math.exp(C.lluvia[cat]-C.lluvia[0])]);
    mot.push([String(k.h).padStart(2,"0")+":00", Math.exp(C.hora[k.h]-mediaHora)]);
    if (k.f!=="no") mot.push([NOMPOS[k.f], Math.exp(C.feriado[k.fer]-C.feriado[0])]);
    mot = mot.filter(m=>m[1]>1.05).sort((a,b)=>b[1]-a[1]).slice(0,2);
    return `<tr><td class="mono"><strong>km ${d.tramos[i]}–${d.tramos[i]+d.tramo_km}</strong></td>
      <td class="mono"><strong>${(v/media).toFixed(1)}x</strong></td>
      <td class="mono">${String(k.h).padStart(2,"0")}:00</td>
      <td>${mot.length? mot.map(m=>`<span class="tag ${["lluvia","llovizna"].includes(m[0])?"rain":"other"}">${esc(m[0])} ${m[1].toFixed(2)}x</span>`).join("") : '<span style="color:var(--ink-3)">—</span>'}</td></tr>`;
  }).join("");
  return `<p class="hint">Los tramos con mayor riesgo acumulado en la ventana.
    «vs tramo promedio» compara contra el tramo medio de esta ruta en esta misma ventana:
    es concentración espacial, no elevación temporal. Los factores listados son solo los
    que <em>elevan</em> el riesgo en la hora peak.</p>
  <table><thead><tr><th>Tramo</th><th>vs tramo promedio</th><th>Hora peak</th>
    <th>Factores dominantes</th></tr></thead><tbody>${filas}</tbody></table>`;
}

async function mostrar(nombre){
  const d = DATA.rutas[nombre];
  document.getElementById("vista").innerHTML =
    '<p class="cargando">Consultando el pronóstico de ' + esc(nombre) + '…</p>';
  const {arr, cache, fallo} = await pronostico(d);
  pintar(d, calcular(d, arr), !!cache, fallo);
}

function iniciar(){
  const sel = document.getElementById("ruta");
  sel.addEventListener("change", () => {
    localStorage.setItem("riesgo-ruta", sel.value);
    mostrar(sel.value);
  });
  let inicial = null;
  try { inicial = localStorage.getItem("riesgo-ruta"); } catch (e) {}
  if (inicial && DATA.rutas[inicial]) sel.value = inicial;
  mostrar(sel.value);
}
iniciar();
"""

NOTAS = """
<section>
  <h2>Cómo leer esto</h2>
  <div class="notes">
    <p><strong>Esto no dice dónde habrá un accidente.</strong> La tasa base ronda el
    <code>0,1&nbsp;%</code> por tramo-hora. Cualquier sistema que prometa señalar el
    kilómetro y la hora exactos está sobrevendiendo. Lo que sí se puede afirmar es cuántos
    siniestros esperar en la ruta completa y qué tramos concentran el riesgo.</p>

    <p><strong>La ubicación hace casi todo el trabajo.</strong> Cada ruta muestra arriba
    cuánto captura su modelo completo y cuánto capturaría solo con la ubicación. La
    diferencia entre ambos es lo que aportan la hora, el día, los feriados y el clima:
    real, pero menor que el efecto de dónde está el tramo.</p>

    <p><strong>La lluvia es el factor más fuerte del modelo</strong> — en la Ruta 5 Sur,
    2,12x sobre calzada seca, por encima de la hora punta de las 18:00 (1,70x). Y
    probablemente esté subestimada: la precipitación viene del reanálisis ERA5, que
    promedia sobre celdas de 25&nbsp;km y se pierde casi la mitad de las lluvias que
    registra Carabineros en terreno (kappa 0,26). El error de medición atenúa el
    coeficiente hacia 1.</p>

    <p><strong>Las rutas no son comparables entre sí.</strong> Cada una tiene su propio
    modelo y su propio basal; un «2,0x» en la Ruta 68 no equivale a un «2,0x» en la Ruta 5
    Sur. Las rutas con menos datos tienen modelos más ruidosos, y por eso se muestra la
    validación de cada una.</p>

    <p><strong>Lo que falta.</strong> No hay flujo vehicular horario: el censo del MOP
    entrega un promedio anual por punto, así que el modelo no puede separar «hay más
    autos» de «conducir a esta hora es más peligroso por auto». Los datos son de
    Carabineros y subregistran los siniestros sin lesionados. El campo de ruta solo está
    poblado hasta 2024.</p>
  </div>
</section>
<footer>
  Siniestros: CONASET / Carabineros de Chile, 2020–2024.
  Pronóstico: <a href="https://open-meteo.com">Open-Meteo</a>, consultado por tu navegador.
  Feriados: CONASET.
  <a href="https://github.com/martinnmg1809/siniestros-transito-chile">Código y datos</a>.
</footer>
"""


def main():
    modelos = json.load(open("modelos.json"))
    fer = json.load(open("feriados.json"))

    def redondear(o, n=4):
        if isinstance(o, float):
            return round(o, n)
        if isinstance(o, list):
            return [redondear(x, n) for x in o]
        if isinstance(o, dict):
            return {k: redondear(v, n) for k, v in o.items()}
        return o

    rutas = {k: redondear(v) for k, v in modelos.items()}
    orden = sorted(rutas, key=lambda k: -rutas[k]["n"])

    datos = {"rutas": rutas,
             "feriados": {k: v["dia"] for k, v in fer.items()
                          if v["dia"] in ("inicio", "intermedio", "final")}}

    opciones = "".join(
        f'<option value="{k}">{k} · {rutas[k]["n"]:,} siniestros</option>'.replace(",", ".")
        for k in orden)

    html = f"""<meta charset="utf-8">
<title>Riesgo en Carreteras de Chile</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Riesgo de siniestros por tramo y hora en {len(rutas)} carreteras de Chile, recalculado en vivo con el pronóstico de lluvia.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}{EXTRA_CSS}{CSS_MULTI}</style>
<div class="wrap">
  <header>
    <div class="eyebrow">{len(rutas)} carreteras de Chile · próximas 12 horas</div>
    <h1>Riesgo de siniestros</h1>
  </header>
  <div class="selector">
    <label for="ruta">Carretera</label>
    <select id="ruta">{opciones}</select>
  </div>
  <div id="vista"><p class="cargando">Cargando…</p></div>
  {NOTAS}
</div>
<script>
const DATA = {json.dumps(datos, ensure_ascii=False, separators=(",", ":"))};
{JS}
</script>
"""
    open("index.html", "w").write(html)
    print(f"index.html — {len(html)/1024:.0f} KB · {len(rutas)} rutas · "
          f"{sum(len(v['tramos']) for v in rutas.values())} tramos")


if __name__ == "__main__":
    main()
