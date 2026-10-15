// Full-log analysis of CIViC evidence-item curation process (D5b).
import fs from 'fs';
const NOW = Date.parse('2026-10-07T00:00:00Z'); const D = 864e5;
const ev = []; const seen = new Set();
for (const f of fs.readdirSync('cache').sort()) for (const e of JSON.parse(fs.readFileSync('cache/' + f))) { if (seen.has(e.id)) continue; seen.add(e.id); ev.push(e); }
ev.sort((a, b) => a.createdAt.localeCompare(b.createdAt) || a.id - b.id); { const bot = new Set((process.env.EXCL || "").split(",").filter(Boolean).map(Number)); const keep = ev.filter(e => !bot.has(e.originatingUser?.id)); ev.length = 0; for (const e of keep) ev.push(e); }
const users = Object.fromEntries(JSON.parse(fs.readFileSync('meta_users.json')).map(u => [u.id, u]));
const meta = Object.fromEntries(JSON.parse(fs.readFileSync('meta_evidence.json')).map(x => [x.id, x]));
const out = {}; const P = (k, v) => { out[k] = v; console.log(k, typeof v === 'object' ? JSON.stringify(v) : v); };
P('events_unique', ev.length);
P('event_span', [ev[0].createdAt, ev.at(-1).createdAt]);
const actCount = {}; for (const e of ev) actCount[e.action] = (actCount[e.action] || 0) + 1; P('actions', actCount);

// revision -> subject map
const rev2subj = {};
for (const e of ev) if (e.originatingObject?.__typename === 'Revision' && e.subject?.id != null) rev2subj[e.originatingObject.id] = e.subject;
const cases = {};
const add = (id, e) => { (cases[id] = cases[id] || []).push(e); };
for (const e of ev) {
  const s = e.subject; if (!s) continue;
  if (s.__typename === 'EvidenceItem') add(s.id, e);
  else if (s.__typename === 'Revision') { const t = rev2subj[s.id]; if (t?.__typename === 'EvidenceItem') add(t.id, { ...e, action: 'REVISION_COMMENTED', revId: s.id }); }
}
const q = (a, p) => { if (!a.length) return null; a = a.slice().sort((x, y) => x - y); return +a[Math.floor(p * (a.length - 1))].toFixed(1); };
const gini = a => { a = a.slice().sort((x, y) => x - y); const n = a.length, s = a.reduce((x, y) => x + y, 0); let c = 0; a.forEach((x, i) => c += (2 * (i + 1) - n - 1) * x); return +(c / (n * s)).toFixed(3); };
const ids = Object.keys(cases).map(Number); P('eid_cases_in_log', ids.length); P('eid_meta', Object.keys(meta).length);
const stCount = {}; for (const id in meta) stCount[meta[id].status] = (stCount[meta[id].status] || 0) + 1; P('status_now', stCount);
const role = uid => users[uid]?.role || 'UNKNOWN';
const isDec = a => a === 'ACCEPTED' || a === 'REJECTED';

const R = { acc: [], rej: [], pendAge: [], fourEyesOK: 0, fourEyesViol: 0, accByRole: {}, rejByRole: {}, nRevSug: [], withRev: 0, withRevRej: 0, withFlag: 0, withComment: 0, reworkLoop: 0, decidedNoSubmit: 0, multiDecision: 0, reverted: 0, rejWithComment: 0, rejN: 0 };
const subYear = {}, decYear = {}, deciderYear = {}, subByUser = {}, decByUser = {}, variants = {};
const pendTouched = { touchedByOtherEditor: 0, untouched: 0 };
const statusMismatch = { logAccNowSub: 0, logNoneNowAcc: 0 };
for (const id of ids) {
  const es = cases[id]; const acts = es.map(e => e.action);
  const sub = es.find(e => e.action === 'SUBMITTED'); const decs = es.filter(e => isDec(e.action));
  const st = meta[id]?.status;
  if (decs.length > 1) R.multiDecision++; if (acts.includes('REVERTED')) R.reverted++;
  const ns = acts.filter(a => a === 'REVISION_SUGGESTED').length; R.nRevSug.push(ns); if (ns) R.withRev++;
  if (acts.includes('REVISION_REJECTED')) R.withRevRej++;
  if (acts.includes('FLAGGED')) R.withFlag++;
  if (acts.includes('COMMENTED')) R.withComment++;
  const iRR = acts.indexOf('REVISION_REJECTED'); if (iRR >= 0 && acts.slice(iRR + 1).includes('REVISION_SUGGESTED')) R.reworkLoop++;
  if (sub) { const y = sub.createdAt.slice(0, 4); subYear[y] = (subYear[y] || 0) + 1; const u = sub.originatingUser?.id; subByUser[u] = (subByUser[u] || 0) + 1; }
  const dec = decs[0];
  if (st === 'SUBMITTED' && dec) statusMismatch.logAccNowSub++;
  if (st === 'ACCEPTED' && !dec) statusMismatch.logNoneNowAcc++;
  if (dec) {
    const y = dec.createdAt.slice(0, 4); decYear[y] = (decYear[y] || 0) + 1; (deciderYear[y] = deciderYear[y] || new Set()).add(dec.originatingUser?.id);
    for (const d of decs) decByUser[d.originatingUser?.id] = (decByUser[d.originatingUser?.id] || 0) + 1;
    const map = dec.action === 'ACCEPTED' ? R.accByRole : R.rejByRole; const r = role(dec.originatingUser?.id); map[r] = (map[r] || 0) + 1;
    if (dec.action === 'REJECTED') { R.rejN++; if (es.some(e => (e.action === 'COMMENTED') && Math.abs(Date.parse(e.createdAt) - Date.parse(dec.createdAt)) < 30 * D)) R.rejWithComment++; }
    if (sub) {
      const d = (Date.parse(dec.createdAt) - Date.parse(sub.createdAt)) / D; (dec.action === 'ACCEPTED' ? R.acc : R.rej).push(d);
      if (dec.action === 'ACCEPTED') { if (dec.originatingUser?.id === sub.originatingUser?.id) R.fourEyesViol++; else R.fourEyesOK++; }
    } else R.decidedNoSubmit++;
  }
  if (st === 'SUBMITTED' && sub) {
    R.pendAge.push((NOW - Date.parse(sub.createdAt)) / D);
    const touched = es.some(e => e !== sub && ['EDITOR', 'ADMIN'].includes(role(e.originatingUser?.id)) && e.originatingUser?.id !== sub.originatingUser?.id);
    touched ? pendTouched.touchedByOtherEditor++ : pendTouched.untouched++;
  }
  const v = acts.filter(a => !/COMMENT/.test(a)).map(a => a.replace('REVISION_', 'R_')).filter((x, i, a) => x !== a[i - 1]).join('>');
  variants[v] = (variants[v] || 0) + 1;
}
P('status_log_mismatch', statusMismatch);
P('acc_days', { n: R.acc.length, p25: q(R.acc, .25), med: q(R.acc, .5), p75: q(R.acc, .75), p90: q(R.acc, .9), le1d: +(R.acc.filter(d => d <= 1).length / R.acc.length).toFixed(3) });
P('rej_days', { n: R.rej.length, med: q(R.rej, .5), p90: q(R.rej, .9), rejWithCommentWithin30d: +(R.rejWithComment / R.rejN).toFixed(3) });
P('pending_age_days', { n: R.pendAge.length, p25: q(R.pendAge, .25), med: q(R.pendAge, .5), p75: q(R.pendAge, .75), gt2y: +(R.pendAge.filter(d => d > 730).length / R.pendAge.length).toFixed(3), gt5y: +(R.pendAge.filter(d => d > 1826).length / R.pendAge.length).toFixed(3) });
P('pending_touched', pendTouched);
P('four_eyes_accept', { ok: R.fourEyesOK, self: R.fourEyesViol, rate: +(R.fourEyesOK / (R.fourEyesOK + R.fourEyesViol)).toFixed(4) });
P('accept_by_current_role', R.accByRole); P('reject_by_current_role', R.rejByRole);
const n = ids.length;
P('rework', { withRev: +(R.withRev / n).toFixed(3), withRevRej: +(R.withRevRej / n).toFixed(3), reworkLoop: +(R.reworkLoop / n).toFixed(3), withFlag: +(R.withFlag / n).toFixed(3), withComment: +(R.withComment / n).toFixed(3), revSugPerCase_mean: +(R.nRevSug.reduce((a, b) => a + b, 0) / n).toFixed(2), p90: q(R.nRevSug, .9), multiDecision: R.multiDecision, reverted: R.reverted, decidedNoSubmit: R.decidedNoSubmit });
const vs = Object.entries(variants).sort((a, b) => b[1] - a[1]);
P('variants', { distinct: vs.length, top1cov: +(vs[0][1] / n).toFixed(3), top10cov: +(vs.slice(0, 10).reduce((a, b) => a + b[1], 0) / n).toFixed(3), singletons: vs.filter(x => x[1] === 1).length, top: vs.slice(0, 8) });

// revision-level conformance (all entity types)
const revs = {};
for (const e of ev) if (e.originatingObject?.__typename === 'Revision') { const r = revs[e.originatingObject.id] = revs[e.originatingObject.id] || {}; r[e.action] = e; }
const revCommented = new Set(ev.filter(e => e.subject?.__typename === 'Revision' && e.action === 'COMMENTED').map(e => e.subject.id));
let rOK = 0, rSelf = 0, rSelfRole = {}, rRole = {}, rs = 0, rsCom = 0, rDays = [];
for (const id in revs) {
  const r = revs[id];
  if (r.REVISION_SUGGESTED) { rs++; if (revCommented.has(+id)) rsCom++; }
  if (r.REVISION_SUGGESTED && r.REVISION_ACCEPTED) {
    const a = r.REVISION_ACCEPTED.originatingUser?.id;
    rDays.push((Date.parse(r.REVISION_ACCEPTED.createdAt) - Date.parse(r.REVISION_SUGGESTED.createdAt)) / D);
    if (a === r.REVISION_SUGGESTED.originatingUser?.id) { rSelf++; rSelfRole[role(a)] = (rSelfRole[role(a)] || 0) + 1; } else rOK++;
    rRole[role(a)] = (rRole[role(a)] || 0) + 1;
  }
}
P('revision_four_eyes_all_entities', { ok: rOK, self: rSelf, rate: +(rOK / (rOK + rSelf)).toFixed(4), selfByRole: rSelfRole, acceptorRole: rRole, acceptDaysMed: q(rDays, .5), le1d: +(rDays.filter(d => d <= 1).length / rDays.length).toFixed(3) });
P('revision_with_comment_share', { suggested: rs, commented: rsCom, share: +(rsCom / rs).toFixed(3) });

// throughput and backlog by year
const years = [...new Set(Object.keys(subYear).concat(Object.keys(decYear)))].sort();
const byYear = [];
for (const y of years) {
  const end = Date.parse(`${+y + 1}-01-01`);
  let pend = 0, ages = [];
  for (const id of ids) {
    const es = cases[id]; const s = es.find(e => e.action === 'SUBMITTED'); if (!s || Date.parse(s.createdAt) >= end) continue;
    const d = es.find(e => isDec(e.action) && Date.parse(e.createdAt) < end);
    if (!d) { pend++; ages.push((end - Date.parse(s.createdAt)) / D); }
  }
  const eds = deciderYear[y]?.size || 0;
  byYear.push({ y, sub: subYear[y] || 0, dec: decYear[y] || 0, deciders: eds, decPerDecider: eds ? +((decYear[y] || 0) / eds).toFixed(1) : 0, pendingEnd: pend, pendMedAgeD: q(ages, .5) });
}
P('by_year', byYear);

// probability of a decision within the next year, given still pending at age T
const surv = [];
for (const T of [30, 90, 180, 365, 730, 1460]) {
  let atRisk = 0, later = 0;
  for (const id of ids) {
    const es = cases[id]; const s = es.find(e => e.action === 'SUBMITTED'); if (!s) continue;
    const t0 = Date.parse(s.createdAt); if (NOW - t0 < (T + 365) * D) continue;
    const d = es.find(e => isDec(e.action)); const dt = d ? (Date.parse(d.createdAt) - t0) / D : Infinity;
    if (dt > T) { atRisk++; if (dt <= T + 365) later++; }
  }
  surv.push({ pendingAtDays: T, n: atRisk, decidedWithinNextYear: +(later / atRisk).toFixed(3) });
}
P('conditional_decision', surv);

// workload concentration
const top = (o, k) => { const a = Object.values(o).sort((x, y) => y - x); return +(a.slice(0, k).reduce((x, y) => x + y, 0) / a.reduce((x, y) => x + y, 0)).toFixed(3); };
P('decider_concentration', { deciders: Object.keys(decByUser).length, gini: gini(Object.values(decByUser)), top1: top(decByUser, 1), top5: top(decByUser, 5) });
P('submitter_concentration', { submitters: Object.keys(subByUser).length, gini: gini(Object.values(subByUser)), top1: top(subByUser, 1), top5: top(subByUser, 5) });
const recentDec = {}; for (const id of ids) { const d = cases[id].find(e => isDec(e.action)); if (d && d.createdAt >= '2023') recentDec[d.originatingUser?.id] = (recentDec[d.originatingUser?.id] || 0) + 1; }
P('decider_concentration_2023plus', { deciders: Object.keys(recentDec).length, gini: gini(Object.values(recentDec)), top1: top(recentDec, 1), top5: top(recentDec, 5) });

// to-be rule check (Little's law, simulation-free), using 2023-2025
const yrs = ['2023', '2024', '2025'];
const lam = yrs.reduce((a, y) => a + (subYear[y] || 0), 0) / 3, mu = yrs.reduce((a, y) => a + (decYear[y] || 0), 0) / 3;
const perEd = yrs.reduce((a, y) => a + (decYear[y] || 0), 0) / yrs.reduce((a, y) => a + (deciderYear[y]?.size || 0), 0);
const B = R.pendAge.length;
const recentCohort = []; let recentCohortN = 0, recentCohortDec = 0;
for (const id of ids) { const es = cases[id]; const s = es.find(e => e.action === 'SUBMITTED'); if (!s || !yrs.includes(s.createdAt.slice(0, 4))) continue; recentCohortN++; const d = es.find(e => isDec(e.action)); if (d) { recentCohortDec++; recentCohort.push((Date.parse(d.createdAt) - Date.parse(s.createdAt)) / D); } }
P('to_be', {
  lambda_sub_per_yr: Math.round(lam), mu_dec_per_yr: Math.round(mu), backlog_now: B, dec_per_decider_yr: +perEd.toFixed(1),
  clear_in_2y_need_mu: Math.round(lam + B / 2), extra_decider_equiv_2y: +((lam + B / 2 - mu) / perEd).toFixed(1),
  littles_law_W_days_now: Math.round(B / mu * 365),
  wip_cap_90d_SLA: Math.round(lam * 90 / 365), wip_cap_180d_SLA: Math.round(lam * 180 / 365), backlog_over_cap90: +(B / (lam * 90 / 365)).toFixed(1),
  cohort2023_25: { n: recentCohortN, decided: recentCohortDec, share: +(recentCohortDec / recentCohortN).toFixed(3), medDaysIfDecided: q(recentCohort, .5) }
});

// organisation at event time; role reconstruction
let withOrg = 0, withOrgDec = 0, nDec = 0; for (const e of ev) { if (e.organization?.id) withOrg++; if (isDec(e.action)) { nDec++; if (e.organization?.id) withOrgDec++; } }
P('events_with_org', { all: +(withOrg / ev.length).toFixed(3), decisions: +(withOrgDec / nDec).toFixed(3) });
const firstMod = {};
for (const e of ev) if (['ACCEPTED', 'REJECTED', 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'ASSERTION_ACCEPTED', 'ASSERTION_REJECTED'].includes(e.action)) { const u = e.originatingUser?.id; if (u != null && !firstMod[u]) firstMod[u] = e.createdAt; }
const modRole = {}; for (const u in firstMod) modRole[role(+u)] = (modRole[role(+u)] || 0) + 1;
P('moderating_users_by_current_role', modRole);
const roleNow = {}; for (const u of Object.values(users)) roleNow[u.role] = (roleNow[u.role] || 0) + 1; P('users_by_role_now', roleNow);
// assertions
const aCases = {}; for (const e of ev) if (e.subject?.__typename === 'Assertion') (aCases[e.subject.id] = aCases[e.subject.id] || []).push(e);
const aDur = [], aAppr = []; let aN = 0, aFE = 0, aFEok = 0;
for (const id in aCases) { const es = aCases[id]; aN++; const s = es.find(e => e.action === 'ASSERTION_SUBMITTED'), a = es.find(e => e.action === 'ASSERTION_ACCEPTED'), ap = es.find(e => e.action === 'ASSERTION_APPROVED');
  if (s && a) { aDur.push((Date.parse(a.createdAt) - Date.parse(s.createdAt)) / D); aFE++; if (a.originatingUser?.id !== s.originatingUser?.id) aFEok++; }
  if (s && ap) aAppr.push((Date.parse(ap.createdAt) - Date.parse(s.createdAt)) / D); }
P('assertions', { cases: aN, accepted: aDur.length, accMedDays: q(aDur, .5), accP90: q(aDur, .9), fourEyes: `${aFEok}/${aFE}`, approved: aAppr.length, apprMedDays: q(aAppr, .5) });
fs.writeFileSync('results_full_excl.json', JSON.stringify(out, null, 1));
