// R5 E: simulator sanity. (1) EDF timeliness bounds with and without withdrawal tokens (first decision = rejection by the submitter).
// (2) Expiry vs as-is under imputed eventual acceptance of never-decided items p = 0, 0.46, 0.917 (env PIMP set per child run).
// Uses copies of W4 code reading items_feat_hmac.json (keyed pseudonyms). Aggregates only.
import fs from 'fs';
import { ITEMS, TOK, TV, NOW } from './lib.mjs';
const mode = process.argv[2];
if (mode === 'bounds') {
  const isW = x => x.out === 'R' && x.decUser != null && x.decUser === x.subUser;
  const BY = Object.fromEntries(ITEMS.map(x => [x.id, x]));
  const all = TOK.filter(t => t.t >= TV).map(t => t.t);
  const noW = TOK.filter(t => t.t >= TV && !isW(BY[t.realItem])).map(t => t.t);
  const nw = ITEMS.filter(x => x.arr >= TV && x.arr <= NOW).map(x => x.arr).sort((a, b) => a - b);
  const edf = (tok, d) => { const J = nw.filter(a => a <= NOW - d); let k = 0, used = 0; const q = []; let h = 0;
    for (const t of tok) { while (k < J.length && J[k] <= t) q.push(J[k++]); while (h < q.length && q[h] + d < t) h++; if (h < q.length) { h++; used++; } }
    return { eligible: J.length, matched: used, share: +(used / J.length).toFixed(4) }; };
  const o = { tokens_all: all.length, tokens_no_withdrawal: noW.length, withdrawal_tokens: all.length - noW.length };
  for (const d of [90, 365]) { o['EDF' + d + '_all'] = edf(all, d); o['EDF' + d + '_noW'] = edf(noW, d); }
  // also: observed withdrawals among first decisions on hold-out NEW arrivals within d
  fs.writeFileSync('../res_e_bounds.json', JSON.stringify(o, null, 1)); console.log(JSON.stringify(o, null, 1));
} else {
  const { runPolicy, BASE, eventuallyAccepted, ACC_ALL } = await import('./w4lib.mjs');
  const { qualW } = await import('./sim3.mjs');
  const REPS = +(process.argv[3] || 10); const out = { pimp: ACC_ALL, reps: REPS, scen: {} };
  for (const r of [0, 0.25, 0.75]) {
    const sc = { ...BASE, r }; const row = {};
    for (const p of ['ASIS_logit', 'EXP365_grandf', 'EXP365_purge']) {
      row[p] = [];
      for (let k = 0; k < REPS; k++) {
        const R = runPolicy(p, sc, k); let vW = 0, vU = 0, lostEA = 0, lostEAw = 0, EAw = 0, lostEAobs = 0;
        for (const s of R.S) {
          const ea = eventuallyAccepted(s.x, k, 'imp'); if (!ea) continue; const w = qualW(s.x); EAw += w;
          const acc = (s.dec != null && !s.lostFinal) ? s.dec : null;
          if (acc != null) { vW += w * (R.end - acc) / 365; vU += (R.end - acc) / 365; }
          if (s.lostFinal) { lostEA++; lostEAw += w; if (s.x.out === 'A') lostEAobs++; }
        }
        row[p].push({ value_levelXrating: vW, value_uniform: vU, lostEA, lostEA_observedAccepted: lostEAobs, lostEA_wshare: lostEAw / EAw, lostFinal: R.S.filter(s => s.lostFinal).length, resub: R.nResub, endPending: R.endSnap.ages.length });
      }
    }
    const m = a => a.reduce((x, y) => x + y, 0) / a.length; const S = {};
    for (const p of Object.keys(row)) { S[p] = {}; for (const key of Object.keys(row[p][0])) S[p][key] = +m(row[p].map(o => o[key])).toFixed(3);
      if (p !== 'ASIS_logit') { const d = row[p].map((o, i) => o.value_levelXrating / row.ASIS_logit[i].value_levelXrating - 1); S[p].rel_value_levelXrating_vs_ASIS = [+m(d).toFixed(4), +Math.min(...d).toFixed(4), +Math.max(...d).toFixed(4)];
        const du = row[p].map((o, i) => o.value_uniform / row.ASIS_logit[i].value_uniform - 1); S[p].rel_value_uniform_vs_ASIS = [+m(du).toFixed(4), +Math.min(...du).toFixed(4), +Math.max(...du).toFixed(4)]; } }
    out.scen['r=' + r] = S; console.error('r', r, 'done', new Date().toISOString().slice(11, 19));
  }
  fs.writeFileSync(`../res_e_expiry_p${(+ACC_ALL).toFixed(3)}.json`, JSON.stringify(out, null, 1)); console.log(JSON.stringify(out));
}
