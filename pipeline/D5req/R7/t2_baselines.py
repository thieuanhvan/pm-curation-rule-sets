# R7 tasks 1e, 2, 3: evaluable controls on the public CIViC log; R(t) vs two static references; deployment-lag
# sensitivity for v1; documented-norm enactment f_c with Wilson CIs. Aggregates only (no ids, no per-person counts).
import os, json, numpy as np, pandas as pd
from t_common import load, BOT, H
E, NOTES = load()
V2 = pd.Timestamp('2022-04-09'); TAU_SA = pd.Timestamp('2016-07-20'); TAU_SA_PART = pd.Timestamp('2016-02-24')
TAU_RSN_EI = pd.Timestamp('2025-04-07')


def wilson(k, n, z=1.96):
    if n == 0: return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(k / n, 4), round(c - h, 4), round(c + h, 4)]


STAT = {'SUBMITTED': 'submitted', 'ASSERTION_SUBMITTED': 'submitted', 'ACCEPTED': 'accepted', 'ASSERTION_ACCEPTED': 'accepted',
        'REJECTED': 'rejected', 'ASSERTION_REJECTED': 'rejected', 'REVERTED': 'submitted', 'ASSERTION_REVERTED': 'submitted'}
status, submitter, revsug, pend = {}, {}, {}, {}
cm_idx = {k: g[['u', 't']].values for k, g in E[E.act == 'COMMENTED'].groupby(['st', 'sid'])}


def commented(st, sid, u, t, before=pd.Timedelta(minutes=2), after=pd.Timedelta(minutes=2)):
    g = cm_idx.get((st, sid))
    if g is None: return False
    return bool(any(uu == u and (t - before) <= tt <= (t + after) for uu, tt in g))


rows = []
for r in E.itertuples():
    k = (r.st, r.sid)
    if r.act == 'REVISION_SUGGESTED':
        revsug[r.oid] = (r.u, r.t); pend.setdefault(k, set()).add(r.oid)
    if r.act in ('REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED'):
        pend.get(k, set()).discard(r.oid)
    if r.u not in BOT:
        if r.act == 'REVISION_ACCEPTED':
            own_rev = revsug.get(r.oid, (None,))[0] == r.u
            own_pending = submitter.get(k) == r.u and status.get(k) == 'submitted'
            rows.append(dict(c='SA_rev', t=r.t, holds=not own_rev, own_pending=own_pending))
        if r.act == 'REVISION_REJECTED' and revsug.get(r.oid, (None,))[0] != r.u:  # others' revisions (withdrawals excluded)
            raw = NOTES.get(r.eid)
            ok = (raw is not None and len(raw) >= 10) or commented('Revision', r.oid, r.u, r.t)
            rows.append(dict(c='RSN_rev', t=r.t, holds=ok, own_pending=False))
        if r.st == 'EvidenceItem' and r.act == 'ACCEPTED':
            rows.append(dict(c='SA_ei', t=r.t, holds=submitter.get(k) != r.u, own_pending=False))
            rows.append(dict(c='FIT1', t=r.t, holds=len(pend.get(k, set())) == 0, own_pending=False))
        if r.st == 'EvidenceItem' and r.act == 'REJECTED' and submitter.get(k) != r.u:
            raw = NOTES.get(r.eid)
            ok = (raw is not None and len(raw.strip()) > 0) or commented('EvidenceItem', r.sid, r.u, r.t, before=pd.Timedelta(days=1))
            rows.append(dict(c='RSN_ei', t=r.t, holds=ok, own_pending=False))
    if r.act in STAT and r.sid is not None:
        if r.act.endswith('SUBMITTED') and k not in submitter: submitter[k] = r.u
        status[k] = STAT[r.act]
D = pd.DataFrame(rows)


def in_force_Rt(c, t, own_pending, lag=0):
    if c in ('SA_rev', 'SA_ei'):
        if t >= V2: return not (c == 'SA_rev' and own_pending)
        return t >= TAU_SA + pd.Timedelta(days=lag)
    if c == 'RSN_rev': return t >= V2
    if c == 'RSN_ei': return t >= TAU_RSN_EI
    return False  # FIT1 never configured


def in_force_doc(c, t, own_pending):  # documented SOP, constant over time; SOP states no self-acceptance without exception
    return True


def in_force_latest(c, t, own_pending):  # latest code (v2.7.6) applied to all time
    if c == 'SA_rev': return not own_pending
    return c in ('SA_ei', 'RSN_rev', 'RSN_ei')


def band(y):
    return '<=2016' if y <= 2016 else ('2017-21' if y <= 2021 else ('2022-24' if y <= 2024 else '2025-26'))


out = {'n_evaluable_events': {c: int((D.c == c).sum()) for c in D.c.unique()}}
for lab, f in (('R_t', in_force_Rt), ('static_doc', in_force_doc), ('static_latest_code', in_force_latest)):
    D[lab] = [f(r.c, r.t, r.own_pending) for r in D.itertuples()]
    D['viol_' + lab] = D[lab] & ~D.holds
cmp = {}
for lab in ('static_doc', 'static_latest_code'):
    fv = D['viol_' + lab] & ~D['viol_R_t']; mv = ~D['viol_' + lab] & D['viol_R_t']
    cmp[lab] = {'violations': int(D['viol_' + lab].sum()), 'false_violations_vs_R_t': int(fv.sum()), 'missed_violations_vs_R_t': int(mv.sum()),
                'false_by_control': D[fv].c.value_counts().to_dict(), 'false_by_period': D[fv].t.dt.year.map(band).value_counts().sort_index().to_dict(),
                'events_with_control_in_force': int(D[lab].sum()), 'conformance': round(1 - D['viol_' + lab].sum() / D[lab].sum(), 4)}
cmp['R_t'] = {'violations': int(D.viol_R_t.sum()), 'by_control': D[D.viol_R_t].c.value_counts().to_dict(),
              'by_year': {int(k): int(v) for k, v in D[D.viol_R_t].t.dt.year.value_counts().sort_index().items()},
              'events_with_control_in_force': int(D.R_t.sum()), 'F_R_evaluable': round(1 - D.viol_R_t.sum() / D.R_t.sum(), 5)}
out['task2_baselines'] = cmp
out['task2_not_evaluable'] = {
    'self_acceptances_2016-02-24_to_2016-07-19 (non-admins refused; role at event not public)': int((D.c.isin(['SA_rev', 'SA_ei']) & ~D.holds & (D.t >= TAU_SA_PART) & (D.t < TAU_SA)).sum()),
    'EI decisions under COI requirement 2019-09-10..2022-04-08 (in R(t), absent from latest code; COI at event not public)': int((D.c.isin(['SA_ei', 'RSN_ei']) & (D.t >= '2019-09-10') & (D.t < V2)).sum())}
lag = {}
for L in (0, 14, 30):
    v = D[D.c.isin(['SA_rev', 'SA_ei']) & (D.t < V2) & ~D.holds & (D.t >= TAU_SA + pd.Timedelta(days=L))]
    lag[f'+{L}d'] = {'v1_violations': int(len(v)), 'in_2016': int((v.t.dt.year == 2016).sum()),
                     'days_after_tau_of_2016_violations': sorted(int((x - TAU_SA).days) for x in v[v.t.dt.year == 2016].t)}
# commit-to-deploy: earliest violation day relative to commit, i.e. is the rule plausibly not yet deployed?
out['task1e_lag'] = lag
t3 = {}
for c in ('SA_rev', 'SA_ei', 'RSN_rev', 'RSN_ei', 'FIT1'):
    x = D[D.c == c]; inf = x[x.R_t]; pre = x[~x.R_t]
    t3[c] = {'in_force_n': int(len(inf)), 'in_force_conforming': wilson(int(inf.holds.sum()), len(inf)),
             'not_in_force_n': int(len(pre)), 'f_c_documented_norm': wilson(int(pre.holds.sum()), len(pre))}
    yy = {}
    for y, g in pre.groupby(pre.t.dt.year):
        if len(g) >= 20: yy[int(y)] = wilson(int(g.holds.sum()), len(g)) + [int(len(g))]
    t3[c]['f_c_by_year'] = yy
out['task3_enactment'] = t3
out['task3_not_evaluable'] = ['D1/D3 editor role at event (only current role is public)', 'D5/D5b COI statement valid at event',
                              'D8 acting organisation membership at event', 'R1 flag resolver role (flagger part only)',
                              'I1/F1 comment at suggestion/flag (stored in activity notes, not in the cached public event log)',
                              'automatic controls X2, F2, RR1 (performed by the system; conformance true by construction)']
json.dump(out, open(os.path.join(H, 'res_t2_t3.json'), 'w', encoding='utf-8'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
# ---- addenda: split SA_rev 'not in force' into pre-tau (documented norm) and v2 own-pending exception; timing of 2016 violations
sa = D[D.c == 'SA_rev']
pre = sa[sa.t < TAU_SA]; exc = sa[(sa.t >= V2) & sa.own_pending]
out['task3_enactment']['SA_rev']['f_c_pre_tau_2015_to_2016-07-19'] = wilson(int(pre.holds.sum()), len(pre)) + [int(len(pre))]
out['task3_enactment']['SA_rev']['v2_own_pending_exception_events'] = int(len(exc))
out['task3_enactment']['SA_rev']['v2_own_pending_exception_self_accept_share'] = round(float((~exc.holds).mean()), 4)
COMMIT = pd.Timestamp('2016-07-20 21:57:45')  # 313586fa, 16:57:45 -0500, UTC
v16 = D[D.c.isin(['SA_rev', 'SA_ei']) & ~D.holds & (D.t >= TAU_SA) & (D.t < '2017-01-01')]
out['task1e_lag']['2016_violations_hours_after_commit_313586fa'] = sorted(round((x - COMMIT).total_seconds() / 3600, 2) for x in v16.t)
sf = D[(D.c == 'SA_rev') & D.viol_static_doc & ~D.viol_R_t]
out['task2_baselines']['static_doc']['SA_rev_false_split'] = {'pre_tau': int((sf.t < TAU_SA).sum()), 'v2_own_pending_exception': int(((sf.t >= V2) & sf.own_pending).sum())}
json.dump(out, open(os.path.join(H, 'res_t2_t3.json'), 'w', encoding='utf-8'), indent=1, default=str)
print(out['task3_enactment']['SA_rev'], out['task1e_lag']['2016_violations_hours_after_commit_313586fa'], out['task2_baselines']['static_doc']['SA_rev_false_split'])
