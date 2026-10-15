# T3: sensitivity of (a) P2 live-queue service position and (b) the age-hazard decline to the abandonment definition.
# Definitions of "not abandoned" at time t: age <= X; item activity (incl. submission) within X; submitter active within X; item OR submitter.
import os, json, pickle, numpy as np, pandas as pd, statsmodels.api as sm
rng = np.random.default_rng(20261007); NSIM = 500
A3 = '../A3/'
d = pickle.load(open(A3 + 'civic_items.pkl', 'rb')); it = d['items'].sort_values(['arr', 'id']).reset_index(drop=True); NOW = d['NOW']; ud = d['udays']
R = {}
def P(k, v): R[k] = v; print(k, json.dumps(v, default=str)[:1500], flush=True)
lastact = [np.sort(np.array(list(a) + [s0])) for a, s0 in zip(it.act_t, it.arr)]
subdays = [ud.get(u, np.array([])) for u in it.subU]
def item_live(i, t, X): a = lastact[i]; k = np.searchsorted(a, t, 'right'); return k > 0 and a[k - 1] > t - X
def sub_live(i, t, X): a = subdays[i]; k = np.searchsorted(a, t, 'right'); return k > 0 and a[k - 1] > t - X
DEFS = {}
for X in (180, 365, 730):
    DEFS[f'age<={X}'] = lambda i, t, X=X: t - it.arr.values[i] <= X
    DEFS[f'itemAct<={X}'] = lambda i, t, X=X: item_live(i, t, X)
    DEFS[f'subActive<={X}'] = lambda i, t, X=X: sub_live(i, t, X)
    DEFS[f'itemOrSub<={X}'] = lambda i, t, X=X: item_live(i, t, X) or sub_live(i, t, X)
arr = it.arr.values; dec = it.dec.values
order = np.argsort(np.where(np.isnan(dec), np.inf, dec), kind='stable'); order = order[~np.isnan(dec[order])]
T21 = pd.Timestamp('2021-01-01').value / 864e11
def tokens(fn, t_from=T21):
    present = np.zeros(len(arr), bool); arr_ord = np.argsort(arr, kind='stable'); ai = 0; out = []
    for j in order:
        t = dec[j]
        while ai < len(arr_ord) and arr[arr_ord[ai]] <= t: present[arr_ord[ai]] = True; ai += 1
        if not present[j]: continue
        if t >= t_from:
            q = np.flatnonzero(present)
            if fn is not None:
                lm = np.array([fn(i, t) for i in q]); ch = bool(lm[q == j][0]); q = q[lm]
            else: ch = True
            if ch and len(q) > 1:
                qa = np.sort(arr[q]); L = len(q)
                def uval(a): return ((L - np.searchsorted(qa, a, 'right')) + 0.5 * (np.searchsorted(qa, a, 'right') - np.searchsorted(qa, a, 'left') - 1)) / (L - 1)
                r = it.iloc[j]
                out.append(dict(u=uval(arr[j]), null=uval(qa[rng.integers(0, L, NSIM)]), L=L, c=f'{r.decU}|{int(t)}', out=r.out,
                                cross=(r.decOrg == r.decOrg and r.subOrg == r.subOrg and r.decOrg != r.subOrg)))
            elif not ch: out.append(dict(u=np.nan, chosen_live=False))
        present[j] = False
    return out
def summ(tk, B=1000):
    tk = [x for x in tk if not np.isnan(x['u'])]
    if len(tk) < 10: return {'n': len(tk)}
    u = np.array([x['u'] for x in tk]); cl = np.array([x['c'] for x in tk]); nl = np.array([x['null'] for x in tk])
    uc, inv = np.unique(cl, return_inverse=True); sums = np.bincount(inv, u); s10 = np.bincount(inv, (u <= .1).astype(float)); cnt = np.bincount(inv)
    bs, b10 = [], []
    for _ in range(B):
        s = rng.integers(0, len(uc), len(uc)); bs.append(sums[s].sum() / cnt[s].sum()); b10.append(s10[s].sum() / cnt[s].sum())
    return {'n': len(u), 'meanU': [round(u.mean(), 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3)],
            'newest10': [round((u <= .1).mean(), 3), round(np.percentile(b10, 2.5), 3), round(np.percentile(b10, 97.5), 3)],
            'null_meanU_95': [round(np.percentile(nl.mean(0), 2.5), 3), round(np.percentile(nl.mean(0), 97.5), 3)], 'median_queue_L': int(np.median([x['L'] for x in tk]))}
pos = {}
base = tokens(None)
pos['no_filter(all pending)'] = {'all': summ(base), 'crossOrg_nonWDR': summ([x for x in base if x['out'] != 'WDR' and x['cross']])}
print('base', pos['no_filter(all pending)'], flush=True)
for k, fn in DEFS.items():
    tk = tokens(fn)
    nlive = sum(1 for x in tk if not np.isnan(x['u'])); nall = len(tk)
    pos[k] = {'share_decisions_on_live_items': round(nlive / max(nall, 1), 3), 'all': summ(tk), 'crossOrg_nonWDR': summ([x for x in tk if not np.isnan(x['u']) and x['out'] != 'WDR' and x['cross']])}
    print(k, json.dumps(pos[k]), flush=True)
R['P2_service_position_2021plus'] = pos
json.dump(R, open('res_t3_abandon.json', 'w'), indent=1, default=str)

# ---------------- (b) age-hazard among items aged >= 1 y, restricted to not-abandoned intervals
rows = []
T = np.where(it.out == 'PEND', NOW - it.arr, it.dec - it.arr)
for i, r in enumerate(it.itertuples()):
    if T[i] <= 365: continue
    a0 = 365.0
    while a0 < T[i]:
        a1 = min(a0 + 91.3125, T[i]); t0 = r.arr + a0
        e = int(a1 == T[i] and r.out != 'PEND')
        rec = dict(i=i, ageY=a0 / 365.25, expo=a1 - a0, year=pd.Timestamp(t0 * 864e11).year, eANY=e, eACC=int(e and r.out == 'ACC'),
                   level=r.level, rating=str(r.rating), etype=r.etype, subU=r.subU, nrev=np.log1p(np.searchsorted(np.array(r.rev_t), t0, 'right')))
        for X in (180, 365, 730):
            rec[f'item{X}'] = item_live(i, t0, X); rec[f'sub{X}'] = sub_live(i, t0, X)
        rows.append(rec); a0 = a1
PE = pd.DataFrame(rows)
print('intervals', len(PE), 'events', PE[['eANY', 'eACC']].sum().to_dict(), flush=True)
def fit(df, y):
    X = pd.concat([df[['ageY', 'nrev']], pd.get_dummies(df.level, prefix='l', dtype=float), pd.get_dummies(df.rating, prefix='r', dtype=float),
                   pd.get_dummies(df.etype, prefix='t', dtype=float), pd.get_dummies(df.year, prefix='y', dtype=float)], axis=1)
    X = X.loc[:, X.std() > 0]
    # drop one dummy per block to avoid collinearity with const
    for pre in ('l_', 'r_', 't_', 'y_'):
        cs = [c for c in X if c.startswith(pre)]
        if cs: X = X.drop(columns=cs[0])
    X = X.assign(const=1.0)
    m = sm.GLM(df[y].values, X, family=sm.families.Poisson(), offset=np.log(df.expo.values)).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(df.subU)[0]}, maxiter=200)
    ci = m.conf_int().loc['ageY']
    return {'HR_per_year_of_age': [round(float(np.exp(m.params['ageY'])), 3), round(float(np.exp(ci[0])), 3), round(float(np.exp(ci[1])), 3)], 'p': float(f"{m.pvalues['ageY']:.2g}"),
            'events': int(df[y].sum()), 'intervals': len(df), 'submitters': int(df.subU.nunique())}
ah = {}
masks = {'all_intervals': np.ones(len(PE), bool)}
for X in (180, 365, 730):
    masks[f'itemAct<={X}'] = PE[f'item{X}'].values; masks[f'subActive<={X}'] = PE[f'sub{X}'].values
    masks[f'itemOrSub<={X}'] = PE[f'item{X}'].values | PE[f'sub{X}'].values
    masks[f'itemAND_sub<={X}'] = PE[f'item{X}'].values & PE[f'sub{X}'].values
for k, m in masks.items():
    ah[k] = {}
    for y in ('eANY', 'eACC'):
        try: ah[k][y] = fit(PE[m], y)
        except Exception as e: ah[k][y] = f'ERR {e}'
    print(k, json.dumps(ah[k]), flush=True)
R['age_hazard_ge1y_by_definition'] = ah
json.dump(R, open('res_t3_abandon.json', 'w'), indent=1, default=str)
