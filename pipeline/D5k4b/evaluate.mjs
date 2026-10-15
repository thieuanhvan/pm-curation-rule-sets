import fs from 'fs'; const {classify, idsIn} = await import(process.env.CLS || './classify_frozen_20261007.mjs'); const SUF = process.env.SUF || 'v1';
const SUB = process.env.SUBSET || 'all'; const devGo = new Set(JSON.parse(fs.readFileSync('dev_set_go.json'))); const hpoS = JSON.parse(fs.readFileSync('sample_hpo.json'));
const keep = (tag, n) => SUB === 'all' ? true : SUB === 'heldout' ? (tag === 'go' ? !devGo.has(+n) : hpoS.indexOf(+n) >= 50) : true;
const D = 864e5; const REPO = {go: 'geneontology/go-ontology', hpo: 'obophenotype/human-phenotype-ontology'};
const FROM = {go: '2016', hpo: '2014'}; // same queue windows as D5k4 (go_2016, hpo_2014)
const q = (a, p) => { a = a.filter(Number.isFinite).sort((x, y) => x - y); return a.length ? +a[Math.floor(p * (a.length - 1))].toFixed(1) : null; };
const wilson = (k, n, z = 1.96) => { if (!n) return null; const p = k / n, d = 1 + z * z / n, c = (p + z * z / (2 * n)) / d, h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return [+(c - h).toFixed(3), +(c + h).toFixed(3)]; };
const kappa = (m) => { const n = m.aa + m.ab + m.ba + m.bb; if (!n) return null; const po = (m.aa + m.bb) / n, pe = ((m.aa + m.ab) * (m.aa + m.ba) + (m.ba + m.bb) * (m.ab + m.bb)) / (n * n); return +((po - pe) / (1 - pe)).toFixed(3); };
const out = {};
for (const tag of ['go', 'hpo']) {
  let tl = {}; try { tl = JSON.parse(fs.readFileSync(`tl_${tag}.json`)); } catch { continue; }
  const obo = JSON.parse(fs.readFileSync(`obo_${tag}.json`));
  const pop = Object.values(JSON.parse(fs.readFileSync(`../D5k4/issues_${tag}.json`))).filter(x => x.c >= FROM[tag]);
  const rows = [];
  for (const t of Object.values(tl).filter(t => keep(tag, t.n))) {
    const r = classify(t, REPO[tag]);
    const open = t.c.slice(0, 10), lo = new Date(Date.parse(t.c) - D).toISOString().slice(0, 10), hi = new Date(Date.parse(r.closeT) + 90 * D).toISOString().slice(0, 10);
    const cite = obo.byTicket[t.n] || [];
    const v1new = cite.filter(i => obo.ids[i].d && obo.ids[i].d.slice(0, 10) >= lo);
    const v1any = cite.length > 0;
    const v2 = idsIn(t).filter(i => obo.ids[i] && obo.ids[i].d && obo.ids[i].d.slice(0, 10) >= lo && obo.ids[i].d.slice(0, 10) <= hi);
    // position u at decision time among all queued tickets of the population window
    const dec = Date.parse(r.closeT), arr = Date.parse(t.c);
    const queue = pop.filter(x => Date.parse(x.c) <= dec && (x.s === 'open' || Date.parse(x.x) >= dec));
    const L = queue.length, newer = queue.filter(x => Date.parse(x.c) > arr).length;
    rows.push({n: t.n, cls: r.cls, tier: r.tier, sig: r.sig, open: t.c, close: r.closeT, ttdD: +((dec - arr) / D).toFixed(2), u: L > 1 ? +(newer / (L - 1)).toFixed(3) : null, L, v1new: v1new.length, v1any, v2: v2.length, comments: t.events.filter(e => e.ev === 'commented').length, sr: t.sr});
  }
  const n = rows.length, by = c => rows.filter(r => r.cls === c);
  const acc = by('ACC'), rej = by('REJ'), unc = by('UNCLEAR'); const cl = acc.length + rej.length;
  const R = {n, classified: cl, coverage: +(cl / n).toFixed(3), coverageCI: wilson(cl, n), acc: acc.length, rej: rej.length, unclear: unc.length,
    acceptRate: +(acc.length / cl).toFixed(3), acceptRateCI: wilson(acc.length, cl),
    tiers: rows.reduce((m, r) => (m[r.cls + '_T' + r.tier] = (m[r.cls + '_T' + r.tier] || 0) + 1, m), {})};
  // agreement with independent signal: positive = (V1 tracker term created >= open) OR (V2 mentioned ID created in [open-1d, close+90d])
  for (const [name, f] of [['V1_tracker_new', r => r.v1new > 0], ['V1_tracker_any', r => r.v1any], ['V2_newID', r => r.v2 > 0], ['V1orV2', r => r.v1new > 0 || r.v2 > 0]]) {
    const m = {aa: acc.filter(f).length, ab: acc.filter(r => !f(r)).length, ba: rej.filter(f).length, bb: rej.filter(r => !f(r)).length};
    R['agree_' + name] = {ACC_pos: m.aa, ACC_neg: m.ab, REJ_pos: m.ba, REJ_neg: m.bb, agreement: +((m.aa + m.bb) / cl).toFixed(3), kappa: kappa(m), UNCLEAR_pos: unc.filter(f).length, UNCLEAR_neg: unc.filter(r => !f(r)).length};
  }
  const tt = a => ({n: a.length, med: q(a.map(r => r.ttdD), .5), p90: q(a.map(r => r.ttdD), .9), le1d: a.length ? +(a.filter(r => r.ttdD <= 1).length / a.length).toFixed(3) : null});
  const pos = a => { const u = a.map(r => r.u).filter(Number.isFinite); return {n: u.length, mean: u.length ? +(u.reduce((s, x) => s + x, 0) / u.length).toFixed(3) : null, newest10: u.length ? +(u.filter(x => x <= .1).length / u.length).toFixed(3) : null}; };
  R.ttd = {ACC: tt(acc), REJ: tt(rej), UNCLEAR: tt(unc), all: tt(rows)}; R.position = {ACC: pos(acc), REJ: pos(rej), all: pos(rows)};
  out[tag] = R; fs.writeFileSync(`rows_${tag}_${SUF}_${SUB}.json`, JSON.stringify(rows, null, 0));
  // population-level extension (offline, OBO only): closed tickets cited by a new term vs not
  const pc = pop.filter(x => x.s === 'closed' && x.c >= '2016').map(x => { const lo = new Date(Date.parse(x.c) - D).toISOString().slice(0, 10); const c = (obo.byTicket[x.n] || []).some(i => obo.ids[i].d && obo.ids[i].d.slice(0, 10) >= lo); return {c, d: (Date.parse(x.x) - Date.parse(x.c)) / D}; });
  R.population_tracker = {nClosed2016: pc.length, citedNew: pc.filter(r => r.c).length, share: +(pc.filter(r => r.c).length / pc.length).toFixed(3), ttd_cited: {med: q(pc.filter(r => r.c).map(r => r.d), .5), p90: q(pc.filter(r => r.c).map(r => r.d), .9)}, ttd_notcited: {med: q(pc.filter(r => !r.c).map(r => r.d), .5), p90: q(pc.filter(r => !r.c).map(r => r.d), .9)}, oboVersion: obo.version};
}
fs.writeFileSync(`results_k4b_${SUF}_${SUB}.json`, JSON.stringify(out, null, 1)); console.log(JSON.stringify(out, null, 1));
