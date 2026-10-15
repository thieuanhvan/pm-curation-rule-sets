// Finish the event pull from offset 168000 page by page; isolate records that make the server fail (HTTP 500).
import fs from 'fs';
const URL = "https://civicdb.org/api/graphql"; const sleep = ms => new Promise(r => setTimeout(r, ms));
const b64 = n => Buffer.from(String(n)).toString('base64');
const SUBJ = ['EvidenceItem', 'Assertion', 'MolecularProfile', 'GeneVariant', 'FactorVariant', 'FusionVariant', 'RegionVariant', 'Gene', 'Factor', 'Fusion', 'Region', 'Source', 'SourceSuggestion', 'VariantGroup', 'Revision', 'RevisionSet', 'Flag', 'Comment'].map(t => `... on ${t}{id}`).join(' ');
const F = `nodes{ id action createdAt organization{id} originatingUser{id} originatingObject{ __typename ... on Revision{id} ... on Flag{id} ... on Comment{id} ... on SourceSuggestion{id} } subject{ __typename ${SUBJ} } }`;
const FMIN = `nodes{ id action createdAt organization{id} originatingUser{id} }`;
async function post(q) { for (let a = 0; a < 2; a++) { try { const r = await fetch(URL, { method: "POST", headers: { "content-type": "application/json", "user-agent": "pm-curation-rule-sets-research (polite, sequential)" }, body: JSON.stringify({ query: q }) }); if (r.status === 200) { const j = await r.json(); if (!j.errors) return j; } } catch (e) { } await sleep(3000); } return null; }
let reqs = 0; const bad = [];
async function page(off, n, fields) { reqs++; const j = await post(`{ e:events(first:${n}, after:"${b64(off)}", sortBy:{column:CREATED,direction:ASC}){ ${fields} } }`); await sleep(800); return j?.data.e.nodes; }
async function get(off, n) {
  const r = await page(off, n, F); if (r) return r;
  if (n > 10) { const out = []; for (let k = 0; k < n; k += 10) out.push(...await get(off + k, Math.min(10, n - k))); return out; }
  if (n > 1) { const out = []; for (let k = 0; k < n; k++) out.push(...await get(off + k, 1)); return out; }
  const m = await page(off, 1, FMIN); bad.push({ off, ev: m?.[0] }); return (m || []).map(x => ({ ...x, subject: null, originatingObject: null, _degraded: true }));
}
const tot = (await post(`{events(first:1){totalCount}}`)).data.events.totalCount; console.log('total', tot);
for (let off = 168000; off < tot; off += 2000) {
  const fn = `cache/ev_${String(off).padStart(7, '0')}.json`; if (fs.existsSync(fn)) continue;
  const nodes = []; for (let p = off; p < Math.min(off + 2000, tot); p += 100) nodes.push(...await get(p, 100));
  fs.writeFileSync(fn, JSON.stringify(nodes)); console.log(off, nodes.length, nodes.at(-1)?.createdAt, 'reqs', reqs, 'bad', bad.length);
}
fs.writeFileSync('pull_tail_bad.json', JSON.stringify(bad)); console.log('done reqs', reqs, 'bad', bad.length);
