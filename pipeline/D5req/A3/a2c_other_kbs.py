# (2, other KBs) Decision hazard by age with calendar-year control (piecewise-exponential Poisson), GO / HPO / Wikidata sample.
import os, json, warnings
import numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings('ignore')
BASE = os.path.dirname(os.path.abspath(__file__)); K4 = os.path.join(BASE, '..', '..', 'D5k4')
NOW = pd.Timestamp('2026-10-07T00:00:00Z').value / 864e11
EDG = [0, 7, 30, 91, 182, 365, 730, 1461, 1e9]; LAB = ['0-7d', '7-30d', '30-91d', '91-182d', '182-365d', '1-2y', '2-4y', '4y+']
br = [0, 7, 30, 91, 182, 273, 365] + [365 + 91.3125 * k for k in range(1, 50)]
def pem(cases, subcol):
    rows = []
    for c in cases.itertuples():
        T = max(c.T, 1e-3); k = 0
        while br[k] < T:
            a0, a1 = br[k], min(br[k + 1], T)
            rows.append((a0, a1 - a0, c.arr + a0, int(a1 == T and c.ev), getattr(c, subcol)))
            k += 1
    P = pd.DataFrame(rows, columns=['age0', 'expo', 't0', 'y', 'sub'])
    P['band'] = pd.cut(P.age0, EDG, right=False, labels=LAB); P['year'] = pd.to_datetime(P.t0, unit='D').dt.year
    out = {}
    for nm, yr in (('age_only', False), ('age+year', True)):
        X = pd.get_dummies(P.band, prefix='a', dtype=float).drop(columns='a_0-7d')
        if yr: X = pd.concat([X, pd.get_dummies(P.year, prefix='y', dtype=float).iloc[:, 1:]], axis=1)
        X = X.loc[:, X.std() > 0].assign(const=1.0)
        r = sm.GLM(P.y.values, X, family=sm.families.Poisson(), offset=np.log(P.expo.values)).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(P['sub'])[0]})
        ci = r.conf_int()
        out[nm] = {c[2:]: [round(float(np.exp(r.params[c])), 4), round(float(np.exp(ci.loc[c, 0])), 4), round(float(np.exp(ci.loc[c, 1])), 4)] for c in r.params.index if c.startswith('a_')}
    out['events'] = int(P.y.sum()); out['items'] = len(cases)
    return out
R = {}
for tag in ('go', 'hpo'):
    o = list(json.load(open(os.path.join(K4, f'issues_{tag}.json'), encoding='utf-8')).values())
    cs = pd.DataFrame([dict(arr=pd.Timestamp(x['c']).value / 864e11, dec=(pd.Timestamp(x['x']).value / 864e11 if x['s'] == 'closed' else np.nan), sub=x['u'] or 'na') for x in o if x['c'] >= '2016'])
    cs['T'] = np.where(cs.dec.isna(), NOW - cs.arr, cs.dec - cs.arr); cs['ev'] = ~cs.dec.isna()
    R[tag] = pem(cs, 'sub'); print(tag, json.dumps(R[tag]))
raw = json.load(open(os.path.join(K4, 'wd_cases.json'), encoding='utf-8'))
cs = pd.DataFrame([dict(arr=x['arr'] / 864e5, dec=(np.nan if x['kind'] == 'pending' else x['dec'] / 864e5), sub=x.get('prop') or 'na') for x in raw
                   if x.get('arr') and x['arr'] >= pd.Timestamp('2016-01-01').value / 1e6 and (x['kind'] == 'pending' or x.get('dec') is not None)])
cs['T'] = np.where(cs.dec.isna(), NOW - cs.arr, np.maximum(cs.dec - cs.arr, 1e-3)); cs['ev'] = ~cs.dec.isna()
R['wikidata_sample'] = pem(cs, 'sub'); print('wd', json.dumps(R['wikidata_sample']))
json.dump(R, open(os.path.join(BASE, 'res_a2c_other_kbs.json'), 'w'), indent=1)
