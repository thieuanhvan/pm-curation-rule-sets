// census pull: content + last-edit ts of every Wikidata:Property proposal/* page (50 per request), chunked files
import fs from 'fs'; import {api} from './lib.mjs';
fs.mkdirSync('raw/content', {recursive: true});
const all = JSON.parse(fs.readFileSync('raw/allpages.json'));
let k = 0; let cont = {};
const st = fs.existsSync('raw/content/_state.json') ? JSON.parse(fs.readFileSync('raw/content/_state.json')) : {k: 0, cont: {}};
k = st.k; cont = st.cont; if (st.done) { console.log('already done'); process.exit(0); }
while (true) {
  const b = await api({action: 'query', generator: 'allpages', gapnamespace: '4', gapprefix: 'Property proposal/', gaplimit: '50', gapfilterredir: 'nonredirects', prop: 'revisions', rvprop: 'content|timestamp', rvslots: 'main', ...cont});
  const pages = (b.query?.pages || []).map(p => ({id: p.pageid, t: p.title, ts: p.revisions?.[0]?.timestamp, c: p.revisions?.[0]?.slots?.main?.content ?? null}));
  fs.writeFileSync(`raw/content/c_${String(k).padStart(4, '0')}.json`, JSON.stringify(pages)); k++;
  if (!b.continue) { fs.writeFileSync('raw/content/_state.json', JSON.stringify({k, done: true})); break; }
  cont = b.continue; fs.writeFileSync('raw/content/_state.json', JSON.stringify({k, cont}));
  if (k % 20 === 0) console.log(new Date().toISOString(), k, pages[pages.length - 1]?.t);
}
console.log('done', k);
