// identical measures (D5k4/analyze.mjs) on the census; windows 2016+ (comparable to manuscript) and 2017+ (subpage era complete)
import fs from 'fs'; import {analyze} from '../../D5k4/analyze.mjs';
const NOW = Date.UTC(2026, 9, 7);
const raw = JSON.parse(fs.readFileSync('wd_cases_census.json'));
const map = {done: 'acc', notdone: 'rej', withdrawn: 'wd', pending: 'pending'};
const all = raw.filter(x => map[x.kind] || x.kind === 'other:done').map(x => ({id: x.id, arr: x.arr, dec: x.kind === 'pending' ? null : (x.dec ?? null), out: map[x.kind] || 'acc', sub: x.prop, decU: x.decU, rationale: x.rationale}));
const cases = all.filter(c => !(c.out !== 'pending' && c.dec == null));
const R = {note: `census: ${raw.length} parsed proposal subpages; ${all.length - cases.length} decided without a parseable decision timestamp dropped (as in D5k4)`};
for (const [lab, t0] of [['from2016', Date.UTC(2016, 0, 1)], ['from2017', Date.UTC(2017, 0, 1)]]) {
  const cs = cases.filter(c => c.arr >= t0); const r = analyze(cs, NOW);
  r.rho_by_year = Object.fromEntries(Object.entries(r.by_year).map(([y, v]) => [y, +(v.dec / v.sub).toFixed(2)]));
  const term = cs.filter(c => c.out !== 'pending'); r.terminal_shares = {n: term.length, acc: +(term.filter(c => c.out === 'acc').length / term.length).toFixed(3), notdone: +(term.filter(c => c.out === 'rej').length / term.length).toFixed(3), withdrawn: +(term.filter(c => c.out === 'wd').length / term.length).toFixed(3)};
  // not-done rationale (all not-done in window, incl. those without decision ts)
  const nd = all.filter(c => c.arr >= t0 && c.out === 'rej'); const rc = {}; for (const c of nd) rc[c.rationale] = (rc[c.rationale] || 0) + 1;
  r.notdone_rationale = {n: nd.length, shares: Object.fromEntries(Object.entries(rc).sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, +(v / nd.length).toFixed(3)]))};
  // pending share incl. decided-without-ts in denominator
  r.pending_share_all_parsed = +(all.filter(c => c.arr >= t0 && c.out === 'pending').length / all.filter(c => c.arr >= t0).length).toFixed(4);
  R[lab] = r;
}
// export for u script (no usernames; pseudonyms only)
fs.writeFileSync('wd_cases_census_u.json', JSON.stringify(raw.map(x => ({id: x.id, kind: x.kind, arr: x.arr, dec: x.dec, decU: x.decU, prop: x.prop}))));
fs.writeFileSync('results_analyze.json', JSON.stringify(R, null, 1));
for (const k of ['from2016', 'from2017']) { const r = R[k]; console.log(k, r.n, r.outcomes, 'backlog', r.backlog, 'rho', r.rho_by_year, 'ttd_rej', r.ttd_rej, 'ttd_acc', r.ttd_acc, r.terminal_shares, r.notdone_rationale, 'pos', r.position.all, 'pendshare', r.pending_share_all_parsed); }
