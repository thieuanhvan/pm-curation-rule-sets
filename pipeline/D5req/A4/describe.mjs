// Descriptives for the report: effort proxy by type/level, observed affinity shares, window population.
import fs from 'fs';
import { ITEMS, TOK, TV, q, mean } from './lib.mjs';
const dec = ITEMS.filter(x => x.dec != null); const o = {};
const grp = (arr, key) => { const g = {}; for (const x of arr) (g[key(x)] = g[key(x)] || []).push(x.effortRaw); return Object.fromEntries(Object.entries(g).filter(([, v]) => v.length >= 5).map(([k, v]) => [k, { n: v.length, mean: +mean(v).toFixed(2), p90: q(v, .9) }])); };
o.effortByType = grp(dec, x => x.type); o.effortByLevel = grp(dec, x => x.lvl);
const ef = dec.map(x => x.effortRaw); const m = mean(ef); o.effortCV = Math.sqrt(mean(ef.map(e => (e - m) ** 2))) / m; o.effortMean = m;
const sameOrg = t => t.org != null && ITEMS.find(x => x.id === t.realItem).subOrg === t.org;
o.orgMatchShare_all = TOK.filter(sameOrg).length / TOK.length; o.orgMatchShare_2023plus = TOK.filter(t => t.t >= TV).filter(sameOrg).length / TOK.filter(t => t.t >= TV).length;
const pop = ITEMS.filter(x => x.arr < Infinity && (x.arr >= TV || x.dec == null || x.dec >= TV));
o.windowPopulation = pop.length; o.windowRealAccepted = pop.filter(x => x.out === 'A').length; o.windowRealAcceptedAB = pop.filter(x => x.out === 'A' && (x.lvl === 'A' || x.lvl === 'B')).length;
o.decidersAll = new Set(TOK.map(t => t.user)).size; o.decidersWindow = new Set(TOK.filter(t => t.t >= TV).map(t => t.user)).size;
o.orgsSubmittingWindow = new Set(ITEMS.filter(x => x.arr >= TV).map(x => x.subOrg)).size;
console.log(JSON.stringify(o, null, 1)); fs.writeFileSync('results_describe.json', JSON.stringify(o, null, 1));
