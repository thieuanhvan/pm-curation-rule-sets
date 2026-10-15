// Minimal polite CIViC GraphQL client with a hard request budget (<= 30 for A6). Each call logged to cache/requests.log.
import fs from 'fs';
const URL="https://civicdb.org/api/graphql"; const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const LOG='cache/requests.log'; const BUDGET=30;
export async function post(q, tag){
  const n = fs.existsSync(LOG) ? fs.readFileSync(LOG,'utf8').split('\n').filter(Boolean).length : 0;
  if (n >= BUDGET) throw new Error('request budget exhausted');
  fs.appendFileSync(LOG, new Date().toISOString()+' '+tag+'\n');
  const r=await fetch(URL,{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite, sequential)"},body:JSON.stringify({query:q})});
  const j=await r.json(); await sleep(1500); return j;
}
