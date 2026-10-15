# R6 task 6: Melitz-Polanec decomposition of evidence-decision intensity on the common activity set A* (main denominator),
# replacing the all-activities decomposition reported before. Same construction as ../R5/d_intensity.py (panel on A*) and
# ../R3_civic/r3_t3_effort.py (decomp, moderator bootstrap). Aggregates only; group sizes reported as bands.
import os, json, numpy as np, pandas as pd
H0 = os.path.dirname(os.path.abspath(__file__)); W3 = os.path.join(H0, '..', 'W3', 'w3_events_hmac.pkl')
rng = np.random.default_rng(20261010)
E = pd.read_pickle(W3); H = E[~E.bot].copy(); H['day'] = np.floor(H.t).astype(int)
V2 = pd.Timestamp('2022-04-09', tz='UTC').value / 864e11
cnt = H.groupby(['act', H.t >= V2]).size().unstack(fill_value=0)
COMMON = sorted(set(cnt.index[(cnt[False] > 0) & (cnt[True] > 0)]) - {'COMPLEX_MOLECULAR_PROFILE_CREATED'})
mod = H[H.modAt].copy()
mod['ev'] = (mod.act.isin(['ACCEPTED', 'REJECTED']) & (mod.st == 'EvidenceItem') & (mod.u != mod.evSub)).astype(int)
def panel(types):
    m = mod if types is None else mod[mod.act.isin(types)]
    D = m.groupby(['u', 'day'])[['ev']].sum().reset_index()
    D['year'] = pd.to_datetime(D.day * 864e11).dt.year; D = D[D.year >= 2016].copy()
    D['period'] = pd.cut(D.year, [2015, 2018, 2022, 2027], labels=['2016-18', '2019-22', '2023-26']).astype(str); return D
def decomp(g0, g1, y='ev'):
    a0 = g0.groupby('u').agg(d=(y, 'size'), e=(y, 'sum')); a1 = g1.groupby('u').agg(d=(y, 'size'), e=(y, 'sum'))
    w0 = a0.d / a0.d.sum(); w1 = a1.d / a1.d.sum(); r0 = a0.e / a0.d; r1 = a1.e / a1.d
    R0 = float((w0 * r0).sum()); R1 = float((w1 * r1).sum())
    st = a0.index.intersection(a1.index); en = a1.index.difference(a0.index); ex = a0.index.difference(a1.index)
    sS0 = w0[st].sum(); sS1 = w1[st].sum(); RS0 = float((w0[st] * r0[st]).sum() / sS0); RS1 = float((w1[st] * r1[st]).sum() / sS1)
    sE = w1[en].sum(); sX = w0[ex].sum(); RE = float((w1[en] * r1[en]).sum() / sE) if sE else RS1; RX = float((w0[ex] * r0[ex]).sum() / sX) if sX else RS0
    return {'R0': R0, 'R1': R1, 'delta': R1 - R0, 'stayers': RS1 - RS0, 'turnover': float(sE * (RE - RS1)) + float(sX * (RS0 - RX)), 'n_stay': len(st)}
out = {}
for tag, ty in (('A_star_main', COMMON), ('all_activities_previous', None)):
    D = panel(ty); g0, g1 = D[D.period == '2016-18'], D[D.period == '2023-26']
    pt = decomp(g0, g1)
    us = np.array(sorted(set(g0.u) | set(g1.u))); G0 = {u: x for u, x in g0.groupby('u')}; G1 = {u: x for u, x in g1.groupby('u')}; bs = []
    for _ in range(2000):
        s = rng.choice(us, len(us)); a, b = [], []
        for k, u in enumerate(s):
            if u in G0: a.append(G0[u].assign(u=f'{u}#{k}'))
            if u in G1: b.append(G1[u].assign(u=f'{u}#{k}'))
        if a and b:
            o = decomp(pd.concat(a), pd.concat(b))
            if o['n_stay'] > 0: bs.append(o)
    ci = lambda k: [round(float(np.percentile([b[k] for b in bs], 2.5)), 2), round(float(np.percentile([b[k] for b in bs], 97.5)), 2)]
    out[tag] = {'intensity_2016_18': round(pt['R0'], 3), 'intensity_2023_26': round(pt['R1'], 3), 'fold': round(pt['R0'] / pt['R1'], 3),
                'delta': [round(pt['delta'], 2)] + ci('delta'), 'stayers': [round(pt['stayers'], 2)] + ci('stayers'), 'turnover': [round(pt['turnover'], 2)] + ci('turnover'),
                'stayers_band': '>=5' if pt['n_stay'] >= 5 else '<5'}
    print(tag, out[tag], flush=True)
json.dump(out, open(os.path.join(H0, 'res_t6_decomp.json'), 'w'), indent=1)
