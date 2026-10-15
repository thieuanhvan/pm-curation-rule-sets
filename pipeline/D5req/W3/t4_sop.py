# T4: SOP model provenance. (a) Petri nets derived strictly from documented SOP text vs from code; alignment fitness/precision.
# (b) Object-centric (per-object lifecycle alignments) vs flattened (case-level alignment) verdicts per event, per object type,
#     with convergence/divergence counts -> substantiate/refute the "flattening artefact" claim.
import json, sys, time, collections as C, numpy as np, pandas as pd, pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
rng = np.random.default_rng(20261007)
R = {}
def P(k, v): R[k] = v; print(k, json.dumps(v, default=str)[:2500], flush=True)
A2 = '../A2/out/'
DEC = ('ACCEPTED', 'REJECTED')
# ---------------- models (process-tree strings)
REVC = "'REVISION_COMMENTED'"
def body(kind, pre):
    if kind == 'text':  # documented: revisions suggested + reviewed (accept/reject); comments (deletable, using/comments); flags (raise; editors rectify)
        rev = "->( 'REVISION_SUGGESTED', X( 'REVISION_ACCEPTED', 'REVISION_REJECTED' ) )" if pre else "->( 'REVISION_SUGGESTED', X( tau, 'REVISION_ACCEPTED', 'REVISION_REJECTED' ) )"
        return f"*( tau, X( {rev}, 'COMMENTED', {REVC}, 'COMMENT_DELETED', ->( 'FLAGGED', X( tau, 'FLAG_RESOLVED' ) ) ) )"
    if kind == 'text_flower':
        return f"*( tau, X( 'REVISION_SUGGESTED', 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'COMMENTED', {REVC}, 'COMMENT_DELETED', 'FLAGGED', 'FLAG_RESOLVED' ) )"
    if kind == 'code':  # A2 strict model = code semantics (optional moderation, superseded, revert cycle)
        return f"*( tau, X( ->( 'REVISION_SUGGESTED', X( tau, 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED' ) ), 'COMMENTED', {REVC}, 'COMMENT_DELETED', ->( 'FLAGGED', X( tau, 'FLAG_RESOLVED' ) ) ) )"
    if kind == 'code_flower':
        return f"*( tau, X( 'REVISION_SUGGESTED', 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED', 'COMMENTED', {REVC}, 'COMMENT_DELETED', 'FLAGGED', 'FLAG_RESOLVED' ) )"
def model(kind):
    if kind.startswith('text'):   # no REVERTED, no SUPERSEDED (not documented); "all revisions reviewed ... then accepted" -> pre-decision revisions moderated
        return f"->( 'SUBMITTED', {body(kind, True)}, X( 'ACCEPTED', 'REJECTED' ), {body(kind, False)} )"
    b = body(kind, False)
    return f"->( 'SUBMITTED', {b}, X( 'ACCEPTED', 'REJECTED' ), {b}, X( tau, ->( 'REVERTED', {b}, X( tau, ->( X( 'ACCEPTED', 'REJECTED' ), {b} ) ) ) ) )"
MODELS = {'TEXT_strict': model('text'), 'TEXT_interleaved': model('text_flower'), 'CODE_strict': model('code'), 'CODE_interleaved': model('code_flower')}
def mklog(vs):
    lg = EventLog()
    for i, k in enumerate(vs):
        tr = Trace(); tr.attributes['concept:name'] = f'v{i}'
        for a in k: tr.append(Event({'concept:name': a}))
        lg.append(tr)
    return lg
def nets():
    out = {}
    for name, s in MODELS.items():
        net, im, fm = pm4py.convert_to_petri_net(pm4py.parse_process_tree(s)); out[name] = (net, im, fm)
        pm4py.write_pnml(net, im, fm, f'{name}.pnml')
    return out
NETS = nets()
def run(mode):
    cx = pd.read_pickle(A2 + f'caselog_ei_{mode}.pkl')
    dec_cases = set(cx.loc[cx['concept:name'].isin(DEC), 'case:concept:name'])
    L = cx[cx['case:concept:name'].isin(dec_cases)].copy()
    traces = {k: tuple(g['concept:name']) for k, g in L.groupby('case:concept:name', sort=False)}
    var = C.Counter(traces.values()); vs = list(var.keys()); w = np.array([var[v] for v in vs], float)
    vlog = mklog(vs)
    res = {'decided_cases': len(dec_cases), 'variants': len(vs)}
    moves = {}
    for name, (net, im, fm) in NETS.items():
        t0 = time.time()
        al = pm4py.conformance_diagnostics_alignments(vlog, net, im, fm, multi_processing=False)
        fit = np.array([a['fitness'] for a in al])
        lm = []
        for a in al:
            pos, mv = 0, set()
            for (l, m) in a['alignment']:
                if l != '>>':
                    if m == '>>': mv.add(pos)
                    pos += 1
            lm.append(mv)
        moves[name] = dict(zip(vs, lm))
        # case-weighted fitness with case-bootstrap CI
        bs = [np.average(fit, weights=rng.multinomial(int(w.sum()), w / w.sum()) + 1e-12) for _ in range(500)]
        dev = C.Counter()
        for v, mv, ww in zip(vs, lm, w):
            for kk in {v[p] for p in mv}: dev[kk] += ww
        o = {'align_fitness_case_weighted': round(float(np.average(fit, weights=w)), 4), 'ci95_case_boot': [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
             'perfectly_fitting_case_share': round(float(w[fit >= 0.99999].sum() / w.sum()), 4),
             'cases_with_log_move_by_activity(share)': {k: round(v / w.sum(), 4) for k, v in dev.most_common(12)}, 'sec_align': round(time.time() - t0)}
        t1 = time.time()
        try:
            # precision on all variants (each variant once; ETC alignments)
            o['align_etc_precision(all variants)'] = round(pm4py.precision_alignments(vlog, net, im, fm, multi_processing=False), 4)
        except Exception as e: o['align_etc_precision(all variants)'] = f'ERR {e}'
        o['sec_prec'] = round(time.time() - t1)
        res[name] = o
        print(mode, name, json.dumps(o), flush=True)
    return res, L, traces, moves
for mode in ('excl', 'incl'):
    res, L, traces, moves = run(mode)
    P(f'petri_fitness_precision_{mode}_bot', res)
    if mode == 'incl': Linc, trinc, mvinc = L, traces, moves

# ---------------- (b) object-centric lifecycle alignments per object type (incl. bot events: full object histories)
L = Linc.sort_values(['case:concept:name', 'time:timestamp', 'src_id']).reset_index(drop=True)
L['pos'] = L.groupby('case:concept:name').cumcount()
OBJ = {
    'revision': ('revision', "->( 'REVISION_SUGGESTED', *( tau, 'REVISION_COMMENTED' ), X( tau, ->( X( 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED' ), *( tau, 'REVISION_COMMENTED' ) ) ) )",
                 ['REVISION_SUGGESTED', 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED', 'REVISION_COMMENTED']),
    'comment': ('comment', "->( X( 'COMMENTED', 'REVISION_COMMENTED' ), X( tau, 'COMMENT_DELETED' ) )", ['COMMENTED', 'REVISION_COMMENTED', 'COMMENT_DELETED']),
    'flag': ('flag', "->( 'FLAGGED', X( tau, 'FLAG_RESOLVED' ) )", ['FLAGGED', 'FLAG_RESOLVED']),
}
ocv = {}   # (case, pos, objtype) -> OC log move?
oc_fit = {}
for ot, (col, tree, acts) in OBJ.items():
    sub = L[L[col].notna() & L['concept:name'].isin(acts)].copy()
    sub[col] = sub[col].astype(str)
    sub = sub.sort_values([col, 'time:timestamp', 'src_id'])
    ob = {k: g for k, g in sub.groupby(col, sort=False)}
    tr = {k: tuple(g['concept:name']) for k, g in ob.items()}
    var = C.Counter(tr.values()); vs = list(var); w = np.array([var[v] for v in vs], float)
    net, im, fm = pm4py.convert_to_petri_net(pm4py.parse_process_tree(tree))
    al = pm4py.conformance_diagnostics_alignments(mklog(vs), net, im, fm, multi_processing=False)
    mvv = {}
    for v, a in zip(vs, al):
        pos, mv = 0, set()
        for (l, m) in a['alignment']:
            if l != '>>':
                if m == '>>': mv.add(pos)
                pos += 1
        mvv[v] = mv
    fit = np.array([a['fitness'] for a in al])
    oc_fit[ot] = {'objects': int(w.sum()), 'variants': len(vs), 'fitness_object_weighted': round(float(np.average(fit, weights=w)), 4),
                  'perfectly_fitting_object_share': round(float(w[fit >= 0.99999].sum() / w.sum()), 4)}
    for k, g in ob.items():
        mv = mvv[tr[k]]
        for p, (c, cp_) in enumerate(zip(g['case:concept:name'], g['pos'])): ocv[(c, cp_, ot)] = p in mv
P('oc_lifecycle_alignment_incl_bot', oc_fit)
# event-level 2x2 per object type and flattened model
cmp = {}
TYPE_OF = {a: ot for ot, (_, _, acts) in OBJ.items() for a in acts}
for name in ('CODE_strict', 'TEXT_strict', 'CODE_interleaved', 'TEXT_interleaved'):
    mv = mvinc[name]; tab = {ot: C.Counter() for ot in OBJ}
    for c, g in L.groupby('case:concept:name', sort=False):
        fm_ = mv[trinc[c]]
        for p, a in zip(g['pos'], g['concept:name']):
            for ot in OBJ:
                if (c, p, ot) in ocv:
                    f = p in fm_; o = ocv[(c, p, ot)]
                    tab[ot][('flat_dev' if f else 'flat_ok') + '|' + ('oc_dev' if o else 'oc_ok')] += 1
    out = {}
    for ot, t in tab.items():
        n = sum(t.values()); fd = t['flat_dev|oc_ok'] + t['flat_dev|oc_dev']
        out[ot] = {'events': n, 'converge_ok': t['flat_ok|oc_ok'], 'converge_dev': t['flat_dev|oc_dev'],
                   'diverge_flat_only(flattening artefact)': t['flat_dev|oc_ok'], 'diverge_oc_only(masked by flattening)': t['flat_ok|oc_dev'],
                   'share_of_flat_deviations_that_are_artefacts': round(t['flat_dev|oc_ok'] / fd, 3) if fd else None}
    cmp[name] = out
P('oc_vs_flattened_event_level', cmp)
# inter-object constraint evidence<->revision from the TEXT SOP: "no pending revision at acceptance"; OC vs flattened
pend_oc = pend_flat = n = both = 0
for c, g in L.groupby('case:concept:name', sort=False):
    open_r = set(); last_unmod = 0
    for a, r in zip(g['concept:name'], g['revision']):
        if a == 'REVISION_SUGGESTED': open_r.add(r); last_unmod += 1
        elif a in ('REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED'): open_r.discard(r); last_unmod = max(0, last_unmod - 1)
        elif a == 'ACCEPTED':
            n += 1; o = len(open_r) > 0; f = last_unmod > 0; pend_oc += o; pend_flat += f; both += o and f
P('evidence_revision_no_pending_at_acceptance', {'acceptances': n, 'violations_OC(by revision id)': pend_oc, 'violations_flattened(count-based)': pend_flat, 'both': both,
                                                 'OC_violation_rate': round(pend_oc / n, 4), 'flat_violation_rate': round(pend_flat / n, 4)})
json.dump(R, open('res_t4_sop.json', 'w'), indent=1, default=str)
