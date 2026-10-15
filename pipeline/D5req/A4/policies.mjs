// (4)+(5) Policy comparison, forward window 2023-01-01..2026-10-07 from the REAL queue state, observed capacity,
// as-is discipline = conditional logit calibrated on 2021-2022 (best temporally validated model).
// Expiry with behavioural resubmission (r, exponential delay), grandfathering; non-expiry alternatives.
import fs from 'fs';
import { TV, NOW, day, ci, mulberry } from './lib.mjs';
import { run, metrics, drawBeta } from './sim2.mjs';
const FIT = JSON.parse(fs.readFileSync('fit_logit.json'));
const fv = (() => { const f = FIT['cal2021_22_T1']; return { b: Object.values(f.coef), cov: f.cov }; })();
const BURST = JSON.parse(fs.readFileSync('results_forecast.json')).bursts; // observed burst size/frequency
const REPS = +(process.argv[2] || 6);
const effort = process.argv[3] === 'proxy' ? 'proxy' : 'unit'; const kappa = +(process.argv[4] || 1);
const sprintMonths = (perYear) => { const ms = []; for (let y = 2023; y <= 2026; y++) for (const m of perYear === 2 ? [2, 8] : [8]) { const a = Date.UTC(y, m, 1) / 864e5, b = Date.UTC(y, m + 1, 1) / 864e5; if (b <= NOW) ms.push([a, b]); } return ms; };
function sprintTokens(perYear, size, seed) { const rng = mulberry(seed); const t = []; for (const [a, b] of sprintMonths(perYear)) for (let i = 0; i < size; i++) t.push({ t: a + rng() * (b - a), user: 'SPRINT', org: null }); return t.sort((x, y) => x.t - y.t); }
const inSprint = (perYear) => { const ms = sprintMonths(perYear); return t => ms.some(([a, b]) => t >= a && t < b); };
const S = Math.round(BURST.excessMedian); // 60 extra decisions per sprint (median observed burst excess)
const P = {
  SQ_asis_visibilityTiers: {},
  PRIO_AB_asis: { prioAB: true },
  PANEL_old365_phi10_quality: { panel: { phi: .10, A: 365, order: 'quality' } },
  PANEL_old365_phi25_quality: { panel: { phi: .25, A: 365, order: 'quality' } },
  PANEL_old365_phi10_oldest: { panel: { phi: .10, A: 365, order: 'oldest' } },
  SPRINT_neutral_2xYear_old365_quality: { panel: { phi: 1, A: 365, order: 'quality', active: inSprint(2) } },
  SPRINT_added_1xYear_60_quality: { sprintPY: 1 },
  SPRINT_added_2xYear_60_quality: { sprintPY: 2 },
};
for (const T of [180, 365]) for (const gf of [false, true]) for (const r of [0, .25, .5, .75]) for (const dl of [30, 180]) {
  if (r === 0 && dl === 180) continue;
  P[`EXP${T}_${gf ? 'grandf' : 'purge'}_r${r}_delay${dl}`] = { expireT: T, grandfather: gf, resub: r, resubDelay: dl };
}
const KEYS = ['decisions', 'decisionsLegacy', 'endPending', 'endPendingMedAge', 'endPendingShareOver365', 'new_medWait', 'new_p90Wait', 'within30', 'within90', 'within365', 'AB_within90',
  'expiredEvents', 'resubmissions', 'lostFinal', 'lostRealAccepted', 'lostRealAcceptedShare', 'lostQualWShareOfRealAccepted', 'lostExpAccQualW', 'lostAB', 'QWAY', 'acceptedItemYears', 'staleUnreviewedItemYears', 'lostTokens', 'resubPendingAtEnd'];
const out = { design: { window: '2023-01-01..2026-10-07', start: 'real queue at 2023-01-01', discipline: 'LOGIT cal2021_22_T1 with parameter draws', reps: REPS, effort, kappa, sprintSize: S, burstsPerYearObserved: BURST.perYear }, policies: {} };
for (const [name, p] of Object.entries(P)) {
  const ms = [];
  for (let k = 0; k < REPS; k++) {
    const opt = { disc: 'LOGIT', tier: 1, beta: drawBeta(fv, mulberry(700 + k)), start: TV, effort, kappa, ...p };
    if (p.sprintPY) { opt.sprint = { tokens: sprintTokens(p.sprintPY, S, 33 + k), A: 365, order: 'quality' }; }
    ms.push(metrics(run(opt, 300 + k)));
  }
  out.policies[name] = Object.fromEntries(KEYS.map(key => [key, ci(ms.map(m => m[key]))]));
  out.policies[name].extraTokens = p.sprintPY ? sprintMonths(p.sprintPY).length * S : 0;
  const v = out.policies[name]; const f = (k, d = 0) => v[k][0] == null ? 'NA' : v[k][0].toFixed(d);
  console.log(name.padEnd(40), 'dec', f('decisions'), 'pend', f('endPending'), 'w90', f('within90', 3), 'w365', f('within365', 3), 'lostRA', f('lostRealAccepted'), 'lostQW%', (100 * v.lostQualWShareOfRealAccepted[0]).toFixed(1), 'resub', f('resubmissions'), 'QWAY', f('QWAY'), 'stale', f('staleUnreviewedItemYears'), 'extra', v.extraTokens);
}
fs.writeFileSync(`results_policies_${effort}_k${kappa}.json`, JSON.stringify(out, null, 1));
