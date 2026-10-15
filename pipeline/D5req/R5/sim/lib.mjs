// Shared helpers for D5req/A4: data, item features, choice-model features.
import fs from 'fs';
export const NOW = Date.parse('2026-10-07T00:00:00Z') / 864e5;
export const day = s => Date.parse(s) / 864e5;
export const TV = day('2023-01-01'); // validation start (calibration = before)
export function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
export const ITEMS = JSON.parse(fs.readFileSync(new URL('../../A4/items_feat_hmac.json', import.meta.url))).sort((a, b) => a.arr - b.arr || a.id - b.id);
ITEMS.forEach((x, i) => { x.ord = i; x.effortRaw = 1 + x.nRevPre + x.nComPre; });
export const TOK = ITEMS.filter(x => x.dec != null).map(x => ({ t: x.dec, user: x.decUser, org: x.decOrg, realItem: x.id })).sort((a, b) => a.t - b.t || a.realItem - b.realItem);
export const BYID = Object.fromEntries(ITEMS.map(x => [x.id, x]));
const TYPES = ['DIAGNOSTIC', 'PROGNOSTIC', 'PREDISPOSING', 'ONCOGENIC', 'FUNCTIONAL']; // PREDICTIVE baseline
export const FEAT_T1 = ['logAge', 'logRank', 'lvlA', 'lvlB', 'lvlD', 'lvlE', 'ratingC', 'ratingNA', ...TYPES.map(t => 'type_' + t), 'sameOrg', 'subPrior', 'selfSub'];
export const FEAT_T2 = [...FEAT_T1, 'act30', 'touched'];
// static part per item
for (const x of ITEMS) {
  x.s = [x.lvl === 'A' ? 1 : 0, x.lvl === 'B' ? 1 : 0, x.lvl === 'D' ? 1 : 0, x.lvl === 'E' ? 1 : 0, x.rating == null ? 0 : x.rating - 3, x.rating == null ? 1 : 0, ...TYPES.map(t => x.type === t ? 1 : 0)];
}
export function act30(x, t) { let n = 0; const a = x.actT; for (let i = a.length - 1; i >= 0; i--) { if (a[i] > t + 1e-6) continue; if (a[i] < t - 30) break; n++; } return Math.log1p(n); }
export function touched(x, t, user) { const a = x.actT; for (let i = 0; i < a.length && a[i] <= t + 1e-6; i++) if (x.actU[i] === user) return 1; return 0; }
// feature vector of item x for a token (t,user,org), rank = # queued items newer than x, hist = Map(user|subUser -> count)
export function fvec(x, t, user, org, rank, hist, tier) {
  const v = [Math.log1p(Math.max(0, t - x.arr)), Math.log1p(rank), ...x.s, (org != null && x.subOrg === org) ? 1 : 0, hist.get(user + '|' + x.subUser) ? 1 : 0, x.subUser === user ? 1 : 0];
  if (tier === 2) v.push(act30(x, t), touched(x, t, user));
  return v;
}
export const q = (a, p) => { a = a.filter(Number.isFinite).sort((x, y) => x - y); if (!a.length) return null; return a[Math.floor(p * (a.length - 1))]; };
export const ks = (a, b) => { a = a.slice().sort((x, y) => x - y); b = b.slice().sort((x, y) => x - y); let i = 0, j = 0, d = 0; while (i < a.length && j < b.length) { const v = Math.min(a[i], b[j]); while (i < a.length && a[i] <= v) i++; while (j < b.length && b[j] <= v) j++; d = Math.max(d, Math.abs(i / a.length - j / b.length)); } return d; };
export const mean = a => a.reduce((s, x) => s + x, 0) / a.length;
export const ci = (a, lo = .025, hi = .975) => { const s = a.filter(Number.isFinite).sort((x, y) => x - y); if (!s.length) return [null, null, null]; return [mean(s), s[Math.floor(lo * (s.length - 1))], s[Math.ceil(hi * (s.length - 1))]]; };
