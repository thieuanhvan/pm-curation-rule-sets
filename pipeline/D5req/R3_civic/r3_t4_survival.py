# R3 T4: age dependence of the acceptance hazard for items >= 1 year old, refitted without the FE + frailty combination.
# (a) Cox stratified by submitter, calendar time as time scale (left-truncated episodes), age as time-varying covariate;
# (b) PEM with submitter-level shared gamma frailty (no FE), year dummies; (c) APC check: Cox on calendar time with
#     arrival-cohort bins (2-year) instead of strata. Input ../A3/civic_pem_hmac.pkl (episode-split, 91-day pieces after age 1 y).
import json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
from statsmodels.duration.hazard_regression import PHReg
from scipy.optimize import minimize
from scipy.special import gammaln, digamma
warnings.filterwarnings('ignore')
P = pd.read_pickle('../A3/civic_pem_hmac.pkl'); P1 = P[P.age0 >= 365].copy().reset_index(drop=True)
P1['ageY'] = (P1.age0 + P1.expo / 2) / 365.25          # age at piece midpoint
P1['entry'] = P1.t0; P1['exit'] = P1.t0 + P1.expo
P1['cohort'] = pd.to_datetime(P1.arr, unit='D').dt.year
P1['coh2'] = ((P1.cohort - 2015) // 2).astype(int)
def items(df):
    return pd.concat([pd.get_dummies(df.level, prefix='lvl', dtype=float).drop(columns='lvl_A', errors='ignore'),
                      pd.get_dummies(df.rating.astype(str), prefix='rat', dtype=float).drop(columns='rat_3', errors='ignore'),
                      pd.get_dummies(df.etype, prefix='typ', dtype=float).drop(columns='typ_PREDICTIVE', errors='ignore'),
                      df[['lrev', 'lcom', 'anyflag', 'live365', 'subActive365']].astype(float)], axis=1)
R = {'n_pieces': len(P1), 'items': int(P1.id.nunique()), 'acceptances': int(P1.eACC.sum()), 'submitters': int(P1.subU.nunique()),
     'submitters_with_>=1_acceptance_after_1y': int((P1.groupby('subU').eACC.sum() > 0).sum())}
def hr(res, names, k='ageY'):
    i = names.index(k); b = res.params[i]; se = res.bse[i]
    return [round(float(np.exp(b)), 3), round(float(np.exp(b - 1.96 * se)), 3), round(float(np.exp(b + 1.96 * se)), 3)]
def cox(df, X, strata=None):
    X = X.loc[:, X.std() > 0]
    m = PHReg(df.exit.values, X.values, status=df.eACC.values, entry=df.entry.values, strata=strata, ties='breslow')
    r = m.fit(groups=pd.factorize(df.subU)[0])  # robust SE clustered by submitter
    return r, list(X.columns)
X = items(P1); X['ageY'] = P1.ageY
r, nm = cox(P1, X, strata=P1.subU.values); R['a_cox_calendar_scale_strata_submitter'] = {'HR_per_year_of_age': hr(r, nm), 'note': 'baseline hazard per submitter over calendar time absorbs period x submitter'}
r, nm = cox(P1, X); R['a0_cox_calendar_scale_no_strata'] = {'HR_per_year_of_age': hr(r, nm)}
Xc = pd.concat([X, pd.get_dummies(P1.coh2, prefix='coh', dtype=float).iloc[:, 1:]], axis=1)
r, nm = cox(P1, Xc); R['c_apc_cox_calendar_scale_cohort2y_bins'] = {'HR_per_year_of_age': hr(r, nm), 'note': 'age identified from within-bin variation; constraint: no cohort effect within a 2-year arrival bin'}
r, nm = cox(P1, Xc, strata=P1.subU.values); R['c2_apc_strata_submitter_plus_cohort2y'] = {'HR_per_year_of_age': hr(r, nm)}
# live-only (activity in the preceding 365 days)
L = P1[P1.live365 == 1].reset_index(drop=True); XL = items(L).drop(columns='live365'); XL['ageY'] = L.ageY
try:
    r, nm = cox(L, XL, strata=L.subU.values); R['a_live_only_strata_submitter'] = {'HR_per_year_of_age': hr(r, nm), 'events': int(L.eACC.sum())}
except Exception as e: R['a_live_only_strata_submitter'] = {'error': str(e)[:200]}
# (b) PEM with submitter-level shared gamma frailty, year dummies, no fixed effects
Z = pd.concat([items(P1), pd.get_dummies(P1.year, prefix='yr', dtype=float).iloc[:, 1:]], axis=1); Z['ageY'] = P1.ageY
Z = Z.loc[:, Z.std() > 0].assign(const=1.0); names = list(Z.columns)
Xv = Z.values.astype(float); y = P1.eACC.values.astype(float); lo = np.log(P1.expo.values)
g = pd.factorize(P1.subU)[0]; G = g.max() + 1; Dg = np.bincount(g, y, G)
def nll(p):
    b, th = p[:-1], np.exp(p[-1]); eta = Xv @ b; w = np.exp(eta + lo); Hg = np.bincount(g, w, G); a = 1 / th
    ll = (y * eta).sum() + (gammaln(a + Dg) - gammaln(a) - Dg * np.log(a) - (a + Dg) * np.log1p(th * Hg)).sum()
    fac = (a + Dg) * th / (1 + th * Hg); gb = Xv.T @ y - Xv.T @ (w * fac[g])
    dA = (digamma(a + Dg) - digamma(a) - Dg / a - np.log1p(th * Hg) + (a + Dg) * 0).sum()   # d/da of terms except last-term th-dependence
    # derivative wrt log theta: d/dth = dA * (-1/th^2) + d/dth[-(a+Dg) log(1+th H)] holding a: -(a+Dg) H/(1+th H)
    dth = dA * (-1 / th ** 2) + (np.log1p(th * Hg) / th ** 2).sum() * 0 - ((a + Dg) * Hg / (1 + th * Hg)).sum()
    return -ll, -np.append(gb, dth * th)
r0 = sm.GLM(y, Xv, family=sm.families.Poisson(), offset=lo).fit()
opt = minimize(lambda p: nll(p)[0], np.append(r0.params, np.log(0.5)), method='L-BFGS-B', options={'maxiter': 5000})
# numerical Hessian (finite differences of the objective) for ageY and log-theta
def num_se(x, idxs, eps=1e-4):
    f = lambda v: nll(v)[0]; Hm = np.zeros((len(x), len(x)))
    gr = lambda v: np.array([(f(v + e) - f(v - e)) / (2 * eps) for e in np.eye(len(x)) * eps])
    for i in range(len(x)):
        e = np.zeros(len(x)); e[i] = eps; Hm[:, i] = (gr(x + e) - gr(x - e)) / (2 * eps)
    C = np.linalg.pinv((Hm + Hm.T) / 2); return {i: float(np.sqrt(max(C[i, i], 0))) for i in idxs}
ia = names.index('ageY'); se = num_se(opt.x, [ia, len(opt.x) - 1])
b = opt.x[ia]
R['b_pem_gamma_frailty_submitter_year_dummies'] = {'converged': bool(opt.success), 'HR_per_year_of_age': [round(float(np.exp(b)), 3), round(float(np.exp(b - 1.96 * se[ia])), 3), round(float(np.exp(b + 1.96 * se[ia])), 3)],
    'theta': round(float(np.exp(opt.x[-1])), 3), 'loglik': round(float(-opt.fun), 1), 'loglik_poisson_same_X': round(float(r0.llf), 1),
    'poisson_no_frailty_HR': round(float(np.exp(r0.params[ia])), 3)}
json.dump(R, open('res_r3_t4.json', 'w'), indent=1); print(json.dumps(R, indent=1))
