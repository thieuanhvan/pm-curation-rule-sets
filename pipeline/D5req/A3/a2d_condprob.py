# P(decision within next 365 d | still pending at age T), with submitter-cluster bootstrap CIs; all items vs items live at T (activity in prior 365 d).
import os, pickle, json, numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); rng = np.random.default_rng(3)
d = pickle.load(open(os.path.join(BASE, 'civic_items.pkl'), 'rb')); it = d['items']; NOW = d['NOW']
R = {}
for T in (30, 90, 180, 365, 730, 1461, 2192):
    el = it[(it.arr + T + 365 <= NOW) & (it.dec.isna() | (it.dec > it.arr + T))].copy()
    el['hit'] = (~el.dec.isna()) & (el.dec <= el.arr + T + 365)
    el['live'] = [any((t > a + T - 365) & (t <= a + T) for t in list(ts) + [a]) for a, ts in zip(el.arr, el.act_t)]
    el['era'] = np.where(el.arr + T < pd.Timestamp('2021-01-01').value / 864e11, 'atRisk<2021', 'atRisk2021+')
    out = {}
    for nm, g in [('all', el), ('live', el[el.live]), ('notlive', el[~el.live]), ('all|atRisk<2021', el[el.era == 'atRisk<2021']), ('all|atRisk2021+', el[el.era == 'atRisk2021+'])]:
        if len(g) < 20: continue
        grp = {u: x.hit.values for u, x in g.groupby('subU')}; us = list(grp)
        bs = []
        for _ in range(1000):
            s = rng.integers(0, len(us), len(us)); k = sum(grp[us[i]].sum() for i in s); n = sum(len(grp[us[i]]) for i in s); bs.append(k / n)
        out[nm] = {'n': len(g), 'p': round(float(g.hit.mean()), 3), 'ci95_clusterboot': [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]}
    R[f'age{T}d'] = out; print(T, out)
json.dump(R, open(os.path.join(BASE, 'res_a2d_condprob.json'), 'w'), indent=1)
