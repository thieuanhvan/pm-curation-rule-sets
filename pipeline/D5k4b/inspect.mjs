import fs from 'fs'; import {idsIn} from './classify_frozen_20261007.mjs';
for (const tag of ['go', 'hpo']) {
  const rows = JSON.parse(fs.readFileSync(`rows_${tag}.json`)), tl = JSON.parse(fs.readFileSync(`tl_${tag}.json`)), obo = JSON.parse(fs.readFileSync(`obo_${tag}.json`));
  const neg = rows.filter(r => r.cls === 'ACC' && !r.v1new && !r.v2);
  const cat = {};
  for (const r of neg) { const ids = idsIn(tl[r.n]); const ex = ids.filter(i => obo.ids[i]); const und = ex.filter(i => !obo.ids[i].d); const old = ex.filter(i => obo.ids[i].d && obo.ids[i].d < r.open.slice(0, 10)); const missing = ids.filter(i => !obo.ids[i]);
    const k = !ids.length ? 'noID' : und.length ? 'undatedID' : missing.length ? 'IDnotInOBO' : 'onlyOlderIDs'; (cat[k] ||= []).push(r.n + '/T' + r.tier); }
  console.log(tag, 'ACC without signal', neg.length, JSON.stringify(Object.fromEntries(Object.entries(cat).map(([k, v]) => [k, v.length]))));
  console.log(JSON.stringify(cat));
}
