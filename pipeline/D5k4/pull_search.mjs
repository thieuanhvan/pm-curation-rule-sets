// pull all issues for a search query, partitioned by created date so each slice < 1000 results
import fs from 'fs'; import crypto from 'crypto'; import {get} from './lib.mjs';
const [tag, base, y0, y1] = process.argv.slice(2);
const SALT = process.env.P17_SALT;
export const ps = s => s ? 'u_' + crypto.createHash('sha256').update(SALT + s.toLowerCase()).digest('hex').slice(0, 10) : null;
const out = `issues_${tag}.json`; let items = {}; try { items = JSON.parse(fs.readFileSync(out)); } catch {}
const slim = it => ({n: it.number, c: it.created_at, x: it.closed_at, s: it.state, sr: it.state_reason, u: ps(it.user?.login), ubot: it.user?.type === 'Bot', aa: it.author_association,
  lab: it.labels.map(l => l.name), asg: (it.assignees || []).map(a => ps(a.login)), cm: it.comments, pr: !!it.pull_request});
async function slice(a, b) {
  const q = `${base} created:${a}..${b}`;
  let page = 1, total = null;
  while (true) {
    const {body} = await get(`https://api.github.com/search/issues?q=${encodeURIComponent(q)}&per_page=100&page=${page}&sort=created&order=asc`, {delay: 6500});
    total = body.total_count;
    if (page === 1 && total > 1000) { // split
      const da = new Date(a), db = new Date(b); const mid = new Date((+da + +db) / 2).toISOString().slice(0, 10);
      console.log('split', a, b, total); await slice(a, mid); const nxt = new Date(+new Date(mid) + 864e5).toISOString().slice(0, 10); await slice(nxt, b); return;
    }
    for (const it of body.items) items[it.number] = slim(it);
    fs.writeFileSync(out, JSON.stringify(items));
    console.log(tag, a, b, 'page', page, 'got', body.items.length, 'total', total, 'have', Object.keys(items).length);
    if (body.items.length < 100 || page * 100 >= total) break; page++;
  }
}
for (let y = +y0; y <= +y1; y++) await slice(`${y}-01-01`, `${y}-12-31`);
console.log('DONE', tag, Object.keys(items).length);
