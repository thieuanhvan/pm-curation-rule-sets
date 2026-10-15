import fs from 'fs'; import {analyze} from './analyze.mjs';
const NOW = Date.UTC(2026, 9, 7); const all = {};
for (const [tag, from] of [['hpo', '2014'], ['go', '2008'], ['go', '2016']]) {
  const o = Object.values(JSON.parse(fs.readFileSync(`issues_${tag}.json`)));
  const cases = o.filter(x => x.c >= from).map(x => ({id: x.n, arr: Date.parse(x.c), dec: x.s === 'closed' ? Date.parse(x.x) : null, out: x.s === 'open' ? 'pending' : (x.sr === 'not_planned' ? 'rej' : 'closed'), sub: x.u, decU: x.s === 'closed' ? (x.asg[0] || null) : null}));
  const R = analyze(cases, NOW); R.decider_source = 'first assignee as proxy (validated on 28-issue closed_by sample)';
  // assignee-proxy four-eyes and assignment coverage of closed items
  R.assignedClosedShare = +(cases.filter(c => c.dec && c.decU).length / cases.filter(c => c.dec).length).toFixed(3);
  R.submitterAssoc = o.filter(x => x.c >= from).reduce((m, x) => (m[x.aa] = (m[x.aa] || 0) + 1, m), {});
  all[tag + '_' + from] = R;
}
fs.writeFileSync('results_gh.json', JSON.stringify(all, null, 1));
for (const [k, R] of Object.entries(all)) { const {by_year, position, ...rest} = R; console.log(k, JSON.stringify(rest)); console.log(' pos', JSON.stringify(position.all), Object.entries(position.by_year).map(([y, v]) => y + ':' + v.mean + '/' + v.newest10 + '/L' + v.Lmed).join(' '));
  console.log(' yr', Object.entries(by_year).map(([y, v]) => `${y}:${v.sub}/${v.dec}/P${v.pendingEnd}/A${v.pendMedAgeD}`).join(' ')); }
