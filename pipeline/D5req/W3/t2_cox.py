# T2: activity -> decision hazards with revisions split by initiator; exposure lag (exclude activity within D days before decision)
# and landmark analyses with a gap; flags/comments -> rejection. Associational only.
import json, sys, numpy as np, pandas as pd
from statsmodels.duration.hazard_regression import PHReg
E = pd.read_pickle('w3_events.pkl'); it = pd.read_pickle('w3_items.pkl')
meta = {m['id']: m for m in json.load(open('../../D5b/meta_evidence.json', encoding='utf-8'))}
NOW = pd.Timestamp('2026-10-07', tz='UTC').value / 864e11
R = {}
def P(k, v): R[k] = v; print(k, json.dumps(v, default=str)[:3000], flush=True)
ei = E[(E.tt == 'EvidenceItem')].copy()
ei = ei[ei.tid.isin(it.index)]
ei = ei.merge(it[['arr', 'dec', 'decU']], left_on='tid', right_index=True)
ei = ei[ei.t >= ei.arr - 1e-6]
ei['rt'] = ei.t - ei.arr
ei['isDecider'] = (ei.u == ei.decU)
cm = ei.act.isin(['COMMENTED', 'REVISION_COMMENTED']); rv = ei.act.eq('REVISION_SUGGESTED'); fl = ei.act.eq('FLAGGED')
H = ~ei.bot; sub = ei.isSubmitter
cls = {
    'rev_submitter': rv & H & sub,
    'rev_moderator': rv & H & ~sub & ei.modAt,
    'rev_moderator_eventual_decider': rv & H & ~sub & ei.modAt & ei.isDecider,
    'rev_moderator_not_decider': rv & H & ~sub & ei.modAt & ~ei.isDecider,
    'rev_other_curator': rv & H & ~sub & ~ei.modAt,
    'rev_bot': rv & ei.bot,
    'com_moderator': cm & H & ~sub & ei.modAt,
    'com_submitter': cm & H & sub,
    'com_other': cm & H & ~sub & ~ei.modAt,
    'flag_human': fl & H,
    'flag_bot': fl & ei.bot,
}
first = {k: ei[m].groupby('tid').rt.min() for k, m in cls.items()}
# submitter revision after a moderator comment (response revision)
mc = first['com_moderator']
sr = ei[cls['rev_submitter']][['tid', 'rt']].copy(); sr['mc'] = sr.tid.map(mc)
first['rev_submitter_after_mod_comment'] = sr[sr.rt > sr.mc].groupby('tid').rt.min()
first['rev_submitter_no_prior_mod_comment'] = sr[~(sr.rt > sr.mc)].groupby('tid').rt.min()
df = it.copy()
df['T'] = np.where(df.dec.isna(), NOW - df.arr, df.dec - df.arr).clip(min=0)
df['ev'] = df.out.map({'PEND': 0, 'ACC': 1, 'REJ': 2, 'WDR': 3})
for k, s in first.items(): df[k] = s.reindex(df.index).fillna(np.inf).values
df['year'] = pd.to_datetime(df.arr * 864e11).dt.year
df['era'] = pd.cut(df.year, [2014, 2016, 2019, 2022, 2027], labels=['2015-16', '2017-19', '2020-22', '2023-26']).astype(str)
df['lvl'] = [meta.get(int(i), {}).get('evidenceLevel') for i in df.index]; df['typ'] = [meta.get(int(i), {}).get('evidenceType') for i in df.index]
df['grp'] = pd.factorize(df.subU)[0]
P('cohort', {'n': len(df), 'events': df.out.value_counts().to_dict(),
             'items_exposed_before_end': {k: int((df[k] < df['T']).sum()) for k in first}})

def cp_data(X, lag):
    rows = []
    for r in df.itertuples():
        on = {x: getattr(r, x) + lag for x in X}
        cuts = sorted({0.0, r.T} | {v for v in on.values() if 0 < v < r.T})
        if len(cuts) == 1: cuts = [0.0, 1e-3]
        for i in range(len(cuts) - 1):
            s0, s1 = cuts[i], max(cuts[i + 1], cuts[i] + 1e-3); last = i == len(cuts) - 2
            rows.append((r.Index, s0, s1, int(last and r.ev == 1), int(last and r.ev == 2), int(last and r.ev == 3), *[int(on[x] <= s0) for x in X], r.lvl, r.typ, r.era, r.grp))
    return pd.DataFrame(rows, columns=['id', 'start', 'stop', 'acc', 'rej', 'wdr', *X, 'lvl', 'typ', 'era', 'grp'])

def cox(cp, X, out, adj=True):
    Z = cp[X].astype(float)
    if adj: Z = pd.concat([Z, pd.get_dummies(cp[['lvl', 'typ']].fillna('NA'), drop_first=True).astype(float)], axis=1)
    Z = Z.loc[:, Z.std() > 0]
    m = PHReg(cp.stop.values, Z.values, status=cp[out].values, entry=cp.start.values, strata=cp.era.values, ties='breslow')
    f = m.fit(method='bfgs', maxiter=2000, disp=0)   # Newton overshoots (large score at 0); BFGS converges
    b = f.params
    # cluster-robust (submitter) sandwich; rows whose interval contains no event time have NaN score residuals in statsmodels -> 0
    sr = np.nan_to_num(m.score_residuals(b)); S = np.zeros((cp.grp.max() + 1, len(b))); np.add.at(S, cp.grp.values, sr)
    Hi = np.linalg.inv(-m.hessian(b)); V = Hi @ (S.T @ S) @ Hi; se = np.sqrt(np.diag(V))
    o = {}
    for i, c in enumerate(Z.columns):
        if c in X:
            nexp = int(cp.loc[cp[c] == 1, out].sum())
            o[c] = [round(float(np.exp(b[i])), 2), round(float(np.exp(b[i] - 1.96 * se[i])), 2), round(float(np.exp(b[i] + 1.96 * se[i])), 2), f'events_exposed={nexp}']
    o['events'] = int(cp[out].sum()); return o

XA = ['rev_submitter', 'rev_moderator', 'rev_other_curator', 'com_moderator', 'com_submitter', 'com_other', 'flag_human']
XB = ['rev_submitter_after_mod_comment', 'rev_submitter_no_prior_mod_comment', 'rev_moderator_eventual_decider', 'rev_moderator_not_decider', 'rev_other_curator', 'com_moderator', 'com_submitter', 'com_other', 'flag_human']
XC = XA + ['rev_bot', 'flag_bot']
for lag in (0, 7, 30):
    for nm, X in (('A_initiator', XA), ('B_response_and_decider', XB), ('C_incl_bot', XC)):
        cp = cp_data(X, lag)
        P(f'tvcox_lag{lag}_{nm}', {out: cox(cp, X, out) for out in ('acc', 'rej', 'wdr')})

# landmark: exposure status fixed at L (activity in [0, L]); risk set = pending at L + gap; follow-up from L + gap (max 2 y)
lm = {}
for gap in (7, 30):
    for L in (30, 90, 180, 365):
        b = df[df['T'] > L + gap].copy()
        T2 = np.minimum(b['T'] - (L + gap), 730.0); ev2 = np.where(b['T'] - (L + gap) <= 730, b.ev, 0)
        for x in XB: b[x] = (b[x] <= L).astype(int)
        b['start'] = 0.0; b['stop'] = np.maximum(T2, 1e-3)
        b['acc'] = (ev2 == 1).astype(int); b['rej'] = (ev2 == 2).astype(int); b['wdr'] = (ev2 == 3).astype(int)
        o = {'n_at_risk': len(b), 'exposed_n': {x: int(b[x].sum()) for x in XB}}
        for out in ('acc', 'rej'):
            try: o[out] = cox(b, [x for x in XB if b[x].sum() >= 5], out)
            except Exception as e: o[out] = f'ERR {e}'
        lm[f'gap{gap}_L{L}'] = o
        print('landmark', gap, L, json.dumps(o)[:1500], flush=True)
R['landmark'] = lm
json.dump(R, open('res_t2_cox.json', 'w'), indent=1, default=str)
