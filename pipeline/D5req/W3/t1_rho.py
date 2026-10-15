# T1: rho on live arrivals; decider-effort normalisation; reconciliation rho=0.47 vs simulation load 2.2.
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261007)
E = pd.read_pickle('w3_events.pkl'); H = E[~E.bot]
NOW = pd.Timestamp('2026-10-07', tz='UTC').value / 864e11
D = lambda s: pd.Timestamp(s, tz='UTC').value / 864e11
ei = H[H.tt == 'EvidenceItem']
sub = ei[ei.act == 'SUBMITTED'].drop_duplicates('tid').set_index('tid')
dec = ei[ei.act.isin(['ACCEPTED', 'REJECTED'])].sort_values('t').drop_duplicates('tid').set_index('tid')
it = pd.DataFrame({'arr': sub.t, 'subU': sub.u})
it['dec'] = dec.t.reindex(it.index); it['decAct'] = dec.act.reindex(it.index); it['decU'] = dec.u.reindex(it.index)
it['dec'] = it.dec.where(it.dec.isna(), np.maximum(it.dec, it.arr))
it['out'] = np.where(it.dec.isna(), 'PEND', np.where(it.decAct == 'ACCEPTED', 'ACC', np.where(it.decU == it.subU, 'WDR', 'REJ')))
oth = ei[ei.act != 'SUBMITTED']
act_any = oth.groupby('tid').t.apply(np.array).to_dict()
act_ns = oth[oth.u != oth.evSub].groupby('tid').t.apply(np.array).to_dict()
def has_within(tid, arr, w, src):
    a = src.get(tid); return a is not None and bool(((a > arr) & (a <= arr + w)).any())
for w in (90, 365):
    it[f'live{w}'] = [has_within(i, a, w, act_any) for i, a in zip(it.index, it.arr)]
    it[f'liveNS{w}'] = [has_within(i, a, w, act_ns) for i, a in zip(it.index, it.arr)]
R = {}
MO = 365.25 / 12

def window(a, b, label):
    A = it[(it.arr >= a) & (it.arr < b)]; Dd = it[(it.dec >= a) & (it.dec < b)]
    mo = (b - a) / MO
    o = {'window': label, 'months': round(mo, 1), 'complete_365d_followup_for_all_arrivals': bool(b + 365 <= NOW)}
    o['arrivals'] = len(A); o['arrivals_per_month'] = round(len(A) / mo, 1)
    for w in (90, 365):
        o[f'live{w}_arrivals'] = int(A[f'live{w}'].sum()); o[f'liveNS{w}_arrivals'] = int(A[f'liveNS{w}'].sum())
    o['decisions_all'] = len(Dd); o['dec_per_month'] = round(len(Dd) / mo, 1)
    for k in ('ACC', 'REJ', 'WDR'): o[f'dec_{k}'] = int((Dd.out == k).sum())
    o['dec_on_items_arrived_in_window'] = int(((Dd.arr >= a) & (Dd.arr < b)).sum())
    o['dec_on_items_arrived_before_window'] = int((Dd.arr < a).sum())
    o['dec_on_live365_items'] = int(Dd.live365.sum())
    nM = int(np.ceil(mo))
    am = np.minimum(np.floor((A.arr.values - a) / MO).astype(int), nM - 1); dm = np.minimum(np.floor((Dd.dec.values - a) / MO).astype(int), nM - 1)
    cnt = lambda x, w=None: np.bincount(x, w, nM)[:nM]
    arrM = cnt(am); liveM = cnt(am, A.live365.values.astype(float)); liveNSM = cnt(am, A.liveNS365.values.astype(float))
    decM = cnt(dm); decNWM = cnt(dm, (Dd.out != 'WDR').values.astype(float)); decAccM = cnt(dm, (Dd.out == 'ACC').values.astype(float))
    defs = {'rho_all = decisions/arrivals': (decM, arrM), 'rho_excl_withdrawals': (decNWM, arrM), 'rho_accept_only': (decAccM, arrM),
            'rho_live365 = decisions/live arrivals': (decM, liveM), 'rho_live365_excl_withdrawals': (decNWM, liveM),
            'rho_liveNS365 = decisions/arrivals touched by non-submitter in 365 d': (decM, liveNSM)}
    bl = 3; idxs = [np.concatenate([np.arange(s, s + bl) % nM for s in rng.integers(0, nM, nM // bl + 1)])[:nM] for _ in range(2000)]
    for k, (n, d) in defs.items():
        est = n.sum() / d.sum(); bs = [n[i].sum() / d[i].sum() for i in idxs]
        o[k] = [round(est, 3), round(np.percentile(bs, 2.5), 3), round(np.percentile(bs, 97.5), 3)]
    o['load = arrivals/decisions'] = round(len(A) / len(Dd), 2)
    c = A[(A.arr + 365 <= NOW)]
    if len(c):
        x = ((c.dec - c.arr) <= 365).values
        o['cohort_share_decided_within_365d'] = [round(x.mean(), 3)] + [round(v, 3) for v in np.percentile([x[rng.integers(0, len(x), len(x))].mean() for _ in range(1000)], [2.5, 97.5])]
        o['cohort_n'] = len(c)
        cl = c[c.live365]; o['cohort_live365_share_decided_within_365d'] = round(((cl.dec - cl.arr) <= 365).mean(), 3)
    return o
W = {'cal2023_25': (D('2023-01-01'), D('2026-01-01')), 'live_complete_2022-10-07..2025-10-06': (D('2022-10-07'), D('2025-10-07')),
     'sim_window_2023-01..2026-09': (D('2023-01-01'), D('2026-10-01')), 'pre_2021_22': (D('2021-01-01'), D('2023-01-01')), 'early_2017_19': (D('2017-01-01'), D('2020-01-01'))}
R['windows'] = {k: window(a, b, k) for k, (a, b) in W.items()}
yt = {}
for y in range(2015, 2027):
    a, b = D(f'{y}-01-01'), min(D(f'{y+1}-01-01'), NOW)
    A = it[(it.arr >= a) & (it.arr < b)]; Dd = it[(it.dec >= a) & (it.dec < b)]
    yt[y] = {'arr': len(A), 'live365_share': round(A.live365.mean(), 3), 'liveNS365_share': round(A.liveNS365.mean(), 3),
             'dec': len(Dd), 'dec_noWDR': int((Dd.out != 'WDR').sum()), 'rho_all': round(len(Dd) / max(len(A), 1), 3),
             'rho_live365': round(len(Dd) / max(A.live365.sum(), 1), 3), 'followup_complete': bool(b + 365 <= NOW)}
R['by_year_rho'] = yt
# ---------- decider effort (moderators-at-time = users after their first moderation of someone else's content)
mod = H[H.modAt].copy()
evdec = H[(H.act.isin(['ACCEPTED', 'REJECTED'])) & (H.st == 'EvidenceItem') & (H.u != H.evSub) & H.modAt].copy()
revmod = H[H.act.isin(['REVISION_ACCEPTED', 'REVISION_REJECTED']) & (H.u != H.revSugg) & H.modAt].copy()
asmod = H[H.act.isin(['ASSERTION_ACCEPTED', 'ASSERTION_REJECTED']) & H.modAt].copy()
for df in (mod, evdec, revmod, asmod):
    df['day'] = np.floor(df.t).astype(int); df['yr'] = pd.to_datetime(df.t * 864e11).dt.year
eff = {}
for y in range(2015, 2027):
    m = mod[mod.yr == y]; e = evdec[evdec.yr == y]; r = revmod[revmod.yr == y]; s = asmod[asmod.yr == y]
    actdays = m.groupby(['u', 'day']).size(); decdays = e.groupby(['u', 'day']).size()
    ad = actdays.reset_index()[['u', 'day']]; key = pd.MultiIndex.from_frame(ad)
    ad['ev'] = decdays.reindex(key).fillna(0).values
    ad['mod'] = ad.ev + r.groupby(['u', 'day']).size().reindex(key).fillna(0).values + s.groupby(['u', 'day']).size().reindex(key).fillna(0).values
    o = {'active_moderators': int(m.u.nunique()), 'moderators_with_evidence_decision': int(e.u.nunique()),
         'moderator_active_days': int(len(actdays)), 'moderator_decision_days': int(len(decdays)),
         'evidence_decisions_on_others': int(len(e)), 'revision_moderations_of_others': int(len(r))}
    if len(ad) >= 5:
        us = ad.u.unique(); g = {u: ad[ad.u == u] for u in us}
        bsd = [ad.ev.values[i].mean() for i in (rng.integers(0, len(ad), len(ad)) for _ in range(1000))]
        o['ev_decisions_per_moderator_active_day'] = [round(ad.ev.mean(), 3), round(np.percentile(bsd, 2.5), 3), round(np.percentile(bsd, 97.5), 3)]
        if len(us) >= 5:
            bsu = []
            for _ in range(1000):
                x = pd.concat([g[u] for u in rng.choice(us, len(us))]); bsu.append(x.ev.sum() / len(x))
            o['ev_decisions_per_active_day_CI_cluster_moderator'] = [round(np.percentile(bsu, 2.5), 3), round(np.percentile(bsu, 97.5), 3)]
        else: o['ev_decisions_per_active_day_CI_cluster_moderator'] = 'fewer than 5 moderators: not shown'
        o['all_moderation_actions_per_moderator_active_day'] = [round(ad['mod'].mean(), 3)] + [round(v, 3) for v in np.percentile([ad['mod'].values[i].mean() for i in (rng.integers(0, len(ad), len(ad)) for _ in range(1000))], [2.5, 97.5])]
        if len(decdays): o['ev_decisions_per_decision_day'] = [round(decdays.mean(), 2)] + [round(v, 2) for v in np.percentile([decdays.values[i].mean() for i in (rng.integers(0, len(decdays), len(decdays)) for _ in range(1000))], [2.5, 97.5])]
        o['share_active_days_with_ev_decision'] = round(len(decdays) / len(actdays), 3)
    eff[y] = o
R['decider_effort_by_year'] = eff
json.dump(R, open('res_t1_rho.json', 'w'), indent=1, default=str)
for k, v in R['windows'].items(): print(k, json.dumps(v))
for y, v in yt.items(): print(y, v)
for y, v in eff.items(): print(y, json.dumps(v))
it.to_pickle('w3_items.pkl')
