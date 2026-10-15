// R3 tasks 1-2 (no network). Inputs: ../W2/tl_w2_*.jsonl (sample of 200/tracker), ../W2/outcomes_w2_*.json, ../../D5k4/issues_*.json,
// ../../D5k4b/obo_*.json. Classifier ../../D5k4b/classify_v2.mjs is used unchanged; classify_v2_fixdplus.mjs is a copy with the
// REJ_KW '#d+' typo fixed (sensitivity only). Output: r3_t1_t2.json
import fs from 'fs';
const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'); process.chdir(HERE);
const V2 = await import('../../D5k4b/classify_v2.mjs'); const FX = await import('./classify_v2_fixdplus.mjs');
const REPO = {go: 'geneontology/go-ontology', hpo: 'obophenotype/human-phenotype-ontology'};
const OUT = {};
const strip = t => ({...t, sr: null, events: t.events.map(e => ({...e, sr: undefined}))}); // cascade without the state_reason signal
for (const tag of ['go', 'hpo']) {
  const S = new Set(JSON.parse(fs.readFileSync(`../W2/sample_w2_${tag}.json`)).n);
  const tl = {}; for (const l of fs.readFileSync(`../W2/tl_w2_${tag}.jsonl`, 'utf8').split('\n')) if (l.trim()) { try { const r = JSON.parse(l); if (S.has(r.n)) tl[r.n] = r; } catch {} }
  const obo = JSON.parse(fs.readFileSync(`../../D5k4b/obo_${tag}.json`));
  const oc = Object.fromEntries(JSON.parse(fs.readFileSync(`../W2/outcomes_w2_${tag}.json`)).map(r => [r.n, r]));
  const rows = [];
  for (const t of Object.values(tl)) {
    if (t.gone || t.s === 'open') continue;
    const a = V2.classify(t, REPO[tag]), b = FX.classify(t, REPO[tag]), c = V2.classify(strip(t), REPO[tag]);
    const closeEv = t.events.filter(e => e.ev === 'closed').at(-1);
    rows.push({n: t.n, close: a.closeT, sr: t.sr, srEv: closeEv?.sr || null, v2: a.cls, v2tier: a.tier, v2sig: a.sig, fix: b.cls, fixSig: b.sig, noSR: c.cls, noSRtier: c.tier, t});
  }
  // ---------- Task 1: state_reason as partial reference
  const pop = Object.values(JSON.parse(fs.readFileSync(`../../D5k4/issues_${tag}.json`))).filter(x => !x.pr && x.s === 'closed');
  const popSR = {}; for (const x of pop) { const y = x.x.slice(0, 4); (popSR[y] ||= {}); popSR[y][x.sr] = (popSR[y][x.sr] || 0) + 1; }
  const firstNP = pop.filter(x => x.sr === 'not_planned').map(x => x.x).sort()[0] || null;
  const post = rows.filter(r => r.close >= '2022-01-01');
  const cm = (key) => { const m = {}; for (const r of post) { const ref = r.sr === 'not_planned' ? 'not_planned' : r.sr; const k = `${ref}|${r[key]}`; m[k] = (m[k] || 0) + 1; } return m; };
  const pr = (key) => { const g = (ref, cls) => post.filter(r => (r.sr === 'not_planned') === (ref === 'NP') && r[key] === cls).length;
    const REJp = g('NP', 'REJ') / Math.max(1, g('NP', 'REJ') + g('C', 'REJ')), REJr = g('NP', 'REJ') / Math.max(1, post.filter(r => r.sr === 'not_planned').length);
    const ACCp = g('C', 'ACC') / Math.max(1, g('C', 'ACC') + g('NP', 'ACC')), ACCr = g('C', 'ACC') / Math.max(1, post.filter(r => r.sr !== 'not_planned').length);
    return {REJ_precision: +REJp.toFixed(3), REJ_recall: +REJr.toFixed(3), ACC_precision_vs_completed: +ACCp.toFixed(3), ACC_recall_vs_completed: +ACCr.toFixed(3)}; };
  const unc = post.filter(r => r.v2 === 'UNCLEAR');
  OUT[tag] = {
    population_state_reason_by_close_year: popSR, population_first_not_planned: firstNP,
    population_not_planned_share_2023plus: (() => { const p = pop.filter(x => x.x >= '2023'); return [p.filter(x => x.sr === 'not_planned').length, p.length]; })(),
    sample_closed: rows.length, sample_closed_2022plus: post.length,
    event_level_sr_2022plus: post.reduce((m, r) => (m[r.srEv || 'null'] = (m[r.srEv || 'null'] || 0) + 1, m), {}),
    pre2022_issue_sr: rows.filter(r => r.close < '2022').reduce((m, r) => (m[r.sr] = (m[r.sr] || 0) + 1, m), {}),
    confusion_v2: cm('v2'), confusion_cascade_without_SR_tier: cm('noSR'), metrics_v2: pr('v2'), metrics_without_SR_tier: pr('noSR'),
    not_planned_cases_without_SR_tier: post.filter(r => r.sr === 'not_planned').map(r => ({noSR: r.noSR, tier: r.noSRtier})),
    unclear_2022plus: unc.length, unclear_resolved_by_not_planned: unc.filter(r => r.sr === 'not_planned').length,
    // ---------- sensitivity
    bugfix_changes: rows.filter(r => r.v2 !== r.fix).map(r => ({from: r.v2, to: r.fix, close: r.close.slice(0, 4), sig: r.fixSig.filter(s => /#\d/.test(s))})),
    bugfix_n_changed: rows.filter(r => r.v2 !== r.fix).length,
    bugfix_counts: ['ACC', 'REJ', 'UNCLEAR'].reduce((m, k) => (m[k] = [rows.filter(r => r.v2 === k).length, rows.filter(r => r.fix === k).length], m), {}),
    unclear_to_rej: (() => { const A = rows.filter(r => r.v2 === 'ACC').length, R = rows.filter(r => r.v2 === 'REJ').length, U = rows.filter(r => r.v2 === 'UNCLEAR').length;
      return {acc_share_classified: +(A / (A + R)).toFixed(3), acc_share_unclear_as_rej: +(A / (A + R + U)).toFixed(3)}; })(),
  };
  // ---------- Task 2: what "acceptance" rests on (GO and HPO) and whether it looks like a term addition
  const ADD = /\+\s*\[Term\]|\+id: (GO|HP):\d{7}|\b(add(ed|ing|s)?|new|creat(e|ed|ing)|ntr)\b/i, OBS = /obsolet|\+is_obsolete|merge[sd]? (into|with)/i,
    EDIT = /\bsynonym|\bdef(inition)?\b|\bxref|\brelationship|\bis_a\b|\bparent|\brenam|\blabel\b|\bfix(ed)? /i;
  const acc = rows.filter(r => r.v2 === 'ACC');
  const mech = r => { const s = r.v2sig.join(' '); if (r.v2tier === 2) return s.includes('closed_by_commit') && !s.includes('merged_PR') ? 'closed_by_commit' : s.includes('merged_PR') ? 'merged_PR' : 'connected_PR';
    return r.v2tier >= 3 && r.v2tier < 4 ? 'comment_wording' : r.v2tier === 4 ? (s.includes('referenced_by_commit') ? 'referencing_commit_before_close' : 'id_in_last_comment') : 'other'; };
  const look = r => { // text of PR titles, commit messages and comments within 2 days after closure (masked bodies)
    const ce = Date.parse(r.close); const ev = r.t.events;
    const txt = ev.filter(e => (e.src && e.src.pr) || e.msg || (e.ev === 'commented' && Math.abs(Date.parse(e.t) - ce) <= 2 * 864e5)).map(e => [e.src?.title, e.msg, e.body].filter(Boolean).join(' ')).join('\n');
    const newId = (V2.idsIn(r.t)).some(i => obo.ids[i]?.d && obo.ids[i].d.slice(0, 10) >= r.t.c.slice(0, 10) && !obo.ids[i].altOf);
    return {corr: !!oc[r.n]?.corroborated, newIdMentioned: newId, add: /\+\s*\[Term\]/.test(txt) || /\+id: (GO|HP):\d{7}/.test(txt) || /\b(add(ed|ing)?|new|creat(e|ed|ing)|ntr)\b/i.test(ev.filter(e => e.src?.pr).map(e => e.src.title).join(' ')),
      obs: OBS.test(txt), edit: EDIT.test(txt) };
  };
  const T2 = {};
  for (const r of acc) { const m = mech(r), L = look(r); const o = (T2[m] ||= {n: 0, obo_corroborated: 0, new_id_or_term_stanza: 0, any_addition_evidence: 0, obsoletion_or_merge_words: 0, only_edit_words_no_addition: 0});
    o.n++; if (L.corr) o.obo_corroborated++; if (L.newIdMentioned || L.add) o.new_id_or_term_stanza++; if (L.corr || L.newIdMentioned || L.add) o.any_addition_evidence++; if (L.obs) o.obsoletion_or_merge_words++; if (!(L.corr || L.newIdMentioned || L.add) && L.edit) o.only_edit_words_no_addition++; }
  OUT[tag].task2_acceptance_mechanism = T2; OUT[tag].task2_n_ACC = acc.length;
}
fs.writeFileSync('r3_t1_t2.json', JSON.stringify(OUT, null, 1));
for (const tag of ['go', 'hpo']) { const o = {...OUT[tag]}; delete o.population_state_reason_by_close_year; console.log(tag, JSON.stringify(o)); }
