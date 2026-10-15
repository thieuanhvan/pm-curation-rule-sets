// Supplementary checks for Task 2/4: per-level deltas for kappa/effort/cal, and joint dominance of capacity-neutral reorderings over ASIS.
import fs from 'fs';
const load = f => JSON.parse(fs.readFileSync(f));
function merge(a, b) { const m = new Map(a.scen.map(s => [s.name, s])); for (const s of b.scen) Object.assign(m.get(s.name).res, s.res); return [...m.values()]; }
const OAT = merge(load('results_sens_oat.json'), load('results_sens_oat_extra.json')), GLO = merge(load('results_sens_global.json'), load('results_sens_global_extra.json'));
const base = OAT.find(s => s.name === 'base'); for (const s of OAT) for (const p of Object.keys(base.res)) if (!s.res[p]) s.res[p] = base.res[p];
const mean = a => a.reduce((x, y) => x + y, 0) / a.length;
const P = ['PRIO_AB', 'EDF90_noexpiry', 'EDF90_panel20_oldest', 'SKILL_pool_affinity', 'LIFO_pool', 'EXP365_purge'];
const K = ['EAimp_by90', 'EAimp_by365', 'EAimp_legacyAcceptedShare', 'EAimp_value_rating', 'EAimp_value_assertionUse'];
const lines = [];
for (const s of OAT.filter(s => /^(base|kappa|effort|cal|cap)/.test(s.name))) {
  lines.push(s.name.padEnd(28) + ' ASIS by90 ' + mean(s.res.ASIS_logit.map(o => o.EAimp_by90)).toFixed(3) + ' leg ' + mean(s.res.ASIS_logit.map(o => o.EAimp_legacyAcceptedShare)).toFixed(3) + ' | ' +
    P.map(p => p.slice(0, 12) + ':' + K.map(k => { const d = mean(s.res[p].map((o, i) => o[k] - s.res.ASIS_logit[i][k])); return k.includes('value') ? d.toFixed(0) : d.toFixed(3); }).join('/')).join('  '));
}
// joint dominance: candidate better on by90 AND by365 AND not worse on legacy (tol 0.005) AND not worse on rating value (tol 1 %)
const dom = (o, a) => o.EAimp_by90 > a.EAimp_by90 + .005 && o.EAimp_by365 > a.EAimp_by365 + .005 && o.EAimp_legacyAcceptedShare >= a.EAimp_legacyAcceptedShare - .005 && o.EAimp_value_rating >= .99 * a.EAimp_value_rating && o.lostFinal === 0;
for (const p of ['PRIO_AB', 'EDF90_panel20_oldest', 'EDF90_noexpiry', 'PANEL10_old365_oldest']) {
  const cnt = (ss, f) => { let n = 0, y = 0; for (const s of ss) s.res[p].forEach((o, i) => { if (f && !f(s)) return; n++; if (dom(o, s.res.ASIS_logit[i])) y++; }); return [y, n]; };
  const a = cnt(OAT.concat(GLO)), b = cnt(GLO, s => s.sc.kappa <= 2), c = cnt(GLO, s => s.sc.kappa > 2);
  lines.push(`dominates ASIS (by90 & by365 up, legacy & rating-value not down, no loss): ${p.padEnd(24)} all ${a[0]}/${a[1]}  global kappa<=2 ${b[0]}/${b[1]}  kappa>2 ${c[0]}/${c[1]}`);
}
// any capacity-neutral, no-loss policy in the set that dominates ASIS, per run
{ const cands = ['PRIO_AB', 'EDF90_panel20_oldest', 'EDF90_noexpiry', 'PANEL10_old365_oldest', 'PANEL25_old365_quality', 'LIFO_pool', 'SKILL_pool_affinity', 'OWN_steal'];
  let n = 0, y = 0; for (const s of OAT.concat(GLO)) s.res.ASIS_logit.forEach((a, i) => { n++; if (cands.some(p => dom(s.res[p][i], a))) y++; }); lines.push(`runs where at least one capacity-neutral no-loss policy dominates ASIS: ${y}/${n}`); }
fs.writeFileSync('extra_checks_log.txt', lines.join('\n')); console.log(lines.join('\n'));
