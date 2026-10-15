// W2: resumable fetch of GitHub issue timelines for seeded random samples (500/repo, open AND closed,
// opened 2016+) of GO 'New term request' and HPO 'new term request' tickets.
// Polite: unauthenticated, descriptive User-Agent, honours X-RateLimit-* (sleeps until reset),
// hard total budget of 1,100 GitHub requests (persisted in reqcount_w2.json), checkpoint after every ticket
// (append-only JSONL), progress log in fetch_w2.log. Safe to kill and restart at any time.
// Usage (from this folder):  node fetch_w2.mjs            (resume / continue)
//                            node fetch_w2.mjs --sample   (only (re)write the sample files, no requests)
import fs from 'fs'; import crypto from 'crypto';
const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
process.chdir(HERE);
const K4 = '../../D5k4', K4B = '../../D5k4b';
const SALT = process.env.P17_SALT; // same first-stage pseudonym as D5k4/D5k4b so identities join; HMAC is applied on top in build_logs.py
const ps = s => s ? 'u_' + crypto.createHash('sha256').update(SALT + s.toLowerCase()).digest('hex').slice(0, 10) : null;
const mask = t => (t || '').replace(/@([A-Za-z0-9-]{1,39})/g, (m, u) => '@' + ps(u)).slice(0, 3000);
const UA = 'pm-curation-rule-sets-research (contact via GitHub thieuanhvan)';
const AUTH = process.env.GITHUB_TOKEN ? {Authorization: 'Bearer ' + process.env.GITHUB_TOKEN} : {}; // 07/10: user's read-only token, from env only, never logged
const BUDGET = 1100, KEEP = 1; // leave KEEP requests of the hourly quota unused
const CNT = 'reqcount_w2.json', LOG = 'fetch_w2.log';
const REPOS = {go: 'geneontology/go-ontology', hpo: 'obophenotype/human-phenotype-ontology'};
const N = 200 /* 07/10 cut 500 -> 300 -> 200 (user); first 200 of the same seeded draw order */, SEED = 20261007;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = (...a) => { const s = new Date().toISOString() + ' ' + a.join(' '); console.log(s); fs.appendFileSync(LOG, s + '\n'); };

// ---------- sample (deterministic; mulberry32) ----------
function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const pops = {}, samples = {};
for (const [i, tag] of ['go', 'hpo'].entries()) {
  const lab = tag === 'go' ? 'New term request' : 'new term request';
  pops[tag] = Object.values(JSON.parse(fs.readFileSync(`${K4}/issues_${tag}.json`))).filter(x => x.c >= '2016' && !x.pr && x.lab.includes(lab)).sort((a, b) => a.n - b.n);
  const rnd = mulberry32(SEED + i), pool = pops[tag].slice(), pick = [];
  while (pick.length < Math.min(N, pops[tag].length)) pick.push(pool.splice(Math.floor(rnd() * pool.length), 1)[0]);
  samples[tag] = pick;
  fs.writeFileSync(`sample_w2_${tag}.json`, JSON.stringify({seed: SEED + i, rng: 'mulberry32', population: pops[tag].length, popOpen: pops[tag].filter(x => x.s === 'open').length, n: pick.map(x => x.n)}));
}
if (process.argv.includes('--sample')) { for (const t in samples) console.log(t, pops[t].length, samples[t].length, samples[t].filter(x => x.s === 'open').length, 'open'); process.exit(0); }

// ---------- request layer ----------
let remaining = null, resetAt = 0;
const cnt = () => { try { return JSON.parse(fs.readFileSync(CNT)); } catch { return {n: 0, byStatus: {}}; } };
async function probe() {
  try { const r = await fetch('https://api.github.com/rate_limit', {headers: {'User-Agent': UA, ...AUTH}}); const j = await r.json(); remaining = j.resources.core.remaining; resetAt = j.resources.core.reset; log('probe core remaining', remaining, 'reset', new Date(resetAt * 1000).toISOString()); }
  catch (e) { log('probe failed', e.message); }
}
async function get(url, tries = 0) {
  const c = cnt(); if (c.n >= BUDGET) throw new Error('budget');
  if (remaining !== null && remaining <= KEEP) {
    const w = resetAt * 1000 - Date.now() + 20000;
    if (w > 0) { log('quota exhausted; sleeping until reset', new Date(resetAt * 1000).toISOString(), Math.round(w / 60000) + ' min'); await sleep(w); }
    await probe(); if (remaining !== null && remaining <= KEEP) { await sleep(60000); return get(url, tries); }
  }
  await sleep(1500);
  c.n++; fs.writeFileSync(CNT, JSON.stringify(c));
  let r;
  try { r = await fetch(url, {headers: {...AUTH, 'User-Agent': UA, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}}); }
  catch (e) { log('network error', e.message); await sleep(60000 * (tries + 1)); if (tries < 5) return get(url, tries + 1); throw e; }
  if (r.headers.get('x-ratelimit-remaining') != null) { remaining = +r.headers.get('x-ratelimit-remaining'); resetAt = +r.headers.get('x-ratelimit-reset'); }
  const c2 = cnt(); c2.byStatus[r.status] = (c2.byStatus[r.status] || 0) + 1; fs.writeFileSync(CNT, JSON.stringify(c2));
  if (r.status === 403 || r.status === 429) {
    const ra = +r.headers.get('retry-after');
    if (ra) { log('secondary limit; retry-after', ra, 's'); await sleep((ra + 5) * 1000); } else { remaining = 0; }
    if (tries < 6) return get(url, tries + 1); throw new Error('HTTP ' + r.status);
  }
  if (r.status >= 500) { log('HTTP', r.status, 'backoff'); await sleep(120000); if (tries < 4) return get(url, tries + 1); throw new Error('HTTP ' + r.status); }
  if (r.status === 404 || r.status === 410) return {gone: r.status};
  if (!r.ok) throw new Error(`HTTP ${r.status} ${url}`);
  return {body: await r.json(), link: r.headers.get('link')};
}

// ---------- event simplification (superset of D5k4b simp) ----------
const simp = e => {
  const o = {ev: e.event, t: e.created_at || e.submitted_at || null, actor: ps(e.actor?.login || e.user?.login), bot: (e.actor?.type || e.user?.type) === 'Bot'};
  if (e.commit_id) o.commit = e.commit_id;
  if (e.commit_url) { const m = e.commit_url.match(/repos\/([^/]+\/[^/]+)\/commits/); if (m) o.crepo = m[1]; }
  if (e.state_reason) o.sr = e.state_reason;
  if (e.label) o.label = e.label.name;
  if (e.assignee) o.assignee = ps(e.assignee.login);
  if (e.event === 'commented') { o.body = mask(e.body); o.aa = e.author_association; o.cid = e.id; }
  if (e.event === 'committed') { o.msg = mask(e.message); o.t = e.author?.date || e.committer?.date || null; o.commit = e.sha; }
  if (e.event === 'reviewed') { o.state = e.state; }
  if (e.source?.issue) { const s = e.source.issue; o.src = {repo: (s.repository?.full_name || s.repository_url?.split('/repos/')[1]), n: s.number, pr: !!s.pull_request, merged: s.pull_request?.merged_at || null, state: s.state, title: mask(s.title), user: ps(s.user?.login)}; }
  if (e.event === 'renamed') o.rename = {from: mask(e.rename?.from), to: mask(e.rename?.to)};
  return o;
};

// ---------- main loop: interleave GO/HPO so partial results stay balanced ----------
const outF = tag => `tl_w2_${tag}.jsonl`;
const have = {go: new Set(), hpo: new Set()};
for (const tag of ['go', 'hpo']) { try { for (const l of fs.readFileSync(outF(tag), 'utf8').split('\n')) if (l.trim()) have[tag].add(JSON.parse(l).n); } catch {} }
// reuse D5k4b timelines (fetched 07/10/2026 03:xx UTC, same simp minus assignee/crepo fields)
for (const tag of ['go', 'hpo']) {
  let old = {}; try { old = JSON.parse(fs.readFileSync(`${K4B}/tl_${tag}.json`)); } catch {}
  for (const x of samples[tag]) if (!have[tag].has(x.n) && old[x.n]) {
    fs.appendFileSync(outF(tag), JSON.stringify({...old[x.n], s: x.s, src: 'D5k4b', fetched: '2026-10-07T03:30Z'}) + '\n'); have[tag].add(x.n);
  }
}
const queue = []; const L = Math.max(samples.go.length, samples.hpo.length);
for (let i = 0; i < L; i++) for (const tag of ['go', 'hpo']) { const x = samples[tag][i]; if (x && !have[tag].has(x.n)) queue.push([tag, x]); }
log('start; todo', queue.length, '| have go', have.go.size, 'hpo', have.hpo.size, '| requests used', cnt().n, '/', BUDGET);
await probe();
for (const [tag, x] of queue) {
  try {
    let url = `https://api.github.com/repos/${REPOS[tag]}/issues/${x.n}/timeline?per_page=100`, ev = [], pages = 0, gone = null;
    while (url) {
      const r = await get(url); if (r.gone) { gone = r.gone; break; }
      ev = ev.concat(r.body); pages++;
      const nx = r.link && r.link.match(/<([^>]+)>;\s*rel="next"/); url = nx ? nx[1] : null;
    }
    const rec = {n: x.n, c: x.c, x: x.x, s: x.s, sr: x.sr, lab: x.lab, sub: x.u, aa: x.aa, cm: x.cm, asg: x.asg, pages, gone, src: 'W2', fetched: new Date().toISOString(), events: ev.map(simp)};
    fs.appendFileSync(outF(tag), JSON.stringify(rec) + '\n'); have[tag].add(x.n);
    log(tag, x.n, x.s, 'events', ev.length, 'pages', pages, gone ? 'GONE ' + gone : '', '| rem', remaining, '| used', cnt().n, '| have', have.go.size + have.hpo.size, '/', samples.go.length + samples.hpo.length);
  } catch (e) { log('ERR', tag, x.n, e.message.slice(0, 200)); if (e.message === 'budget') { log('STOP budget reached'); process.exit(0); } }
}
log('DONE have go', have.go.size, 'hpo', have.hpo.size, 'requests', cnt().n);
