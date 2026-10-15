// Task 1: outcome metrics not defined by the triage key, base scenario, paired (common random numbers) vs ASIS.
import fs from 'fs';
import { POLICIES, BASE, runPolicy, outcomes, ci } from './w4lib.mjs';
import { metrics } from '../A4/sim2.mjs';
const REPS = +(process.argv[2] || 20);
const res = {}; const raw = {};
for (const n of Object.keys(POLICIES)) { raw[n] = [];
  for (let k = 0; k < REPS; k++) { const r = runPolicy(n, BASE, k); const o = outcomes(r, k); const m = metrics(r); o.A4_QWAY = m.QWAY; o.A4_AB_within90 = m.AB_within90; o.A4_within90 = m.within90; raw[n].push(o); }
  console.error('done', n);
}
const keys = Object.keys(raw.ASIS_logit[0]);
for (const n of Object.keys(raw)) { res[n] = {};
  for (const key of keys) { const v = raw[n].map(o => o[key]); res[n][key] = ci(v.map(x => x == null ? NaN : x));
    const d = raw[n].map((o, i) => (o[key] ?? NaN) - (raw.ASIS_logit[i][key] ?? NaN)); res[n]['d_' + key] = ci(d); } }
fs.writeFileSync('results_outcomes.json', JSON.stringify({ base: BASE, reps: REPS, note: 'mean [2.5,97.5] over reps (logit parameter draws + Gumbel noise + imputation draws); d_ = paired difference vs ASIS_logit', res }, null, 1));
const f = (a, d = 3) => a[0] == null || Number.isNaN(a[0]) ? 'NA' : `${a[0].toFixed(d)} [${a[1].toFixed(d)}, ${a[2].toFixed(d)}]`;
const show = ['new_decBy90', 'new_decBy365', 'new_RMST365', 'EAimp_by90', 'EAimp_by365', 'EAimp_RMST365', 'EAimp_KMmedTTA', 'EAobs_by365', 'EAobs_RMST365', 'EAimp_legacyAcceptedShare', 'EAimp_value_uniform', 'EAimp_value_rating', 'EAimp_value_assertionUse', 'EAimp_value_level_KEY', 'EAimp_value_levelXrating_A4', 'EAobs_value_uniform', 'A4_QWAY', 'lostFinal', 'endPending'];
for (const key of show) { console.log('\n##', key); for (const n of Object.keys(res)) console.log('  ', n.padEnd(24), f(res[n][key], key.includes('value') || key.includes('RMST') || key.includes('QWAY') || key.includes('Med') || key.includes('lost') || key.includes('Pend') ? 0 : 3), '  d=', f(res[n]['d_' + key], key.includes('value') || key.includes('RMST') || key.includes('QWAY') || key.includes('Med') || key.includes('lost') || key.includes('Pend') ? 0 : 3)); }
