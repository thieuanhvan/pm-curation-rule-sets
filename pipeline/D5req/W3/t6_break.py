# T6: structural break in CIViC evidence intake (85 -> 51 per month): change-point(s) with bootstrap CI, campaign-robust variants.
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261007)
E = pd.read_pickle('w3_events.pkl'); it = pd.read_pickle('w3_items.pkl')
R = {}
def P(k, v): R[k] = v; print(k, json.dumps(v, default=str)[:2500], flush=True)
it['m'] = pd.to_datetime(it.arr * 864e11).dt.to_period('M')
it['day'] = np.floor(it.arr).astype(int)
bd = it.groupby(['subU', 'day']).size(); it['burst'] = [bd[(u, d)] for u, d in zip(it.subU, it.day)]
months = pd.period_range('2015-07', '2026-09', freq='M')
def series(mask=None):
    s = it if mask is None else it[mask]
    return s.groupby('m').size().reindex(months, fill_value=0)
S = {'all': series(), 'non_burst(<20/submitter-day)': series(it.burst < 20),
     'distinct_submitters': it.groupby('m').subU.nunique().reindex(months, fill_value=0)}
first = it.groupby('subU').arr.min(); it['newSub'] = it.arr.values == it.subU.map(first).values
S['new_submitters'] = it[it.newSub].groupby('m').subU.nunique().reindex(months, fill_value=0)

def seg_cost(y, i, j, kind):
    x = y[i:j]
    if kind == 'pois':
        lam = max(x.mean(), 1e-9); return -(x * np.log(lam) - lam).sum()
    return ((x - x.mean()) ** 2).sum()
def best_k(y, k, kind, minseg=6):
    n = len(y); INF = 1e18
    cs = np.full((k + 1, n + 1), INF); arg = np.zeros((k + 1, n + 1), int)
    cost = {}
    def c(i, j):
        if (i, j) not in cost: cost[(i, j)] = seg_cost(y, i, j, kind)
        return cost[(i, j)]
    for j in range(minseg, n + 1): cs[0, j] = c(0, j)
    for kk in range(1, k + 1):
        for j in range((kk + 1) * minseg, n + 1):
            best = INF; bi = 0
            for i in range(kk * minseg, j - minseg + 1):
                v = cs[kk - 1, i] + c(i, j)
                if v < best: best, bi = v, i
            cs[kk, j], arg[kk, j] = best, bi
    cps = []; j = n
    for kk in range(k, 0, -1): i = arg[kk, j]; cps.append(i); j = i
    return cs[k, n], sorted(cps)
def analyse(y, label, lo='2019-01', kmax=4):
    # restrict to the window where the 85 -> 51 break is claimed (2019-01 .. 2026-09) and also full series
    out = {}
    for win in ('2019-01..2026-09', 'full'):
        idx = np.arange(len(months)) if win == 'full' else np.flatnonzero(months >= pd.Period(lo, 'M'))
        yy = y.values[idx].astype(float); mm = months[idx]
        # overdispersed counts: segment on log1p with LS (robust to campaign spikes) and on Poisson; BIC on LS
        ly = np.log1p(yy); n = len(ly)
        fits = {k: best_k(ly, k, 'ls') for k in range(0, kmax + 1)}
        bic = {k: n * np.log(fits[k][0] / n) + (2 * k + 1) * np.log(n) for k in fits}
        k = min(bic, key=bic.get); cps = fits[k][1]
        # single most important break (k=1) with block-bootstrap CI (12-month blocks of residuals around the k-segment fit)
        c1 = fits[1][1][0]
        edges = [0] + cps + [n]; fitted = np.zeros(n)
        for a, b in zip(edges[:-1], edges[1:]): fitted[a:b] = ly[a:b].mean()
        res = ly - fitted; bcp = []
        for _ in range(300):
            ii = np.concatenate([np.arange(s, s + 12) % n for s in rng.integers(0, n, n // 12 + 1)])[:n]
            yb = fitted + res[ii]; bcp.append(best_k(yb, 1, 'ls')[1][0])
        lo_, hi_ = np.percentile(bcp, [2.5, 97.5]).astype(int)
        segs = [(str(mm[a]), str(mm[b - 1]), round(float(yy[a:b].mean()), 1), round(float(np.median(yy[a:b])), 1)) for a, b in zip(edges[:-1], edges[1:])]
        o = {'k_BIC(log1p LS)': k, 'changepoints': [str(mm[c]) for c in cps], 'segments(start,end,mean,median)': segs,
             'single_break_k1': str(mm[c1]), 'single_break_ci95_block_boot': [str(mm[lo_]), str(mm[min(hi_, n - 1)])],
             'single_break_means_before_after': [round(float(yy[:c1].mean()), 1), round(float(yy[c1:].mean()), 1)]}
        # Poisson single break (no bootstrap), for comparison
        o['single_break_k1_poisson'] = str(mm[best_k(yy, 1, 'pois')[1][0]])
        out[win] = o
    P(f'break_{label}', out)
for k, y in S.items(): analyse(y, k)
# annual table
yr = it.groupby(it.m.dt.year).agg(arrivals=('arr', 'size'), submitters=('subU', 'nunique'), share_burst20=('burst', lambda b: round(float((b >= 20).mean()), 3)))
P('annual_intake', yr.to_dict('index'))
# event-type fingerprints for platform changes (first / last month of selected actions)
EV = E.copy(); EV['m'] = pd.to_datetime(EV.t * 864e11).dt.to_period('M').astype(str)
fp = {a: [EV[EV.act == a].m.min(), EV[EV.act == a].m.max(), int((EV.act == a).sum())] for a in ['DEPRECATED_VARIANT', 'DEPRECATED_MOLECULAR_PROFILE', 'REVISION_SUPERSEDED', 'CURATED_SOURCE_SUGGESTION', 'REVERTED', 'FEATURE_CREATED', 'DEPRECATED_FEATURE', 'COMMENT_DELETED']}
P('event_type_first_last_month', fp)
P('bot_activity_by_month_top', EV[EV.bot].m.value_counts().head(10).to_dict())
# monthly arrivals around the break for the record
P('monthly_arrivals_2021_2024', {str(k): int(v) for k, v in S['all'].items() if '2021-07' <= str(k) <= '2023-12'})
P('monthly_distinct_submitters_2021_2024', {str(k): int(v) for k, v in S['distinct_submitters'].items() if '2021-07' <= str(k) <= '2023-12'})
json.dump(R, open('res_t6_break.json', 'w'), indent=1, default=str)
# decomposition of the drop: submitters active 2021-22 vs 2023-25 (aggregated, k>=5)
a = it[(it.m >= pd.Period('2021-01', 'M')) & (it.m <= pd.Period('2022-12', 'M'))]; b = it[(it.m >= pd.Period('2023-01', 'M')) & (it.m <= pd.Period('2025-12', 'M'))]
ca = a.subU.value_counts(); cb = b.subU.value_counts()
top5 = list(ca.index[:5]); top10 = list(ca.index[:10])
stay = set(ca.index) & set(cb.index)
P('drop_decomposition_2021_22_vs_2023_25', {
    'per_month_before_after': [round(len(a) / 24, 1), round(len(b) / 36, 1)],
    'submitters_before_after': [int(len(ca)), int(len(cb))], 'submitters_in_both': len(stay),
    'top5_2021_22_submitters_per_month_before_after': [round(a.subU.isin(top5).sum() / 24, 1), round(b.subU.isin(top5).sum() / 36, 1)],
    'top10_2021_22_submitters_per_month_before_after': [round(a.subU.isin(top10).sum() / 24, 1), round(b.subU.isin(top10).sum() / 36, 1)],
    'others_per_month_before_after': [round((~a.subU.isin(top10)).sum() / 24, 1), round((~b.subU.isin(top10)).sum() / 36, 1)],
    'share_of_drop_explained_by_top10_2021_22': round(((a.subU.isin(top10).sum() / 24) - (b.subU.isin(top10).sum() / 36)) / ((len(a) / 24) - (len(b) / 36)), 3),
    'burst20_items_per_month_before_after': [round((a.burst >= 20).sum() / 24, 1), round((b.burst >= 20).sum() / 36, 1)]})
json.dump(R, open('res_t6_break.json', 'w'), indent=1, default=str)
