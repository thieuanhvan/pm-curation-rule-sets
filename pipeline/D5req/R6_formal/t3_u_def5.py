# R6 task 3: Definition 5 (service position) recomputed with the corrected definition.
#   Q(t-) = {j : a_j < t <= d_j}  (pending just before t; items decided at the same instant stay in the queue)
#   Q_h(t-) = {j in Q(t-) : t - a_j <= h};  decisions with d_i - a_i > h are excluded (i is outside the live queue)
#   S_i = Q_h(d_i-) U {i};  u_i = ( #{j in S_i : a_j > a_i} + 0.5 * #{j in S_i, j != i : a_j = a_i} ) / (|S_i| - 1)
#   decisions with |S_i| = 1 are excluded (undefined). Null: j drawn uniformly from S_i, u_j by the same formula (2,000 draws).
# CIViC: ../A3/civic_items.pkl (first terminal decision per evidence item, bot excluded upstream).
# GO/HPO: population ../../D5k4/issues_<tag>.json (all NTR tickets, open/close), decisions = sampled closures ../W2/outcomes_w2_<tag>.json.
import os, json, pickle, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); R0 = os.path.join(H, '..')
rng = np.random.default_rng(20261007); NS = 2000; B = 2000
T21 = pd.Timestamp('2021-01-01').value / 864e11

def u_all(arr, dec, cand, h, t_from, cluster):
    """arr, dec: arrays in days (dec = inf if pending); cand: indices of decisions to score."""
    out = []
    for i in cand:
        t = dec[i]
        if t < t_from: continue
        if t - arr[i] > h: out.append(None); continue
        m = (arr < t) & (dec >= t) & (t - arr <= h)
        m[i] = True
        qa = np.sort(arr[m]); L = len(qa)
        if L < 2: continue
        def uval(a):
            gt = L - np.searchsorted(qa, a, 'right'); eq = np.searchsorted(qa, a, 'right') - np.searchsorted(qa, a, 'left') - 1
            return (gt + 0.5 * eq) / (L - 1)
        out.append(dict(u=float(uval(arr[i])), null=uval(qa[rng.integers(0, L, NS)]), L=L, c=cluster[i]))
    return out

def summ(tk):
    excl = sum(1 for x in tk if x is None); tk = [x for x in tk if x is not None]
    u = np.array([x['u'] for x in tk]); nl = np.array([x['null'] for x in tk]); cl = np.array([str(x['c']) for x in tk])
    uc, inv = np.unique(cl, return_inverse=True); sums = np.bincount(inv, u); s10 = np.bincount(inv, (u <= .1).astype(float)); cnt = np.bincount(inv)
    bs, b10 = [], []
    for _ in range(B):
        s = rng.integers(0, len(uc), len(uc)); bs.append(sums[s].sum() / cnt[s].sum()); b10.append(s10[s].sum() / cnt[s].sum())
    nm = nl.mean(0)
    return {'n_scored': int(len(u)), 'n_excluded_age_gt_h': int(excl), 'meanU': [round(u.mean(), 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3)],
            'newest10': [round((u <= .1).mean(), 3), round(np.percentile(b10, 2.5), 3), round(np.percentile(b10, 97.5), 3)],
            'null_meanU_95': [round(np.percentile(nm, 2.5), 3), round(np.percentile(nm, 97.5), 3)],
            'null_newest10_95': [round(np.percentile((nl <= .1).mean(0), 2.5), 3), round(np.percentile((nl <= .1).mean(0), 97.5), 3)],
            'perm_p_one_sided': float((nm <= u.mean()).mean()), 'median_queue_size': int(np.median([x['L'] for x in tk])),
            'share_scored_with_tied_arrivals': None}

res = {}
# ---------------- CIViC
d = pickle.load(open(os.path.join(R0, 'A3', 'civic_items.pkl'), 'rb')); it = d['items'].reset_index(drop=True)
arr = it.arr.values.astype(float); dec = np.where(it.dec.isna(), np.inf, it.dec.values.astype(float))
cluster = it.subOrg.astype(str).values  # cluster for bootstrap: submitter-organisation proxy not ideal; use decision-day x decider as in W3
cluster = np.array([f'{r.decOrg}|{int(r.dec) if r.dec == r.dec else -1}' for r in it.itertuples()])
cand = np.flatnonzero(np.isfinite(dec))
ties = pd.Series(arr).duplicated(keep=False).values
for h, lab in ((365, 'h365'), (np.inf, 'hinf')):
    tk = u_all(arr, dec, cand, h, T21, cluster)
    s = summ(tk); s['share_decided_items_with_tied_arrival'] = round(float(ties[[i for i in cand if dec[i] >= T21]].mean()), 3)
    res[f'civic_2021plus_{lab}'] = s; print('civic', lab, s, flush=True)
# old definition for comparison (W3: Q excludes items decided earlier at the same instant, no {i} union rule) from res_t3_abandon
try:
    w3 = json.load(open(os.path.join(R0, 'W3', 'res_t3_abandon.json'), encoding='utf-8'))['P2_service_position_2021plus']
    res['civic_previous_definition'] = {'age<=365': w3.get('age<=365', {}).get('all'), 'all_pending': w3.get('no_filter(all pending)', {}).get('all')}
except Exception as e:
    res['civic_previous_definition'] = str(e)
# ---------------- GO / HPO
for tag in ('go', 'hpo'):
    pop = json.load(open(os.path.join(R0, '..', 'D5k4', f'issues_{tag}.json'), encoding='utf-8'))
    pop = [x for x in pop.values() if not x.get('pr')]
    oc = [r for r in json.load(open(os.path.join(R0, 'W2', f'outcomes_w2_{tag}.json'), encoding='utf-8')) if r.get('cls') and r.get('close')]
    idx = {x['n']: k for k, x in enumerate(pop)}
    a = np.array([pd.Timestamp(x['c']).value / 864e11 for x in pop]); x_ = np.array([np.inf if x['s'] == 'open' or not x.get('x') else pd.Timestamp(x['x']).value / 864e11 for x in pop])
    # decision time for sampled tickets = classifier close time (final close); population uses final close time too
    for r in oc:
        if r['n'] in idx: x_[idx[r['n']]] = pd.Timestamp(r['close']).value / 864e11
    cand = [idx[r['n']] for r in oc if r['n'] in idx]
    cl = np.array([str(x['n']) for x in pop])
    for h, lab in ((365, 'h365'), (np.inf, 'hinf')):
        tk = u_all(a, x_, cand, h, T21, cl)
        s = summ(tk); res[f'{tag}_2021plus_{lab}'] = s; print(tag, lab, s, flush=True)
    res[f'{tag}_previous'] = {'source': '../R3_trackers/r3_t4_u_null.json'}
prev = json.load(open(os.path.join(R0, 'R3_trackers', 'r3_t4_u_null.json')))
for tag in ('go', 'hpo'): res[f'{tag}_previous'] = prev.get(f'{tag}_2021plus')
for k, v in res.items():
    if isinstance(v, dict): v.pop('share_scored_with_tied_arrivals', None)
json.dump(res, open(os.path.join(H, 'res_t3.json'), 'w'), indent=1)
