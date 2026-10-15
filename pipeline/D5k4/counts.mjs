import {get} from './lib.mjs';
const repos = process.argv.slice(2);
for (const r of repos) {
  for (const t of ['pr', 'issue']) {
    try { const {body, rem} = await get(`https://api.github.com/search/issues?q=repo:${r}+type:${t}&per_page=1`, {delay: 6500});
      console.log(r, t, body.total_count, 'rem', rem, body.items?.[0]?.created_at); }
    catch (e) { console.log(r, t, 'ERR', e.message.slice(0, 150)); }
  }
}
