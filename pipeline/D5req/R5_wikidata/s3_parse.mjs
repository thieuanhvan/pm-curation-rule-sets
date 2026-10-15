// Parser = D5k4/wd_parse.mjs (same status/arrival/decision rules), applied to the census pull; new salt process.env.P17_SALT_WD;
// adds: not-done rationale class, open-status detail, done-pid list. Raw usernames never written.
import fs from 'fs'; import crypto from 'crypto';
const ps = s => s ? 'u_' + crypto.createHash('sha256').update(process.env.P17_SALT_WD + s.trim().toLowerCase().replace(/_/g, ' ')).digest('hex').slice(0, 12) : null;
const M = {January:0,February:1,March:2,April:3,May:4,June:5,July:6,August:7,September:8,October:9,November:10,December:11};
const TS = /(\d{1,2}):(\d{2}), (\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4}) \(UTC\)/g;
const USER = /\[\[\s*(?:User|Benutzer|Utilisateur|Usuario|Utente|Gebruiker|Special:Contributions\/)[: ]?([^|\]\/#]+)/gi;
function sigs(line) { const out = []; let m; TS.lastIndex = 0;
  while ((m = TS.exec(line))) { const t = Date.UTC(+m[5], M[m[4]], +m[3], +m[1], +m[2]); const before = line.slice(0, m.index); let u = null, mm; USER.lastIndex = 0; while ((mm = USER.exec(before))) u = mm[1]; out.push({t, u}); } return out; }
const pages = {};
for (const f of fs.readdirSync('raw/content').filter(f => f.startsWith('c_')).sort()) for (const p of JSON.parse(fs.readFileSync('raw/content/' + f))) { if (!pages[p.id] || (pages[p.id].c == null && p.c != null)) pages[p.id] = p; }
const RAT = [['duplicate_or_existing_property', /duplicate|already (exists|have|covered)|existing propert|redundant|covered by|use \{\{\s*P\|/i],
  ['model_as_item_or_qualifier', /\bas (an? )?items?\b|use (an? )?items?|qualifier|model(l)?(ed|ing)? (it )?(with|as|using|via)|instead of (a )?(new )?property|better (handled|modelled|modeled)/i],
  ['no_consensus_or_stale', /no consensus|lack of consensus|not (enough|sufficient) support|no support|insufficient support|stale|no (further )?(activity|progress|response|discussion)|inactive|without (any )?support|unsupported|opposed|too many oppos/i],
  ['source_defunct_or_unstable', /dead link|defunct|offline|no longer (exist|available|online)|not (stable|persistent)|website (is )?down/i],
  ['scope_or_notability', /out of scope|not notable|too (specific|narrow|niche)|too few|small number|not useful/i]];
const cases = []; const stat = {pages: Object.keys(pages).length, noContent: 0, redirect: 0, noTemplate: 0, noSig: 0, archiveOrMeta: 0};
for (const p of Object.values(pages)) {
  const c = p.c; if (c == null) { stat.noContent++; continue; }
  if (/^#REDIRECT/i.test(c)) { stat.redirect++; continue; }
  const sub = p.t.slice('Wikidata:Property proposal/'.length);
  if (/^(Archive|Editintro)\//.test(sub)) { stat.archiveOrMeta++; continue; }
  if (!/\{\{\s*Property proposal\s*\n?\s*\|/i.test(c)) { stat.noTemplate++; continue; }
  let st = (c.match(/\|\s*status\s*=([^\n|]*)/i) || [, ''])[1].replace(/<!--.*?-->/g, '').trim();
  const lines = c.split('\n'); const all = lines.flatMap(sigs).filter(s => s.t > Date.UTC(2012, 0, 1));
  if (!all.length) { stat.noSig++; continue; }
  const arr = Math.min(...all.map(s => s.t));
  const pb = (c.match(/\|\s*proposed by\s*=([^\n]*)/i) || [, ''])[1]; let prop = null; { let mm; USER.lastIndex = 0; while ((mm = USER.exec(pb))) { prop = mm[1]; break; } }
  if (!prop) prop = all.slice().sort((a, b) => a.t - b.t)[0].u;
  let kind; const pid = (st.match(/^P?(\d+)$/i) || [])[1];
  if (pid) kind = 'done'; else if (/not done|rejected|declined/i.test(st)) kind = 'notdone'; else if (/withdrawn/i.test(st)) kind = 'withdrawn';
  else if (/^(|ready|on hold|hold|under discussion|in progress|needs? .*)$/i.test(st)) kind = 'pending'; else kind = 'other:' + st.slice(0, 20);
  let dec = null, decUser = null, decLine = -1;
  if (kind === 'done' || kind === 'notdone' || kind === 'withdrawn') {
    const re = kind === 'done' ? new RegExp(`\{\{\s*(done|created)|\bcreated\b|\{\{\s*P\|P?${pid}\s*\}\}|Property:P${pid}\b`, 'i') : kind === 'notdone' ? /not done|not created|\{\{\s*nd\s*\}\}|closing|closed|no consensus|rejected/i : /withdraw/i;
    for (let i = 0; i < lines.length; i++) if (re.test(lines[i]) && !/^\s*\|/.test(lines[i])) { let s = sigs(lines[i]); for (let j = 1; !s.length && j <= 2 && i + j < lines.length; j++) s = sigs(lines[i + j]); if (s.length && s[s.length-1].t >= arr) { const last = s[s.length - 1]; dec = last.t; decUser = last.u; decLine = i; } }
  }
  let rationale = null;
  if (kind === 'notdone') { const txt = decLine >= 0 ? lines.slice(Math.max(0, decLine - 2), decLine + 2).join(' ') : '';
    rationale = (RAT.find(([, r]) => r.test(txt)) || ['other_or_unstated'])[0]; }
  cases.push({id: p.t.slice(27), kind, st: kind === 'pending' ? (st || 'blank') : undefined, pid: pid ? +pid : null, arr, dec, prop: ps(prop), decU: ps(decUser), lastEdit: Date.parse(p.ts), nSig: all.length, rationale});
}
const by = {}; for (const x of cases) by[x.kind] = (by[x.kind] || 0) + 1;
const miss = cases.filter(x => ['done','notdone','withdrawn'].includes(x.kind) && !x.dec).length;
console.log(stat, by, 'decided without dec ts', miss);
fs.writeFileSync('wd_cases_census.json', JSON.stringify(cases));
fs.writeFileSync('parse_stat.json', JSON.stringify({stat, by, decidedWithoutTs: miss}, null, 1));
