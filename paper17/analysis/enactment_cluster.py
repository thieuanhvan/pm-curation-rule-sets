# R8 analysis C (+ B recomputation): Table 3 as a decomposition; dated C_doc; f_c only within documented periods;
# change points (PELT, ruptures) on monthly behaviour series vs tau_c. Aggregates only.
import os, sys, json, numpy as np, pandas as pd
H = (__import__("os").environ.get("P17_PIPELINE", str(next(p for p in __import__("pathlib").Path(__file__).resolve().parents if (p / "pipeline").is_dir()) / "pipeline")) + "/D5req/R8"); R0 = os.path.join(H, '..')
OUTD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(R0, 'R7'))
from t_common import load, BOT
E, NOTES = load()
V2 = pd.Timestamp('2022-04-09'); TAU_SA = pd.Timestamp('2016-07-20'); TAU_SA_PART = pd.Timestamp('2016-02-24')
TAU_RSN_EI = pd.Timestamp('2025-04-07')
DOC = json.load(open(os.path.join(H, 'res_b_docdates.json'), encoding='utf-8'))


def docfrom(key):
    ds = [DOC[r]['first_match'][key]['date'] for r in ('civic-client', 'civic-docs') if DOC[r]['first_match'].get(key)]
    return pd.Timestamp(min(ds)) if ds else None


DOCFROM = {'SA_rev': docfrom('C5C7_no_self_acceptance'), 'SA_ei': docfrom('C5C7_no_self_acceptance'),
           'RSN_rev': docfrom('C10C11_reason_on_reject'), 'RSN_ei': docfrom('C10C11_reason_on_reject'), 'FIT1': None}
DANOS = pd.Timestamp('2019-11-29')


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
            rows.append(dict(c='SA_rev', t=r.t, holds=not own_rev, own_pending=own_pending, u=r.u, note_ok=not own_rev))
        if r.act == 'REVISION_REJECTED' and revsug.get(r.oid, (None,))[0] != r.u:
            raw = NOTES.get(r.eid)
            ok = (raw is not None and len(raw) >= 10) or commented('Revision', r.oid, r.u, r.t)
            rows.append(dict(c='RSN_rev', t=r.t, holds=ok, own_pending=False, u=r.u, note_ok=(raw is not None and len(raw) >= 10)))
        if r.st == 'EvidenceItem' and r.act == 'ACCEPTED':
            rows.append(dict(c='SA_ei', t=r.t, holds=submitter.get(k) != r.u, own_pending=False, u=r.u, note_ok=submitter.get(k) != r.u))
            rows.append(dict(c='FIT1', t=r.t, holds=len(pend.get(k, set())) == 0, own_pending=False, u=r.u, note_ok=len(pend.get(k, set())) == 0))
        if r.st == 'EvidenceItem' and r.act == 'REJECTED' and submitter.get(k) != r.u:
            raw = NOTES.get(r.eid)
            ok = (raw is not None and len(raw.strip()) > 0) or commented('EvidenceItem', r.sid, r.u, r.t, before=pd.Timedelta(days=1))
            rows.append(dict(c='RSN_ei', t=r.t, holds=ok, own_pending=False, u=r.u, note_ok=(raw is not None and len(raw.strip()) > 0)))
    if r.act in STAT and r.sid is not None:
        if r.act.endswith('SUBMITTED') and k not in submitter: submitter[k] = r.u
        status[k] = STAT[r.act]
D = pd.DataFrame(rows)


def in_R(c, t, op, commit_tau=True):
    if c in ('SA_rev', 'SA_ei'):
        if t >= V2: return not (c == 'SA_rev' and op)
        return t >= (pd.Timestamp('2016-07-20 21:57:45') if commit_tau else TAU_SA)
    if c == 'RSN_rev': return t >= V2
    if c == 'RSN_ei': return t >= TAU_RSN_EI
    return False


D['inR'] = [in_R(r.c, r.t, r.own_pending) for r in D.itertuples()]
D['inR_month'] = [in_R(r.c, r.t, r.own_pending, False) for r in D.itertuples()]
D['violR'] = D.inR & ~D.holds
D['violR_month'] = D.inR_month & ~D.holds


def category(r):
    """why a reference flags an event that R(t) does not: the code at that time did not refuse it."""
    if r.c == 'FIT1': return 'C3 inferred norm (never documented as a rule, never coded)'
    if r.c in ('SA_rev', 'SA_ei'):
        if r.t >= V2 and r.own_pending: return 'self-acceptance of a revision on one\'s own pending submission (v2 permits)'
        if r.t < TAU_SA_PART: return 'self-acceptance before any guard (documented norm, not coded)'
        return 'self-acceptance 24 Feb-19 Jul 2016 (guard for non-administrators only; role not public)'
    if r.c == 'RSN_rev': return 'revision rejection without reason before Apr 2022 (documented norm, not coded)'
    if r.c == 'RSN_ei': return 'evidence-item rejection without reason before Apr 2025 (documented norm, not coded)'


refs = {
    'documented_constant_incl_C3': lambda r: True,
    'documented_constant_excl_C3': lambda r: r.c != 'FIT1',
    'documented_dated_excl_C3': lambda r: r.c != 'FIT1' and DOCFROM[r.c] is not None and r.t >= DOCFROM[r.c],
    'documented_dated_excl_C3_SA_rev_implicit_2015-12-17': lambda r: r.c != 'FIT1' and ((r.t >= pd.Timestamp('2015-12-17')) if r.c == 'SA_rev' else (DOCFROM[r.c] is not None and r.t >= DOCFROM[r.c])),
    'documented_from_SOP_2019_excl_C3': lambda r: r.c != 'FIT1' and r.t >= DANOS,
    'latest_code_v2.7.6': lambda r: (not r.own_pending) if r.c == 'SA_rev' else r.c in ('SA_ei', 'RSN_rev', 'RSN_ei'),
}
out = {'doc_from': {k: (str(v.date()) if v is not None else None) for k, v in DOCFROM.items()}, 'n_events': int(len(D))}
dec = {}
for name, f in refs.items():
    inref = np.array([f(r) for r in D.itertuples()])
    flag = inref & ~D.holds.values
    both = flag & D.violR.values
    only_ref = flag & ~D.violR.values
    cats = pd.Series([category(r) for r in D[only_ref].itertuples()]).value_counts().to_dict() if only_ref.any() else {}
    dec[name] = {'events_with_control_in_reference': int(inref.sum()), 'flagged_by_reference': int(flag.sum()),
                 'i_not_refused_by_code_in_force': int(only_ref.sum()), 'i_by_category': cats,
                 'ii_violations_of_R_t_also_flagged': int(both.sum()),
                 'R_t_violations_missed_by_reference': int((D.violR.values & ~flag).sum()),
                 'flags_by_year_band': pd.Series(D[only_ref].t.dt.year).map(lambda y: '<=2016' if y <= 2016 else ('2017-21' if y <= 2021 else ('2022-24' if y <= 2024 else '2025-26'))).value_counts().sort_index().to_dict()}
dec['R_t_commit_tau'] = {'events_with_control_in_force': int(D.inR.sum()), 'violations': int(D.violR.sum())}
dec['R_t_monthly_tau'] = {'events_with_control_in_force': int(D.inR_month.sum()), 'violations': int(D.violR_month.sum())}
out['table3_decomposition'] = dec

# f_c only within documented periods (documented-from date <= t < tau_c)
fc = {}
for c in ('SA_rev', 'SA_ei', 'RSN_rev', 'RSN_ei'):
    x = D[(D.c == c) & ~D.inR & ~((D.c == 'SA_rev') & D.own_pending & (D.t >= V2))]
    allpre = wilson(int(x.holds.sum()), len(x)) + [int(len(x))]
    if DOCFROM[c] is not None:
        y = x[x.t >= DOCFROM[c]]
        dated = (wilson(int(y.holds.sum()), len(y)) + [int(len(y))]) if len(y) else None
    else:
        dated = None
    z = x[x.t >= DANOS]
    fc[c] = {'all_pre_tau': allpre, 'within_documented_period': dated, 'within_SOP_period_from_2019-11-29': (wilson(int(z.holds.sum()), len(z)) + [int(len(z))]) if len(z) else None}
for c in ('SA_rev', 'SA_ei'):
    y = D[(D.c == c) & ~D.inR & (D.t >= pd.Timestamp('2015-12-17')) & (D.t < V2)]
    fc[c]['within_implicit_statement_2015-12-17_to_tau'] = wilson(int(y.holds.sum()), len(y)) + [int(len(y))]
x = D[D.c == 'FIT1']; fc['FIT1_C3_inferred_norm_all_time'] = wilson(int(x.holds.sum()), len(x)) + [int(len(x))]
out['f_c_documented_periods'] = fc

# ---- 14/10/2026 additions: cluster bootstrap by deciding user, and notes-only operationalisation of 'reason present'
rng = np.random.default_rng(17)


def cluster_ci(x, col='holds', B=2000):
    g = x.groupby('u')[col].agg(['sum', 'count'])
    s, n = g['sum'].values, g['count'].values
    k = len(g)
    vals = []
    for _ in range(B):
        idx = rng.integers(0, k, k)
        vals.append(s[idx].sum() / n[idx].sum())
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975)), int(k)]


def subsets():
    yield 'SA_rev_documented_implicit', D[(D.c == 'SA_rev') & ~D.inR & (D.t >= pd.Timestamp('2015-12-17')) & (D.t < V2)]
    yield 'SA_ei_documented_implicit', D[(D.c == 'SA_ei') & ~D.inR & (D.t >= pd.Timestamp('2015-12-17')) & (D.t < V2)]
    for c in ('RSN_rev', 'RSN_ei'):
        x = D[(D.c == c) & ~D.inR]
        yield f'{c}_documented', x[x.t >= DOCFROM[c]]
        yield f'{c}_all_before_tau', x
    for c in ('SA_rev', 'SA_ei'):
        yield f'{c}_all_before_tau', D[(D.c == c) & ~D.inR & ~((D.c == 'SA_rev') & D.own_pending & (D.t >= V2))]
    for c in ('SA_rev', 'SA_ei', 'RSN_rev', 'RSN_ei'):
        yield f'{c}_in_force', D[(D.c == c) & D.inR & ~((D.c == 'SA_rev') & D.own_pending & (D.t >= V2))]
    yield 'FIT1_all_time', D[D.c == 'FIT1']


res = {}
for name, x in subsets():
    res[name] = {'n': int(len(x)), 'share': float(x.holds.mean()) if len(x) else None,
                 'cluster_ci_by_decider': cluster_ci(x) if len(x) else None,
                 'share_notes_only': float(x.note_ok.mean()) if len(x) else None,
                 'cluster_ci_notes_only': cluster_ci(x, 'note_ok') if len(x) else None}
json.dump(res, open(os.path.join(OUTD, 'res_enactment_cluster.json'), 'w', encoding='utf-8'), indent=1)
for k, v in res.items():
    print(k, v['n'], round(v['share'], 4) if v['share'] is not None else None, [round(a, 4) for a in v['cluster_ci_by_decider'][:2]] if v['cluster_ci_by_decider'] else None,
          'deciders', v['cluster_ci_by_decider'][2] if v['cluster_ci_by_decider'] else None, '| notes only', round(v['share_notes_only'], 4) if v['share_notes_only'] is not None else None,
          [round(a, 4) for a in v['cluster_ci_notes_only'][:2]] if v['cluster_ci_notes_only'] else None)
