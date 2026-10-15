// (3) Heterogeneous effort + decider specialisation: pooled vs ownership routing.
// Forward window 2023-01-01..2026-10-07 from the real queue state (main) and full history 2015-2026 (robustness).
// Effort: unit | proxy (1 + revisions suggested + comments before first decision) | lognormal CV 1 | CV 2.
// Affinity: decider matched to item if decider's org == submitter's org OR decider has decided an item of that submitter before.
// kappa = work multiplier for a mismatched decider (1 = no specialisation). Effort is normalised so the observed allocation is feasible.
import fs from 'fs';
import { TV, ci, mulberry } from './lib.mjs';
import { run, metrics, drawBeta } from './sim2.mjs';
const FIT = JSON.parse(fs.readFileSync('fit_logit.json'));
const fv = (() => { const f = FIT['cal2021_22_T1']; return { b: Object.values(f.coef), cov: f.cov }; })();
const mode = process.argv[2] || 'fwd'; const REPS = +(process.argv[3] || 8);
const start = mode === 'fwd' ? TV : undefined;
const EFF = mode === 'fwd' ? { unit: 'unit', proxy: 'proxy', cv1: { cv: 1 }, cv2: { cv: 2 } } : { unit: 'unit', proxy: 'proxy' };
const KAP = mode === 'fwd' ? [1, 1.5, 2, 3] : [1, 2, 3];
const POL = {
  POOL_FIFO: { route: 'pool', disc: 'FIFO' },
  POOL_LOGIT_asis: { route: 'pool', disc: 'LOGIT', tier: 1, logit: true },
  POOL_SKILL: { route: 'pool', disc: 'SKILL' },
  OWN_strict: { route: 'own', ownDisc: 'FIFO' },
  OWN_steal: { route: 'own', ownDisc: 'FIFO', steal: true },
  OWN_steal_reassign90: { route: 'own', ownDisc: 'FIFO', steal: true, reassignAfter: 90 },
  OWN_steal_LOGIT: { route: 'own', ownDisc: 'LOGIT', tier: 1, steal: true, logit: true },
};
const KEYS = ['decisions', 'matchedShare', 'endPending', 'new_medWait', 'new_p90Wait', 'within90', 'within365', 'AB_within90', 'lostTokens', 'QWAY'];
const out = { mode, reps: REPS, grid: {} };
for (const [en, e] of Object.entries(EFF)) for (const k of KAP) {
  const cell = {};
  for (const [pn, p] of Object.entries(POL)) {
    const stoch = p.logit || typeof e === 'object';
    const n = stoch ? REPS : 1; const ms = [];
    for (let r = 0; r < n; r++) { const opt = { ...p, effort: e, kappa: k, start, affinity: process.argv[4] || 'org' }; if (p.logit) opt.beta = drawBeta(fv, mulberry(500 + r)); ms.push(metrics(run(opt, 40 + r))); }
    cell[pn] = Object.fromEntries(KEYS.map(key => [key, ci(ms.map(m => m[key]))]));
  }
  out.grid[`${en}_k${k}`] = cell;
  console.log(`${en} k=${k}`); for (const [pn, v] of Object.entries(cell)) console.log('  ', pn.padEnd(22), 'dec', v.decisions[0].toFixed(0), 'match', v.matchedShare[0]?.toFixed(2), 'med', v.new_medWait[0]?.toFixed(0), 'p90', v.new_p90Wait[0]?.toFixed(0), 'w90', v.within90[0]?.toFixed(3), 'idle', v.lostTokens[0].toFixed(0), 'QWAY', v.QWAY[0].toFixed(0));
}
fs.writeFileSync(`results_routing_${mode}_${process.argv[4] || 'org'}.json`, JSON.stringify(out, null, 1));
