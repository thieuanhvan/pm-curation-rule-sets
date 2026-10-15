# R7 task 4: graded stage coverage. Controls (19 in R6 table, absence records excluded) +, as sensitivity, the controls
# found only by the second coder. For stage s with identified controls C_s (all modes, incl. documented-only):
#   kappa_share_s(t) = |{c in C_s in force at t with mode guard/automatic}| / |C_s|
#   kappa_w_s(t)     = sum_c w(c, t) / |C_s|,  w = 1 guard, 1 automatic, 0.5 permission, 0 documented-only / not in force
# Stages with no identified control (selection, allocation) are reported as 0 (absence records).
import os, json, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(H, '..', 'R6_formal', 'res_t1_controls.json'), encoding='utf-8'))['controls']
ABS = {'S1', 'A1', 'X4', 'X5'}
ctrl = [dict(id=c['id'], stage=c['stage'].replace('exit (no judgement)', 'exit'), obj=c['object'], mode=c['mode'],
             tau=c['tau_release'], rho=c['removed']) for c in C if c['id'] not in ABS and c['id'] != 'I3']
EXTRA = [  # second coder only (dates: first commit / release; v1 continuous deployment)
    dict(id='c2_fit_stale', stage='fit', obj='revision', mode='guard', tau='2015-01-12', rho='2022-04-09'),
    dict(id='c2_fit_approval', stage='fit', obj='assertion approval', mode='guard', tau='2025-06-03', rho=None),
    dict(id='c2_reopen_rejected_ei', stage='re-review', obj='evidence item', mode='automatic', tau='2016-01-20', rho='2022-04-09'),
    dict(id='c2_ss_curated', stage='exit', obj='source suggestion', mode='automatic', tau='2016-10-06', rho='2022-04-09'),
    dict(id='c2_flag_account', stage='flag raising', obj='any entity', mode='guard', tau='2017-04-04', rho=None),
    dict(id='c2_assert_editor_noself', stage='decision', obj='assertion', mode='guard', tau='2017-10-10', rho=None)]
W = {'guard': 1.0, 'automatic': 1.0, 'permission': 0.5}
STAGES = ['intake', 'fit', 'selection', 'allocation', 'decision', 'flag raising', 'flag resolution', 'exit', 're-review']
def ei_queue(c):  # evidence-item queue: controls on evidence items or on all moderated objects
    return any(k in c['obj'] for k in ('evidence item', 'all moderated'))
def kappa(cs, t):
    row = {}
    for s in STAGES:
        Cs = [c for c in cs if c['stage'] == s]
        if not Cs: row[s] = (0.0, 0.0, 0); continue
        on = [c for c in Cs if c['tau'] and c['tau'] <= t and (not c['rho'] or c['rho'] > t)]
        sh = sum(c['mode'] in ('guard', 'automatic') for c in on) / len(Cs)
        w = sum(W.get(c['mode'], 0) for c in on) / len(Cs)
        row[s] = (round(sh, 3), round(w, 3), len(Cs))
    return row
qs = pd.period_range('2015Q1', '2026Q3', freq='Q')
res = {}
for lab, cs in (('ei_queue_R6', [c for c in ctrl if ei_queue(c)]), ('all_objects_R6', ctrl),
                ('ei_queue_R6_plus_coder2', [c for c in ctrl + EXTRA if ei_queue(c)]), ('all_objects_R6_plus_coder2', ctrl + EXTRA)):
    series, prev = [], None
    for q in qs:
        t = q.end_time.strftime('%Y-%m-%d'); row = kappa(cs, t)
        key = {s: row[s][:2] for s in STAGES}
        if key != prev: series.append({'from': str(q), **{s: {'share': row[s][0], 'weighted': row[s][1], 'n_controls': row[s][2]} for s in STAGES if row[s][2]}}); prev = key
    res[lab] = series
# COI removal effect on the evidence-item decision stage (quarter before vs after the v2 launch)
b, a = kappa([c for c in ctrl if ei_queue(c)], '2022-03-31')['decision'], kappa([c for c in ctrl if ei_queue(c)], '2022-06-30')['decision']
res['coi_removal_ei_decision'] = {'2022Q1': b[:2], '2022Q2': a[:2], 'n_controls': b[2]}
json.dump(res, open(os.path.join(H, 'res_t4_graded_kappa.json'), 'w', encoding='utf-8'), indent=1)
for lab in ('ei_queue_R6', 'ei_queue_R6_plus_coder2'):
    print(lab)
    for r in res[lab]: print(' ', r['from'], {s: (v['share'], v['weighted'], v['n_controls']) for s, v in r.items() if s != 'from'})
print(res['coi_removal_ei_decision'])
