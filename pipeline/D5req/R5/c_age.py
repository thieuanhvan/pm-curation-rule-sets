# R5 C: age dependence of acceptance hazard, items >= 1 y. Submitter-stratified Cox on calendar time (as R3 T4a),
# B = 1,000 cluster-bootstrap draws over submitters (parallel). Variants: (i) without evidence level/rating/type covariates
# (shows what early-quality conditioning does); (ii) stratified by submitter x evidence level (quality conditioning in the baseline);
# (iii) PEM with ITEM-level shared gamma frailty + submitter... (year dummies, quality covariates); identified only by functional form.
# Input ../A3/civic_pem_hmac.pkl (pseudonymised). Aggregates only.
import json, sys, warnings, numpy as np, pandas as pd
from multiprocessing import Pool
warnings.filterwarnings('ignore')
src = open('../R3_civic/r3_t4_survival.py', encoding='utf-8').read().split("R = {'n_pieces'")[0]
import os; os.chdir('../R3_civic'); exec(src); os.chdir('../R5')
from statsmodels.duration.hazard_regression import PHReg

def fitage(df, quality=True, strata_col='sid'):
    X = items(df)
    if not quality: X = X.drop(columns=[c for c in X.columns if c.startswith(('lvl_', 'rat_', 'typ_'))])
    X['ageY'] = df.ageY.values; X = X.loc[:, X.std() > 0]
    r = PHReg(df.exit.values, X.values, status=df.eACC.values, entry=df.entry.values, strata=df[strata_col].values, ties='breslow').fit()
    i = list(X.columns).index('ageY'); return float(np.exp(r.params[i])), float(r.bse[i])

G = {u: x for u, x in P1.groupby('subU')}; US = np.array(list(G))
def draw(seed):
    rng = np.random.default_rng(seed); s = rng.choice(US, len(US))
    df = pd.concat([G[u].assign(sid=k) for k, u in enumerate(s)]).reset_index(drop=True)
    try: return fitage(df)[0]
    except Exception: return np.nan

if __name__ == '__main__':
    B = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    P1['sid'] = P1.subU; P1['sid_lvl'] = P1.subU + '|' + P1.level.astype(str)
    R = {'n_pieces': len(P1), 'items': int(P1.id.nunique()), 'acceptances': int(P1.eACC.sum()), 'submitters': int(P1.subU.nunique())}
    hr, se = fitage(P1); R['strat_submitter_point'] = [round(hr, 3), round(float(np.exp(np.log(hr) - 1.96 * se)), 3), round(float(np.exp(np.log(hr) + 1.96 * se)), 3)]
    hr, se = fitage(P1, quality=False); R['strat_submitter_no_quality_covariates'] = [round(hr, 3), round(float(np.exp(np.log(hr) - 1.96 * se)), 3), round(float(np.exp(np.log(hr) + 1.96 * se)), 3)]
    hr, se = fitage(P1, strata_col='sid_lvl'); R['strat_submitter_x_level'] = [round(hr, 3), round(float(np.exp(np.log(hr) - 1.96 * se)), 3), round(float(np.exp(np.log(hr) + 1.96 * se)), 3)]
    # high-quality subset: levels A/B or rating >= 4 (early quality proxy, current metadata)
    hq = P1[P1.level.isin(['A', 'B']) | (pd.to_numeric(P1.rating, errors='coerce') >= 4)].reset_index(drop=True)
    try:
        hr, se = fitage(hq); R['strat_submitter_high_quality_subset'] = {'HR': [round(hr, 3), round(float(np.exp(np.log(hr) - 1.96 * se)), 3), round(float(np.exp(np.log(hr) + 1.96 * se)), 3)], 'events': int(hq.eACC.sum()), 'items': int(hq.id.nunique())}
    except Exception as e: R['strat_submitter_high_quality_subset'] = str(e)[:200]
    with Pool(7) as p: bs = p.map(draw, range(20261100, 20261100 + B))
    bs = np.array(bs); ok = np.isfinite(bs)
    R['cluster_bootstrap'] = {'B': B, 'finite': int(ok.sum()), 'ci95': [round(float(np.percentile(bs[ok], 2.5)), 3), round(float(np.percentile(bs[ok], 97.5)), 3)], 'median': round(float(np.median(bs[ok])), 3)}
    json.dump(R, open('res_c_age.json', 'w'), indent=1); print(json.dumps(R, indent=1))
