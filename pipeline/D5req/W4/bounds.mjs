// Task 4: policy bounds under fixed capacity (unit effort, pooled, kappa = 1, real token instants 2023-01-01..2026-10-07).
// Oracle schedules that no real policy can beat on a given outcome:
//  (a) max share of new arrivals decided within d: EDF on deadline arr+d (equal-length windows -> greedy optimal)
//  (b) the same restricted to eventually-accepted items (oracle knows the outcome)
//  (c) max / min value (accepted item-years before NOW) under weight w: greedy max/min w at each token
//      (optimal by exchange: multiplier NOW - t decreases in t and availability only grows)
//  (d) frontier: share s of tokens reserved for legacy (oldest first), rest EDF(365) on new arrivals
import fs from 'fs';
import { ITEMS, TOK, TV, NOW, withCapacity, eventuallyAccepted, WEIGHTS, ci } from './w4lib.mjs';
const res = {};
function setup() {
  const toks = TOK.filter(t => t.t >= TV);
  const items = ITEMS.filter(x => x.arr <= NOW && (x.dec == null || x.dec >= TV)).map(x => ({ x, arr: x.arr, legacy: x.arr < TV, dec: null }));
  items.sort((a, b) => a.arr - b.arr); return { toks, items };
}
// generic greedy: pick(avail, t) returns index into avail
function sched(pick) {
  const { toks, items } = setup(); const avail = []; let ai = 0;
  for (const tk of toks) { while (ai < items.length && items[ai].arr <= tk.t) avail.push(items[ai++]); if (!avail.length) continue; const i = pick(avail, tk.t); if (i < 0) continue; avail[i].dec = tk.t; avail.splice(i, 1); }
  return items;
}
function evalItems(items, draw) {
  const nw = items.filter(s => !s.legacy); const o = {};
  for (const d of [90, 365]) { const el = nw.filter(s => s.arr <= NOW - d); o['new_by' + d] = el.filter(s => s.dec != null && s.dec - s.arr <= d).length / el.length;
    const ea = el.filter(s => eventuallyAccepted(s.x, draw, 'imp')); o['EAimp_by' + d] = ea.filter(s => s.dec != null && s.dec - s.arr <= d).length / ea.length; }
  const L = items.filter(s => s.legacy && eventuallyAccepted(s.x, draw, 'imp')); o.legacyAcceptedShare = L.filter(s => s.dec != null).length / L.length;
  for (const [wn, w] of Object.entries(WEIGHTS)) o['value_' + wn] = items.reduce((a, s) => a + (s.dec != null && eventuallyAccepted(s.x, draw, 'imp') ? w(s.x) * (NOW - s.dec) / 365 : 0), 0);
  o.decisions = items.filter(s => s.dec != null).length; o.decNew = nw.filter(s => s.dec != null).length; o.backlogEnd = items.length - o.decisions;
  return o;
}
const edf = (d, filt) => (avail, t) => { // oldest item still inside its window (arr + d >= t); fallback: oldest legacy, then anything
  let best = -1; for (let i = 0; i < avail.length; i++) { const s = avail[i]; if (s.legacy || (filt && !filt(s))) continue; if (s.arr + d >= t) { best = i; break; } }
  if (best >= 0) return best; for (let i = 0; i < avail.length; i++) if (avail[i].legacy) return i; return 0; };
for (const cap of [0.75, 1, 1.25]) withCapacity(cap, 9100, () => {
  const R = {}; const DR = [0, 1, 2, 3, 4];
  const agg = f => { const a = DR.map(f); const k = Object.keys(a[0]); return Object.fromEntries(k.map(key => [key, ci(a.map(o => o[key]))])); };
  R.tokens = TOK.filter(t => t.t >= TV).length;
  R.EDF90 = agg(d => evalItems(sched(edf(90)), d));
  R.EDF365 = agg(d => evalItems(sched(edf(365)), d));
  R.EDF90_oracleEA = agg(d => evalItems(sched(edf(90, s => eventuallyAccepted(s.x, d, 'imp'))), d));
  R.EDF365_oracleEA = agg(d => evalItems(sched(edf(365, s => eventuallyAccepted(s.x, d, 'imp'))), d));
  R.LEGACY_first = agg(d => evalItems(sched((av) => { const i = av.findIndex(s => s.legacy && eventuallyAccepted(s.x, d, 'imp')); return i >= 0 ? i : 0; }), d));
  for (const wn of Object.keys(WEIGHTS)) {
    const w = WEIGHTS[wn];
    R['VALUEMAX_' + wn] = agg(d => evalItems(sched((av) => { let b = 0, bv = -1; for (let i = 0; i < av.length; i++) { const v = eventuallyAccepted(av[i].x, d, 'imp') ? w(av[i].x) : 0; if (v > bv) { bv = v; b = i; } } return b; }), d));
    R['VALUEMIN_' + wn] = agg(d => evalItems(sched((av) => { let b = 0, bv = Infinity; for (let i = 0; i < av.length; i++) { const v = eventuallyAccepted(av[i].x, d, 'imp') ? w(av[i].x) : 0; if (v < bv) { bv = v; b = i; } } return b; }), d));
  }
  // frontier: reserve share s of tokens (deterministic interleave) for legacy oldest-first, rest EDF(365) on new
  R.frontier = [];
  for (const D of [365, 90]) for (const s of [0, .1, .2, .3, .4, .5, .6, .8, 1]) {
    R.__D = D; let acc = 0; const pick = (av, t) => { acc += s; if (acc >= 1 - 1e-9) { acc -= 1; const i = av.findIndex(z => z.legacy); if (i >= 0) return i; } return edf(R.__D)(av, t); };
    const o = agg(d => { acc = 0; return evalItems(sched(pick), d); }); R.frontier.push({ D, legacyShareOfTokens: s, new_by365: o.new_by365, new_by90: o.new_by90, EAimp_by365: o.EAimp_by365, legacyAcceptedShare: o.legacyAcceptedShare, value_uniform: o.value_uniform });
  }
  res['cap' + cap] = R; console.error('cap', cap, 'done');
});
fs.writeFileSync('results_bounds.json', JSON.stringify(res, null, 1));
const f = a => a[0].toFixed(3);
for (const [c, R] of Object.entries(res)) {
  console.log('==', c, 'tokens', R.tokens);
  for (const [k, o] of Object.entries(R)) { if (k === 'tokens' || k === 'frontier' || k === '__D') continue; console.log('  ', k.padEnd(30), 'new90', f(o.new_by90), 'new365', f(o.new_by365), 'EA90', f(o.EAimp_by90), 'EA365', f(o.EAimp_by365), 'legAcc', f(o.legacyAcceptedShare), 'vU', o.value_uniform[0].toFixed(0), 'vR', o.value_rating[0].toFixed(0), 'vAs', o.value_assertionUse[0].toFixed(0), 'vKEY', o.value_level_KEY[0].toFixed(0), 'backlog', o.backlogEnd[0]); }
  for (const p of R.frontier) console.log('   frontier D', p.D, 's=', p.legacyShareOfTokens, 'new365', f(p.new_by365), 'new90', f(p.new_by90), 'EA365', f(p.EAimp_by365), 'legAcc', f(p.legacyAcceptedShare), 'vU', p.value_uniform[0].toFixed(0));
}
