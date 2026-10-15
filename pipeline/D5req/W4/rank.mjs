// Task 2 analysis: tornado (OAT), global sensitivity, ranking stability, robust sign vs ASIS.
import fs from 'fs';
const load = f => fs.existsSync(f) ? JSON.parse(fs.readFileSync(f)) : null;
function merge(main, extra) { const m = new Map(main.scen.map(s => [s.name, s])); if (extra) for (const s of extra.scen) { const t = m.get(s.name); Object.assign(t.res, s.res); } return [...m.values()]; }
const OAT = merge(load('results_sens_oat.json'), load('results_sens_oat_extra.json'));
const GLO = merge(load('results_sens_global.json'), load('results_sens_global_extra.json'));
const base = OAT.find(s => s.name === 'base');
for (const s of OAT) for (const p of Object.keys(base.res)) if (!s.res[p]) s.res[p] = base.res[p]; // r/delay scenarios: non-expiry policies unaffected
const POL = Object.keys(base.res).filter(p => p !== 'SPRINT_added_2xY'); // fixed-capacity set
const MET = { EAimp_by90: 1, EAimp_by365: 1, EAimp_RMST365: -1, EAimp_legacyAcceptedShare: 1, EAimp_value_uniform: 1, EAimp_value_rating: 1, EAimp_value_assertionUse: 1, EAimp_value_level_KEY: 1, lostFinal: -1 };
const mean = a => a.reduce((x, y) => x + y, 0) / a.length;
const mOf = (s, p, k) => mean(s.res[p].map(o => o[k]));
const tol = (k, ref) => k.includes('value') ? 0.01 * Math.abs(ref) : k.includes('RMST') ? 2 : k === 'lostFinal' ? 0.5 : 0.005;
function ranks(vals, dir) { // average ranks, 1 = best
  const idx = vals.map((v, i) => [dir * v, i]).sort((a, b) => b[0] - a[0]); const r = new Array(vals.length);
  for (let i = 0; i < idx.length;) { let j = i; while (j + 1 < idx.length && Math.abs(idx[j + 1][0] - idx[i][0]) < 1e-9) j++; for (let k = i; k <= j; k++) r[idx[k][1]] = (i + j) / 2 + 1; i = j + 1; } return r; }
function kendall(a, b) { let c = 0, d = 0, ta = 0, tb = 0; for (let i = 0; i < a.length; i++) for (let j = i + 1; j < a.length; j++) { const x = Math.sign(a[i] - a[j]), y = Math.sign(b[i] - b[j]); if (x === 0 && y === 0) continue; if (x === 0) { ta++; continue; } if (y === 0) { tb++; continue; } x === y ? c++ : d++; } return (c - d) / Math.sqrt((c + d + ta) * (c + d + tb)); }
const q = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.floor(p * (s.length - 1))]; };
const out = { policies: POL, metrics: MET, tornado: {}, rankStability: {}, robustSign: {}, globalDrivers: {} };
const L = [];
// ---------- tornado: mean paired delta vs ASIS at each OAT level ----------
const PARAMS = ['r', 'delay', 'kappa', 'effort', 'cap', 'cal'];
for (const k of ['EAimp_by90', 'EAimp_by365', 'EAimp_RMST365', 'EAimp_legacyAcceptedShare', 'EAimp_value_rating', 'EAimp_value_assertionUse']) {
  out.tornado[k] = {}; L.push(`\n### Tornado ${k}: paired delta vs ASIS (mean over 8 reps) — base, then [min, max] over levels of each parameter`);
  for (const p of POL.concat('SPRINT_added_2xY')) { if (p === 'ASIS_logit') continue;
    const d = s => mean(s.res[p].map((o, i) => o[k] - s.res.ASIS_logit[i][k]));
    const row = { base: d(base) }; for (const par of PARAMS) { const ss = OAT.filter(s => s.name.startsWith(par + '=')).concat(base); const v = ss.map(d); row[par] = [Math.min(...v), Math.max(...v)]; }
    out.tornado[k][p] = row; const f = x => (Math.abs(x) >= 10 ? x.toFixed(0) : x.toFixed(3));
    L.push(`  ${p.padEnd(24)} base ${f(row.base).padStart(7)} | ` + PARAMS.map(par => `${par} [${f(row[par][0])}, ${f(row[par][1])}]`).join(' '));
  }
}
// ---------- ranking stability ----------
L.push('\n### Ranking stability (fixed-capacity policies, n = ' + POL.length + '); Kendall tau_b of each scenario ranking vs base ranking');
for (const [k, dir] of Object.entries(MET)) {
  const rk = s => ranks(POL.map(p => mOf(s, p, k)), dir); const rb = rk(base);
  const tO = OAT.filter(s => s.name !== 'base').map(s => kendall(rk(s), rb)), tG = GLO.map(s => kendall(rk(s), rb));
  const perPol = {}; POL.forEach((p, i) => { const all = OAT.map(s => rk(s)[i]), g = GLO.map(s => rk(s)[i]); perPol[p] = { base: rb[i], oatRange: [Math.min(...all), Math.max(...all)], global5_95: [q(g, .05), q(g, .95)], globalTop1: g.filter(x => x <= 1.5).length / g.length }; });
  out.rankStability[k] = { tauOAT: { median: q(tO, .5), min: Math.min(...tO) }, tauGlobal: { median: q(tG, .5), p5: q(tG, .05), min: Math.min(...tG) }, perPolicy: perPol };
  L.push(`  ${k.padEnd(28)} tau OAT median ${q(tO, .5).toFixed(2)} min ${Math.min(...tO).toFixed(2)} | global median ${q(tG, .5).toFixed(2)} p5 ${q(tG, .05).toFixed(2)} min ${Math.min(...tG).toFixed(2)}`);
  L.push('     ' + POL.map(p => `${p.replace(/_.*$/, '').slice(0, 6)}${p.includes('panel') ? 'P' : ''}${p.includes('grandf') ? 'g' : p.includes('purge') ? 'p' : ''}${p.includes('365') && p.startsWith('PANEL') ? '' : ''}:${perPol[p].base}[${perPol[p].global5_95.join('-')}]`).join(' '));
}
// ---------- robust sign vs ASIS ----------
L.push('\n### Sign of paired delta vs ASIS over ALL runs (OAT 17 scenarios x 8 reps + 100 global draws); better/worse beyond tolerance');
for (const p of POL.concat('SPRINT_added_2xY')) { if (p === 'ASIS_logit') continue; out.robustSign[p] = {}; const cells = [];
  for (const [k, dir] of Object.entries(MET)) {
    let b = 0, w = 0, n = 0; for (const s of OAT.concat(GLO)) s.res[p].forEach((o, i) => { const a = s.res.ASIS_logit[i][k]; const d = dir * (o[k] - a); n++; if (d > tol(k, a)) b++; else if (d < -tol(k, a)) w++; });
    const cls = b / n >= .95 ? 'BETTER' : w / n >= .95 ? 'WORSE' : (b / n >= .8 ? 'better?' : w / n >= .8 ? 'worse?' : (b + w) / n < .2 ? 'equal' : 'mixed');
    out.robustSign[p][k] = { better: b / n, worse: w / n, n, cls }; cells.push(`${k.replace('EAimp_', '').replace('value_', 'v_')}=${cls}(${(100 * b / n).toFixed(0)}/${(100 * w / n).toFixed(0)})`);
  }
  L.push(`  ${p.padEnd(24)} ` + cells.join(' '));
}
// ---------- global drivers: Spearman correlation between parameter and delta vs ASIS ----------
const rk1 = a => ranks(a, -1); const spear = (a, b) => { const ra = rk1(a), rb = rk1(b); const ma = mean(ra), mb = mean(rb); let s = 0, sa = 0, sb = 0; for (let i = 0; i < a.length; i++) { s += (ra[i] - ma) * (rb[i] - mb); sa += (ra[i] - ma) ** 2; sb += (rb[i] - mb) ** 2; } return s / Math.sqrt(sa * sb); };
const parv = { r: s => s.sc.r, delay: s => Math.log(s.sc.delay), kappa: s => s.sc.kappa, effortCV: s => s.sc.effort === 'unit' ? 0 : s.sc.effort === 'proxy' ? 0.5 : s.sc.effort.cv, cap: s => s.sc.cap, calRecent: s => s.sc.cal === 'cal2021_22' ? 1 : 0 };
L.push('\n### Global drivers (100 joint draws): Spearman rho(parameter, delta vs ASIS); |rho| >= 0.3 shown');
for (const p of POL) { if (p === 'ASIS_logit') continue; out.globalDrivers[p] = {}; const cells = [];
  for (const k of ['EAimp_by90', 'EAimp_by365', 'EAimp_value_rating', 'EAimp_value_assertionUse', 'EAimp_legacyAcceptedShare']) {
    const d = GLO.map(s => s.res[p][0][k] - s.res.ASIS_logit[0][k]); const rr = {}; for (const [pn, f] of Object.entries(parv)) rr[pn] = spear(GLO.map(f), d);
    out.globalDrivers[p][k] = { rho: rr, deltaMedian: q(d, .5), delta5_95: [q(d, .05), q(d, .95)] };
    const big = Object.entries(rr).filter(([, v]) => Math.abs(v) >= .3).map(([n, v]) => `${n}${v.toFixed(2)}`).join(','); cells.push(`${k.replace('EAimp_', '')} med ${q(d, .5).toFixed(k.includes('value') ? 0 : 3)} [${q(d, .05).toFixed(k.includes('value') ? 0 : 3)},${q(d, .95).toFixed(k.includes('value') ? 0 : 3)}]${big ? ' {' + big + '}' : ''}`);
  }
  L.push(`  ${p.padEnd(24)} ` + cells.join(' | '));
}
fs.writeFileSync('results_rank.json', JSON.stringify(out, null, 1)); fs.writeFileSync('rank_log.txt', L.join('\n')); console.log(L.join('\n'));
