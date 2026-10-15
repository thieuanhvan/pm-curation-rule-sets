// Build item-level features (effort proxies, evidence type/rating, activity timestamps) for D5req/A4.
// Reuses ../../D5sim/trace_excl.json (arrivals + first decisions) and ../../D5b cache (events) + meta.
import fs from 'fs';
const B = '../../D5b/';
const tr = JSON.parse(fs.readFileSync('../../D5sim/trace_excl.json')).items;
const meta = Object.fromEntries(JSON.parse(fs.readFileSync(B + 'meta_evidence.json')).map(x => [x.id, x]));
const act = {}; const seen = new Set();
for (const f of fs.readdirSync(B + 'cache').sort()) for (const e of JSON.parse(fs.readFileSync(B + 'cache/' + f))) {
  if (seen.has(e.id)) continue; seen.add(e.id);
  if (e.originatingUser?.id === 385) continue;
  if (e.subject?.__typename !== 'EvidenceItem') continue;
  if (!['REVISION_SUGGESTED', 'COMMENTED', 'FLAGGED', 'REVISION_ACCEPTED', 'REVISION_REJECTED'].includes(e.action)) continue;
  (act[e.subject.id] = act[e.subject.id] || []).push([Date.parse(e.createdAt) / 864e5, ({REVISION_SUGGESTED:'RS',COMMENTED:'CM',FLAGGED:'FL',REVISION_ACCEPTED:'RA',REVISION_REJECTED:'RR'})[e.action], e.originatingUser?.id ?? -1]);
}
const out = tr.map(x => {
  const m = meta[x.id] || {}; const a = (act[x.id] || []).sort((p, q) => p[0] - q[0]);
  const cut = x.dec ?? Infinity;
  const pre = a.filter(z => z[0] <= cut + 1e-6);
  const nRev = pre.filter(z => z[1] === 'RS').length, nCom = pre.filter(z => z[1] === 'CM').length;
  return { id: x.id, arr: x.arr, dec: x.dec ?? null, out: x.out ?? null, lvl: x.lvl, rating: m.evidenceRating ?? null, type: m.evidenceType ?? null,
    subUser: x.subUser, subOrg: x.subOrg, decUser: x.decUser ?? null, decOrg: x.decOrg ?? null,
    nRevPre: nRev, nComPre: nCom, nFlagPre: pre.filter(z => z[1] === 'FL').length, nActAll: a.length,
    actT: a.map(z => +z[0].toFixed(3)), actU: a.map(z => z[2]) };
});
const kinds = {}; for (const id in act) for (const z of act[id]) kinds[z[1]] = (kinds[z[1]] || 0) + 1;
console.log(kinds, out.length, out.filter(x => x.dec != null).length);
fs.writeFileSync('items_feat.json', JSON.stringify(out));
