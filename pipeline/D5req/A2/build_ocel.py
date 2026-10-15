# A2 step 1: build OCEL 2.0 (full + evidence-item scope) and flattened per-evidence-item case log from the cached CIViC event log.
# Users pseudonymised with salted SHA-256 (salt as in D5k4); bot account 385 kept but tagged (is_bot) and excluded from the main case log.
import json, os, hashlib, pickle, collections as C
import pandas as pd, pm4py
from pm4py.objects.ocel.obj import OCEL

B = '../../D5b/'; OUT = 'out/'; os.makedirs(OUT, exist_ok=True)
SALT = __import__("os").environ["P17_SALT"]; BOT = 385
ps = lambda uid: None if uid is None else 'u_' + hashlib.sha256(f'{SALT}civic:{uid}'.encode()).hexdigest()[:10]

ev = {}
for f in sorted(os.listdir(B + 'cache')):
    for e in json.load(open(B + 'cache/' + f, encoding='utf-8')): ev[e['id']] = e
ev = sorted(ev.values(), key=lambda e: (e['createdAt'], e['id']))
users = {u['id']: u for u in json.load(open(B + 'meta_users.json', encoding='utf-8'))}
meta = {m['id']: m for m in json.load(open(B + 'meta_evidence.json', encoding='utf-8'))}

OT = {'EvidenceItem': 'evidence_item', 'Revision': 'revision', 'Flag': 'flag', 'Comment': 'comment', 'Assertion': 'assertion',
      'GeneVariant': 'variant', 'FusionVariant': 'variant', 'FactorVariant': 'variant', 'MolecularProfile': 'molecular_profile',
      'Feature': 'feature', 'Source': 'source', 'SourceSuggestion': 'source_suggestion', 'VariantGroup': 'variant_group',
      'VariantCoordinate': 'coordinate', 'ExonCoordinate': 'coordinate'}
oid = lambda tn, i: f'{OT[tn]}:{i}'

# revision -> subject entity (from REVISION_* events); flag/comment -> subject entity
rev_target, objtarget = {}, {}
for e in ev:
    oo, s = e.get('originatingObject') or {}, e.get('subject') or {}
    if oo.get('__typename') in ('Revision', 'Flag', 'Comment') and oo.get('id') is not None and s.get('id') is not None:
        if oo['__typename'] == 'Revision' and s['__typename'] != 'Revision': rev_target[oo['id']] = (s['__typename'], s['id'])
        objtarget[(oo['__typename'], oo['id'])] = (s['__typename'], s['id'])

E, R, O = [], [], {}
def addobj(o, t, **a):
    if o not in O: O[o] = dict({'ocel:oid': o, 'ocel:type': t}, **a)
for e in ev:
    eid = f"e{e['id']}"; act = e['action']; ts = pd.Timestamp(e['createdAt'])
    uid = (e.get('originatingUser') or {}).get('id'); org = (e.get('organization') or {}).get('id')
    s, oo = e.get('subject') or {}, e.get('originatingObject') or {}
    E.append({'ocel:eid': eid, 'ocel:activity': act, 'ocel:timestamp': ts, 'is_bot': uid == BOT, 'src_id': e['id']})
    rel = []
    if s.get('__typename') in OT and s.get('id') is not None:
        rel.append((oid(s['__typename'], s['id']), OT[s['__typename']], 'subject'))
        if s['__typename'] == 'Revision' and s['id'] in rev_target:   # comment on a revision: also link the revised entity
            tn, ti = rev_target[s['id']]
            if tn in OT: rel.append((oid(tn, ti), OT[tn], 'revised_entity'))
    if oo.get('__typename') in OT and oo.get('id') is not None and oo.get('__typename') != s.get('__typename'):
        rel.append((oid(oo['__typename'], oo['id']), OT[oo['__typename']], 'originating_object'))
    if uid is not None:
        u = ps(uid); rel.append((u, 'user', 'actor'))
        addobj(u, 'user', role_now=users.get(uid, {}).get('role', 'UNKNOWN'), is_bot=uid == BOT)
    if org is not None:
        rel.append((f'org:{org}', 'organisation', 'organisation')); addobj(f'org:{org}', 'organisation')
    for o, t, q in rel:
        if t == 'evidence_item':
            m = meta.get(int(o.split(':')[1]), {})
            addobj(o, t, status_now=m.get('status'), evidence_level=m.get('evidenceLevel'), evidence_type=m.get('evidenceType'))
        else: addobj(o, t)
        R.append({'ocel:eid': eid, 'ocel:oid': o, 'ocel:type': t, 'ocel:activity': act, 'ocel:timestamp': ts, 'ocel:qualifier': q})

events = pd.DataFrame(E); relations = pd.DataFrame(R).drop_duplicates(['ocel:eid', 'ocel:oid'])
objects = pd.DataFrame(list(O.values()))
for c in objects.columns:
    if c not in ('ocel:oid', 'ocel:type'): objects[c] = objects[c].astype(object)
print('events', len(events), 'objects', len(objects), 'relations', len(relations))
print(objects['ocel:type'].value_counts().to_dict())
ocel = OCEL(events=events, objects=objects, relations=relations)
pickle.dump({'events': events, 'objects': objects, 'relations': relations}, open(OUT + 'ocel_full.pkl', 'wb'))
pm4py.write_ocel2_sqlite(ocel, OUT + 'civic_ocel2_full.sqlite')

# evidence-item scope: events related to an evidence_item object (subject or revised_entity); keep all their objects
ei_eids = set(relations.loc[relations['ocel:type'] == 'evidence_item', 'ocel:eid'])
ev_ei = events[events['ocel:eid'].isin(ei_eids)]; rel_ei = relations[relations['ocel:eid'].isin(ei_eids)]
ob_ei = objects[objects['ocel:oid'].isin(set(rel_ei['ocel:oid']))]
ocel_ei = OCEL(events=ev_ei.copy(), objects=ob_ei.copy(), relations=rel_ei.copy())
print('EI scope events', len(ev_ei), 'objects', len(ob_ei), 'relations', len(rel_ei))
pm4py.write_ocel2_json(ocel_ei, OUT + 'civic_ocel2_evidence.jsonocel')
pm4py.write_ocel2_sqlite(ocel_ei, OUT + 'civic_ocel2_evidence.sqlite')
pickle.dump({'events': ev_ei, 'objects': ob_ei, 'relations': rel_ei}, open(OUT + 'ocel_ei.pkl', 'wb'))

# flattened case log per evidence item; revision comments renamed REVISION_COMMENTED; keep object ids as attributes
r = rel_ei
ei_of = r[r['ocel:type'] == 'evidence_item'][['ocel:eid', 'ocel:oid']].rename(columns={'ocel:oid': 'case:concept:name'})
aux = {}
for t in ('revision', 'flag', 'comment', 'user', 'organisation'):
    aux[t] = r[r['ocel:type'] == t].drop_duplicates('ocel:eid').set_index('ocel:eid')['ocel:oid']
cl = ev_ei.merge(ei_of, on='ocel:eid')
subj = r[r['ocel:qualifier'] == 'subject'].set_index('ocel:eid')['ocel:type']
cl['act'] = cl['ocel:activity']
cl.loc[(cl['ocel:activity'] == 'COMMENTED') & (cl['ocel:eid'].map(subj) == 'revision'), 'act'] = 'REVISION_COMMENTED'
for t in aux: cl[t] = cl['ocel:eid'].map(aux[t])
cl['role_now'] = cl['user'].map(objects.set_index('ocel:oid')['role_now'])
cl = cl.rename(columns={'act': 'concept:name', 'ocel:timestamp': 'time:timestamp', 'user': 'org:resource'})
cl = cl.sort_values(['case:concept:name', 'time:timestamp', 'src_id']).reset_index(drop=True)
cl['time:timestamp'] = pd.to_datetime(cl['time:timestamp'], utc=True)
cl.to_pickle(OUT + 'caselog_ei_incl.pkl')
cx = cl[~cl['is_bot']].copy(); cx.to_pickle(OUT + 'caselog_ei_excl.pkl')
print('caselog incl', len(cl), 'cases', cl['case:concept:name'].nunique(), '| excl', len(cx), cx['case:concept:name'].nunique())
print(cx['concept:name'].value_counts().to_dict())
keep = ['case:concept:name', 'concept:name', 'time:timestamp', 'org:resource', 'role_now', 'revision', 'flag', 'comment', 'organisation', 'src_id']
lx = pm4py.convert_to_event_log(pm4py.format_dataframe(cx[keep].astype({'revision': str, 'flag': str, 'comment': str, 'organisation': str, 'org:resource': str}), case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp'))
pm4py.write_xes(lx, OUT + 'civic_evidence_caselog_excl_bot.xes')
print('done')
