// W2 fix (07/10): timelines fetched by fetch_w2.mjs lacked the submitter because the D5k4 issue list
// has no author field. Fetch /issues/{n} once per affected ticket and add sub (same first-stage
// pseudonym as fetch_w2.mjs) and ubot. Rewrites tl_w2_{go,hpo}.jsonl in place (backup *.bak).
import fs from 'fs'; import crypto from 'crypto';
const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
process.chdir(HERE);
const SALT = process.env.P17_SALT;
const ps = s => s ? 'u_' + crypto.createHash('sha256').update(SALT + s.toLowerCase()).digest('hex').slice(0, 10) : null;
const UA = 'pm-curation-rule-sets-research (contact via GitHub thieuanhvan)';
const AUTH = process.env.GITHUB_TOKEN ? {Authorization: 'Bearer ' + process.env.GITHUB_TOKEN} : {};
const REPOS = {go: 'geneontology/go-ontology', hpo: 'obophenotype/human-phenotype-ontology'};
const sleep = ms => new Promise(r => setTimeout(r, ms));
for (const tag of ['go', 'hpo']) {
  const f = `tl_w2_${tag}.jsonl`, lines = fs.readFileSync(f, 'utf8').split('\n').filter(l => l.trim());
  fs.writeFileSync(f + '.bak', lines.join('\n') + '\n');
  let fixed = 0, fail = 0;
  const out = [];
  for (const l of lines) {
    const r = JSON.parse(l);
    if (!('sub' in r) && !r.gone) {
      const res = await fetch(`https://api.github.com/repos/${REPOS[tag]}/issues/${r.n}`, {headers: {...AUTH, 'User-Agent': UA, 'Accept': 'application/vnd.github+json'}});
      if (res.ok) { const j = await res.json(); r.sub = ps(j.user?.login); r.ubot = j.user?.type === 'Bot'; fixed++; } else fail++;
      await sleep(300);
    }
    out.push(JSON.stringify(r));
  }
  fs.writeFileSync(f, out.join('\n') + '\n');
  console.log(tag, 'fixed', fixed, 'failed', fail);
}
