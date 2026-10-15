// Build sampled choice sets (chosen + 40 uniformly sampled queued alternatives) for every observed decision token.
// Output: choice_t1.csv / includes T2 columns; column 'period' = cal (<2023) / val.
import fs from 'fs';
import { ITEMS, TOK, BYID, TV, FEAT_T2, fvec, mulberry } from './lib.mjs';
const rng = mulberry(20261007); const K = 40;
const queue = []; let ai = 0; const hist = new Map(); const rows = [];
let gid = 0;
for (const tk of TOK) {
  while (ai < ITEMS.length && ITEMS[ai].arr <= tk.t) queue.push(ITEMS[ai++]);
  const idx = queue.findIndex(x => x.id === tk.realItem); const L = queue.length;
  if (L >= 2) {
    const alts = new Set(); const m = Math.min(K, L - 1);
    while (alts.size < m) { const j = Math.floor(rng() * L); if (j !== idx) alts.add(j); }
    gid++;
    for (const j of [idx, ...alts]) { const x = queue[j]; const v = fvec(x, tk.t, tk.user, tk.org, L - 1 - j, hist, 2); rows.push([gid, j === idx ? 1 : 0, tk.t < TV ? 'cal' : 'val', +(tk.t).toFixed(2), ...v.map(z => +z.toFixed(4))].join(',')); }
  }
  queue.splice(idx, 1);
  const k = tk.user + '|' + BYID[tk.realItem].subUser; hist.set(k, (hist.get(k) || 0) + 1);
}
fs.writeFileSync('choice.csv', ['gid,chosen,period,t,' + FEAT_T2.join(','), ...rows].join('\n'));
console.log('groups', gid, 'rows', rows.length);
