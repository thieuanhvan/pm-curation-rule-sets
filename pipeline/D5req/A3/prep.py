# A3 prep: build CIViC evidence-item table + per-item event times + per-user activity days.
# Reuses ../../D5b/cache (no API calls). Bot account 385 excluded (as in D5sim 'excl').
# User ids are pseudonymised (salted SHA-256, salt as in D5k4 + 'civic:' prefix) before anything is written.
import json, os, glob, hashlib, pickle
import numpy as np, pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, '..', '..', 'D5b')
NOW = pd.Timestamp('2026-10-07T00:00:00Z').value / 864e11  # days since epoch
BOT = {385}
ps = lambda u: None if u is None else 'u_' + hashlib.sha256(('<salt>civic:' + str(u)).encode()).hexdigest()[:10]

ev, seen = [], set()
for f in sorted(glob.glob(os.path.join(SRC, 'cache', 'ev_*.json'))):
    for e in json.load(open(f, encoding='utf-8')):
        if e['id'] in seen: continue
        seen.add(e['id']); ev.append(e)
ev = [e for e in ev if (e.get('originatingUser') or {}).get('id') not in BOT]
ev.sort(key=lambda e: (e['createdAt'], e['id']))
day = lambda s: pd.Timestamp(s).value / 864e11
users = {u['id']: u for u in json.load(open(os.path.join(SRC, 'meta_users.json')))}
meta = {m['id']: m for m in json.load(open(os.path.join(SRC, 'meta_evidence.json')))}

rev2subj = {}
for e in ev:
    oo, s = e.get('originatingObject') or {}, e.get('subject') or {}
    if oo.get('__typename') == 'Revision' and s.get('id') is not None and s.get('__typename') != 'Revision':
        rev2subj[oo.get('id')] = s
items = {}
user_days = {}
for e in ev:
    uid = (e.get('originatingUser') or {}).get('id')
    t = day(e['createdAt'])
    if uid is not None: user_days.setdefault(uid, []).append(t)
    s = e.get('subject') or {}
    eid = None; act = e['action']
    if s.get('__typename') == 'EvidenceItem': eid = s['id']
    elif s.get('__typename') == 'Revision':
        tt = rev2subj.get(s['id'])
        if tt and tt.get('__typename') == 'EvidenceItem': eid = tt['id']; act = 'REVISION_COMMENTED'
    if eid is None: continue
    it = items.setdefault(eid, {'id': eid, 'ev': []})
    it['ev'].append((t, act, uid, (e.get('organization') or {}).get('id')))

rows = []
for eid, it in items.items():
    es = it['ev']
    sub = next((x for x in es if x[1] == 'SUBMITTED'), None)
    if sub is None: continue
    dec = next((x for x in es if x[1] in ('ACCEPTED', 'REJECTED')), None)
    m = meta.get(eid, {})
    r = dict(id=eid, arr=sub[0], subU=sub[2], subOrg=sub[3], subRoleNow=users.get(sub[2], {}).get('role', 'UNKNOWN'),
             level=m.get('evidenceLevel'), rating=m.get('evidenceRating'), etype=m.get('evidenceType'),
             flaggedNow=m.get('flagged'), statusNow=m.get('status'))
    if dec:
        t = max(dec[0], sub[0])
        out = 'ACC' if dec[1] == 'ACCEPTED' else ('WDR' if dec[2] == sub[2] else 'REJ')
        r.update(dec=t, out=out, decU=dec[2], decOrg=dec[3], decRoleNow=users.get(dec[2], {}).get('role', 'UNKNOWN'))
    else:
        r.update(dec=np.nan, out='PEND', decU=None, decOrg=None, decRoleNow=None)
    # activity times other than SUBMITTED itself (any actor except bot, already removed)
    r['act_t'] = sorted(x[0] for x in es if x[1] != 'SUBMITTED' and x[1] not in ('ACCEPTED', 'REJECTED'))
    r['rev_t'] = sorted(x[0] for x in es if x[1] == 'REVISION_SUGGESTED')
    r['com_t'] = sorted(x[0] for x in es if x[1] in ('COMMENTED', 'REVISION_COMMENTED'))
    r['flag_t'] = sorted(x[0] for x in es if x[1] == 'FLAGGED')
    r['nonsub_act_t'] = sorted(x[0] for x in es if x[1] not in ('SUBMITTED', 'ACCEPTED', 'REJECTED') and x[2] != sub[2])
    rows.append(r)
df = pd.DataFrame(rows).sort_values(['arr', 'id']).reset_index(drop=True)
# submitter features (computed on raw ids, then pseudonymised)
df['subDay'] = np.floor(df.arr).astype(int)
vol = df.groupby('subU').size(); df['subVol'] = df.subU.map(vol)
df['subRank'] = df.groupby('subU').cumcount() + 1          # 1 = submitter's first evidence item
burst = df.groupby(['subU', 'subDay']).size(); df['burstN'] = [burst[(u, d)] for u, d in zip(df.subU, df.subDay)]
firstAny = {u: min(v) for u, v in user_days.items()}
df['subTenureD'] = [r.arr - firstAny.get(r.subU, r.arr) for r in df.itertuples()]
udays = {ps(u): np.array(sorted(v)) for u, v in user_days.items()}
for c in ('subU', 'decU'): df[c] = df[c].map(lambda u: ps(int(u)) if u is not None and u == u else None)
df['NOW'] = NOW
pickle.dump({'items': df, 'udays': udays, 'NOW': NOW}, open(os.path.join(BASE, 'civic_items.pkl'), 'wb'))
print(len(ev), 'events kept;', len(df), 'items;', df.out.value_counts().to_dict())
print('submitters', df.subU.nunique(), 'vol>=100:', (vol >= 100).sum())
