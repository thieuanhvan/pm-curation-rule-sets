# R7 task 7: number reconciliation (aggregates only).
import os, json, numpy as np, pandas as pd
from t_common import load, BOT, H
R = os.path.join(H, '..')
out = {}
# (a) 85 vs 74: evidence-item rejections after 2025-04-07, split by withdrawal (submitter) vs others' items
E, NOTES = load()
ei = E[E.st == 'EvidenceItem']; sub = ei[ei.act == 'SUBMITTED'].drop_duplicates('sid').set_index('sid').u
rj = ei[(ei.act == 'REJECTED') & ~ei.u.isin(BOT) & (ei.t >= '2025-04-07')]
own = rj.sid.map(sub) == rj.u
out['ei_rejections_after_2025-04-07'] = {'all': int(len(rj)), 'by_submitter_withdrawal': int(own.sum()), 'of_other_users_items': int((~own).sum()),
    'with_note_or_comment_all': None}
rjm = ei[(ei.act == 'REJECTED') & ~ei.u.isin(BOT) & (ei.t >= '2025-04-01') & (ei.t < '2025-04-07')]
out['ei_rejections_2025-04-01_to_06'] = {'all': int(len(rjm)), 'of_other_users_items': int((rjm.sid.map(sub) != rjm.u).sum())}
# (b) arrivals falsification: log ratio of pooled means vs mean of monthly log ratios, both with placebo bands
PN = pd.read_pickle(os.path.join(R, 'R3_causal', 'panel.pkl'))
T, C = PN['EID'].loc['2023-09':'2026-09'], PN['REV'].loc['2023-09':'2026-09']
def lr_means(t0):
    pre = T.index < t0
    return float(np.log(T.arr[~pre].mean() / T.arr[pre].mean()) - np.log(C.arr[~pre].mean() / C.arr[pre].mean()))
def lr_monthly(t0):
    pre = T.index < t0; l = np.log(T.arr + 0.5) - np.log(C.arr + 0.5); return float(l[~pre].mean() - l[pre].mean())
idx = T.index; cands = [p for k, p in enumerate(idx) if k >= 6 and len(idx) - k >= 6]
for nm, f in (('log_ratio_of_pooled_means', lr_means), ('mean_of_monthly_log_ratios', lr_monthly)):
    e = f(pd.Period('2025-04', 'M')); pl = np.array([f(p) for p in cands])
    out['arrivals_' + nm] = {'estimate': round(e, 3), 'placebo_95': [round(float(np.percentile(pl, 2.5)), 3), round(float(np.percentile(pl, 97.5)), 3)],
                              'p': round(float((np.abs(pl) >= abs(e)).mean()), 3)}
# (c) Wikidata census statuses from 2016
c = json.load(open(os.path.join(R, 'R5_wikidata', 'wd_cases_census.json'), encoding='utf-8'))
import collections
k = collections.Counter(x['kind'] for x in c if x.get('arr') and x['arr'] >= 1451606400000)
out['wikidata_from2016_kinds'] = dict(k)
# (d) S14 as-is model, share decided within 90 days
v = json.load(open(os.path.join(R, 'A4', 'results_validation.json'), encoding='utf-8'))
m = v['models']['LOGIT_T1_cal2021_22']; obs = v['observed']['within']['90']
out['S14_within90'] = {'observed': round(obs, 4), 'pred_mean_and_range_over_40_reps': [round(x, 4) for x in m['pred_within90']],
                       'abs_error_of_mean_prediction': round(abs(m['pred_within90'][0] - obs), 4), 'mean_abs_error_over_reps': [round(x, 4) for x in m['AE_within90']],
                       'naive_persistence_abs_error': round(v['models']['NAIVE_persistence_2021_22']['AE_within90'][0], 4)}
# (e) v1 snapshots: months with a commit vs calendar months
sig = json.load(open(os.path.join(R, 'R6_formal', 't1_signatures.json'), encoding='utf-8'))['meta']
out['v1_snapshots'] = {'months_with_commit': sig['v1_snapshots'], 'calendar_months_2014-08_to_2022-11': int(len(pd.period_range('2014-08', '2022-11', freq='M')))}
json.dump(out, open(os.path.join(H, 'res_t7_numbers.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps(out, indent=1))
