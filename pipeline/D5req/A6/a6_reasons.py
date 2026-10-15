# A6 (4): do CIViC rejection events carry reasons outside comment events? Join cached events (../../D5b/cache)
# with moderation / revision-rejection activities pulled into cache/ (activity.note). Notes are analysed only as
# presence, length and templating; no note text is written out. Bot account 385 excluded (as A2/A3).
import os, json, glob, numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(BASE, '..', '..', 'D5b', 'cache')
BOT = {385}; R = {}
def P(k, v): R[k] = v; print(k, json.dumps(v, default=str)[:1500], flush=True)
def wilson(k, n, z=1.96):
    if n == 0: return None
    p = k / n; den = 1 + z*z/n; c = (p + z*z/(2*n)) / den; h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return [round(p, 3), round(c-h, 3), round(c+h, 3), int(n)]
ev, seen = [], set()
for f in sorted(glob.glob(os.path.join(SRC, 'ev_*.json'))):
    for e in json.load(open(f, encoding='utf-8')):
        if e['id'] in seen: continue
        seen.add(e['id']); ev.append(e)
E = pd.DataFrame([{'eid': e['id'], 'act': e['action'], 't': pd.Timestamp(e['createdAt']), 'u': (e.get('originatingUser') or {}).get('id'),
                   'ot': (e.get('originatingObject') or {}).get('__typename'), 'oid': (e.get('originatingObject') or {}).get('id'),
                   'st': (e.get('subject') or {}).get('__typename'), 'sid': (e.get('subject') or {}).get('id')} for e in ev])
E = E[~E.u.isin(BOT)].copy()
note = {}; matched_acts = 0
for t in ('MODERATE_EVIDENCE_ITEM', 'REJECT_REVISIONS'):
    for a in json.load(open(os.path.join(BASE, 'cache', f'act_{t}.json'), encoding='utf-8')):
        n = (a.get('note') or '').strip()
        for x in a['events']: note[x['id']] = n
E['note'] = E.eid.map(note).fillna('')
E['has_act'] = E.eid.isin(note.keys())
P('activity_link_coverage', {a: wilson(int(g.has_act.sum()), len(g)) for a, g in E[E.act.isin(['REJECTED', 'ACCEPTED', 'REVISION_REJECTED'])].groupby('act')})
rv = E[(E.ot == 'Revision') & (E.st == 'EvidenceItem')]
rev2ei = dict(zip(rv.oid, rv.sid))
sug = E[E.act == 'REVISION_SUGGESTED']; rev_sugg = dict(zip(sug.oid, sug.u))
cm_rev = E[(E.act == 'COMMENTED') & (E.st == 'Revision')].copy(); cm_rev['ei'] = cm_rev.sid.map(rev2ei); cm_rev['rev'] = cm_rev.sid
cm_ei = E[(E.act == 'COMMENTED') & (E.st == 'EvidenceItem')].copy(); cm_ei['ei'] = cm_ei.sid; cm_ei['rev'] = np.nan
comments = pd.concat([cm_ei, cm_rev])[['ei', 'rev', 't', 'u']]
cbyei = {k: g for k, g in comments.dropna(subset=['ei']).groupby('ei')}
subm = E[(E.act == 'SUBMITTED') & (E.st == 'EvidenceItem')].drop_duplicates('sid'); submitter = dict(zip(subm.sid, subm.u))
rr = E[(E.act == 'REVISION_REJECTED') & (E.ot == 'Revision')].copy(); rr['ei'] = rr.oid.map(rev2ei)
rrbyei = {k: g for k, g in rr.dropna(subset=['ei']).groupby('ei')}
D30 = pd.Timedelta(days=30); D1 = pd.Timedelta(days=1)
def has(df, cond): return bool(df is not None and len(df) and cond(df).any())
rows = []
for r in E[(E.act == 'REJECTED') & (E.st == 'EvidenceItem')].itertuples():
    c = cbyei.get(r.sid); x = rrbyei.get(r.sid)
    o = {'t': r.t, 'self': submitter.get(r.sid) == r.u,
         'A2_comment_before': has(c, lambda d: d.t < r.t),
         'A2_comment_pm30': has(c, lambda d: (d.t - r.t).abs() <= D30),
         'A2_comment_by_rejector_before_sameday': has(c, lambda d: (d.u == r.u) & (d.t <= r.t + D1)),
         'note_on_rejection_event': bool(r.note),
         'note_on_revision_rejection_pm30': has(x, lambda d: ((d.t - r.t).abs() <= D30) & (d.note.str.len() > 0)),
         'note_len': len(r.note)}
    o['union_strict'] = o['A2_comment_before'] or o['note_on_rejection_event'] or has(x, lambda d: (d.t <= r.t + D1) & (d.note.str.len() > 0))
    o['union_pm30'] = o['A2_comment_pm30'] or o['note_on_rejection_event'] or o['note_on_revision_rejection_pm30']
    rows.append(o)
J = pd.DataFrame(rows); J['period'] = np.where(J.t >= pd.Timestamp('2025-03-20T16:16:24Z'), 'after_2025-03-20', 'before_2025-03-20')
cols = ['A2_comment_before', 'A2_comment_pm30', 'A2_comment_by_rejector_before_sameday', 'note_on_rejection_event', 'note_on_revision_rejection_pm30', 'union_strict', 'union_pm30']
groups = [('all', J), ('other_rejector', J[~J.self]), ('self_withdrawal', J[J.self])]
groups += [(f'all|{p}', g) for p, g in J.groupby('period')] + [(f'other_rejector|{p}', g) for p, g in J[~J.self].groupby('period')]
P('EID_rejections_reasoned', {lab: {c: wilson(int(g[c].sum()), len(g)) for c in cols} for lab, g in groups})
P('EID_rejection_note_presence_by_year', {int(y): wilson(int(g.note_on_rejection_event.sum()), len(g)) for y, g in J.groupby(J.t.dt.year)})
nl = J.loc[J.note_len > 0, 'note_len']
P('EID_rejection_note_length', {'n': int(len(nl)), 'median': float(nl.median()) if len(nl) else None, 'share_lt15chars': round(float((nl < 15).mean()), 3) if len(nl) else None})

rows = []
cr = {k: g for k, g in cm_rev.groupby('rev')}
for r in rr.itertuples():
    c = cr.get(r.oid); s = rev_sugg.get(r.oid)
    o = {'t': r.t, 'self': s == r.u, 'A2_revcomment_before': has(c, lambda d: d.t < r.t),
         'revcomment_pm30': has(c, lambda d: (d.t - r.t).abs() <= D30), 'note': bool(r.note), 'note_len': len(r.note)}
    o['union_strict'] = o['A2_revcomment_before'] or o['note']; o['union_pm30'] = o['revcomment_pm30'] or o['note']; rows.append(o)
Q = pd.DataFrame(rows); Q['era'] = pd.cut(Q.t.dt.year, [2014, 2022, 2023, 2026], labels=['2015-22', '2023', '2024-26']).astype(str)
cols = ['A2_revcomment_before', 'revcomment_pm30', 'note', 'union_strict', 'union_pm30']
groups = [('all', Q), ('other_rejector', Q[~Q.self]), ('self_withdrawal', Q[Q.self])]
groups += [(f'other_rejector|{e}', g) for e, g in Q[~Q.self].groupby('era')] + [(f'self|{e}', g) for e, g in Q[Q.self].groupby('era')]
P('revision_rejections_reasoned', {lab: {c: wilson(int(g[c].sum()), len(g)) for c in cols} for lab, g in groups})
day = Q.groupby(Q.t.dt.date).size(); P('revision_rejection_mass_days_ge100', {str(k): int(v) for k, v in day[day >= 100].items()})
nl = Q.loc[Q.note_len > 0, 'note_len']
P('revision_note_length', {'n': int(len(nl)), 'median': float(nl.median()), 'share_lt15chars': round(float((nl < 15).mean()), 3)})
vc = rr.note[rr.note.str.len() > 0].value_counts()
P('revision_note_templating', {'n_notes': int(vc.sum()), 'distinct': int(len(vc)), 'top1_share': round(float(vc.iloc[0] / vc.sum()), 3), 'top5_share': round(float(vc.iloc[:5].sum() / vc.sum()), 3)})
# other-rejector revision rejections excluding mass days (>=100/day) and templated notes (identical text used >=20 times)
tmpl = set(vc[vc >= 20].index); mass = set(day[day >= 100].index)
Q['note_text_idx'] = rr.note.values; Q['mass'] = Q.t.dt.date.isin(mass); Q['templated'] = Q.note_text_idx.isin(tmpl)
g = Q[~Q.self & ~Q.mass]
P('revision_other_rejector_excl_massdays', {'n': len(g), 'union_strict': wilson(int(g.union_strict.sum()), len(g)),
   'union_strict_nontemplated': wilson(int((g.A2_revcomment_before | (g.note & ~g.templated)).sum()), len(g))})
json.dump(R, open(os.path.join(BASE, 'res_a6_reasons.json'), 'w'), indent=1, default=str)
print('done')
