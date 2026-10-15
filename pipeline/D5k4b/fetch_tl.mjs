// K4b: fetch issue timelines for a seeded random sample of 100 closed 2016+ tickets per repo.
// Polite: unauthenticated, checks X-RateLimit headers, sleeps until reset, hard budget 255 GitHub requests.
import fs from 'fs'; import crypto from 'crypto';
const SALT = process.env.P17_SALT;
const ps = s => s ? 'u_' + crypto.createHash('sha256').update(SALT + s.toLowerCase()).digest('hex').slice(0, 10) : null;
const mask = t => (t || '').replace(/@([A-Za-z0-9-]{1,39})/g, (m, u) => '@' + ps(u)).slice(0, 3000);
const UA = 'pm-curation-rule-sets-research (academic process-mining feasibility; non-commercial)';
const CNT = 'reqcount.json'; const BUDGET = 255;
const sleep = ms => new Promise(r => setTimeout(r, ms));
let resetAt = 0, remaining = null;
async function get(url) {
  let c = {n: 0, log: []}; try { c = JSON.parse(fs.readFileSync(CNT)); } catch {}
  if (c.n >= BUDGET) throw new Error('budget');
  if (remaining !== null && remaining <= 1) { const w = resetAt * 1000 - Date.now() + 10000; if (w > 0) { console.log(new Date().toISOString(), 'sleep until reset', Math.round(w / 60000), 'min'); await sleep(w); } remaining = null; }
  await sleep(2000);
  c.n++; c.log.push(url.slice(0, 160)); fs.writeFileSync(CNT, JSON.stringify(c));
  const r = await fetch(url, {headers: {'User-Agent': UA, 'Accept': 'application/vnd.github+json'}});
  remaining = +r.headers.get('x-ratelimit-remaining'); resetAt = +r.headers.get('x-ratelimit-reset');
  if (r.status === 403 || r.status === 429) { console.log('rate-limited', r.status); remaining = 0; return get(url); }
  if (!r.ok) throw new Error(`HTTP ${r.status} ${url}`);
  return {body: await r.json(), link: r.headers.get('link')};
}
// initial quota probe (rate_limit endpoint does not count against core)
{ const r = await fetch('https://api.github.com/rate_limit', {headers: {'User-Agent': UA}}); const j = await r.json(); remaining = j.resources.core.remaining; resetAt = j.resources.core.reset; console.log('core remaining', remaining, 'reset', new Date(resetAt * 1000).toISOString()); }
const REPOS = {go: 'geneontology/go-ontology', hpo: 'obophenotype/human-phenotype-ontology'};
const simp = e => {
  const o = {ev: e.event, t: e.created_at || e.submitted_at || null, actor: ps(e.actor?.login || e.user?.login), bot: (e.actor?.type || e.user?.type) === 'Bot'};
  if (e.commit_id) o.commit = e.commit_id;
  if (e.state_reason) o.sr = e.state_reason;
  if (e.label) o.label = e.label.name;
  if (e.event === 'commented') { o.body = mask(e.body); o.aa = e.author_association; }
  if (e.event === 'committed') { o.msg = mask(e.message); }
  if (e.source?.issue) { const s = e.source.issue; o.src = {repo: (s.repository?.full_name || s.repository_url?.split('/repos/')[1]), n: s.number, pr: !!s.pull_request, merged: s.pull_request?.merged_at || null, state: s.state, title: mask(s.title)}; }
  if (e.event === 'renamed') o.rename = {from: mask(e.rename?.from), to: mask(e.rename?.to)};
  return o;
};
for (const tag of ['go', 'hpo']) {
  const o = Object.values(JSON.parse(fs.readFileSync(`../D5k4/issues_${tag}.json`))).filter(x => x.s === 'closed' && x.c >= '2016').sort((a, b) => a.n - b.n);
  let seed = 20261007; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  const pool = o.slice(), pick = []; while (pick.length < 100) pick.push(pool.splice(Math.floor(rnd() * pool.length), 1)[0]);
  fs.writeFileSync(`sample_${tag}.json`, JSON.stringify(pick.map(x => x.n)));
  const out = `tl_${tag}.json`; let res = {}; try { res = JSON.parse(fs.readFileSync(out)); } catch {}
  for (const x of pick) { if (res[x.n]) continue;
    try {
      const u = `https://api.github.com/repos/${REPOS[tag]}/issues/${x.n}/timeline?per_page=100`;
      let {body, link} = await get(u); let ev = body; let pages = 1;
      const last = link && link.match(/<([^>]+)>;\s*rel="last"/);
      if (last) { const r2 = await get(last[1]); ev = ev.concat(r2.body); pages = 2; }
      res[x.n] = {n: x.n, c: x.c, x: x.x, sr: x.sr, lab: x.lab, sub: x.u, aa: x.aa, cm: x.cm, pages, events: ev.map(simp)};
      fs.writeFileSync(out, JSON.stringify(res));
      console.log(new Date().toISOString(), tag, x.n, 'events', ev.length, 'rem', remaining);
    } catch (e) { console.log('ERR', e.message.slice(0, 200)); if (e.message === 'budget') process.exit(0); }
  }
}
console.log('DONE');
