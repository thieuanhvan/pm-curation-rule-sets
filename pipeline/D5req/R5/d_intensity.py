# R5 D: evidence-decision intensity with the active-day denominator restricted to event types logged in BOTH platform versions
# (v1 before 2022-04-09, v2 after). v2-only types (deprecations, feature creation, supersession, comment deletion, source-suggestion
# curation, assertion approval/revert, complex molecular profiles) are dropped. 'strict' also drops REVISION_COMMENTED (5,086 v1 vs 93 v2).
# Also: moderators active per year (headcount), and the extensive-margin crowd-out RR with and without the own-curation control.
# Input ../W3/w3_events_hmac.pkl. Aggregates only (all cells >= 5 moderators except where flagged).
import json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings('ignore'); rng = np.random.default_rng(20261108)
E = pd.read_pickle('../W3/w3_events_hmac.pkl'); H = E[~E.bot].copy(); H['day'] = np.floor(H.t).astype(int)
V2 = pd.Timestamp('2022-04-09', tz='UTC').value / 864e11
cnt = H.groupby(['act', H.t >= V2]).size().unstack(fill_value=0)
COMMON = sorted(set(cnt.index[(cnt[False] > 0) & (cnt[True] > 0)]) - {'COMPLEX_MOLECULAR_PROFILE_CREATED'})
STRICT = sorted(set(COMMON) - {'REVISION_COMMENTED'})
R = {'common_types': COMMON, 'v2_only_or_excluded': sorted(set(cnt.index) - set(COMMON))}
mod = H[H.modAt].copy()
mod['ev'] = (mod.act.isin(['ACCEPTED', 'REJECTED']) & (mod.st == 'EvidenceItem') & (mod.u != mod.evSub)).astype(int)
mod['revmod'] = (mod.act.isin(['REVISION_ACCEPTED', 'REVISION_REJECTED']) & (mod.u != mod.revSugg)).astype(int)
evd = mod[mod.ev == 1][['u', 'day', 'tid']]; key_same = set(zip(evd.u, evd.day, evd.tid))
same = (mod.revmod == 1) & (mod.tt == 'EvidenceItem') & np.array([(u, d, i) in key_same for u, d, i in zip(mod.u, mod.day, mod.tid)])
mod['revmod'] = mod.revmod.where(~same, 0)   # as W7: revision moderations bundled with a same-day decision on the same item are not 'other' load
mod['own'] = mod.act.isin(['REVISION_SUGGESTED', 'COMMENTED', 'REVISION_COMMENTED', 'SUBMITTED', 'ASSERTION_SUBMITTED']).astype(int)
mod['anymod'] = (mod.ev + mod.revmod + mod.act.isin(['ASSERTION_ACCEPTED', 'ASSERTION_REJECTED', 'ASSERTION_APPROVED']).astype(int))
def panel(types):
    m = mod if types is None else mod[mod.act.isin(types)]
    D = m.groupby(['u', 'day'])[['ev', 'revmod', 'own', 'anymod']].sum().reset_index()
    D['year'] = pd.to_datetime(D.day * 864e11).dt.year; D = D[D.year >= 2016].copy()
    D['period'] = pd.cut(D.year, [2015, 2018, 2022, 2027], labels=['2016-18', '2019-22', '2023-26']).astype(str); return D
def fe(D, y, X, fe_u=True):
    d = D.reset_index(drop=True); X = X.reset_index(drop=True)
    if fe_u:
        k = d.groupby('u')[y].transform('sum') > 0; d = d[k].reset_index(drop=True); X = X.loc[k.values].reset_index(drop=True)
        Z = pd.concat([X, pd.get_dummies(d.u, prefix='m', dtype=float).iloc[:, 1:]], axis=1)
    else: Z = X.copy()
    Z = Z.loc[:, Z.std() > 0].assign(const=1.0)
    r = sm.GLM(d[y].values, Z, family=sm.families.Poisson()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.u)[0]})
    ci = r.conf_int(); return {c: [round(float(np.exp(r.params[c])), 3), round(float(np.exp(ci.loc[c, 0])), 3), round(float(np.exp(ci.loc[c, 1])), 3)] for c in X.columns if c in r.params}
def intensity(D, tag):
    g0, g1 = D[D.period == '2016-18'], D[D.period == '2023-26']
    r0, r1 = g0.ev.mean(), g1.ev.mean()
    Pd = pd.get_dummies(D.period, dtype=float)[['2019-22', '2023-26']]
    o = {'active_days_2016_18': len(g0), 'active_days_2023_26': len(g1), 'ev_per_day_2016_18': round(float(r0), 4), 'ev_per_day_2023_26': round(float(r1), 4),
         'fold': round(float(r0 / r1), 3), 'FE_ratio': fe(D, 'ev', Pd)['2023-26'], 'noFE_ratio': fe(D, 'ev', Pd, False)['2023-26']}
    Dm = D[D.anymod > 0]; m0, m1 = Dm[Dm.period == '2016-18'].ev.mean(), Dm[Dm.period == '2023-26'].ev.mean()
    o['moderation_days_only_fold'] = round(float(m0 / m1), 3)
    # moderator-cluster bootstrap of the fold
    us = np.array(D.u.unique()); G = {u: x for u, x in D.groupby('u')}; bs = []
    for _ in range(2000):
        x = pd.concat([G[u] for u in rng.choice(us, len(us))]); a, b = x[x.period == '2016-18'].ev.mean(), x[x.period == '2023-26'].ev.mean()
        if b > 0: bs.append(a / b)
    o['fold_CI'] = [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]
    R[tag] = o
for tag, ty in (('all_types', None), ('common_types', COMMON), ('strict_common', STRICT)): intensity(panel(ty), tag)
# headcount: moderators with >= 1 active day per year (any type) and with >= 1 evidence decision on others' items
D = panel(None)
R['moderators_active_per_year'] = D.groupby('year').u.nunique().to_dict()
R['moderators_with_ev_decision_per_year'] = D[D.ev > 0].groupby('year').u.nunique().to_dict()
R['moderators_with_ge20_active_days_per_year'] = D.groupby(['year', 'u']).size().ge(20).groupby('year').sum().to_dict()
# extensive margin crowd-out (as W7 M4): P(any evidence decision) by same-day revision-moderation band, year + moderator FE
def bins(x, lab):
    x = np.asarray(x); return pd.DataFrame({f'{lab}_1-4': ((x >= 1) & (x < 5)).astype(float), f'{lab}_5-19': ((x >= 5) & (x < 20)).astype(float), f'{lab}_20+': (x >= 20).astype(float)})
for tag, ty in (('all_types', None), ('common_types', COMMON)):
    D = panel(ty).reset_index(drop=True); D['anyev'] = (D.ev > 0).astype(int)
    Yd = pd.get_dummies(D.year, prefix='y', dtype=float).iloc[:, 1:]
    Br = bins(D.revmod.values, 'rev'); Bo = bins(D.own.values, 'own')
    R[f'crowdout_{tag}'] = {'RR_any_ev_with_own_control': {k: v for k, v in fe(D, 'anyev', pd.concat([Br, Bo, Yd], axis=1)).items() if k.startswith('rev')},
                            'RR_any_ev_without_own_control': {k: v for k, v in fe(D, 'anyev', pd.concat([Br, Yd], axis=1)).items() if k.startswith('rev')},
                            'IRR_count_with_own_control': {k: v for k, v in fe(D, 'ev', pd.concat([Br, Bo, Yd], axis=1)).items() if k.startswith('rev')},
                            'IRR_count_without_own_control': {k: v for k, v in fe(D, 'ev', pd.concat([Br, Yd], axis=1)).items() if k.startswith('rev')},
                            'days': len(D)}
json.dump(R, open('res_d_intensity.json', 'w'), indent=1, default=str); print(json.dumps(R, indent=1, default=str))
