# (5) Replace the single Little's-law '25-year' figure by windowed estimates with bootstrap CIs (projections, not observed waits).
import os, pickle, json
import numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
d = pickle.load(open(os.path.join(BASE, 'civic_items.pkl'), 'rb')); it = d['items']; NOW = d['NOW']
rng = np.random.default_rng(5)
arr = it.arr.values; dec = it.dec.values
act = [np.sort(np.concatenate([[a], np.array(t, float)])) for a, t in zip(arr, it.act_t)]
def stats_at(t, wm):
    w = wm * 30.4375
    B = int(((arr <= t) & (np.isnan(dec) | (dec > t))).sum())
    pend = np.flatnonzero((arr <= t) & (np.isnan(dec) | (dec > t)))
    Blive = int(sum(np.searchsorted(act[i], t, 'right') - np.searchsorted(act[i], t - 365, 'right') > 0 for i in pend))
    # monthly counts in the trailing window for block bootstrap
    edges = t - w + np.arange(wm + 1) * 30.4375
    dm = np.histogram(dec[~np.isnan(dec)], edges)[0]; am = np.histogram(arr, edges)[0]
    mu, lam = dm.sum() / (w / 365.25), am.sum() / (w / 365.25)
    bs = []
    for _ in range(2000):
        i = rng.integers(0, wm, wm); bs.append((dm[i].sum() / (w / 365.25), am[i].sum() / (w / 365.25)))
    bs = np.array(bs)
    clr = B / bs[:, 0]; clr_live = Blive / bs[:, 0]
    net = bs[:, 0] - bs[:, 1]
    return {'backlog': B, 'backlog_live365': Blive, 'arrivals_per_y': [round(lam), round(np.percentile(bs[:, 1], 2.5)), round(np.percentile(bs[:, 1], 97.5))],
            'decisions_per_y': [round(mu), round(np.percentile(bs[:, 0], 2.5)), round(np.percentile(bs[:, 0], 97.5))],
            'clearance_years_B_over_mu': [round(B / mu, 1), round(np.percentile(clr, 2.5), 1), round(np.percentile(clr, 97.5), 1)],
            'clearance_years_live_only': [round(Blive / mu, 2), round(np.percentile(clr_live, 2.5), 2), round(np.percentile(clr_live, 97.5), 2)],
            'net_drain_mu_minus_lambda_per_y': [round(mu - lam), round(np.percentile(net, 2.5)), round(np.percentile(net, 97.5))],
            'P(mu>lambda)_boot': round(float((net > 0).mean()), 3)}
R = {}
dates = [pd.Timestamp(f'{y}-12-31').value / 864e11 for y in range(2018, 2026)] + [NOW]
for wm in (12, 24, 36):
    R[f'window_{wm}m'] = {pd.Timestamp(t * 864e11).strftime('%Y-%m-%d'): stats_at(t, wm) for t in dates}
# observed waits for comparison: decided items in the last 36 months (age at decision)
m = ~np.isnan(dec) & (dec > NOW - 3 * 365.25)
w = dec[m] - arr[m]
R['observed_age_at_decision_last36m_days'] = {'n': int(m.sum()), 'p25': round(float(np.percentile(w, 25)), 1), 'median': round(float(np.median(w)), 1), 'p75': round(float(np.percentile(w, 75)), 1), 'p90': round(float(np.percentile(w, 90)), 1),
                                             'share_age_gt_5y': round(float((w > 5 * 365.25).mean()), 3)}
json.dump(R, open(os.path.join(BASE, 'res_a5_little.json'), 'w'), indent=1)
for k, v in R.items():
    if k.startswith('window'):
        for t, s in v.items(): print(k, t, s)
    else: print(k, v)
