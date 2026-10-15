# A6 extras: who are the 27 bulk submitters (role now, home org, active span; aggregates only, n>=5),
# share of 2023-25 decisions spent on campaign items, spring-cohort months, submitter-month spikes.
import os, json, pickle, numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); A3 = os.path.join(BASE, '..', 'A3')
it = pickle.load(open(os.path.join(A3, 'civic_items.pkl'), 'rb'))['items'].copy()
dt = pd.to_datetime(it.arr, unit='D'); it['yr'] = dt.dt.year; it['ym'] = dt.dt.strftime('%Y-%m'); it['decyr'] = pd.to_datetime(it.dec, unit='D').dt.year
it['org'] = it.subOrg.fillna(-1).astype(int)
sm = it.groupby(['subU', 'ym']).size(); it['subMonthN'] = [sm[(u, m)] for u, m in zip(it.subU, it.ym)]
om = it.groupby(['org', 'ym']).size(); it['orgMonthN'] = [om[(o, m)] for o, m in zip(it.org, it.ym)]
R = {}
bulk = it[it.subVol >= 100]
g = bulk.groupby('subU').agg(n=('id', 'size'), f=('arr', 'min'), l=('arr', 'max'), role=('subRoleNow', 'first'),
                             org=('org', lambda s: s.mode().iat[0]), months=('ym', 'nunique'), maxday=('burstN', 'max'))
g['span_y'] = (g.l - g.f) / 365.25
R['bulk27_n_submitters'] = len(g)
R['bulk27_span_years_quartiles'] = [round(float(x), 2) for x in g.span_y.quantile([.25, .5, .75])]
R['bulk27_active_months_quartiles'] = [float(x) for x in g.months.quantile([.25, .5, .75])]
R['bulk27_share_items_by_role_now'] = bulk.subRoleNow.value_counts(normalize=True).round(3).to_dict()
rc = g.role.value_counts(); R['bulk27_submitters_by_role_now'] = {k: (int(v) if v >= 5 else '<5') for k, v in rc.items()}
R['bulk27_items_home_org_CIViC_or_WashU(1,12)'] = round(float(bulk.org.isin([1, 12]).mean()), 3)
R['bulk27_span_ge_2y_submitters'] = int((g.span_y >= 2).sum())
R['bulk27_items_level_C_or_E'] = round(float(bulk.level.isin(['C', 'E']).mean()), 3)
R['nonbulk_items_level_C_or_E'] = round(float(it[it.subVol < 100].level.isin(['C', 'E']).mean()), 3)
defs = {'bulk27': it.subVol >= 100, 'C1': (it.burstN >= 20) | (it.subMonthN >= 40), 'C3': it.orgMonthN >= 100}
defs['U_approx(C1|C3)'] = defs['C1'] | defs['C3']
w = it.decyr.between(2023, 2025)
R['decisions_2023_25_total'] = int(w.sum())
R['share_of_2023_25_decisions_on_campaign_items'] = {k: round(float((w & m).sum() / w.sum()), 3) for k, m in defs.items()}
R['share_of_2023_25_decisions_on_campaign_items_arrived_before_2023'] = {k: round(float((w & m & (it.yr < 2023)).sum() / w.sum()), 3) for k, m in defs.items()}
R['submitter_months_ge40'] = int((sm >= 40).sum()); R['submitter_days_ge20'] = int((it.groupby(['subU', 'subDay']).size() >= 20).sum())
gg = it.groupby('subU').agg(f=('arr', 'min'), l=('arr', 'max'), n=('id', 'size'), org0=('org', 'first'))
gg['fm'] = pd.to_datetime(gg.f, unit='D').dt.strftime('%Y-%m')
coh = {}
for m in ['2020-03', '2019-03', '2018-04', '2021-04', '2016-12']:
    s = gg[gg.fm == m]; items = it[it.subU.isin(s.index)]
    coh[m] = {'new_submitters': len(s), 'items': int(len(items)), 'median_items_per_submitter': float(s.n.median()),
              'share_span_le120d': round(float(((s.l - s.f) <= 120).mean()), 3), 'top_org_share': round(float(s.org0.value_counts(normalize=True).iloc[0]), 3),
              'pending_share': round(float((items.out == 'PEND').mean()), 3), 'acc_share': round(float((items.out == 'ACC').mean()), 3)}
R['first_time_cohort_months'] = coh
small = gg[(gg.n <= 20) & ((gg.l - gg.f) <= 120)]
R['short_small_submitters(<=20 items, <=120 d)'] = {'submitters': len(small), 'items': int(it.subU.isin(small.index).sum()), 'share_of_intake': round(float(it.subU.isin(small.index).mean()), 3)}
print(json.dumps(R, indent=1)); json.dump(R, open(os.path.join(BASE, 'res_a6_extra.json'), 'w'), indent=1)
