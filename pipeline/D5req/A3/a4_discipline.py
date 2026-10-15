# (4) Service-discipline index with a random-order-service null, live-only queue, submitter-decider pairs,
#     same-day batches, and change-point detection with block-bootstrap CIs. CIViC + GO/HPO/Wikidata.
import os, pickle, json, sys
import numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); K4 = os.path.join(BASE, '..', '..', 'D5k4')
rng = np.random.default_rng(11)
NSIM = 1000

def tokens_u(cases, live_fn=None):
    """cases: DataFrame id, arr, dec (nan if pending) sorted by arr. For each decision token (in dec order):
    u = (#queued items newer than chosen + 0.5 #ties)/(L-1); 0 = newest, 1 = oldest. Also the null draws."""
    arr = cases.arr.values; dec = cases.dec.values; ids = cases.id.values
    order = np.argsort(np.where(np.isnan(dec), np.inf, dec), kind='stable'); order = order[~np.isnan(dec[order])]
    present = np.zeros(len(arr), bool); ai = 0; arr_ord = np.argsort(arr, kind='stable')
    out = []
    for j in order:
        t = dec[j]
        while ai < len(arr_ord) and arr[arr_ord[ai]] <= t: present[arr_ord[ai]] = True; ai += 1
        if not present[j]: continue
        qidx = np.flatnonzero(present)
        if live_fn is not None:
            lm = live_fn(qidx, t); chosen_live = bool(lm[qidx == j][0]); qidx = qidx[lm]
            if not chosen_live: out.append(dict(i=j, t=t, L=len(qidx), u=np.nan, chosen_live=False, null=np.full(NSIM, np.nan))); present[j] = False; continue
        L = len(qidx)
        if L > 1:
            qa = np.sort(arr[qidx])
            def uval(a): newer = len(qa) - np.searchsorted(qa, a, 'right'); ties = np.searchsorted(qa, a, 'right') - np.searchsorted(qa, a, 'left') - 1; return (newer + 0.5 * ties) / (L - 1)
            u = uval(arr[j]); nd = uval(qa[rng.integers(0, L, NSIM)])
            out.append(dict(i=j, t=t, L=L, u=u, chosen_live=True, null=nd))
        present[j] = False
    return out

def summarize(toks, key=lambda x: pd.Timestamp(x['t'] * 864e11).year, clus=None, B=500):
    """per group: observed mean u, share newest-10%, random-order null mean (95% null interval), cluster-bootstrap CI."""
    df = pd.DataFrame([dict(g=key(x), u=x['u'], c=(clus(x) if clus else x['i'])) for x in toks if not np.isnan(x['u'])])
    nulls = np.array([x['null'] for x in toks if not np.isnan(x['u'])])
    res = {}
    for g, sub in df.groupby('g'):
        if len(sub) < 5: continue
        idx = sub.index.values; nm = nulls[idx].mean(0); n10 = (nulls[idx] <= .1).mean(0)
        cl = sub.c.values; uc = np.unique(cl); grp = {c: sub.u.values[cl == c] for c in uc}
        bs, bs10 = [], []
        for _ in range(B):
            s = rng.choice(uc, len(uc)); v = np.concatenate([grp[c] for c in s]); bs.append(v.mean()); bs10.append((v <= .1).mean())
        res[str(g)] = {'n': len(sub), 'clusters': len(uc), 'meanU': [round(sub.u.mean(), 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3)],
                       'newest10': [round((sub.u <= .1).mean(), 3), round(np.percentile(bs10, 2.5), 3), round(np.percentile(bs10, 97.5), 3)],
                       'null_meanU_95': [round(np.percentile(nm, 2.5), 3), round(np.percentile(nm, 97.5), 3)],
                       'null_newest10_95': [round(np.percentile(n10, 2.5), 3), round(np.percentile(n10, 97.5), 3)]}
    return res

def segfit(y, w, kmax=4, minseg=6):
    """optimal weighted least-squares segmentation of series y (weights w) into k+1 segments (DP)."""
    n = len(y); cw = np.concatenate([[0], np.cumsum(w)]); cy = np.concatenate([[0], np.cumsum(w * y)]); cyy = np.concatenate([[0], np.cumsum(w * y * y)])
    def cost(i, j):
        W = cw[j] - cw[i]
        return 0 if W == 0 else (cyy[j] - cyy[i]) - (cy[j] - cy[i]) ** 2 / W
    INF = 1e18; best = {}
    C = np.full((kmax + 1, n + 1), INF); arg = np.zeros((kmax + 1, n + 1), int)
    for j in range(minseg, n + 1): C[0, j] = cost(0, j)
    for k in range(1, kmax + 1):
        for j in range((k + 1) * minseg, n + 1):
            cand = [(C[k - 1, i] + cost(i, j), i) for i in range(k * minseg, j - minseg + 1)]
            C[k, j], arg[k, j] = min(cand)
    for k in range(kmax + 1):
        cps = []; j = n
        for kk in range(k, 0, -1): i = arg[kk, j]; cps.append(i); j = i
        best[k] = (C[k, n], sorted(cps))
    return best

def changepoints(toks, label, kmax=4, B=300):
    """monthly mean-u series; BIC-selected number of change points; moving-block bootstrap (12 months) of residuals."""
    df = pd.DataFrame([dict(m=pd.Timestamp(x['t'] * 864e11).to_period('M'), u=x['u']) for x in toks if not np.isnan(x['u'])])
    g = df.groupby('m').u.agg(['mean', 'count']); allm = pd.period_range(g.index.min(), g.index.max(), freq='M'); g = g.reindex(allm)
    g = g[g['count'].fillna(0) > 0]
    y, w = g['mean'].values, g['count'].values.astype(float); months = [str(p) for p in g.index]
    best = segfit(y, w, kmax)
    N = w.sum(); s2 = best[kmax][0] / N
    bic = {k: N * np.log(best[k][0] / N) + (2 * k + 1) * np.log(len(y)) for k in best}
    k = min(bic, key=bic.get); cps = best[k][1]
    seg_means = []; edges = [0] + cps + [len(y)]
    fitted = np.zeros(len(y))
    for a, b in zip(edges[:-1], edges[1:]):
        m = (w[a:b] * y[a:b]).sum() / w[a:b].sum(); fitted[a:b] = m; seg_means.append((months[a], months[b - 1], round(float(m), 3), int(w[a:b].sum())))
    res = y - fitted; bl = 12; bcps = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, s + bl) % len(y) for s in rng.integers(0, len(y), len(y) // bl + 1)])[:len(y)]
        yb = fitted + res[idx] * np.sqrt(w[idx] / w)  # rescale residual to target weight (approx. heteroscedastic)
        bcps.append(segfit(yb, w, k)[k][1] if k else [])
    ci = []
    for c in range(k):
        v = np.array([b[c] for b in bcps]); lo, hi = np.percentile(v, [2.5, 97.5]).astype(int)
        ci.append({'cp_month': months[cps[c]], 'ci95': [months[lo], months[min(hi, len(months) - 1)]]})
    return {'series_months': len(y), 'k_BIC': k, 'bic': {str(a): round(float(b), 1) for a, b in bic.items()}, 'changepoints': ci, 'segments(start,end,meanU,nTokens)': seg_means}

R = {}
# ---------------- CIViC
d = pickle.load(open(os.path.join(BASE, 'civic_items.pkl'), 'rb')); it = d['items'].sort_values(['arr', 'id']).reset_index(drop=True)
toks = tokens_u(it[['id', 'arr', 'dec']])
for x in toks:
    r = it.iloc[x['i']]; x.update(decU=r.decU, subU=r.subU, sameOrg=(r.decOrg == r.subOrg) if r.decOrg == r.decOrg and r.subOrg == r.subOrg else None,
                                  day=int(np.floor(x['t'])), out=r.out, decRole=r.decRoleNow, ageD=x['t'] - r.arr)
# decider-day batches
bd = pd.Series([(x['decU'], x['day']) for x in toks]).value_counts()
for x in toks: x['batchN'] = int(bd[(x['decU'], x['day'])])
clus = lambda x: f"{x['decU']}|{x['day']}"
R['civic_all_by_year'] = summarize(toks, clus=clus)
R['civic_all_overall'] = summarize(toks, key=lambda x: 'all', clus=clus)
R['civic_2021plus'] = summarize([x for x in toks if x['t'] >= pd.Timestamp('2021-01-01').value / 864e11], key=lambda x: '2021+', clus=clus)
R['civic_by_outcome_2021plus'] = summarize([x for x in toks if x['t'] >= pd.Timestamp('2021-01-01').value / 864e11], key=lambda x: x['out'], clus=clus)
R['civic_batch_vs_single_by_era'] = summarize(toks, key=lambda x: ('batch>=10' if x['batchN'] >= 10 else ('batch2-9' if x['batchN'] >= 2 else 'single')) + '|' + ('<=2018' if x['t'] < pd.Timestamp('2019-01-01').value / 864e11 else '2019+'), clus=clus)
R['civic_sameOrg_by_era'] = summarize([x for x in toks if x['sameOrg'] is not None], key=lambda x: ('sameOrg' if x['sameOrg'] else 'crossOrg') + '|' + ('<=2018' if x['t'] < pd.Timestamp('2019-01-01').value / 864e11 else '2019+'), clus=clus)
# pair concentration: share of decisions in pairs with >= 5 decisions
pc = pd.Series([(x['decU'], x['subU']) for x in toks]).value_counts()
for x in toks: x['pairN'] = int(pc[(x['decU'], x['subU'])])
R['civic_pairs'] = {'pairs': int(len(pc)), 'share_decisions_in_pairs_ge5': round(float((pc[pc >= 5].sum()) / pc.sum()), 3), 'share_decisions_in_pairs_ge20': round(float((pc[pc >= 20].sum()) / pc.sum()), 3),
                    'self_pairs_decisions': int(sum(1 for x in toks if x['decU'] == x['subU']))}
R['civic_pairsize_by_era'] = summarize(toks, key=lambda x: ('pair>=20' if x['pairN'] >= 20 else 'pair<20') + '|' + ('<=2018' if x['t'] < pd.Timestamp('2019-01-01').value / 864e11 else '2019+'), clus=clus)
# one token per decider-day batch (batch collapsed to its mean u): is drift driven by a few batches?
bt = pd.DataFrame([dict(c=clus(x), y=pd.Timestamp(x['t'] * 864e11).year, u=x['u']) for x in toks if not np.isnan(x['u'])]).groupby(['c', 'y']).u.mean().reset_index()
R['civic_batchCollapsed_by_year'] = {str(y): {'deciderDays': int(len(g)), 'meanU': round(g.u.mean(), 3), 'newest10': round((g.u <= .1).mean(), 3)} for y, g in bt.groupby('y')}
# age at decision: share of decisions on items aged < 30 d (fast lane)
R['civic_share_decisions_age_lt30d_by_year'] = {str(y): round(float(np.mean([x['ageD'] < 30 for x in g])), 3) for y, g in pd.Series(toks).groupby([pd.Timestamp(x['t'] * 864e11).year for x in toks])}
R['civic_changepoints_all'] = changepoints(toks, 'civic')
E19 = pd.Timestamp('2019-01-01').value / 864e11
R['civic_excl_selfWithdrawal_by_year'] = summarize([x for x in toks if x['out'] != 'WDR'], clus=clus)
R['civic_crossOrg_ACC_by_year'] = summarize([x for x in toks if x['out'] == 'ACC' and (x['sameOrg'] is not None and not x['sameOrg'])], clus=clus)
R['civic_share_sameOrg_by_year'] = {str(y): round(float(np.mean([bool(x['sameOrg']) for x in g if x['sameOrg'] is not None])), 3) for y, g in pd.Series(toks).groupby([pd.Timestamp(x['t'] * 864e11).year for x in toks])}
R['civic_changepoints_crossOrg_nonWDR'] = changepoints([x for x in toks if x['out'] != 'WDR' and (x['sameOrg'] is not None and not x['sameOrg'])], 'civic_cross')
pickle.dump([{k: v for k, v in x.items() if k != 'null'} for x in toks], open(os.path.join(BASE, 'civic_tokens.pkl'), 'wb'))
# live-only queue: item had activity (incl. its own submission) in the 365 (and 90) days before t
# activity events (incl. submission) swept in time order -> lastAct[i] = latest activity <= t
EVT = sorted([(a, i) for i, a in enumerate(it.arr.values)] + [(t, i) for i, ts in enumerate(it.act_t) for t in ts])
EVt = np.array([e[0] for e in EVT]); EVi = np.array([e[1] for e in EVT])
def make_live(w):
    st = {'k': 0, 'last': np.full(len(it), -1e9)}
    def f(qidx, t):
        k = st['k']; k2 = np.searchsorted(EVt, t, 'right')
        if k2 > k: st['last'][EVi[k:k2]] = np.maximum(st['last'][EVi[k:k2]], EVt[k:k2]); st['k'] = k2
        return st['last'][qidx] > t - w
    return f
for w in (365, 90):
    lt = tokens_u(it[['id', 'arr', 'dec']], live_fn=make_live(w))
    for x in lt: r = it.iloc[x['i']]; x.update(decU=r.decU, day=int(np.floor(x['t'])), out=r.out, sameOrg=(r.decOrg == r.subOrg) if r.decOrg == r.decOrg and r.subOrg == r.subOrg else None)
    R[f'civic_live{w}_crossOrg_nonWDR_by_year'] = summarize([x for x in lt if x['out'] != 'WDR' and (x['sameOrg'] is not None and not x['sameOrg'])], clus=clus)
    R[f'civic_live{w}_crossOrg_nonWDR_2021plus'] = summarize([x for x in lt if x['out'] != 'WDR' and (x['sameOrg'] is not None and not x['sameOrg']) and x['t'] >= pd.Timestamp('2021-01-01').value / 864e11], key=lambda x: '2021+', clus=clus)
    R[f'civic_live{w}_by_year'] = summarize(lt, clus=clus)
    R[f'civic_live{w}_2021plus'] = summarize([x for x in lt if x['t'] >= pd.Timestamp('2021-01-01').value / 864e11], key=lambda x: '2021+', clus=clus)
    R[f'civic_live{w}_share_decisions_on_live_items_by_year'] = {str(y): round(float(np.mean([x['chosen_live'] for x in g])), 3) for y, g in pd.Series(lt).groupby([pd.Timestamp(x['t'] * 864e11).year for x in lt])}
    R[f'civic_live{w}_queue_median_L_by_year'] = {str(y): int(np.median([x['L'] for x in g])) for y, g in pd.Series(lt).groupby([pd.Timestamp(x['t'] * 864e11).year for x in lt])}
    if w == 365: R['civic_live365_changepoints'] = changepoints(lt, 'civic_live')
    print('live', w, 'done', flush=True)

# ---------------- GO / HPO / Wikidata
NOWgh = pd.Timestamp('2026-10-07T00:00:00Z').value / 864e11
for tag in ('go', 'hpo'):
    o = list(json.load(open(os.path.join(K4, f'issues_{tag}.json'), encoding='utf-8')).values())
    cs = pd.DataFrame([dict(id=x['n'], arr=pd.Timestamp(x['c']).value / 864e11, dec=(pd.Timestamp(x['x']).value / 864e11 if x['s'] == 'closed' else np.nan), decU=(x['asg'][0] if x['s'] == 'closed' and x['asg'] else 'na')) for x in o if x['c'] >= '2016'])
    cs = cs.sort_values(['arr', 'id']).reset_index(drop=True)
    tk = tokens_u(cs[['id', 'arr', 'dec']])
    for x in tk: x.update(decU=cs.decU.iloc[x['i']], day=int(np.floor(x['t'])))
    R[f'{tag}_by_year'] = summarize(tk, clus=clus); R[f'{tag}_overall'] = summarize(tk, key=lambda x: 'all', clus=clus)
    R[f'{tag}_changepoints'] = changepoints(tk, tag)
    print(tag, 'done', flush=True)
raw = json.load(open(os.path.join(K4, 'wd_cases.json'), encoding='utf-8'))
cs = pd.DataFrame([dict(id=i, arr=x['arr'] / 864e5, dec=(np.nan if x['kind'] == 'pending' else x['dec'] / 864e5), decU=x.get('decU') or 'na') for i, x in enumerate(raw)
                   if x.get('arr') and x['arr'] >= pd.Timestamp('2016-01-01').value / 1e6 and (x['kind'] == 'pending' or x.get('dec') is not None)])
cs = cs.sort_values(['arr', 'id']).reset_index(drop=True)
tk = tokens_u(cs[['id', 'arr', 'dec']])
for x in tk: x.update(decU=cs.decU.iloc[x['i']], day=int(np.floor(x['t'])))
R['wd_sample_by_year'] = summarize(tk, clus=clus); R['wd_sample_overall'] = summarize(tk, key=lambda x: 'all', clus=clus)
R['wd_note'] = 'Wikidata is a ~15% alphabetical-window sample: queue positions are computed within the sample only (relative position preserved in expectation under random sampling).'
json.dump(R, open(os.path.join(BASE, 'res_a4_discipline.json'), 'w'), indent=1, default=str)
print('done')
