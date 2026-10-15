# R3 T1: live throughput with one explicit cohort definition (round-3 PM reviewer).
# Input: ../W3/w3_events_hmac.pkl (keyed pseudonyms). Aggregates only.
# Cohort C: evidence items (non-bot submitter) arriving in W = [2022-10-07, DATA_END - 365 d), so every arrival has >= 365 d follow-up.
# Liveness (new, L1): any non-bot event on the item (incl. revisions/comments/flags on it) strictly after arrival, within 365 d,
#   strictly BEFORE the item's first decision, excluding (i) the decision event, (ii) any event by the eventual decider within 24 h
#   before the decision (same-day work that is part of the decision), (iii) the SUBMITTED event.
# L1ns: as L1 but only events by someone other than the submitter.  L0 = old definition (any non-bot event within 365 d, incl. decision).
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261008)
E = pd.read_pickle('../W3/w3_events_hmac.pkl'); H = E[~E.bot]
DATA_END = float(E.t.max())
D = lambda s: pd.Timestamp(s, tz='UTC').value / 864e11
ei = H[H.tt == 'EvidenceItem']
sub = ei[ei.act == 'SUBMITTED'].sort_values('t').drop_duplicates('tid').set_index('tid')
dec = ei[ei.act.isin(['ACCEPTED', 'REJECTED'])].sort_values('t').drop_duplicates('tid').set_index('tid')
it = pd.DataFrame({'arr': sub.t, 'subU': sub.u})
it['dec'] = dec.t.reindex(it.index); it['decAct'] = dec.act.reindex(it.index); it['decU'] = dec.u.reindex(it.index)
it['dec'] = it.dec.where(it.dec.isna(), np.maximum(it.dec, it.arr))
it['out'] = np.where(it.dec.isna(), 'PEND', np.where(it.decAct == 'ACCEPTED', 'ACC', np.where(it.decU == it.subU, 'WDR', 'REJ')))
oth = ei[(ei.act != 'SUBMITTED')][['tid', 't', 'u', 'act']]
oth = oth.merge(it[['arr', 'dec', 'decU', 'subU']], left_on='tid', right_index=True)
w365 = (oth.t > oth.arr) & (oth.t <= oth.arr + 365)
isdec = oth.act.isin(['ACCEPTED', 'REJECTED'])
before_dec = oth.dec.isna() | (oth.t < oth.dec)
decider_sameday = oth.decU.notna() & (oth.u == oth.decU) & (oth.t >= oth.dec - 1.0)
L0 = set(oth[w365].tid)
ok1 = w365 & ~isdec & before_dec & ~decider_sameday
L1 = set(oth[ok1].tid); L1ns = set(oth[ok1 & (oth.u != oth.subU)].tid)
it['L0'] = it.index.isin(L0); it['L1'] = it.index.isin(L1); it['L1ns'] = it.index.isin(L1ns)
a, b = D('2022-10-07'), DATA_END - 365
C = it[(it.arr >= a) & (it.arr < b)].copy()
C['d365'] = C.dec.notna() & (C.dec - C.arr <= 365); C['dEnd'] = C.dec.notna()
R = {'cohort': {'window': ['2022-10-07', str(pd.to_datetime(b * 864e11).date())], 'data_end': str(pd.to_datetime(DATA_END * 864e11)), 'arrivals': len(C)}}

def stats(df):
    n = len(df); o = {}
    for L in ('L0', 'L1', 'L1ns'):
        nl = int(df[L].sum()); o[f'live_{L}'] = nl; o[f'live_share_{L}'] = nl / n
        for dcol in ('d365', 'dEnd'):
            d = int(df[dcol].sum()); dl = int((df[dcol] & df[L]).sum())
            o[f'rho_{dcol}'] = d / n
            o[f'rho_live_{L}_{dcol}'] = d / nl                 # decisions on cohort items / live cohort items
            o[f'share_dec_on_nonlive_{L}_{dcol}'] = 1 - dl / d  # share of decisions on items not live before decision
            o[f'share_live_decided_{L}_{dcol}'] = dl / nl
    return o
pt = stats(C)
# cluster bootstrap over submitters
g = {u: x for u, x in C.groupby('subU')}; us = np.array(list(g)); bs = []
for _ in range(2000):
    bs.append(stats(pd.concat([g[u] for u in rng.choice(us, len(us))])))
R['cohort_estimates'] = {k: [round(v, 3), round(float(np.percentile([x[k] for x in bs], 2.5)), 3), round(float(np.percentile([x[k] for x in bs], 97.5)), 3)] if isinstance(v, float) else v for k, v in pt.items()}
R['cohort_counts'] = {'decided_365': int(C.d365.sum()), 'decided_by_end': int(C.dEnd.sum()), 'acc365': int((C.d365 & (C.out == 'ACC')).sum()),
                      'rej365': int((C.d365 & (C.out == 'REJ')).sum()), 'wdr365': int((C.d365 & (C.out == 'WDR')).sum()),
                      'decided365_not_live_L1': int((C.d365 & ~C.L1).sum()), 'decided365_not_live_L1_decided_within_1d': int((C.d365 & ~C.L1 & (C.dec - C.arr <= 1)).sum()),
                      'decided365_not_live_L1_acc': int((C.d365 & ~C.L1 & (C.out == 'ACC')).sum())}
# period (Table 3) definition under the new liveness, same window: decisions in window on ANY item / live arrivals in window
Dw = it[(it.dec >= a) & (it.dec < b)]
R['period_definition_same_window'] = {'decisions_in_window_any_item': len(Dw), 'of_which_on_items_arrived_before_window': int((Dw.arr < a).sum()),
    'rho_period': round(len(Dw) / len(C), 3), 'rho_live_period_L0': round(len(Dw) / C.L0.sum(), 3), 'rho_live_period_L1': round(len(Dw) / C.L1.sum(), 3),
    'rho_live_period_L1ns': round(len(Dw) / C.L1ns.sum(), 3)}
json.dump(R, open('res_r3_t1.json', 'w'), indent=1)
print(json.dumps(R, indent=1))
# addendum: decision rates by liveness, pending-at-end composition of the cohort
x = {'decided365_rate_live_L1': round(float(C[C.L1].d365.mean()), 3), 'decided365_rate_nonlive_L1': round(float(C[~C.L1].d365.mean()), 3),
     'pending_at_end': int((~C.dEnd).sum()), 'pending_at_end_share_never_live_L1': round(float((~C[~C.dEnd].L1).mean()), 3),
     'pending_at_end_share_no_activity_at_all_after_submission': round(float((~C[~C.dEnd].index.isin(set(oth[(oth.t > oth.arr)].tid))).mean()), 3)}
R['addendum'] = x; print(x)
json.dump(R, open('res_r3_t1.json', 'w'), indent=1)
