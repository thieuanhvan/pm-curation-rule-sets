// R3 task 1 add-on: same checks on the 100+100 pilot timelines (../../D5k4b/tl_*.json) not in the W2 sample. No network.
import fs from 'fs';
const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'); process.chdir(HERE);
const V2 = await import('../../D5k4b/classify_v2.mjs'); const FX = await import('./classify_v2_fixdplus.mjs');
const REPO = {go: 'geneontology/go-ontology', hpo: 'obophenotype/human-phenotype-ontology'}; const OUT = {};
const strip = t => ({...t, sr: null, events: t.events.map(e => ({...e, sr: undefined}))});
for (const tag of ['go', 'hpo']) {
  const S = new Set(JSON.parse(fs.readFileSync(`../W2/sample_w2_${tag}.json`)).n);
  const tl = Object.values(JSON.parse(fs.readFileSync(`../../D5k4b/tl_${tag}.json`))).filter(t => !S.has(t.n) && t.events && t.x);
  const r = tl.map(t => ({n: t.n, close: (t.events.filter(e => e.ev === 'closed').at(-1)?.t || t.x), sr: t.sr, v2: V2.classify(t, REPO[tag]).cls, fix: FX.classify(t, REPO[tag]).cls, noSR: V2.classify(strip(t), REPO[tag]).cls}));
  const post = r.filter(x => x.close >= '2022');
  OUT[tag] = {n_extra_closed: r.length, post2022: post.length, confusion_v2: post.reduce((m, x) => (m[x.sr + '|' + x.v2] = (m[x.sr + '|' + x.v2] || 0) + 1, m), {}),
    confusion_noSR: post.reduce((m, x) => (m[x.sr + '|' + x.noSR] = (m[x.sr + '|' + x.noSR] || 0) + 1, m), {}), bugfix_changed: r.filter(x => x.v2 !== x.fix).map(x => [x.v2, x.fix])};
}
fs.writeFileSync('r3_t1_pilot.json', JSON.stringify(OUT, null, 1)); console.log(JSON.stringify(OUT));
