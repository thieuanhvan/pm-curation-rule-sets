# (2) Cause-specific piecewise-exponential (Poisson) hazard models with time-varying covariates,
#     calendar-period control, submitter fixed effects, and a gamma-frailty model.
import os, pickle, json, warnings
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize
warnings.filterwarnings('ignore')
BASE = os.path.dirname(os.path.abspath(__file__))
d = pickle.load(open(os.path.join(BASE, 'civic_items.pkl'), 'rb')); it = d['items']; NOW = d['NOW']; ud = d['udays']
it = it.copy()
it['T'] = np.where(it.out == 'PEND', NOW - it.arr, it.dec - it.arr)
# ---- interval split on age
br = [0, 1, 7, 30, 91, 182, 273, 365] + [365 + 91.3125 * k for k in range(1, 50)]
br = np.array(br)
BAND_EDGES = [0, 1, 7, 30, 91, 182, 365, 730, 1461, 1e9]
BAND_LAB = ['0-1d', '1-7d', '7-30d', '30-91d', '91-182d', '182-365d', '1-2y', '2-4y', '4y+']
rows = []
for r in (it.itertuples() if not os.path.exists(os.path.join(BASE, 'civic_pem.pkl')) else []):
    T = max(r.T, 1e-3); arr = r.arr
    rev, com, flg, act = np.array(r.rev_t), np.array(r.com_t), np.array(r.flag_t), np.array(r.act_t)
    uds = ud.get(r.subU, np.array([]))
    k = 0
    while br[k] < T:
        a0, a1 = br[k], min(br[k + 1], T); t0 = arr + a0
        ev = 1 if (a1 == T and r.out != 'PEND') else 0
        n_rev = np.searchsorted(rev, t0, 'right'); n_com = np.searchsorted(com, t0, 'right'); n_flg = np.searchsorted(flg, t0, 'right')
        live = int(np.searchsorted(act, t0, 'right') - np.searchsorted(act, t0 - 365, 'right') > 0)
        sact = int(np.searchsorted(uds, t0, 'right') - np.searchsorted(uds, t0 - 365, 'right') > (1 if a0 < 365 else 0))  # exclude this submission event itself
        rows.append((r.id, a0, a1 - a0, t0, ev * (r.out == 'ACC'), ev * (r.out == 'REJ'), ev * (r.out == 'WDR'), ev, n_rev, n_com, n_flg, live, sact))
        k += 1
COLS = ['id', 'age0', 'expo', 't0', 'eACC', 'eREJ', 'eWDR', 'eANY', 'nrev', 'ncom', 'nflag', 'live365', 'subActive365']
P = pd.read_pickle(os.path.join(BASE, 'civic_pem.pkl'))[COLS] if not rows else pd.DataFrame(rows, columns=COLS)
P = P.merge(it[['id', 'level', 'rating', 'etype', 'subU', 'subOrg', 'subRoleNow', 'subVol', 'subRank', 'burstN', 'arr']], on='id')
P['band'] = pd.Categorical(pd.cut(P.age0, BAND_EDGES, right=False, labels=BAND_LAB), categories=BAND_LAB)
P['year'] = pd.to_datetime(P.t0, unit='D').dt.year
P['volc'] = pd.cut(P.subVol, [0, 1, 9, 99, 1e9], labels=['v1', 'v2-9', 'v10-99', 'v100+']).astype(str)
P['burst20'] = (P.burstN >= 20).astype(int); P['firstSub'] = (P.subRank == 1).astype(int)
P['subEditor'] = P.subRoleNow.isin(['EDITOR', 'ADMIN']).astype(int)
orgc = it.subOrg.value_counts(); bigorg = set(orgc[orgc >= 200].index)
P['org'] = P.subOrg.map(lambda o: f'o{int(o)}' if o in bigorg else 'oOther')
P['lrev'] = np.log1p(P.nrev); P['lcom'] = np.log1p(P.ncom); P['anyflag'] = (P.nflag > 0).astype(int)
P['rating'] = P.rating.fillna(0).astype(int).astype(str)
# calendar capacity: first decisions in quarter / pending at quarter start (per day)
q = pd.to_datetime(P.t0, unit='D').dt.to_period('Q')
P['qtr'] = q.astype(str)
dec_days = it.dec.dropna().values; arr_days = it.arr.values
qs = sorted(P.qtr.unique()); cap = {}
for qq in qs:
    s = pd.Period(qq).start_time.value / 864e11; e = pd.Period(qq).end_time.value / 864e11
    D_ = ((dec_days >= s) & (dec_days < e)).sum(); Q_ = ((arr_days < s) & ((it.dec.isna()) | (it.dec >= s))).sum()
    cap[qq] = (D_ + 0.5) / max(Q_, 1) / (e - s)
P['lcap'] = np.log(P.qtr.map(cap))
P.to_pickle(os.path.join(BASE, 'civic_pem.pkl'))
print('person-intervals', len(P), 'events', P[['eACC', 'eREJ', 'eWDR']].sum().to_dict())

def design(df, period='year', fe=False, tv=True, items=True):
    X = pd.get_dummies(df['band'], prefix='age', dtype=float).drop(columns='age_0-1d')
    parts = [X]
    if items:
        parts += [pd.get_dummies(df.level, prefix='lvl', dtype=float).drop(columns='lvl_A', errors='ignore'),
                  pd.get_dummies(df.rating, prefix='rat', dtype=float).drop(columns='rat_3', errors='ignore'),
                  pd.get_dummies(df.etype, prefix='typ', dtype=float).drop(columns='typ_PREDICTIVE', errors='ignore'),
                  pd.get_dummies(df.volc, prefix='vol', dtype=float).drop(columns='vol_v10-99', errors='ignore'),
                  df[['burst20', 'firstSub', 'subEditor']].astype(float),
                  pd.get_dummies(df.org, prefix='org', dtype=float).drop(columns='org_oOther', errors='ignore')]
    if tv: parts.append(df[['lrev', 'lcom', 'anyflag', 'live365', 'subActive365']].astype(float))
    if period == 'year': parts.append(pd.get_dummies(df.year, prefix='yr', dtype=float).drop(columns='yr_2019', errors='ignore'))
    elif period == 'cap': parts.append(df[['lcap']])
    if fe:
        cnt = it.subU.value_counts(); keep = set(cnt[cnt >= 5].index)
        s = df.subU.where(df.subU.isin(keep), 'small')
        parts.append(pd.get_dummies(s, prefix='S', dtype=float).drop(columns='S_small'))
        # submitter FE absorbs submitter-constant terms
        X = pd.concat(parts, axis=1)
        X = X.drop(columns=[c for c in X if c.startswith(('vol_', 'burst20', 'subEditor', 'org_'))], errors='ignore')
        return sm.add_constant(X)
    return sm.add_constant(pd.concat(parts, axis=1))

class CP:  # result holder for conditional (submitter-stratified) Poisson
    def __init__(s, names, b, V, n, ll): s.params = pd.Series(b, names); s.bse = pd.Series(np.sqrt(np.diag(V)), names); s.nobs = n; s.aic = -2 * ll + 2 * len(b)
    def conf_int(s): return pd.DataFrame({0: s.params - 1.96 * s.bse, 1: s.params + 1.96 * s.bse})
    @property
    def pvalues(s):
        from scipy.stats import norm; return pd.Series(2 * norm.sf(np.abs(s.params / s.bse)), s.params.index)

def condpois(df, y, X):
    """Poisson with submitter fixed effects concentrated out (= conditional multinomial likelihood); cluster-robust (submitter) SEs."""
    Xv = X.values.astype(float); yv = df[y].values.astype(float); lo = np.log(df.expo.values); g = pd.factorize(df.subU)[0]; G = g.max() + 1
    Yg = np.bincount(g, yv, G)
    def f(b):
        eta = Xv @ b + lo; m = np.exp(eta - eta.max()); M = np.bincount(g, m, G)
        ll = (yv * (eta)).sum() - (Yg[Yg > 0] * np.log(M[Yg > 0])).sum() - eta.max() * Yg.sum()
        Mx = np.zeros((G, Xv.shape[1])); np.add.at(Mx, g, m[:, None] * Xv)
        gr = Xv.T @ yv - (Yg[:, None] * Mx / np.maximum(M, 1e-300)[:, None]).sum(0)
        return -ll, -gr
    r = minimize(f, np.zeros(Xv.shape[1]), jac=True, method='L-BFGS-B', options={'maxiter': 5000})
    b = r.x; eta = Xv @ b + lo; m = np.exp(eta - eta.max()); M = np.bincount(g, m, G); p = m / M[g]
    Mx = np.zeros((G, Xv.shape[1])); np.add.at(Mx, g, p[:, None] * Xv)
    H = np.zeros((Xv.shape[1],) * 2)
    for gg in np.flatnonzero(Yg > 0):
        ii = g == gg; xi = Xv[ii]; pi = p[ii]; mx = Mx[gg]
        H += Yg[gg] * ((xi * pi[:, None]).T @ xi - np.outer(mx, mx))
    sc = np.zeros((G, Xv.shape[1])); np.add.at(sc, g, (yv - Yg[g] * p)[:, None] * Xv)
    Hi = np.linalg.pinv(H); V = Hi @ (sc.T @ sc) @ Hi
    return CP(list(X.columns), b, V, len(df), -r.fun)

def fit(df, y, **kw):
    fe = kw.pop('fe', False)
    X = design(df, **kw)
    if fe:
        X = X.drop(columns=[c for c in X if c.startswith(('vol_', 'burst20', 'subEditor', 'org_', 'const'))], errors='ignore')
        X = X.loc[:, X.std() > 0]
        return condpois(df, y, X)
    X = X.loc[:, X.std() > 0].assign(const=1.0)
    m = sm.GLM(df[y].values, X, family=sm.families.Poisson(), offset=np.log(df.expo.values))
    r = m.fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(df.subU)[0]}, maxiter=200)
    return r

def ages(r):
    o = {}
    for c in r.params.index:
        if c.startswith('age_'):
            ci = r.conf_int().loc[c]; o[c[4:]] = [round(float(np.exp(r.params[c])), 4), round(float(np.exp(ci[0])), 4), round(float(np.exp(ci[1])), 4)]
    return o
def coefs(r, pref):
    o = {}
    for c in r.params.index:
        if c.startswith(pref):
            ci = r.conf_int().loc[c]; o[c] = [round(float(np.exp(r.params[c])), 3), round(float(np.exp(ci[0])), 3), round(float(np.exp(ci[1])), 3), round(float(r.pvalues[c]), 4)]
    return o

R = {}
specs = {
    'M0_age_only': dict(period=None, items=False, tv=False),
    'M1_age+year': dict(period='year', items=False, tv=False),
    'M2_age+year+items': dict(period='year', items=True, tv=False),
    'M3_age+year+items+tv': dict(period='year', items=True, tv=True),
    'M3cap_age+capacity+items+tv': dict(period='cap', items=True, tv=True),
    'M4_M3+submitterFE': dict(period='year', items=True, tv=True, fe=True),
}
for cause in ['eANY', 'eACC', 'eREJ', 'eWDR']:
    for name, kw in specs.items():
        if cause in ('eREJ', 'eWDR') and name not in ('M0_age_only', 'M3_age+year+items+tv'): continue
        try:
            r = fit(P, cause, **kw)
        except Exception as ex:
            R[f'{cause}|{name}'] = {'error': str(ex)[:200]}; print(cause, name, 'ERR', ex); continue
        res = {'HR_age_vs_0-1d': ages(r), 'aic': round(float(r.aic), 1), 'n': int(r.nobs)}
        if name.startswith('M3'):
            res['tv'] = coefs(r, ('lrev', 'lcom', 'anyflag', 'live365', 'subActive365', 'lcap'))
            res['items'] = coefs(r, ('lvl_', 'rat_', 'typ_', 'vol_', 'burst20', 'firstSub', 'subEditor'))
        if name.startswith('M4'): res['tv'] = coefs(r, ('lrev', 'lcom', 'anyflag', 'live365', 'subActive365'))
        R[f'{cause}|{name}'] = res
        print(cause, name, json.dumps(res['HR_age_vs_0-1d']))
        if 'tv' in res: print('   tv', json.dumps(res['tv']))
        if 'items' in res: print('   items', json.dumps(res['items']))

# Age trend restricted to items aged >= 1 y (the claim concerns old items): log-linear slope per extra year
P1 = P[P.age0 >= 365].copy(); P1['ageY'] = P1.age0 / 365.25
for cause in ['eANY', 'eACC']:
    for name, kw in {'year+items+tv': dict(period='year', items=True, tv=True), '+submitterFE': dict(period='year', items=True, tv=True, fe=True),
                     'live-only:year+items+tv': dict(period='year', items=True, tv=True)}.items():
        df = P1[P1.live365 == 1] if name.startswith('live') else P1
        kw = dict(kw); fe = kw.pop('fe', False)
        X = design(df, **kw); X = X.drop(columns=[c for c in X if c.startswith('age_')]); X['ageY'] = df.ageY.values
        if fe:
            X = X.drop(columns=[c for c in X if c.startswith(('vol_', 'burst20', 'subEditor', 'org_', 'const'))], errors='ignore'); X = X.loc[:, X.std() > 0]
            r = condpois(df, cause, X)
        else:
            X = X.loc[:, X.std() > 0].assign(const=1.0)
            r = sm.GLM(df[cause].values, X, family=sm.families.Poisson(), offset=np.log(df.expo.values)).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(df.subU)[0]}, maxiter=200)
        ci = r.conf_int().loc['ageY']
        R[f'slope_ge1y|{cause}|{name}'] = {'HR_per_year': [round(float(np.exp(r.params['ageY'])), 3), round(float(np.exp(ci[0])), 3), round(float(np.exp(ci[1])), 3)], 'p': float(r.pvalues['ageY']), 'events': int(df[cause].sum()), 'n': len(df)}
        print('slope>=1y', cause, name, R[f'slope_ge1y|{cause}|{name}'])

# ---- gamma frailty PEM (item-level shared frailty, single spell), any decision, year + items + tv
X = design(P, period='year', items=True, tv=True); X = X.loc[:, X.std() > 0].assign(const=1.0)
Xv = X.values.astype(float); y = P.eANY.values.astype(float); lo = np.log(P.expo.values)
gid = pd.factorize(P.id)[0]; G = gid.max() + 1
last = P.groupby(gid).cumcount(ascending=False).values == 0
dI = np.zeros(G); np.add.at(dI, gid, y)
def nll(p):
    b, phi = p[:-1], p[-1]; th = np.exp(phi)
    eta = Xv @ b; w = np.exp(eta + lo)
    H = np.bincount(gid, w, G)
    ll = (y * eta).sum() - ((1 / th + dI) * np.log1p(th * H)).sum()
    fac = (1 / th + dI) * th / (1 + th * H)       # per item
    gb = Xv.T @ y - Xv.T @ (w * fac[gid])
    gphi = ((np.log1p(th * H) / th ** 2) - (1 / th + dI) * H / (1 + th * H)).sum() * th
    return -ll, -np.append(gb, gphi)
# start from Poisson fit
r0 = sm.GLM(y, Xv, family=sm.families.Poisson(), offset=lo).fit()
p0 = np.append(r0.params, np.log(0.5))
opt = minimize(nll, p0, jac=True, method='L-BFGS-B', options={'maxiter': 3000})
# observed-information SE via finite differences of the analytic gradient (age + theta only)
names = list(X.columns) + ['log_theta']
idx = [i for i, c in enumerate(names) if c.startswith('age_')] + [len(names) - 1]
Hm = np.zeros((len(p0), len(p0))); eps = 1e-4
for i in range(len(p0)):
    e = np.zeros(len(p0)); e[i] = eps
    Hm[:, i] = (nll(opt.x + e)[1] - nll(opt.x - e)[1]) / (2 * eps)
cov = np.linalg.pinv((Hm + Hm.T) / 2)
fr = {'converged': bool(opt.success), 'theta': [round(float(np.exp(opt.x[-1])), 3), round(float(np.exp(opt.x[-1] - 1.96 * np.sqrt(cov[-1, -1]))), 3), round(float(np.exp(opt.x[-1] + 1.96 * np.sqrt(cov[-1, -1]))), 3)],
      'loglik_frailty': round(float(-opt.fun), 1), 'loglik_poisson': round(float(r0.llf), 1)}
fr['HR_age_vs_0-1d'] = {names[i][4:]: [round(float(np.exp(opt.x[i])), 4), round(float(np.exp(opt.x[i] - 1.96 * np.sqrt(cov[i, i]))), 4), round(float(np.exp(opt.x[i] + 1.96 * np.sqrt(cov[i, i]))), 4)] for i in idx[:-1]}
fr['HR_age_poisson_same_X'] = {names[i][4:]: round(float(np.exp(r0.params[i])), 4) for i in idx[:-1]}
R['gamma_frailty_eANY_year+items+tv'] = fr
print('frailty', json.dumps(fr))
json.dump(R, open(os.path.join(BASE, 'res_a2_hazard.json'), 'w'), indent=1)
