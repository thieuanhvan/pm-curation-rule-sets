# R3 T4c: cluster bootstrap over submitters (B=60) for the age HR in the submitter-stratified Cox (calendar time scale) and the APC variant.
import json, warnings, numpy as np, pandas as pd
from statsmodels.duration.hazard_regression import PHReg
warnings.filterwarnings('ignore'); rng = np.random.default_rng(20261010)
src = open('r3_t4_survival.py', encoding='utf-8').read().split("R = {'n_pieces'")[0]; exec(src)
def fitage(df, coh=False, strata=True):
    X = items(df); X['ageY'] = df.ageY.values
    if coh: X = pd.concat([X, pd.get_dummies(df.coh2, prefix='coh', dtype=float).iloc[:, 1:]], axis=1)
    X = X.loc[:, X.std() > 0]
    r = PHReg(df.exit.values, X.values, status=df.eACC.values, entry=df.entry.values, strata=df.sid.values if strata else None, ties='breslow').fit()
    return float(np.exp(r.params[list(X.columns).index('ageY')]))
G = {u: x for u, x in P1.groupby('subU')}; us = np.array(list(G)); out = {'strata': [], 'apc_cohort_bins': []}
for b in range(60):
    s = rng.choice(us, len(us)); df = pd.concat([G[u].assign(sid=k) for k, u in enumerate(s)]).reset_index(drop=True)
    try: out['strata'].append(fitage(df)); out['apc_cohort_bins'].append(fitage(df, coh=True, strata=False))
    except Exception: pass
R = json.load(open('res_r3_t4.json'))
R['cluster_bootstrap_B60'] = {k: [round(float(np.nanpercentile(v, 2.5)), 3), round(float(np.nanpercentile(v, 97.5)), 3), int(np.isfinite(v).sum())] for k, v in out.items()}
R['cluster_bootstrap_raw'] = out
json.dump(R, open('res_r3_t4.json', 'w'), indent=1); print(R['cluster_bootstrap_B60'])
