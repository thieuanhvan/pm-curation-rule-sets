// W7 T4: log-measured counterparts of simulator outcomes (hold-out 2023-01-01..2026-10-07) and denominators of the legacy bound.
// Reuses ../A4/lib.mjs and ../W4/w4lib.mjs (no network). Writes res_w7_t4_logvalues.json.
import fs from 'fs';
import { ITEMS, TV, NOW, runPolicy, BASE, eventuallyAccepted, ci } from '../W4/w4lib.mjs';
const R = {};
function kmAt(times, events, t0) { const o = times.map((t, i) => [t, events[i]]).sort((a, b) => a[0] - b[0]); let n = o.length, S = 1;
  for (let i = 0; i < o.length;) { const t = o[i][0]; if (t > t0) break; let d = 0, c = 0; while (i < o.length && o[i][0] === t) { o[i][1] ? d++ : c++; i++; } if (d) S *= 1 - d / n; n -= d + c; } return 1 - S; }
const share = (xs, d) => { const el = xs.filter(s => s.arr <= NOW - d); return { n: el.length, share: el.filter(s => s.dec != null && s.dec - s.arr <= d).length / el.length }; };
// observed log
const nw = ITEMS.filter(x => x.arr >= TV && x.arr <= NOW).map(x => ({ arr: x.arr, dec: (x.dec != null && x.dec <= NOW) ? x.dec : null }));
const t = nw.map(s => s.dec != null ? s.dec - s.arr : NOW - s.arr), e = nw.map(s => s.dec != null);
// bootstrap over items for log CIs
import { mulberry } from '../A4/lib.mjs'; const rnd = mulberry(20261007);
const bootKM = (d) => { const a = []; for (let b = 0; b < 1000; b++) { const ti = [], ei = []; for (let i = 0; i < nw.length; i++) { const k = Math.floor(rnd() * nw.length); ti.push(t[k]); ei.push(e[k]); } a.push(kmAt(ti, ei, d)); } return ci(a); };
R.observed_log = { new_arrivals: nw.length, KM_decided_by90: kmAt(t, e, 90), KM_by90_CI: bootKM(90), KM_decided_by365: kmAt(t, e, 365), KM_by365_CI: bootKM(365),
  share_by90_full_followup: share(nw, 90), share_by365_full_followup: share(nw, 365) };
// as-is model, both definitions (20 reps as in W4 outcomes)
const a90 = [], a365 = [], s90 = [], s365 = [];
for (let k = 0; k < 20; k++) { const r = runPolicy('ASIS_logit', BASE, k); const S = r.S.filter(s => !s.legacy).map(s => ({ arr: s.arr0, dec: s.dec }));
  const tt = S.map(s => s.dec != null ? s.dec - s.arr : NOW - s.arr), ee = S.map(s => s.dec != null);
  a90.push(kmAt(tt, ee, 90)); a365.push(kmAt(tt, ee, 365)); s90.push(share(S, 90).share); s365.push(share(S, 365).share); }
R.asis_model = { KM_by90: ci(a90), KM_by365: ci(a365), share_by90_full_followup: ci(s90), share_by365_full_followup: ci(s365) };
// legacy denominators (items pending at 2023-01-01 that arrived before it)
const leg = ITEMS.filter(x => x.arr < TV && (x.dec == null || x.dec >= TV));
R.legacy = { pending_at_holdout_start: leg.length, observed_accepted_later: leg.filter(x => x.out === 'A').length, observed_rejected_later: leg.filter(x => x.out === 'R').length,
  still_pending_now: leg.filter(x => x.dec == null).length,
  eventually_accepted_imputed_by_draw: [0, 1, 2, 3, 4].map(d => leg.filter(x => eventuallyAccepted(x, d, 'imp')).length),
  observed_share_of_EAimp_decided_in_holdout_by_draw: [0, 1, 2, 3, 4].map(d => { const L = leg.filter(x => eventuallyAccepted(x, d, 'imp')); return L.filter(x => x.dec != null && x.out === 'A').length / L.length; }),
  note: 'eventually accepted (imputed) = observed later acceptances + Bernoulli(p = overall acceptance share) for never-decided items; bound 18.8 % = all tokens to legacy oldest-first (frontier s = 1), 21.4 % = all tokens to legacy items known to be eventually accepted (oracle, LEGACY_first)' };
fs.writeFileSync('res_w7_t4_logvalues.json', JSON.stringify(R, null, 1)); console.log(JSON.stringify(R, null, 1));
