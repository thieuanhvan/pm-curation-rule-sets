# W2 step 2: build OCEL 2.0 (objects: ticket, comment, commit, pr, user, label) and flattened per-ticket XES/CSV case logs
# for the GO / HPO 500-ticket samples (tl_w2_*.jsonl + outcomes_w2_*.json from classify_w2.mjs).
# Pseudonyms: user = HMAC-SHA256(secret key, first-stage salted pseudonym), ticket/PR/commit ids likewise; the key is read from
# env D5_HMAC_KEY or $P17_HMAC_KEY_FILE and never written anywhere. Without a key: salted SHA-256 fallback, flagged.
# Publishable outputs (out/*.jsonocel, *.sqlite, *.xes, *_caselog.csv) carry no comment text, no ticket numbers, no logins.
# internal/ keeps the analysis table with ticket numbers (NOT for publication).
import json, os, hmac, hashlib, pickle, sys
import pandas as pd, pm4py
from pm4py.objects.ocel.obj import OCEL
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs('out', exist_ok=True); os.makedirs('internal', exist_ok=True)
REPO = {'go': 'geneontology/go-ontology', 'hpo': 'obophenotype/human-phenotype-ontology'}
INSIDER = {'OWNER', 'MEMBER', 'COLLABORATOR'}

key = os.environ.get('D5_HMAC_KEY'); KEYSRC = 'env'
if not key and os.path.exists(__import__('os').environ.get('P17_HMAC_KEY_FILE', '')):
    key = open(__import__('os').environ.get('P17_HMAC_KEY_FILE', ''), encoding='utf-8').read().strip(); KEYSRC = 'file'
if key:
    H = lambda pfx, s: None if s is None else pfx + hmac.new(key.encode(), f'd5w2|{s}'.encode(), hashlib.sha256).hexdigest()[:12]
else:
    KEYSRC = 'FALLBACK_salted_sha256 (NOT publishable)'
    H = lambda pfx, s: None if s is None else pfx + hashlib.sha256(f'd5w2-fallback|{s}'.encode()).hexdigest()[:12]
print('pseudonym key source:', KEYSRC)

SAMPLE_N = {t: set(json.load(open(f'sample_w2_{t}.json', encoding='utf-8'))['n']) for t in ('go', 'hpo')}  # 07/10: N cut 500 -> 300 (first 300 of the seeded draw order)

def load(tag):
    tl = {}
    for l in open(f'tl_w2_{tag}.jsonl', encoding='utf-8'):
        if l.strip():
            try:
                r = json.loads(l)
                if r['n'] in SAMPLE_N[tag]: tl[r['n']] = r
            except Exception: pass
    oc = {r['n']: r for r in json.load(open(f'outcomes_w2_{tag}.json', encoding='utf-8'))}
    return tl, oc

E, R, O, CASE, TAB = [], [], {}, [], []
def obj(oid, typ, **a):
    if oid not in O: O[oid] = {'ocel:oid': oid, 'ocel:type': typ, **a}
eidc = [0]
def ev(act, ts, rels, case_act=None, case=None, res=None, **attrs):
    if not ts: return
    eidc[0] += 1; eid = f'e{eidc[0]}'; ts = pd.Timestamp(ts)
    E.append({'ocel:eid': eid, 'ocel:activity': act, 'ocel:timestamp': ts, **attrs})
    for oid, typ, q in rels:
        if oid: R.append({'ocel:eid': eid, 'ocel:oid': oid, 'ocel:type': typ, 'ocel:activity': act, 'ocel:timestamp': ts, 'ocel:qualifier': q})
    if case_act: CASE.append({'case:concept:name': case, 'concept:name': case_act, 'time:timestamp': ts, 'org:resource': res, 'ocel_activity': act, **{k: v for k, v in attrs.items() if k in ('state_reason', 'is_bot', 'same_repo')}})

for tag in ('go', 'hpo'):
    tl, oc = load(tag)
    for n, t in sorted(tl.items()):
        o = oc.get(n)
        if not o or t.get('gone'): continue
        tid = H('t_', f'{tag}#{n}'); sub = t['sub']; subp = H('p_', sub); insider = t.get('aa') in INSIDER
        cls = o.get('cls'); final_state = t['s']
        obj(tid, 'ticket', repo=tag, submitter_insider=insider, final_state=final_state, outcome=cls or 'PENDING', opened_year=int(t['c'][:4]))
        obj(subp, 'user')
        TAB.append({'tag': tag, 'n': n, 'tid': tid, 'open': t['c'], 'state': final_state, 'insider': insider, 'aa': t.get('aa'), 'cls': cls,
                    'tier': o.get('tier'), 'close': o.get('close'), 'closer': H('p_', o.get('closer')), 'closerBot': o.get('closerBot'), 'sub': subp,
                    'firstAssignee': H('p_', o.get('firstAssignee')), 'corroborated': o.get('corroborated'), 'u': o.get('u'), 'uAlive365': o.get('uAlive365'),
                    'closeSR': o.get('closeSR'), 'closedByCommit': o.get('closedByCommit'), 'src': t.get('src')})
        ev('OPENED', t['c'], [(tid, 'ticket', 'ticket'), (subp, 'user', 'actor')], 'OPENED', tid, subp, repo=tag)
        evs = t['events']; closes = [i for i, e in enumerate(evs) if e['ev'] == 'closed']; last = closes[-1] if (closes and final_state == 'closed') else None
        seen_pr_merge = set(); t0 = pd.Timestamp(t['c'])
        for i, e in enumerate(evs):
            k = e['ev']; ts = e.get('t'); a = H('p_', e.get('actor')); bot = bool(e.get('bot'))
            if a: obj(a, 'user')
            base = [(tid, 'ticket', 'ticket'), (a, 'user', 'actor')]
            if k == 'labeled':
                lab = 'label:' + e.get('label', '?'); obj(lab, 'label', name=e.get('label'))
                at_open = ts is not None and (pd.Timestamp(ts) - t0).total_seconds() <= 120
                ev('LABELED', ts, base + [(lab, 'label', 'label')], None if at_open else 'LABELED', tid, a, at_open=at_open, is_bot=bot)
            elif k == 'unlabeled':
                lab = 'label:' + e.get('label', '?'); obj(lab, 'label', name=e.get('label')); ev('UNLABELED', ts, base + [(lab, 'label', 'label')], is_bot=bot)
            elif k == 'assigned':
                asg = H('p_', e.get('assignee')) if e.get('assignee') else None
                if asg: obj(asg, 'user')
                ev('ASSIGNED', ts, base + ([(asg, 'user', 'assignee')] if asg else []), 'ASSIGNED', tid, a, is_bot=bot, assignee_known=bool(asg), self_assign=bool(asg and asg == a))
            elif k == 'unassigned': ev('UNASSIGNED', ts, base, is_bot=bot)
            elif k == 'commented':
                cid = H('c_', f"{tag}#{n}#{e.get('cid') or i}"); obj(cid, 'comment', length=len(e.get('body') or ''), author_assoc=e.get('aa'))
                act = 'COMMENT_BOT' if bot else ('COMMENT_SUBMITTER' if e.get('actor') == sub else 'COMMENT_OTHER')
                ev(act, ts, base + [(cid, 'comment', 'comment')], act, tid, a, is_bot=bot)
            elif k == 'referenced' and e.get('commit'):
                cm = H('k_', 'commit:' + e['commit']); same = (e.get('crepo') == REPO[tag]) if e.get('crepo') else None
                obj(cm, 'commit', same_repo=same)
                ev('COMMIT_REF', ts, base + [(cm, 'commit', 'commit')], 'COMMIT_REF', tid, a, same_repo=same, is_bot=bot)
            elif k == 'cross-referenced':
                s = e.get('src') or {}
                if s.get('pr'):
                    pr = H('r_', f"pr:{s.get('repo')}#{s.get('n')}"); obj(pr, 'pr', same_repo=s.get('repo') == REPO[tag], merged=bool(s.get('merged')))
                    ev('PR_LINKED', ts, base + [(pr, 'pr', 'pr')], 'PR_LINKED', tid, a, same_repo=s.get('repo') == REPO[tag], is_bot=bot)
                    if s.get('merged') and pr not in seen_pr_merge:
                        seen_pr_merge.add(pr); ev('PR_MERGED', s['merged'], [(tid, 'ticket', 'ticket'), (pr, 'pr', 'pr')], 'PR_MERGED', tid, None, same_repo=s.get('repo') == REPO[tag])
                else:
                    ev('CROSS_REF', ts, base, 'CROSS_REF', tid, a, same_repo=s.get('repo') == REPO[tag], is_bot=bot)
            elif k == 'connected': ev('PR_LINKED', ts, base, 'PR_LINKED', tid, a, is_bot=bot)
            elif k == 'renamed': ev('RENAMED', ts, base, 'RENAMED', tid, a, is_bot=bot)
            elif k == 'marked_as_duplicate': ev('MARKED_DUPLICATE', ts, base, 'MARKED_DUPLICATE', tid, a, is_bot=bot)
            elif k == 'reopened': ev('REOPENED', ts, base, 'REOPENED', tid, a, is_bot=bot)
            elif k == 'closed':
                fin = i == last; ca = f'CLOSED_{cls}' if fin else 'CLOSED_INTERIM'
                rels = base + ([(H('k_', 'commit:' + e['commit']), 'commit', 'closing_commit')] if e.get('commit') else [])
                if e.get('commit'): obj(H('k_', 'commit:' + e['commit']), 'commit', same_repo=None)
                ev('CLOSED', ts, rels, ca, tid, a, state_reason=e.get('sr') or (t.get('sr') if fin else None), final=fin, outcome=cls if fin else None, by_commit=bool(e.get('commit')), is_bot=bot)

events = pd.DataFrame(E); relations = pd.DataFrame(R).drop_duplicates(['ocel:eid', 'ocel:oid', 'ocel:qualifier']); objects = pd.DataFrame(list(O.values()))
for c in events.columns:
    if c not in ('ocel:eid', 'ocel:activity', 'ocel:timestamp'): events[c] = events[c].astype(object)
for c in objects.columns:
    if c not in ('ocel:oid', 'ocel:type'): objects[c] = objects[c].astype(object)
events['ocel:timestamp'] = pd.to_datetime(events['ocel:timestamp'], utc=True); relations['ocel:timestamp'] = pd.to_datetime(relations['ocel:timestamp'], utc=True)
ocel = OCEL(events=events, objects=objects, relations=relations)
pickle.dump({'events': events, 'objects': objects, 'relations': relations}, open('internal/ocel_w2.pkl', 'wb'))
try:
    pm4py.write_ocel2_json(ocel, 'out/gohpo_ocel2.jsonocel')
except Exception as ex: print('ocel2 json failed:', ex)
try:
    if os.path.exists('out/gohpo_ocel2.sqlite'): os.remove('out/gohpo_ocel2.sqlite')
    pm4py.write_ocel2_sqlite(ocel, 'out/gohpo_ocel2.sqlite')
except Exception as ex: print('ocel2 sqlite failed:', ex)

cl = pd.DataFrame(CASE); cl['time:timestamp'] = pd.to_datetime(cl['time:timestamp'], utc=True)
cl['ord'] = cl['concept:name'].map(lambda a: 0 if a == 'OPENED' else (2 if a.startswith('CLOSED_') and a != 'CLOSED_INTERIM' else 1))
cl = cl.sort_values(['case:concept:name', 'time:timestamp', 'ord']).drop(columns='ord').reset_index(drop=True)
tab = pd.DataFrame(TAB); tab.to_pickle('internal/tickets_w2.pkl')
cl['repo'] = cl['case:concept:name'].map(tab.set_index('tid')['tag'])
cl.to_pickle('internal/caselog_w2.pkl')
for tag in ('go', 'hpo'):
    x = cl[cl['repo'] == tag].drop(columns=['repo']).copy()
    x.to_csv(f'out/{tag}_w2_caselog.csv', index=False)
    for c in x.columns:
        if c not in ('case:concept:name', 'concept:name', 'time:timestamp'): x[c] = x[c].astype(str)
    lx = pm4py.convert_to_event_log(pm4py.format_dataframe(x, case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp'))
    pm4py.write_xes(lx, f'out/{tag}_w2_caselog.xes')
summary = {'key_source': KEYSRC, 'ocel_events': len(events), 'ocel_objects': objects['ocel:type'].value_counts().to_dict(), 'ocel_relations': len(relations),
           'case_events': len(cl), 'cases': {t: int(tab[tab.tag == t].shape[0]) for t in ('go', 'hpo')},
           'activities': cl.groupby('repo')['concept:name'].value_counts().unstack(0).fillna(0).astype(int).to_dict()}
json.dump(summary, open('out/build_summary.json', 'w'), indent=1, default=str); print(json.dumps(summary, default=str)[:2500])
