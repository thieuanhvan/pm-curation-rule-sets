# Shared loader: CIViC public event log (D5b/cache) + activity notes (A6/cache). Aggregates only downstream.
import os, json, glob, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(H, '..', '..')
BOT = {385}
def load():
    ev, seen = [], set()
    for f in sorted(glob.glob(os.path.join(ROOT, 'D5b', 'cache', 'ev_*.json'))):
        for e in json.load(open(f, encoding='utf-8')):
            if e['id'] in seen: continue
            seen.add(e['id']); ev.append(e)
    E = pd.DataFrame([{'eid': e['id'], 'act': e['action'], 't': pd.Timestamp(e['createdAt']).tz_localize(None),
                       'u': (e.get('originatingUser') or {}).get('id'), 'ot': (e.get('originatingObject') or {}).get('__typename'),
                       'oid': (e.get('originatingObject') or {}).get('id'), 'st': (e.get('subject') or {}).get('__typename'),
                       'sid': (e.get('subject') or {}).get('id')} for e in ev]).sort_values(['t', 'eid']).reset_index(drop=True)
    notes = {}
    for t in ('MODERATE_EVIDENCE_ITEM', 'REJECT_REVISIONS'):
        for a in json.load(open(os.path.join(ROOT, 'D5req', 'A6', 'cache', f'act_{t}.json'), encoding='utf-8')):
            for x in a['events']: notes[x['id']] = a.get('note')
    return E, notes
