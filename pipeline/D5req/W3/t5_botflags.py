# T5: are bot flags auto-closed or superseded by later bot actions? recompute the "hidden queue" of open flags.
import json, collections as C, numpy as np, pandas as pd
E = pd.read_pickle('w3_events.pkl')
meta = {m['id']: m for m in json.load(open('../../D5b/meta_evidence.json', encoding='utf-8'))}
NOW = pd.Timestamp('2026-10-07', tz='UTC').value / 864e11
R = {}
def P(k, v): R[k] = v; print(k, json.dumps(v, default=str)[:2500], flush=True)
def wilson(k, n, z=1.96):
    if n == 0: return [None, None, None, 0]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 3), round(c - h, 3), round(c + h, 3), n]
F = E[(E.ot == 'Flag') & E.act.isin(['FLAGGED', 'FLAG_RESOLVED'])]
raised = F[F.act == 'FLAGGED'].drop_duplicates('oid').set_index('oid')
res = F[F.act == 'FLAG_RESOLVED'].sort_values('t').drop_duplicates('oid').set_index('oid')
fl = pd.DataFrame({'t': raised.t, 'bot': raised.bot, 'st': raised.st, 'sid': raised.sid})
fl['res_t'] = res.t.reindex(fl.index); fl['res_bot'] = res.bot.reindex(fl.index)
fl['resolved'] = fl.res_t.notna()
# later actions by the bot / anyone on the same entity
ent = E.groupby(['st', 'sid'])
bot_ev = E[E.bot].groupby(['st', 'sid'])
def later(row, df_groups, acts):
    try: g = df_groups.get_group((row.st, row.sid))
    except KeyError: return False
    return bool(((g.t > row.t) & g.act.isin(acts)).any())
fl['later_bot_flag_same_entity'] = [later(r, bot_ev, ['FLAGGED']) for r in fl.itertuples()]
fl['later_bot_revision_same_entity'] = [later(r, bot_ev, ['REVISION_SUGGESTED']) for r in fl.itertuples()]
fl['later_bot_rev_rejected_or_deprecated'] = [later(r, bot_ev, ['REVISION_REJECTED', 'DEPRECATED_VARIANT', 'DEPRECATED_MOLECULAR_PROFILE', 'DEPRECATED_FEATURE']) for r in fl.itertuples()]
# entity-level outcomes for evidence
def evstate(r):
    if r.st != 'EvidenceItem': return None, None
    m = meta.get(int(r.sid), {}); return m.get('status'), m.get('flagged')
st = [evstate(r) for r in fl.itertuples()]
fl['ev_status_now'] = [s[0] for s in st]; fl['ev_flagged_now'] = [s[1] for s in st]
# decision on the evidence item after the flag (accepted / rejected)
ei = E[(E.st == 'EvidenceItem') & E.act.isin(['ACCEPTED', 'REJECTED'])].groupby('sid')
def dec_after(r):
    if r.st != 'EvidenceItem': return None
    try: g = ei.get_group(r.sid)
    except KeyError: return None
    g = g[g.t > r.t]; return None if g.empty else g.sort_values('t').act.iloc[0]
fl['decision_after_flag'] = [dec_after(r) for r in fl.itertuples()]
fl['ym'] = pd.to_datetime(fl.t * 864e11).dt.to_period('M').astype(str)
P('flags_total', {'flags': len(fl), 'bot': int(fl.bot.sum()), 'human': int((~fl.bot).sum()), 'bot_by_entity': fl[fl.bot].st.value_counts().to_dict(),
                  'bot_flags_top_months': fl[fl.bot].ym.value_counts().head(6).to_dict()})
out = {}
for who, g in (('bot', fl[fl.bot]), ('human', fl[~fl.bot])):
    o = {'n': len(g), 'resolved_logged': wilson(int(g.resolved.sum()), len(g)),
         'resolved_by_bot': int((g.resolved & (g.res_bot == True)).sum()), 'resolved_by_human': int((g.resolved & (g.res_bot == False)).sum()),
         'median_days_to_resolution': round(float((g.res_t - g.t).median()), 1) if g.resolved.any() else None,
         'later_bot_flag_same_entity': int(g.later_bot_flag_same_entity.sum()), 'later_bot_revision_same_entity': int(g.later_bot_revision_same_entity.sum()),
         'later_bot_revreject_or_deprecation_same_entity': int(g.later_bot_rev_rejected_or_deprecated.sum())}
    ge = g[g.st == 'EvidenceItem']
    o['evidence'] = {'n': len(ge), 'status_now': ge.ev_status_now.value_counts().to_dict(), 'flagged_now_true': int((ge.ev_flagged_now == True).sum()),
                     'unresolved_but_entity_not_flagged_now(silent closure)': int(((~ge.resolved) & (ge.ev_flagged_now == False)).sum()),
                     'decision_after_flag': ge.decision_after_flag.value_counts(dropna=False).to_dict()}
    out[who] = o
P('by_raiser', out)
# hidden queue: open flags = no FLAG_RESOLVED; for evidence also cross-check against current 'flagged' attribute
b = fl[fl.bot]; h = fl[~fl.bot]
def hq(g):
    o = {'open_by_log': int((~g.resolved).sum())}
    ge = g[g.st == 'EvidenceItem']; gn = g[g.st != 'EvidenceItem']
    o['evidence_open_by_log'] = int((~ge.resolved).sum())
    o['evidence_open_by_log_AND_flagged_now'] = int(((~ge.resolved) & (ge.ev_flagged_now == True)).sum())
    o['evidence_open_by_log_AND_flagged_now_AND_not_rejected'] = int(((~ge.resolved) & (ge.ev_flagged_now == True) & (ge.ev_status_now != 'REJECTED')).sum())
    o['  of which accepted items'] = int(((~ge.resolved) & (ge.ev_flagged_now == True) & (ge.ev_status_now == 'ACCEPTED')).sum())
    o['  of which submitted items'] = int(((~ge.resolved) & (ge.ev_flagged_now == True) & (ge.ev_status_now == 'SUBMITTED')).sum())
    o['distinct_evidence_items_open_flagged_now'] = int(ge[(~ge.resolved) & (ge.ev_flagged_now == True)].sid.nunique())
    o['non_evidence_open_by_log'] = int((~gn.resolved).sum())
    o['open_flags_age_years_quartiles'] = [round(x / 365.25, 2) for x in np.percentile(NOW - g[~g.resolved].t, [25, 50, 75])] if (~g.resolved).any() else None
    return o
P('hidden_queue', {'bot': hq(b), 'human': hq(h), 'all': hq(fl)})
# current flagged evidence items (meta) vs log
cur = [k for k, m in meta.items() if m.get('flagged')]
logged_open = set(fl[(~fl.resolved) & (fl.st == 'EvidenceItem')].sid.astype(int))
P('meta_flagged_now_crosscheck', {'evidence_flagged_now(meta)': len(cur), 'with_open_flag_in_log': len(set(cur) & logged_open),
                                  'with_open_bot_flag': len(set(cur) & set(b[(~b.resolved) & (b.st == 'EvidenceItem')].sid.astype(int))),
                                  'flagged_now_without_open_flag_in_log': len(set(cur) - logged_open)})
# 2021-08 batch: what happened to those items
batch = b[b.ym == '2021-08']
P('bot_batch_2021_08', {'n': len(batch), 'resolved_logged': wilson(int(batch.resolved.sum()), len(batch)), 'status_now': batch.ev_status_now.value_counts().to_dict(),
                        'flagged_now_true': int((batch.ev_flagged_now == True).sum()), 'later_bot_revision_same_entity': int(batch.later_bot_revision_same_entity.sum())})
# flags on submitted items: does an open bot flag precede the item's decision? (hazard check is in T2: flag_bot)
json.dump(R, open('res_t5_botflags.json', 'w'), indent=1, default=str)
ge = fl[fl.bot & (fl.st == 'EvidenceItem')]
silent = (~ge.resolved) & (ge.ev_flagged_now == False)
P('silent_closure_vs_later_bot_revision', {'silent': int(silent.sum()), 'silent_with_later_bot_revision(2023-01 v2 migration)': int((silent & ge.later_bot_revision_same_entity).sum()),
    'still_flagged_with_later_bot_revision': int(((ge.ev_flagged_now == True) & ge.later_bot_revision_same_entity).sum()),
    'still_flagged_without_later_bot_revision': int(((ge.ev_flagged_now == True) & ~ge.later_bot_revision_same_entity).sum()),
    'silent_without_later_bot_revision': int((silent & ~ge.later_bot_revision_same_entity).sum())})
json.dump(R, open('res_t5_botflags.json', 'w'), indent=1, default=str)
