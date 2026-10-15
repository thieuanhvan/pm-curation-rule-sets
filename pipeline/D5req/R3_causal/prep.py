# R3_causal prep: build object tables and a monthly panel for evidence items (EID) and revisions (REV)
# from the cached CIViC event log (../../D5b/cache) and activity notes (../A6/cache).
# Bot account 385 excluded (as A2/A3/A6). Output: panel.pkl (aggregate monthly), objs.pkl (internal, numeric ids only).
import os, json, glob, numpy as np, pandas as pd
B = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(B, '..', '..', 'D5b', 'cache')
BOT = {385}
ev, seen = [], set()
for f in sorted(glob.glob(os.path.join(SRC, 'ev_*.json'))):
    for e in json.load(open(f, encoding='utf-8')):
        if e['id'] in seen: continue
        seen.add(e['id']); ev.append(e)
E = pd.DataFrame([{'eid': e['id'], 'act': e['action'], 't': pd.Timestamp(e['createdAt']).tz_localize(None),
                   'u': (e.get('originatingUser') or {}).get('id'),
                   'ot': (e.get('originatingObject') or {}).get('__typename'), 'oid': (e.get('originatingObject') or {}).get('id'),
                   'st': (e.get('subject') or {}).get('__typename'), 'sid': (e.get('subject') or {}).get('id')} for e in ev])
print('events', len(E), E.t.min(), E.t.max())
note, actid = {}, {}
for t in ('MODERATE_EVIDENCE_ITEM', 'REJECT_REVISIONS'):
    for a in json.load(open(os.path.join(B, '..', 'A6', 'cache', f'act_{t}.json'), encoding='utf-8')):
        n = (a.get('note') or '').strip()
        for x in a['events']: note[x['id']] = n; actid[x['id']] = a['id']
E['note_len'] = E.eid.map(lambda i: len(note.get(i, ''))); E['act_id'] = E.eid.map(actid)
# note templating: identical text used >= 20 times across all notes
vc = pd.Series([v for v in note.values() if v]).value_counts(); templ = set(vc[vc >= 20].index)
E['note_templ'] = E.eid.map(lambda i: note.get(i, '') in templ)
Eh = E[~E.u.isin(BOT)].copy()

# ---- evidence items: submission, first terminal decision
ei = Eh[Eh.st == 'EvidenceItem']
sub = ei[ei.act == 'SUBMITTED'].sort_values('t').drop_duplicates('sid').set_index('sid')
dec = ei[ei.act.isin(['ACCEPTED', 'REJECTED'])].sort_values('t')
# a decision event (all, not only first): label self vs other
dec = dec.assign(sub_u=dec.sid.map(sub.u), sub_t=dec.sid.map(sub.t))
dec['self'] = dec.u == dec.sub_u
dec['kind'] = np.where(dec.act == 'ACCEPTED', 'acc', np.where(dec.self, 'wd', 'rej'))
dec['ttd'] = (dec.t - dec.sub_t).dt.total_seconds() / 86400
dec['type'] = 'EID'
# comment before decision (pre-enforcement reason proxy) for EID rejections
cm = Eh[(Eh.act == 'COMMENTED') & (Eh.st == 'EvidenceItem')][['sid', 't', 'u']]
cmg = {k: g for k, g in cm.groupby('sid')}
def cbefore(r, by_same=True):
    g = cmg.get(r.sid)
    if g is None: return False
    m = (g.t <= r.t + pd.Timedelta(minutes=1)) & (g.t >= r.t - pd.Timedelta(days=30))
    if by_same: m &= g.u == r.u
    return bool(m.any())
dec['cm_before'] = [cbefore(r) for r in dec.itertuples()]

# ---- revisions
rv = Eh[Eh.ot == 'Revision']
rsug = rv[rv.act == 'REVISION_SUGGESTED'].sort_values('t').drop_duplicates('oid').set_index('oid')
rdec = rv[rv.act.isin(['REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED'])].sort_values('t').drop_duplicates('oid').copy()
rdec['sub_u'] = rdec.oid.map(rsug.u); rdec['sub_t'] = rdec.oid.map(rsug.t)
rdec['self'] = rdec.u == rdec.sub_u
rdec['kind'] = np.select([rdec.act == 'REVISION_ACCEPTED', rdec.act == 'REVISION_SUPERSEDED', rdec.self], ['acc', 'sup', 'wd'], 'rej')
rdec['ttd'] = (rdec.t - rdec.sub_t).dt.total_seconds() / 86400
rdec['type'] = 'REV'
rcm = Eh[(Eh.act == 'COMMENTED') & (Eh.st == 'Revision')][['sid', 't', 'u']]
rcmg = {k: g for k, g in rcm.groupby('sid')}
def rcbefore(r):
    g = rcmg.get(r.oid)
    if g is None: return False
    return bool(((g.u == r.u) & (g.t <= r.t + pd.Timedelta(minutes=1))).any())
rdec['cm_before'] = [rcbefore(r) for r in rdec.itertuples()]
rdec['subj_eid'] = rdec.st == 'EvidenceItem'

print('EID decisions', dec.kind.value_counts().to_dict())
print('REV decisions', rdec.kind.value_counts().to_dict())
# monthly enforcement check: share of rejections (other + self) with note >= 10 chars
for nm, d in (('EID', dec[dec.kind != 'acc']), ('REV', rdec[rdec.kind.isin(['rej', 'wd'])])):
    s = d.assign(m=d.t.dt.to_period('M')).groupby('m').apply(lambda g: pd.Series({'n': len(g), 'note10': (g.note_len >= 10).mean()}))
    print(nm, s.loc['2023-05':'2024-02'].to_string() if nm == 'REV' else s.loc['2024-10':'2025-07'].to_string())
# exact switch: first decision timestamp after which every rejection carries a note >= 10 chars
for nm, d in (('EID', dec[dec.kind != 'acc']), ('REV', rdec[rdec.kind.isin(['rej', 'wd'])])):
    d = d.sort_values('t'); bad = d[d.note_len < 10]
    print(nm, 'last rejection without note>=10:', bad.t.max(), '| next rejection:', d[d.t > bad.t.max()].t.min())

# ---- moderator-days: days on which a user decided (accept/reject) another user's EID or revision
mods = pd.concat([dec[~dec.self][['u', 't']], rdec[(~rdec.self) & rdec.kind.isin(['acc', 'rej'])][['u', 't']]])
mods['d'] = mods.t.dt.normalize()
md = mods.drop_duplicates(['u', 'd'])
pd.to_pickle({'dec': dec.drop(columns=['ot']), 'rdec': rdec, 'sub': sub[['t', 'u']].reset_index(), 'rsug': rsug[['t', 'u', 'st']].reset_index(),
              'md': md[['u', 'd']]}, os.path.join(B, 'objs.pkl'))
print('moderator-days', len(md))
