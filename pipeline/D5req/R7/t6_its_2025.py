# R7 task 6: (a) interrupted time series for the April 2025 reason requirement (evidence items), with pre-trend, level and
# slope change, comparative ITS against revisions; inference by HAC (Newey-West, 3 lags) and by PRE-TREATMENT placebo
# breaks only. (b) Wild cluster bootstrap (Webb six-point weights, moderator clusters) for the decision-intensity ratio
# 2016-18 / 2023-26 on the common activity set A*. Aggregates only; cluster counts as bands.
import os, json, numpy as np, pandas as pd, statsmodels.api as sm
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..')
PN = pd.read_pickle(os.path.join(R, 'R3_causal', 'panel.pkl'))
WIN = ('2022-05', '2026-09'); T0 = pd.Period('2025-04', 'M'); MINSIDE = 6
def series(key):
    s = PN[key].loc[WIN[0]:WIN[1]]; return s[s.n_other_dec > 0]
def design(idx, t0):
    t = np.array([(p - idx[0]).n for p in idx], float); post = np.array([p >= t0 for p in idx], float)
    ts = np.array([(p - t0).n for p in idx], float) * post
    return np.column_stack([np.ones(len(idx)), t, post, ts])
def its(S, t0, fam=True):
    X = design(S.index, t0); y = S.rej.values / S.n_other_dec.values
    m = sm.GLM(np.column_stack([S.rej.values, S.n_other_dec.values - S.rej.values]), X, family=sm.families.Binomial()).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
    return m
def comparative(T, C, t0):
    idx = T.index.intersection(C.index); T, C = T.loc[idx], C.loc[idx]
    X0 = design(idx, t0); n = len(idx)
    X = np.vstack([np.column_stack([X0, X0 * 1.0]), np.column_stack([X0, X0 * 0.0])])  # treated rows get group interactions
    Y = np.concatenate([np.column_stack([T.rej, T.n_other_dec - T.rej]), np.column_stack([C.rej, C.n_other_dec - C.rej])])
    return sm.GLM(Y, X, family=sm.families.Binomial()).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
T, C = series('EID'), series('REV')
out = {'window': WIN, 'T0': str(T0), 'months_treated': int(len(T)), 'outcome': 'rejection share of decisions on other users items (monthly, binomial GLM, logit link)'}
m = its(T, T0)
names = ['intercept', 'pre_trend_per_month', 'level_change', 'slope_change_per_month']
out['ITS_treated'] = {k: {'coef_logit': round(float(m.params[i]), 4), 'ci95': [round(float(x), 4) for x in m.conf_int()[i]], 'p_HAC': round(float(m.pvalues[i]), 4)} for i, k in enumerate(names)}
mc = comparative(T, C, T0)
cn = names + ['treated_' + k for k in names]
out['comparative_ITS'] = {k: {'coef_logit': round(float(mc.params[i]), 4), 'ci95': [round(float(x), 4) for x in mc.conf_int()[i]], 'p_HAC': round(float(mc.pvalues[i]), 4)} for i, k in enumerate(cn) if k.startswith('treated_')}
# pre-treatment placebos: fit the same model on pre-period data only, with fake breaks leaving >= MINSIDE months each side
pre_T = T[T.index < T0]; pre_C = C[C.index < T0]
cands = [p for k, p in enumerate(pre_T.index) if k >= MINSIDE and len(pre_T) - k >= MINSIDE]
pl_lvl, pl_cmp = [], []
for p in cands:
    try:
        pl_lvl.append(float(its(pre_T, p).params[2])); pl_cmp.append(float(comparative(pre_T, pre_C, p).params[6]))
    except Exception: pass
def pp(obs, pl):
    pl = np.array(pl); return {'observed': round(obs, 4), 'n_placebos': int(len(pl)), 'placebo_range': [round(float(pl.min()), 4), round(float(pl.max()), 4)],
                               'p_placebo_two_sided': round(float((np.abs(pl) >= abs(obs)).mean()), 3) if len(pl) else None}
out['pre_treatment_placebos_level_change'] = {'treated_ITS': pp(float(m.params[2]), pl_lvl), 'comparative_ITS': pp(float(mc.params[6]), pl_cmp)}
# raw descriptive: fitted counterfactual vs observed mean share after T0
Xc = design(T.index, T0); Xc0 = Xc.copy(); Xc0[:, 2:] = 0
post = np.array([p >= T0 for p in T.index])
out['treated_post_mean_observed_vs_counterfactual'] = [round(float((T.rej / T.n_other_dec)[post].mean()), 4), round(float(m.predict(Xc0)[post].mean()), 4)]
# ---------------- (b) wild cluster bootstrap for the intensity ratio
E = pd.read_pickle(os.path.join(R, 'W3', 'w3_events_hmac.pkl')); Hh = E[~E.bot].copy(); Hh['day'] = np.floor(Hh.t).astype(int)
V2 = pd.Timestamp('2022-04-09', tz='UTC').value / 864e11
cnt = Hh.groupby(['act', Hh.t >= V2]).size().unstack(fill_value=0)
COMMON = sorted(set(cnt.index[(cnt[False] > 0) & (cnt[True] > 0)]) - {'COMPLEX_MOLECULAR_PROFILE_CREATED'})
mod = Hh[Hh.modAt & Hh.act.isin(COMMON)].copy()
mod['ev'] = (mod.act.isin(['ACCEPTED', 'REJECTED']) & (mod.st == 'EvidenceItem') & (mod.u != mod.evSub)).astype(int)
D = mod.groupby(['u', 'day'])[['ev']].sum().reset_index(); D['year'] = pd.to_datetime(D.day * 864e11).dt.year
D['p'] = np.where(D.year.between(2016, 2018), 0, np.where(D.year.between(2023, 2026), 1, -1)); D = D[D.p >= 0]
A = D.groupby(['u', 'p']).agg(d=('ev', 'sum'), a=('ev', 'size')).unstack(fill_value=0)
d0, a0, d1, a1 = A[('d', 0)].values, A[('a', 0)].values, A[('d', 1)].values, A[('a', 1)].values
I0, I1 = d0.sum() / a0.sum(), d1.sum() / a1.sum(); theta = np.log(I0 / I1)
psi = (d0 - I0 * a0) / a0.sum() / I0 - (d1 - I1 * a1) / a1.sum() / I1   # linearised contribution of each moderator to log fold
rng = np.random.default_rng(20261007); WEBB = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)])
bs = theta + rng.choice(WEBB, (9999, len(psi))) @ psi
G = len(psi)
# pairs cluster bootstrap for comparison
pb = []
for _ in range(4999):
    s = rng.integers(0, G, G)
    if a0[s].sum() and a1[s].sum() and d1[s].sum(): pb.append(np.log((d0[s].sum() / a0[s].sum()) / (d1[s].sum() / a1[s].sum())))
out['intensity_ratio'] = {'intensity_2016_18': round(float(I0), 3), 'intensity_2023_26': round(float(I1), 3), 'fold': round(float(np.exp(theta)), 3),
                          'wild_cluster_bootstrap_webb_95': [round(float(np.exp(np.percentile(bs, 2.5))), 2), round(float(np.exp(np.percentile(bs, 97.5))), 2)],
                          'pairs_cluster_bootstrap_95': [round(float(np.exp(np.percentile(pb, 2.5))), 2), round(float(np.exp(np.percentile(pb, 97.5))), 2)],
                          'clusters_band': '20-49' if 20 <= G < 50 else ('50-99' if 50 <= G < 100 else ('>=100' if G >= 100 else '<20')),
                          'share_of_both_periods_days_from_top_cluster_band': 'not reported (individual)'}
json.dump(out, open(os.path.join(H, 'res_t6_its.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps(out, indent=1))
