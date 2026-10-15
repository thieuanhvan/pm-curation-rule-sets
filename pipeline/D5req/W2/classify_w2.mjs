// W2: outcomes for the 500-ticket samples: rule classifier v2 (../../D5k4b/classify_v2.mjs, unchanged) on closed tickets,
// OBO corroboration (as D5k4b/evaluate.mjs), actual closer from the timeline, service position u at decision time
// against the full ticket queue (all tickets of the tracker label, any open date), all-queue and alive<=365 d variants.
import fs from 'fs';
const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'); process.chdir(HERE);
const {classify, idsIn} = await import('../../D5k4b/classify_v2.mjs');
const D = 864e5; const REPO = {go: 'geneontology/go-ontology', hpo: 'obophenotype/human-phenotype-ontology'};
const SN = {go: new Set(JSON.parse(fs.readFileSync('sample_w2_go.json')).n), hpo: new Set(JSON.parse(fs.readFileSync('sample_w2_hpo.json')).n)}; // 07/10: sample cut to 300
const out = {};
for (const tag of ['go', 'hpo']) {
  const tl = {}; for (const l of fs.readFileSync(`tl_w2_${tag}.jsonl`, 'utf8').split('\n')) if (l.trim()) { try { const r = JSON.parse(l); if (SN[tag].has(r.n)) tl[r.n] = r; } catch {} }
  const obo = JSON.parse(fs.readFileSync(`../../D5k4b/obo_${tag}.json`));
  const all = Object.values(JSON.parse(fs.readFileSync(`../../D5k4/issues_${tag}.json`))).filter(x => !x.pr);
  const qa = all.map(x => [Date.parse(x.c), x.s === 'open' ? Infinity : Date.parse(x.x)]);
  const rows = [];
  for (const t of Object.values(tl)) {
    if (t.gone) { rows.push({n: t.n, gone: t.gone}); continue; }
    const closes = t.events.filter(e => e.ev === 'closed'); const fin = closes.at(-1);
    const isOpen = t.s === 'open';
    const row = {n: t.n, open: t.c, state: t.s, sub: t.sub, subAA: t.aa, nEvents: t.events.length, pages: t.pages, src: t.src,
      nCloses: closes.length, nReopen: t.events.filter(e => e.ev === 'reopened').length};
    if (!isOpen) {
      const r = classify(t, REPO[tag]);
      const lo = new Date(Date.parse(t.c) - D).toISOString().slice(0, 10), hi = new Date(Date.parse(r.closeT) + 90 * D).toISOString().slice(0, 10);
      const cite = obo.byTicket[t.n] || [];
      const v1new = cite.filter(i => obo.ids[i].d && obo.ids[i].d.slice(0, 10) >= lo).length;
      const v2 = idsIn(t).filter(i => obo.ids[i] && obo.ids[i].d && obo.ids[i].d.slice(0, 10) >= lo && obo.ids[i].d.slice(0, 10) <= hi).length;
      const dec = Date.parse(r.closeT), arr = Date.parse(t.c);
      let L = 0, newer = 0, La = 0, newerA = 0;
      for (const [a, x] of qa) { if (a <= dec && x >= dec) { L++; if (a > arr) newer++; if (dec - a <= 365 * D || a === arr) { La++; if (a > arr) newerA++; } } }
      Object.assign(row, {cls: r.cls, tier: r.tier, sig: r.sig, close: r.closeT, ttdD: +((dec - arr) / D).toFixed(3), closeSR: fin?.sr || t.sr || null,
        closer: fin?.actor || null, closerBot: !!fin?.bot, closedByCommit: !!fin?.commit, firstAssignee: (t.asg || [])[0] || null,
        v1new, v2, corroborated: v1new > 0 || v2 > 0, u: L > 1 ? +(newer / (L - 1)).toFixed(4) : null, L, uAlive365: (dec - arr <= 365 * D && La > 1) ?  +(newerA / (La - 1)).toFixed(4) : null, Lalive: La});
      // 07/10 fix: decisions on tickets older than 365 d are outside the live queue (as in W3/CIViC); before, they scored u = 1 by construction
    }
    rows.push(row);
  }
  rows.sort((a, b) => a.n - b.n);
  fs.writeFileSync(`outcomes_w2_${tag}.json`, JSON.stringify(rows));
  const cl = rows.filter(r => r.cls); const by = k => cl.filter(r => r.cls === k).length;
  out[tag] = {n: rows.length, open: rows.filter(r => r.state === 'open').length, closed: cl.length, ACC: by('ACC'), REJ: by('REJ'), UNCLEAR: by('UNCLEAR'), gone: rows.filter(r => r.gone).length};
}
console.log(JSON.stringify(out));
