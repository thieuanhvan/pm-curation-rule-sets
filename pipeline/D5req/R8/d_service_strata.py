# R8 analysis D1: service position (Definition 5) stratified by
#   (a) same- vs cross-organisation decision (decider's acting organisation == submitter's organisation at submission)
#   (b) core vs community submitter: core = submitter who also made >= 1 decision on another user's evidence item
#       (accept/reject) anywhere in the log (band-level group; counts of people not reported).
# Scored decisions: first decisions since 2021 on queues of items <= h old, h in {365, inf}; queue S_i is the full pending
# set (all strata), only the scored decision is stratified. Null: j uniform from S_i (2,000 draws); cluster bootstrap over
# organisation x decision day as in R6 t3_u_def5.py. Aggregates only.
import os, sys, json, pickle, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); R0 = os.path.join(H, '..')
sys.path.insert(0, os.path.join(R0, 'R7'))
from t_common import load, BOT
rng = np.random.default_rng(20261008); NS = 2000; B = 2000
T21 = pd.Timestamp('2021-01-01').value / 864e11
d = pickle.load(open(os.path.join(R0, 'A3', 'civic_items.pkl'), 'rb')); it = d['items'].reset_index(drop=True)
E, _ = load()
sub = E[(E.act == "SUBMITTED") & (E.st == "EvidenceItem")].dropna(subset=["sid"]).drop_duplicates("sid").assign(sid=lambda d: d.sid.astype(int)).set_index("sid").u
dec_ev = E[(E.st == 'EvidenceItem') & E.act.isin(['ACCEPTED', 'REJECTED'])].copy()
dec_ev['subm'] = dec_ev.sid.map(sub)
deciders = set(dec_ev[(dec_ev.u != dec_ev.subm) & ~dec_ev.u.isin(BOT)].u.dropna())
it['subm'] = it.id.astype(int).map(sub)
it['core'] = it.subm.isin(deciders)
it['same_org'] = (it.subOrg == it.decOrg) & it.subOrg.notna()
arr = it.arr.values.astype(float); dec = np.where(it.dec.isna(), np.inf, it.dec.values.astype(float))
cluster = np.array([f'{r.decOrg}|{int(r.dec) if r.dec == r.dec else -1}' for r in it.itertuples()])
cand = np.flatnonzero(np.isfinite(dec) & (dec >= T21))


def score(h):
    out = {}
    for i in cand:
        t = dec[i]
        if t - arr[i] > h: continue
        m = (arr < t) & (dec >= t) & (t - arr <= h); m[i] = True
        qa = np.sort(arr[m]); L = len(qa)
        if L < 2: continue
        def uval(a):
            r = np.searchsorted(qa, a, 'right'); l = np.searchsorted(qa, a, 'left')
            return (L - r + 0.5 * (r - l - 1)) / (L - 1)
        out[i] = (float(uval(arr[i])), uval(qa[rng.integers(0, L, NS)]))
    return out


def summ(sc, idx):
    idx = [i for i in idx if i in sc]
    if len(idx) < 20: return {'n_band': '<20', 'meanU': None}
    u = np.array([sc[i][0] for i in idx]); nl = np.array([sc[i][1] for i in idx]); cl = cluster[idx]
    uc, inv = np.unique(cl, return_inverse=True); sums = np.bincount(inv, u); cnt = np.bincount(inv)
    bs = []
    for _ in range(B):
        s = rng.integers(0, len(uc), len(uc)); bs.append(sums[s].sum() / cnt[s].sum())
    nm = nl.mean(0)
    return {'n_decisions': int(len(u)), 'meanU': [round(u.mean(), 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3)],
            'null_95': [round(np.percentile(nm, 2.5), 3), round(np.percentile(nm, 97.5), 3)], 'perm_p_one_sided': float((nm <= u.mean()).mean()),
            'newest10': round(float((u <= .1).mean()), 3)}


res = {'core_definition': 'submitter with >=1 decision on another user\'s evidence item in the log',
       'share_items_core_submitter_band': None}
share_core = float(it.core.mean())
res['share_items_core_submitter_band'] = f'{int(share_core * 10) * 10}-{int(share_core * 10) * 10 + 10} %'
for h, lab in ((365, 'h365'), (np.inf, 'hinf')):
    sc = score(h)
    S = {}
    for name, mask in (('all', np.ones(len(it), bool)), ('same_org', it.same_org.values), ('cross_org', ~it.same_org.values & it.subOrg.notna().values & it.decOrg.notna().values),
                       ('core_submitter', it.core.values), ('community_submitter', ~it.core.values),
                       ('cross_org_community', ~it.same_org.values & ~it.core.values), ('same_org_core', it.same_org.values & it.core.values)):
        S[name] = summ(sc, list(np.flatnonzero(mask)))
    res[lab] = S
    print(lab, json.dumps(S), flush=True)
json.dump(res, open(os.path.join(H, 'res_d_service_strata.json'), 'w', encoding='utf-8'), indent=1)
