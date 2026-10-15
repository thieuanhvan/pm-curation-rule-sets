// R3 copy of ../../D5k4b/classify_v2.mjs with the REJ_KW typo fixed (#d+ -> #\d+, 2 places); sensitivity only.
// Transparent rule-based classifier for closed term-request tickets: ACC / REJ / UNCLEAR.
// Decision list (first matching tier wins; conflicting signals within a tier -> UNCLEAR at that tier, continue to next tier only if none fired).
export const REJ_LABEL = /^(duplicate|wontfix|wont fix|won't fix|invalid|out of scope|out-of-scope|rejected|declined|not planned|no action)$/i;
const REJ_KW = /\b(duplicates?|dup(licate)? of|already (exists?|have|covered|in (go|hpo|the ontology))|existing term|out of scope|not in scope|outside (the )?scope|won'?t (add|fix|be)|will not (add|be)|not going to|declin\w*|withdraw\w*|no longer (needed|required)|not (be )?needed|not needed|don'?t (think|need)|do not need|use (the )?existing|can (already )?be captured|instead,? (use|annotate)|not (a )?(go|hpo|phenotype)\b|stale|no response|did not hear|lack of response|closing (this )?(as|for now|due)|not add(ing)?|rather than (adding|creating)|merged? (in)?to (an )?existing|obsoleted? instead|is not a (phenotype|term)|(will be |is )?(addressed|handled|tracked|continued|covered) (in|by|at) #\d+|moved to #\d+|superseded by)/i;
const ACC_KW = /\b(added|has been added|have been added|created|have created|new term|ntrs? (is|are) (done|in)|is now (in|available)|now exists|done|fixed|merged|will be (in|available)|available (in|from) the next|in the next release|implemented|adding (it|this|them|to|the|with|as)|(i|we) (can|will|'ll) add (it|this|them)|i'?ll add|i (have )?made|made the (new )?term|term is (live|in)|thanks?,? (it'?s|this is) (in|done))\b/i;
const REJ_WEAK = /(clos(e|ing) (this|the) (issue|ticket|request)|hold off|is unclear|meaning of .{0,40} unclear|(does|do) not use|is a disease|disease rather than|rather than a phenotyp|synonym (of|for)|should not be a (new )?term|not (be )?a (new|separate) term|we would use|can be (coded|annotated|captured|represented|described) (with|by|using)|no context|hard to define|i will close)/i;
const ID = /\b(GO|HP)[:_](\d{7})\b/g;
export function classify(t, repo) {
  const ev = t.events; const closeEv = ev.filter(e => e.ev === 'closed').pop();
  const closeT = closeEv?.t || t.x;
  const sig = [];
  // labels present at close (from issue snapshot + timeline label events)
  const labs = new Set(t.lab); for (const e of ev) { if (e.ev === 'labeled' && e.t <= closeT) labs.add(e.label); }
  const rl = [...labs].filter(l => REJ_LABEL.test(l));
  // Tier 1: explicit state / labels / duplicate marking
  const t1 = [];
  if (t.sr === 'not_planned' || closeEv?.sr === 'not_planned' || closeEv?.sr === 'duplicate') t1.push(['REJ', 'state_reason:' + (closeEv?.sr || t.sr)]);
  if (rl.length) t1.push(['REJ', 'label:' + rl.join('|')]);
  if (ev.some(e => e.ev === 'marked_as_duplicate')) t1.push(['REJ', 'marked_as_duplicate']);
  // Tier 2: closed by a commit / merged same-repo PR that references the ticket
  const t2 = [];
  if (closeEv?.commit) t2.push(['ACC', 'closed_by_commit']);
  const prs = ev.filter(e => e.src && e.src.pr && e.src.repo === repo && e.src.merged && e.src.merged <= addDays(closeT, 2));
  if (prs.length) t2.push(['ACC', 'merged_PR:' + prs.length]);
  if (ev.some(e => e.ev === 'connected')) t2.push(['ACC', 'connected_PR']);
  // Tier 3: wording of the last 3 comments up to closure (+ closing-PR titles)
  const cm = ev.filter(e => e.ev === 'commented' && e.t <= addDays(closeT, 0.01)).slice(-3);
  const txt = cm.map(e => e.body).join('\n');
  const t3 = []; let useTxt = txt; for (const c of cm.slice().reverse()) { const lr = REJ_KW.test(c.body), la = ACC_KW.test(c.body); if (lr || la) { useTxt = c.body; break; } } const r3 = useTxt.match(REJ_KW), a3 = useTxt.match(ACC_KW);
  const ids = [...txt.matchAll(ID)].map(m => m[1] + ':' + m[2]);
  if (r3) t3.push(['REJ', 'kw:' + r3[0].toLowerCase()]);
  if (a3) t3.push(['ACC', 'kw:' + a3[0].toLowerCase() + (ids.length ? '+id' : '')]);
  // Tier 3w (v2): weak decline phrasing in the last comment that carries any keyword, only if no accept keyword anywhere in the last 3 comments
  const t3w = []; if (!a3 && !r3) { for (const c of cm.slice().reverse()) { const m = c.body.match(REJ_WEAK); if (m) { t3w.push(['REJ', 'weak:' + m[0].toLowerCase()]); break; } } }
  // Tier 4: weaker structural traces: referencing commit in same repo before close, or ID mentioned in last comments
  const t4 = [];
  if (ev.some(e => e.ev === 'referenced' && e.commit && e.t <= addDays(closeT, 0.01))) t4.push(['ACC', 'referenced_by_commit']);
  if (!t3.length && ids.length) t4.push(['ACC', 'id_in_last_comments']);
  for (const [tier, s] of [[1, t1], [2, t2], [3, t3], [3.7, t3w], [4, t4]]) {
    if (!s.length) continue; const cls = new Set(s.map(x => x[0]));
    sig.push(...s.map(x => 'T' + tier + ':' + x[0] + ':' + x[1]));
    if (cls.size === 1) return {cls: [...cls][0], tier, sig, closeT};
    // within-tier conflict: tier-3 conflict resolved by the last comment alone
    if (tier === 3) { const last = cm.at(-1)?.body || ''; const r = REJ_KW.test(last), a = ACC_KW.test(last);
      if (r !== a) return {cls: r ? 'REJ' : 'ACC', tier: 3.5, sig, closeT}; }
    return {cls: 'UNCLEAR', tier, sig, closeT};
  }
  return {cls: 'UNCLEAR', tier: 0, sig: ['no_signal', 'comments:' + ev.filter(e => e.ev === 'commented').length], closeT};
}
function addDays(iso, d) { return new Date(Date.parse(iso) + d * 864e5).toISOString(); }
export const idsIn = t => { const s = new Set(); for (const e of t.events) { for (const m of ((e.body || '') + ' ' + (e.src?.title || '') + ' ' + (e.rename?.to || '')).matchAll(ID)) s.add(m[1] + ':' + m[2]); } return [...s]; };
