# R6 task 5: 2025 reason-for-rejection requirement (evidence items, T0 = 2025-04) against revisions on evidence items.
# Raw pooled shares before/after, quarterly pre-trend data, intake falsification, and randomisation (in-time permutation)
# bands over all admissible break dates instead of Newey-West. Input: ../R3_causal/panel.pkl (aggregate monthly panel).
# Also reports the same raw numbers for the 2022 revision requirement (T0 = 2022-05, 2022-04 dropped).
import os, json, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
PN = pd.read_pickle(os.path.join(H, '..', 'R3_causal', 'panel.pkl'))
MINSIDE = 6  # placebo break dates need >= 6 months on each side inside the window

def pooled(P, a, b, num, den):
    s = P.loc[a:b]; n = float(s[den].sum()); k = float(s[num].sum())
    return {'k': int(k), 'n': int(n), 'share': round(k / n, 4) if n else None}

def did(T, C, T0, num, den):
    pre_end = (pd.Period(T0, 'M') - 1)
    tp = pooled(T, T.index[0], pre_end, num, den); tq = pooled(T, pd.Period(T0, 'M'), T.index[-1], num, den)
    cp = pooled(C, C.index[0], pre_end, num, den); cq = pooled(C, pd.Period(T0, 'M'), C.index[-1], num, den)
    if None in (tp['share'], tq['share'], cp['share'], cq['share']): return None, (tp, tq, cp, cq)
    return (tq['share'] - tp['share']) - (cq['share'] - cp['share']), (tp, tq, cp, cq)

def window(key, win, drop):
    s = PN[key].loc[win[0]:win[1]]
    return s.drop([pd.Period(d, 'M') for d in drop if pd.Period(d, 'M') in s.index])

def analyse(name, treated, control, T0, win, drop, outcomes):
    T, C = window(treated, win, drop), window(control, win, drop)
    res = {'treated': treated, 'control': control, 'T0': T0, 'window': win, 'dropped': drop, 'outcomes': {}}
    idx = T.index
    cands = [p for k, p in enumerate(idx) if k >= MINSIDE and len(idx) - k >= MINSIDE]
    for lab, num, den in outcomes:
        est, parts = did(T, C, T0, num, den)
        perm = []
        for p in cands:
            e, _ = did(T, C, str(p), num, den)
            if e is not None: perm.append(e)
        perm = np.array(perm)
        res['outcomes'][lab] = {
            'treated_pre': parts[0], 'treated_post': parts[1], 'control_pre': parts[2], 'control_post': parts[3],
            'did_raw': round(est, 4) if est is not None else None,
            'randomisation_band_95': [round(float(np.percentile(perm, 2.5)), 4), round(float(np.percentile(perm, 97.5)), 4)],
            'randomisation_p_two_sided': round(float((np.abs(perm) >= abs(est) - 1e-12).mean()), 3) if est is not None else None,
            'n_break_dates': int(len(perm))}
    # quarterly pre-trend data (rejection share and arrivals), relative quarter to T0
    q = []
    t0 = pd.Period(T0, 'M')
    for key, S in (('treated', T), ('control', C)):
        rel = np.array([(p - t0).n for p in S.index]); qb = np.floor(rel / 3).astype(int)
        g = pd.DataFrame({'qb': qb, 'rej': S.rej.values, 'n': S.n_other_dec.values, 'wd': S.wd.values, 'nt': S.n_term.values, 'arr': S.arr.values})
        for b, x in g.groupby('qb'):
            q.append({'series': key, 'rel_q': int(b), 'rej': int(x.rej.sum()), 'n_other_dec': int(x.n.sum()),
                      'rej_share': round(x.rej.sum() / x.n.sum(), 4) if x.n.sum() else None,
                      'arrivals_per_month': round(float(x.arr.mean()), 2), 'months': int(len(x))})
    res['quarterly'] = q
    # quarterly treated-minus-control difference relative to bin -1, with randomisation band over placebo break dates
    def qdiff(T0x):
        t0x = pd.Period(T0x, 'M'); out = {}
        rel = np.array([(p - t0x).n for p in idx]); qb = np.floor(rel / 3).astype(int)
        for b in sorted(set(qb)):
            m = qb == b; tn, cn = T.n_other_dec.values[m].sum(), C.n_other_dec.values[m].sum()
            if tn and cn: out[int(b)] = T.rej.values[m].sum() / tn - C.rej.values[m].sum() / cn
        if -1 in out: out = {b: v - out[-1] for b, v in out.items()}
        return out
    obs = qdiff(T0); pl = [qdiff(str(p)) for p in cands]
    res['event_study_quarters'] = [{'rel_q': b, 'diff_vs_ref': round(v, 4),
                                    'band_95': [round(float(np.percentile([d[b] for d in pl if b in d], 2.5)), 4), round(float(np.percentile([d[b] for d in pl if b in d], 97.5)), 4)] if sum(1 for d in pl if b in d) >= 10 else None}
                                   for b, v in sorted(obs.items())]
    return res

OUT = {}
OUTC = [('rejection_share_other_users', 'rej', 'n_other_dec'), ('withdrawal_share_terminal', 'wd', 'n_term')]
OUT['E2025'] = analyse('E2025', 'EID', 'REV', '2025-04', ('2023-09', '2026-09'), [], OUTC)
OUT['E2025_control_revisions_on_evidence_items'] = {k: v for k, v in analyse('E2025b', 'EID', 'REV_EID', '2025-04', ('2023-09', '2026-09'), [], OUTC).items() if k == 'outcomes'}
OUT['E2022'] = {k: v for k, v in analyse('E2022', 'REV', 'EID', '2022-05', ('2019-02', '2024-12'), ['2022-04'], OUTC).items() if k in ('outcomes',)}
# intake falsification 2025: arrivals per month treated and control, pre/post, and log-ratio change with randomisation band
def intake(T, C, T0):
    t0 = pd.Period(T0, 'M'); pre = T.index < t0
    lr = np.log(T.arr + 0.5) - np.log(C.arr + 0.5)
    return float(lr[~pre].mean() - lr[pre].mean()), {'treated_pre': round(float(T.arr[pre].mean()), 2), 'treated_post': round(float(T.arr[~pre].mean()), 2),
                                                     'control_pre': round(float(C.arr[pre].mean()), 2), 'control_post': round(float(C.arr[~pre].mean()), 2)}
T, C = window('EID', ('2023-09', '2026-09'), []), window('REV', ('2023-09', '2026-09'), [])
e, m = intake(T, C, '2025-04')
idx = T.index; cands = [p for k, p in enumerate(idx) if k >= MINSIDE and len(idx) - k >= MINSIDE]
pe = np.array([intake(T, C, str(p))[0] for p in cands])
OUT['E2025_intake_falsification'] = {'arrivals_per_month': m, 'did_log_ratio': round(e, 3), 'randomisation_band_95': [round(float(np.percentile(pe, 2.5)), 3), round(float(np.percentile(pe, 97.5)), 3)],
                                     'randomisation_p_two_sided': round(float((np.abs(pe) >= abs(e)).mean()), 3), 'monthly': [{'m': str(p), 'eid': int(T.arr[p]), 'control_revisions': int(C.arr[p])} for p in idx]}
OUT['notes'] = 'Pooled raw shares = sum(numerator)/sum(denominator) over months. Randomisation: same statistic at every break date with >= 6 months each side; p = share with |placebo| >= |observed|. No Newey-West.'
json.dump(OUT, open(os.path.join(H, 'res_t5.json'), 'w'), indent=1)
print(json.dumps({k: (v['outcomes'] if 'outcomes' in v else v) for k, v in OUT.items() if k != 'notes'}, indent=1)[:5000])
