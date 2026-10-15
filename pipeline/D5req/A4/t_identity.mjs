// sanity checks: (i) full-history FIFO with unit effort reproduces D5sim FIFO numbers; (ii) backlog path invariance across disciplines
import { run, metrics } from './sim2.mjs';
import { TV, NOW } from './lib.mjs';
const t0 = Date.now();
for (const disc of ['FIFO', 'LIFO', 'RANDOM']) { const r = run({ disc, daily: true }, 3); const m = metrics(r); console.log(disc, 'endPending', m.endPending, 'decisions', m.decisions, 'lostTok', r.lostTok, 'medWait', m.new_medWait?.toFixed(1), 'within90', m.within90?.toFixed(3), 'sumDaily', r.daily.reduce((a, b) => a + b, 0)); }
for (const disc of ['FIFO', 'LIFO']) { const r = run({ disc, start: TV, daily: true }, 3); const m = metrics(r); console.log('fwd', disc, m.endPending, m.decisions, r.daily.reduce((a, b) => a + b, 0)); }
console.log('ms', Date.now() - t0);
