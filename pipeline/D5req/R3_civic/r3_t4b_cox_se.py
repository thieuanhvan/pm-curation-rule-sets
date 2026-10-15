# R3 T4b: Cox refits of r3_t4_survival.py with finite standard errors (robust if available, else model-based).
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
    r = m.fit()
    try:
        rr = m.fit(groups=pd.factorize(df.subU)[0])
        if np.all(np.isfinite(rr.bse)): r = rr; R.setdefault('se_type', []).append('robust_cluster_submitter')
        else: R.setdefault('se_type', []).append('model_based(robust failed)')
    except Exception as e: R.setdefault('se_type', []).append('model_based(robust error)')
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
R['b_pem_gamma_frailty_submitter_year_dummies'] = json.load(open('res_r3_t4.json'))['b_pem_gamma_frailty_submitter_year_dummies']
json.dump(R, open('res_r3_t4.json', 'w'), indent=1); print(json.dumps(R))
