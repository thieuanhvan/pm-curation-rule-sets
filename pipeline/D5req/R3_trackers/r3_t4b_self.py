# R3 task 4 add-on: tracker live-queue u excluding self-closures (closer = submitter), which are newest-first by construction.
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261008); R = {}
for tag in ('go', 'hpo'):
    oc = pd.DataFrame(json.load(open(f'../W2/outcomes_w2_{tag}.json'))); oc = oc[oc.cls.notna() & oc.uAlive365.notna()]
    oc = oc[pd.to_datetime(oc.close, utc=True) >= pd.Timestamp('2021-01-01', tz='UTC')]
    for lab, d in (('all', oc), ('self_closed', oc[oc.closer == oc['sub']]), ('other_closed', oc[oc.closer != oc['sub']])):
        u = d.uAlive365.values.astype(float); bm = [u[rng.integers(0, len(u), len(u))].mean() for _ in range(5000)]
        R[f'{tag}_2021plus_{lab}'] = {'n': int(len(u)), 'meanU': [round(u.mean(), 3), round(np.percentile(bm, 2.5), 3), round(np.percentile(bm, 97.5), 3)], 'newest10': round(float((u <= .1).mean()), 3)}
json.dump(R, open('r3_t4b_self.json', 'w'), indent=1); print(json.dumps(R))
