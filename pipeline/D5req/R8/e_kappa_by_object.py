# R8: second-coding presence agreement (Cohen's kappa) per object type, from R7 res_t1b_agreement.json units
import json, os
H = os.path.dirname(os.path.abspath(__file__))
U = json.load(open(os.path.join(H, '..', 'R7', 'res_t1b_agreement.json'), encoding='utf-8'))['units']
MAP = {'rejected EI re-opened on revision suggestion/acceptance (v1)': 'evidence item', 'fit: approval refused if assertion flagged/not accepted': 'assertion',
       'COI for revision/flag/source-suggestion moderation': 'cross-cutting or other', 'COI for EI/assertion moderation': 'evidence item',
       'reason to reject EI/assertion': 'evidence item', 'source suggestion auto-curated on EI submission (v1)': 'cross-cutting or other'}
def obj(n):
    if n in MAP: return MAP[n]
    n = n.lower()
    if 'flag' in n: return 'flag'
    if 'assertion' in n or 'approval' in n: return 'assertion'
    if 'revision' in n or 'supersed' in n or 'stale' in n: return 'revision'
    if ' ei' in n or n.endswith('ei') or 'withdrawal' in n or 'rejected ei' in n or 'account to submit' in n: return 'evidence item'
    return 'cross-cutting or other'
def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n; pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 2), round(po, 3), n
res = {}
groups = {}
for u in U:
    groups.setdefault(obj(u['unit']), []).append(u)
for g, us in groups.items():
    a = sum((u['pres_R6'] for u in us), []); b = sum((u['pres_coder2'] for u in us), [])
    k, po, n = kappa(a, b); res[g] = {'units': len(us), 'cells': n, 'agreement': po, 'kappa': k, 'unit_names': [u['unit'] for u in us]}
json.dump(res, open(os.path.join(H, 'res_e_kappa_by_object.json'), 'w', encoding='utf-8'), indent=1)
for g, r in res.items(): print(g, r['units'], r['cells'], r['agreement'], r['kappa'], r['unit_names'])
