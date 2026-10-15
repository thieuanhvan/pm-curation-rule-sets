import fs from 'fs'; import {get} from './lib_wd.mjs';
const A = 'https://www.wikidata.org/w/api.php?format=json&formatversion=2&';
const froms = process.argv.slice(2);
for (const f of froms) {
  const out = `wd/raw_${f.replace(/[^A-Za-z0-9]/g, '_')}.json`; if (fs.existsSync(out)) continue;
  const u = A + 'action=query&generator=allpages&gapnamespace=4&gapprefix=' + encodeURIComponent('Property proposal/') + '&gapfrom=' + encodeURIComponent('Property proposal/' + f) + '&gaplimit=50&prop=revisions&rvprop=content|timestamp|user&rvslots=main';
  const {body} = await get(u, {delay: 12000});
  const pages = (body.query?.pages || []).map(p => ({t: p.title, ts: p.revisions?.[0]?.timestamp, c: p.revisions?.[0]?.slots?.main?.content}));
  fs.writeFileSync(out, JSON.stringify(pages)); console.log(f, pages.length);
}
