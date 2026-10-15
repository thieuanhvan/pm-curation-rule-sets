// (1) properties by creation year: allpages ns 120 + first-revision timestamps on a pid grid with binary search at year boundaries
// (3) sample of 100 properties created since 2016: proposal link on talk page; (2b) status categories of pending proposals
import fs from 'fs'; import {api, paged} from './lib.mjs';
const J = f => JSON.parse(fs.readFileSync(f));
if (!fs.existsSync('raw/props.json')) { const out = [];
  for await (const b of paged({action: 'query', list: 'allpages', apnamespace: '120', aplimit: '500'})) out.push(...b.query.allpages.map(p => +p.title.slice(10)));
  out.sort((a, b) => a - b); fs.writeFileSync('raw/props.json', JSON.stringify(out)); console.log('existing properties', out.length, 'max', out[out.length - 1]); }
const P = J('raw/props.json');
const cache = fs.existsSync('raw/firstrev.json') ? J('raw/firstrev.json') : {};
async function first(pid) { if (cache[pid]) return cache[pid];
  const b = await api({action: 'query', prop: 'revisions', titles: 'Property:P' + pid, rvdir: 'newer', rvlimit: '1', rvprop: 'timestamp'});
  const ts = b.query.pages[0].revisions?.[0]?.timestamp; cache[pid] = ts; fs.writeFileSync('raw/firstrev.json', JSON.stringify(cache)); return ts; }
// grid on index of existing pids
const STEP = 100; const grid = []; for (let i = 0; i < P.length; i += STEP) grid.push(i); grid.push(P.length - 1);
for (const i of grid) await first(P[i]);
// boundaries: first index with ts >= YYYY-01-01
const bounds = {};
for (let y = 2013; y <= 2026; y++) { const B = `${y}-01-01`;
  let lo = 0, hi = P.length; // find first i with ts>=B ; use grid to bracket
  for (const i of grid) { if (cache[P[i]] < B) lo = i + 1; else { hi = i; break; } }
  while (lo < hi) { const m = (lo + hi) >> 1; if ((await first(P[m])) < B) lo = m + 1; else hi = m; }
  bounds[y] = lo; }
const perYear = {}; for (let y = 2013; y <= 2026; y++) perYear[y] = (y < 2026 ? bounds[y + 1] : P.length) - bounds[y];
const firstPid = Object.fromEntries(Object.entries(bounds).map(([y, i]) => [y, P[i]]));
fs.writeFileSync('raw/prop_years.json', JSON.stringify({perYear, firstPidOfYear: firstPid, nExisting: P.length, maxPid: P[P.length - 1], note: 'existing (non-deleted) properties; creation = first revision; boundaries exact by binary search'}, null, 1));
console.log(perYear, firstPid);
// (3) talk-page sample
if (!fs.existsSync('raw/talk_sample.json')) {
  let s = 20261007; const rnd = () => (s = (s * 1103515245 + 12345) % 2147483648) / 2147483648;
  const pool = P.slice(bounds[2016]); const pick = new Set(); while (pick.size < 100) pick.add(pool[Math.floor(rnd() * pool.length)]);
  const ids = [...pick].sort((a, b) => a - b); const out = [];
  for (let k = 0; k < ids.length; k += 50) {
    const b = await api({action: 'query', prop: 'revisions', rvprop: 'content', rvslots: 'main', titles: ids.slice(k, k + 50).map(i => 'Property talk:P' + i).join('|')});
    for (const p of b.query.pages) { const c = p.revisions?.[0]?.slots?.main?.content || ''; const m = c.match(/\|\s*proposal discussion\s*=\s*([^\n|]*)/i);
      out.push({pid: +p.title.slice(15), talkExists: !p.missing, proposalParam: m ? m[1].trim().slice(0, 200) : null}); } }
  fs.writeFileSync('raw/talk_sample.json', JSON.stringify(out)); }
// (2b) categories of currently pending pages
if (fs.existsSync('wd_cases_census.json') && !fs.existsSync('raw/pending_cats.json')) {
  const pend = J('wd_cases_census.json').filter(x => x.kind === 'pending').slice(0, 50).map(x => 'Wikidata:Property proposal/' + x.id);
  const b = await api({action: 'query', prop: 'categories', cllimit: 'max', titles: pend.join('|')});
  const cats = {}; for (const p of b.query.pages) for (const c of p.categories || []) cats[c.title] = (cats[c.title] || 0) + 1;
  const names = Object.keys(cats).slice(0, 50); const b2 = await api({action: 'query', prop: 'categoryinfo', titles: names.join('|')});
  fs.writeFileSync('raw/pending_cats.json', JSON.stringify({catsAmongPending: cats, info: b2.query.pages.map(p => [p.title, p.categoryinfo?.pages])}, null, 1)); console.log('cats done'); }
