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

/* ---------------- vista mapa ---------------- */
/* La Ruta 5 Sur recorre 9,7 grados de latitud y solo 3,2 de longitud: dibujada a
   escala real es una línea casi vertical. Se respeta esa proporción (corrigiendo
   longitud por cos(lat)) en vez de ensancharla, y las etiquetas van al costado. */
function proyector(){
  const pts = DATA.tramos.map(k => DATA.geometria[k]);
  const lats = pts.map(p => p[0]), lons = pts.map(p => p[1]);
  const latMin = Math.min(...lats), latMax = Math.max(...lats);
  const lonMin = Math.min(...lons), lonMax = Math.max(...lons);
  const kx = Math.cos((latMin + latMax) / 2 * Math.PI / 180);
  const alto = 1000, esc = alto / (latMax - latMin);
  const ancho = (lonMax - lonMin) * kx * esc;
  return {
    pts, ancho, alto,
    p: ll => [((ll[1] - lonMin) * kx * esc), (latMax - ll[0]) * esc],
  };
}

function svgMapa(mu, vmax, j){
  const P = proyector(), n = DATA.tramos.length;
  const MARGEN = 190;                      // espacio a la derecha para etiquetas
  const vb = `-14 -18 ${P.ancho + MARGEN} ${P.alto + 36}`;

  let trazo = "";
  for (let i = 0; i < n - 1; i++){
    const a = P.p(P.pts[i]), b = P.p(P.pts[i + 1]);
    trazo += `<line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${b[0].toFixed(1)}" y2="${b[1].toFixed(1)}" stroke="${color(mu[i][j], vmax)}" stroke-width="11" stroke-linecap="round"><title>km ${DATA.tramos[i]}–${DATA.tramos[i]+5} · ${mu[i][j].toFixed(4)} esperados</title></line>`;
  }

  let ciudades = "";
  for (const c of DATA.ciudades){
    const [x, y] = P.p([c.lat, c.lon]);
    const lx = P.ancho + 30;
    ciudades += `<line x1="${(x+9).toFixed(1)}" y1="${y.toFixed(1)}" x2="${lx-8}" y2="${y.toFixed(1)}" class="guia"/>`
      + `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4.5" class="ciudad"/>`
      + `<text x="${lx}" y="${(y+5).toFixed(1)}" class="etq">${esc(c.nombre)}</text>`
      + `<text x="${lx}" y="${(y+22).toFixed(1)}" class="etqkm">km ${c.km}</text>`;
  }
  return `<svg viewBox="${vb}" class="mapa" role="img" aria-label="Mapa de la Ruta 5 Sur coloreado por riesgo">${trazo}${ciudades}</svg>`;
}

async function main(){
  const lat = DATA.celdas.map(c => c[0].toFixed(2)).join(",");
  const lon = DATA.celdas.map(c => c[1].toFixed(2)).join(",");
  const url = "https://api.open-meteo.com/v1/forecast?latitude=" + lat +
              "&longitude=" + lon + "&hourly=precipitation&forecast_days=2" +
              "&timezone=America%2FSantiago";
  /* El pronóstico solo cambia una vez por hora, y cada carga cuesta 60 llamadas
     contra la cuota gratuita de Open-Meteo. Se cachea por hora en el navegador:
     así una visita repetida dentro de la misma hora no vuelve a pedir nada. */
  const claveHora = ahoraChile().slice(0, 13);
  const leerCache = () => {
    try {
      const c = JSON.parse(localStorage.getItem("riesgo-r5-pronostico") || "null");
      return c && c.hora === claveHora ? c.datos : null;
    } catch (e) { return null; }
  };
  const guardarCache = datos => {
    try {
      localStorage.setItem("riesgo-r5-pronostico",
        JSON.stringify({hora: claveHora, datos}));
    } catch (e) { /* modo privado o almacenamiento lleno: seguir sin cachear */ }
  };

  let arr = leerCache(), desdeCache = !!arr, fallo = null;
  if (!arr){
    for (let intento = 0; intento < 2 && !arr; intento++){
      try {
        if (intento) await new Promise(r => setTimeout(r, 1500));
        const ctrl = new AbortController();
        const reloj = setTimeout(() => ctrl.abort(), 8000);
        const r = await fetch(url, {signal: ctrl.signal});
        clearTimeout(reloj);
        if (!r.ok) throw new Error("HTTP " + r.status);
        const j = await r.json();
        arr = Array.isArray(j) ? j : [j];
        guardarCache(arr);
      } catch (e) { fallo = e; }
    }
  }

  /* Sin pronóstico la página NO se cae: el clima es una de cuatro variables, y sin
     ella el modelo sigue capturando la mayor parte de la señal (17,8 % contra 19,2 %
     en el top 5 % de la validación). Se calcula con calzada seca y se avisa arriba. */
  const sinClima = !arr;
  if (sinClima){
    const dia = ahoraChile().slice(0, 10), sig = new Date(Date.now() + 864e5)
      .toLocaleString("sv-SE", {timeZone:"America/Santiago"}).slice(0, 10);
    const ts = [];
    for (const d of [dia, sig])
      for (let h = 0; h < 24; h++) ts.push(d + "T" + String(h).padStart(2,"0") + ":00");
    arr = DATA.celdas.map(() => ({hourly:{time: ts, precipitation: ts.map(() => 0)}}));
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

  /* vmax global de las 12 horas: así el mapa cambia de verdad al mover la hora */
  const planoMu = mu.flat().slice().sort((a,b) => a-b);
  const vmaxMapa = planoMu[Math.floor(planoMu.length * 0.995)];

  const banner = sinClima
    ? '<div class="aviso"><strong>Sin datos de lluvia.</strong> api.open-meteo.com no ' +
      'responde ahora mismo (' + esc(String((fallo && fallo.message) || "sin respuesta")) +
      '), así que el riesgo de abajo está calculado con calzada seca. La ubicación, la ' +
      'hora, el día y los feriados sí están considerados; solo falta el clima, que es ' +
      'el factor más fuerte del modelo. Recarga en unos minutos para incluirlo.</div>'
    : "";

  document.getElementById("app").innerHTML = banner + `
<header>
  <div class="eyebrow">Ruta 5 Sur · Santiago – Puerto Montt · próximas 12 horas</div>
  <h1>Riesgo de siniestros</h1>
  <p class="sub mono">${fecha}, ${H[0].slice(11,16)} – ${H[nH-1].slice(11,16)}
    · <span class="vivo">${desdeCache ? "recalculado" : "calculado ahora"}</span> · hora de Chile</p>
</header>
<div class="metrics">
  <div class="metric"><div class="eyebrow">Siniestros esperados</div>
    <span class="v mono">${total.toFixed(1)}</span>
    <div class="n">en los ${nT} tramos de la ruta, próximas ${nH} h</div></div>
  <div class="metric"><div class="eyebrow">Contra un día normal</div>
    <span class="v mono">${ratio.toFixed(2)}x</span>
    <div class="n"><span class="pill" style="background:${pillBg};color:${pillFg}">${ratio>=1?"+":""}${((ratio-1)*100).toFixed(0)}%</span> basal ${basal.toFixed(1)} siniestros</div></div>
  <div class="metric"><div class="eyebrow">Lluvia pronosticada</div>
    <span class="v mono" style="color:${sinClima?"var(--ink-3)":"var(--rain)"}">${sinClima?"—":nLluvia}</span>
    <div class="n">${sinClima?"pronóstico no disponible":`de ${nT} tramos con precipitación en la ventana`}${fers.length?" · "+esc(fers.join(", ")):""}</div></div>
</div>
<div class="tabs" role="tablist">
  <button class="tab activa" id="t-tira" role="tab" aria-selected="true">Tira horaria</button>
  <button class="tab" id="t-mapa" role="tab" aria-selected="false">Mapa</button>
</div>
<section id="sec-tira">
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
<section id="sec-mapa" hidden>
  <h2>Mapa de la ruta</h2>
  <p class="hint">La ruta a escala real, coloreada por el riesgo de cada tramo de 5 km en
    la hora seleccionada. Mueve el control para recorrer las 12 horas: la escala de color
    es la misma en todas, así que los cambios que veas son cambios reales de riesgo.</p>
  <div class="ctrl">
    <label for="hora">Hora</label>
    <input type="range" id="hora" min="0" max="${nH-1}" value="0" step="1">
    <span class="mono" id="horaVal">${H[0].slice(11,16)}</span>
    <span class="mono" id="horaTot" style="color:var(--ink-3)"></span>
  </div>
  <div class="mapawrap" id="mapa"></div>
</section>
<section id="sec-tabla">
  <h2>Dónde y por qué</h2>
  <p class="hint">Los ocho tramos de 5 km con mayor riesgo acumulado en la ventana.
    «vs tramo promedio» compara contra el tramo medio de la ruta en esta misma ventana:
    es concentración espacial, no elevación temporal. Los factores listados son solo los
    que <em>elevan</em> el riesgo en la hora peak.</p>
  <table><thead><tr><th>Tramo</th><th>Región</th><th>vs tramo promedio</th>
    <th>Hora peak</th><th>Factores dominantes</th></tr></thead><tbody>${tt}</tbody></table>
</section>
` + document.getElementById("notas").innerHTML;

  /* --- interacción --- */
  const pintarMapa = j => {
    document.getElementById("mapa").innerHTML = svgMapa(mu, vmaxMapa, j);
    document.getElementById("horaVal").textContent = H[j].slice(11,16);
    let s = 0; for (let bi = 0; bi < nB; bi++) s += M[bi][j];
    document.getElementById("horaTot").textContent = `· ${s.toFixed(2)} esperados en la ruta`;
  };
  document.getElementById("hora").addEventListener("input", e => pintarMapa(+e.target.value));

  const tira = document.getElementById("sec-tira"), mapa = document.getElementById("sec-mapa");
  const bT = document.getElementById("t-tira"), bM = document.getElementById("t-mapa");
  const ver = esMapa => {
    tira.hidden = esMapa; mapa.hidden = !esMapa;
    bT.classList.toggle("activa", !esMapa); bM.classList.toggle("activa", esMapa);
    bT.setAttribute("aria-selected", String(!esMapa));
    bM.setAttribute("aria-selected", String(esMapa));
    if (esMapa && !mapa.dataset.listo){ pintarMapa(+document.getElementById("hora").value); mapa.dataset.listo = "1"; }
  };
  bT.addEventListener("click", () => ver(false));
  bM.addEventListener("click", () => ver(true));
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

/* pestañas de vista */
.tabs{display:flex;gap:2px;margin-bottom:26px;border-bottom:1px solid var(--line)}
.tab{font-family:inherit;font-size:12px;letter-spacing:.09em;text-transform:uppercase;
  font-weight:600;color:var(--ink-3);background:none;border:none;cursor:pointer;
  padding:9px 16px;border-bottom:2px solid transparent;margin-bottom:-1px}
.tab:hover{color:var(--ink-2)}
.tab.activa{color:var(--ink);border-bottom-color:var(--accent)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px}

/* control de hora */
.ctrl{display:flex;align-items:center;gap:13px;margin:0 0 20px;flex-wrap:wrap}
.ctrl label{font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);font-weight:600}
.ctrl input[type=range]{flex:1;min-width:200px;max-width:380px;accent-color:var(--accent)}
.ctrl input[type=range]:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.ctrl .mono{font-size:14px;font-weight:600}

/* mapa */
.mapawrap{background:var(--surface);border:1px solid var(--line);border-radius:3px;
  padding:20px 14px;overflow-x:auto}
.mapa{display:block;margin:0 auto;height:min(78vh,860px);max-width:100%}
.mapa .ciudad{fill:var(--surface);stroke:var(--ink-2);stroke-width:2}
.mapa .guia{stroke:var(--line);stroke-width:1}
.mapa .etq{fill:var(--ink);font-family:"Archivo",sans-serif;font-size:19px;font-weight:600}
.mapa .etqkm{fill:var(--ink-3);font-family:"IBM Plex Mono",monospace;font-size:15px}
"""


def main():
    m = json.load(open("modelo_final.json"))
    fer = json.load(open("feriados.json"))
    ciudades = json.load(open("ciudades.json"))

    # Cada visita cuesta una llamada por celda contra la cuota gratuita de Open-Meteo,
    # así que 60 celdas es demasiado: una página con algo de tráfico agota el límite.
    # Submuestreando a 1 de cada 4 quedan 15, y medido sobre las 43.848 horas de
    # entrenamiento el costo es: 3,2 % de error medio en mu por tramo y -0,05 % de
    # sesgo en el total de la ruta. Muy por debajo de la incertidumbre del modelo.
    PASO = 4
    celdas_full = m["celdas"]
    sel = list(range(0, len(celdas_full), PASO))
    celdas_red = [celdas_full[i] for i in sel]

    def mas_cercana(c):
        return min(range(len(celdas_red)),
                   key=lambda k: (celdas_red[k][0] - c[0]) ** 2
                                 + (celdas_red[k][1] - c[1]) ** 2)

    tramo_celda_red = [mas_cercana(celdas_full[i]) for i in m["tramo_celda"]]
    # el km 0 de la Ruta 5 Sur es Santiago por definición
    g0 = m["geometria"][str(min(m["tramos"]))]
    ciudades = [{"nombre": "Santiago", "km": 0,
                 "lat": round(g0[0], 4), "lon": round(g0[1], 4)}] + [
        {k: c[k] for k in ("nombre", "km", "lat", "lon")} for c in ciudades]
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
        "tramo_celda": tramo_celda_red,
        "celdas": celdas_red,
        "basal_hora": m["basal_ruta_hora"],
        "geometria": {str(t): [round(v, 4) for v in m["geometria"][str(t)]]
                      for t in tramos},
        "ciudades": ciudades,
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
  <div id="vistas" hidden></div>
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
