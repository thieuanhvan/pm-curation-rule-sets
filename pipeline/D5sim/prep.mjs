// Build the evidence-item queue trace (arrivals + decision tokens) from the cached CIViC event log.
// Usage: node prep.mjs [excl|incl]  -> trace_excl.json / trace_incl.json
import fs from 'fs';
const SRC = '../D5b/'; const mode = process.argv[2] || 'excl';
const BOT = mode === 'excl' ? new Set([385]) : new Set();
const ev = []; const seen = new Set(); let raw = 0;
for (const f of fs.readdirSync(SRC + 'cache').sort()) for (const e of JSON.parse(fs.readFileSync(SRC + 'cache/' + f))) { raw++; if (seen.has(e.id)) continue; seen.add(e.id); if (BOT.has(e.originatingUser?.id)) continue; ev.push(e); }
ev.sort((a, b) => a.createdAt.localeCompare(b.createdAt) || a.id - b.id);
const meta = Object.fromEntries(JSON.parse(fs.readFileSync(SRC + 'meta_evidence.json')).map(x => [x.id, x]));
const items = {};
for (const e of ev) {
  if (e.subject?.__typename !== 'EvidenceItem') continue;
  const it = items[e.subject.id] = items[e.subject.id] || { id: e.subject.id };
  const t = Date.parse(e.createdAt) / 864e5;
  if (e.action === 'SUBMITTED' && it.arr == null) { it.arr = t; it.subUser = e.originatingUser?.id; it.subOrg = e.organization?.id ?? null; }
  if ((e.action === 'ACCEPTED' || e.action === 'REJECTED') && it.dec == null) { it.dec = t; it.out = e.action[0]; it.decUser = e.originatingUser?.id; it.decOrg = e.organization?.id ?? null; }
}
let noSub = 0, decBeforeSub = 0, botSub = 0; const out = [];
for (const it of Object.values(items)) {
  if (it.arr == null) { noSub++; continue; }
  if (it.dec != null && it.dec < it.arr) { decBeforeSub++; it.dec = it.arr; }
  it.lvl = meta[it.id]?.evidenceLevel ?? null; it.statusNow = meta[it.id]?.status ?? null;
  out.push(it);
}
out.sort((a, b) => a.arr - b.arr || a.id - b.id);
const info = { mode, rawPulled: raw, unique: seen.size, dupShare: +((raw - seen.size) / raw).toFixed(4), eventsKept: ev.length, items: out.length, noSubmission: noSub, decBeforeSubClipped: decBeforeSub, decided: out.filter(x => x.dec != null).length };
console.log(JSON.stringify(info));
fs.writeFileSync(`trace_${mode}.json`, JSON.stringify({ info, items: out }));
