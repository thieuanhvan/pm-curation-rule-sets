# Single and double change-point fits (fixed k) with block-bootstrap CIs, on saved CIViC tokens.
import os, pickle, json, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'a4_discipline.py'), encoding='utf-8').read()
exec(src.split("R = {}")[0])
toks = pickle.load(open(os.path.join(BASE, 'civic_tokens.pkl'), 'rb'))
def cpk(tk, k, B=500):
    df = pd.DataFrame([dict(m=pd.Timestamp(x['t'] * 864e11).to_period('M'), u=x['u']) for x in tk if not np.isnan(x['u'])])
    g = df.groupby('m').u.agg(['mean', 'count']); y, w = g['mean'].values, g['count'].values.astype(float); months = [str(p) for p in g.index]
    cps = segfit(y, w, k)[k][1]; edges = [0] + cps + [len(y)]; fitted = np.zeros(len(y)); segs = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (w[a:b] * y[a:b]).sum() / w[a:b].sum(); fitted[a:b] = m; segs.append((months[a], months[b - 1], round(float(m), 3), int(w[a:b].sum())))
    res = y - fitted; bl = 12; bc = []; bm = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, s + bl) % len(y) for s in rng.integers(0, len(y), len(y) // bl + 1)])[:len(y)]
        yb = fitted + res[idx] * np.sqrt(w[idx] / w); c = segfit(yb, w, k)[k][1]; bc.append(c)
        e2 = [0] + c + [len(y)]; bm.append([(w[a:b] * yb[a:b]).sum() / w[a:b].sum() for a, b in zip(e2[:-1], e2[1:])])
    bc = np.array(bc); bm = np.array(bm)
    return {'changepoints': [{'cp': months[cps[i]], 'ci95': [months[int(np.percentile(bc[:, i], 2.5))], months[min(int(np.percentile(bc[:, i], 97.5)), len(months) - 1)]]} for i in range(k)],
            'segments': segs, 'segment_mean_ci95': [[round(float(np.percentile(bm[:, j], 2.5)), 3), round(float(np.percentile(bm[:, j], 97.5)), 3)] for j in range(k + 1)]}
R = {}
for k in (1, 2):
    R[f'civic_all_k{k}'] = cpk(toks, k)
    R[f'civic_crossOrg_nonWDR_k{k}'] = cpk([x for x in toks if x['out'] != 'WDR' and x['sameOrg'] is not None and not x['sameOrg']], k)
    R[f'civic_sameOrg_k{k}'] = cpk([x for x in toks if x['sameOrg'] is not None and x['sameOrg']], k)
for k, v in R.items(): print(k, json.dumps(v))
json.dump(R, open(os.path.join(BASE, 'res_a4b_cp_fixedk.json'), 'w'), indent=1)
