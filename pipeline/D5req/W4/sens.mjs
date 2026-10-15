// Task 2: one-at-a-time (tornado) and global random sensitivity. Saves raw per-run key outcomes.
import fs from 'fs';
import { POLICIES, BASE, runPolicy, outcomes, mulberry } from './w4lib.mjs';
const mode = process.argv[2] || 'oat'; const REPS = +(process.argv[3] || 8); const NG = +(process.argv[4] || 80);
const KEEP = ['new_decBy90', 'new_decBy365', 'new_RMST365', 'EAimp_by90', 'EAimp_by365', 'EAimp_RMST365', 'EAobs_by365', 'EAimp_legacyAcceptedShare',
  'EAimp_value_uniform', 'EAimp_value_rating', 'EAimp_value_assertionUse', 'EAimp_value_level_KEY', 'EAimp_value_levelXrating_A4', 'lostFinal', 'endPending', 'resub', 'idleTokens'];
const pick = o => Object.fromEntries(KEEP.map(k => [k, o[k]]));
const out = { mode, base: BASE, reps: REPS, scen: [] };
function doScen(name, sc, reps, policies, seed0 = 0) {
  const row = { name, sc, res: {} };
  for (const p of policies) { row.res[p] = []; for (let k = 0; k < reps; k++) row.res[p].push(pick(outcomes(runPolicy(p, sc, seed0 + k), seed0 + k))); }
  out.scen.push(row); console.error(mode, name, new Date().toISOString().slice(11, 19));
}
const ONLY = process.env.POL ? process.env.POL.split(',') : null; const ALL = Object.keys(POLICIES).filter(p => !ONLY || ONLY.includes(p)), EXPP = ALL.filter(p => POLICIES[p].usesResub);
if (mode === 'oat') {
  doScen('base', BASE, REPS, ALL);
  const V = { r: [0, .5, .75], delay: [7, 180, 365], kappa: [1.5, 2, 3], effort: ['proxy', { cv: 1 }, { cv: 2 }], cap: [.75, 1.25], cal: ['cal2015_22', 'full2015_26_insample'] };
  for (const [k, vals] of Object.entries(V)) for (const v of vals) {
    const sc = { ...BASE, [k]: v }; const lab = `${k}=${typeof v === 'object' ? 'cv' + v.cv : v}`;
    doScen(lab, sc, REPS, (k === 'r' || k === 'delay') ? EXPP : ALL); // other policies are unaffected by r/delay (identical seeds) -> reuse base
  }
} else {
  const rng = mulberry(20261007); const EF = ['unit', 'proxy', { cv: 1 }, { cv: 2 }], CA = ['cal2021_22', 'cal2015_22', 'full2015_26_insample'];
  for (let g = 0; g < NG; g++) {
    const sc = { r: .75 * rng(), delay: Math.exp(Math.log(7) + rng() * Math.log(365 / 7)), kappa: 1 + 2 * rng(), effort: EF[Math.floor(rng() * 4)], cap: .75 + .5 * rng(), cal: CA[Math.floor(rng() * 3)] };
    doScen('g' + g, sc, 1, ALL, 1000 + g);
  }
}
fs.writeFileSync(`results_sens_${mode}${process.env.POL ? "_extra" : ""}.json`, JSON.stringify(out));
