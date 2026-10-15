# Conditional-logit (McFadden, uniformly sampled alternatives) model of the observed service discipline.
# Own Newton-Raphson (vectorised); fits on calibration tokens (<2023), evaluates out-of-sample on 2023-2026 tokens.
import json, numpy as np, pandas as pd
d = pd.read_csv('choice.csv').sort_values(['gid', 'chosen'], ascending=[True, False]).reset_index(drop=True)
T1 = ['logAge','logRank','lvlA','lvlB','lvlD','lvlE','ratingC','ratingNA','type_DIAGNOSTIC','type_PROGNOSTIC','type_PREDISPOSING','type_ONCOGENIC','type_FUNCTIONAL','sameOrg','subPrior','selfSub']
T2 = T1 + ['act30','touched']
SPECS = {'rankonly':['logRank'], 'age_rank':['logAge','logRank'], 'T1':T1, 'T2':T2}
def prep(sub):
    g = pd.factorize(sub['gid'].values)[0]; return g, sub['chosen'].values.astype(float)
def ll_grad_hess(X, g, y, b, G):
    u = X @ b; m = np.full(G, -np.inf); np.maximum.at(m, g, u); e = np.exp(u - m[g]); s = np.bincount(g, e, G); p = e / s[g]
    ll = float((u * y).sum() - (np.log(s) + m).sum())
    xbar = np.vstack([np.bincount(g, p * X[:, k], G) for k in range(X.shape[1])]).T
    grad = (X * y[:, None]).sum(0) - xbar.sum(0)
    Xc = X - xbar[g]; H = -(Xc * p[:, None]).T @ Xc
    return ll, grad, H, p
LAM = 0.5  # weak ridge penalty (stabilises quasi-separated dummies, e.g. ratingNA in 2021-22)
def pen(X, g, y, b, G):
    ll, gr, H, p = ll_grad_hess(X, g, y, b, G); return ll - LAM * (b @ b) / 2, gr - LAM * b, H - LAM * np.eye(len(b)), p
def fit(sub, cols):
    X = sub[cols].values.astype(float); g, y = prep(sub); G = g.max() + 1; b = np.zeros(len(cols))
    for it in range(100):
        ll, gr, H, _ = pen(X, g, y, b, G)
        step = np.linalg.solve(H - 1e-8 * np.eye(len(b)), gr); b2 = b - step; t = 1.0
        while pen(X, g, y, b - t * step, G)[0] < ll - 1e-9 and t > 1e-4: t /= 2
        b = b - t * step
        if np.abs(t * step).max() < 1e-7: break
    ll, gr, H, _ = pen(X, g, y, b, G); V = np.linalg.inv(-H); se = np.sqrt(np.diag(V)); fit.V = V
    return b, se, ll
def evalset(sub, cols, b):
    g, y = prep(sub); G = g.max() + 1
    u = sub[cols].values.astype(float) @ b if cols else np.zeros(len(sub))
    m = np.full(G, -np.inf); np.maximum.at(m, g, u); s = np.bincount(g, np.exp(u - m[g]), G)
    llc = u[y == 1] - (np.log(s) + m)  # rows sorted so chosen first per group
    # top-1: chosen has the max utility (ties broken pessimistically -> fraction)
    ismax = (u >= m[g] - 1e-12).astype(float); nmax = np.bincount(g, ismax, G)
    top1 = (ismax[y == 1] / nmax)
    n = len(llc); boot = [llc[np.random.default_rng(i).integers(0, n, n)].mean() for i in range(200)]
    return {'meanLL': float(llc.mean()), 'meanLL_ci': [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))], 'top1': float(top1.mean()), 'nGroups': int(n)}
cal = d[d.period == 'cal']; val = d[d.period == 'val']; rec = d[(d.period == 'cal') & (d.t >= 18628)]
out = {'note': 'sampled choice sets: chosen + up to 40 uniform alternatives; LL per choice on sampled sets; uniform = -log(set size)'}
out['val_uniform'] = evalset(val, [], None); out['cal_uniform'] = evalset(cal, [], None)
print('uniform val', out['val_uniform'])
for nm, sub in [('cal', cal), ('cal2021_22', rec), ('full', d)]:
    for sp, cols in SPECS.items():
        b, se, ll = fit(sub, cols)
        r = {'coef': dict(zip(cols, map(float, b))), 'se': dict(zip(cols, map(float, se))), 'n_groups': int(sub.gid.nunique()), 'llf': ll, 'cov': fit.V.tolist(), 'in_sample': evalset(sub, cols, b)}
        if nm != 'full': r['val'] = evalset(val, cols, b)
        out[f'{nm}_{sp}'] = r
        print(nm, sp, 'in', r['in_sample']['meanLL'], 'val', r.get('val'))
json.dump(out, open('fit_logit.json', 'w'), indent=1)
for k in ['cal_T1', 'cal_T2', 'cal2021_22_T1', 'full_T1']:
    print(k, {c: f"{out[k]['coef'][c]:.2f}±{1.96*out[k]['se'][c]:.2f}" for c in out[k]['coef']})
