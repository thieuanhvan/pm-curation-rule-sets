// (a) all subpages Wikidata:Property proposal/* (ns 4), incl. redirects flag; (b) property creation log ns 120
import fs from 'fs'; import {paged} from './lib.mjs';
if (!fs.existsSync('raw/allpages.json')) {
  const out = [];
  for await (const b of paged({action: 'query', list: 'allpages', apnamespace: '4', apprefix: 'Property proposal/', aplimit: '500'})) { out.push(...b.query.allpages.map(p => ({id: p.pageid, t: p.title}))); process.stdout.write(out.length + ' '); }
  // redirects separately
  const red = [];
  for await (const b of paged({action: 'query', list: 'allpages', apnamespace: '4', apprefix: 'Property proposal/', aplimit: '500', apfilterredir: 'redirects'})) red.push(...b.query.allpages.map(p => p.pageid));
  const rs = new Set(red); out.forEach(p => p.redirect = rs.has(p.id));
  fs.writeFileSync('raw/allpages.json', JSON.stringify(out)); console.log('\nallpages', out.length, 'redirects', red.length);
}
if (!fs.existsSync('raw/prop_create_log.json')) {
  const out = [];
  for await (const b of paged({action: 'query', list: 'logevents', letype: 'create', lenamespace: '120', lelimit: '500', leprop: 'title|timestamp|ids', ledir: 'newer'})) { out.push(...b.query.logevents.map(e => ({t: e.title, ts: e.timestamp, pageid: e.pageid}))); process.stdout.write(out.length + ' '); }
  fs.writeFileSync('raw/prop_create_log.json', JSON.stringify(out)); console.log('\ncreate log', out.length);
}
