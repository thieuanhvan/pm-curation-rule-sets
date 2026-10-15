// R3 task 5: is low HPO release-file corroboration a provenance artefact? Uses cached ../../D5k4b/obo_*.json (current OBO
// releases) and ../W2 sample timelines. (a) share of terms carrying a tracker link / a creation date by creation year;
// (b) for inferred acceptances by ticket-opening period: corroborated, cited by any term (any date), any ID mentioned, mentioned
// IDs that pre-date the ticket, mentioned IDs without a creation date. No network.
import fs from 'fs';
const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'); process.chdir(HERE);
const {idsIn} = await import('../../D5k4b/classify_v2.mjs'); const OUT = {};
const per = y => y < 2019 ? '2016-18' : y < 2022 ? '2019-21' : '2022-26';
for (const tag of ['go', 'hpo']) {
  const obo = JSON.parse(fs.readFileSync(`../../D5k4b/obo_${tag}.json`)); const pfx = tag === 'go' ? 'GO:' : 'HP:';
  const terms = Object.entries(obo.ids).filter(([i, v]) => i.startsWith(pfx) && !v.altOf && !v.obs);
  const byY = {}; for (const [i, v] of terms) { const y = v.d ? v.d.slice(0, 4) : 'no_date'; const o = (byY[y] ||= {n: 0, tracker_link: 0}); o.n++; if (v.tr.length) o.tracker_link++; }
  const keep = {}; for (const [y, o] of Object.entries(byY)) if (y === 'no_date' || +y >= 2010) keep[y] = {...o, share_link: +(o.tracker_link / o.n).toFixed(3)};
  // max ID number by creation year (to show undated terms are old ones)
  const S = new Set(JSON.parse(fs.readFileSync(`../W2/sample_w2_${tag}.json`)).n);
  const tl = {}; for (const l of fs.readFileSync(`../W2/tl_w2_${tag}.jsonl`, 'utf8').split('\n')) if (l.trim()) { try { const r = JSON.parse(l); if (S.has(r.n)) tl[r.n] = r; } catch {} }
  const oc = JSON.parse(fs.readFileSync(`../W2/outcomes_w2_${tag}.json`)).filter(r => r.cls === 'ACC');
  const P = {};
  for (const r of oc) { const t = tl[r.n]; const p = per(+r.open.slice(0, 4)); const o = (P[p] ||= {n: 0, corroborated: 0, cited_by_any_term: 0, any_id_mentioned: 0, only_preexisting_ids: 0, mentioned_id_no_date: 0, no_id_no_citation: 0});
    o.n++; if (r.corroborated) o.corroborated++;
    const cited = (obo.byTicket[r.n] || []).length > 0; if (cited) o.cited_by_any_term++;
    const ids = idsIn(t).filter(i => obo.ids[i]); if (ids.length) o.any_id_mentioned++;
    if (!r.corroborated && ids.length && ids.every(i => obo.ids[i].d && obo.ids[i].d.slice(0, 10) < r.open.slice(0, 10))) o.only_preexisting_ids++;
    if (!r.corroborated && ids.some(i => !obo.ids[i].d)) o.mentioned_id_no_date++;
    if (!cited && !ids.length) o.no_id_no_citation++; }
  OUT[tag] = {terms_by_creation_year: keep, acc_by_open_period: P};
}
fs.writeFileSync('r3_t5_corrob.json', JSON.stringify(OUT, null, 1)); console.log(JSON.stringify(OUT));
