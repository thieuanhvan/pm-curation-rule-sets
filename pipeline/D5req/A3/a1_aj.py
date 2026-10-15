# (1) Aalen-Johansen cumulative incidence (competing risks) with administrative right-censoring at extraction.
# CIViC: ACC / REJ (decider != submitter) / WDR (submitter self-rejects). GO/HPO: completed / not_planned. Wikidata: done / notdone / withdrawn.
import json, os, pickle
import numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); K4 = os.path.join(BASE, '..', '..', 'D5k4')
rng = np.random.default_rng(20261007)
HORIZ = [30, 365, 730, 1826]

def aj(T, C, causes, grid):
    """T: time (days) to event/censor, C: cause label or None (censored). Returns CIF[cause][grid]."""
    o = np.argsort(T); T, C = T[o], C[o]
    ut, idx = np.unique(T, return_index=True)
    n = len(T); nrisk = n - idx
    S = 1.0; cif = {k: np.zeros(len(ut)) for k in causes}; acc = {k: 0.0 for k in causes}
    cnt = {k: np.add.reduceat((C == k).astype(float), idx) for k in causes}
    dall = sum(cnt.values())
    for j in range(len(ut)):
        for k in causes: acc[k] += S * cnt[k][j] / nrisk[j]; cif[k][j] = acc[k]
        S *= 1 - dall[j] / nrisk[j]
    out = {}
    for k in causes:
        pos = np.searchsorted(ut, grid, side='right') - 1
        out[k] = np.where(pos >= 0, cif[k][np.clip(pos, 0, None)], 0.0)
    return out

def aj_ci(T, C, causes, grid, B=300):
    est = aj(T, C, causes, grid); bs = {k: [] for k in causes}
    for _ in range(B):
        i = rng.integers(0, len(T), len(T)); r = aj(T[i], C[i], causes, grid)
        for k in causes: bs[k].append(r[k])
    res = {}
    for k in causes:
        b = np.array(bs[k]); lo, hi = np.percentile(b, [2.5, 97.5], axis=0)
        res[k] = {f'{g}d': [round(float(e), 4), round(float(l), 4), round(float(h), 4)] for g, e, l, h in zip(grid, est[k], lo, hi)}
    return res

def run(df, causes, label, cohort_col='cy', B=300):
    out = {'overall': {'n': len(df), **aj_ci(df['T'].values, df['C'].values, causes, HORIZ, B)}}
    maxfu = {}
    for y, g in df.groupby(cohort_col, observed=True):
        if len(g) < 20: continue
        fu = float(g['NOWd'].iloc[0] - g['arr'].max())  # min follow-up in cohort
        grid = [h for h in HORIZ if h <= (g['NOWd'].iloc[0] - g['arr'].min())]
        r = aj_ci(g['T'].values, g['C'].values, causes, grid, B)
        out[str(y)] = {'n': len(g), 'minFollowUpDays': round(fu), **r}
    return out

R = {}
# CIViC
d = pickle.load(open(os.path.join(BASE, 'civic_items.pkl'), 'rb')); it = d['items']; NOW = d['NOW']
it = it.assign(T=np.where(it.out == 'PEND', NOW - it.arr, it.dec - it.arr), C=np.where(it.out == 'PEND', None, it.out),
               cy=pd.to_datetime(it.arr, unit='D').dt.year, NOWd=NOW)
it['C'] = it['C'].astype(object)
R['civic'] = run(it, ['ACC', 'REJ', 'WDR'], 'civic')
# CIViC by era of submission (coarser, more stable)
it['era'] = pd.cut(it.cy, [2014, 2016, 2018, 2022, 2026], labels=['2015-16', '2017-18', '2019-22', '2023-26'])
R['civic_era'] = run(it, ['ACC', 'REJ', 'WDR'], 'civic', cohort_col='era')

# GO / HPO (rule-free crude: GitHub state_reason completed vs not_planned; 'completed' includes non-acceptance closures)
NOWgh = pd.Timestamp('2026-10-07T00:00:00Z').value / 864e11
for tag in ('go', 'hpo'):
    o = list(json.load(open(os.path.join(K4, f'issues_{tag}.json'), encoding='utf-8')).values())
    rows = []
    for x in o:
        if x['c'] < '2016': continue
        a = pd.Timestamp(x['c']).value / 864e11
        if x['s'] == 'open': rows.append((a, NOWgh - a, None))
        else: rows.append((a, pd.Timestamp(x['x']).value / 864e11 - a, 'NOTPLANNED' if x.get('sr') == 'not_planned' else 'COMPLETED'))
    g = pd.DataFrame(rows, columns=['arr', 'T', 'C']); g['cy'] = pd.to_datetime(g.arr, unit='D').dt.year; g['NOWd'] = NOWgh
    g['C'] = g['C'].astype(object)
    R[tag] = run(g, ['COMPLETED', 'NOTPLANNED'], tag)
# Wikidata sample
raw = json.load(open(os.path.join(K4, 'wd_cases.json'), encoding='utf-8'))
mp = {'done': 'DONE', 'other:done': 'DONE', 'notdone': 'NOTDONE', 'withdrawn': 'WITHDRAWN'}
rows = []
for x in raw:
    if x.get('arr') is None or x['arr'] < pd.Timestamp('2016-01-01').value / 1e6: continue
    a = x['arr'] / 864e5
    if x['kind'] == 'pending': rows.append((a, NOWgh - a, None))
    elif x['kind'] in mp and x.get('dec') is not None: rows.append((a, max(0, x['dec'] / 864e5 - a), mp[x['kind']]))
g = pd.DataFrame(rows, columns=['arr', 'T', 'C']); g['cy'] = pd.to_datetime(g.arr, unit='D').dt.year; g['NOWd'] = NOWgh
g['C'] = g['C'].astype(object)
R['wikidata_sample'] = run(g, ['DONE', 'NOTDONE', 'WITHDRAWN'], 'wd')
json.dump(R, open(os.path.join(BASE, 'res_a1_aj.json'), 'w'), indent=1)
def show(k):
    for c, v in R[k].items():
        print(k, c, 'n=', v['n'], {kk: {h: vv[h] for h in vv} for kk, vv in v.items() if isinstance(vv, dict)})
for k in R: show(k)
