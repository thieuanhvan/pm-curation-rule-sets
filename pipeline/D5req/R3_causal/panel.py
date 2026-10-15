# R3_causal: monthly aggregate panel per object type (EID, REV) from objs.pkl. Aggregates only.
import os, numpy as np, pandas as pd
B = os.path.dirname(os.path.abspath(__file__))
o = pd.read_pickle(os.path.join(B, 'objs.pkl'))
M = pd.period_range('2015-07', '2026-09', freq='M')
md = o['md'].assign(m=o['md'].d.dt.to_period('M'))
mdays = md.groupby('m').size().reindex(M, fill_value=0)
nmods = md.groupby('m').u.nunique().reindex(M, fill_value=0)

def build(dec, arr, typ, id_col):
    dec = dec.assign(m=dec.t.dt.to_period('M'))
    first = dec.sort_values('t').drop_duplicates(id_col)
    g = dec.groupby('m')
    P = pd.DataFrame(index=M)
    for k in ['acc', 'rej', 'wd', 'sup']:
        P[k] = dec[dec.kind == k].groupby('m').size().reindex(M, fill_value=0)
    P['acc_other'] = dec[(dec.kind == 'acc') & (~dec.self)].groupby('m').size().reindex(M, fill_value=0)
    P['n_other_dec'] = P.acc_other + P.rej
    P['rej_share'] = P.rej / P.n_other_dec.replace(0, np.nan)
    P['n_term'] = P.acc + P.rej + P.wd + P.sup
    P['wd_share'] = P.wd / P.n_term.replace(0, np.nan)
    P['sup_share'] = P.sup / P.n_term.replace(0, np.nan)
    P['wdsup_share'] = (P.wd + P.sup) / P.n_term.replace(0, np.nan)
    P['ttd_med'] = first.groupby('m').ttd.median().reindex(M)
    P['log_ttd'] = np.log1p(P.ttd_med)
    a = arr.assign(m=arr.t.dt.to_period('M')).groupby('m').size().reindex(M, fill_value=0)
    P['arr'] = a
    ex = first.groupby('m').size().reindex(M, fill_value=0)
    P['stock'] = (a - ex).cumsum()
    P['stock_growth'] = (a - ex) / P.stock.shift(1).clip(lower=1) * 100  # % per month
    rj = dec[dec.kind == 'rej']
    P['rej_note_med'] = rj.groupby('m').note_len.median().reindex(M)
    P['rej_reason_any'] = rj.assign(x=(rj.note_len >= 10) | rj.cm_before).groupby('m').x.mean().reindex(M)
    P['rej_nontempl'] = rj.assign(x=(rj.note_len >= 10) & ~rj.note_templ).groupby('m').x.mean().reindex(M)
    P['mdays'] = mdays; P['nmods'] = nmods; P['type'] = typ
    P['rej_per_md'] = P.rej / P.mdays.replace(0, np.nan)
    P['acc_per_md'] = P.acc_other / P.mdays.replace(0, np.nan)
    P['log_arr'] = np.log1p(P.arr)
    return P

E = build(o['dec'], o['sub'], 'EID', 'sid')
R = build(o['rdec'], o['rsug'], 'REV', 'oid')
# sensitivity: revisions whose subject is an evidence item
re = o['rdec'][o['rdec'].subj_eid]; rs = o['rsug'][o['rsug'].st == 'EvidenceItem']
RE = build(re, rs, 'REV_EID', 'oid')
pd.to_pickle({'EID': E, 'REV': R, 'REV_EID': RE}, os.path.join(B, 'panel.pkl'))
with pd.option_context('display.width', 250, 'display.max_columns', 40):
    for nm, P in (('EID', E), ('REV', R)):
        y = P.groupby(P.index.year)[['acc', 'rej', 'wd', 'sup', 'arr', 'mdays']].sum()
        print(nm); print(y)
    print('moderators per month min (2016-2026):', nmods['2016-01':].min())
