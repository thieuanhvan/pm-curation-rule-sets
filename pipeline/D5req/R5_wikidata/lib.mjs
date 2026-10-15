// polite MediaWiki client: fixed UA, >= 1.1 s between requests, maxlag, request log
// maxlag omitted: read-only queries; Wikidata's maxlag includes WDQS lag (~10 s on 07/10/2026) and blocked all reads
import fs from 'fs';
const UA = 'pm-curation-rule-sets-research (contact via GitHub thieuanhvan)';
const LOG = new URL('./requests.log', import.meta.url);
export const API = 'https://www.wikidata.org/w/api.php';
const sleep = ms => new Promise(r => setTimeout(r, ms));
let last = 0;
export async function api(params) {
  const p = new URLSearchParams({format: 'json', formatversion: '2', ...params});
  for (let attempt = 0; attempt < 6; attempt++) {
    const wait = last + 1100 - Date.now(); if (wait > 0) await sleep(wait);
    last = Date.now();
    fs.appendFileSync(LOG, new Date().toISOString() + ' ' + p.toString().slice(0, 200) + '\n');
    let r; try { r = await fetch(API + '?' + p, {headers: {'User-Agent': UA, 'Accept-Encoding': 'gzip'}}); } catch (e) { await sleep(5000 * (attempt + 1)); continue; }
    if (r.status === 429 || r.status >= 500) { await sleep(10000 * (attempt + 1)); continue; }
    const b = await r.json();
    if (b.error?.code === 'maxlag') { await sleep(6000 * (attempt + 1)); continue; }
    if (b.error) throw new Error(JSON.stringify(b.error));
    return b;
  }
  throw new Error('failed after retries');
}
// iterate continuation
export async function* paged(params) {
  let cont = {};
  while (true) { const b = await api({...params, ...cont}); yield b; if (!b.continue) break; cont = b.continue; }
}
