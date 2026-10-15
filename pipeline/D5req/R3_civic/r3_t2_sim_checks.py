# R3 T2: simulator checks. (a) decomposition of 'unweighted value' across policies; (b) independent max-matching check of the
# EDF 90/365-day bounds (Hopcroft-Karp via scipy) ; (d) resubmission counts; (e) arrival counts. No person-level output.
import json, numpy as np, pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
IT = json.load(open('../A4/items_feat.json'))
NOW = pd.Timestamp('2026-10-07', tz='UTC').value / 864e11; TV = pd.Timestamp('2023-01-01', tz='UTC').value / 864e11
arr = np.array([x['arr'] for x in IT]); dec = np.array([np.nan if x['dec'] is None else x['dec'] for x in IT])
tok = np.sort(dec[~np.isnan(dec) & (dec >= TV)])
R = {'tokens_holdout': int(len(tok)), 'token_item_years_sum': round(float(((NOW - tok) / 365).sum()), 1)}
new = np.sort(arr[(arr >= TV) & (arr <= NOW)])
R['arrivals'] = {'holdout_2023-01-01_to_2026-10-07': int(len(new)), 'calendar_2023_25': int(((new < pd.Timestamp('2026-01-01', tz='UTC').value / 864e11)).sum()),
                 'in_2026': int((new >= pd.Timestamp('2026-01-01', tz='UTC').value / 864e11).sum()), 'final_90d': int((new > NOW - 90).sum()), 'final_365d': int((new > NOW - 365).sum()),
                 'with_90d_followup': int((new <= NOW - 90).sum()), 'with_365d_followup': int((new <= NOW - 365).sum()),
                 'per_month_2026_Jan_Oct': round(float((new >= pd.Timestamp('2026-01-01', tz='UTC').value / 864e11).sum() / (9 + 6 / 31)), 1),
                 'per_month_final_90d': round(float((new > NOW - 90).sum() / (90 / 30.4375)), 1)}
# (b) bound = maximum matching between eligible new arrivals (arr <= NOW-d) and tokens t with arr <= t <= arr + d
for d in (90, 365):
    J = new[new <= NOW - d]; rows, cols = [], []
    for j, a in enumerate(J):
        lo, hi = np.searchsorted(tok, a, 'left'), np.searchsorted(tok, a + d, 'right')
        rows += [j] * (hi - lo); cols += list(range(lo, hi))
    G = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(J), len(tok)))
    m = maximum_bipartite_matching(G, perm_type='column')
    # greedy oldest-feasible-first (EDF with equal relative deadlines) for comparison
    used = 0; ptr = 0; pend = []
    import collections; q = collections.deque(); k = 0
    for t in tok:
        while k < len(J) and J[k] <= t: q.append(J[k]); k += 1
        while q and q[0] + d < t: q.popleft()
        if q: q.popleft(); used += 1
    R[f'bound_{d}d'] = {'eligible': int(len(J)), 'max_matching': int((m >= 0).sum()), 'share_max_matching': round(float((m >= 0).sum() / len(J)), 4),
                        'greedy_EDF_matched': used, 'share_greedy_EDF': round(used / len(J), 4)}
# (a) value decomposition from W4 results (EAimp_value_uniform = accepted item-years before NOW)
O = json.load(open('../W4/results_outcomes.json'))['res']
R['value_uniform_by_policy'] = {p: {'value_item_years': round(o['EAimp_value_uniform'][0], 1), 'token_weighted_EA_share': round(o['EAimp_value_uniform'][0] / R['token_item_years_sum'], 4),
                                    'endPending': o['endPending'][0], 'lostByExpiry': o['lostFinal'][0], 'idleTokens': o['idleTokens'][0], 'resub': o['resub'][0]} for p, o in O.items()}
# withdrawal tokens in the hold-out (from W3 items: decider == submitter)
E = pd.read_pickle('../W3/w3_events_hmac.pkl'); H = E[~E.bot]; ei = H[H.tt == 'EvidenceItem']
sub = ei[ei.act == 'SUBMITTED'].sort_values('t').drop_duplicates('tid').set_index('tid')
dd = ei[ei.act.isin(['ACCEPTED', 'REJECTED'])].sort_values('t').drop_duplicates('tid').set_index('tid')
dd = dd[(dd.t >= TV)]; dd['subU'] = sub.u.reindex(dd.index)
R['holdout_token_types_W3'] = {'accept': int((dd.act == 'ACCEPTED').sum()), 'reject_by_other': int(((dd.act == 'REJECTED') & (dd.u != dd.subU)).sum()),
                               'withdrawal_by_submitter': int(((dd.act == 'REJECTED') & (dd.u == dd.subU)).sum())}
# (d) resubmissions in sensitivity runs
mx = []
for f in ('../W4/results_sens_oat.json', '../W4/results_sens_global.json'):
    for s in json.load(open(f))['scen']:
        for p, rs in s['res'].items():
            for r in rs:
                if r.get('resub'): mx.append((r['resub'], p, s['sc'].get('r')))
mx.sort(reverse=True)
R['resubmissions'] = {'max_events': mx[0][0], 'policy': mx[0][1], 'r': mx[0][2], 'base_r0.25_EXP365_purge': O['EXP365_purge']['resub'][0], 'base_r0.25_EXP365_grandf': O['EXP365_grandf']['resub'][0],
                      'stock_at_risk': 5409 + int(len(new)), 'max_resub_per_item_in_code': 3,
                      'geometric_expectation_purge_r0.75_legacy_only': round(5409 * (0.75 + 0.75 ** 2 + 0.75 ** 3), 0)}
json.dump(R, open('res_r3_t2.json', 'w'), indent=1); print(json.dumps(R, indent=1))
