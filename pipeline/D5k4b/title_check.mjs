// V3 (HPO only): does the ticket title (requested label) match the name/synonym of an HP term, and when was that term created?
import fs from 'fs';
const T = JSON.parse(fs.readFileSync('titles_hpo.json')); const txt = fs.readFileSync('hp.obo', 'utf8');
const norm = s => s.toLowerCase().replace(/^\s*(\[?(ntr|new term( request)?|request|term request|nt)\]?\s*[:\-–]?\s*)+/i, '').replace(/["'`*_]/g, '').replace(/\(.*?\)/g, '').replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim().replace(/s\b/g, '');
const lab = {};
for (const blk of txt.split(/\n\[Term\]\n/).slice(1)) { const id = (blk.match(/^id: (\S+)/m) || [])[1]; const d = (blk.match(/^property_value: terms:date "([^"]+)"/m) || [])[1] || null;
  const names = [(blk.match(/^name: (.+)$/m) || [])[1], ...[...blk.matchAll(/^synonym: "([^"]+)"/gm)].map(m => m[1])].filter(Boolean);
  for (const nm of names) (lab[norm(nm)] ||= []).push({id, d}); }
const v1 = JSON.parse(fs.readFileSync('rows_hpo_v1_all.json')), v2 = JSON.parse(fs.readFileSync('rows_hpo_v2_all.json'));
const res = {};
for (const r of v2) { const t = T[r.n]; if (!t) continue; const hits = lab[norm(t)] || []; const lo = new Date(Date.parse(r.open) - 864e5).toISOString().slice(0, 10);
  res[r.n] = {title: t, match: hits.length ? (hits.some(h => h.d && h.d.slice(0, 10) >= lo) ? 'new' : hits.some(h => !h.d) ? 'undated' : 'old') : 'none'}; }
fs.writeFileSync('v3_title_hpo.json', JSON.stringify(res));
for (const [name, rows] of [['v1', v1], ['v2', v2]]) { const tab = {}; for (const r of rows) { const k = r.cls + '|' + (res[r.n]?.match || 'na'); tab[k] = (tab[k] || 0) + 1; } console.log(name, JSON.stringify(Object.entries(tab).sort())); }
// combined independent positive for HPO = V1 tracker-new or V2 new ID or V3 title->new term
for (const [name, rows] of [['v1', v1], ['v2', v2]]) { const pos = r => r.v1new > 0 || r.v2 > 0 || res[r.n]?.match === 'new'; const A = rows.filter(r => r.cls === 'ACC'), R = rows.filter(r => r.cls === 'REJ'), U = rows.filter(r => r.cls === 'UNCLEAR');
  const m = {aa: A.filter(pos).length, ab: A.filter(r => !pos(r)).length, ba: R.filter(pos).length, bb: R.filter(r => !pos(r)).length}; const n = m.aa + m.ab + m.ba + m.bb, po = (m.aa + m.bb) / n, pe = ((m.aa + m.ab) * (m.aa + m.ba) + (m.ba + m.bb) * (m.ab + m.bb)) / n / n;
  console.log(name, 'V1|V2|V3', JSON.stringify(m), 'agree', po.toFixed(3), 'kappa', ((po - pe) / (1 - pe)).toFixed(3), 'UNCLEAR pos', U.filter(pos).length, '/', U.length); }
console.log(Object.entries(res).slice(0, 8).map(([n, v]) => n + ' ' + v.title + ' => ' + v.match).join('\n'));
