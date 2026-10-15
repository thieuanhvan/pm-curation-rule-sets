import {get} from './lib.mjs';
const qs = process.argv.slice(2);
for (const q of qs) {
  try { const {body, rem} = await get(`https://api.github.com/search/issues?q=${encodeURIComponent(q)}&per_page=2`, {delay: 6500});
    const it = body.items?.[0]; console.log(q, '=>', body.total_count, 'rem', rem, it ? JSON.stringify({c: it.created_at, s: it.state, sr: it.state_reason, aa: it.author_association, labels: it.labels.map(l => l.name)}) : ''); }
  catch (e) { console.log(q, 'ERR', e.message.slice(0, 150)); }
}
