# R5 G: period-matched one-year acceptance (Aalen-Johansen CIF) for CIViC and the tracker samples, cohorts 2016+ and 2021+;
# and tracker label timing (was the 'new term request' label added after opening?). Aggregates only.
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261110)
D = lambda s: pd.Timestamp(s, tz='UTC').value / 864e11
def aj(t, cause, causes, horizon=365):
    # t: time to event or censoring; cause: label or None (censored). Returns CIF at horizon per cause.
    o = np.argsort(t); t = np.asarray(t)[o]; c = np.asarray(cause, dtype=object)[o]; n = len(t); S = 1.0; F = {k: 0.0 for k in causes}; i = 0
    while i < n and t[i] <= horizon:
        j = i; d = {k: 0 for k in causes}
        while j < n and t[j] == t[i]:
            if c[j] is not None: d[c[j]] += 1
            j += 1
        at = n - i; dt = sum(d.values())
        for k in causes: F[k] += S * d[k] / at
        S *= 1 - dt / at; i = j
    return F
R = {}
# ---------- CIViC
E = pd.read_pickle('../W3/w3_events_hmac.pkl'); H = E[~E.bot]; END = float(E.t.max())
ei = H[H.tt == 'EvidenceItem']
sub = ei[ei.act == 'SUBMITTED'].sort_values('t').drop_duplicates('tid').set_index('tid')
dec = ei[ei.act.isin(['ACCEPTED', 'REJECTED'])].sort_values('t').drop_duplicates('tid').set_index('tid')
it = pd.DataFrame({'arr': sub.t, 'subU': sub.u}); it['dec'] = dec.t.reindex(it.index); it['act'] = dec.act.reindex(it.index); it['decU'] = dec.u.reindex(it.index)
it['cause'] = np.where(it.dec.isna(), None, np.where(it.act == 'ACCEPTED', 'ACC', np.where(it.decU == it.subU, 'WDR', 'REJ')))
it['T'] = np.where(it.dec.isna(), END - it.arr, np.maximum(it.dec - it.arr, 0))
def civ(df): return aj(df['T'].values, list(df.cause.values), ['ACC', 'REJ', 'WDR'])
for lab, a in (('2016plus', '2016-01-01'), ('2021plus', '2021-01-01'), ('2022-10plus_cohort_window', '2022-10-07')):
    C = it[it.arr >= D(a)]; pt = civ(C); g = {u: x for u, x in C.groupby('subU')}; us = np.array(list(g))
    bs = [civ(pd.concat([g[u] for u in rng.choice(us, len(us))]))['ACC'] for _ in range(1000)]
    R[f'civic_{lab}'] = {'n': len(C), 'CIF365_ACC': [round(pt['ACC'], 3), round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
                         'CIF365_REJ': round(pt['REJ'], 3), 'CIF365_WDR': round(pt['WDR'], 3)}
# ---------- trackers (W2 samples, 200 each; inferred outcomes ACC / REJ / UNCLEAR; INTERIM closures treated as censored? -> as UNCLEAR)
T = pd.read_pickle('../W2/internal/tickets_w2.pkl'); TEND = D('2026-10-07')
T['o'] = pd.to_datetime(T.open, utc=True).map(lambda x: x.value / 864e11)
T['c'] = pd.to_datetime(T.close, utc=True).map(lambda x: x.value / 864e11 if pd.notna(x) else np.nan)
R['tracker_cls_values'] = T.cls.value_counts(dropna=False).to_dict()
T['cause'] = [None if pd.isna(c) else ('ACC' if k == 'ACC' else 'REJ' if k == 'REJ' else 'UNC') for c, k in zip(T.c, T.cls)]
T['Tt'] = np.where(T.c.isna(), TEND - T.o, T.c - T.o)
for tag in ('go', 'hpo'):
    for lab, a in (('2016plus', '2016-01-01'), ('2021plus', '2021-01-01')):
        S = T[(T.tag == tag) & (T.o >= D(a))].reset_index(drop=True); f = lambda df: aj(df.Tt.values, list(df.cause.values), ['ACC', 'REJ', 'UNC'])
        pt = f(S); bs = [f(S.iloc[rng.integers(0, len(S), len(S))])['ACC'] for _ in range(1000)]
        R[f'{tag}_{lab}'] = {'n': len(S), 'CIF365_ACC': [round(pt['ACC'], 3), round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)], 'CIF365_REJ': round(pt['REJ'], 3), 'CIF365_UNC': round(pt['UNC'], 3)}
# ---------- label timing
for tag in ('go', 'hpo'):
    keep = set(T[T.tag == tag].n)
    rows = []
    for l in open(f'../W2/tl_w2_{tag}.jsonl', encoding='utf-8'):
        x = json.loads(l)
        if x['n'] not in keep: continue
        c = pd.Timestamp(x['c']).value / 864e11; xclose = pd.Timestamp(x['x']).value / 864e11 if x.get('x') else None
        labs = [e for e in x['events'] if e.get('ev') == 'labeled' and 'new term' in str(e.get('label', '')).lower()]
        if not labs: rows.append({'has_label_event': False}); continue
        t = min(pd.Timestamp(e['t']).value / 864e11 for e in labs); d = t - c
        rows.append({'has_label_event': True, 'delay_d': d, 'after_open_gt_1h': d > 1 / 24, 'after_open_gt_1d': d > 1, 'at_or_after_close': xclose is not None and t >= xclose - 1 / 1440,
                     'by_submitter': any(e.get('actor') == x.get('sub') for e in labs if pd.Timestamp(e['t']).value / 864e11 == t)})
    df = pd.DataFrame(rows); lab = df[df.has_label_event]; late = lab[lab.after_open_gt_1h]
    R[f'label_timing_{tag}'] = {'tickets': len(df), 'with_label_event': len(lab), 'without_label_event_in_timeline': int((~df.has_label_event).sum()),
        'share_label_after_open_gt_1h': round(float(lab.after_open_gt_1h.mean()), 3), 'share_gt_1d': round(float(lab.after_open_gt_1d.mean()), 3),
        'median_delay_days_if_late': round(float(late.delay_d.median()), 2) if len(late) else None, 'p75_delay_days_if_late': round(float(late.delay_d.quantile(.75)), 2) if len(late) else None,
        'share_label_at_or_after_close': round(float(lab.at_or_after_close.mean()), 3), 'label_by_submitter_share': round(float(lab.by_submitter.mean()), 3)}
json.dump(R, open('res_g_period.json', 'w'), indent=1, default=str); print(json.dumps(R, indent=1, default=str))
