# W7 T5: campaign-excluded rho on the full-follow-up window (definitions copied from ../A6/a6_campaign.py)
# A6 (1)-(3): objective campaign-intake definitions for CIViC evidence items and recomputation of capacity ratio,
# pending share, 1-y acceptance (Aalen-Johansen), live-queue service discipline and same-organisation share,
# excluding campaign intake and with it as a separate class. Reuses ../A3/civic_items.pkl (pseudonymised; no API).
import os, json, pickle, numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); A3 = os.path.join(BASE, '..', 'A3')
d = pickle.load(open(os.path.join(A3, 'civic_items.pkl'), 'rb')); it = d['items'].copy(); NOW = d['NOW']
st = pd.read_csv(os.path.join(A3, 'pending_states.csv'))[['id', 'state']]
it = it.merge(st, on='id', how='left'); it['state'] = it.state.fillna('decided')
rng = np.random.default_rng(20261007); B = int(os.environ.get('B', 1000))
dt = pd.to_datetime(it.arr, unit='D'); it['yr'] = dt.dt.year; it['ym'] = dt.dt.strftime('%Y-%m')
it['decyr'] = pd.to_datetime(it.dec, unit='D').dt.year
it['org'] = it.subOrg.fillna(-1).astype(int)
R = {}
def P(k, v): R[k] = v; print(k, json.dumps(v, default=str)[:900], flush=True)
def wilson(k, n, z=1.96):
    if n == 0: return None
    p = k / n; den = 1 + z*z/n; c = (p + z*z/(2*n)) / den; h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return [round(p, 3), round(c-h, 3), round(c+h, 3), int(n)]
def qci(a):
    a = np.asarray([x for x in a if np.isfinite(x)])
    return [round(float(np.quantile(a, .025)), 3), round(float(np.quantile(a, .975)), 3)] if len(a) else None

# ---------------- (1) campaign definitions ----------------
sm = it.groupby(['subU', 'ym']).size(); it['subMonthN'] = [sm[(u, m)] for u, m in zip(it.subU, it.ym)]
om = it.groupby(['org', 'ym']).size(); it['orgMonthN'] = [om[(o, m)] for o, m in zip(it.org, it.ym)]
g = it.groupby('subU').agg(f=('arr', 'min'), l=('arr', 'max'), n=('id', 'size'))
g['org0'] = it.sort_values('arr').groupby('subU').org.first()
g['span'] = g.l - g.f
fv = g.f.values; ov = g.org0.values
g['coh15org'] = [int(((np.abs(fv - a) <= 15) & (ov == o)).sum()) for a, o in zip(fv, ov)]
g['coh30any'] = [int((np.abs(fv - a) <= 30).sum()) for a in fv]
short = g.span <= 120
C2a = set(g.index[short & (g.coh15org >= 5)]); C2b = set(g.index[short & (g.coh30any >= 8)])
K_BULK, K_C1, K_C2, K_C2B, K_C3 = 'bulk27', 'C1', 'C2', 'C2b', 'C3'
LABELS = {
  K_BULK: 'submitter with >=100 items (reviewer set)',
  K_C1: 'burst: submitter same-day >=20 or submitter calendar-month >=40',
  K_C2: 'cohort: short-lived (<=120 d) submitter whose first submission falls in a cohort of >=5 first-time submitters within +-15 d under the same org',
  K_C2B: 'cohort (loose): short-lived submitter, >=8 first-time submitters within +-30 d, any org',
  K_C3: 'organisational surge: org calendar-month with >=100 submissions',
  'U': 'union C1|C2|C3', 'W': 'widest: U | bulk27 | C2b'}
defs = {K_BULK: it.subVol >= 100, K_C1: (it.burstN >= 20) | (it.subMonthN >= 40), K_C2: it.subU.isin(C2a),
        K_C2B: it.subU.isin(C2b), K_C3: it.orgMonthN >= 100}
defs['U'] = defs[K_C1] | defs[K_C2] | defs[K_C3]
defs['W'] = defs['U'] | defs[K_BULK] | defs[K_C2B]

# W7: throughput ratio of non-campaign intake on the full-follow-up window, with submitter-cluster bootstrap
D = lambda s: pd.Timestamp(s).value / 864e11
WIN = {'full_followup_2022-10-07..2025-10-06': (D('2022-10-07'), D('2025-10-07')), 'cal2023_25': (D('2023-01-01'), D('2026-01-01'))}
arr = it.arr.values; dec = it.dec.values
subs = it.subU.values; usub = np.unique(subs); idx_by_sub = {u: np.where(subs == u)[0] for u in usub}
BOOT = [np.concatenate([idx_by_sub[u] for u in rng.choice(usub, len(usub), replace=True)]) for _ in range(B)]
out = {}
for wn, (a, b) in WIN.items():
    o = {}
    for k, m in [('all', pd.Series(True, index=it.index))] + list(defs.items()):
        mv = ~m.values if k != 'all' else m.values
        f = lambda ix: ((dec[ix] >= a) & (dec[ix] < b)).sum() / max(((arr[ix] >= a) & (arr[ix] < b)).sum(), 1)
        ii = np.where(mv)[0]; est = f(ii); reps = [f(ix[mv[ix]]) for ix in BOOT]
        o[k] = {'est': round(float(est), 3), 'ci_cluster_submitter': qci(reps), 'arrivals': int(((arr[ii] >= a) & (arr[ii] < b)).sum())}
    out[wn] = o
P('rho_noncampaign_by_window', out)
json.dump(R, open(os.path.join(BASE, 'res_w7_t5_campaign_window.json'), 'w'), indent=1, default=str)
