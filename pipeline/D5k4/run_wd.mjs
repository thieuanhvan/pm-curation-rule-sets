import fs from 'fs'; import {analyze} from './analyze.mjs';
const NOW = Date.UTC(2026, 9, 7);
const raw = JSON.parse(fs.readFileSync('wd_cases.json'));
const map = {done: 'acc', notdone: 'rej', withdrawn: 'wd', pending: 'pending'};
const cases = raw.filter(x => map[x.kind] || x.kind === 'other:done').map(x => ({id: x.id, arr: x.arr, dec: x.kind === 'pending' ? null : (x.dec ?? null), out: map[x.kind] || 'acc', sub: x.prop, decU: x.decU}))
  .filter(c => !(c.out !== 'pending' && c.dec == null)); // drop decided-without-timestamp (reported)
const R = analyze(cases.filter(c => c.arr >= Date.UTC(2016, 0, 1)), NOW);
R.note = 'sample: ' + raw.length + ' subpages from 44 alphabetical windows; ' + (raw.length - cases.length) + ' dropped (no decision ts / odd status); window 2016+';
fs.writeFileSync('results_wd.json', JSON.stringify(R, null, 1)); console.log(JSON.stringify(R, null, 0).slice(0, 4000));
