// D5req/W4 shared helpers: reuse ../A4 simulator (sim2.mjs), data (items_feat.json), logit fits (fit_logit.json).
// Adds: (i) outcome metrics NOT defined by the triage key, (ii) capacity scaling, (iii) calibration-window switch,
// (iv) a compact policy catalogue used by the sensitivity / ranking analyses.
import fs from 'fs';
import { ITEMS, TOK, TV, NOW, mulberry, ci, q } from './lib.mjs';
import { run, drawBeta, qualW, LVLW, pAccLvl } from './sim3.mjs'; // = ../A4/sim2.mjs + EDF discipline
export { ITEMS, TOK, TV, NOW, mulberry, ci, q, run, drawBeta };
const A4 = new URL('../../A4/', import.meta.url);
export const FIT = JSON.parse(fs.readFileSync(new URL('fit_logit.json', A4)));
const T1 = ['logAge', 'logRank', 'lvlA', 'lvlB', 'lvlD', 'lvlE', 'ratingC', 'ratingNA', 'type_DIAGNOSTIC', 'type_PROGNOSTIC', 'type_PREDISPOSING', 'type_ONCOGENIC', 'type_FUNCTIONAL', 'sameOrg', 'subPrior', 'selfSub'];
export function fitVec(key) { const f = FIT[key]; const cols = Object.keys(f.coef); const idx = T1.map(n => cols.indexOf(n));
  return { b: idx.map(i => i >= 0 ? f.coef[cols[i]] : 0), cov: idx.map(i => idx.map(j => (i >= 0 && j >= 0) ? f.cov[i][j] : 0)) }; }
export const CAL = { cal2021_22: 'cal2021_22_T1', cal2015_22: 'cal_T1', full2015_26_insample: 'full_T1' };

// ---------- downstream-use weight: evidence item cited by any CIViC assertion (offline, ../D5b/assertions_evidence.json)
const AE = JSON.parse(fs.readFileSync(new URL('../../../D5b/assertions_evidence.json', import.meta.url)));
const CITED = new Map(); for (const a of AE) for (const e of a.evidenceItems) CITED.set(e.id, (CITED.get(e.id) || 0) + 1);
export const WEIGHTS = {
  uniform: () => 1,
  rating: x => (x.rating ?? 3) / 3,              // rating only (missing -> neutral 3)
  assertionUse: x => 1 + 4 * (CITED.has(x.id) ? 1 : 0), // downstream use (cited by >=1 assertion): 5 vs 1
  level_KEY: x => LVLW[x.lvl] ?? 1,              // = triage key of PRIO_AB (reference only)
  levelXrating_A4: x => qualW(x),                 // = A4 quality weight (reference only)
};
export const ACC_ALL_OBS = ITEMS.filter(x => x.out).reduce((a, x) => a + (x.out === 'A'), 0) / ITEMS.filter(x => x.out).length; export const ACC_ALL = process.env.PIMP != null ? +process.env.PIMP : ACC_ALL_OBS;
// imputed eventual acceptance for items never decided in reality: level-free Bernoulli(p = overall accept share),
// fixed per (item, draw) so every policy sees the same imputation (common random numbers)
function hash32(a, b) { let h = Math.imul(a ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(b + 0x632be59b, 0xc2b2ae35); h ^= h >>> 13; h = Math.imul(h, 0x27d4eb2f); h ^= h >>> 16; return (h >>> 0) / 4294967296; }
export const eventuallyAccepted = (x, draw, mode) => x.out === 'A' ? true : x.out === 'R' ? false : (mode === 'obs' ? false : hash32(x.id, draw) < ACC_ALL);

// ---------- capacity scaling: thin / duplicate decision tokens inside the forward window (restored after each run)
const TOK0 = TOK.slice();
export function withCapacity(scale, seed, fn) {
  if (scale === 1) return fn();
  const rng = mulberry(seed); const pre = TOK0.filter(t => t.t < TV), win = TOK0.filter(t => t.t >= TV); let nw;
  if (scale < 1) nw = win.filter(() => rng() >= 1 - scale);
  else { nw = win.slice(); for (const t of win) if (rng() < scale - 1) nw.push({ ...t, t: Math.min(NOW - 1e-6, t.t + rng() * 7) }); }
  nw.sort((a, b) => a.t - b.t || a.realItem - b.realItem);
  TOK.length = 0; TOK.push(...pre, ...nw);
  try { return fn(); } finally { TOK.length = 0; TOK.push(...TOK0); }
}

// ---------- Kaplan–Meier helpers (event times t, censor flags) ----------
function km(times, events) { // returns step function S(t)
  const o = times.map((t, i) => [t, events[i]]).sort((a, b) => a[0] - b[0]); let n = o.length, S = 1; const st = [[0, 1]];
  for (let i = 0; i < o.length;) { const t = o[i][0]; let d = 0, c = 0; while (i < o.length && o[i][0] === t) { o[i][1] ? d++ : c++; i++; } if (d) { S *= 1 - d / n; st.push([t, S]); } n -= d + c; }
  return st;
}
const kmQ = (st, p) => { for (const [t, S] of st) if (1 - S >= p) return t; return null; };
const kmAt = (st, t) => { let S = 1; for (const [u, s] of st) { if (u > t) break; S = s; } return 1 - S; };

// ---------- outcome metrics independent of the triage key ----------
export function outcomes(r, draw = 0) {
  const end = r.end, start = r.start;
  const out = {};
  const nw = r.S.filter(s => !s.legacy), leg = r.S.filter(s => s.legacy);
  // waits of all new arrivals (decision = event), KM with administrative censoring at NOW
  { const t = nw.map(s => s.dec != null ? s.dec - s.arr0 : end - s.arr0), e = nw.map(s => s.dec != null); const st = km(t, e);
    out.new_KMmedWait = kmQ(st, .5); out.new_KMp75Wait = kmQ(st, .75); out.new_decBy90 = kmAt(st, 90); out.new_decBy365 = kmAt(st, 365);
    const el = nw.filter(s => s.arr0 <= end - 365); out.new_RMST365 = el.reduce((a, s) => a + Math.min(365, s.dec != null ? s.dec - s.arr0 : 365), 0) / el.length; }
  for (const mode of ['obs', 'imp']) {
    const isEA = s => eventuallyAccepted(s.x, draw, mode) && !s.lostFinal ? 'A' : (eventuallyAccepted(s.x, draw, mode) ? 'L' : null);
    // time-to-accept for eventually accepted NEW arrivals (lost-by-expiry items stay in the cohort as never accepted)
    const C = nw.filter(s => eventuallyAccepted(s.x, draw, mode));
    const t = C.map(s => (s.dec != null && !s.lostFinal) ? s.dec - s.arr0 : end - s.arr0), e = C.map(s => s.dec != null && !s.lostFinal);
    const st = km(t, e); const k = 'EA' + mode + '_';
    out[k + 'n'] = C.length; out[k + 'KMmedTTA'] = kmQ(st, .5); out[k + 'by90'] = kmAt(st, 90); out[k + 'by365'] = kmAt(st, 365);
    const el = C.filter(s => s.arr0 <= end - 365); out[k + 'RMST365'] = el.reduce((a, s) => a + Math.min(365, (s.dec != null && !s.lostFinal) ? s.dec - s.arr0 : 365), 0) / el.length;
    // legacy EA items (pending at window start): share accepted by end of window
    const L = leg.filter(s => eventuallyAccepted(s.x, draw, mode)); out[k + 'legacyAcceptedShare'] = L.filter(s => s.dec != null && !s.lostFinal).length / L.length;
    // value under weightings = accepted item-years available before NOW (all items present in window); delay = complement
    for (const [wn, w] of Object.entries(WEIGHTS)) {
      let v = 0, d = 0;
      for (const s of r.S) { if (!eventuallyAccepted(s.x, draw, mode)) continue; const from = Math.max(s.arr0, start);
        const acc = (s.dec != null && !s.lostFinal) ? s.dec : null; const ww = w(s.x);
        if (acc != null) { v += ww * (end - acc) / 365; d += ww * (acc - from) / 365; } else d += ww * (end - from) / 365; }
      out[k + 'value_' + wn] = v; out[k + 'delay_' + wn] = d;
    }
  }
  out.endPending = r.endSnap.ages.length; out.lostFinal = r.S.filter(s => s.lostFinal).length; out.resub = r.nResub; out.idleTokens = r.lostTok;
  return out;
}

// ---------- policy catalogue ----------
const sprintMonths = perYear => { const ms = []; for (let y = 2023; y <= 2026; y++) for (const m of perYear === 2 ? [2, 8] : [8]) { const a = Date.UTC(y, m, 1) / 864e5, b = Date.UTC(y, m + 1, 1) / 864e5; if (b <= NOW) ms.push([a, b]); } return ms; };
function sprintTokens(perYear, size, seed) { const rng = mulberry(seed); const t = []; for (const [a, b] of sprintMonths(perYear)) for (let i = 0; i < size; i++) t.push({ t: a + rng() * (b - a), user: 'SPRINT', org: null }); return t.sort((x, y) => x.t - y.t); }
export const POLICIES = {
  ASIS_logit: { disc: 'LOGIT' },
  FIFO_pool: { disc: 'FIFO' },
  LIFO_pool: { disc: 'LIFO' },
  PRIO_AB: { disc: 'LOGIT', prioAB: true },
  PANEL25_old365_quality: { disc: 'LOGIT', panel: { phi: .25, A: 365, order: 'quality' } },
  PANEL10_old365_oldest: { disc: 'LOGIT', panel: { phi: .10, A: 365, order: 'oldest' } },
  SKILL_pool_affinity: { disc: 'SKILL' },
  OWN_strict: { route: 'own', ownDisc: 'FIFO' },
  OWN_steal: { route: 'own', ownDisc: 'FIFO', steal: true },
  EXP365_grandf: { disc: 'LOGIT', expireT: 365, grandfather: true, usesResub: true },
  EXP365_purge: { disc: 'LOGIT', expireT: 365, grandfather: false, usesResub: true },
  EDF365_noexpiry: { disc: 'EDF', edfD: 365 },
  EDF90_noexpiry: { disc: 'EDF', edfD: 90 },
  EDF90_panel20_oldest: { disc: 'EDF', edfD: 90, panel: { phi: .20, A: 365, order: 'oldest' } },
  SPRINT_added_2xY: { disc: 'LOGIT', sprintPY: 2, extraCapacity: true },
};
export const BASE = { r: .25, delay: 30, kappa: 1, effort: 'unit', cap: 1, cal: 'cal2021_22' };
export function runPolicy(name, sc, rep) {
  const p = POLICIES[name]; const fv = fitVec(CAL[sc.cal]);
  const opt = { ...p, tier: 1, beta: drawBeta(fv, mulberry(700 + rep)), start: TV, effort: sc.effort, kappa: sc.kappa };
  if (p.usesResub) { opt.resub = sc.r; opt.resubDelay = sc.delay; }
  if (p.sprintPY) opt.sprint = { tokens: sprintTokens(p.sprintPY, 60, 33 + rep), A: 365, order: 'quality' };
  return withCapacity(sc.cap, 9100 + rep, () => run(opt, 300 + rep));
}
