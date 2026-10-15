// Task 3: Simod-style validation of the as-is model on the 2023-01-01..2026-10-07 hold-out.
// Measures: EMD (Wasserstein-1) of cycle times (raw days and log1p days), relative-event (age-at-decision) EMD,
// pending-age EMD at year ends, absolute event distribution (hour/day-of-week/calendar-day) of decision events,
// n-gram distance of case status sequences (monthly P/D) and of the decision stream (age bucket of decided item),
// plus KS. Baselines as in ../A4/validate.mjs. Noise floor: bootstrap of the observed log against itself.
import fs from 'fs';
import { ITEMS, TOK, TV, NOW, mulberry, ci, run, drawBeta, fitVec } from './w4lib.mjs';
import { ks } from '../A4/lib.mjs';
const day = s => Date.parse(s) / 864e5;
const CK = [day('2023-12-31'), day('2024-12-31'), day('2025-12-31')];
const BYID = new Map(ITEMS.map(x => [x.id, x]));
// ---------- distances ----------
function emd(a, b) {
  a = a.slice().sort((x, y) => x - y); b = b.slice().sort((x, y) => x - y);
  const pts = [...new Set([...a, ...b])].sort((x, y) => x - y);
  let i = 0, j = 0, s = 0;
  for (let k = 0; k < pts.length - 1; k++) { const v = pts[k]; while (i < a.length && a[i] <= v) i++; while (j < b.length && b[j] <= v) j++; s += Math.abs(i / a.length - j / b.length) * (pts[k + 1] - v); }
  return s;
}
const L1 = a => a.map(v => Math.log1p(Math.max(0, v)));
function hist(vals, nb, f) { const h = new Array(nb).fill(0); for (const v of vals) h[f(v)]++; const n = vals.length || 1; return h.map(c => c / n); }
const tvd = (h1, h2) => h1.reduce((s, v, i) => s + Math.abs(v - h2[i]), 0) / 2; // total-variation distance
function ngrams(seqs, n) { const m = new Map(); for (const s of seqs) for (let i = 0; i + n <= s.length; i++) { const g = s.slice(i, i + n).join('|'); m.set(g, (m.get(g) || 0) + 1); } return m; }
function ngDist(A, B) { const keys = new Set([...A.keys(), ...B.keys()]); let d = 0, t = 0; for (const k of keys) { const a = A.get(k) || 0, b = B.get(k) || 0; d += Math.abs(a - b); t += a + b; } return t ? d / t : 0; }
const drop = m => { const n = new Map(m); n.delete('P|P|P'); return n; };
// ---------- trace representations ----------
const monthEnds = [];
{ let y = 2023, mo = 0; while (true) { const t = Date.UTC(y, mo + 1, 0) / 864e5; if (t > NOW) break; monthEnds.push(t); mo++; if (mo === 12) { mo = 0; y++; } } }
function statusSeq(arr, dec, legacy) { const s = [legacy ? '^L' : '^N']; for (const m of monthEnds) { if (m < arr) continue; s.push(dec != null && dec <= m ? 'D' : 'P'); } s.push('$'); return s; }
const ageSym = a => a < 30 ? 'a<30' : a < 365 ? 'a<1y' : a < 1095 ? 'a<3y' : 'a3y+';
function features(cases, decStream) { // cases: [{arr, dec, legacy}], decStream: [{t, age}] in token order
  const nw = cases.filter(c => !c.legacy);
  const cyc = nw.filter(c => c.dec != null).map(c => c.dec - c.arr);
  const cycOpen = nw.map(c => (c.dec ?? NOW) - c.arr);
  const ageDec = decStream.map(d => d.age); const arrDec = decStream.map(d => d.t - d.age);
  const pend = [...CK, NOW].map(c => cases.filter(x => x.arr <= c && (x.dec == null || x.dec > c)).map(x => c - x.arr));
  return { cyc, cycOpen, ageDec, arrDec, pend, times: decStream.map(d => d.t), seqs: cases.map(c => statusSeq(c.arr, c.dec, c.legacy)), stream: decStream.map(d => ageSym(d.age)) };
}
const F_HOUR = t => Math.min(23, Math.floor((t - Math.floor(t)) * 24)), F_DOW = t => ((Math.floor(t) + 4) % 7 + 7) % 7;
function score(P, O) {
  const r = {};
  r.EMD_cycle_days = emd(P.cyc, O.cyc); r.EMD_cycle_log = emd(L1(P.cyc), L1(O.cyc)); r.KS_cycle = ks(P.cyc, O.cyc);
  r.EMD_cycleInclOpen_days = emd(P.cycOpen, O.cycOpen); r.EMD_cycleInclOpen_log = emd(L1(P.cycOpen), L1(O.cycOpen));
  r.EMD_ageAtDecision_days = emd(P.ageDec, O.ageDec); r.EMD_ageAtDecision_log = emd(L1(P.ageDec), L1(O.ageDec)); r.KS_ageAtDecision = ks(P.ageDec, O.ageDec);
  r.EMD_arrivalDateOfDecided_days = emd(P.arrDec, O.arrDec);
  r.EMD_pendingAge_mean_days = P.pend.reduce((s, a, i) => s + emd(a, O.pend[i]), 0) / P.pend.length;
  r.KS_pending_mean = P.pend.reduce((s, a, i) => s + ks(a, O.pend[i]), 0) / P.pend.length;
  if (P.times) { r.AED_hour_TVD = tvd(hist(P.times, 24, F_HOUR), hist(O.times, 24, F_HOUR)); r.AED_dow_TVD = tvd(hist(P.times, 7, F_DOW), hist(O.times, 7, F_DOW)); r.AED_calendar_EMD_days = emd(P.times, O.times); }
  if (P.seqs) { r.NGRAM3_status = ngDist(ngrams(P.seqs, 3), ngrams(O.seqs, 3)); r.NGRAM3_status_noPPP = ngDist(drop(ngrams(P.seqs, 3)), drop(ngrams(O.seqs, 3))); }
  if (P.stream) { r.NGRAM2_decStream = ngDist(ngrams([P.stream], 2), ngrams([O.stream], 2)); r.NGRAM3_decStream = ngDist(ngrams([P.stream], 3), ngrams([O.stream], 3)); }
  return r;
}
// ---------- observed ----------
const obsCases = ITEMS.filter(x => x.arr <= NOW && (x.dec == null || x.dec >= TV)).map(x => ({ arr: x.arr, dec: x.dec, legacy: x.arr < TV }));
const obsStream = TOK.filter(t => t.t >= TV).map(t => ({ t: t.t, age: t.t - BYID.get(t.realItem).arr }));
const O = features(obsCases, obsStream);
// ---------- simulated ----------
function simFeat(r) {
  const cases = r.S.map(s => ({ arr: s.arr0, dec: s.dec, legacy: s.legacy }));
  const st = r.S.filter(s => s.dec != null && s.dec >= TV).sort((a, b) => a.dec - b.dec).map(s => ({ t: s.dec, age: s.dec - s.arr0 }));
  return features(cases, st);
}
function observedU() { const arr = ITEMS.slice(); let ai = 0; const Q = []; const us = [];
  for (const tk of TOK) { while (ai < arr.length && arr[ai].arr <= tk.t) Q.push(arr[ai++]); const idx = Q.findIndex(x => x.id === tk.realItem); const L = Q.length; us.push({ t: tk.t, u: L > 1 ? (L - 1 - idx) / (L - 1) : 0 }); Q.splice(idx, 1); } return us; }
const U = observedU(); const uCal = U.filter(x => x.t < TV).map(x => x.u); const uRec = U.filter(x => x.t >= day('2021-01-01') && x.t < TV).map(x => x.u);
const REPS = +(process.argv[2] || 30);
const MODELS = {
  FIFO: { opt: { disc: 'FIFO' }, reps: 1 }, LIFO: { opt: { disc: 'LIFO' }, reps: 1 }, RANDOM: { opt: { disc: 'RANDOM' }, reps: REPS },
  RANKU_2015_22: { opt: { disc: 'RANKU', uDist: uCal }, reps: REPS }, RANKU_2021_22: { opt: { disc: 'RANKU', uDist: uRec }, reps: REPS },
  LOGIT_T1_cal2015_22: { logit: 'cal_T1', reps: REPS }, LOGIT_T1_cal2021_22_ASIS: { logit: 'cal2021_22_T1', reps: REPS },
};
const out = { design: { holdout: '2023-01-01..2026-10-07', calibration: '<2023', tokens: obsStream.length, newArrivals: obsCases.filter(c => !c.legacy).length, legacyPending: obsCases.filter(c => c.legacy).length, reps: REPS,
  note: 'capacity tokens (decision timestamps) and arrivals are replayed from the log, so absolute event distributions of decisions/arrivals are identical by construction; time realism is tested through relative (age) measures' }, models: {} };
for (const [name, m] of Object.entries(MODELS)) {
  const sc = [];
  for (let k = 0; k < m.reps; k++) {
    let opt = m.opt; if (m.logit) { const fv = fitVec(m.logit); opt = { disc: 'LOGIT', tier: 1, beta: drawBeta(fv, mulberry(9000 + k)) }; }
    const r = run({ ...opt, start: TV, checkpoints: CK }, 100 + k); sc.push(score(simFeat(r), O));
  }
  out.models[name] = Object.fromEntries(Object.keys(sc[0]).map(key => [key, ci(sc.map(s => s[key]))])); console.error('done', name);
}
// naive persistence (2021-22 distributions shifted to the hold-out; no case-level traces)
{ const t0 = day('2021-01-01'); const recTok = TOK.filter(t => t.t >= t0 && t.t < TV); const recNew = ITEMS.filter(x => x.arr >= t0 && x.arr < TV);
  const P = { cyc: recNew.filter(x => x.dec != null && x.dec < TV).map(x => x.dec - x.arr), cycOpen: recNew.map(x => Math.min(x.dec ?? TV, TV) - x.arr), ageDec: recTok.map(t => t.t - BYID.get(t.realItem).arr),
    arrDec: recTok.map(t => BYID.get(t.realItem).arr + (TV - t0)), pend: [0, 1, 2, 3].map(() => ITEMS.filter(x => x.arr < TV && (x.dec == null || x.dec >= TV)).map(x => TV - x.arr)),
    stream: recTok.map(t => ageSym(t.t - BYID.get(t.realItem).arr)) };
  const s = score(P, O); out.models.NAIVE_persistence_2021_22 = Object.fromEntries(Object.entries(s).map(([k, v]) => [k, [v, v, v]])); }
// noise floor: bootstrap observed vs observed (cases resampled; decision stream block-bootstrapped, block 50)
{ const rng = mulberry(4242); const B = +(process.argv[3] || 100); const sc = [];
  for (let b = 0; b < B; b++) {
    const cs = obsCases.map(() => obsCases[Math.floor(rng() * obsCases.length)]);
    const st = []; while (st.length < obsStream.length) { const i0 = Math.floor(rng() * (obsStream.length - 50)); for (let i = i0; i < i0 + 50 && st.length < obsStream.length; i++) st.push(obsStream[i]); }
    sc.push(score(features(cs, st), O));
  }
  out.models.NOISE_FLOOR_bootstrap_observed = Object.fromEntries(Object.keys(sc[0]).map(key => [key, ci(sc.map(s => s[key]))])); }
fs.writeFileSync('results_simod.json', JSON.stringify(out, null, 1));
const keys = Object.keys(out.models.LOGIT_T1_cal2021_22_ASIS);
for (const key of keys) { console.log('##', key); for (const [n, v] of Object.entries(out.models)) if (v[key]) console.log('  ', n.padEnd(32), v[key][0].toFixed(3), `[${v[key][1].toFixed(3)}, ${v[key][2].toFixed(3)}]`); }
