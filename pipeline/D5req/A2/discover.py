# A2 step 2: discovery on the CIViC OCEL (evidence-item scope, bot excluded): OC-DFG, per-object-type DFG, IMf on the case log,
# variants, rework loops. Output: out/discovery.json + PNML.
import pickle, json, collections as C, numpy as np, pandas as pd, pm4py
from pm4py.objects.ocel.obj import OCEL
rng = np.random.default_rng(20261007)
OUT = 'out/'; RES = {}
def P(k, v): RES[k] = v; print(k, json.dumps(v, default=str)[:1500])
def wilson(k, n, z=1.96):
    if n == 0: return [None, None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 4), round(c - h, 4), round(c + h, 4)]

d = pickle.load(open(OUT + 'ocel_ei.pkl', 'rb'))
ev = d['events'][~d['events']['is_bot']]; rel = d['relations'][d['relations']['ocel:eid'].isin(set(ev['ocel:eid']))]
ob = d['objects'][d['objects']['ocel:oid'].isin(set(rel['ocel:oid']))]
ocel = OCEL(events=ev.copy(), objects=ob.copy(), relations=rel.copy())
P('ocel_ei_excl_bot', {'events': len(ev), 'objects': ob['ocel:type'].value_counts().to_dict(), 'relations': len(rel)})

# ---- OC-DFG (pm4py) ----
oc = pm4py.discover_ocdfg(ocel)
ocdfg = {}
for ot, edges in oc['edges']['event_couples'].items():
    cnt = sorted(((a + ' -> ' + b, len(v)) for (a, b), v in edges.items()), key=lambda x: -x[1])
    ocdfg[ot] = {'n_edges': len(cnt), 'top': cnt[:12]}
P('ocdfg_edges_by_object_type', ocdfg)
act_ot = {ot: sorted(a) for ot, a in pm4py.ocel_object_type_activities(ocel).items()}
P('activities_per_object_type', act_ot)
# convergence/divergence diagnostics (what flattening hides): events per object of each type per evidence item
ei_rel = rel[rel['ocel:type'] == 'evidence_item'][['ocel:eid', 'ocel:oid']].rename(columns={'ocel:oid': 'ei'})
def per_ei(t):
    x = rel[rel['ocel:type'] == t][['ocel:eid', 'ocel:oid']].merge(ei_rel, on='ocel:eid').groupby('ei')['ocel:oid'].nunique()
    x = x.reindex(ob[ob['ocel:type'] == 'evidence_item']['ocel:oid'], fill_value=0)
    return {'share_ge1': round(float((x >= 1).mean()), 4), 'mean': round(float(x.mean()), 3), 'p90': int(x.quantile(.9)), 'max': int(x.max())}
P('objects_per_evidence_item', {t: per_ei(t) for t in ['revision', 'flag', 'comment', 'user', 'organisation']})

# ---- per object type flattened DFG ----
flat = {}
for ot in ['evidence_item', 'revision', 'flag', 'comment']:
    fl = pm4py.ocel_flattening(ocel, ot)
    dfg, sa, ea = pm4py.discover_dfg(fl)
    flat[ot] = {'cases': fl['case:concept:name'].nunique(), 'start': dict(sorted(sa.items(), key=lambda x: -x[1])[:6]), 'end': dict(sorted(ea.items(), key=lambda x: -x[1])[:6]),
                'top_edges': [(a + ' -> ' + b, n) for (a, b), n in sorted(dfg.items(), key=lambda x: -x[1])[:12]]}
    if ot in ('revision', 'flag'):
        v = pm4py.get_variants(fl); tot = sum(v.values())
        flat[ot]['variants'] = [('>'.join(k), n, round(n / tot, 4)) for k, n in sorted(v.items(), key=lambda x: -x[1])[:8]]
P('per_object_type_dfg', flat)

# ---- case log (evidence-item view) ----
cl = pd.read_pickle(OUT + 'caselog_ei_excl.pkl')
log = pm4py.format_dataframe(cl[['case:concept:name', 'concept:name', 'time:timestamp', 'org:resource']].copy(), case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
# variants: full alphabet and status-only projection
def variants(df, name):
    v = pm4py.get_variants(df); n = sum(v.values()); s = sorted(v.items(), key=lambda x: -x[1]); cum = np.cumsum([x[1] for x in s]) / n
    out = {'cases': n, 'distinct': len(s), 'singletons': sum(1 for x in s if x[1] == 1), 'distinct_per_case': round(len(s) / n, 3),
           'top1': wilson(s[0][1], n), 'top5_cov': round(float(cum[min(4, len(s) - 1)]), 4), 'top10_cov': round(float(cum[min(9, len(s) - 1)]), 4),
           'n_for_80pct': int(np.searchsorted(cum, .8) + 1), 'n_for_90pct': int(np.searchsorted(cum, .9) + 1),
           'top': [(' > '.join(k) if len(k) < 12 else ' > '.join(k[:12]) + ' ...', c, round(c / n, 4)) for k, c in s[:10]]}
    P('variants_' + name, out)
variants(log, 'full')
core = log[log['concept:name'].isin(['SUBMITTED', 'ACCEPTED', 'REJECTED', 'REVERTED', 'REVISION_SUGGESTED', 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED', 'FLAGGED', 'FLAG_RESOLVED'])]
# collapse self-loops (repeated identical activity) for a readable variant view
cc = core.copy(); cc['prev'] = cc.groupby('case:concept:name')['concept:name'].shift()
variants(cc[cc['concept:name'] != cc['prev']].drop(columns='prev'), 'no_comments_selfloops_collapsed')
stat = log[log['concept:name'].isin(['SUBMITTED', 'ACCEPTED', 'REJECTED', 'REVERTED'])]
variants(stat, 'status_projection')

# IMf (noise 0.2) on the evidence-item case log; quality by token replay (alignments in conformance.py)
for name, df, nt in [('full', log, 0.2), ('no_comments', core, 0.2), ('full_imf0', log, 0.0)]:
    net, im, fm = pm4py.discover_petri_net_inductive(df, noise_threshold=nt)
    pm4py.write_pnml(net, im, fm, OUT + f'imf_{name}.pnml')
    fit = pm4py.fitness_token_based_replay(df, net, im, fm); prec = pm4py.precision_token_based_replay(df, net, im, fm)
    tree = pm4py.discover_process_tree_inductive(df, noise_threshold=nt)
    P('imf_' + name, {'noise': nt, 'places': len(net.places), 'transitions': len(net.transitions), 'silent': sum(1 for t in net.transitions if t.label is None),
                      'tbr_log_fitness': round(fit['log_fitness'], 4), 'tbr_perc_fit_traces': round(fit['perc_fit_traces'], 2), 'tbr_precision': round(prec, 4), 'process_tree': str(tree)[:900]})

# ---- rework loops ----
cases = {k: g for k, g in cl.groupby('case:concept:name', sort=False)}
N = len(cases); loop_flat = loop_same = loop_obj = 0; rr_with_later = 0; gaps = []; revdec = C.Counter(); rej_then = C.Counter()
sus = {}
for k, g in cases.items():
    a = g['concept:name'].tolist(); u = g['org:resource'].tolist(); rv = g['revision'].tolist(); t = g['time:timestamp'].tolist()
    # flattened pattern: R_SUGGESTED ... R_REJECTED ... R_SUGGESTED
    found = False; same = False
    for i, x in enumerate(a):
        if x == 'REVISION_REJECTED':
            rid = rv[i]; sidx = [j for j in range(i) if a[j] == 'REVISION_SUGGESTED' and rv[j] == rid]
            sug_user = u[sidx[0]] if sidx else None
            later = [j for j in range(i + 1, len(a)) if a[j] == 'REVISION_SUGGESTED']
            if sidx and later:
                found = True
                if any(u[j] == sug_user for j in later): same = True; gaps.append((t[[j for j in later if u[j] == sug_user][0]] - t[i]).total_seconds() / 864e2)
    loop_flat += found; loop_same += same
    # per-revision lifecycle outcome
P('rework', {'cases': N, 'loop_suggest_reject_suggest': wilson(loop_flat, N), 'loop_same_suggester_resubmits': wilson(loop_same, N),
             'resubmit_gap_days_median': round(float(np.median(gaps)), 1) if gaps else None, 'resubmit_gap_p25_p75': [round(float(np.percentile(gaps, 25)), 1), round(float(np.percentile(gaps, 75)), 1)] if gaps else None})
# revision object lifecycle (object-centric): outcome per revision object, multiple outcomes, self-moderation
rl = cl[cl['revision'].notna()]
outc = rl.groupby('revision')['concept:name'].apply(lambda s: tuple(x for x in s if x != 'REVISION_COMMENTED'))
oc_c = C.Counter(outc); nrev = len(outc)
P('revision_object_lifecycles', {'revisions': nrev, 'top': [(' > '.join(k), n, round(n / nrev, 4)) for k, n in oc_c.most_common(8)],
     'no_suggestion_event_in_scope': int(sum(1 for k in outc if 'REVISION_SUGGESTED' not in k)),
     'pending': int(sum(1 for k in outc if k == ('REVISION_SUGGESTED',)))})
# status-level loops
sl = stat.groupby('case:concept:name')['concept:name'].apply(tuple)
P('status_loops', {'decision_then_reverted': int(sum(1 for k in sl if 'REVERTED' in k)), 'multiple_decisions': int(sum(1 for k in sl if sum(x in ('ACCEPTED', 'REJECTED') for x in k) > 1)),
                   'accepted_and_rejected_both': int(sum(1 for k in sl if 'ACCEPTED' in k and 'REJECTED' in k)), 'patterns': [(' > '.join(k), n) for k, n in C.Counter(sl).most_common(10)]})
json.dump(RES, open(OUT + 'discovery.json', 'w'), indent=1, default=str)
