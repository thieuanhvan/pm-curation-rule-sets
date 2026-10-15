import {get} from './lib_wd.mjs';
const A = 'https://www.wikidata.org/w/api.php?format=json&formatversion=2&';
const r1 = await get(A + 'action=query&list=logevents&letype=create&lenamespace=4&leprefix=' + encodeURIComponent('Wikidata:Property proposal/') + '&lelimit=5&ledir=newer', {delay: 1000});
console.log(JSON.stringify(r1.body).slice(0, 1500));
const r2 = await get(A + 'action=query&list=logevents&letype=create&lenamespace=120&lelimit=3&ledir=newer', {delay: 1000});
console.log(JSON.stringify(r2.body).slice(0, 1000));
