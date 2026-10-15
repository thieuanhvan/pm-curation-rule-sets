# W2 step 3: process mining + survival for GO / HPO 500-ticket samples, mirroring the CIViC analyses of D5req/A2 and A5.
# (1) discovery: DFG, OC-DFG, variants, IMf (noise 0.2) + token replay (all cases) + alignments (seeded variant-weighted sample)
# (2) DECLARE-style constraints with activation / vacuity and Wilson CIs, split by submitter insider/outsider
# (3) time-varying Cox (counting process, statsmodels PHReg, strata = era), exposure lag 0 / 7 / 30 d, any / ACC / REJ
# (4) Aalen-Johansen CIFs with right-censoring (pending tickets), landmark AJ at 30 d by exposure
# (5) regime triple (rho 2023-25, discipline u on live queue <= 365 d, top-5 closer share) with bootstrap CIs
import json, os, sys, collections as C, warnings
import numpy as np, pandas as pd, pm4py
from statsmodels.duration.hazard_regression import PHReg
warnings.filterwarnings('ignore')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
RES = {}; rng = np.random.default_rng(20261007); NOW = pd.Timestamp('2026-10-07T00:00:00Z'); D = 86400.0
B = int(os.environ.get('B', 1000))
def P(k, v): RES[k] = v; print(k, json.dumps(v, default=str)[:900], flush=True)
def wilson(k, n, z=1.96):
    if n == 0: return [None, None, None, 0]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 4), round(c - h, 4), round(c + h, 4), int(n)]
def pci(a):
    a = np.asarray([x for x in a if np.isfinite(x)]); return [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)] if len(a) else None

cl = pd.read_pickle('internal/caselog_w2.pkl'); tab = pd.read_pickle('internal/tickets_w2.pkl')
pick = pd.read_pickle('internal/ocel_w2.pkl')
P('sample', {t: {'n': int((tab.tag == t).sum()), 'open': int(((tab.tag == t) & (tab.state == 'open')).sum()),
                 'closed_by_class': tab[(tab.tag == t)]['cls'].fillna('PENDING').value_counts().to_dict(),
                 'insider_submitter_share': wilson(int(tab[(tab.tag == t)].insider.sum()), int((tab.tag == t).sum())),
                 'source': tab[tab.tag == t]['src'].value_counts().to_dict(),
                 'classifier_coverage_closed': wilson(int(tab[(tab.tag == t) & tab.cls.isin(['ACC', 'REJ'])].shape[0]), int(tab[(tab.tag == t) & tab.cls.notna()].shape[0])),
                 'accept_share_classified': wilson(int((tab[(tab.tag == t)].cls == 'ACC').sum()), int(tab[(tab.tag == t) & tab.cls.isin(['ACC', 'REJ'])].shape[0])),
                 'OBO_corroborated_ACC': wilson(int(tab[(tab.tag == t) & (tab.cls == 'ACC')].corroborated.fillna(False).astype(bool).sum()), int(((tab.tag == t) & (tab.cls == 'ACC')).sum())),
                 'OBO_corroborated_REJ': wilson(int(tab[(tab.tag == t) & (tab.cls == 'REJ')].corroborated.fillna(False).astype(bool).sum()), int(((tab.tag == t) & (tab.cls == 'REJ')).sum())),
                 'OBO_corroborated_UNCLEAR': wilson(int(tab[(tab.tag == t) & (tab.cls == 'UNCLEAR')].corroborated.fillna(False).astype(bool).sum()), int(((tab.tag == t) & (tab.cls == 'UNCLEAR')).sum())),
                 'tier_counts': tab[(tab.tag == t) & tab.cls.notna()].apply(lambda r: f"{r.cls}_T{r.tier}", axis=1).value_counts().to_dict(),
                 'state_reason_final_close': tab[(tab.tag == t) & tab.cls.notna()].closeSR.fillna('none').value_counts().to_dict()} for t in ('go', 'hpo')})

# ---------------------------------------------------------------- (1) discovery
def discover(df, name):
    df = df[['case:concept:name', 'concept:name', 'time:timestamp', 'org:resource']].copy()
    df = pm4py.format_dataframe(df, case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
    dfg, sa, ea = pm4py.discover_dfg(df)
    v = pm4py.get_variants(df); n = sum(v.values()); s = sorted(v.items(), key=lambda x: -x[1])
    cc = df.copy(); cc['prev'] = cc.groupby('case:concept:name')['concept:name'].shift(); cc = cc[cc['concept:name'] != cc['prev']].drop(columns='prev')
    v2 = pm4py.get_variants(cc); s2 = sorted(v2.items(), key=lambda x: -x[1])
    net, im, fm = pm4py.discover_petri_net_inductive(df, noise_threshold=0.2); pm4py.write_pnml(net, im, fm, f'out/imf_{name}.pnml')
    out = {'cases': int(n), 'events': len(df), 'activities': df['concept:name'].value_counts().to_dict(),
           'top_edges': [(a + ' -> ' + b, c) for (a, b), c in sorted(dfg.items(), key=lambda x: -x[1])[:15]], 'start': sa, 'end': ea,
           'variants_distinct': len(s), 'top1_variant_share': wilson(s[0][1], n), 'variants_selfloops_collapsed': len(s2),
           'top_variants_collapsed': [(' > '.join(k[:12]), c) for k, c in s2[:8]],
           'process_tree': str(pm4py.discover_process_tree_inductive(df, noise_threshold=0.2))[:700]}
    try:
        tr = pm4py.fitness_token_based_replay(df, net, im, fm); out['token_replay'] = {'log_fitness': round(tr['log_fitness'], 4), 'perc_fit_traces': round(tr['perc_fit_traces'], 2),
            'precision_etc': round(pm4py.precision_token_based_replay(df, net, im, fm), 4)}
    except Exception as e: out['token_replay'] = f'ERR {e}'
    # alignments on a seeded sample of up to 150 cases (cases drawn uniformly => variant-weighted)
    ids = df['case:concept:name'].unique(); sm = rng.choice(ids, min(150, len(ids)), replace=False); dsm = df[df['case:concept:name'].isin(sm)]
    try:
        fa = pm4py.fitness_alignments(dsm, net, im, fm); pa = pm4py.precision_alignments(dsm, net, im, fm)
        # bootstrap CI over the sampled cases for alignment fitness
        al = pm4py.conformance_diagnostics_alignments(dsm, net, im, fm); f = np.array([a['fitness'] for a in al])
        out['alignments_sample'] = {'n_cases': len(sm), 'avg_trace_fitness': round(fa['average_trace_fitness'], 4), 'ci95': pci([rng.choice(f, len(f)).mean() for _ in range(B)]),
                                    'perc_fit_traces': round(fa['percFitTraces'], 2), 'precision_align': round(pa, 4)}
    except Exception as e: out['alignments_sample'] = f'ERR {e}'
    P('discovery_' + name, out); return df
for tag in ('go', 'hpo'):
    discover(cl[cl.repo == tag], tag)
    discover(cl[(cl.repo == tag) & cl['case:concept:name'].isin(tab[(tab.tag == tag) & (tab.state == 'closed')].tid)], tag + '_closed_only')

# OC-DFG on the OCEL (both repos)
try:
    from pm4py.objects.ocel.obj import OCEL
    ocel = OCEL(events=pick['events'], objects=pick['objects'], relations=pick['relations'])
    oc = pm4py.discover_ocdfg(ocel)
    edges = {}
    for ot, d in oc['edges']['event_couples'].items():
        edges[ot] = sorted([(f'{a} -> {b}', len(v)) for (a, b), v in d.items()], key=lambda x: -x[1])[:12]
    acts = {ot: {a: len(v) for a, v in d.items()} for ot, d in oc['activities_ot']['events'].items()} if 'activities_ot' in oc else None
    P('ocdfg', {'object_types': list(edges), 'top_edges_per_type': edges, 'activity_counts_per_type': acts,
                'objects_per_type': pick['objects']['ocel:type'].value_counts().to_dict(), 'events': len(pick['events'])})
    try: pm4py.save_vis_ocdfg(oc, 'out/ocdfg_gohpo.svg', annotation='frequency')
    except Exception as e: print('ocdfg vis skipped:', str(e)[:120])
    # OC-DFG vs flattening: convergence/divergence (ticket object type)
    try:
        conv = {}
        for ot in pick['objects']['ocel:type'].unique():
            r = pick['relations'][pick['relations']['ocel:type'] == ot]; per_e = r.groupby('ocel:eid')['ocel:oid'].nunique()
            per_o = r.groupby('ocel:oid')['ocel:eid'].nunique()
            conv[ot] = {'events_with_>1_obj_of_type(convergence)': int((per_e > 1).sum()), 'mean_events_per_object': round(float(per_o.mean()), 2)}
        P('ocel_convergence', conv)
    except Exception as e: print('conv err', e)
except Exception as e: P('ocdfg', f'ERR {e}')

# ---------------------------------------------------------------- (2) DECLARE-style constraints
cases = {k: g.reset_index(drop=True) for k, g in cl.groupby('case:concept:name')}
T = tab.set_index('tid')
def acts(g): return g['concept:name'].tolist()
FIN = ('CLOSED_ACC', 'CLOSED_REJ', 'CLOSED_UNCLEAR')
def fin_idx(a):
    ii = [i for i, x in enumerate(a) if x in FIN]; return ii[-1] if ii else None
DEC = {}
for tag in ('go', 'hpo'):
    R = {}
    for grp, sel in (('all', lambda t: True), ('insider_submitter', lambda t: t.insider), ('outsider_submitter', lambda t: not t.insider)):
        cs = {k: g for k, g in cases.items() if T.loc[k, 'tag'] == tag and sel(T.loc[k])}; n = len(cs)
        r = {'n_traces': n}
        # C1 response(OPENED, CLOSE_final) -- right-censored: pending traces count as (not yet) violated; also among tickets aged >= 365 d, closed within 365 d
        ok = sum(fin_idx(acts(g)) is not None for g in cs.values()); r['response(OPENED,CLOSE)'] = wilson(ok, n)
        old = [k for k in cs if (NOW - pd.Timestamp(T.loc[k, 'open'])).days >= 365]
        ok1 = sum(1 for k in old if T.loc[k, 'state'] == 'closed' and (pd.Timestamp(T.loc[k, 'close']) - pd.Timestamp(T.loc[k, 'open'])).days <= 365)
        r['response_within_365d(OPENED,CLOSE) [aged>=365d]'] = wilson(ok1, len(old))
        # C2 four-eyes: final closer != opener (non-bot closer)
        for d in FIN + ('ANY',):
            act = [k for k, g in cs.items() if (d == 'ANY' and fin_idx(acts(g)) is not None) or d in acts(g)]
            act = [k for k in act if not T.loc[k, 'closerBot'] and T.loc[k, 'closer']]
            ok = sum(T.loc[k, 'closer'] != T.loc[k, 'sub'] for k in act); r[f'four_eyes closer!=opener [{d}]'] = wilson(ok, len(act))
        # C3 precedence(COMMENT_OTHER, CLOSE_final): other-person (non-bot, non-submitter) comment before final close
        for d in FIN:
            act = [g for g in cs.values() if d in acts(g)]
            ok = sum('COMMENT_OTHER' in acts(g)[:acts(g).index(d)] for g in act); r[f'precedence(COMMENT_OTHER,{d})'] = wilson(ok, len(act))
            # stricter: comment by someone other than both submitter and closer
            ok2 = 0
            for g in act:
                i = acts(g).index(d); clo = g['org:resource'][i]
                ok2 += any(a == 'COMMENT_OTHER' and res != clo for a, res in zip(acts(g)[:i], g['org:resource'][:i]))
            r[f'precedence(COMMENT_third_person,{d})'] = wilson(ok2, len(act))
        # C4 implementation trace before accepted close: COMMIT_REF | PR_LINKED | PR_MERGED before CLOSED_ACC; variant counting closing commit as trace
        act = [(k, g) for k, g in cs.items() if 'CLOSED_ACC' in acts(g)]
        ok = sum(any(x in ('COMMIT_REF', 'PR_LINKED', 'PR_MERGED') for x in acts(g)[:acts(g).index('CLOSED_ACC')]) for k, g in act)
        okc = sum(any(x in ('COMMIT_REF', 'PR_LINKED', 'PR_MERGED') for x in acts(g)[:acts(g).index('CLOSED_ACC')]) or bool(T.loc[k, 'closedByCommit']) for k, g in act)
        r['precedence(COMMIT|PR,CLOSED_ACC)'] = wilson(ok, len(act)); r['precedence(COMMIT|PR or closing commit,CLOSED_ACC)'] = wilson(okc, len(act))
        # C5 precedence(ASSIGNED, CLOSE_final)
        act = [g for g in cs.values() if fin_idx(acts(g)) is not None]
        ok = sum('ASSIGNED' in acts(g)[:fin_idx(acts(g))] for g in act); r['precedence(ASSIGNED,CLOSE)'] = wilson(ok, len(act))
        # first other-person response within 30 d (response(OPENED, COMMENT_OTHER|ASSIGNED|CLOSE) timed) among tickets aged >= 30 d
        ok = tot = 0
        for k, g in cs.items():
            t0 = g['time:timestamp'][0]
            if (NOW - t0).days < 30: continue
            tot += 1
            ok += any((a in ('COMMENT_OTHER', 'ASSIGNED') or a in FIN) and (tt - t0).days <= 30 for a, tt in zip(acts(g), g['time:timestamp']))
        r['response_30d(OPENED, COMMENT_OTHER|ASSIGNED|CLOSE)'] = wilson(ok, tot)
        # self-closure share among insider/outsider (the 'conventional gate')
        act = [k for k in cs if T.loc[k, 'state'] == 'closed' and not T.loc[k, 'closerBot'] and T.loc[k, 'closer']]
        r['self_closure_share'] = wilson(sum(T.loc[k, 'closer'] == T.loc[k, 'sub'] for k in act), len(act))
        R[grp] = r
    # vacuity
    n = sum(1 for k in cases if T.loc[k, 'tag'] == tag)
    R['activation_counts'] = {d: sum(1 for k, g in cases.items() if T.loc[k, 'tag'] == tag and d in acts(g)) for d in FIN + ('COMMENT_OTHER', 'ASSIGNED', 'COMMIT_REF', 'PR_LINKED', 'REOPENED')}
    R['reopen_share'] = wilson(R['activation_counts']['REOPENED'], n)
    DEC[tag] = R
P('declare', DEC)
try:
    dd = cl[cl.repo == 'go'][['case:concept:name', 'concept:name', 'time:timestamp']]
    dm = pm4py.discover_declare(pm4py.format_dataframe(dd.copy(), case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp'), min_support_ratio=0.3, min_confidence_ratio=0.8)
    P('pm4py_discover_declare_go_minsupp0.3_conf0.8', {k: [f'{a}' for a in list(v)[:15]] for k, v in dm.items() if v})
except Exception as e: print('discover_declare err', str(e)[:200])

# ---------------------------------------------------------------- (3) survival data
rows = []
for k, g in cases.items():
    t = T.loc[k]; a = acts(g); ts = g['time:timestamp']; t0 = ts[0]
    fi = fin_idx(a)
    if fi is not None: Tt = max((ts[fi] - t0).total_seconds() / D, 1e-3); ev = {'CLOSED_ACC': 1, 'CLOSED_REJ': 2, 'CLOSED_UNCLEAR': 3}[a[fi]]
    else: Tt = (NOW - t0).total_seconds() / D; ev = 0
    def onset(names, before=None):
        ii = [i for i, x in enumerate(a) if x in names and (before is None or i < before)]
        return (ts[ii[0]] - t0).total_seconds() / D if ii else np.inf
    yr = t0.year
    rows.append({'id': k, 'tag': t['tag'], 'T': Tt, 'ev': ev, 'year': yr, 'insider': int(bool(t['insider'])),
                 'comment_other': onset({'COMMENT_OTHER'}, fi), 'comment_sub': onset({'COMMENT_SUBMITTER'}, fi), 'pr_commit': onset({'COMMIT_REF', 'PR_LINKED'}, fi),
                 'assigned': onset({'ASSIGNED'}, fi), 'labeled_later': onset({'LABELED'}, fi)})
S = pd.DataFrame(rows); S['era'] = pd.cut(S['year'], [2015, 2018, 2021, 2027], labels=['2016-18', '2019-21', '2022-26']).astype(str)
S.to_pickle('internal/surv_w2.pkl')
X = ['comment_other', 'comment_sub', 'pr_commit', 'assigned']
P('surv_cohort', {tag: {'n': int((S.tag == tag).sum()), 'events': S[S.tag == tag]['ev'].map({0: 'censored', 1: 'ACC', 2: 'REJ', 3: 'UNCLEAR'}).value_counts().to_dict(),
                        'exposed_before_end': {x: round(float((S[S.tag == tag][x] < S[S.tag == tag]['T']).mean()), 3) for x in X},
                        'exposed_at_t<=1h': {x: int((S[S.tag == tag][x] <= 1 / 24).sum()) for x in X}} for tag in ('go', 'hpo')})

def cox(df, lag, strata_cols=('era',), xs=X, adj=('insider',)):
    d = df.copy()
    for x in xs: d[x] = d[x] + lag
    cp = []; EPS = 1e-3
    for r in d.itertuples():
        cuts = sorted({0.0, r.T} | {getattr(r, x) for x in xs if 0 < getattr(r, x) < r.T})
        for i in range(len(cuts) - 1):
            s0, s1 = cuts[i], cuts[i + 1]; last = s1 == r.T
            cp.append({'start': s0, 'stop': max(s1, s0 + EPS), 'acc': int(r.ev == 1 and last), 'rej': int(r.ev == 2 and last), 'any': int(r.ev > 0 and last),
                       **{x: int(getattr(r, x) <= s0) for x in xs}, **{c: getattr(r, c) for c in adj}, 'strat': '|'.join(str(getattr(r, c)) for c in strata_cols), 'id': r.id})
    cp = pd.DataFrame(cp); Z = cp[list(xs) + list(adj)].astype(float)
    Z = Z.loc[:, Z.std() > 0]
    out = {}
    for o in ('any', 'acc', 'rej'):
        if cp[o].sum() < 5: out[o] = {'events': int(cp[o].sum()), 'note': 'too few events'}; continue
        try:
            m = PHReg(cp['stop'].values, Z.values, status=cp[o].values, entry=cp['start'].values, strata=cp['strat'].values, ties='efron').fit()
            ci = m.conf_int()
            out[o] = {c: {'HR': round(float(np.exp(m.params[i])), 3), 'ci95': [round(float(np.exp(ci[i, 0])), 3), round(float(np.exp(ci[i, 1])), 3)], 'p': float(f'{m.pvalues[i]:.2g}')} for i, c in enumerate(Z.columns)}
            out[o]['events'] = int(cp[o].sum())
        except Exception as e: out[o] = f'ERR {e}'
    return out
CX = {}
for lag in (0, 7, 30):
    for tag in ('go', 'hpo'):
        CX[f'{tag}_lag{lag}'] = cox(S[S.tag == tag], lag)
    CX[f'pooled_lag{lag}'] = cox(S, lag, strata_cols=('tag', 'era'))
P('cox_time_varying', CX)

# ---------------------------------------------------------------- (4) Aalen-Johansen with censoring
def aj_curve(Tv, Ev, grid, causes=(1, 2, 3)):
    o = np.argsort(Tv, kind='stable'); Tv, Ev = Tv[o], Ev[o]; n = len(Tv); S_ = 1.0; F = {c: 0.0 for c in causes}; i = 0; res = {}; gi = 0; grid = list(grid)
    out = []
    while i < n:
        tcur = Tv[i]
        while gi < len(grid) and grid[gi] < tcur: out.append([F[c] for c in causes]); gi += 1
        j = i; dcnt = C.Counter()
        while j < n and Tv[j] == tcur: dcnt[Ev[j]] += 1; j += 1
        at = n - i; dtot = sum(dcnt[c] for c in causes)
        for c in causes: F[c] += S_ * dcnt[c] / at
        S_ *= 1 - dtot / at; i = j
    while gi < len(grid): out.append([F[c] for c in causes]); gi += 1
    return np.array(out)
GRID = [30, 90, 365, 730, 1825]
AJ = {}
for tag in ('go', 'hpo'):
    for nm, sub in (('all', S[S.tag == tag]),) + tuple((f'era_{e}', S[(S.tag == tag) & (S.era == e)]) for e in ('2016-18', '2019-21', '2022-26')) + \
                   (('insider', S[(S.tag == tag) & (S.insider == 1)]), ('outsider', S[(S.tag == tag) & (S.insider == 0)])):
        if len(sub) < 10: continue
        Tv, Ev = sub['T'].values, sub['ev'].values; pt = aj_curve(Tv, Ev, GRID)
        bs = np.array([aj_curve(Tv[ii], Ev[ii], GRID) for ii in (rng.integers(0, len(Tv), len(Tv)) for _ in range(min(B, 500)))])
        AJ[f'{tag}_{nm}'] = {'n': len(sub), 'censored': int((Ev == 0).sum()), **{f'{c}_{g}d': [round(float(pt[gi, ci]), 3)] + pci(bs[:, gi, ci]) for ci, c in enumerate(('CIF_ACC', 'CIF_REJ', 'CIF_UNCLEAR')) for gi, g in enumerate(GRID)}}
P('aalen_johansen', AJ)
LM = {}
for tag in ('go', 'hpo'):
    for L in (30,):
        base = S[(S.tag == tag) & (S['T'] > L)].copy(); base['Tl'] = base['T'] - L
        for x in X:
            res = {}
            for nm, g in (('exposed', base[base[x] <= L]), ('unexposed', base[base[x] > L])):
                if len(g) < 5: res[nm] = {'n': len(g)}; continue
                Tv, Ev = g['Tl'].values, g['ev'].values; pt = aj_curve(Tv, Ev, [365])
                bs = np.array([aj_curve(Tv[ii], Ev[ii], [365]) for ii in (rng.integers(0, len(Tv), len(Tv)) for _ in range(300))])
                res[nm] = {'n': len(g), 'CIF_ACC_1y': [round(float(pt[0, 0]), 3)] + pci(bs[:, 0, 0]), 'CIF_REJ_1y': [round(float(pt[0, 1]), 3)] + pci(bs[:, 0, 1])}
            LM[f'{tag}_L{L}_{x}'] = res
P('landmark_AJ_L30_1y', LM)

# ---------------------------------------------------------------- (5) regime triple (sample-based, actual closer as decider)
W0, W1 = pd.Timestamp('2023-01-01', tz='UTC'), pd.Timestamp('2026-01-01', tz='UTC')
tb = tab.copy(); tb['openT'] = pd.to_datetime(tb['open'], utc=True); tb['closeT'] = pd.to_datetime(tb['close'], utc=True)
def triple(d, decmode):
    isdec = {'closure': d['state'].eq('closed'), 'classified': d['cls'].isin(['ACC', 'REJ']), 'accepted': d['cls'].eq('ACC'),
             'corroborated_lb': (d['cls'].eq('ACC') & d['corroborated'].fillna(False).astype(bool)) | (d['cls'].eq('REJ') & d['tier'].eq(1))}[decmode]
    arr = ((d.openT >= W0) & (d.openT < W1)).sum(); dec = (isdec & (d.closeT >= W0) & (d.closeT < W1)).sum()
    rho = dec / arr if arr else np.nan
    dd = d[isdec & d.closeT.notna()]
    u = dd[dd.closeT >= pd.Timestamp('2016-01-01', tz='UTC')]['uAlive365'].astype(float); u21 = dd[dd.closeT >= pd.Timestamp('2021-01-01', tz='UTC')]['uAlive365'].astype(float)
    uall = dd['u'].astype(float)
    hum = dd[~dd.closerBot.fillna(False).astype(bool) & dd.closer.notna()]; cnt = hum['closer'].value_counts().values
    top5 = cnt[:5].sum() / cnt.sum() if cnt.sum() else np.nan
    return {'rho_2023_25': rho, 'u_alive365_2016plus': u.mean(), 'u_alive365_2021plus': u21.mean(), 'u_allqueue_2016plus': uall.mean(),
            'newest10_alive365': (u <= .1).mean(), 'top5_closer_share': top5, 'n_closers': len(cnt), 'arrivals_W': arr, 'decisions_W': dec}
TR = {}
for tag in ('go', 'hpo'):
    d = tb[tb.tag == tag].reset_index(drop=True)
    for mode in ('closure', 'classified', 'accepted', 'corroborated_lb'):
        pt = triple(d, mode); reps = [triple(d.iloc[rng.integers(0, len(d), len(d))], mode) for _ in range(B)]
        TR[f'{tag}_{mode}'] = {k: {'est': round(float(v), 4) if v == v else None, 'ci95': pci([r[k] for r in reps])} for k, v in pt.items()}
    # decider-proxy validation: first assignee (issue snapshot) vs actual closer
    c = d[(d.state == 'closed') & ~d.closerBot.fillna(False).astype(bool) & d.closer.notna()]
    wa = c[c.firstAssignee.notna()]; TR[f'{tag}_proxy_first_assignee_is_closer'] = wilson(int((wa.firstAssignee == wa.closer).sum()), len(wa))
    TR[f'{tag}_bot_closer_share'] = wilson(int(d[d.state == 'closed'].closerBot.fillna(False).astype(bool).sum()), int((d.state == 'closed').sum()))
    TR[f'{tag}_n_distinct_human_closers'] = int(c.closer.nunique())
P('regime_triple', TR)
json.dump(RES, open('out/results_w2.json', 'w'), indent=1, default=str)
print('WROTE out/results_w2.json')
