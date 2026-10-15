# R3 T6: number reconciliations (CIViC). Aggregates only; organisation-level results only as pooled shares (no organisation named).
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20261011)
E = pd.read_pickle('../W3/w3_events_hmac.pkl'); H = E[~E.bot]
yr = lambda t: pd.to_datetime(t * 864e11).year
D = lambda s: pd.Timestamp(s, tz='UTC').value / 864e11
R = {}
# ---- item counts (12,092 vs 12,091 vs 12,085)
ei_all = set(E[E.tt == 'EvidenceItem'].tid.dropna()); ei_sub = set(E[(E.act == 'SUBMITTED') & (E.st == 'EvidenceItem')].sid)
ei_nonbot = set(H[H.tt == 'EvidenceItem'].tid.dropna())
meta = json.load(open('../../D5b/meta_evidence.json', encoding='utf-8'))
R['item_counts'] = {'evidence_item_ids_in_any_event': len(ei_all), 'with_SUBMITTED_event': len(ei_sub), 'with_any_nonbot_event(case log scope)': len(ei_nonbot),
                    'ids_without_SUBMITTED_event': len(ei_all - ei_sub), 'meta_evidence_records': len(meta),
                    'ids_only_bot_events': len(ei_all - ei_nonbot)}
# ---- items, outcomes
ei = H[H.tt == 'EvidenceItem']
sub = ei[ei.act == 'SUBMITTED'].sort_values('t').drop_duplicates('tid').set_index('tid')
dec = ei[ei.act.isin(['ACCEPTED', 'REJECTED'])].sort_values('t').drop_duplicates('tid').set_index('tid')
it = pd.DataFrame({'arr': sub.t, 'subU': sub.u, 'subOrg': sub.org})
for c in ('t', 'act', 'u', 'org', 'modAt'): it['d_' + c] = dec[c].reindex(it.index)
it['out'] = np.where(it.d_t.isna(), 'PEND', np.where(it.d_act == 'ACCEPTED', 'ACC', np.where(it.d_u == it.subU, 'WDR', 'REJ')))
n = len(it); pend = int((it.out == 'PEND').sum())
R['pending'] = {'pending': pend, 'items': n, 'share': round(pend / n, 4), 'share_of_12092': round(pend / 12092, 4),
                'since_2016_pending_share': round(float((it[it.arr >= D('2016-01-01')].out == 'PEND').mean()), 4)}
# ---- withdrawals: split by whether the submitter-withdrawer had moderated others' content before (moderator-at-time proxy)
w = it[it.out == 'WDR']; rj = it[it.out == 'REJ']
R['withdrawals'] = {'first_decision_rejections_total': int(len(w) + len(rj)), 'by_others': int(len(rj)), 'withdrawals_by_submitter': int(len(w)),
                    'withdrawal_share': round(len(w) / (len(w) + len(rj)), 3),
                    'withdrawals_by_submitter_who_was_moderator_at_time(editor self-rejection)': int(w.d_modAt.fillna(False).sum()),
                    'withdrawals_by_submitter_not_moderator_at_time(curator self-withdrawal)': int((~w.d_modAt.fillna(False).astype(bool)).sum()),
                    'distinct_withdrawers_moderator': int(w[w.d_modAt.fillna(False).astype(bool)].subU.nunique()),
                    'distinct_withdrawers_curator': int(w[~w.d_modAt.fillna(False).astype(bool)].subU.nunique()),
                    'roleNow_of_withdrawers(event rows)': E[(E.act == 'REJECTED') & E.eid.isin(ei[(ei.act == 'REJECTED')].eid)].merge(w[[]], left_on='tid', right_index=True).drop_duplicates('tid').roleNow.value_counts().to_dict()}
# ---- reasons for rejections of other users' evidence items (first decisions), one definition, by period
cm = H[(H.tt == 'EvidenceItem') & H.act.isin(['COMMENTED', 'REVISION_COMMENTED'])][['tid', 't', 'u']]
r = rj.copy(); r['T25'] = r.d_t >= D('2025-03-20')
def has(row, lo, hi):
    c = cm[(cm.tid == row.name) & (cm.u == row.d_u)]; dt = row.d_t - c.t
    return bool(((dt > lo) & (dt <= hi)).any())
r['strict_before_any'] = [has(x, 0, 1e6) for _, x in r.iterrows()]
r['strict_before_1d'] = [has(x, 0, 1) for _, x in r.iterrows()]
r['to_1min_after_any'] = [has(x, -1 / 1440, 1e6) for _, x in r.iterrows()]
r['per'] = pd.cut(r.d_t.map(yr), [2014, 2018, 2022, 2027], labels=['2015-18', '2019-22', '2023-26'])
def sh(df):
    o = {'n': len(df)}
    for k in ('strict_before_any', 'strict_before_1d', 'to_1min_after_any'):
        x = df[k].values.astype(float); bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(2000)] if len(x) else [np.nan]
        o[k] = [round(float(x.mean()), 3), round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)] if len(x) else None
    return o
pre = r[~r.T25]
R['reasons_first_decision_rejections_by_others'] = {'all': sh(r), 'pre_enforcement': sh(pre), 'post_enforcement(comment only; reason field mandatory)': sh(r[r.T25]),
    'pre_by_period': {str(p): sh(g) for p, g in pre.groupby('per')}}
# ---- same-organisation share of acceptances of others' items, by period, with permutation null over organisation composition
a = it[(it.out == 'ACC') & (it.d_u != it.subU)].copy(); a['per'] = pd.cut(a.d_t.map(yr), [2014, 2018, 2022, 2027], labels=['2015-18', '2019-22', '2023-26']).astype(str)
a['year'] = a.d_t.map(yr)
so = {}
for p, g in a.groupby('per'):
    k = g[g.subOrg.notna() & g.d_org.notna()]
    obs = float((k.subOrg == k.d_org).mean()); obs_missing_as_cross = float(((g.subOrg == g.d_org) & g.subOrg.notna()).mean())
    # null 1: permute decider organisation across acceptances within period; null 2: within calendar year
    n1 = [float((k.subOrg.values == rng.permutation(k.d_org.values)).mean()) for _ in range(2000)]
    n2 = []
    for _ in range(2000):
        dd = k.groupby('year').d_org.transform(lambda s: rng.permutation(s.values)); n2.append(float((k.subOrg == dd).mean()))
    so[p] = {'acceptances': len(g), 'with_both_orgs': len(k), 'missing_org_share': round(1 - len(k) / len(g), 3), 'same_org_share': round(obs, 3),
             'same_org_share_missing_as_cross': round(obs_missing_as_cross, 3),
             'null_permute_within_period': [round(float(np.mean(n1)), 3), round(float(np.percentile(n1, 2.5)), 3), round(float(np.percentile(n1, 97.5)), 3)],
             'null_permute_within_year': [round(float(np.mean(n2)), 3), round(float(np.percentile(n2, 2.5)), 3), round(float(np.percentile(n2, 97.5)), 3)],
             'n_decider_orgs': int(k.d_org.nunique()), 'n_submitter_orgs': int(k.subOrg.nunique())}
R['same_org'] = so
# ---- organisation missingness at event time by year (all non-bot events, and acceptances)
H2 = H.assign(y=H.t.map(yr))
R['org_missing_by_year'] = {int(y): {'events': len(g), 'missing_share': round(float(g.org.isna().mean()), 3)} for y, g in H2.groupby('y')}
R['org_first_recorded'] = str(pd.to_datetime(H[H.org.notna()].t.min() * 864e11))
R['org_count_first_seen_by_year'] = H2[H2.org.notna()].groupby('org').y.min().value_counts().sort_index().to_dict()
# ---- bot flags: batch Aug 2021 and the Jan 2023 bot activity
B = E[E.bot].assign(m=lambda d: pd.to_datetime(d.t * 864e11).dt.strftime('%Y-%m'))
fl = B[(B.act == 'FLAGGED')]
R['bot_flags'] = {'by_month_top': fl.m.value_counts().head(6).to_dict(), 'aug2021_by_subject_type': fl[fl.m == '2021-08'].st.value_counts().to_dict(),
                  'bot_actions_2023_01_by_action': B[B.m == '2023-01'].act.value_counts().to_dict(),
                  'bot_actions_2023_01_by_subject_type': B[B.m == '2023-01'].st.value_counts().to_dict(),
                  'bot_actions_by_month_top': B.m.value_counts().head(8).to_dict()}
R['bot_flag_ids_aug2021_sample'] = sorted(rng.choice(fl[fl.m == '2021-08'].oid.dropna().astype(int).unique(), 12, replace=False).tolist())
json.dump(R, open('res_r3_t6.json', 'w'), indent=1, default=str); print(json.dumps(R, indent=1, default=str))
