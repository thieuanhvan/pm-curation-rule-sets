import fs from 'fs'; import crypto from 'crypto';
const ps = s => s ? 'u_' + crypto.createHash('sha256').update(process.env.P17_SALT + s.trim().toLowerCase().replace(/_/g, ' ')).digest('hex').slice(0, 10) : null;
const M = {January:0,February:1,March:2,April:3,May:4,June:5,July:6,August:7,September:8,October:9,November:10,December:11};
const TS = /(\d{1,2}):(\d{2}), (\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4}) \(UTC\)/g;
const USER = /\[\[\s*(?:User|Benutzer|Utilisateur|Usuario|Utente|Gebruiker|Special:Contributions\/)[: ]?([^|\]\/#]+)/gi;
function sigs(line) { const out = []; let m; TS.lastIndex = 0;
  while ((m = TS.exec(line))) { const t = Date.UTC(+m[5], M[m[4]], +m[3], +m[1], +m[2]); const before = line.slice(0, m.index); let u = null, mm; USER.lastIndex = 0; while ((mm = USER.exec(before))) u = mm[1]; out.push({t, u}); } return out; }
const pages = {}; for (const f of fs.readdirSync('wd')) for (const p of JSON.parse(fs.readFileSync('wd/' + f))) pages[p.t] = p;
const cases = []; const stat = {pages: Object.keys(pages).length, noTemplate: 0, redirect: 0, noSig: 0};
for (const p of Object.values(pages)) {
  const c = p.c || ''; if (/^#REDIRECT/i.test(c)) { stat.redirect++; continue; }
  if (!/\{\{\s*Property proposal\s*\n?\s*\|/i.test(c)) { stat.noTemplate++; continue; }
  let st = (c.match(/\|\s*status\s*=([^\n|]*)/i) || [, ''])[1].replace(/<!--.*?-->/g, '').trim();
  const lines = c.split('\n'); const all = lines.flatMap(sigs).filter(s => s.t > Date.UTC(2012, 0, 1));
  if (!all.length) { stat.noSig++; continue; }
  const arr = Math.min(...all.map(s => s.t));
  const pb = (c.match(/\|\s*proposed by\s*=([^\n]*)/i) || [, ''])[1]; let prop = null; { let mm; USER.lastIndex = 0; while ((mm = USER.exec(pb))) { prop = mm[1]; break; } }
  if (!prop) prop = all.sort((a, b) => a.t - b.t)[0].u;
  let kind; const pid = (st.match(/^P?(\d+)$/i) || [])[1];
  if (pid) kind = 'done'; else if (/not done|rejected|declined/i.test(st)) kind = 'notdone'; else if (/withdrawn/i.test(st)) kind = 'withdrawn';
  else if (/^(|ready|on hold|hold|under discussion|in progress|needs? .*)$/i.test(st)) kind = 'pending'; else kind = 'other:' + st.slice(0, 20);
  let dec = null, decUser = null;
  if (kind === 'done' || kind === 'notdone' || kind === 'withdrawn') {
    const re = kind === 'done' ? new RegExp(`\{\{\s*(done|created)|\bcreated\b|\{\{\s*P\|P?${pid}\s*\}\}|Property:P${pid}\b`, 'i') : kind === 'notdone' ? /not done|not created|\{\{\s*nd\s*\}\}|closing|closed|no consensus|rejected/i : /withdraw/i;
    for (let i = 0; i < lines.length; i++) if (re.test(lines[i]) && !/^\s*\|/.test(lines[i])) { let s = sigs(lines[i]); for (let j = 1; !s.length && j <= 2 && i + j < lines.length; j++) s = sigs(lines[i + j]); if (s.length && s[s.length-1].t >= arr) { const last = s[s.length - 1]; dec = last.t; decUser = last.u; } }
    // use the LAST matching line (closure is usually last)
  }
  cases.push({id: p.t.slice(27), kind, pid: pid ? +pid : null, arr, dec, prop: ps(prop), decU: ps(decUser), lastEdit: Date.parse(p.ts), nSig: all.length});
}
const by = {}; for (const x of cases) by[x.kind] = (by[x.kind] || 0) + 1;
const miss = cases.filter(x => ['done','notdone','withdrawn'].includes(x.kind) && !x.dec).length;
console.log(stat, by, 'decided without dec ts', miss);
fs.writeFileSync('wd_cases.json', JSON.stringify(cases));
// validation: Spearman between pid and dec for done
const d = cases.filter(x => x.kind === 'done' && x.dec && x.pid);
const rank = a => { const s = a.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]); const r = []; s.forEach(([, i], k) => r[i] = k); return r; };
const r1 = rank(d.map(x => x.pid)), r2 = rank(d.map(x => x.dec)); const n = d.length; let s = 0; for (let i = 0; i < n; i++) s += (r1[i] - r2[i]) ** 2;
console.log('spearman pid~decTs', (1 - 6 * s / (n * (n * n - 1))).toFixed(4), 'n', n);
