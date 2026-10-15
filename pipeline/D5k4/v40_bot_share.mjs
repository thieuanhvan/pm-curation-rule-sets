import fs from 'fs'; import crypto from 'crypto';
const ps = s => s ? s.trim().replace(/_/g,' ') : null;
const STRICT = u => !!u && /(^|[ _-])bot$|bot$|^bot[ _]|[ _]bot[ _]/i.test(u.trim()) ;
const LOOSE = u => !!u && /bot/i.test(u);
const ps0 = s => s ? 'u_' + crypto.createHash('sha256').update(process.env.P17_SALT + s.trim().toLowerCase().replace(/_/g, ' ')).digest('hex').slice(0, 10) : null;
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

const sigU = []; for (const p of Object.values(pages)) { const c = p.c || ''; for (const l of c.split('\n')) for (const g of sigs(l)) if (g.t > Date.UTC(2012,0,1) && g.u) sigU.push({u: g.u.trim(), t: g.t, title: p.t}); }
const cs = cases.filter(x => x.arr >= Date.UTC(2016,0,1) && (x.dec || x.kind === 'pending'));
const decided = cs.filter(x => x.dec);
const share = (arr, f) => ({n: arr.length, k: arr.filter(f).length, p: arr.length ? +(arr.filter(f).length / arr.length).toFixed(4) : null});
const sigS = sigU.filter(g => cs.some(x => x.id === g.title.slice(27)));
const out = {
  note: 'V40: bot share in Wikidata property-proposal sample, from page text signatures only (no revision history was retrieved, so archival/unsigned bot edits are not observable). Strict = name ends with or has a separate token "bot"; loose = "bot" anywhere in the name.',
  sample_n: cs.length, decided_n: decided.length,
  proposer_bot_strict: share(cs, x => STRICT(x.prop)), proposer_bot_loose: share(cs, x => LOOSE(x.prop)),
  decider_bot_strict: share(decided, x => STRICT(x.decU)), decider_bot_loose: share(decided, x => LOOSE(x.decU)),
  decider_unidentified: share(decided, x => !x.decU),
  signatures_n: sigS.length, signatures_bot_strict: share(sigS, g => STRICT(g.u)), signatures_bot_loose: share(sigS, g => LOOSE(g.u)),
  proposals_with_any_bot_signature_strict: share(cs, x => sigS.some(g => g.title.slice(27) === x.id && STRICT(g.u))),
  bot_name_counts_loose: Object.entries(sigS.filter(g => LOOSE(g.u)).reduce((a, g) => (a[STRICT(g.u) ? 'strict' : 'loose_only'] = (a[STRICT(g.u) ? 'strict' : 'loose_only'] || 0) + 1, a), {})),
};
// mass decisions: same decider, same UTC day, >= 10 decisions
const day = {}; for (const x of decided) if (x.decU) { const k = x.decU + '|' + Math.floor(x.dec / 864e5); day[k] = (day[k] || 0) + 1; }
for (const th of [5, 10, 20]) { const big = new Set(Object.entries(day).filter(([, v]) => v >= th).map(([k]) => k)); out['decisions_in_same_decider_day_ge' + th] = share(decided, x => x.decU && big.has(x.decU + '|' + Math.floor(x.dec / 864e5))); }
out.max_decisions_one_decider_one_day = Math.max(...Object.values(day));
fs.writeFileSync('res_v40_wd_bot.json', JSON.stringify(out, null, 1)); console.log(JSON.stringify(out, null, 1));
