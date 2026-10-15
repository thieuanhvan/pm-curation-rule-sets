// identical measures for every log; input: cases [{id, arr, dec|null, out, sub, decU}]
import fs from 'fs';
const D = 864e5, Y = 365.25 * D;
const q = (a, p) => { a = a.filter(Number.isFinite).sort((x, y) => x - y); return a.length ? +a[Math.floor(p * (a.length - 1))].toFixed(1) : null; };
const gini = v => { v = v.slice().sort((a, b) => a - b); const n = v.length, s = v.reduce((a, b) => a + b, 0); if (!n || !s) return null; let c = 0; v.forEach((x, i) => c += (2 * (i + 1) - n - 1) * x); return +(c / (n * s)).toFixed(3); };
export function analyze(cases, NOW, {decidedOuts = ['acc', 'rej', 'closed', 'wd']} = {}) {
  cases = cases.filter(c => Number.isFinite(c.arr) && c.arr <= NOW);
  const decd = cases.filter(c => c.dec != null && decidedOuts.includes(c.out));
  const pend = cases.filter(c => c.dec == null);
  const R = {n: cases.length, outcomes: {}, span: [new Date(Math.min(...cases.map(c => c.arr))).toISOString().slice(0, 10), new Date(NOW).toISOString().slice(0, 10)]};
  for (const c of cases) R.outcomes[c.out] = (R.outcomes[c.out] || 0) + 1;
  const ttd = o => { const d = decd.filter(c => !o || c.out === o).map(c => (c.dec - c.arr) / D); return {n: d.length, med: q(d, .5), p90: q(d, .9), le1d: d.length ? +(d.filter(x => x <= 1).length / d.length).toFixed(3) : null}; };
  R.ttd_all = ttd(); R.ttd_acc = ttd('acc'); R.ttd_rej = ttd('rej');
  const ages = pend.map(c => (NOW - c.arr) / D);
  R.backlog = {n: pend.length, share: +(pend.length / cases.length).toFixed(3), ageMed: q(ages, .5), ageP90: q(ages, .9), gt2y: ages.length ? +(ages.filter(a => a > 730).length / ages.length).toFixed(3) : null};
  // hazard: P(decided within next 365 d | undecided at age a), only items observable for a+365 d
  R.hazard = {};
  for (const a of [30, 365, 4 * 365]) { const el = cases.filter(c => c.arr + (a + 365) * D <= NOW && (c.dec == null || c.dec > c.arr + a * D));
    const hit = el.filter(c => c.dec != null && c.dec <= c.arr + (a + 365) * D); R.hazard['age' + a + 'd'] = {n: el.length, p: el.length ? +(hit.length / el.length).toFixed(3) : null}; }
  // yearly flow
  const yrs = {}; const yr = t => new Date(t).getUTCFullYear();
  for (const c of cases) { (yrs[yr(c.arr)] ||= {sub: 0, dec: 0}).sub++; if (c.dec != null) (yrs[yr(c.dec)] ||= {sub: 0, dec: 0}).dec++; }
  for (const y of Object.keys(yrs)) { const end = Date.UTC(+y + 1, 0, 1); const pe = cases.filter(c => c.arr < end && (c.dec == null || c.dec >= end)); yrs[y].pendingEnd = pe.length; yrs[y].pendMedAgeD = q(pe.map(c => (Math.min(end, NOW) - c.arr) / D), .5); }
  R.by_year = yrs;
  const last3 = [2023, 2024, 2025].map(y => yrs[y] || {sub: 0, dec: 0}); R.flow_2023_25 = {subPerY: +(last3.reduce((s, x) => s + x.sub, 0) / 3).toFixed(1), decPerY: +(last3.reduce((s, x) => s + x.dec, 0) / 3).toFixed(1)};
  // Little: L = lambda W -> implied wait for backlog
  R.little_impliedWaitY = R.flow_2023_25.decPerY ? +(pend.length / R.flow_2023_25.decPerY).toFixed(2) : null;
  // four eyes and concentration (only where decider known)
  const known = decd.filter(c => c.decU); 
  if (known.length) { const self = known.filter(c => c.decU === c.sub).length; R.fourEyes = {n: known.length, other: +(1 - self / known.length).toFixed(4), self};
    const cnt = {}; for (const c of known) cnt[c.decU] = (cnt[c.decU] || 0) + 1; const v = Object.values(cnt).sort((a, b) => b - a);
    R.deciders = {n: v.length, gini: gini(v), top5share: +(v.slice(0, 5).reduce((a, b) => a + b, 0) / known.length).toFixed(3), lt10: v.filter(x => x < 10).length}; }
  // service position: u = (# queued items newer than chosen)/(L-1); 1 = oldest (FIFO), 0 = newest (LIFO)
  const toks = decd.slice().sort((a, b) => a.dec - b.dec); const arr = cases.slice().sort((a, b) => a.arr - b.arr);
  let ai = 0; const queue = []; const us = [];
  for (const tk of toks) { while (ai < arr.length && arr[ai].arr <= tk.dec) queue.push(arr[ai++]);
    const idx = queue.indexOf(tk); if (idx < 0) continue; const L = queue.length; if (L > 1) us.push({y: yr(tk.dec), u: (L - 1 - idx) / (L - 1), L}); queue.splice(idx, 1); }
  const pos = {}; for (const x of us) { (pos[x.y] ||= []).push(x); }
  R.position = {all: {mean: +(us.reduce((s, x) => s + x.u, 0) / us.length).toFixed(3), newest10: +(us.filter(x => x.u <= .1).length / us.length).toFixed(3)}, by_year: Object.fromEntries(Object.entries(pos).map(([y, a]) => [y, {n: a.length, mean: +(a.reduce((s, x) => s + x.u, 0) / a.length).toFixed(2), newest10: +(a.filter(x => x.u <= .1).length / a.length).toFixed(2), Lmed: q(a.map(x => x.L), .5)}]))};
  return R;
}
