// Build an index from the current OBO releases: id -> {date, obsolete, trackers[]}, ticket -> [ids]
import fs from 'fs';
for (const [tag, file, repo] of [['go', 'go.obo', 'geneontology/go-ontology'], ['hpo', 'hp.obo', 'obophenotype/human-phenotype-ontology']]) {
  const txt = fs.readFileSync(file, 'utf8'); const ids = {}, byTicket = {};
  const re = new RegExp(String.raw`github[.]com/${repo}/issues/([0-9]+)`, "g");
  for (const blk of txt.split(/\n\[(?:Term|Typedef)\]\n/).slice(1)) {
    const id = (blk.match(/^id: (\S+)/m) || [])[1]; if (!id) continue;
    const d = (blk.match(/^creation_date: (\S+)/m) || blk.match(/^property_value: terms:date "([^"]+)"/m) || [])[1] || null;
    const alt = [...blk.matchAll(/^alt_id: (\S+)/gm)].map(m => m[1]);
    const tr = [...new Set([...blk.matchAll(re)].map(m => +m[1]))];
    ids[id] = {d, obs: /^is_obsolete: true/m.test(blk), tr, rb: (blk.match(/^replaced_by: (\S+)/m) || [])[1] || null};
    for (const a of alt) ids[a] ||= {d, obs: false, tr: [], altOf: id};
    for (const t of tr) (byTicket[t] ||= []).push(id);
  }
  fs.writeFileSync(`obo_${tag}.json`, JSON.stringify({version: (txt.match(/^data-version: (.+)$/m) || [])[1], ids, byTicket}));
  const iss = Object.values(JSON.parse(fs.readFileSync(`../D5k4/issues_${tag}.json`))).filter(x => x.s === 'closed' && x.c >= '2016');
  const cited = iss.filter(x => byTicket[x.n]);
  const cNew = iss.filter(x => (byTicket[x.n] || []).some(i => ids[i].d && ids[i].d >= x.c.slice(0, 10)));
  console.log(tag, 'terms', Object.keys(ids).length, 'withDate', Object.values(ids).filter(v => v.d).length, 'tickets cited', Object.keys(byTicket).length, '| closed 2016+', iss.length, 'cited', cited.length, (cited.length / iss.length).toFixed(3), 'cited by term created>=open', cNew.length, (cNew.length / iss.length).toFixed(3));
}
