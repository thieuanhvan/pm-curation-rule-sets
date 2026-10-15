# R5 B: liveness redo. Cohort = R3 T1 (non-bot evidence items arriving 2022-10-07 .. DATA_END-365 d).
# One exclusion window everywhere: events by the eventual decider within 7 days before the decision are excluded (matches the
# seven-day window of the time-varying Cox models), as are the decision itself, later events and the SUBMITTED event.
# (1) Full-window liveness (activity within 365 d, before decision) with 7-d exclusion: P(decided <= 365 d | live) - P(.. | not live).
# (2) Landmark at L = 30, 90 d: items still pending at L; live = qualifying event in [arr, arr+L); outcome = decision in (L, 365].
# Cluster bootstrap by submitter, B = 2,000. (3) Leave-top-submitter-out for the 1-y cohort decision share.
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261107); B = 2000; EXCL = 7.0
E = pd.read_pickle('../W3/w3_events_hmac.pkl'); H = E[~E.bot]
DATA_END = float(E.t.max()); D = lambda s: pd.Timestamp(s, tz='UTC').value / 864e11
ei = H[H.tt == 'EvidenceItem']
sub = ei[ei.act == 'SUBMITTED'].sort_values('t').drop_duplicates('tid').set_index('tid')
dec = ei[ei.act.isin(['ACCEPTED', 'REJECTED'])].sort_values('t').drop_duplicates('tid').set_index('tid')
it = pd.DataFrame({'arr': sub.t, 'subU': sub.u})
it['dec'] = dec.t.reindex(it.index); it['decU'] = dec.u.reindex(it.index)
it['dec'] = it.dec.where(it.dec.isna(), np.maximum(it.dec, it.arr))
oth = ei[ei.act != 'SUBMITTED'][['tid', 't', 'u', 'act']].merge(it[['arr', 'dec', 'decU', 'subU']], left_on='tid', right_index=True)
ok = (oth.t > oth.arr) & ~oth.act.isin(['ACCEPTED', 'REJECTED']) & (oth.dec.isna() | (oth.t < oth.dec)) \
     & ~(oth.decU.notna() & (oth.u == oth.decU) & (oth.t >= oth.dec - EXCL))
q = oth[ok]
a, b = D('2022-10-07'), DATA_END - 365
C = it[(it.arr >= a) & (it.arr < b)].copy(); C['age_dec'] = C.dec - C.arr
C['d365'] = C.dec.notna() & (C.age_dec <= 365)
first_q = q.assign(age=q.t - q.arr).groupby('tid').age.min()
C['firstAct'] = first_q.reindex(C.index)
C['live365'] = C.firstAct.notna() & (C.firstAct <= 365)
R = {'cohort_n': len(C), 'exclusion_window_days': EXCL}

def diff(df, live, out):
    p1 = df.loc[df[live], out].mean(); p0 = df.loc[~df[live], out].mean(); return p1, p0, p1 - p0
def boot(df, f):
    g = {u: x for u, x in df.groupby('subU')}; us = np.array(list(g)); res = []
    for _ in range(B): res.append(f(pd.concat([g[u] for u in rng.choice(us, len(us))])))
    return np.array(res)
ci = lambda v: [round(float(np.nanpercentile(v, 2.5)), 3), round(float(np.nanpercentile(v, 97.5)), 3)]

# (1) full window
p1, p0, d = diff(C, 'live365', 'd365'); bs = boot(C, lambda x: diff(x, 'live365', 'd365')[2])
R['full_window_7d'] = {'live_share': round(float(C.live365.mean()), 3), 'p_live': round(p1, 3), 'p_notlive': round(p0, 3), 'diff': round(d, 3), 'diff_ci': ci(bs),
    'share_of_365d_decisions_on_not_live': round(float((C.d365 & ~C.live365).sum() / C.d365.sum()), 3), 'n_live': int(C.live365.sum())}
# (2) landmarks
for L in (30, 90):
    S = C[C.dec.isna() | (C.age_dec >= L)].copy()
    S['liveL'] = S.firstAct.notna() & (S.firstAct < L)
    S['out'] = S.dec.notna() & (S.age_dec <= 365)
    p1, p0, d = diff(S, 'liveL', 'out'); bs = boot(S, lambda x: diff(x, 'liveL', 'out')[2])
    R[f'landmark_{L}d'] = {'at_risk': len(S), 'live_n': int(S.liveL.sum()), 'live_share': round(float(S.liveL.mean()), 3),
        'p_decided_by_365_live': round(p1, 3), 'p_not_live': round(p0, 3), 'diff': round(d, 3), 'diff_ci': ci(bs),
        'decided_n': int(S.out.sum())}
# (3) cohort 1-y decision share, all and leaving out the largest submitter (and top-5, aggregated)
f = lambda x: x.d365.mean()
R['cohort_decided_365'] = {'share': round(float(f(C)), 3), 'ci': ci(boot(C, f)), 'n': len(C), 'decided': int(C.d365.sum())}
vc = C.subU.value_counts()
for k in (1, 5):
    Ck = C[~C.subU.isin(vc.index[:k])]
    R[f'cohort_decided_365_drop_top{k}_submitters'] = {'share': round(float(f(Ck)), 3), 'ci': ci(boot(Ck, f)), 'n': len(Ck),
        **({'top_share_of_cohort': round(float(vc.iloc[:k].sum() / len(C)), 3), 'top_decided_share': round(float(C[C.subU.isin(vc.index[:k])].d365.mean()), 3)} if k >= 5 else {'top_share_of_cohort_rounded': round(float(vc.iloc[:k].sum() / len(C)), 1)})}
R['n_submitters_cohort'] = int(C.subU.nunique())
json.dump(R, open('res_b_liveness.json', 'w'), indent=1); print(json.dumps(R, indent=1))
