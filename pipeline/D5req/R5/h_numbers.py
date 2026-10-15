# R5 H (CIViC part): reconcile counts. Aggregates only.
import json, sqlite3, numpy as np, pandas as pd
rng = np.random.default_rng(20261109)
E = pd.read_pickle('../W3/w3_events_hmac.pkl'); H = E[~E.bot]; DATA_END = float(E.t.max())
D = lambda s: pd.Timestamp(s, tz='UTC').value / 864e11
R = {}
ei_all = E[E.tt == 'EvidenceItem']; ei = H[H.tt == 'EvidenceItem']
R['evidence_items_any_event_incl_bot'] = int(ei_all.tid.nunique()); R['evidence_items_any_nonbot_event'] = int(ei.tid.nunique())
sub = ei[ei.act == 'SUBMITTED'].sort_values('t').drop_duplicates('tid').set_index('tid')
dec = ei[ei.act.isin(['ACCEPTED', 'REJECTED'])].sort_values('t').drop_duplicates('tid').set_index('tid')
R['items_with_submission'] = len(sub); R['items_with_first_decision_nonbot_any'] = len(dec)
R['items_with_first_decision_and_submission'] = int(dec.index.isin(sub.index).sum())
# OCEL caselog (Fig 2a / Fig 6a basis)
for f in ('../A2/out/caselog_ei_excl_hmac.pkl',):
    try:
        C = pd.read_pickle(f); R['caselog_cols'] = list(map(str, C.columns))[:12]
        cid = [c for c in C.columns if 'case' in str(c).lower()][0]; act = [c for c in C.columns if 'activity' in str(c).lower()][0]
        R['caselog_cases'] = int(C[cid].nunique())
        R['caselog_cases_with_decision'] = int(C[C[act].isin(['ACCEPTED', 'REJECTED'])][cid].nunique())
        R['caselog_cases_with_status_event'] = int(C[C[act].isin(['SUBMITTED', 'ACCEPTED', 'REJECTED'])][cid].nunique())
    except Exception as e: R['caselog_err'] = str(e)[:200]
# 2025 rejections of other users' evidence items
subU = sub.u
rej = ei[(ei.act == 'REJECTED')].copy(); rej['subU'] = subU.reindex(rej.tid).values
rej_o = rej[rej.u != rej.subU]
for lab, a in (('from_2025-04-01', '2025-04-01'), ('from_2025-04-07_release', '2025-04-07')):
    R[f'rejections_of_others_{lab}_all_events'] = int((rej_o.t >= D(a)).sum())
    fr = rej_o.sort_values('t').drop_duplicates('tid'); R[f'first_rejections_of_others_{lab}'] = int((fr.t >= D(a)).sum())
R['rejections_of_others_2023-09_to_2025-03_all_events'] = int(((rej_o.t >= D('2023-09-01')) & (rej_o.t < D('2025-04-01'))).sum())
R['rejections_of_others_2025-04_to_2026-09_all_events'] = int(((rej_o.t >= D('2025-04-01')) & (rej_o.t < D('2026-10-01'))).sum())
# legacy (pending at 2023-01-01) composition
TV = D('2023-01-01'); it = pd.DataFrame({'arr': sub.t}); fd = dec.reindex(it.index)
it['dec'] = fd.t; it['act'] = fd.act; it['decU'] = fd.u; it['subU'] = subU
leg = it[(it.arr < TV) & (it.dec.isna() | (it.dec >= TV))]
R['legacy'] = {'n': len(leg), 'accepted_in_holdout': int((leg.act == 'ACCEPTED').sum()), 'rejected_by_other_in_holdout': int(((leg.act == 'REJECTED') & (leg.decU != leg.subU)).sum()),
               'withdrawn_in_holdout': int(((leg.act == 'REJECTED') & (leg.decU == leg.subU)).sum()), 'never_decided': int(leg.dec.isna().sum())}
# window throughput (S1 / S5): decisions in window on any item / arrivals in window; calendar 2023-25 likewise; one bootstrap (submitters, B=2000)
def ratio(df, a, b): return ((df.dec >= a) & (df.dec < b)).sum() / max(1, ((df.arr >= a) & (df.arr < b)).sum())
g = {u: x for u, x in it.groupby('subU')}; us = np.array(list(g))
for lab, a, b in (('window_2022-10-07_2025-10-07', D('2022-10-07'), DATA_END - 365), ('calendar_2023_25', D('2023-01-01'), D('2026-01-01'))):
    bs = [ratio(pd.concat([g[u] for u in rng.choice(us, len(us))]), a, b) for _ in range(2000)]
    R[f'rho_{lab}'] = [round(float(ratio(it, a, b)), 3), round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]
    R[f'rho_{lab}_counts'] = [int(((it.dec >= a) & (it.dec < b)).sum()), int(((it.arr >= a) & (it.arr < b)).sum())]
# monthly intake around the change point (non-bot submissions)
m = pd.to_datetime(sub.t * 864e11).dt.tz_localize(None).dt.to_period('M').value_counts().sort_index()
m = m[(m.index >= pd.Period('2019-01', 'M')) & (m.index <= pd.Period('2026-09', 'M'))]
R['arrivals_per_month'] = {'2022-01_to_2023-07': round(float(m[(m.index >= pd.Period('2022-01', 'M')) & (m.index <= pd.Period('2023-07', 'M'))].mean()), 1),
                           '2023-08_to_2026-09': round(float(m[m.index >= pd.Period('2023-08', 'M')].mean()), 1),
                           'calendar_2022': round(float(m[(m.index.year == 2022)].mean()), 1), 'calendar_2023': round(float(m[(m.index.year == 2023)].mean()), 1),
                           'calendar_2024_25': round(float(m[(m.index.year >= 2024) & (m.index.year <= 2025)].mean()), 1),
                           '2026_Jan_Sep': round(float(m[m.index.year == 2026].mean()), 1)}
# simple single change point (least squares on monthly counts 2019-01..2026-09)
y = m.values.astype(float); best = None
for k in range(6, len(y) - 6):
    sse = ((y[:k] - y[:k].mean()) ** 2).sum() + ((y[k:] - y[k:].mean()) ** 2).sum()
    if best is None or sse < best[0]: best = (sse, k)
k = best[1]; R['changepoint_2019_2026'] = {'first_month_after': str(m.index[k]), 'mean_before': round(float(y[:k].mean()), 1), 'mean_after': round(float(y[k:].mean()), 1)}
# flags (bot vs human) and OCEL object totals
c = sqlite3.connect('../A2/out/civic_ocel2_full_hmac.sqlite')
R['ocel_objects_by_type'] = dict(c.execute('select ocel_type, count(*) from object group by ocel_type').fetchall())
R['ocel_totals'] = {'objects': c.execute('select count(*) from object').fetchone()[0], 'events': c.execute('select count(*) from event').fetchone()[0], 'e2o': c.execute('select count(*) from event_object').fetchone()[0]}
json.dump(R, open('res_h_numbers.json', 'w'), indent=1, default=str); print(json.dumps(R, indent=1, default=str))
