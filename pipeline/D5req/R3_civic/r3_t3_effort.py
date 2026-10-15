# R3 T3: decision effort. Reconcile moderator-FE ratio vs shift-share; alternative intensity counting all moderation types;
# Melitz-Polanec (2015) decomposition (entrants/exiters compared with stayers, not with the old aggregate); k>=5 cell check.
# Input ../W3/w3_events_hmac.pkl. Aggregates only; cells with < 5 moderators are flagged and not reported as stand-alone numbers.
import json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings('ignore')
rng = np.random.default_rng(20261009)
E = pd.read_pickle('../W3/w3_events_hmac.pkl'); H = E[~E.bot].copy(); H['day'] = np.floor(H.t).astype(int)
mod = H[H.modAt].copy()
c = {}
c['ev_decision'] = mod.act.isin(['ACCEPTED', 'REJECTED']) & (mod.st == 'EvidenceItem') & (mod.u != mod.evSub)
c['revision_moderation'] = mod.act.isin(['REVISION_ACCEPTED', 'REVISION_REJECTED']) & (mod.u != mod.revSugg)
c['assertion_moderation'] = mod.act.isin(['ASSERTION_ACCEPTED', 'ASSERTION_REJECTED', 'ASSERTION_APPROVED'])
c['flag_resolution'] = mod.act.eq('FLAG_RESOLVED')
c['source_suggestion_curation'] = mod.act.eq('CURATED_SOURCE_SUGGESTION')
c['revert'] = mod.act.isin(['REVERTED', 'ASSERTION_REVERTED'])
c['entity_creation'] = mod.act.isin(['VARIANT_CREATED', 'COMPLEX_MOLECULAR_PROFILE_CREATED', 'FEATURE_CREATED'])
c['deprecation'] = mod.act.str.startswith('DEPRECATED')
c['flag_raise'] = mod.act.eq('FLAGGED')
for k, v in c.items(): mod[k] = v.astype(int)
D = mod.groupby(['u', 'day'])[list(c)].sum().reset_index()
D['year'] = pd.to_datetime(D.day * 864e11).dt.year
D = D[D.year >= 2016].copy()
D['period'] = pd.cut(D.year, [2015, 2018, 2022, 2027], labels=['2016-18', '2019-22', '2023-26']).astype(str)
MOD_CORE = ['ev_decision', 'revision_moderation', 'assertion_moderation', 'flag_resolution', 'source_suggestion_curation', 'revert']
D['moderation_all'] = D[MOD_CORE].sum(1)                                   # every decision on others' content
D['moderation_plus_maintenance'] = D.moderation_all + D[['entity_creation', 'deprecation', 'flag_raise']].sum(1)
D['nonev_moderation'] = D.moderation_all - D.ev_decision
OUTS = ['ev_decision', 'moderation_all', 'nonev_moderation', 'moderation_plus_maintenance']
R = {'panel': {'moderator_days': len(D), 'moderators': int(D.u.nunique()), 'by_period': D.groupby('period').u.nunique().to_dict()}}

def fe_fit(df, y, fe_u=True):
    d = df.reset_index(drop=True)
    if fe_u:
        keep = d.groupby('u')[y].transform('sum') > 0; d = d[keep].reset_index(drop=True)
    X = pd.get_dummies(d.period, dtype=float)[['2019-22', '2023-26']]
    if fe_u: X = pd.concat([X, pd.get_dummies(d.u, prefix='m', dtype=float).iloc[:, 1:]], axis=1)
    X = X.loc[:, X.std() > 0].assign(const=1.0)
    r = sm.GLM(d[y].values, X, family=sm.families.Poisson()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.u)[0]})
    ci = r.conf_int()
    return {k: [round(float(np.exp(r.params[k])), 3), round(float(np.exp(ci.loc[k, 0])), 3), round(float(np.exp(ci.loc[k, 1])), 3)] for k in ('2019-22', '2023-26')} | {'moderators': int(d.u.nunique())}

def decomp(g0, g1, y):
    a0 = g0.groupby('u').agg(d=(y, 'size'), e=(y, 'sum')); a1 = g1.groupby('u').agg(d=(y, 'size'), e=(y, 'sum'))
    w0 = a0.d / a0.d.sum(); w1 = a1.d / a1.d.sum(); r0 = a0.e / a0.d; r1 = a1.e / a1.d
    R0 = float((w0 * r0).sum()); R1 = float((w1 * r1).sum())
    st = a0.index.intersection(a1.index); en = a1.index.difference(a0.index); ex = a0.index.difference(a1.index)
    o = {'R0': R0, 'R1': R1, 'delta': R1 - R0, 'n_stay': len(st), 'n_entry': len(en), 'n_exit': len(ex)}
    # FHK (as in the manuscript)
    o['fhk_within'] = float((w0[st] * (r1[st] - r0[st])).sum()); o['fhk_between'] = float(((w1[st] - w0[st]) * (r0[st] - R0)).sum())
    o['fhk_cross'] = float(((w1[st] - w0[st]) * (r1[st] - r0[st])).sum()); o['fhk_entry'] = float((w1[en] * (r1[en] - R0)).sum())
    o['fhk_exit'] = -float((w0[ex] * (r0[ex] - R0)).sum())
    # Melitz-Polanec: stayers' aggregate change (within + covariance) and entry/exit relative to stayers in the same period
    sS0 = w0[st].sum(); sS1 = w1[st].sum(); RS0 = float((w0[st] * r0[st]).sum() / sS0) if sS0 else np.nan; RS1 = float((w1[st] * r1[st]).sum() / sS1) if sS1 else np.nan
    sE = w1[en].sum(); sX = w0[ex].sum()
    RE = float((w1[en] * r1[en]).sum() / sE) if sE else RS1; RX = float((w0[ex] * r0[ex]).sum() / sX) if sX else RS0
    o['mp_stayers'] = RS1 - RS0; o['mp_entry'] = float(sE * (RE - RS1)); o['mp_exit'] = float(sX * (RS0 - RX))
    # stayers' change split: unweighted mean rate change vs reallocation among stayers
    o['mp_stayers_meanrate'] = float(r1[st].mean() - r0[st].mean()) if len(st) else np.nan
    o['stayer_rate_ratio'] = RS1 / RS0 if RS0 else np.nan
    return o
def boot(g0, g1, y, B=2000):
    us = np.array(sorted(set(g0.u) | set(g1.u))); G0 = {u: x for u, x in g0.groupby('u')}; G1 = {u: x for u, x in g1.groupby('u')}; out = []
    for _ in range(B):
        s = rng.choice(us, len(us)); a, b = [], []
        for k, u in enumerate(s):
            if u in G0: a.append(G0[u].assign(u=f'{u}#{k}'))
            if u in G1: b.append(G1[u].assign(u=f'{u}#{k}'))
        if a and b:
            o = decomp(pd.concat(a), pd.concat(b), y)
            if o['n_stay'] > 0: out.append(o)
    return out
g0, g1 = D[D.period == '2016-18'], D[D.period == '2023-26']
for y in OUTS:
    o = {'per_active_day_2016_18': round(float(g0[y].mean()), 3), 'per_active_day_2023_26': round(float(g1[y].mean()), 3),
         'fold_decline': round(float(g0[y].mean() / g1[y].mean()), 2), 'FE_ratio_2023_26_vs_2016_18': fe_fit(D, y, True)['2023-26'],
         'noFE_ratio_2023_26_vs_2016_18': fe_fit(D, y, False)['2023-26']}
    pt = decomp(g0, g1, y); bs = boot(g0, g1, y, 1000 if y != 'ev_decision' else 2000)
    q = lambda k: [round(float(np.nanpercentile([b[k] for b in bs], 2.5)), 3), round(float(np.nanpercentile([b[k] for b in bs], 97.5)), 3)]
    o['decomp'] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in pt.items()}
    for k in ('delta', 'mp_stayers', 'mp_entry', 'mp_exit', 'fhk_within', 'fhk_entry', 'stayer_rate_ratio'): o['decomp'][k + '_CI'] = q(k)
    o['decomp']['mp_entry_plus_exit'] = round(pt['mp_entry'] + pt['mp_exit'], 3)
    o['decomp']['mp_entry_plus_exit_CI'] = [round(float(np.nanpercentile([b['mp_entry'] + b['mp_exit'] for b in bs], p)), 3) for p in (2.5, 97.5)]
    o['decomp']['mp_stayer_share_of_delta'] = round(pt['mp_stayers'] / pt['delta'], 3)
    R[y] = o; print(y, json.dumps(o))
# two-group coarsening for disclosure control: stayers (>=5) vs all others (entry+exit pooled = 'changers')
R['cells_main_comparison'] = {'stay': R['ev_decision']['decomp']['n_stay'], 'entry': R['ev_decision']['decomp']['n_entry'], 'exit': R['ev_decision']['decomp']['n_exit']}
other = {}
for k, (a, b) in {'2016-18_to_2019-22': ('2016-18', '2019-22'), '2019-22_to_2023-26': ('2019-22', '2023-26')}.items():
    pt = decomp(D[D.period == a], D[D.period == b], 'ev_decision'); other[k] = {kk: pt[kk] for kk in ('n_stay', 'n_entry', 'n_exit')}
steps = []
for yy in range(2016, 2026):
    pt = decomp(D[D.year == yy], D[D.year == yy + 1], 'ev_decision'); steps.append([yy, pt['n_stay'], pt['n_entry'], pt['n_exit']])
other['annual_steps_[from,stay,entry,exit]'] = steps
other['annual_steps_with_any_cell_lt5'] = sum(1 for s in steps if min(s[1:]) < 5)
R['cells_other'] = other
json.dump(R, open('res_r3_t3.json', 'w'), indent=1, default=float)
