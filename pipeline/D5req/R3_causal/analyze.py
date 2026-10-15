# R3_causal: ITS (segmented regression, Newey-West) + DiD on the treated-minus-control difference series
# + event study (quarter bins) + placebo dates + falsification outcome, for three enforcement dates.
import os, json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings('ignore')
B = os.path.dirname(os.path.abspath(__file__))
PN = pd.read_pickle(os.path.join(B, 'panel.pkl'))
HAC = dict(cov_type='HAC', cov_kwds={'maxlags': 6})
OUT = {}

EVENTS = {
    # T0 = first full post month. Dates verified from repository history (see notes.md).
    'E2016_no_self_accept': dict(T0='2016-08', win=('2015-07', '2018-12'), drop=[], treated=['EID', 'REV'], control=None),
    'E2022_rev_reason': dict(T0='2022-05', win=('2019-02', '2024-12'), drop=['2022-04'], treated='REV', control='EID'),
    'E2025_eid_reason': dict(T0='2025-04', win=('2023-09', '2026-09'), drop=[], treated='EID', control='REV'),
}
SHARE = ['rej_share', 'wd_share', 'wdsup_share', 'log_ttd', 'stock_growth', 'rej_per_md', 'acc_per_md']
COUNT = ['rej', 'acc_other']  # Poisson with log(moderator-days) offset
FALS = 'log_arr'

def design(idx, T0, seas=True):
    t = np.arange(len(idx), dtype=float)
    post = (idx >= pd.Period(T0, 'M')).astype(float)
    k0 = np.argmax(post) if post.any() else len(idx)
    X = pd.DataFrame({'const': 1.0, 't': t, 'post': post, 't_post': post * (t - k0)}, index=idx)
    if seas:
        moy = pd.get_dummies(pd.Series(idx.month, index=idx), prefix='m', drop_first=True).astype(float)
        X = X.join(moy)
    return X

def fit_ols(y, X):
    ok = y.notna(); r = sm.OLS(y[ok], X[ok]).fit(**HAC)
    ci = r.conf_int()
    return {k: [round(float(r.params[k]), 4), round(float(ci.loc[k, 0]), 4), round(float(ci.loc[k, 1]), 4), round(float(r.pvalues[k]), 4)] for k in ('post', 't_post') if k in r.params} | {'n': int(ok.sum())}

def fit_pois(y, X, md):
    ok = md > 0
    r = sm.GLM(y[ok], X[ok], family=sm.families.Poisson(), offset=np.log(md[ok])).fit(**HAC)
    ci = r.conf_int()
    # Pearson dispersion reported; HAC SEs are robust to overdispersion
    return {k: [round(float(np.exp(r.params[k])), 4), round(float(np.exp(ci.loc[k, 0])), 4), round(float(np.exp(ci.loc[k, 1])), 4), round(float(r.pvalues[k]), 4)] for k in ('post', 't_post')} | {'n': int(ok.sum()), 'scale': 'IRR', 'dispersion': round(float(r.pearson_chi2 / r.df_resid), 2)}

def window(P, ev):
    s = P.loc[ev['win'][0]:ev['win'][1]]
    return s.drop([pd.Period(d, 'M') for d in ev['drop'] if pd.Period(d, 'M') in s.index])

def diff_series(ev, col):
    T, C = window(PN[ev['treated']], ev), window(PN[ev['control']], ev)
    if col in ('rej', 'acc_other'):  # log count ratio (pooled exposure cancels)
        return np.log(T[col] + 0.5) - np.log(C[col] + 0.5)
    return T[col] - C[col]

def event_study(d, T0, lo=-8, hi=8):
    idx = d.index; rel = np.array([(p - pd.Period(T0, 'M')).n for p in idx]); q = np.floor(rel / 3).astype(int)
    q = np.clip(q, lo, hi)
    X = pd.DataFrame({'const': 1.0}, index=idx)
    for b in range(lo, hi + 1):
        if b == -1: continue
        X[f'q{b}'] = (q == b).astype(float)
    X = X.loc[:, (X != 0).any()]
    ok = d.notna(); r = sm.OLS(d[ok], X[ok]).fit(**HAC); ci = r.conf_int()
    coefs = {c: [round(float(r.params[c]), 4), round(float(ci.loc[c, 0]), 4), round(float(ci.loc[c, 1]), 4)] for c in X.columns if c != 'const'}
    leads = [c for c in X.columns if c.startswith('q-')]
    r1 = sm.OLS(d[ok], X[ok]).fit(cov_type='HC1')
    w = r1.wald_test(np.eye(len(r1.params))[[list(X.columns).index(c) for c in leads]], scalar=True) if leads else None
    pre = d[(d.index < pd.Period(T0, 'M')) & d.notna()]
    rs = sm.OLS(pre, sm.add_constant(np.arange(len(pre), dtype=float))).fit(**HAC)
    return {'coefs': coefs, 'pretrend_joint_leads_HC1_F_p': [round(float(w.statistic), 3), round(float(w.pvalue), 4)] if w is not None else None,
            'pre_slope_per_month_HAC': [round(float(rs.params.iloc[1]), 4), round(float(rs.conf_int().iloc[1, 0]), 4), round(float(rs.conf_int().iloc[1, 1]), 4), round(float(rs.pvalues.iloc[1]), 4)],
            'note': 'bins at -8/+8 pool endpoints; ref q-1; joint lead test uses HC1 because HAC on 3-month dummies is anti-conservative'}

def ri_rank(d, ev, est):
    # in-time randomisation inference: level-change estimate at every fake date with >= 6 months each side,
    # using pre-only data for fake dates before T0 and post-only data after; share of |fake| >= |true|
    T0 = pd.Period(ev['T0'], 'M'); fakes = []
    for side in (d[d.index < T0], d[d.index >= T0]):
        side = side.dropna()
        for k in range(6, len(side) - 6 + 1):
            P0 = side.index[k]
            try: fakes.append(fit_ols(side, design(side.index, str(P0), seas=False))['post'][0])
            except Exception: pass
    fakes = np.abs(np.array(fakes))
    return {'n_fake': int(len(fakes)), 'p_rank': round(float((1 + (fakes >= abs(est)).sum()) / (1 + len(fakes))), 3) if len(fakes) else None}

def placebo(d, ev, shifts=(-12, -6, 6, 12)):
    T0 = pd.Period(ev['T0'], 'M'); res = {}
    for s in shifts:
        P0 = T0 + s
        sub = d[d.index < T0] if s < 0 else d[d.index >= T0]
        if (sub.index < P0).sum() < 6 or (sub.index >= P0).sum() < 6: res[s] = 'insufficient'; continue
        res[s] = fit_ols(sub, design(sub.index, str(P0), seas=False))['post']
    return res

for name, ev in EVENTS.items():
    R = {}
    if ev['control'] is None:
        for typ in ev['treated']:
            P = window(PN[typ], ev); X = design(P.index, ev['T0'])
            R[typ] = {c: fit_ols(P[c], X) for c in SHARE + [FALS]} | {c + '_pois': fit_pois(P[c], X, P.mdays) for c in COUNT}
            R[typ]['placebo_rej_share'] = placebo(P['rej_share'], ev); R[typ]['placebo_log_ttd'] = placebo(P['log_ttd'], ev)
            R[typ]['placebo_acc_per_md'] = placebo(P['acc_per_md'], ev)
    else:
        for role in ('treated', 'control'):
            P = window(PN[ev[role]], ev); X = design(P.index, ev['T0'])
            R['its_' + role] = {c: fit_ols(P[c], X) for c in SHARE + [FALS]} | {c + '_pois': fit_pois(P[c], X, P.mdays) for c in COUNT}
        R['did'] = {}; R['event_study'] = {}; R['placebo'] = {}
        for c in SHARE + COUNT + [FALS]:
            d = diff_series(ev, c); X = design(d.index, ev['T0'])
            R['did'][c] = fit_ols(d, X)
            Xl = design(d.index, ev['T0'], seas=True).drop(columns=['t_post'])  # level-only DiD with common differential trend
            R['did'][c + '_levelonly'] = fit_ols(d, Xl)['post']
            R['event_study'][c] = event_study(d, ev['T0'])
            R['placebo'][c] = placebo(d, ev)
            R['placebo'][c + '_ri'] = ri_rank(d, ev, R['did'][c]['post'][0])
        if name.startswith('E2022'):
            ev2 = dict(ev, win=(ev['win'][0], '2022-12'))  # before the Molecular Profile migration (Jan 2023)
            R['did_pre_MP_migration'] = {c: fit_ols(diff_series(ev2, c), design(diff_series(ev2, c).index, ev['T0'], seas=False)) for c in ['rej_share', 'wd_share', 'log_ttd', 'rej', 'acc_other']}
            ev3 = dict(ev, treated='REV_EID')
            R['did_rev_on_eid_only'] = {c: fit_ols(diff_series(ev3, c), design(diff_series(ev3, c).index, ev['T0'])) for c in ['rej_share', 'wd_share', 'log_ttd', 'rej', 'acc_other']}
    # descriptive pre/post means of treated type (reason quality etc.)
    typs = ev['treated'] if isinstance(ev['treated'], list) else [ev['treated'], ev['control']]
    R['prepost_means'] = {}
    for typ in typs:
        P = window(PN[typ], ev); post = P.index >= pd.Period(ev['T0'], 'M')
        R['prepost_means'][typ] = {c: [round(float(P.loc[~post, c].mean()), 3), round(float(P.loc[post, c].mean()), 3)] for c in
                                   ['rej_share', 'wd_share', 'sup_share', 'wdsup_share', 'ttd_med', 'stock_growth', 'rej_per_md', 'acc_per_md', 'rej_note_med', 'rej_reason_any', 'rej_nontempl', 'arr']} | \
                                  {'sum_rej_pre_post': [int(P.loc[~post, 'rej'].sum()), int(P.loc[post, 'rej'].sum())], 'sum_wd_pre_post': [int(P.loc[~post, 'wd'].sum()), int(P.loc[post, 'wd'].sum())],
                                   'months_pre_post': [int((~post).sum()), int(post.sum())], 'mdays_pre_post': [int(P.loc[~post, 'mdays'].sum()), int(P.loc[post, 'mdays'].sum())]}
    OUT[name] = R
    print('=====', name)
    print(json.dumps({k: v for k, v in R.items() if k != 'event_study'}, indent=None)[:6000])
    if 'event_study' in R:
        print('pretrend:', {c: (R['event_study'][c]['pretrend_joint_leads_HC1_F_p'], R['event_study'][c]['pre_slope_per_month_HAC']) for c in R['event_study']})
        print('RI:', {c: R['placebo'][c] for c in R['placebo'] if c.endswith('_ri')})

# minimum detectable effect (80 % power, alpha .05) for the DiD level change: 2.8 x SE
for name in ('E2022_rev_reason', 'E2025_eid_reason'):
    mde = {}
    for c in ('rej_share', 'wd_share', 'log_ttd', 'rej'):
        b, lo, hi, p = OUT[name]['did'][c]['post']; se = (hi - lo) / 3.92; mde[c] = round(2.8 * se, 3)
    OUT[name]['mde_level_change'] = mde
    print(name, 'MDE', mde)
json.dump(OUT, open(os.path.join(B, 'results_r3_causal.json'), 'w'), indent=1)
