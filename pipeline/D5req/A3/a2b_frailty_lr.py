# LR test for gamma frailty variance: compare frailty log-lik with the same continuous-time PEM log-lik at theta -> 0.
import os, json, numpy as np, pandas as pd, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'a2_hazard.py'), encoding='utf-8').read().split("R = {}")[0])
X = design(P, period='year', items=True, tv=True); X = X.loc[:, X.std() > 0].assign(const=1.0)
Xv = X.values.astype(float); y = P.eANY.values.astype(float); lo = np.log(P.expo.values)
r0 = sm.GLM(y, Xv, family=sm.families.Poisson(), offset=lo).fit()
eta = Xv @ r0.params; ll0 = (y * eta).sum() - np.exp(eta + lo).sum()
R = json.load(open(os.path.join(BASE, 'res_a2_hazard.json')))
llf = R['gamma_frailty_eANY_year+items+tv']['loglik_frailty']
R['gamma_frailty_eANY_year+items+tv']['loglik_no_frailty_same_scale'] = round(float(ll0), 1)
R['gamma_frailty_eANY_year+items+tv']['LR_chi2_boundary'] = round(float(2 * (llf - ll0)), 1)
json.dump(R, open(os.path.join(BASE, 'res_a2_hazard.json'), 'w'), indent=1)
print(ll0, llf, 2 * (llf - ll0))
