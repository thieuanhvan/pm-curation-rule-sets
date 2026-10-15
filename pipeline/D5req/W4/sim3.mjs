// W4 copy of ../A4/sim2.mjs with one addition: discipline EDF (serve oldest item still inside its D-day target).
// D5req/A4 simulator: generalisation of ../../D5sim/sim.mjs.
// Capacity = observed decision tokens (time, decider, decider org). New in this version:
//  - start at any date from the REAL queue state (forward / temporal-validation runs)
//  - calibrated conditional-logit service discipline (features as in choice.mjs), optional parameter draws
//  - heterogeneous effort (work units per item) with fractional carry, decider-item affinity (mismatch multiplier kappa)
//  - ownership routing (affinity-based owner, steal, reassignment of inactive owners) vs pooled routing
//  - expiry with behavioural resubmission (prob r, delay), grandfathering, curation sprints, old-item panel
import { ITEMS, TOK, NOW, mulberry, fvec, FEAT_T1, FEAT_T2, act30, touched } from '../A4/lib.mjs';

export const LVLW = { A: 5, B: 4, C: 3, D: 2, E: 1 };
export const qualW = x => (LVLW[x.lvl] ?? 1) * ((x.rating ?? 3) / 3);
// expected acceptance probability for items never decided in reality: observed accept share by level
const pAccLvl = (() => { const c = {}; for (const x of ITEMS) if (x.out) { const k = x.lvl; c[k] = c[k] || [0, 0]; c[k][1]++; if (x.out === 'A') c[k][0]++; } return Object.fromEntries(Object.entries(c).map(([k, v]) => [k, v[0] / v[1]])); })();
export const expAcc = x => x.out === 'A' ? 1 : x.out === 'R' ? 0 : (pAccLvl[x.lvl] ?? 0.9);
export { pAccLvl };

function gauss(rng) { let u = 0, v = 0; while (u === 0) u = rng(); while (v === 0) v = rng(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
export function drawBeta(fit, rng) { // multivariate normal draw via Cholesky of cov
  const b = fit.b, V = fit.cov, n = b.length, L = Array.from({ length: n }, () => new Array(n).fill(0));
  for (let i = 0; i < n; i++) for (let j = 0; j <= i; j++) { let s = V[i][j]; for (let k = 0; k < j; k++) s -= L[i][k] * L[j][k]; L[i][j] = i === j ? Math.sqrt(Math.max(s, 1e-12)) : s / L[j][j]; }
  const z = b.map(() => gauss(rng)); return b.map((bi, i) => bi + L[i].reduce((s, l, k) => s + l * z[k], 0));
}

// effort weights (work units before normalisation)
function effortOf(x, mode, rng) {
  if (mode === 'unit') return 1;
  if (mode === 'proxy') return x.effortRaw; // 1 + revisions suggested + comments before first decision (or to date)
  if (mode && mode.cv) { const s2 = Math.log(1 + mode.cv * mode.cv); return Math.exp(Math.sqrt(s2) * gauss(rng) - s2 / 2); }
  throw new Error('effort');
}

export function run(opt, seed = 1) {
  const rng = mulberry(seed);
  const start = opt.start ?? -Infinity, end = opt.end ?? NOW;
  const tier = opt.tier ?? 1;
  const beta = opt.beta;
  const kappa = opt.kappa ?? 1;
  // ---- tokens in window (+ sprint tokens) ----
  let toks = TOK.filter(t => t.t >= start && t.t <= end).map(t => ({ ...t }));
  if (opt.sprint) toks = toks.concat(opt.sprint.tokens.map(t => ({ ...t, sprint: true }))).sort((a, b) => a.t - b.t);
  // ---- decider history (decider|submitter) and activity from real history before start ----
  const hist = new Map(); const lastTok = new Map(); const userOrg = new Map();
  const preTok = TOK.filter(t => t.t < start);
  for (const tk of preTok) { const it = ITEMS[ordOf[tk.realItem]]; const k = tk.user + '|' + it.subUser; hist.set(k, (hist.get(k) || 0) + 1); lastTok.set(tk.user, tk.t); userOrg.set(tk.user, tk.org); }
  // ---- item states ----
  const S = []; const pending = []; const future = [];
  for (const x of ITEMS) {
    if (x.arr > end) continue;
    const s = { x, arr0: x.arr, arr: x.arr, gen: 0, need: effortOf(x, opt.effort ?? 'unit', rng), prog: 0, dec: null, decBy: null, exp: null, owner: null, legacy: x.arr < start, resubAt: null, lostFinal: false, lastWork: null };
    if (x.arr < start) { if (x.dec != null && x.dec < start) continue; pending.push(s); } else future.push(s);
    S.push(s);
  }
  // ---- normalise effort so that the observed allocation in the window is exactly feasible ----
  {
    let tot = 0, ntok = toks.filter(t => !t.sprint).length; const h2 = new Map(hist);
    const byId = new Map(S.map(s => [s.x.id, s]));
    for (const tk of toks) { if (tk.sprint) continue; const s = byId.get(tk.realItem); if (!s) continue; const m = (tk.org != null && s.x.subOrg === tk.org) || (opt.affinity === 'orgOrSub' && h2.get(tk.user + '|' + s.x.subUser)) ? 1 : kappa; tot += s.need * m; const k = tk.user + '|' + s.x.subUser; h2.set(k, (h2.get(k) || 0) + 1); }
    const scale = tot > 0 ? ntok / tot : 1; for (const s of S) s.need *= scale;
  }
  pending.sort((a, b) => a.arr - b.arr); future.sort((a, b) => a.arr - b.arr);
  // ---- queues ----
  const pool = pending.slice(); // pooled queue sorted by arr
  const ownQ = new Map(); const inProg = new Map();
  const route = opt.route ?? 'pool';
  const activeUsers = now => { const r = []; for (const [u, t] of lastTok) if (t >= now - 365) r.push(u); return r.sort((a, b) => a - b); };
  const load = u => (ownQ.get(u) || []).length;
  const matched = (u, org, s) => (org != null && s.x.subOrg === org) || (opt.affinity === 'orgOrSub' && !!hist.get(u + '|' + s.x.subUser));
  function insertSorted(Q, s) { let lo = 0, hi = Q.length; while (lo < hi) { const m = (lo + hi) >> 1; if (Q[m].arr <= s.arr) lo = m + 1; else hi = m; } Q.splice(lo, 0, s); }
  function assignOwner(s, now) {
    const act = activeUsers(now); if (!act.length) { s.owner = -1; insertSorted(ownQ.get(-1) || ownQ.set(-1, []).get(-1), s); return; }
    let cand = act.filter(u => matched(u, userOrg.get(u), s)); if (!cand.length) cand = act;
    let best = cand[0]; for (const u of cand) if (load(u) < load(best)) best = u;
    s.owner = best; if (!ownQ.has(best)) ownQ.set(best, []); insertSorted(ownQ.get(best), s);
  }
  function enqueue(s, now) { if (route === 'own') assignOwner(s, now); else insertSorted(pool, s); }
  if (route === 'own') { const p = pool.splice(0); for (const s of p) assignOwner(s, start === -Infinity ? s.arr : start); }
  const allQueues = () => route === 'own' ? [...ownQ.values()] : [pool];
  const size = () => allQueues().reduce((a, Q) => a + Q.length, 0);
  // ---- expiry / resubmission ----
  const resubQ = []; let nResub = 0, nExpired = 0;
  function expireCheck(now) {
    if (opt.expireT == null) return;
    for (const Q of allQueues()) for (let i = Q.length - 1; i >= 0; i--) {
      const s = Q[i]; if (opt.grandfather && s.legacy && s.gen === 0) continue;
      if (s.arr + opt.expireT <= now) {
        Q.splice(i, 1); s.exp = s.arr + opt.expireT; nExpired++;
        if (opt.resub && s.gen < (opt.maxResub ?? 3) && rng() < opt.resub) { const d = -Math.log(1 - rng()) * (opt.resubDelay ?? 30); s.resubAt = s.exp + d; resubQ.push(s); resubQ.sort((a, b) => a.resubAt - b.resubAt); }
        else s.lostFinal = true;
      }
    }
  }
  // ---- picking ----
  const nF = (tier === 2 ? FEAT_T2 : FEAT_T1).length;
  // fast path: static utility part cached per item (levels, rating, type); dynamic part = age, rank, sameOrg, subPrior, selfSub (+T2)
  const statU = new Map();
  const sU = x => { let v = statU.get(x); if (v === undefined) { v = 0; for (let k = 0; k < x.s.length; k++) v += beta[2 + k] * x.s[k]; statU.set(x, v); } return v; };
  function logitPick(Q, tk, filter) {
    let best = -1, bu = -Infinity; const L = Q.length; const iO = 2 + ITEMS[0].s.length;
    const bA = beta[0], bR = beta[1], bO = beta[iO], bP = beta[iO + 1], bS = beta[iO + 2];
    const pre = tk.user + '|';
    for (let j = 0; j < L; j++) { const s = Q[j]; if (filter && !filter(s)) continue; const x = s.x;
      let u = sU(x) + bA * Math.log1p(Math.max(0, tk.t - s.arr)) + bR * Math.log1p(L - 1 - j);
      if (tk.org != null && x.subOrg === tk.org) u += bO;
      if (bP && hist.get(pre + x.subUser)) u += bP;
      if (x.subUser === tk.user) u += bS;
      if (tier === 2) { u += beta[iO + 3] * act30(x, tk.t) + beta[iO + 4] * touched(x, tk.t, tk.user); }
      u += -Math.log(-Math.log(rng() || 1e-12)); if (u > bu) { bu = u; best = j; } }
    return best;
  }
  function pickIdx(Q, tk, disc, filter) {
    const L = Q.length; if (!L) return -1;
    if (filter) { // constrained subset (panel / sprint / priority)
      const idxs = []; for (let j = 0; j < L; j++) if (filter(Q[j])) idxs.push(j); if (!idxs.length) return -1;
      if (disc === 'LOGIT') return logitPick(Q, tk, filter);
      if (disc === 'QUALITY') { let b = idxs[0]; for (const j of idxs) if (qualW(Q[j].x) > qualW(Q[b].x)) b = j; return b; }
      if (disc === 'LIFO') return idxs[idxs.length - 1];
      if (disc === 'RANDOM') return idxs[Math.floor(rng() * idxs.length)];
      return idxs[0];
    }
    switch (disc) {
      case 'FIFO': return 0; case 'LIFO': return L - 1; case 'RANDOM': return Math.floor(rng() * L);
      case 'RANKU': { const u = opt.uDist[Math.floor(rng() * opt.uDist.length)]; return L - 1 - Math.round(u * (L - 1)); }
      case 'LOGIT': return logitPick(Q, tk, null);
      case 'EDF': { const D = opt.edfD ?? 365; for (let j = 0; j < L; j++) if (tk.t - Q[j].arr <= D) return j; return 0; } // W4: oldest item still within its D-day target; overdue items only when none is within target
      case 'SKILL': { for (let j = 0; j < L; j++) if (matched(tk.user, tk.org, Q[j])) return j; return 0; } // oldest matched, else oldest
      case 'QUALITY': { let b = 0; for (let j = 1; j < L; j++) if (qualW(Q[j].x) > qualW(Q[b].x)) b = j; return b; }
    }
    throw new Error('disc ' + disc);
  }
  const isAB = s => s.x.lvl === 'A' || s.x.lvl === 'B';
  function pickFor(tk) {
    const now = tk.t; const disc = opt.disc ?? 'FIFO';
    const old = s => now - s.arr >= (opt.panel?.A ?? opt.sprint?.A ?? 365);
    if (tk.sprint) { const i = pickIdx(pool, tk, opt.sprint.order === 'quality' ? 'QUALITY' : 'FIFO', old); if (i >= 0) return pool.splice(i, 1)[0]; const j = pickIdx(pool, tk, 'FIFO'); return j >= 0 ? pool.splice(j, 1)[0] : null; }
    if (route === 'own') {
      const Q = ownQ.get(tk.user);
      if (Q && Q.length) { const i = pickIdx(Q, tk, opt.ownDisc ?? 'FIFO'); return Q.splice(i, 1)[0]; }
      if (opt.steal) { let bq = null; for (const [u, Q2] of ownQ) if (Q2.length && (!bq || Q2[0].arr < bq[0].arr)) bq = Q2; if (bq) { const s = bq.shift(); s.owner = tk.user; return s; } }
      return null;
    }
    if (opt.panel && (!opt.panel.active || opt.panel.active(now)) && rng() < opt.panel.phi) { const i = pickIdx(pool, tk, opt.panel.order === 'quality' ? 'QUALITY' : 'FIFO', old); if (i >= 0) return pool.splice(i, 1)[0]; }
    if (opt.prioAB) { const i = pickIdx(pool, tk, disc, isAB); if (i >= 0) return pool.splice(i, 1)[0]; }
    const i = pickIdx(pool, tk, disc); return i >= 0 ? pool.splice(i, 1)[0] : null;
  }
  // ---- event loop ----
  let fi = 0; let lostTok = 0; let usedTok = 0; const snaps = {}; const CK = opt.checkpoints ?? [];
  let ci = 0; let nextDay = Math.ceil(Math.max(start === -Infinity ? future[0].arr : start, 0));
  const daily = [];
  function snapshot(now) { const ages = []; for (const Q of allQueues()) for (const s of Q) ages.push(now - s.arr0); for (const s of inProg.values()) if (s) ages.push(now - s.arr0); return { n: ages.length, ages }; }
  function advanceTo(t) {
    while (true) {
      const na = fi < future.length ? future[fi].arr : Infinity, nr = resubQ.length ? resubQ[0].resubAt : Infinity;
      const nd = nextDay, nc = ci < CK.length ? CK[ci] : Infinity;
      const m = Math.min(na, nr, nd, nc); if (m > t) break;
      if (m === nc) { expireCheck(nc); snaps[CK[ci]] = snapshot(nc); ci++; continue; }
      if (m === na) { const s = future[fi++]; enqueue(s, na); continue; }
      if (m === nr) { const s = resubQ.shift(); s.gen++; s.arr = s.resubAt; s.resubAt = null; s.exp = null; s.prog = 0; nResub++; enqueue(s, s.arr); continue; }
      // daily tick: expiry, abandon stale in-progress work, reassign inactive owners
      expireCheck(nd);
      for (const [u, s] of inProg) if (s && s.lastWork < nd - 90) { inProg.set(u, null); s.owner = null; enqueue(s, nd); }
      if (route === 'own' && opt.reassignAfter) for (const [u, Q] of [...ownQ]) { if (u === -1 || (lastTok.get(u) ?? -Infinity) < nd - opt.reassignAfter) { if (!Q.length) continue; const moved = Q.splice(0); for (const s of moved) assignOwner(s, nd); } }
      if (opt.daily) daily.push(size());
      nextDay++;
    }
  }
  for (const tk of toks) {
    advanceTo(tk.t);
    if (!tk.sprint) { lastTok.set(tk.user, tk.t); userOrg.set(tk.user, tk.org); }
    let budget = 1;
    while (budget > 1e-9) {
      let s = inProg.get(tk.user);
      if (!s) { s = pickFor(tk); if (!s) { lostTok += budget; break; } inProg.set(tk.user, s); }
      const k = (tk.sprint || matched(tk.user, tk.org, s)) ? 1 : kappa;
      const left = (s.need - s.prog) * k; const use = Math.min(budget, left);
      s.prog += use / k; budget -= use; s.lastWork = tk.t; usedTok += use;
      if (s.prog >= s.need - 1e-9) { s.dec = tk.t; s.decBy = tk.user; s.mt = !!(tk.sprint || matched(tk.user, tk.org, s)); inProg.set(tk.user, null); if (!tk.sprint) { const hk = tk.user + '|' + s.x.subUser; hist.set(hk, (hist.get(hk) || 0) + 1); } }
    }
    if (tk.sprint) { const s = inProg.get(tk.user); if (s) { inProg.set(tk.user, null); insertSorted(pool, s); } } // unfinished sprint item returns to pool with progress kept
  }
  advanceTo(end);
  const endSnap = snapshot(end);
  return { S, snaps, endSnap, lostTok, usedTok, nResub, nExpired, resubPendingAtEnd: resubQ.length, toks: toks.length, start, end, daily };
}
const ordOf = Object.fromEntries(ITEMS.map((x, i) => [x.id, i]));

// ---------- metrics ----------
const qq = (a, p) => { if (!a.length) return null; const s = a.slice().sort((x, y) => x - y); return s[Math.floor(p * (s.length - 1))]; };
export function metrics(r) {
  const { S, start, end } = r;
  const nw = S.filter(s => !s.legacy);
  const within = d => { const el = nw.filter(s => s.arr0 <= end - d); return el.length ? el.filter(s => s.dec != null && s.dec - s.arr0 <= d).length / el.length : null; };
  const dw = nw.filter(s => s.dec != null).map(s => s.dec - s.arr0);
  const decInWin = S.filter(s => s.dec != null && s.dec >= (start === -Infinity ? 0 : start));
  const lost = S.filter(s => s.lostFinal);
  const realAcc = S.filter(s => s.x.out === 'A');
  const wAll = realAcc.reduce((a, s) => a + qualW(s.x), 0);
  const ages = r.endSnap.ages;
  const qway = decInWin.reduce((a, s) => a + expAcc(s.x) * qualW(s.x) * (end - s.dec) / 365, 0);
  const qwayUnw = decInWin.reduce((a, s) => a + expAcc(s.x) * (end - s.dec) / 365, 0);
  const staleExposure = S.reduce((a, s) => { const stop = Math.min(end, s.dec ?? (s.lostFinal ? s.exp : null) ?? end); const from = Math.max(s.arr0 + 365, start === -Infinity ? -Infinity : start); return a + Math.max(0, stop - from) / 365; }, 0);
  const AB = nw.filter(s => s.x.lvl === 'A' || s.x.lvl === 'B'); const withinAB = d => { const el = AB.filter(s => s.arr0 <= end - d); return el.filter(s => s.dec != null && s.dec - s.arr0 <= d).length / el.length; };
  return {
    decisions: decInWin.length, decisionsLegacy: decInWin.filter(s => s.legacy).length, matchedShare: decInWin.length ? decInWin.filter(s => s.mt).length / decInWin.length : null,
    endPending: ages.length, endPendingMedAge: qq(ages, .5), endPendingShareOver365: ages.length ? ages.filter(a => a > 365).length / ages.length : 0,
    new_medWait: qq(dw, .5), new_p90Wait: qq(dw, .9), within30: within(30), within90: within(90), within365: within(365), AB_within90: withinAB(90),
    expiredEvents: r.nExpired, resubmissions: r.nResub, lostFinal: lost.length,
    lostRealAccepted: lost.filter(s => s.x.out === 'A').length,
    lostRealAcceptedShare: realAcc.length ? lost.filter(s => s.x.out === 'A').length / realAcc.length : 0,
    lostQualWShareOfRealAccepted: wAll ? lost.filter(s => s.x.out === 'A').reduce((a, s) => a + qualW(s.x), 0) / wAll : 0,
    lostExpAccQualW: lost.reduce((a, s) => a + expAcc(s.x) * qualW(s.x), 0),
    lostAB: lost.filter(s => s.x.lvl === 'A' || s.x.lvl === 'B').length,
    QWAY: qway, acceptedItemYears: qwayUnw, staleUnreviewedItemYears: staleExposure,
    lostTokens: r.lostTok, resubPendingAtEnd: r.resubPendingAtEnd,
  };
}
