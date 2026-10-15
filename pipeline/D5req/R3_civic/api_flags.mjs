// R3 T6: read-only CIViC GraphQL probe (budget 4 requests, logged) to learn what the August 2021 bot flags said.
import fs from 'fs';
const URL = 'https://civicdb.org/api/graphql', LOG = 'cache/requests.log', BUDGET = 4;
async function post(q, tag) {
  const n = fs.existsSync(LOG) ? fs.readFileSync(LOG, 'utf8').split('\n').filter(Boolean).length : 0;
  if (n >= BUDGET) throw new Error('budget exhausted');
  fs.appendFileSync(LOG, new Date().toISOString() + ' ' + tag + '\n');
  const r = await fetch(URL, { method: 'POST', headers: { 'content-type': 'application/json', 'user-agent': 'pm-curation-rule-sets-research (polite, sequential)' }, body: JSON.stringify({ query: q }) });
  const j = await r.json(); await new Promise(s => setTimeout(s, 1500)); return j;
}
const step = process.argv[2];
if (step === 'intro') {
  const j = await post(`{ a: __type(name:"Flag"){ fields{ name type{ name kind ofType{ name kind } } } } b: __type(name:"FlagEvent"){ name } }`, 'introspect Flag');
  fs.writeFileSync('cache/flag_intro.json', JSON.stringify(j, null, 1)); console.log(JSON.stringify(j).slice(0, 3000));
} else {
  const ids = JSON.parse(fs.readFileSync('res_r3_t6.json')).bot_flag_ids_aug2021_sample;
  const body = ids.map(i => `f${i}: flag(id:${i}){ id state createdAt flaggable{ __typename name } comments(first:2){ nodes{ comment createdAt } } }`).join('\n');
  const j = await post(`{ ${body} }`, 'flags sample ' + ids.join(','));
  // strip user identities: query asks for none
  fs.writeFileSync('cache/flags_sample.json', JSON.stringify(j, null, 1)); console.log(JSON.stringify(j).slice(0, 6000));
}
