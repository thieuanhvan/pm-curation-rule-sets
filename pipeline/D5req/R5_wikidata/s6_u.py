# R5_wikidata (copy of D5req/W7/w7_t3_wd_u.py on the census). W7 T3: Wikidata property proposals, relative queue position u re-implemented as in W3/t3_abandon.py
# (live-queue u is computed only for decisions whose chosen item is itself live; queue = live items; ties count 1/2;
#  permutation null; cluster bootstrap over decider-day). Input wd_cases_census_u.json (pseudonymised). No network.
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261007); NSIM = 500
raw = json.load(open('wd_cases_census_u.json', encoding='utf-8'))
DEC = {'done', 'notdone', 'withdrawn', 'other:done'}
rows = [dict(id=x['id'], arr=x['arr'] / 864e5, dec=(x['dec'] / 864e5 if x['kind'] in DEC else np.nan), kind=x['kind'], decU=x.get('decU'), sub=x.get('prop'))
        for x in raw if x['kind'] == 'pending' or (x['kind'] in DEC and x.get('dec') is not None)]
it = pd.DataFrame(rows); it = it[it.arr >= pd.Timestamp('2016-01-01').value / 864e11].sort_values('arr').reset_index(drop=True)
it['dec'] = np.where(it.dec < it.arr, it.arr, it.dec)
arr = it.arr.values; dec = it.dec.values
order = np.argsort(np.where(np.isnan(dec), np.inf, dec), kind='stable'); order = order[~np.isnan(dec[order])]
D = lambda s: pd.Timestamp(s).value / 864e11
def tokens(X=None, t_from=D('2016-01-01'), excl_withdrawn=False):
    present = np.zeros(len(arr), bool); ao = np.argsort(arr, kind='stable'); ai = 0; out = []
    for j in order:
        t = dec[j]
        while ai < len(ao) and arr[ao[ai]] <= t: present[ao[ai]] = True; ai += 1
        if not present[j]: continue
        if t >= t_from and not (excl_withdrawn and it.kind.values[j] == 'withdrawn'):
            q = np.flatnonzero(present)
            if X is not None:
                live = (t - arr[q]) <= X; ch = bool(live[q == j][0]); q = q[live]
            else: ch = True
            if ch and len(q) > 1:
                qa = np.sort(arr[q]); L = len(q)
                uval = lambda a: ((L - np.searchsorted(qa, a, 'right')) + 0.5 * (np.searchsorted(qa, a, 'right') - np.searchsorted(qa, a, 'left') - 1)) / (L - 1)
                out.append(dict(u=float(uval(arr[j])), null=uval(qa[rng.integers(0, L, NSIM)]), L=L, c=f'{it.decU.values[j]}|{int(t)}'))
            elif not ch: out.append(dict(u=np.nan))
        present[j] = False
    return out
def summ(tk, B=2000):
    nall = len(tk); tk = [x for x in tk if not np.isnan(x['u'])]
    u = np.array([x['u'] for x in tk]); cl = np.array([x['c'] for x in tk]); nl = np.array([x['null'] for x in tk])
    uc, inv = np.unique(cl, return_inverse=True); sums = np.bincount(inv, u); s10 = np.bincount(inv, (u <= .1).astype(float)); cnt = np.bincount(inv)
    bs, b10 = [], []
    for _ in range(B):
        s = rng.integers(0, len(uc), len(uc)); bs.append(sums[s].sum() / cnt[s].sum()); b10.append(s10[s].sum() / cnt[s].sum())
    return {'n': len(u), 'share_decisions_on_live_items': round(len(u) / max(nall, 1), 3), 'meanU': [round(u.mean(), 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3)],
            'newest10': [round((u <= .1).mean(), 3), round(np.percentile(b10, 2.5), 3), round(np.percentile(b10, 97.5), 3)],
            'null_meanU_95': [round(np.percentile(nl.mean(0), 2.5), 3), round(np.percentile(nl.mean(0), 97.5), 3)],
            'null_newest10_95': [round(np.percentile((nl <= .1).mean(0), 2.5), 3), round(np.percentile((nl <= .1).mean(0), 97.5), 3)], 'median_queue_L': int(np.median([x['L'] for x in tk]))}
R = {'n_cases': len(it), 'n_decisions': int((~np.isnan(dec)).sum()), 'n_pending_now': int(np.isnan(dec).sum()),
     'note': 'Census of proposal subpages (R5_wikidata), u relative to all parsed pending proposals.'}
for lab, tf in (('from2016', D('2016-01-01')), ('from2021', D('2021-01-01'))):
    o = {'all_pending': summ(tokens(None, tf)), 'all_pending_excl_withdrawn': summ(tokens(None, tf, True))}
    for X in (180, 365, 730): o[f'live_age<={X}'] = summ(tokens(X, tf))
    R[lab] = o; print(lab, json.dumps(o), flush=True)
json.dump(R, open('results_u.json', 'w'), indent=1)
