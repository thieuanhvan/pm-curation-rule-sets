// Temporal validation of the as-is model: calibrate discipline on 2015-2022 tokens, predict 2023-01-01..2026-10-07.
// Conditional mode: real queue state at 2023-01-01, real arrivals and real token stream (capacity) are given;
// the model must predict WHICH items are decided (age at decision), waiting-time quantiles of new arrivals and
// the pending-age distribution at year ends. (Backlog counts are identical by construction: see Lemma 1.)
import fs from 'fs';
import { ITEMS, TOK, TV, NOW, day, q, ks, mean, ci, mulberry } from './lib.mjs';
import { run, drawBeta } from './sim2.mjs';
const FIT = JSON.parse(fs.readFileSync('fit_logit.json'));
const T1 = ['logAge', 'logRank', 'lvlA', 'lvlB', 'lvlD', 'lvlE', 'ratingC', 'ratingNA', 'type_DIAGNOSTIC', 'type_PROGNOSTIC', 'type_PREDISPOSING', 'type_ONCOGENIC', 'type_FUNCTIONAL', 'sameOrg', 'subPrior', 'selfSub'];
const T2 = [...T1, 'act30', 'touched'];
function fitVec(key, names) { const f = FIT[key]; const cols = Object.keys(f.coef); const idx = names.map(n => cols.indexOf(n));
  const b = idx.map(i => i >= 0 ? f.coef[cols[i]] : 0); const cov = idx.map(i => idx.map(j => (i >= 0 && j >= 0) ? f.cov[i][j] : 0)); return { b, cov }; }
const CK = [day('2023-12-31'), day('2024-12-31'), day('2025-12-31')];
const CKN = ['2023-12-31', '2024-12-31', '2025-12-31', '2026-10-07'];
// ---------- observed ----------
const obsAgeDec = TOK.filter(t => t.t >= TV).map(t => t.t - ITEMS.find(x => x.id === t.realItem).arr);
const pendObs = c => ITEMS.filter(x => x.arr <= c && (x.dec == null || x.dec > c)).map(x => c - x.arr);
const obsPend = [...CK, NOW].map(pendObs);
const newItems = ITEMS.filter(x => x.arr >= TV);
const obsWithin = d => { const el = newItems.filter(x => x.arr <= NOW - d); return el.filter(x => x.dec != null && x.dec - x.arr <= d).length / el.length; };
const obsNewWait = newItems.filter(x => x.dec != null).map(x => x.dec - x.arr);
const OBS = { ageDec: obsAgeDec, pend: obsPend, within: { 7: obsWithin(7), 30: obsWithin(30), 90: obsWithin(90), 365: obsWithin(365) }, newWait: obsNewWait };
// ---------- observed discipline (rank u) for RANKU baselines ----------
function observedU() { const arr = ITEMS.slice(); let ai = 0; const Q = []; const us = [];
  for (const tk of TOK) { while (ai < arr.length && arr[ai].arr <= tk.t) Q.push(arr[ai++]); const idx = Q.findIndex(x => x.id === tk.realItem); const L = Q.length; us.push({ t: tk.t, u: L > 1 ? (L - 1 - idx) / (L - 1) : 0 }); Q.splice(idx, 1); } return us; }
const U = observedU(); const uCal = U.filter(x => x.t < TV).map(x => x.u); const uRec = U.filter(x => x.t >= day('2021-01-01') && x.t < TV).map(x => x.u);
// ---------- scoring ----------
const PS = Array.from({ length: 19 }, (_, i) => (i + 1) * .05);
const lq = (a, p) => Math.log10(1 + q(a, p));
function score(pred) { // pred: {ageDec, pend[4], within{}, newWait}
  const o = {};
  o.KS_ageAtDecision = ks(pred.ageDec, OBS.ageDec);
  for (const p of [.1, .25, .5, .75, .9]) o['AE_q' + p * 100 + '_ageAtDecision_d'] = Math.abs(q(pred.ageDec, p) - q(OBS.ageDec, p));
  o.RMSE_log10quantiles_ageAtDecision = Math.sqrt(mean(PS.map(p => (lq(pred.ageDec, p) - lq(OBS.ageDec, p)) ** 2)));
  o.KS_newWaitDecided = pred.newWait && pred.newWait.length ? ks(pred.newWait, OBS.newWait) : null;
  o.AE_median_newWait_d = pred.newWait && pred.newWait.length ? Math.abs(q(pred.newWait, .5) - q(OBS.newWait, .5)) : null;
  o.AE_p90_newWait_d = pred.newWait && pred.newWait.length ? Math.abs(q(pred.newWait, .9) - q(OBS.newWait, .9)) : null;
  if (pred.within) for (const d of [7, 30, 90, 365]) o['AE_within' + d] = Math.abs(pred.within[d] - OBS.within[d]);
  if (pred.pend) { pred.pend.forEach((a, i) => { o['KS_pending_' + CKN[i]] = ks(a, OBS.pend[i]); o['AE_pendMedAge_' + CKN[i]] = Math.abs(q(a, .5) - q(OBS.pend[i], .5)); o['AE_pendP90Age_' + CKN[i]] = Math.abs(q(a, .9) - q(OBS.pend[i], .9)); });
    o.KS_pending_mean = mean(pred.pend.map((a, i) => ks(a, OBS.pend[i]))); }
  return o;
}
function simPred(r) {
  const ageDec = r.S.filter(s => s.dec != null && s.dec >= TV).map(s => s.dec - s.arr0);
  const pend = [...CK.map(c => r.snaps[c].ages), r.endSnap.ages];
  const nw = r.S.filter(s => !s.legacy); const within = {}; for (const d of [7, 30, 90, 365]) { const el = nw.filter(s => s.arr0 <= NOW - d); within[d] = el.filter(s => s.dec != null && s.dec - s.arr0 <= d).length / el.length; }
  return { ageDec, pend, within, newWait: nw.filter(s => s.dec != null).map(s => s.dec - s.arr0), pendMed: pend.map(a => q(a, .5)), q50: q(ageDec, .5), q90: q(ageDec, .9), nwMed: q(nw.filter(s => s.dec != null).map(s => s.dec - s.arr0), .5) };
}
const REPS = +(process.argv[2] || 40);
const models = {
  FIFO: { opt: { disc: 'FIFO' }, reps: 1 }, LIFO: { opt: { disc: 'LIFO' }, reps: 1 }, RANDOM: { opt: { disc: 'RANDOM' }, reps: REPS },
  RANKU_cal2015_22: { opt: { disc: 'RANKU', uDist: uCal }, reps: REPS }, RANKU_recent2021_22: { opt: { disc: 'RANKU', uDist: uRec }, reps: REPS },
  LOGIT_ageRank_cal: { logit: ['cal_age_rank', T1, 1], reps: REPS }, LOGIT_T1_cal: { logit: ['cal_T1', T1, 1], reps: REPS },
  LOGIT_T1_cal2021_22: { logit: ['cal2021_22_T1', T1, 1], reps: REPS }, LOGIT_T2_cal_nowcast: { logit: ['cal_T2', T2, 2], reps: REPS },
};
const out = { design: { calibration: '2015-06..2022-12 tokens', validation: '2023-01-01..2026-10-07', tokensValidation: OBS.ageDec.length, newArrivalsValidation: newItems.length, pendingAtStart: pendObs(TV).length, reps: REPS, note: 'logit reps draw beta from N(beta_hat, V) (parameter + Gumbel choice noise); intervals = 2.5-97.5 % over reps' },
  observed: { ageDec_q: [.1, .25, .5, .75, .9].map(p => q(OBS.ageDec, p)), within: OBS.within, newWait_q50: q(OBS.newWait, .5), newWait_q90: q(OBS.newWait, .9), pending: OBS.pend.map((a, i) => ({ at: CKN[i], n: a.length, med: q(a, .5), p90: q(a, .9), over365: a.filter(z => z > 365).length / a.length })) }, models: {} };
for (const [name, m] of Object.entries(models)) {
  const scores = []; const preds = [];
  for (let k = 0; k < m.reps; k++) {
    let opt = m.opt;
    if (m.logit) { const fv = fitVec(m.logit[0], m.logit[1]); const beta = m.reps > 1 ? drawBeta(fv, mulberry(9000 + k)) : fv.b; opt = { disc: 'LOGIT', beta, tier: m.logit[2] }; }
    const r = run({ ...opt, start: TV, checkpoints: CK }, 100 + k); const p = simPred(r); preds.push(p); scores.push(score(p));
  }
  const agg = {}; for (const key of Object.keys(scores[0])) agg[key] = ci(scores.map(s => s[key]));
  agg.pred_ageDec_q50 = ci(preds.map(p => p.q50)); agg.pred_ageDec_q90 = ci(preds.map(p => p.q90)); agg.pred_newWait_q50 = ci(preds.map(p => p.nwMed));
  for (const d of [7, 30, 90, 365]) agg['pred_within' + d] = ci(preds.map(p => p.within[d]));
  agg.pred_pendMed = CKN.map((c, i) => ci(preds.map(p => p.pendMed[i])));
  out.models[name] = agg; console.log(name, 'KSage', agg.KS_ageAtDecision.map(v => v?.toFixed(3)).join('/'), 'RMSElogq', agg.RMSE_log10quantiles_ageAtDecision[0].toFixed(3), 'KSpend', agg.KS_pending_mean[0].toFixed(3), 'AEw90', agg.AE_within90[0].toFixed(3));
}
// naive persistence baselines (no simulation)
const recTok = TOK.filter(t => t.t >= day('2021-01-01') && t.t < TV).map(t => t.t - ITEMS.find(x => x.id === t.realItem).arr);
const recNew = ITEMS.filter(x => x.arr >= day('2021-01-01') && x.arr < TV);
const recNewWait = recNew.filter(x => x.dec != null && x.dec < TV).map(x => x.dec - x.arr);
const recWithin = d => { const el = recNew.filter(x => x.arr <= TV - d); return el.filter(x => x.dec != null && x.dec - x.arr <= d).length / el.length; };
const pend22 = pendObs(TV - 1e-6);
const naive = score({ ageDec: recTok, pend: [pend22, pend22, pend22, pend22], within: { 7: recWithin(7), 30: recWithin(30), 90: recWithin(90), 365: recWithin(365) }, newWait: recNewWait });
out.models.NAIVE_persistence_2021_22 = Object.fromEntries(Object.entries(naive).map(([k, v]) => [k, [v, v, v]]));
console.log('NAIVE', JSON.stringify(naive));
fs.writeFileSync('results_validation.json', JSON.stringify(out, null, 1));
