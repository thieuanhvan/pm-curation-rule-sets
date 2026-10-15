import fs from 'fs';
const CNT = new URL('./reqcount_wd.json', import.meta.url);
const UA = 'pm-curation-rule-sets-research (academic process-mining feasibility; non-commercial)';
export const sleep = ms => new Promise(r => setTimeout(r, ms));
export async function get(url, {delay = 1500, json = true} = {}) {
  let c = {n: 0, log: []}; try { c = JSON.parse(fs.readFileSync(CNT)); } catch {}
  if (c.n >= 290) throw new Error('request budget reached');
  await sleep(delay);
  c.n++; c.log.push(url.slice(0, 160));
  fs.writeFileSync(CNT, JSON.stringify(c, null, 0));
  const r = await fetch(url, {headers: {'User-Agent': UA, 'Accept': 'application/vnd.github+json'}});
  const rem = r.headers.get('x-ratelimit-remaining');
  if (!r.ok) { const t = await r.text(); throw new Error(`HTTP ${r.status} ${url} rem=${rem} ${t.slice(0, 200)}`); }
  const body = json ? await r.json() : await r.text();
  return {body, rem, link: r.headers.get('link')};
}
