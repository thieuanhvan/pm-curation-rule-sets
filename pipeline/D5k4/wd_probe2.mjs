import {get} from './lib_wd.mjs';
const A = 'https://www.wikidata.org/w/api.php?format=json&formatversion=2&';
const r1 = await get(A + 'action=query&list=allpages&apnamespace=4&apprefix=' + encodeURIComponent('Property proposal/') + '&aplimit=20', {delay: 1000});
console.log(JSON.stringify(r1.body).slice(0, 1800));
