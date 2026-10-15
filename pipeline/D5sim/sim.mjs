// D5sim: counterfactual, trace-driven simulation of queue-design rules on the real CIViC evidence-item log.
// Capacity is held at the observed level: every observed first decision (ACCEPTED/REJECTED) is a "decision token"
// (time, decider). A policy only chooses WHICH queued item a token is spent on (plus expiry / intake rules).
// Usage: node sim.mjs  -> results_sim.json + console tables
import fs from 'fs';
const NOW = Date.parse('2026-10-07T00:00:00Z') / 864e5;
const T0 = '2021-01-01'; const T0d = Date.parse(T0) / 864e5; // calibration / holdout split
const yEnd = y => Date.parse(`${y + 1}-01-01`) / 864e5;
const YEARS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];

// ---------- RNG ----------
function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// ---------- data ----------
const load = m => JSON.parse(fs.readFileSync(`trace_${m}.json`)).items;
const ITEMS = load('excl');
function tokensOf(items) { return items.filter(x => x.dec != null).map(x => ({ t: x.dec, user: x.decUser, org: x.decOrg, realItem: x.id })).sort((a, b) => a.t - b.t); }

// ---------- helpers ----------
const q = (a, p) => { a = a.filter(Number.isFinite).sort((x, y) => x - y); if (!a.length) return null; return +a[Math.floor(p * (a.length - 1))].toFixed(1); };
const qInf = (a, p) => { a = a.slice().sort((x, y) => x - y); const v = a[Math.floor(p * (a.length - 1))]; return Number.isFinite(v) ? +v.toFixed(1) : 'never'; };
const r3 = x => x == null ? null : +x.toFixed(3);

// observed service discipline: for every real token, relative position of the chosen item in the queue
// u = (# queued items newer than chosen) / (queue length - 1); u=0 newest (LIFO), u=1 oldest (FIFO)
function observedRanks(items) {
  const toks = tokensOf(items); const byId = Object.fromEntries(items.map(x => [x.id, x]));
  const arr = items.slice().sort((a, b) => a.arr - b.arr); let ai = 0; const queue = []; const us = [];
  for (const tk of toks) {
    while (ai < arr.length && arr[ai].arr <= tk.t) queue.push(arr[ai++]);
    const idx = queue.findIndex(x => x.id === tk.realItem);
    const L = queue.length; us.push({ t: tk.t, u: L > 1 ? (L - 1 - idx) / (L - 1) : 0, L });
    queue.splice(idx, 1);
  }
  return us;
}

// ---------- simulator ----------
// policy: {disc:'FIFO'|'LIFO'|'RANDOM'|'RANK'|'REAL', uDist:[...], expireT, wipK, wipMode:'bounce'|'defer', prio:boolean, route:null|'rr'|'org', steal:boolean}
function simulate(items, tokens, pol, seed = 1) {
  const rng = mulberry(seed);
  const st = {}; for (const x of items) st[x.id] = { id: x.id, arr: x.arr, lvl: x.lvl, realDec: x.dec, realOut: x.out, subOrg: x.subOrg, dec: null, exp: null, bounced: false };
  const arr = items.slice().sort((a, b) => a.arr - b.arr);
  const isAB = x => x.lvl === 'A' || x.lvl === 'B';
  // queues: pooled -> [hi, lo] (hi used only with prio); routed -> per editor
  const pooled = [[], []]; const edQ = {}; const outside = []; let lost = 0;
  let ai = 0; const snaps = {}; const daily = []; let nextDay = Math.ceil(arr[0].arr); let yi = 0;
  const recentDec = []; let rr = 0; // for routing: decision tokens seen so far
  const allQueues = () => pol.route ? Object.values(edQ) : pooled;
  const size = () => allQueues().reduce((s, a) => s + a.length, 0);
  const purge = now => { if (pol.expireT == null) return; for (const Q of allQueues()) { while (Q.length && Q[0].arr + pol.expireT <= now) { const it = Q.shift(); it.exp = it.arr + pol.expireT; } }
    // queues are arrival-sorted only for pooled/routed FIFO insertion; insertion always appends in arrival order (defer admits oldest first) so front is oldest
  };
  const admitDeferred = now => { while (outside.length && size() < pol.wipK) enqueue(outside.shift(), now); };
  function activeEditors(now, org) {
    const s = new Map(); for (let i = recentDec.length - 1; i >= 0 && recentDec[i].t >= now - 365; i--) { const d = recentDec[i]; if (org == null || d.org === org) s.set(d.user, 1); }
    return [...s.keys()].sort((a, b) => a - b);
  }
  function enqueue(it, now) {
    if (pol.route) {
      let eds = pol.route === 'org' && it.subOrg != null ? activeEditors(now, it.subOrg) : [];
      if (!eds.length) eds = activeEditors(now, null);
      if (!eds.length) eds = [tokens[0].user];
      const e = eds[rr++ % eds.length]; (edQ[e] = edQ[e] || []).push(it); it.owner = e;
    } else pooled[pol.prio && isAB(it) ? 0 : (pol.prio ? 1 : 0)].push(it);
  }
  function pick(Q, t) {
    const L = Q.length; let i;
    switch (pol.disc) {
      case 'FIFO': i = 0; break;
      case 'LIFO': i = L - 1; break;
      case 'RANDOM': i = Math.floor(rng() * L); break;
      case 'RANK': { const D = (pol.uByYear && pol.uByYear[new Date(t * 864e5).getUTCFullYear()]) || pol.uDist; const u = D[Math.floor(rng() * D.length)]; i = L - 1 - Math.round(u * (L - 1)); break; }
    }
    return Q.splice(i, 1)[0];
  }
  function advanceTo(t) { // process arrivals with arr <= t, daily snapshots and year-end snapshots before t
    while (true) {
      const na = ai < arr.length ? arr[ai].arr : Infinity;
      const nd = nextDay, ny = yi < YEARS.length ? yEnd(YEARS[yi]) : Infinity;
      const m = Math.min(na, nd, ny);
      if (m > t) break;
      if (m === na && na <= nd && na <= ny) {
        purge(na); const it = st[arr[ai++].id];
        if (pol.wipK != null && size() >= pol.wipK) { if (pol.wipMode === 'defer') outside.push(it); else it.bounced = true; }
        else enqueue(it, na);
      } else if (m === ny && ny <= nd) { purge(ny); snaps[YEARS[yi]] = snapshot(ny); yi++; }
      else { purge(nd); if (nd <= NOW) daily.push(size() + outside.length); nextDay++; }
    }
  }
  function snapshot(now) { const ages = []; for (const Q of allQueues()) for (const it of Q) ages.push(now - it.arr); return { n: ages.length + outside.length, inQueue: ages.length, outside: outside.length, medAge: q(ages, .5) }; }
  for (const tk of tokens) {
    advanceTo(tk.t); purge(tk.t);
    let it = null;
    if (pol.disc === 'REAL') { // replay the actual choice (identity check)
      for (const Q of pooled) { const i = Q.findIndex(x => x.id === tk.realItem); if (i >= 0) { it = Q.splice(i, 1)[0]; break; } }
    } else if (pol.route) {
      const Q = edQ[tk.user];
      if (Q && Q.length) it = pick(Q, tk.t);
      else if (pol.steal) { let best = null; for (const k in edQ) if (edQ[k].length && (!best || edQ[k][0].arr < best[0].arr)) best = edQ[k]; if (best) it = best.shift(); }
    } else {
      const Q = pooled[0].length ? pooled[0] : pooled[1];
      if (Q.length) it = pick(Q, tk.t);
    }
    if (it) it.dec = tk.t; else lost++;
    recentDec.push(tk);
    if (pol.wipK != null && pol.wipMode === 'defer') admitDeferred(tk.t);
  }
  advanceTo(NOW); purge(NOW);
  const end = snapshot(NOW);
  return { st: Object.values(st), snaps, end, lost, daily };
}

// ---------- metrics ----------
function metrics(res, filter = () => true, label) {
  const S = res.st.filter(filter);
  const dt = S.map(x => x.dec != null ? x.dec - x.arr : Infinity);
  const decided = S.filter(x => x.dec != null);
  const within = d => { const el = S.filter(x => x.arr <= NOW - d); return r3(el.filter(x => x.dec != null && x.dec - x.arr <= d).length / el.length); };
  const exp = S.filter(x => x.exp != null);
  const m = {
    n: S.length, decided: decided.length, expired: exp.length, bounced: S.filter(x => x.bounced).length,
    medDecided: q(decided.map(x => x.dec - x.arr), .5), p90Decided: q(decided.map(x => x.dec - x.arr), .9),
    medAll: qInf(dt, .5), p90All: qInf(dt, .9),
    within90: within(90), within365: within(365),
    shareExpired: r3(exp.length / S.length),
  };
  if (exp.length) { m.expiredLaterDecidedInReality = r3(exp.filter(x => x.realDec != null).length / exp.length); m.expiredLaterAcceptedInReality = r3(exp.filter(x => x.realOut === 'A').length / exp.length); m.realAcceptedLostToExpiry = r3(exp.filter(x => x.realOut === 'A').length / S.filter(x => x.realOut === 'A').length); }
  m.decidedNeverDecidedInReality = decided.filter(x => x.realDec == null).length;
  return m;
}
function system(res) {
  // Little's law: time-average backlog from daily samples vs (sum of truncated sojourns)/horizon
  const start = Math.ceil(Math.min(...res.st.map(x => x.arr)));
  const H = NOW - start; const Lbar = res.daily.reduce((a, b) => a + b, 0) / res.daily.length;
  const soj = res.st.reduce((s, x) => { if (x.bounced) return s; const exit = x.dec ?? x.exp ?? NOW; return s + Math.max(0, Math.min(exit, NOW) - Math.max(x.arr, start)); }, 0);
  const lam = res.st.filter(x => !x.bounced).length / H;
  return { endBacklog: res.end.n, endInQueue: res.end.inQueue, endOutside: res.end.outside, endMedAgeD: res.end.medAge, lostTokens: res.lost, yearEnd: Object.fromEntries(Object.entries(res.snaps).map(([y, s]) => [y, s.n])), little: { Lbar: Math.round(Lbar), lambdaW: Math.round(soj / H), relErr: r3(Math.abs(Lbar - soj / H) / Lbar), W_days: Math.round(soj / H / lam) } };
}
function summarize(name, resList) { // average over stochastic reps
  const one = resList.map(r => ({ all: metrics(r), ab: metrics(r, x => x.lvl === 'A' || x.lvl === 'B'), rec: metrics(r, x => x.arr >= T0d), sys: system(r) }));
  const avg = (get) => { const v = one.map(get); if (typeof v[0] !== 'number') return v[0]; const mu = v.reduce((a, b) => a + b, 0) / v.length; return v.length > 1 ? +mu.toFixed(3) : v[0]; };
  const walk = (proto, get) => { const o = {}; for (const k in proto) o[k] = (proto[k] && typeof proto[k] === 'object') ? walk(proto[k], x => get(x)[k]) : avg(x => get(x)[k]); return o; };
  return { name, reps: resList.length, ...walk(one[0], x => x) };
}

// ---------- observed (ground truth) ----------
const TOK = tokensOf(ITEMS);
const obs = { st: ITEMS.map(x => ({ id: x.id, arr: x.arr, lvl: x.lvl, dec: x.dec ?? null, exp: null, bounced: false, realDec: x.dec, realOut: x.out })) };
const out = {};
const realRun = simulate(ITEMS, TOK, { disc: 'REAL' });
out.identity_check_REAL_replay = { sameDecisions: (() => { const m = Object.fromEntries(ITEMS.map(y => [y.id, y.dec ?? null])); return realRun.st.every(x => x.dec === m[x.id]); })(), lost: realRun.lost };
const OBS = summarize('OBSERVED', [realRun]);
out.OBSERVED = OBS;

// observed discipline
const U = observedRanks(ITEMS);
const uAll = U.map(x => x.u), uCal = U.filter(x => x.t < T0d).map(x => x.u), uRecent = U.filter(x => x.t >= T0d).map(x => x.u);
const UBY = {}; for (const x of U) (UBY[new Date(x.t * 864e5).getUTCFullYear()] = UBY[new Date(x.t * 864e5).getUTCFullYear()] || []).push(x.u);
const UHOLD = {}; const u1920 = U.filter(x => { const y = new Date(x.t * 864e5).getUTCFullYear(); return y === 2019 || y === 2020; }).map(x => x.u); for (const y in UBY) UHOLD[y] = +y < 2021 ? UBY[y] : u1920;
out.observed_discipline_by_year = Object.fromEntries(Object.entries(UBY).map(([y, a]) => [y, { n: a.length, newest10pct: +(a.filter(x => x <= .1).length / a.length).toFixed(3), oldest10pct: +(a.filter(x => x >= .9).length / a.length).toFixed(3), mean: +(a.reduce((s, x) => s + x, 0) / a.length).toFixed(3) }]));
const uStats = a => ({ n: a.length, mean: r3(a.reduce((s, x) => s + x, 0) / a.length), newest10pct: r3(a.filter(x => x <= .1).length / a.length), oldest10pct: r3(a.filter(x => x >= .9).length / a.length), exactNewest: r3(a.filter(x => x === 0).length / a.length) });
out.observed_discipline = { all: uStats(uAll), before2021: uStats(uCal), from2021: uStats(uRecent) };

// ---------- validation ----------
const REPS = 20;
const runN = (pol, n = REPS, items = ITEMS, toks = TOK) => Array.from({ length: n }, (_, i) => simulate(items, toks, pol, 1000 + i));
const val = {};
const cand = {
  FIFO: [simulate(ITEMS, TOK, { disc: 'FIFO' })], LIFO: [simulate(ITEMS, TOK, { disc: 'LIFO' })], RANDOM: runN({ disc: 'RANDOM' }),
  RANK_insample: runN({ disc: 'RANK', uDist: uAll }), RANK_cal2015_20: runN({ disc: 'RANK', uDist: uCal }), RANK_byYear_insample: runN({ disc: 'RANK', uDist: uAll, uByYear: UBY }), RANK_holdout_u2019_20: runN({ disc: 'RANK', uDist: uAll, uByYear: UHOLD }),
};
// monthly-capacity variant: token times re-drawn uniformly within their month (capacity known only per month)
function monthlyTokens(seed) { const rng = mulberry(seed); return TOK.map(tk => { const d = new Date(tk.t * 864e5); const a = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1) / 864e5, b = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1) / 864e5; return { ...tk, t: Math.min(a + rng() * (b - a), NOW) }; }).sort((x, y) => x.t - y.t); }
cand.RANK_cal2015_20_monthlyCap = Array.from({ length: REPS }, (_, i) => simulate(ITEMS, monthlyTokens(77 + i), { disc: 'RANK', uDist: uCal }, 500 + i));
const ks = (a, b) => { a = a.slice().sort((x, y) => x - y); b = b.slice().sort((x, y) => x - y); let i = 0, j = 0, d = 0; while (i < a.length && j < b.length) { const v = Math.min(a[i], b[j]); while (i < a.length && a[i] <= v) i++; while (j < b.length && b[j] <= v) j++; d = Math.max(d, Math.abs(i / a.length - j / b.length)); } return d; };
const obsRecDt = ITEMS.filter(x => x.arr >= T0d && x.dec != null).map(x => x.dec - x.arr);
for (const [k, rl] of Object.entries(cand)) {
  const s = summarize(k, rl);
  const ksv = rl.map(r => ks(r.st.filter(x => x.arr >= T0d && x.dec != null).map(x => x.dec - x.arr), obsRecDt));
  const ye = YEARS.map(y => s.sys.yearEnd[y]), yo = YEARS.map(y => OBS.sys.yearEnd[y]);
  val[k] = {
    yearEndBacklogRMSE: Math.round(Math.sqrt(ye.reduce((a, v, i) => a + (v - yo[i]) ** 2, 0) / ye.length)),
    endMedAgeD: s.sys.endMedAgeD, obsEndMedAgeD: OBS.sys.endMedAgeD,
    holdout2021plus: { medDecided: s.rec.medDecided, p90Decided: s.rec.p90Decided, within90: s.rec.within90, within365: s.rec.within365, KS_decidedTimes: r3(ksv.reduce((a, b) => a + b, 0) / ksv.length) },
    all: { medDecided: s.all.medDecided, p90Decided: s.all.p90Decided, within90: s.all.within90, within365: s.all.within365 },
    lostTokens: s.sys.lostTokens,
  };
}
val.OBSERVED = { endMedAgeD: OBS.sys.endMedAgeD, holdout2021plus: { medDecided: OBS.rec.medDecided, p90Decided: OBS.rec.p90Decided, within90: OBS.rec.within90, within365: OBS.rec.within365 }, all: { medDecided: OBS.all.medDecided, p90Decided: OBS.all.p90Decided, within90: OBS.all.within90, within365: OBS.all.within365 }, yearEnd: OBS.sys.yearEnd };
out.validation = val;

// ---------- counterfactual policies (same capacity) ----------
const pols = {
  'a_FIFO': [{ disc: 'FIFO' }, 1], 'b_LIFO': [{ disc: 'LIFO' }, 1], 'base_OBSDISC': [{ disc: 'RANK', uDist: uAll, uByYear: UBY }, REPS],
};
for (const T of [90, 180, 365]) { pols[`c_expire${T}_OBSDISC`] = [{ disc: 'RANK', uDist: uAll, uByYear: UBY, expireT: T }, REPS]; pols[`c_expire${T}_FIFO`] = [{ disc: 'FIFO', expireT: T }, 1]; }
for (const K of [141, 283, 600]) { pols[`d_wip${K}_bounce_FIFO`] = [{ disc: 'FIFO', wipK: K, wipMode: 'bounce' }, 1]; pols[`d_wip${K}_defer_FIFO`] = [{ disc: 'FIFO', wipK: K, wipMode: 'defer' }, 1]; }
pols['e_prioAB_FIFO'] = [{ disc: 'FIFO', prio: true }, 1]; pols['e_prioAB_OBSDISC'] = [{ disc: 'RANK', uDist: uAll, uByYear: UBY, prio: true }, REPS];
pols['e_prioAB_FIFO_expire365'] = [{ disc: 'FIFO', prio: true, expireT: 365 }, 1];
pols['f_route_rr_strict'] = [{ disc: 'FIFO', route: 'rr', steal: false }, 1]; pols['f_route_rr_steal'] = [{ disc: 'FIFO', route: 'rr', steal: true }, 1];
pols['f_route_org_strict'] = [{ disc: 'FIFO', route: 'org', steal: false }, 1]; pols['f_route_org_steal'] = [{ disc: 'FIFO', route: 'org', steal: true }, 1];
const cf = {}; const row = s => ({ endBacklog: s.sys.endBacklog, endMedAgeD: s.sys.endMedAgeD, lostTokens: s.sys.lostTokens, medDecided: s.all.medDecided, p90Decided: s.all.p90Decided, medAll: s.all.medAll, within90: s.all.within90, within365: s.all.within365, shareExpired: s.all.shareExpired, bounced: s.all.bounced, expiredLaterAcceptedInReality: s.all.expiredLaterAcceptedInReality, realAcceptedLostToExpiry: s.all.realAcceptedLostToExpiry, AB_realAcceptedLostToExpiry: s.ab.realAcceptedLostToExpiry, decidedNeverDecidedInReality: s.all.decidedNeverDecidedInReality, AB: { n: s.ab.n, medDecided: s.ab.medDecided, p90Decided: s.ab.p90Decided, within90: s.ab.within90, within365: s.ab.within365, shareExpired: s.ab.shareExpired }, little: s.sys.little });
cf.OBSERVED = row(OBS);
for (const [k, [p, n]] of Object.entries(pols)) { cf[k] = row(summarize(k, runN(p, n))); }
out.counterfactual = cf;

// routing feasibility: editor-level capacity
const decUsers = {}; for (const tk of TOK) decUsers[tk.user] = (decUsers[tk.user] || 0) + 1;
const tenure = {}; for (const tk of TOK) { const r = tenure[tk.user] = tenure[tk.user] || [tk.t, tk.t]; r[1] = tk.t; }
out.routing_feasibility = { deciders: Object.keys(decUsers).length, decidersWithLt10Decisions: Object.values(decUsers).filter(v => v < 10).length, medianActiveSpanDays: q(Object.values(tenure).map(r => r[1] - r[0]), .5), decisionsWithOrg: r3(TOK.filter(t => t.org != null).length / TOK.length), submissionsWithOrg: r3(ITEMS.filter(x => x.subOrg != null).length / ITEMS.length) };

// ---------- sensitivity ----------
const sens = {};
function scaleTokens(f, seed) { const rng = mulberry(seed); if (f < 1) return TOK.filter(() => rng() < f); const extra = TOK.filter(() => rng() < f - 1).map(tk => ({ ...tk, t: Math.min(NOW, Math.max(TOK[0].t, tk.t + (rng() - .5) * 30)), realItem: null })); return TOK.concat(extra).sort((a, b) => a.t - b.t); }
const sensPols = { FIFO: { disc: 'FIFO' }, OBSDISC: { disc: 'RANK', uDist: uAll, uByYear: UBY }, expire365_OBSDISC: { disc: 'RANK', uDist: uAll, uByYear: UBY, expireT: 365 }, expire180_FIFO: { disc: 'FIFO', expireT: 180 }, prioAB_FIFO: { disc: 'FIFO', prio: true }, wip283_bounce: { disc: 'FIFO', wipK: 283, wipMode: 'bounce' } };
for (const f of [0.75, 1.25]) for (const [k, p] of Object.entries(sensPols)) { const rl = Array.from({ length: 10 }, (_, i) => simulate(ITEMS, scaleTokens(f, 31 + i), p, 900 + i)); sens[`cap${f}_${k}`] = row(summarize(k, rl)); }
// missing events: drop 0.26 % of arrivals and tokens, or add 0.26 % extra tokens
function perturb(seed, add) { const rng = mulberry(seed); const items = ITEMS.filter(() => rng() >= 0.0026); const ids = new Set(items.map(x => x.id)); let toks = TOK.filter(t => ids.has(t.realItem) && rng() >= 0.0026); if (add) toks = toks.concat(TOK.filter(() => rng() < 0.0052).map(t => ({ ...t, realItem: null }))).sort((a, b) => a.t - b.t); return [items, toks]; }
for (const [k, p] of Object.entries(sensPols)) { const rl = Array.from({ length: 10 }, (_, i) => { const [it, tk] = perturb(55 + i, i % 2 === 1); return simulate(it, tk, p, 700 + i); }); sens[`missing0.26_${k}`] = row(summarize(k, rl)); }
// bot inclusion
const ITEMS_INCL = load('incl'); const TOK_INCL = tokensOf(ITEMS_INCL);
sens.botIncluded_FIFO = row(summarize('FIFO', [simulate(ITEMS_INCL, TOK_INCL, { disc: 'FIFO' })]));
sens.botIncluded_identicalQueueTrace = JSON.stringify(ITEMS.map(x => [x.arr, x.dec])) === JSON.stringify(ITEMS_INCL.map(x => [x.arr, x.dec]));
out.sensitivity = sens;

fs.writeFileSync('results_sim.json', JSON.stringify(out, null, 1));
// console summary
console.log('identity', JSON.stringify(out.identity_check_REAL_replay));
console.log('discipline', JSON.stringify(out.observed_discipline));
console.log('\nVALIDATION'); for (const [k, v] of Object.entries(val)) console.log(k.padEnd(28), JSON.stringify(v));
console.log('\nCOUNTERFACTUAL'); for (const [k, v] of Object.entries(cf)) console.log(k.padEnd(28), JSON.stringify(v));
console.log('\nROUTING', JSON.stringify(out.routing_feasibility));
console.log('\nSENSITIVITY'); for (const [k, v] of Object.entries(sens)) console.log(k.padEnd(30), JSON.stringify(v));
