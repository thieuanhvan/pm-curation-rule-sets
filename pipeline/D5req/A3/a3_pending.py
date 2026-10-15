# (3) Stratify the pending CIViC evidence items: live / dormant / abandoned, by submitter type and evidence level (cells k >= 5).
import os, pickle, json
import numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
d = pickle.load(open(os.path.join(BASE, 'civic_items.pkl'), 'rb')); it = d['items']; NOW = d['NOW']; ud = d['udays']
P = it[it.out == 'PEND'].copy()
def last_in(a, w): a = np.asarray(a, float); return bool(((a > NOW - w) & (a <= NOW)).any())
for w in (90, 365, 730):
    P[f'itemAct{w}'] = [last_in(list(a) + [s0], w) for a, s0 in zip(P.act_t, P.arr)]  # includes the submission itself: newly submitted items are live
    P[f'otherAct{w}'] = [last_in(a, w) for a in P.nonsub_act_t]
    P[f'subAct{w}'] = [last_in(ud.get(u, []), w) for u in P.subU]
P['state'] = np.where(P.itemAct365, 'live', np.where(P.subAct365, 'dormant_item_submitter_active', 'abandoned'))
P['lastItemAct'] = [max(a) if len(a) else np.nan for a in P.act_t]
P['sinceLast'] = NOW - np.fmax(P.lastItemAct.fillna(-1e9), P.arr)
P['volc'] = pd.cut(P.subVol, [0, 1, 9, 99, 1e9], labels=['1', '2-9', '10-99', '100+']).astype(str)
P['burst'] = np.where(P.burstN >= 20, 'burst>=20/day', 'non-burst')
P['firstSub'] = np.where(P.subRank == 1, 'first-time', 'repeat')
P['era'] = pd.cut(pd.to_datetime(P.arr, unit='D').dt.year, [2014, 2016, 2018, 2022, 2026], labels=['2015-16', '2017-18', '2019-22', '2023-26']).astype(str)
def wilson(k, n, z=1.96):
    if n == 0: return [None, None]
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(c - h, 3), round(c + h, 3)]
def tab(col):
    out = {}
    for v, g in P.groupby(col):
        n = len(g)
        if n < 5: out[str(v)] = {'n': '<5 (suppressed)'}; continue
        o = {'n': n, 'nSubmitters': int(g.subU.nunique())}
        if o['nSubmitters'] < 5 and col in ('volc', 'burst', 'subRoleNow'): o['note'] = 'fewer than 5 submitters: aggregate only'
        for s in ['live', 'dormant_item_submitter_active', 'abandoned']:
            k = int((g.state == s).sum()); o[s] = [round(k / n, 3)] + wilson(k, n)
        o['otherEditorTouchedEver'] = round(float(np.mean([len(a) > 0 for a in g.nonsub_act_t])), 3)
        out[str(v)] = o
    return out
R = {'n_pending': len(P)}
R['overall'] = tab(lambda i: 'all')
for w in (90, 365, 730):
    R[f'share_itemActivity_last{w}d'] = [round(P[f'itemAct{w}'].mean(), 3)] + wilson(int(P[f'itemAct{w}'].sum()), len(P))
    R[f'share_nonSubmitterActivity_last{w}d'] = [round(P[f'otherAct{w}'].mean(), 3)] + wilson(int(P[f'otherAct{w}'].sum()), len(P))
    R[f'share_submitterActive_last{w}d'] = [round(P[f'subAct{w}'].mean(), 3)] + wilson(int(P[f'subAct{w}'].sum()), len(P))
R['yearsSinceLastItemActivity_quartiles'] = [round(x / 365.25, 2) for x in np.percentile(P.sinceLast, [25, 50, 75])]
for col in ['level', 'etype', 'rating', 'volc', 'burst', 'firstSub', 'subRoleNow', 'era']:
    R['by_' + col] = tab(col)
# concentration of pending among submitters (aggregated)
c = P.subU.value_counts()
R['pending_by_top_submitters'] = {'submitters': int(len(c)), 'top1share': round(c.iloc[0] / len(P), 3), 'top5share': round(c.iloc[:5].sum() / len(P), 3), 'top10share': round(c.iloc[:10].sum() / len(P), 3)}
# level x state cross-tab (k>=5)
ct = pd.crosstab(P.level, P.state); R['level_x_state'] = {k: {kk: (int(vv) if vv >= 5 else '<5') for kk, vv in v.items()} for k, v in ct.to_dict('index').items()}
ct = pd.crosstab(P.volc, P.state); R['volume_x_state'] = {k: {kk: (int(vv) if vv >= 5 else '<5') for kk, vv in v.items()} for k, v in ct.to_dict('index').items()}
P[['id', 'state', 'itemAct365', 'subAct365', 'level', 'volc', 'burst', 'era']].to_csv(os.path.join(BASE, 'pending_states.csv'), index=False)
json.dump(R, open(os.path.join(BASE, 'res_a3_pending.json'), 'w'), indent=1)
print(json.dumps(R, indent=0)[:6000])
# submitter-cluster bootstrap CIs (items are clustered: few bulk submitters hold most pending items)
rng = np.random.default_rng(7); subs = P.subU.unique(); grp = {u: g for u, g in P.groupby('subU')}
def cb(mask_fn, B=1000):
    vals = []
    for _ in range(B):
        s = rng.choice(subs, len(subs)); k = sum(int(mask_fn(grp[u]).sum()) for u in s); n = sum(len(grp[u]) for u in s); vals.append(k / n)
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]
R['clusterBootCI_overall'] = {s: cb(lambda g, s=s: (g.state == s)) for s in ['live', 'dormant_item_submitter_active', 'abandoned']}
json.dump(R, open(os.path.join(BASE, 'res_a3_pending.json'), 'w'), indent=1)
print('cluster CI', R['clusterBootCI_overall'])
