# W7 T2: is the moderator-comment -> rejection association mechanical? (built from ../W3/t2_cox.py)
# T2: activity -> decision hazards with revisions split by initiator; exposure lag (exclude activity within D days before decision)
# and landmark analyses with a gap; flags/comments -> rejection. Associational only.
import json, sys, numpy as np, pandas as pd
from statsmodels.duration.hazard_regression import PHReg
E = pd.read_pickle('../W3/w3_events.pkl'); it = pd.read_pickle('../W3/w3_items.pkl')
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
    'com_moderator_decider': cm & H & ~sub & ei.modAt & ei.isDecider,
    'com_moderator_not_decider': cm & H & ~sub & ei.modAt & ~ei.isDecider,
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


# ---- (a) descriptive: rejections of others' items preceded by a comment of the same moderator on the same item
rejs = df[df.ev == 2]
cmt = ei[cm & H].copy()
def share_pre(win_lo, win_hi, who):
    n = 0; k = 0
    for i, r in rejs.iterrows():
        c = cmt[cmt.tid == i]
        if who == 'decider': c = c[c.u == r.decU]
        elif who == 'other_moderator': c = c[(c.u != r.decU) & c.modAt & ~c.isSubmitter]
        dt = r['T'] - c.rt  # days before decision (positive = before)
        n += 1; k += int(((dt >= win_lo) & (dt <= win_hi)).any())
    return k, n
def boot_share(flags, B=2000):
    flags = np.asarray(flags); rng = np.random.default_rng(7)
    return [round(float(np.percentile([flags[rng.integers(0, len(flags), len(flags))].mean() for _ in range(B)], q)), 3) for q in (2.5, 97.5)]
desc = {}
rid = list(rejs.index)
for nm, lo, hi, who in [('decider_comment_0to1d_before', 0, 1, 'decider'), ('decider_comment_strictly_before_0to1d', 1e-9, 1, 'decider'),
                         ('decider_comment_within_1min_after_to_1d_before', -1/1440, 1, 'decider'), ('decider_comment_0to7d_before', 0, 7, 'decider'),
                         ('decider_comment_0to30d_before', 0, 30, 'decider'), ('decider_comment_more_than_30d_before', 30 + 1e-9, 1e6, 'decider'),
                         ('decider_comment_any_time_before', 0, 1e6, 'decider'), ('other_moderator_comment_0to1d_before', 0, 1, 'other_moderator'),
                         ('other_moderator_comment_more_than_7d_before', 7 + 1e-9, 1e6, 'other_moderator')]:
    fl = []
    for i in rid:
        r = rejs.loc[i]; c = cmt[cmt.tid == i]
        c = c[c.u == r.decU] if who == 'decider' else c[(c.u != r.decU) & c.modAt & ~c.isSubmitter]
        dt = r['T'] - c.rt; fl.append(int(((dt >= lo) & (dt <= hi)).any()))
    desc[nm] = {'k': int(sum(fl)), 'n': len(fl), 'share': round(float(np.mean(fl)), 3), 'CI': boot_share(fl)}
# by era (pre/post March 2025 mandatory reason)
T25 = pd.Timestamp('2025-03-20', tz='UTC').value / 864e11
for nm, m in [('pre_2025-03-20', rejs.arr + rejs['T'] < T25), ('post_2025-03-20', rejs.arr + rejs['T'] >= T25)]:
    fl = []
    for i in rejs[m].index:
        r = rejs.loc[i]; c = cmt[(cmt.tid == i) & (cmt.u == r.decU)]; dt = r['T'] - c.rt; fl.append(int(((dt >= 0) & (dt <= 1)).any()))
    desc['decider_comment_0to1d_before_' + nm] = {'k': int(sum(fl)), 'n': len(fl), 'share': round(float(np.mean(fl)), 3) if fl else None}
P('rejections_with_comment', desc)

# ---- (b) Cox with moderator comments split by eventual decider; and with all decider comments removed
XS = ['rev_submitter', 'rev_moderator', 'rev_other_curator', 'com_moderator_decider', 'com_moderator_not_decider', 'com_submitter', 'com_other', 'flag_human']
XN = ['rev_submitter', 'rev_moderator', 'rev_other_curator', 'com_moderator_not_decider', 'com_submitter', 'com_other', 'flag_human']
for lag in (0, 7, 30):
    for nm, X in (('split_decider', XS), ('excl_decider_comments', XN)):
        cp = cp_data(X, lag)
        P(f'tvcox_lag{lag}_{nm}', {out: cox(cp, X, out) for out in ('rej', 'acc')})
# landmark with gap, excluding decider comments
lm = {}
XB2 = ['rev_submitter', 'rev_moderator', 'rev_other_curator', 'com_moderator_not_decider', 'com_moderator_decider', 'com_submitter', 'com_other', 'flag_human']
for gap in (7, 30):
    for L in (90, 180, 365):
        b = df[df['T'] > L + gap].copy()
        T2 = np.minimum(b['T'] - (L + gap), 730.0); ev2 = np.where(b['T'] - (L + gap) <= 730, b.ev, 0)
        for x in XB2: b[x] = (b[x] <= L).astype(int)
        b['start'] = 0.0; b['stop'] = np.maximum(T2, 1e-3); b['rej'] = (ev2 == 2).astype(int); b['acc'] = (ev2 == 1).astype(int)
        try: lm[f'gap{gap}_L{L}'] = {'n_at_risk': len(b), 'rej': cox(b, [x for x in XB2 if b[x].sum() >= 5], 'rej')}
        except Exception as e: lm[f'gap{gap}_L{L}'] = f'ERR {e}'
        print('landmark', gap, L, json.dumps(lm[f'gap{gap}_L{L}'])[:800], flush=True)
R['landmark_split'] = lm
json.dump(R, open('res_w7_t2_comment_rejection.json', 'w'), indent=1, default=str)
