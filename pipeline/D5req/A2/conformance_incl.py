# A2 step 3: conformance of the CIViC evidence-item process against the documented SOP (Danos et al. 2019; civic.readthedocs.io).
# (a) SOP as process tree -> Petri net; alignment fitness + align-ETC precision on decided cases (variant-level, sample if needed);
# (b) DECLARE/LTLf constraints incl. data-aware four-eyes, evaluated with activation-aware metrics; object-centric revision/flag constraints.
import json, sys, time, collections as C, numpy as np, pandas as pd, pm4py
OUT = 'out/'; RES = {}; rng = np.random.default_rng(20261007)
def P(k, v): RES[k] = v; print(k, json.dumps(v, default=str)[:1500], flush=True)
def wilson(k, n, z=1.96):
    if n == 0: return [None, None, None, 0]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 4), round(c - h, 4), round(c + h, 4), n]
NOW = pd.Timestamp('2026-10-07T00:00:00Z'); MATURE = NOW - pd.Timedelta(days=730)
cx = pd.read_pickle(OUT + 'caselog_ei_excl.pkl'); ci = pd.read_pickle(OUT + 'caselog_ei_incl.pkl')
DEC = ('ACCEPTED', 'REJECTED')

# ------------------------------------------------------------------ (a) Petri-net conformance
BODY = "*( tau, X( ->( 'REVISION_SUGGESTED', X( tau, 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED' ) ), 'COMMENTED', 'REVISION_COMMENTED', 'COMMENT_DELETED', ->( 'FLAGGED', X( tau, 'FLAG_RESOLVED' ) ) ) )"
BODYF = "*( tau, X( 'REVISION_SUGGESTED', 'REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED', 'COMMENTED', 'REVISION_COMMENTED', 'COMMENT_DELETED', 'FLAGGED', 'FLAG_RESOLVED' ) )"
def sop(body):
    return f"->( 'SUBMITTED', {body}, X( 'ACCEPTED', 'REJECTED' ), {body}, X( tau, ->( 'REVERTED', {body}, X( tau, ->( X( 'ACCEPTED', 'REJECTED' ), {body} ) ) ) ) )"
models = {'SOP_strict_revision_cycles': sop(BODY), 'SOP_revision_flower': sop(BODYF)}
dec_cases = set(cx.loc[cx['concept:name'].isin(DEC), 'case:concept:name'])
L = ci[ci['case:concept:name'].isin(dec_cases)][['case:concept:name', 'concept:name', 'time:timestamp']].copy()
L = pm4py.format_dataframe(L, case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
var = pm4py.get_variants(L); nv = len(var)
P('alignment_log', {'decided_cases': len(dec_cases), 'variants': nv, 'trace_len_p50_p90_max': [int(x) for x in np.percentile(L.groupby('case:concept:name').size(), [50, 90, 100])]})
# sample design: all variants with frequency >= 2 (cover most cases) + simple random sample of 400 singleton variants (seed 20261007); weights restore case-level estimates
freq = sorted(var.items(), key=lambda x: -x[1]); multi = [v for v in freq if v[1] >= 2]; single = [v for v in freq if v[1] == 1]
pick = rng.choice(len(single), min(400, len(single)), replace=False); sampled = multi + [single[i] for i in pick]
w_single = len(single) / max(1, len(pick))
P('alignment_sample', {'multi_variants': len(multi), 'cases_in_multi': sum(v[1] for v in multi), 'singleton_variants': len(single), 'singletons_sampled': len(pick), 'singleton_weight': round(w_single, 3)})
from pm4py.objects.log.obj import EventLog, Trace, Event
def mklog(vs):
    lg = EventLog()
    for i, (k, n) in enumerate(vs):
        tr = Trace(); tr.attributes['concept:name'] = f'v{i}'
        for a in k: tr.append(Event({'concept:name': a}))
        lg.append(tr)
    return lg
vlog = mklog(sampled)
dev_tables = {}
for name, s in list(models.items()):
    tree = pm4py.parse_process_tree(s); net, im, fm = pm4py.convert_to_petri_net(tree)
    pm4py.write_pnml(net, im, fm, OUT + f'{name}_incl.pnml')
    t0 = time.time()
    al = pm4py.conformance_diagnostics_alignments(vlog, net, im, fm, multi_processing=False)
    ta = time.time() - t0
    fits, wts, dev = [], [], C.Counter(); devcase = C.Counter(); perfect = 0; tot = 0
    for (k, n), a in zip(sampled, al):
        w = n if n >= 2 else w_single
        fits.append(a['fitness']); wts.append(w); tot += w
        if a['fitness'] >= 0.99999: perfect += w
        seen = set()
        for (lm, mm) in a['alignment']:
            if lm == '>>' and mm is not None: key = 'model_move(skip):' + mm
            elif mm == '>>': key = 'log_move(unexpected):' + lm
            else: continue
            dev[key] += w; seen.add(key)
        for kk in seen: devcase[kk] += w
    fits, wts = np.array(fits), np.array(wts)
    fit = float(np.sum(fits * wts) / np.sum(wts))
    # bootstrap over sampled singleton variants for CI
    bs = []
    mi = np.array([n >= 2 for (k, n) in sampled])
    for _ in range(500):
        jj = rng.choice(np.where(~mi)[0], (~mi).sum()); f = np.concatenate([fits[mi], fits[jj]]); ww = np.concatenate([wts[mi], wts[jj]]); bs.append(np.sum(f * ww) / np.sum(ww))
    t1 = time.time()
    try:
        prec = pm4py.precision_alignments(vlog, net, im, fm, multi_processing=False)
    except Exception as e: prec = f'ERR {e}'
    tp = time.time() - t1
    tl = mklog(multi + [single[i] for i in pick])
    P('petri_' + name, {'places': len(net.places), 'transitions': len(net.transitions), 'align_fitness_case_weighted': round(fit, 4), 'ci95_boot': [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                        'perfectly_fitting_case_share': round(perfect / tot, 4), 'align_etc_precision_on_variant_sample': prec if isinstance(prec, str) else round(prec, 4), 'sec_align': round(ta), 'sec_prec': round(tp)})
    dev_tables[name] = [(k, round(v / tot, 4)) for k, v in devcase.most_common(15)]
P('deviation_types_case_share', dev_tables)
json.dump(RES, open(OUT + 'conformance_petri_incl_bot.json', 'w'), indent=1, default=str)
