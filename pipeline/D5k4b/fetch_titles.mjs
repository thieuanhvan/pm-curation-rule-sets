// Fetch HPO ticket titles via search API (separate 10/min limit), for title->ontology-label independent check.
import fs from 'fs';
const UA = 'pm-curation-rule-sets-research (academic process-mining feasibility; non-commercial)';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const mask = t => (t || '').replace(/@([A-Za-z0-9-]{1,39})/g, '@user');
const sample = new Set(JSON.parse(fs.readFileSync('sample_hpo.json')));
const out = 'titles_hpo.json'; const T = {};
const base = 'repo:obophenotype/human-phenotype-ontology is:issue label:"new term request"';
for (const [a, b] of [['2016-01-01', '2017-12-31'], ['2018-01-01', '2020-12-31'], ['2021-01-01', '2022-12-31'], ['2023-01-01', '2024-12-31'], ['2025-01-01', '2026-12-31']]) {
  for (let page = 1; page <= 10; page++) {
    let c = JSON.parse(fs.readFileSync('reqcount.json')); if (c.n >= 255) { console.log('budget'); process.exit(0); }
    await sleep(7000); c.n++; c.log.push('search ' + a + ' p' + page); fs.writeFileSync('reqcount.json', JSON.stringify(c));
    const r = await fetch(`https://api.github.com/search/issues?q=${encodeURIComponent(base + ` created:${a}..${b}`)}&per_page=100&page=${page}&sort=created&order=asc`, {headers: {'User-Agent': UA, 'Accept': 'application/vnd.github+json'}});
    if (!r.ok) { console.log('HTTP', r.status, r.headers.get('x-ratelimit-remaining'), r.headers.get('x-ratelimit-reset')); await sleep(65000); page--; continue; }
    const j = await r.json(); for (const it of j.items) if (sample.has(it.number)) T[it.number] = mask(it.title);
    fs.writeFileSync(out, JSON.stringify(T)); console.log(a, page, j.items.length, j.total_count, 'have', Object.keys(T).length);
    if (page * 100 >= j.total_count) break;
  }
}
