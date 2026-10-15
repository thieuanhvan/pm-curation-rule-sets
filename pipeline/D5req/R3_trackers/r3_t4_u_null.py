# R3 task 4: permutation null for tracker service position u on the live queue (tickets <= 365 d old; decisions on older
# tickets excluded, corrected definition in ../W2/classify_w2.mjs). Null: the decided ticket is drawn uniformly from the live
# queue at decision time (as for CIViC in ../W3/t3_abandon.py). Ticket bootstrap for observed values. GO vs CIViC same window.
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261007); NS, B = 5000, 5000; R = {}
CIVIC_2021 = {'meanU': [0.152, 0.122, 0.182], 'newest10': [0.659, 0.601, 0.715], 'n': 955, 'null_meanU_95': [0.48, 0.517], 'median_L': 557, 'src': '../W3/res_t3_abandon.json P2_service_position_2021plus/age<=365/all'}
bulk = json.load(open('r3_t3_bursts.json'))
for tag in ('go', 'hpo'):
    oc = pd.DataFrame(json.load(open(f'../W2/outcomes_w2_{tag}.json'))); oc = oc[oc.cls.notna() & oc.uAlive365.notna()].copy()
    oc['closeT'] = pd.to_datetime(oc.close, utc=True)
    for lab, t0 in (('2016plus', '2016-01-01'), ('2021plus', '2021-01-01')):
        d = oc[oc.closeT >= pd.Timestamp(t0, tz='UTC')]; u = d.uAlive365.values.astype(float); L = d.Lalive.values.astype(int)
        k = rng.integers(0, L[:, None], (len(L), NS)); nu = k / (L[:, None] - 1)
        bs = [u[rng.integers(0, len(u), len(u))] for _ in range(B)]
        bm = np.array([b.mean() for b in bs]); b10 = np.array([(b <= .1).mean() for b in bs])
        R[f'{tag}_{lab}'] = {'n': int(len(u)), 'meanU': [round(u.mean(), 3), round(np.percentile(bm, 2.5), 3), round(np.percentile(bm, 97.5), 3)],
            'newest10': [round((u <= .1).mean(), 3), round(np.percentile(b10, 2.5), 3), round(np.percentile(b10, 97.5), 3)],
            'null_meanU_95': [round(np.percentile(nu.mean(0), 2.5), 3), round(np.percentile(nu.mean(0), 97.5), 3)],
            'null_newest10_95': [round(np.percentile((nu <= .1).mean(0), 2.5), 3), round(np.percentile((nu <= .1).mean(0), 97.5), 3)],
            'perm_p_meanU_le_obs': float(((nu.mean(0)) <= u.mean()).mean()), 'median_L': int(np.median(L))}
        if lab == '2021plus' and tag == 'go':
            cb = np.random.default_rng(1).normal(CIVIC_2021['meanU'][0], (CIVIC_2021['meanU'][2] - CIVIC_2021['meanU'][1]) / 3.92, B)
            diff = bm - cb
            R['go_minus_civic_2021plus_meanU'] = [round(u.mean() - CIVIC_2021['meanU'][0], 3), round(np.percentile(diff, 2.5), 3), round(np.percentile(diff, 97.5), 3)]
            R['go_minus_civic_note'] = 'GO ticket bootstrap minus normal approximation of the CIViC cluster-bootstrap interval; positive = GO less newest-first'
R['civic_2021plus_age365'] = CIVIC_2021
json.dump(R, open('r3_t4_u_null.json', 'w'), indent=1); print(json.dumps(R, indent=0))
