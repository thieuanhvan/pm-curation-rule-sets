# W3 prep: per-event table for CIViC (all entities), actor classes, moderator-at-time, revision/comment/flag object ids.
# Reuses ../../D5b/cache (no API calls). User ids pseudonymised (salted SHA-256 as D5k4/A2) before writing.
import json, glob, hashlib, pickle, os, numpy as np, pandas as pd
B = '../../D5b/'; BOT = 385
ps = lambda u: None if u is None else 'u_' + hashlib.sha256(f'<salt>civic:{u}'.encode()).hexdigest()[:10]
ev = {}
for f in glob.glob(B + 'cache/ev_*.json'):
    for e in json.load(open(f, encoding='utf-8')): ev[e['id']] = e
ev = sorted(ev.values(), key=lambda e: (e['createdAt'], e['id']))
day = lambda s: pd.Timestamp(s).value / 864e11
rows = []
for e in ev:
    s, oo = e.get('subject') or {}, e.get('originatingObject') or {}
    rows.append(dict(eid=e['id'], act=e['action'], t=day(e['createdAt']), u=(e.get('originatingUser') or {}).get('id'),
                     org=(e.get('organization') or {}).get('id'), st=s.get('__typename'), sid=s.get('id'), ot=oo.get('__typename'), oid=oo.get('id')))
E = pd.DataFrame(rows)
E['bot'] = E.u == BOT
# revision / flag / comment -> target entity
tgt = {}
for r in E.itertuples():
    if r.ot in ('Revision', 'Flag', 'Comment') and r.oid is not None and r.st is not None and r.st != 'Revision':
        tgt[(r.ot, r.oid)] = (r.st, r.sid)
# comments on a revision -> the revised entity
E['tt'] = E.st; E['tid'] = E.sid
m = E.st == 'Revision'
E.loc[m, 'tt'] = [tgt.get(('Revision', i), (None, None))[0] for i in E.loc[m, 'sid']]
E.loc[m, 'tid'] = [tgt.get(('Revision', i), (None, None))[1] for i in E.loc[m, 'sid']]
E.loc[m, 'act'] = E.loc[m, 'act'].replace({'COMMENTED': 'REVISION_COMMENTED'})
# owners: evidence submitter, assertion submitter, revision suggester, flag raiser
sub_u = E[(E.act == 'SUBMITTED') & (E.st == 'EvidenceItem')].drop_duplicates('sid').set_index('sid').u.to_dict()
asub_u = E[(E.act == 'ASSERTION_SUBMITTED')].drop_duplicates('sid').set_index('sid').u.to_dict()
rev_u = E[(E.act == 'REVISION_SUGGESTED') & (E.ot == 'Revision')].drop_duplicates('oid').set_index('oid').u.to_dict()
# moderator-at-time: first moderation of someone else's content (non-bot)
mod_t = {}
def mark(u, t):
    if u is None or u == BOT: return
    if u not in mod_t or t < mod_t[u]: mod_t[u] = t
for r in E.itertuples():
    if r.act in ('ACCEPTED', 'REJECTED') and r.st == 'EvidenceItem' and sub_u.get(r.sid) not in (None, r.u): mark(r.u, r.t)
    elif r.act in ('ASSERTION_ACCEPTED', 'ASSERTION_REJECTED') and asub_u.get(r.sid) not in (None, r.u): mark(r.u, r.t)
    elif r.act in ('REVISION_ACCEPTED', 'REVISION_REJECTED') and r.ot == 'Revision':
        sg = rev_u.get(r.oid); own = sub_u.get(r.sid) if r.st == 'EvidenceItem' else None
        if sg not in (None, r.u) and own != r.u: mark(r.u, r.t)
E['modAt'] = [(u in mod_t and t >= mod_t[u] - 1e-9) for u, t in zip(E.u, E.t)]
E['modEver'] = E.u.isin(set(mod_t))
users = {u['id']: u for u in json.load(open(B + 'meta_users.json'))}
E['roleNow'] = E.u.map(lambda u: users.get(u, {}).get('role', 'UNKNOWN'))
E['evSub'] = [sub_u.get(i) if tt == 'EvidenceItem' else None for tt, i in zip(E.tt, E.tid)]
E['isSubmitter'] = (E.u == E.evSub) & E.u.notna()
E['revSugg'] = [rev_u.get(o) if ot == 'Revision' else None for ot, o in zip(E.ot, E.oid)]
print('events', len(E), 'moderators (ever)', len(mod_t), 'roleNow of moderators', pd.Series([users.get(u, {}).get('role') for u in mod_t]).value_counts().to_dict())
# pseudonymise
for c in ('u', 'evSub', 'revSugg'): E[c] = E[c].map(lambda x: ps(int(x)) if x is not None and x == x else None)
E.to_pickle('w3_events.pkl')
pickle.dump({'n_mod': len(mod_t)}, open('w3_meta.pkl', 'wb'))
