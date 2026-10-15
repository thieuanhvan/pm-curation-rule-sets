# R6 task 6: number reconciliation for the round-5 "number mismatches" list. Aggregates only.
import os, json, pickle, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); R0 = os.path.join(H, '..')
out = {}
d = pickle.load(open(os.path.join(R0, 'A3', 'civic_items.pkl'), 'rb')); it = d['items']
D = lambda s: pd.Timestamp(s).value / 864e11
s16 = it[it.arr >= D('2016-01-01')]
out['pending'] = {'all_items': [int((it.out == 'PEND').sum()), int(len(it)), round(float((it.out == 'PEND').mean()) * 100, 1)],
                  'submitted_since_2016': [int((s16.out == 'PEND').sum()), int(len(s16)), round(float((s16.out == 'PEND').mean()) * 100, 1)]}
h = it[it.dec >= D('2023-01-01')]
out['holdout_tokens'] = {'all': int(len(h)), 'by_outcome': h.out.value_counts().to_dict(), 'non_withdrawal': int((h.out != 'WDR').sum())}
inten = json.load(open(os.path.join(R0, 'R5', 'res_d_intensity.json')))
out['intensity_unrounded'] = {k: {kk: inten[k][kk] for kk in ('ev_per_day_2016_18', 'ev_per_day_2023_26', 'fold', 'fold_CI')} for k in ('common_types', 'all_types', 'strict_common')}
out['decomposition_A_star'] = json.load(open(os.path.join(H, 'res_t6_decomp.json')))
out['app_flags'] = {'flag_objects': 7661, 'with_clear_event': 1584, 'open_at_end': 6106, 'closed_at_end': 7661 - 6106,
                    'cleared_then_reraised_open_at_end': 1584 + 6106 - 7661}
o = pickle.load(open(os.path.join(R0, 'R3_causal', 'objs.pkl'), 'rb')); r = o['rdec']
x = r[r.kind.isin(['rej', 'wd'])].copy(); x['y'] = x.t.dt.year
tab = {}
for y in (2019, 2020, 2021):
    for k, lab in (('rej', 'other_users_revisions'), ('wd', 'own_revisions_withdrawn')):
        g = x[(x.kind == k) & (x.y == y)]
        tab[f'{y}_{lab}'] = {'n': int(len(g)), 'note10': round(float((g.note_len >= 10).mean()), 3), 'note10_or_comment_before': round(float(((g.note_len >= 10) | g.cm_before).mean()), 3)}
    g = x[x.y == y]; tab[f'{y}_all_revision_rejections'] = {'n': int(len(g)), 'note10': round(float((g.note_len >= 10).mean()), 3)}
out['revision_rejection_note_share_pre_v2'] = tab
json.dump(out, open(os.path.join(H, 'res_t6_numbers.json'), 'w'), indent=1, default=int)
print(json.dumps(out, indent=1, default=int))
