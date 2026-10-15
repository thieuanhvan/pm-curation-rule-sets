// Follow-up checks: curator 'rejections', flag campaigns, bulk submission bursts, self-accepted revisions by curators.
import fs from 'fs';
const ev = []; const seen = new Set();
for (const f of fs.readdirSync('cache').sort()) for (const e of JSON.parse(fs.readFileSync('cache/' + f))) { if (seen.has(e.id)) continue; seen.add(e.id); ev.push(e); }
ev.sort((a, b) => a.createdAt.localeCompare(b.createdAt) || a.id - b.id);
const users = Object.fromEntries(JSON.parse(fs.readFileSync('meta_users.json')).map(u => [u.id, u]));
const role = u => users[u]?.role || 'UNKNOWN';
const sub = {}; for (const e of ev) if (e.action === 'SUBMITTED' && e.subject?.__typename === 'EvidenceItem') sub[e.subject.id] = e;
// 1. evidence REJECTED by current curators: self-withdrawal?
let cr = 0, crSelf = 0; for (const e of ev) if (e.action === 'REJECTED' && e.subject?.__typename === 'EvidenceItem' && role(e.originatingUser?.id) === 'CURATOR') { cr++; if (sub[e.subject.id]?.originatingUser?.id === e.originatingUser?.id) crSelf++; }
console.log('curator_rejections', cr, 'of which own submission (withdrawal)', crSelf);
// 2. flags by year and top flaggers
const fy = {}, fu = {}; for (const e of ev) if (e.action === 'FLAGGED') { const y = e.createdAt.slice(0, 4); fy[y] = (fy[y] || 0) + 1; fu[e.originatingUser?.id] = (fu[e.originatingUser?.id] || 0) + 1; }
console.log('flags_by_year', JSON.stringify(fy)); console.log('top_flaggers', JSON.stringify(Object.entries(fu).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([u, n]) => [u, role(+u), n])));
// 3. submission bursts: user-days with >= 50 submissions
const ud = {}; for (const id in sub) { const e = sub[id]; const k = e.originatingUser?.id + '|' + e.createdAt.slice(0, 10); ud[k] = (ud[k] || 0) + 1; }
const bursts = Object.entries(ud).filter(x => x[1] >= 50).sort((a, b) => b[1] - a[1]);
console.log('submission_bursts(>=50/user-day)', bursts.length, 'items', bursts.reduce((a, b) => a + b[1], 0), JSON.stringify(bursts.slice(0, 6)));
// pending items from bursts
const meta = Object.fromEntries(JSON.parse(fs.readFileSync('meta_evidence.json')).map(x => [x.id, x]));
const burstKeys = new Set(bursts.map(b => b[0])); let pendB = 0, pendAll = 0;
for (const id in sub) { if (meta[id]?.status !== 'SUBMITTED') continue; pendAll++; const e = sub[id]; if (burstKeys.has(e.originatingUser?.id + '|' + e.createdAt.slice(0, 10))) pendB++; }
console.log('pending_from_bursts', pendB, 'of', pendAll);
// pending by submitter concentration
const ps = {}; for (const id in sub) if (meta[id]?.status === 'SUBMITTED') { const u = sub[id].originatingUser?.id; ps[u] = (ps[u] || 0) + 1; }
const psA = Object.entries(ps).sort((a, b) => b[1] - a[1]); console.log('pending_submitters', psA.length, 'top5 share', (psA.slice(0, 5).reduce((a, b) => a + b[1], 0) / pendAll).toFixed(3), JSON.stringify(psA.slice(0, 5).map(([u, n]) => [u, role(+u), n])));
// pending by evidence level / rating (do high-value items wait too?)
const lv = {}; for (const id in meta) { const m = meta[id]; const k = m.evidenceLevel; lv[k] = lv[k] || { A: 0, S: 0, R: 0 }; lv[k][m.status[0]]++; }
console.log('status_by_level', JSON.stringify(lv));
// 4. revision self-accepted by current curators: subject types
const revs = {}; for (const e of ev) if (e.originatingObject?.__typename === 'Revision') { const r = revs[e.originatingObject.id] = revs[e.originatingObject.id] || {}; r[e.action] = e; }
const t = {}; for (const id in revs) { const r = revs[id]; if (r.REVISION_SUGGESTED && r.REVISION_ACCEPTED && r.REVISION_ACCEPTED.originatingUser?.id === r.REVISION_SUGGESTED.originatingUser?.id && role(r.REVISION_ACCEPTED.originatingUser?.id) === 'CURATOR') { const k = r.REVISION_ACCEPTED.subject?.__typename + '|' + r.REVISION_ACCEPTED.createdAt.slice(0, 4); t[k] = (t[k] || 0) + 1; } }
console.log('curator_self_accepted_revisions', JSON.stringify(t));
// 5. organization at event time vs user's current org (shows org history is recoverable)
const uOrgs = {}; for (const e of ev) if (e.organization?.id && e.originatingUser?.id) (uOrgs[e.originatingUser.id] = uOrgs[e.originatingUser.id] || new Set()).add(e.organization.id);
const multi = Object.values(uOrgs).filter(s => s.size > 1).length; console.log('users_with_events_under_>1_org', multi, 'of', Object.keys(uOrgs).length);
// 6. automated/bulk events share
const big = {}; for (const e of ev) { const k = e.originatingUser?.id + '|' + e.action + '|' + e.createdAt.slice(0, 10); big[k] = (big[k] || 0) + 1; }
console.log('bulk user-action-days >=500', JSON.stringify(Object.entries(big).filter(x => x[1] >= 500).map(([k, n]) => [k, role(+k.split('|')[0]), n])));
