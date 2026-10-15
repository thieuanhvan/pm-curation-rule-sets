// Backlog forecast 2023-01..2026-09 (month ends) from rates calibrated on <= 2022, vs naive baselines.
// Also: historical capacity bursts (for the curation-sprint policy).
import fs from 'fs';
import { ITEMS, TOK, TV, mulberry, q, mean } from './lib.mjs';
const mKey = t => { const d = new Date(t * 864e5); return d.getUTCFullYear() * 12 + d.getUTCMonth(); };
const k0 = mKey(ITEMS[0].arr), kTV = mKey(TV), kEnd = mKey(Date.parse('2026-09-30') / 864e5);
const A = {}, D = {}; for (const x of ITEMS) A[mKey(x.arr)] = (A[mKey(x.arr)] || 0) + 1; for (const t of TOK) D[mKey(t.t)] = (D[mKey(t.t)] || 0) + 1;
const monthEnd = k => Date.UTC(Math.floor(k / 12), k % 12 + 1, 1) / 864e5;
const backlogAt = c => ITEMS.filter(x => x.arr < c && (x.dec == null || x.dec >= c)).length;
const obs = []; for (let k = kTV; k <= kEnd; k++) obs.push(backlogAt(monthEnd(k)));
const B0 = backlogAt(TV);
const months = (a, b) => { const r = []; for (let k = a; k <= b; k++) r.push(k); return r; };
const H = kEnd - kTV + 1;
const err = (pred) => { const e = pred.map((p, i) => p - obs[i]); return { RMSE: Math.sqrt(mean(e.map(z => z * z))), MAE: mean(e.map(Math.abs)), MAPE: mean(e.map((z, i) => Math.abs(z) / obs[i])), endErr: e[e.length - 1], endPred: pred[pred.length - 1] }; };
const res = { B0_2023_01_01: B0, obsEnd_2026_09: obs[obs.length - 1], horizonMonths: H, models: {} };
// model: queue-accounting with block-bootstrapped monthly (arrivals, tokens) pairs from a calibration window
function boot(win, reps = 2000, seed = 7) {
  const rng = mulberry(seed); const pairs = months(win[0], win[1]).map(k => [A[k] || 0, D[k] || 0]); const paths = [];
  for (let r = 0; r < reps; r++) { let b = B0; const p = []; for (let h = 0; h < H; h++) { const [a, d] = pairs[Math.floor(rng() * pairs.length)]; b = Math.max(0, b + a - d); p.push(b); } paths.push(p); }
  const point = Array.from({ length: H }, (_, h) => mean(paths.map(p => p[h])));
  const lo = Array.from({ length: H }, (_, h) => q(paths.map(p => p[h]), .05)), hi = Array.from({ length: H }, (_, h) => q(paths.map(p => p[h]), .95));
  const cover = obs.filter((o, h) => o >= lo[h] && o <= hi[h]).length / H;
  return { ...err(point), PI90_coverage: cover, PI90_end: [lo[H - 1], hi[H - 1]], meanNetPerMonth: mean(pairs.map(p => p[0] - p[1])) };
}
const kk = (y, m) => y * 12 + m;
res.models.QUEUE_rates2021_22 = boot([kk(2021, 0), kk(2022, 11)]);
res.models.QUEUE_rates2017_22 = boot([kk(2017, 0), kk(2022, 11)]);
res.models.NAIVE_noChange = err(obs.map(() => B0));
{ // linear trend on month-end backlog 2017-01..2022-12 (OLS)
  const xs = months(kk(2017, 0), kk(2022, 11)); const ys = xs.map(k => backlogAt(monthEnd(k)));
  const mx = mean(xs), my = mean(ys); const b = xs.reduce((s, x, i) => s + (x - mx) * (ys[i] - my), 0) / xs.reduce((s, x) => s + (x - mx) ** 2, 0);
  res.models.NAIVE_linearTrend2017_22 = { ...err(months(kTV, kEnd).map(k => my + b * (k - mx))), slopePerMonth: b };
}
{ // random walk with drift = mean monthly change over 2022
  const xs = months(kk(2022, 0), kk(2022, 11)).map(k => backlogAt(monthEnd(k))); const drift = (xs[11] - backlogAt(Date.UTC(2021, 11, 31) / 864e5 + 1)) / 12;
  res.models.NAIVE_drift2022 = { ...err(months(kTV, kEnd).map((k, h) => B0 + drift * (h + 1))), driftPerMonth: drift };
}
// historical capacity bursts: months with tokens > median + 3*MAD (2016-01..2026-09; 2015 import excluded)
const mk = months(kk(2016, 0), kEnd); const tv = mk.map(k => D[k] || 0); const med = q(tv, .5); const mad = q(tv.map(v => Math.abs(v - med)), .5);
const thr = med + 3 * mad; const bursts = mk.map((k, i) => ({ ym: `${Math.floor(k / 12)}-${String(k % 12 + 1).padStart(2, '0')}`, tokens: tv[i], excess: tv[i] - med })).filter(b => b.tokens > thr);
res.bursts = { monthlyTokensMedian: med, MAD: mad, threshold: thr, nBurstMonths: bursts.length, perYear: bursts.length / (mk.length / 12), excessMedian: q(bursts.map(b => b.excess), .5), excessTotal: bursts.reduce((s, b) => s + b.excess, 0), list: bursts,
  meanMonthlyTokens2023_26: mean(months(kTV, kEnd).map(k => D[k] || 0)), meanMonthlyArrivals2023_26: mean(months(kTV, kEnd).map(k => A[k] || 0)) };
fs.writeFileSync('results_forecast.json', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, (k, v) => typeof v === 'number' ? +v.toFixed(3) : v, 1).slice(0, 4000));
// decomposition: which input is mis-forecast? (oracle arrivals + calibrated tokens, and vice versa)
{
  const win = months(kk(2021, 0), kk(2022, 11)); const mA = mean(win.map(k => A[k] || 0)), mD = mean(win.map(k => D[k] || 0));
  const path = (fa, fd) => { let b = B0; return months(kTV, kEnd).map(k => (b = Math.max(0, b + fa(k) - fd(k)))); };
  res.decomposition = { meanMonthlyArrivals2021_22: mA, meanMonthlyTokens2021_22: mD,
    oracleArrivals_calTokens: err(path(k => A[k] || 0, () => mD)), calArrivals_oracleTokens: err(path(() => mA, k => D[k] || 0)), oracleBoth: err(path(k => A[k] || 0, k => D[k] || 0)) };
  fs.writeFileSync('results_forecast.json', JSON.stringify(res, null, 1));
  console.log('DECOMP', JSON.stringify(res.decomposition));
}
