# A2 step 2b: do flags / comments / revisions change time-to-decision (TTD) of CIViC evidence items?
# (i) naive "ever-exposed" comparison among decided items (two-timestamp style, biased), (ii) Cox PH with time-varying exposures
# (counting process, statsmodels PHReg), all-cause and cause-specific (accept / reject), (iii) landmark Aalen-Johansen CIFs, bootstrap CIs.
import json, sys, numpy as np, pandas as pd
from statsmodels.duration.hazard_regression import PHReg
OUT = 'out/'; RES = {}; rng = np.random.default_rng(20261007)
def P(k, v): RES[k] = v; print(k, json.dumps(v, default=str)[:1200])
mode = sys.argv[1] if len(sys.argv) > 1 else 'excl'
cl = pd.read_pickle(OUT + f'caselog_ei_{mode}.pkl')
meta = {m['id']: m for m in json.load(open('../../D5b/meta_evidence.json', encoding='utf-8'))}
NOW = pd.Timestamp('2026-10-07T00:00:00Z'); D = 86400.0
rows = []
for k, g in cl.groupby('case:concept:name', sort=False):
    a = g['concept:name'].values; t = g['time:timestamp'].values
    s = np.where(a == 'SUBMITTED')[0]
    if not len(s): continue
    t0 = pd.Timestamp(t[s[0]]).tz_localize('UTC') if pd.Timestamp(t[s[0]]).tzinfo is None else pd.Timestamp(t[s[0]])
    dd = np.where((a == 'ACCEPTED') | (a == 'REJECTED'))[0]
    if len(dd):
        td = pd.Timestamp(t[dd[0]]); td = td.tz_localize('UTC') if td.tzinfo is None else td
        T = max((td - t0).total_seconds() / D, 0.0); ev = 1 if a[dd[0]] == 'ACCEPTED' else 2
    else: T = (NOW - t0).total_seconds() / D; ev = 0
    def onset(names):
        ii = np.where(np.isin(a, names))[0]
        if not len(ii): return np.inf
        x = pd.Timestamp(t[ii[0]]); x = x.tz_localize('UTC') if x.tzinfo is None else x
        return max((x - t0).total_seconds() / D, 0.0)
    m = meta.get(int(k.split(':')[1]), {})
    rows.append({'id': k, 'T': T, 'ev': ev, 'year': t0.year, 'lvl': m.get('evidenceLevel'), 'typ': m.get('evidenceType'),
                 'flag': onset(['FLAGGED']), 'comment': onset(['COMMENTED', 'REVISION_COMMENTED']), 'revision': onset(['REVISION_SUGGESTED'])})
df = pd.DataFrame(rows)
df['era'] = pd.cut(df['year'], [2014, 2016, 2019, 2022, 2027], labels=['2015-16', '2017-19', '2020-22', '2023-26']).astype(str)
X = ['flag', 'comment', 'revision']
P('cohort', {'mode': mode, 'n': len(df), 'accepted': int((df.ev == 1).sum()), 'rejected': int((df.ev == 2).sum()), 'pending': int((df.ev == 0).sum()),
             'exposed_before_decision_or_censoring': {x: round(float((df[x] < df['T']).mean()), 4) for x in X},
             'exposed_at_time0': {x: int((df[x] == 0).sum()) for x in X}})

# (i) naive comparison: decided items, ever exposed before decision vs never; median TTD diff with bootstrap CI
naive = {}
dec = df[df.ev > 0]
for x in X:
    e = dec[dec[x] < dec['T']]['T'].values; n = dec[~(dec[x] < dec['T'])]['T'].values
    bs = [np.median(rng.choice(e, len(e))) - np.median(rng.choice(n, len(n))) for _ in range(1000)]
    naive[x] = {'n_exposed': len(e), 'med_exposed': round(float(np.median(e)), 1), 'n_unexposed': len(n), 'med_unexposed': round(float(np.median(n)), 1),
                'diff_med_days': round(float(np.median(e) - np.median(n)), 1), 'ci95': [round(float(np.percentile(bs, 2.5)), 1), round(float(np.percentile(bs, 97.5)), 1)]}
P('naive_decided_only_median_ttd', naive)

# (ii) counting-process data: split at exposure onsets (exposure starts LAG days after onset; LAG from argv[2])
LAG = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
for x in X: df[x] = df[x] + LAG
RES['lag_days'] = LAG
EPS = 1e-3; cp = []
for r in df.itertuples():
    cuts = sorted({0.0, r.T} | {getattr(r, x) for x in X if 0 < getattr(r, x) < r.T})
    for i in range(len(cuts) - 1):
        s0, s1 = cuts[i], cuts[i + 1]
        cp.append({'id': r.id, 'start': s0, 'stop': max(s1, s0 + EPS), 'acc': int(r.ev == 1 and s1 == r.T), 'rej': int(r.ev == 2 and s1 == r.T),
                   **{x: int(getattr(r, x) <= s0) for x in X}, 'lvl': r.lvl, 'typ': r.typ, 'era': r.era})
    if len(cuts) == 1:  # T == 0
        cp.append({'id': r.id, 'start': 0.0, 'stop': EPS, 'acc': int(r.ev == 1), 'rej': int(r.ev == 2), **{x: int(getattr(r, x) <= 0) for x in X}, 'lvl': r.lvl, 'typ': r.typ, 'era': r.era})
cp = pd.DataFrame(cp); cp['any'] = cp['acc'] | cp['rej']
dm = pd.get_dummies(cp[['lvl', 'typ']].fillna('NA'), drop_first=True).astype(float)
Z = pd.concat([cp[X].astype(float), dm], axis=1)
cox = {}
for out in ['any', 'acc', 'rej']:
    m = PHReg(cp['stop'].values, Z.values, status=cp[out].values, entry=cp['start'].values, strata=cp['era'].values, ties='efron').fit()
    ci = m.conf_int()
    cox[out] = {x: {'HR': round(float(np.exp(m.params[i])), 3), 'ci95': [round(float(np.exp(ci[i, 0])), 3), round(float(np.exp(ci[i, 1])), 3)], 'p': float(f'{m.pvalues[i]:.2g}')} for i, x in enumerate(X)}
    cox[out]['events'] = int(cp[out].sum())
P('cox_time_varying_strata_era_adj_level_type', cox)
m = PHReg(cp['stop'].values, cp[X].values.astype(float), status=cp['rej'].values, entry=cp['start'].values, strata=cp['era'].values, ties='breslow').fit(); ci = m.conf_int()
P('cox_rej_strata_era_no_level_type', {x: {'HR': round(float(np.exp(m.params[i])), 3), 'ci95': [round(float(np.exp(ci[i, 0])), 3), round(float(np.exp(ci[i, 1])), 3)]} for i, x in enumerate(X)})
# sensitivity: unadjusted, no strata
m = PHReg(cp['stop'].values, cp[X].values.astype(float), status=cp['any'].values, entry=cp['start'].values, ties='efron').fit(); ci = m.conf_int()
P('cox_any_unadjusted', {x: {'HR': round(float(np.exp(m.params[i])), 3), 'ci95': [round(float(np.exp(ci[i, 0])), 3), round(float(np.exp(ci[i, 1])), 3)]} for i, x in enumerate(X)})
# sensitivity: post-2019 submissions only
sub = cp[cp['era'].isin(['2020-22', '2023-26'])]; Zs = Z.loc[sub.index]
m = PHReg(sub['stop'].values, Zs.values, status=sub['any'].values, entry=sub['start'].values, strata=sub['era'].values, ties='efron').fit(); ci = m.conf_int()
P('cox_any_2020plus', {x: {'HR': round(float(np.exp(m.params[i])), 3), 'ci95': [round(float(np.exp(ci[i, 0])), 3), round(float(np.exp(ci[i, 1])), 3)]} for i, x in enumerate(X)} | {'n_items': int(sub['id'].nunique()), 'events': int(sub['any'].sum())})

# (iii) landmark Aalen-Johansen: among items pending at L, exposed by L vs not; CIF of accept / reject within H days after L
def aj(T, E, H):
    o = np.argsort(T); T, E = T[o], E[o]; n = len(T); S = 1.0; F = {1: 0.0, 2: 0.0}; i = 0
    while i < n and T[i] <= H:
        j = i; d = {0: 0, 1: 0, 2: 0}
        while j < n and T[j] == T[i]: d[E[j]] += 1; j += 1
        at = n - i
        for k in (1, 2): F[k] += S * d[k] / at
        S *= 1 - (d[1] + d[2]) / at; i = j
    return F[1], F[2]
for x in X: df[x] = df[x] - LAG
lm = {}
for L in (30, 180):
    base = df[df['T'] > L].copy(); base['Tl'] = base['T'] - L
    for x in X:
        g1 = base[base[x] <= L]; g0 = base[base[x] > L]; res = {}
        for nm, g in (('exposed', g1), ('unexposed', g0)):
            T, E = g['Tl'].values, g['ev'].values; a, r = aj(T, E, 365)
            bs = np.array([aj(T[ii], E[ii], 365) for ii in (rng.integers(0, len(T), len(T)) for _ in range(300))])
            res[nm] = {'n': len(g), 'CIF_acc_1y': [round(a, 3), round(float(np.percentile(bs[:, 0], 2.5)), 3), round(float(np.percentile(bs[:, 0], 97.5)), 3)],
                       'CIF_rej_1y': [round(r, 3), round(float(np.percentile(bs[:, 1], 2.5)), 3), round(float(np.percentile(bs[:, 1], 97.5)), 3)]}
        lm[f'L{L}_{x}'] = res
P('landmark_AJ_CIF_1y', lm)
json.dump(RES, open(OUT + f'ttd_{mode}_lag{int(LAG)}.json', 'w'), indent=1, default=str)
