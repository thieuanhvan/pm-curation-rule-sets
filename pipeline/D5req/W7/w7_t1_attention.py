# W7 T1: does revision moderation crowd out evidence decisions within moderator and day?
# Input: ../W3/w3_events.pkl (pseudonymised, built by W3/prep_w3.py). No network. Aggregates only (k >= 5 moderators).
import json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings('ignore')
rng = np.random.default_rng(20261007)
E = pd.read_pickle('../W3/w3_events.pkl'); H = E[~E.bot].copy()
H['day'] = np.floor(H.t).astype(int)
R = {}
def P(k, v): R[k] = v; print(k, json.dumps(v, default=str)[:2500], flush=True)

mod = H[H.modAt].copy()
isEv = mod.act.isin(['ACCEPTED', 'REJECTED']) & (mod.st == 'EvidenceItem') & (mod.u != mod.evSub)
isRev = mod.act.isin(['REVISION_ACCEPTED', 'REVISION_REJECTED']) & (mod.u != mod.revSugg)
isAsr = mod.act.isin(['ASSERTION_ACCEPTED', 'ASSERTION_REJECTED', 'ASSERTION_APPROVED'])
isSugg = mod.act.eq('REVISION_SUGGESTED')
isCom = mod.act.isin(['COMMENTED', 'REVISION_COMMENTED'])
isSub = mod.act.isin(['SUBMITTED', 'ASSERTION_SUBMITTED'])
isDep = mod.act.str.startswith('DEPRECATED')
mod['typ'] = np.select([isEv, isRev, isAsr, isSugg, isCom, isSub, isDep],
                       ['ev_decision', 'revision_moderation', 'assertion_moderation', 'revision_suggestion', 'comment', 'submission', 'deprecation'], 'other')
# revision moderations on an evidence item that the same moderator decides on the same day (mechanical bundling)
evd = mod[isEv][['u', 'day', 'tid']]
key_same = set(zip(evd.u, evd.day, evd.tid))
mod['rev_same_item'] = isRev & (mod.tt == 'EvidenceItem') & [(u, d, i) in key_same for u, d, i in zip(mod.u, mod.day, mod.tid)]
mod['typ2'] = np.where(mod.rev_same_item, 'revision_moderation_same_item', mod.typ)
D = pd.crosstab([mod.u, mod.day], mod.typ2).reset_index()
for c in ['ev_decision', 'revision_moderation', 'revision_moderation_same_item', 'assertion_moderation', 'revision_suggestion', 'comment', 'submission', 'deprecation', 'other']:
    if c not in D: D[c] = 0
D['rev_all'] = D.revision_moderation + D.revision_moderation_same_item
D['own_work'] = D.revision_suggestion + D.comment + D.submission
D['n_all'] = D[['ev_decision', 'rev_all', 'assertion_moderation', 'revision_suggestion', 'comment', 'submission', 'deprecation', 'other']].sum(1)
D['year'] = pd.to_datetime(D.day * 864e11).dt.year
D['period'] = pd.cut(D.year, [2014, 2018, 2022, 2027], labels=['2015-18', '2019-22', '2023-26']).astype(str)
D = D.sort_values(['u', 'day']).reset_index(drop=True)
# lagged revision moderation (previous 1..7 calendar days, any day of that moderator)
lag7 = np.zeros(len(D)); lag1 = np.zeros(len(D)); evlag7 = np.zeros(len(D))
for u, g in D.groupby('u'):
    d = g.day.values; r = g.revision_moderation.values + g.revision_moderation_same_item.values; e = g.ev_decision.values
    cr = np.concatenate([[0], np.cumsum(r)]); ce = np.concatenate([[0], np.cumsum(e)])
    lo = np.searchsorted(d, d - 7, 'left'); hi = np.searchsorted(d, d, 'left')
    lag7[g.index] = cr[hi] - cr[lo]; evlag7[g.index] = ce[hi] - ce[lo]
    lo1 = np.searchsorted(d, d - 1, 'left'); lag1[g.index] = cr[hi] - cr[lo1]
D['rev_lag1_7'] = lag7; D['rev_lag1'] = lag1; D['ev_lag1_7'] = evlag7
S = D[(D.year >= 2016)].copy()
P('panel', {'moderator_days': len(S), 'moderators': int(S.u.nunique()), 'years': [2016, 2026],
            'moderators_by_period': S.groupby('period').u.nunique().to_dict(),
            'moderators_in_both_2015-18_and_2023-26': int(len(set(S[S.period == '2015-18'].u) & set(S[S.period == '2023-26'].u))),
            'moderators_in_>=2_periods': int((S.groupby('u').period.nunique() >= 2).sum())})

def bins(x, edges=(0, 1, 5, 20), lab='r'):
    x = np.asarray(x); out = pd.DataFrame(index=range(len(x)))
    for i in range(1, len(edges)):
        lo = edges[i]; hi = edges[i + 1] if i + 1 < len(edges) else np.inf
        out[f'{lab}_{lo}' + (f'-{int(hi) - 1}' if np.isfinite(hi) else '+')] = ((x >= lo) & (x < hi)).astype(float)
    return out

def fe_fit(df, y, X, family='poisson', fe_u=True, fe_y=True):
    d = df.reset_index(drop=True); X = X.reset_index(drop=True)
    if fe_u:  # drop moderators with no outcome events (FE Poisson convention)
        keep = d.groupby('u')[y].transform('sum') > 0; d = d[keep].reset_index(drop=True)
        X = X.loc[keep.values].reset_index(drop=True)
    Z = X.copy()
    if fe_y: Z = pd.concat([Z, pd.get_dummies(d.year, prefix='y', dtype=float).iloc[:, 1:]], axis=1)
    if fe_u: Z = pd.concat([Z, pd.get_dummies(d.u, prefix='m', dtype=float).iloc[:, 1:]], axis=1)
    Z = Z.loc[:, Z.std() > 0].assign(const=1.0)
    g = pd.factorize(d.u)[0]
    if family == 'poisson':
        r = sm.GLM(d[y].values, Z, family=sm.families.Poisson()).fit(cov_type='cluster', cov_kwds={'groups': g})
    else:
        r = sm.NegativeBinomial(d[y].values, Z).fit(disp=0, maxiter=500, method='bfgs', cov_type='cluster', cov_kwds={'groups': g})
    ci = r.conf_int()
    o = {c: [round(float(np.exp(r.params[c])), 3), round(float(np.exp(ci.loc[c, 0])), 3), round(float(np.exp(ci.loc[c, 1])), 3)] for c in X.columns if c in r.params.index}
    o['n_days'] = len(d); o['n_moderators'] = int(d.u.nunique()); o['events'] = int(d[y].sum())
    if family != 'poisson': o['alpha'] = round(float(r.params.get('alpha', np.nan)), 3)
    return o

# ---- M1-M4: same-day association (IRR vs days with 0 revision moderations of other items)
B_rev = bins(S.revision_moderation.values, lab='revOther')
B_own = bins(S.own_work.values, lab='own')
M = {}
M['M1_poisson_FEmod_FEyear_revOtherItems'] = fe_fit(S, 'ev_decision', B_rev)
M['M2_plus_own_work_control'] = fe_fit(S, 'ev_decision', pd.concat([B_rev, B_own], axis=1))
M['M3_negbin_FEmod_FEyear'] = fe_fit(S, 'ev_decision', pd.concat([B_rev, B_own], axis=1), family='nb')
M['M1b_log1p_revOther_poisson'] = fe_fit(S, 'ev_decision', pd.DataFrame({'log1p_revOther': np.log1p(S.revision_moderation.values)}))
M['M1c_log1p_revAll_incl_same_item_poisson'] = fe_fit(S, 'ev_decision', pd.DataFrame({'log1p_revAll': np.log1p(S.rev_all.values)}))
# M4 extensive margin: any evidence decision (Poisson on binary ~ risk ratio)
S['any_ev'] = (S.ev_decision > 0).astype(int)
M['M4_any_ev_decision_RR'] = fe_fit(S, 'any_ev', pd.concat([B_rev, B_own], axis=1))
# M5 lagged: revision moderation in previous 1..7 days (and previous day) with same-day control
B_l7 = bins(S.rev_lag1_7.values, (0, 1, 10, 50), 'revLag1_7')
M['M5_lag1_7_poisson'] = fe_fit(S, 'ev_decision', pd.concat([B_l7, B_rev, B_own], axis=1))
M['M5b_lag1_log1p'] = fe_fit(S, 'ev_decision', pd.DataFrame({'log1p_revPrevDay': np.log1p(S.rev_lag1.values), 'log1p_revLag1_7': np.log1p(S.rev_lag1_7.values),
                                                               'log1p_revOtherToday': np.log1p(S.revision_moderation.values), 'log1p_evLag1_7': np.log1p(S.ev_lag1_7.values)}))
# M6 period subsample (2023-26 only)
S23 = S[S.year >= 2023]
M['M6_2023_26_only_poisson'] = fe_fit(S23, 'ev_decision', pd.concat([bins(S23.revision_moderation.values, lab='revOther'), bins(S23.own_work.values, lab='own')], axis=1))
# M7 weekly panel (all weeks with any activity of the moderator)
S['wk'] = S.day // 7
W = S.groupby(['u', 'wk']).agg(ev=('ev_decision', 'sum'), rev=('revision_moderation', 'sum'), own=('own_work', 'sum'), year=('year', 'first')).reset_index()
W = W.sort_values(['u', 'wk']); W['rev_prev'] = W.groupby('u').rev.shift(1).where(W.groupby('u').wk.diff() == 1, 0).fillna(0)
M['M7_weekly_poisson'] = fe_fit(W, 'ev', pd.DataFrame({'log1p_revOther_week': np.log1p(W.rev.values), 'log1p_revOther_prevWeek': np.log1p(W.rev_prev.values), 'log1p_own_week': np.log1p(W.own.values)}))
P('crowd_out_models', M)

# ---- C: within-moderator period decline (period FE, with / without moderator FE, with / without load controls)
Pd = pd.get_dummies(S.period, dtype=float)[['2019-22', '2023-26']].reset_index(drop=True)
C = {}
C['no_moderator_FE'] = fe_fit(S, 'ev_decision', Pd, fe_u=False, fe_y=False)
C['moderator_FE'] = fe_fit(S, 'ev_decision', Pd, fe_u=True, fe_y=False)
C['moderator_FE_plus_load_controls'] = fe_fit(S, 'ev_decision', pd.concat([Pd, B_rev, B_own], axis=1), fe_u=True, fe_y=False)
# only days with at least one moderation action of any kind
Sm = S[(S.ev_decision + S.rev_all + S.assertion_moderation) > 0]
C['moderation_days_only_moderator_FE'] = fe_fit(Sm, 'ev_decision', pd.get_dummies(Sm.period, dtype=float)[['2019-22', '2023-26']], fe_u=True, fe_y=False)
# the same for revision moderation as outcome: did revision moderation per active day also fall within moderator?
C['revision_moderation_outcome_moderator_FE'] = fe_fit(S, 'rev_all', Pd, fe_u=True, fe_y=False)
C['all_moderation_actions_outcome_moderator_FE'] = fe_fit(S.assign(allmod=S.ev_decision + S.rev_all + S.assertion_moderation), 'allmod', Pd, fe_u=True, fe_y=False)
P('within_moderator_period_effects_IRR_vs_2015-18', C)

# ---- D: action composition by period (pooled; mean of moderator shares for moderators with >= 20 actions)
T = ['ev_decision', 'rev_all', 'assertion_moderation', 'revision_suggestion', 'comment', 'submission', 'deprecation', 'other']
comp = {}
for p, g in S.groupby('period'):
    tot = g[T].sum(); o = {'moderators': int(g.u.nunique()), 'active_days': len(g), 'actions_per_active_day': round(float(g.n_all.mean()), 2)}
    o['pooled_share'] = {k: round(float(tot[k] / tot.sum()), 3) for k in T}
    o['per_active_day'] = {k: round(float(g[k].mean()), 3) for k in T}
    pm = g.groupby('u')[T].sum(); pm = pm[pm.sum(1) >= 20]
    if len(pm) >= 5:
        sh = pm.div(pm.sum(1), axis=0)
        o['mean_of_moderator_shares'] = {k: round(float(sh[k].mean()), 3) for k in T}; o['moderators_ge20_actions'] = len(pm)
        bs = [sh.iloc[rng.integers(0, len(sh), len(sh))]['ev_decision'].mean() for _ in range(2000)]
        o['mean_moderator_share_ev_decision_CI'] = [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]
        o['ev_share_of_moderation_actions_pooled'] = round(float(tot.ev_decision / (tot.ev_decision + tot.rev_all + tot.assertion_moderation)), 3)
    comp[p] = o
# yearly pooled share of evidence decisions among moderation actions and per active day
yr = {}
for y, g in S.groupby('year'):
    t = g[T].sum(); m = t.ev_decision + t.rev_all + t.assertion_moderation
    yr[int(y)] = {'ev_share_of_moderation': round(float(t.ev_decision / m), 3), 'moderation_per_active_day': round(float(m / len(g)), 2), 'ev_per_active_day': round(float(t.ev_decision / len(g)), 3),
                  'own_work_per_active_day': round(float((t.revision_suggestion + t.comment + t.submission) / len(g)), 2), 'share_days_with_any_moderation': round(float(((g.ev_decision + g.rev_all + g.assertion_moderation) > 0).mean()), 3)}
comp['by_year'] = yr
P('action_composition', comp)

# ---- E: shift-share (Foster-Haltiwanger-Krizan) of evidence decisions per active moderator-day
def fhk(g0, g1):
    a0 = g0.groupby('u').agg(d=('ev_decision', 'size'), e=('ev_decision', 'sum')); a1 = g1.groupby('u').agg(d=('ev_decision', 'size'), e=('ev_decision', 'sum'))
    w0 = a0.d / a0.d.sum(); w1 = a1.d / a1.d.sum(); r0 = a0.e / a0.d; r1 = a1.e / a1.d
    R0 = float((w0 * r0).sum()); R1 = float((w1 * r1).sum())
    st = a0.index.intersection(a1.index); en = a1.index.difference(a0.index); ex = a0.index.difference(a1.index)
    within = float((w0[st] * (r1[st] - r0[st])).sum()); between = float(((w1[st] - w0[st]) * (r0[st] - R0)).sum())
    cross = float(((w1[st] - w0[st]) * (r1[st] - r0[st])).sum()); entry = float((w1[en] * (r1[en] - R0)).sum()); exit_ = -float((w0[ex] * (r0[ex] - R0)).sum())
    return {'R0': R0, 'R1': R1, 'delta': R1 - R0, 'within': within, 'between': between, 'cross': cross, 'entry': entry, 'exit': exit_,
            'n_stay': len(st), 'n_entry': len(en), 'n_exit': len(ex)}
def boot_fhk(g0, g1, B=2000):
    us = np.array(sorted(set(g0.u) | set(g1.u))); G0 = {u: x for u, x in g0.groupby('u')}; G1 = {u: x for u, x in g1.groupby('u')}
    out = []
    for _ in range(B):
        s = rng.choice(us, len(us)); a, b = [], []
        for k, u in enumerate(s):
            if u in G0: a.append(G0[u].assign(u=f'{u}#{k}'))
            if u in G1: b.append(G1[u].assign(u=f'{u}#{k}'))
        if not a or not b: continue
        out.append(fhk(pd.concat(a), pd.concat(b)))
    return out
SS = {}
pairs = {'2016-18_to_2023-26': (S[S.year.between(2016, 2018)], S[S.year.between(2023, 2026)]),
         '2016-18_to_2019-22': (S[S.year.between(2016, 2018)], S[S.year.between(2019, 2022)]),
         '2019-22_to_2023-26': (S[S.year.between(2019, 2022)], S[S.year.between(2023, 2026)])}
for k, (g0, g1) in pairs.items():
    pt = fhk(g0, g1); bs = boot_fhk(g0, g1)
    o = {kk: round(v, 3) if isinstance(v, float) else v for kk, v in pt.items()}
    for kk in ('delta', 'within', 'between', 'cross', 'entry', 'exit'):
        o[kk + '_CI'] = [round(float(np.percentile([b[kk] for b in bs], 2.5)), 3), round(float(np.percentile([b[kk] for b in bs], 97.5)), 3)]
    o['composition_total(between+entry+exit)'] = round(pt['between'] + pt['entry'] + pt['exit'], 3)
    o['composition_total_CI'] = [round(float(np.percentile([b['between'] + b['entry'] + b['exit'] for b in bs], q)), 3) for q in (2.5, 97.5)]
    o['within_plus_cross'] = round(pt['within'] + pt['cross'], 3)
    o['within_plus_cross_CI'] = [round(float(np.percentile([b['within'] + b['cross'] for b in bs], q)), 3) for q in (2.5, 97.5)]
    if pt['n_stay'] < 5: o['note'] = 'fewer than 5 stayers: within term rests on < 5 people, report only in aggregate with caution'
    SS[k] = o
# chained annual decomposition 2016 -> 2026 (sum of year-to-year terms)
ch = {'within': 0, 'between': 0, 'cross': 0, 'entry': 0, 'exit': 0}; steps = []
for y in range(2016, 2026):
    pt = fhk(S[S.year == y], S[S.year == y + 1]); steps.append({'from': y, 'n_stay': pt['n_stay'], 'delta': round(pt['delta'], 3), 'within': round(pt['within'], 3)})
    for kk in ch: ch[kk] += pt[kk]
ch = {k: round(v, 3) for k, v in ch.items()}; ch['total'] = round(sum(ch.values()), 3)
ch['composition_total'] = round(ch['between'] + ch['entry'] + ch['exit'], 3); ch['within_plus_cross'] = round(ch['within'] + ch['cross'], 3)
ch['min_stayers_per_step'] = min(s['n_stay'] for s in steps); ch['steps'] = steps
SS['chained_annual_2016_to_2026'] = ch
P('shift_share_FHK_ev_per_active_day', SS)
json.dump(R, open('res_w7_t1_attention.json', 'w'), indent=1, default=str)
