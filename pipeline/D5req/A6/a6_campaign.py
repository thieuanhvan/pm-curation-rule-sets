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
P('definitions', LABELS)

ab = it.state == 'abandoned'; pend = it.out == 'PEND'
desc = {}
for k, m in defs.items():
    c = it[m]; n = it[~m]
    o = {'items': int(m.sum()), 'share_of_intake': round(m.mean(), 3), 'submitters': int(c.subU.nunique()) if c.subU.nunique() >= 5 else '<5',
         'share_of_pending': round((m & pend).sum() / pend.sum(), 3), 'share_of_abandoned_pending': round((m & ab).sum() / ab.sum(), 3),
         'arrivals_by_year': {int(y): int(v) for y, v in c.groupby('yr').size().items()},
         'arrivals_2023_25': int(c.yr.between(2023, 2025).sum()), 'arrivals_2023_25_noncampaign': int(n.yr.between(2023, 2025).sum()),
         'orgs_top_share': {int(kk): round(v, 3) for kk, v in c.org.value_counts(normalize=True).head(5).items()}}
    for lab, s in (('campaign', c), ('noncampaign', n)):
        o[lab] = {'level_mix': s.level.value_counts(normalize=True).round(3).to_dict(), 'share_level_C_D_E': round(s.level.isin(['C', 'D', 'E']).mean(), 3),
                  'first_item_of_submitter': round((s.subRank == 1).mean(), 3),
                  'touched_by_nonsubmitter': wilson(int(sum(len(a) > 0 for a in s.nonsub_act_t)), len(s)),
                  'any_comment': wilson(int(sum(len(a) > 0 for a in s.com_t)), len(s)),
                  'any_revision': wilson(int(sum(len(a) > 0 for a in s.rev_t)), len(s)),
                  'pending_share': wilson(int((s.out == 'PEND').sum()), len(s)),
                  'abandoned_share_of_pending': wilson(int((s.state == 'abandoned').sum()), int((s.out == 'PEND').sum())),
                  'outcome': s.out.value_counts().to_dict()}
    desc[k] = o
P('describe', desc)
ks = list(defs)
P('overlap_jaccard', {f'{a}~{b}': round(float((defs[a] & defs[b]).sum() / max(1, (defs[a] | defs[b]).sum())), 3) for i, a in enumerate(ks) for b in ks[i+1:]})
P('bulk27_items_inside_C1', wilson(int((defs[K_BULK] & defs[K_C1]).sum()), int(defs[K_BULK].sum())))
P('bulk27_items_inside_U', wilson(int((defs[K_BULK] & defs['U']).sum()), int(defs[K_BULK].sum())))
joins = pd.to_datetime(g.f, unit='D').dt.strftime('%Y-%m').value_counts()
P('first_time_submitters_per_month_top10', joins.sort_values(ascending=False).head(10).to_dict())
P('first_time_submitters_per_month_median', float(joins.reindex(pd.period_range('2015-06', '2026-09', freq='M').strftime('%Y-%m')).fillna(0).median()))
P('submitters_short_lived_share', wilson(int(short.sum()), len(g)))
P('cohort_submitters', {'C2': len(C2a), 'C2b': len(C2b)})

# ---------------- (2) recomputation ----------------
subs = it.subU.values; usub = np.unique(subs); idx_by_sub = {u: np.where(subs == u)[0] for u in usub}
BOOT_IDX = [np.concatenate([idx_by_sub[u] for u in rng.choice(usub, len(usub), replace=True)]) for _ in range(B)]
YEARS = list(range(2015, 2026))
yr_all = it.yr.values; dy_all = it.decyr.values
def rho_tab(yr, dy):
    o = {}
    for y in YEARS:
        a = (yr == y).sum(); o[y] = (dy == y).sum() / a if a else np.nan
    a = ((yr >= 2023) & (yr <= 2025)).sum(); o['2023-25'] = ((dy >= 2023) & (dy <= 2025)).sum() / a if a else np.nan
    return o
def rho_with_ci(mask):
    mv = mask.values; pt = rho_tab(yr_all[mv], dy_all[mv]); reps = []
    for ix in BOOT_IDX:
        s = ix[mv[ix]]; reps.append(rho_tab(yr_all[s], dy_all[s]))
    ii = np.where(mv)[0]; reps_i = []
    for _ in range(B):
        s = rng.choice(ii, len(ii), replace=True); reps_i.append(rho_tab(yr_all[s], dy_all[s]))
    return {str(k): {'est': round(v, 3) if np.isfinite(v) else None, 'ci_cluster_submitter': qci([r[k] for r in reps]), 'ci_item': qci([r[k] for r in reps_i])} for k, v in pt.items()}
RHO = {'all': rho_with_ci(pd.Series(True, index=it.index))}
def alloc(ix, mv):
    a = (((yr_all[ix] >= 2023) & (yr_all[ix] <= 2025)) & ~mv[ix]).sum(); dd = ((dy_all[ix] >= 2023) & (dy_all[ix] <= 2025)).sum(); return dd / a
for k, m in defs.items():
    RHO[k] = {'noncampaign': rho_with_ci(~m), 'campaign': rho_with_ci(m)}
    mv = m.values; allix = np.arange(len(it))
    RHO[k]['alloc_bound_2023_25'] = {'est': round(alloc(allix, mv), 3), 'ci_cluster_submitter': qci([alloc(ix, mv) for ix in BOOT_IDX])}
P('rho', RHO)

def aj(arr, dec, out, h=365):
    t = np.where(out == 'PEND', NOW - arr, dec - arr).astype(float); e = np.where(out == 'PEND', 0, np.where(out == 'ACC', 1, 2))
    o = np.argsort(t, kind='mergesort'); t, e = t[o], e[o]; n = len(t); S = 1.0; F1 = F2 = 0.0; i = 0
    while i < n and t[i] <= h:
        j = i
        while j < n and t[j] == t[i]: j += 1
        d1 = (e[i:j] == 1).sum(); d2 = (e[i:j] == 2).sum(); r = n - i
        F1 += S * d1 / r; F2 += S * d2 / r; S *= 1 - (d1 + d2) / r; i = j
    return F1, F2
A_arr, A_dec, A_out = it.arr.values, it.dec.values, it.out.values
def aj_ci(mask, B2=300):
    mv = mask.values
    if mv.sum() < 20: return 'n<20'
    f1, f2 = aj(A_arr[mv], A_dec[mv], A_out[mv]); r1 = []
    for ix in BOOT_IDX[:B2]:
        s = ix[mv[ix]]
        if len(s): r1.append(aj(A_arr[s], A_dec[s], A_out[s])[0])
    return {'n': int(mv.sum()), 'acc1y': round(f1, 3), 'ci_cluster_submitter': qci(r1), 'rej_or_wdr1y': round(f2, 3)}
ERA = {'all': it.yr > 0, '2017-18': it.yr.between(2017, 2018), '2019-22': it.yr.between(2019, 2022), '2023-26': it.yr >= 2023}
AJ = {'all': {e: aj_ci(f) for e, f in ERA.items()}}
for k, m in defs.items():
    AJ[k] = {cl: {e: aj_ci(mm & f) for e, f in ERA.items()} for cl, mm in (('noncampaign', ~m), ('campaign', m))}
P('aalen_johansen_accept_1y', AJ)

def positions(df, alive=365, frm=2021):
    arr = df.arr.values; dec = df.dec.values; ev = []
    for i in range(len(arr)):
        ev.append((arr[i], 0, i))
        if np.isfinite(dec[i]): ev.append((dec[i], 1, i))
    ev.sort(); inq = {}; us = []; t0 = pd.Timestamp(f'{frm}-01-01').value / 864e11
    for t, kk, i in ev:
        if kk == 0: inq[i] = arr[i]; continue
        if i not in inq: continue
        if t >= t0:
            a = np.fromiter(inq.values(), float)
            if alive: a = a[(t - a <= alive)]
            if alive and t - arr[i] > alive: a = np.append(a, arr[i])  # the decided item itself always counts
            L = len(a); newer = (a > arr[i]).sum()
            if L > 1: us.append((t, newer / (L - 1)))
        del inq[i]
    return us
def block(us):
    if len(us) < 20: return None
    by = {}
    for t, u in us: by.setdefault(pd.Timestamp(t * 864e11).strftime('%Y-%m'), []).append(u)
    kk = list(by); m = np.mean([u for _, u in us]); n10 = np.mean([u <= .1 for _, u in us]); reps = []
    for _ in range(B):
        xs = np.concatenate([by[kk[q]] for q in rng.integers(0, len(kk), len(kk))]); reps.append((xs.mean(), (xs <= .1).mean()))
    return {'n': len(us), 'u_mean': round(m, 3), 'ci': qci([r[0] for r in reps]), 'newest10': round(n10, 3), 'newest10_ci': qci([r[1] for r in reps])}
def disc(df):
    return {'alive365_2021+': block(positions(df)), 'full_2021+': block(positions(df, alive=None)), 'alive365_2023+': block(positions(df, frm=2023))}
DISC = {'all': disc(it)}
for k, m in defs.items():
    DISC[k] = {'noncampaign': disc(it[~m].reset_index(drop=True)), 'campaign': disc(it[m].reset_index(drop=True))}
P('discipline', DISC)

so_ok = ((it.out == 'ACC') & it.decOrg.notna() & it.subOrg.notna()).values
same = (it.decOrg == it.subOrg).values
def so(mv, sel):
    q = mv & so_ok & sel; return same[q].mean() if q.sum() else np.nan, int(q.sum())
SO = {}
SEL = {'all_years': np.ones(len(it), bool), 'dec2021+': (dy_all >= 2021), 'dec2023+': (dy_all >= 2023)}
for k, m in [('all', pd.Series(True, index=it.index))] + list(defs.items()):
    SO[k] = {}
    for cl, mm in ((('all', m),) if k == 'all' else (('noncampaign', ~m), ('campaign', m))):
        mv = mm.values
        for lab, sel in SEL.items():
            p, n = so(mv, sel); reps = []
            for ix in BOOT_IDX[:500]:
                q = ix[(mv & so_ok & sel)[ix]]
                if len(q): reps.append(same[q].mean())
            SO[k][f'{cl}|{lab}'] = {'share': round(p, 3) if n else None, 'n': n, 'ci_cluster_submitter': qci(reps)}
P('same_org_accept_share', SO)
json.dump(R, open(os.path.join(BASE, 'res_a6_campaign.json'), 'w'), indent=1, default=str)
print('done')
