# R8 analysis D2: graded coverage with the final control list (Table S3, C1-C26) and final dates, per object type,
# permission weight 0 / 0.5 / 1. kappa~_s(t) = sum_c w(c,t) / |C_s|, w = 1 guard or automatic in force, w_p permission
# in force, 0 documented-only or not in force. Stages without identified controls are not reported (absence records).
import os, json, pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__))
FIG = "fig3_graded_coverage_r9.png"
V2 = '2022-04-09'
# (id, stage, object types, mode, tau, rho)
C = [('C1', 'intake', 'EI', 'guard', '2015-02-20', None), ('C2', 'intake', 'REV', 'guard', V2, None),
     ('C3', 'fit', 'EI', 'documented', None, None),
     ('C4', 'decision', 'EI', 'guard', '2015-01-27', None), ('C5', 'decision', 'EI', 'guard', '2016-02-24', None),
     ('C6', 'decision', 'REV', 'guard', '2015-01-12', None), ('C7', 'decision', 'REV', 'guard', '2016-02-24', None),
     ('C8', 'decision', 'EI AS', 'guard', '2019-09-10', V2), ('C8', 'decision', 'REV FL SS', 'guard', '2019-09-10', None),  # C8 continued as C9 for REV/FL/SS
     ('C10', 'decision', 'REV', 'guard', V2, None), ('C11', 'decision', 'EI AS', 'guard', '2025-04-07', None),
     ('C12', 'decision', 'EI REV AS SS', 'guard', '2020-04-30', None),
     ('C13', 'flag raising', 'FL', 'guard', V2, None), ('C14', 'flag raising', 'FL', 'automatic', '2023-11-08', None),
     ('C15', 'flag resolution', 'FL', 'guard', '2017-04-04', None),
     ('C16', 'exit', 'REV', 'automatic', '2015-04-29', '2016-02-24'), ('C17', 'exit', 'REV', 'automatic', V2, None),
     ('C18', 'exit', 'EI', 'permission', '2019-01-29', None),
     ('C19', 're-review', 'AS', 'automatic', '2025-06-03', None), ('C20', 'fit', 'REV', 'guard', '2015-01-12', V2),
     ('C21', 're-review', 'EI', 'automatic', '2016-01-20', V2), ('C22', 'fit', 'AS', 'guard', '2025-06-03', None),
     ('C23', 'decision', 'AS', 'guard', '2020-06-30', None), ('C24', 'decision', 'AS', 'guard', '2025-11-12', None),
     ('C25', 'flag raising', 'FL', 'guard', '2020-06-30', None), ('C26', 'decision', 'SS', 'automatic', '2016-10-06', V2)]
OBJ = {'EI': 'evidence item', 'REV': 'revision', 'AS': 'assertion', 'FL': 'flag', 'SS': 'source suggestion'}
STAGES = ['intake', 'fit', 'decision', 'flag raising', 'flag resolution', 'exit', 're-review']
qs = pd.period_range('2015Q1', '2026Q3', freq='Q')


def kap(obj, stage, t, wp):
    cs = [c for c in C if obj in c[2].split() and c[1] == stage]
    if not cs: return None
    w = 0.0
    for _, _, _, m, tau, rho in cs:
        if tau is None or tau > t or (rho and rho <= t): continue
        w += {'guard': 1, 'automatic': 1, 'permission': wp}.get(m, 0)
    return round(w / len(cs), 3)


res = {}
for wp in (0, 0.5, 1):
    for obj in OBJ:
        rows, prev = [], None
        for q in qs:
            t = q.end_time.strftime('%Y-%m-%d')
            r = {s: kap(obj, s, t, wp) for s in STAGES}
            r = {s: v for s, v in r.items() if v is not None}
            if r != prev: rows.append({'from': str(q), **r}); prev = r
        res[f'{OBJ[obj]}|wp={wp}'] = rows
json.dump(res, open(os.path.join(H, 'res_d_graded_coverage.json'), 'w', encoding='utf-8'), indent=1)
for k in ('evidence item|wp=0.5', 'revision|wp=0.5', 'assertion|wp=0.5', 'flag|wp=0.5', 'evidence item|wp=0', 'evidence item|wp=1'):
    print(k)
    for r in res[k]: print('  ', r)
# figure: evidence-item queue, wp = 0.5, all stages with identified controls + selection/allocation (no control)
fig, ax = plt.subplots(figsize=(7.5, 3.6), dpi=200)
x = [q.start_time for q in qs]
sty = {'intake': ('#1f77b4', '-'), 'decision': ('#d62728', '-'), 'exit': ('#2ca02c', '--'), 're-review': ('#9467bd', ':'), 'fit': ('#7f7f7f', '-.')}
for s, (col, ls) in sty.items():
    y = [kap('EI', s, q.end_time.strftime('%Y-%m-%d'), 0.5) for q in qs]
    off = {'intake': 0.012, 'decision': 0, 'exit': -0.012, 're-review': 0.024, 'fit': -0.024}[s]
    ax.step(x, [v + off for v in y], where='post', color=col, ls=ls, lw=1.6, label=s)
ax.axhline(-0.036, color='black', lw=1.2, ls=(0, (1, 2)), label='selection, allocation (no control)')
for d in ('2016-02-24', '2019-09-10', '2020-04-30', '2022-04-09', '2025-04-07'):
    ax.axvline(pd.Timestamp(d), color='#bbbbbb', lw=0.6, zorder=0)
ax.set_ylim(-0.08, 1.08); ax.set_ylabel('graded coverage'); ax.set_xlabel('quarter')
ax.legend(fontsize=7, ncol=3, loc='upper center', bbox_to_anchor=(0.5, -0.18), frameon=False)
fig.tight_layout(); fig.savefig(FIG); print('fig', FIG)
