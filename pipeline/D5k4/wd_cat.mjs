import {get} from './lib_wd.mjs';
const A = 'https://www.wikidata.org/w/api.php?format=json&formatversion=2&';
const r = await get(A + 'action=query&prop=categories&cllimit=50&titles=' + encodeURIComponent('Wikidata:Property proposal/E-CRIS.SR ID|Wikidata:Property proposal/Malta company ID'), {delay: 8000});
console.log(JSON.stringify(r.body.query.pages.map(p => [p.title, (p.categories||[]).map(c => c.title)])));
const cats = [...new Set(r.body.query.pages.flatMap(p => (p.categories||[]).map(c => c.title)))].join('|');
const r2 = await get(A + 'action=query&prop=categoryinfo&titles=' + encodeURIComponent(cats), {delay: 8000});
console.log(JSON.stringify(r2.body.query.pages.map(p => [p.title, p.categoryinfo?.pages])));
