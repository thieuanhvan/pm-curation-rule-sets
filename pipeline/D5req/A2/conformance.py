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
L = cx[cx['case:concept:name'].isin(dec_cases)][['case:concept:name', 'concept:name', 'time:timestamp']].copy()
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
    pm4py.write_pnml(net, im, fm, OUT + f'{name}.pnml')
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
# IMf comparison: see discovery.json (token-based replay); alignments on the IMf net were too slow (state explosion from silent transitions) and were dropped
# ------------------------------------------------------------------ (b) DECLARE / LTLf with activation-aware metrics
def caselist(df):
    return {k: g.reset_index(drop=True) for k, g in df.groupby('case:concept:name', sort=False)}
CX = caselist(cx)
R = {}
def report(name, act, ful, tr_act, tr_ok, n_tr, extra=None):
    R[name] = {'event_confidence': wilson(ful, act), 'activated_traces': tr_act, 'trace_confidence': wilson(tr_ok, tr_act), 'non_vacuous_support': wilson(tr_ok, n_tr), 'vacuous_share': round(1 - tr_act / n_tr, 4) if n_tr else None}
    if extra: R[name].update(extra)
n_tr = len(CX)
# C1 init(SUBMITTED)
ok = sum(g['concept:name'].iloc[0] == 'SUBMITTED' for g in CX.values()); report('init(SUBMITTED)', n_tr, ok, n_tr, ok, n_tr)
# C2 response(SUBMITTED, ACC|REJ): all and mature (submitted >= 2 y before cut-off)
for lab, cond in (('all', lambda t: True), ('mature_2y', lambda t: t <= MATURE)):
    act = ful = 0
    for g in CX.values():
        a = g['concept:name'].tolist(); s = [i for i, x in enumerate(a) if x == 'SUBMITTED']
        if not s or not cond(g['time:timestamp'].iloc[s[0]]): continue
        act += 1; ful += any(x in DEC for x in a[s[0] + 1:]) or any(x in DEC for x in a[s[0]:])
    report(f'response(SUBMITTED, ACCEPTED|REJECTED)[{lab}]', act, ful, act, ful, n_tr)
# C3 precedence(SUBMITTED, ACC|REJ)
act = ful = ta = to = 0
for g in CX.values():
    a = g['concept:name'].tolist(); ds = [i for i, x in enumerate(a) if x in DEC]
    if not ds: continue
    ta += 1; good = True
    for i in ds:
        act += 1; f = 'SUBMITTED' in a[:i] or (i + 1 < len(a) and a[i + 1] == 'SUBMITTED' and g['time:timestamp'][i] == g['time:timestamp'][i + 1]); ful += f; good &= f
    to += good
report('precedence(SUBMITTED, ACCEPTED|REJECTED)', act, ful, ta, to, n_tr, {'note': 'same-timestamp SUBMITTED counted as preceding (2015 bulk import ties)'})
# C4 not-coexistence(ACCEPTED, REJECTED) strict and 'unless REVERTED between'; C5 at most one decision per REVERTED cycle
nc = nc2 = ta = 0; multi_dec = 0
for g in CX.values():
    a = [x for x in g['concept:name'] if x in DEC + ('REVERTED',)]
    if not any(x in DEC for x in a): continue
    ta += 1
    nc += not ('ACCEPTED' in a and 'REJECTED' in a)
    ok2 = True; last = None
    for x in a:
        if x == 'REVERTED': last = None
        elif last is not None: ok2 = False
        else: last = x
    nc2 += ok2
report('not-coexistence(ACCEPTED, REJECTED)[strict]', ta, nc, ta, nc, n_tr)
report('at-most-one decision between reversions (absence2 per cycle)', ta, nc2, ta, nc2, n_tr)
# C6 precedence(COMMENT, REJECTED) - reasoned rejection; variants: any comment (EI or revision) before; comment within 30 d before/after; comment by the rejector
for lab in ('any_before', 'within_30d_before_or_after', 'by_rejector_before_or_same_day'):
    act = ful = ta = to = 0
    for g in CX.values():
        a = g['concept:name'].tolist(); rj = [i for i, x in enumerate(a) if x == 'REJECTED']
        if not rj: continue
        ta += 1; good = True
        for i in rj:
            act += 1; t = g['time:timestamp'][i]; u = g['org:resource'][i]
            cm = [j for j, x in enumerate(a) if x in ('COMMENTED', 'REVISION_COMMENTED')]
            if lab == 'any_before': f = any(j < i for j in cm)
            elif lab == 'within_30d_before_or_after': f = any(abs((g['time:timestamp'][j] - t).days) <= 30 for j in cm)
            else: f = any(g['org:resource'][j] == u and g['time:timestamp'][j] <= t + pd.Timedelta(days=1) for j in cm)
            ful += f; good &= f
        to += good
    report(f'precedence(COMMENT, REJECTED)[{lab}]', act, ful, ta, to, n_tr)
# C7 four-eyes (data-aware): resource(decision) != resource(SUBMITTED)
for d in DEC:
    act = ful = 0; viol_roles = C.Counter()
    for g in CX.values():
        a = g['concept:name'].tolist(); s = [i for i, x in enumerate(a) if x == 'SUBMITTED']
        if not s: continue
        su = g['org:resource'][s[0]]
        for i, x in enumerate(a):
            if x == d:
                act += 1; f = g['org:resource'][i] != su; ful += f
                if not f: viol_roles[g['role_now'][i]] += 1
    report(f'four-eyes: user({d}) != user(SUBMITTED)', act, ful, act, ful, n_tr, {'violations_by_current_role': dict(viol_roles)})
# C8 role-aware decision: decider current role in {EDITOR, ADMIN}
act = ful = 0; rr = C.Counter()
for g in CX.values():
    for i, x in enumerate(g['concept:name']):
        if x in DEC: act += 1; r = g['role_now'][i]; ful += r in ('EDITOR', 'ADMIN'); rr[(x, r)] += 1
report('role(decider) in {EDITOR, ADMIN} [current role, approximate]', act, ful, act, ful, n_tr, {'by_action_role': {f'{k[0]}|{k[1]}': v for k, v in rr.items()}})
# C9 no acceptance while a flag is open / while revisions are pending (hygiene, not stated SOP)
CI = caselist(ci)
for lab, opener, closer in (('open_flag', 'FLAGGED', ('FLAG_RESOLVED',)), ('pending_revision', 'REVISION_SUGGESTED', ('REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED'))):
    key = 'flag' if lab == 'open_flag' else 'revision'
    act = ful = 0
    for g in CI.values():
        openset = set()
        for i, x in enumerate(g['concept:name']):
            if x == opener: openset.add(g[key][i])
            elif x in closer: openset.discard(g[key][i])
            elif x == 'ACCEPTED': act += 1; ful += not openset
    report(f'not ACCEPTED while {lab} (incl. bot objects)', act, ful, act, ful, len(CI))

# ---- object-centric constraints on revision and flag objects (incl. bot; bot = automated curator account)
def objlog(df, key):
    return {k: g.reset_index(drop=True) for k, g in df[df[key].notna()].groupby(key, sort=False)}
REV = objlog(ci, 'revision'); FLG = objlog(ci, 'flag')
bot_users = set(ci.loc[ci['is_bot'], 'org:resource'])
MOD = ('REVISION_ACCEPTED', 'REVISION_REJECTED', 'REVISION_SUPERSEDED')
pre = ful = 0; resp = respf = 0; one = onef = 0; fe = fef = 0; self_rej = rej = rej_cm = 0; by_sugg = C.Counter(); sub_bot = C.Counter()
for k, g in REV.items():
    a = g['concept:name'].tolist(); u = g['org:resource'].tolist(); t = g['time:timestamp'].tolist()
    s = [i for i, x in enumerate(a) if x == 'REVISION_SUGGESTED']; m = [i for i, x in enumerate(a) if x in MOD]
    for i in m: pre += 1; ful += bool(s) and s[0] < i
    if s and t[s[0]] <= MATURE:
        resp += 1; respf += bool(m); sub_bot[('bot' if u[s[0]] in bot_users else 'human', bool(m))] += 1
    if m: one += 1; onef += len(m) == 1
    for i in m:
        if a[i] == 'REVISION_ACCEPTED' and s:
            fe += 1; fef += u[i] != u[s[0]]
        if a[i] == 'REVISION_REJECTED' and s:
            rej += 1; self_rej += u[i] == u[s[0]]
            rej_cm += any(a[j] == 'REVISION_COMMENTED' and j < i for j in range(len(a)))
    if s: by_sugg[('bot' if u[s[0]] in bot_users else 'human', next((a[i] for i in m), 'PENDING'))] += 1
nrev = len(REV)
report('OC revision: precedence(REVISION_SUGGESTED, moderation)', pre, ful, pre, ful, nrev)
report('OC revision: response(REVISION_SUGGESTED, moderation)[mature_2y]', resp, respf, resp, respf, nrev, {'by_suggester': {f'{k[0]}|moderated={k[1]}': v for k, v in sub_bot.items()}})
report('OC revision: exactly-one moderation', one, onef, one, onef, nrev)
report('OC revision four-eyes: user(REVISION_ACCEPTED) != user(REVISION_SUGGESTED) [same revision object]', fe, fef, fe, fef, nrev)
report('OC revision: reasoned rejection precedence(REVISION_COMMENTED, REVISION_REJECTED)', rej, rej_cm, rej, rej_cm, nrev, {'self_rejections(withdrawals)': wilson(self_rej, rej)})
P('revision_outcome_by_suggester_type', {f'{k[0]}|{k[1]}': v for k, v in by_sugg.most_common()})
# flattened approximation of the revision four-eyes check (what a case-level log without revision ids would conclude)
fa = faf = 0
for g in CI.values():
    last_s = None
    for i, x in enumerate(g['concept:name']):
        if x == 'REVISION_SUGGESTED': last_s = g['org:resource'][i]
        elif x == 'REVISION_ACCEPTED' and last_s is not None: fa += 1; faf += g['org:resource'][i] != last_s
R['FLATTENED approx four-eyes: user(REVISION_ACCEPTED) != user(last REVISION_SUGGESTED in case)'] = {'event_confidence': wilson(faf, fa)}
fl_r = C.Counter(); fpre = fpf = 0; ffe = ffef = 0
for k, g in FLG.items():
    a = g['concept:name'].tolist(); u = g['org:resource'].tolist(); t = g['time:timestamp'].tolist()
    f = [i for i, x in enumerate(a) if x == 'FLAGGED']; r = [i for i, x in enumerate(a) if x == 'FLAG_RESOLVED']
    for i in r: fpre += 1; fpf += bool(f) and f[0] < i
    for i in r:
        if f: ffe += 1; ffef += u[i] != u[f[0]]
    if f and t[f[0]] <= MATURE: fl_r[('bot' if u[f[0]] in bot_users else 'human', bool(r))] += 1
for who in ('bot', 'human'):
    n = fl_r[(who, True)] + fl_r[(who, False)]; report(f'OC flag: response(FLAGGED, FLAG_RESOLVED)[mature_2y, raised by {who}]', n, fl_r[(who, True)], n, fl_r[(who, True)], len(FLG))
report('OC flag: precedence(FLAGGED, FLAG_RESOLVED)', fpre, fpf, fpre, fpf, len(FLG))
report('OC flag four-eyes: resolver != raiser', ffe, ffef, ffe, ffef, len(FLG))
P('declare', R)
# discovered DECLARE (pm4py) on decided cases, for contrast with the prescribed set
try:
    dm = pm4py.discover_declare(L, min_support_ratio=0.5, min_confidence_ratio=0.9)
    P('pm4py_discover_declare_decided', {tpl: sorted([(' , '.join(k) if isinstance(k, tuple) else k, round(v['confidence'], 3)) for k, v in d.items()], key=lambda x: -x[1])[:10] for tpl, d in dm.items() if d})
except Exception as e: P('pm4py_discover_declare_decided', f'ERR {e}')
json.dump(RES, open(OUT + 'conformance.json', 'w'), indent=1, default=str)
