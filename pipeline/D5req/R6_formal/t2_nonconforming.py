# R6 task 2: nonconforming events against R(t) and the 84 % (2022Q2) vs >= 95 % reason enactment.
# Inputs: D5b/cache (event log), A6/cache (activities with note), A1/meta via D5b/meta_users.json (current role only).
# Output: res_t2.json (aggregates only, no user ids).
import os, json, glob, collections
import pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..')
BOT = {385}
ev, seen = [], set()
for f in sorted(glob.glob(os.path.join(R, '..', 'D5b', 'cache', 'ev_*.json'))):
    for e in json.load(open(f, encoding='utf-8')):
        if e['id'] in seen: continue
        seen.add(e['id']); ev.append(e)
E = pd.DataFrame([{'eid': e['id'], 'act': e['action'], 't': pd.Timestamp(e['createdAt']).tz_localize(None),
                   'u': (e.get('originatingUser') or {}).get('id'), 'ot': (e.get('originatingObject') or {}).get('__typename'),
                   'oid': (e.get('originatingObject') or {}).get('id'), 'st': (e.get('subject') or {}).get('__typename'),
                   'sid': (e.get('subject') or {}).get('id')} for e in ev]).sort_values(['t', 'eid'])
users = {u['id']: u for u in json.load(open(os.path.join(R, '..', 'D5b', 'meta_users.json'), encoding='utf-8'))}
act = {}
for t in ('MODERATE_EVIDENCE_ITEM', 'REJECT_REVISIONS'):
    for a in json.load(open(os.path.join(R, 'A6', 'cache', f'act_{t}.json'), encoding='utf-8')):
        for x in a['events']:
            act[x['id']] = {'type': t, 'note': (a.get('note') or '').strip(), 'act_t': a['createdAt'], 'act_id': a['id'], 'n_events': len(a['events']), 'act_u': (a.get('user') or {}).get('id')}
out = {}
V2 = pd.Timestamp('2022-04-09')
# ---------- revision rejections: reason enactment by quarter, split by linkage to a REJECT_REVISIONS activity
rv = E[E.ot == 'Revision']
sug = rv[rv.act == 'REVISION_SUGGESTED'].drop_duplicates('oid').set_index('oid')
rej = rv[(rv.act == 'REVISION_REJECTED') & ~rv.u.isin(BOT)].drop_duplicates('oid').copy()
rej['self'] = rej.oid.map(sug.u) == rej.u
rej['linked'] = rej.eid.map(lambda i: i in act)
rej['note_len'] = rej.eid.map(lambda i: len(act[i]['note']) if i in act else -1)
rej['n_in_act'] = rej.eid.map(lambda i: act[i]['n_events'] if i in act else 0)
rej['q'] = rej.t.dt.to_period('Q').astype(str)
post = rej[rej.t >= V2]
def qtab(d):
    g = d.groupby('q')
    return {q: {'n': int(len(x)), 'note10_all': round(float((x.note_len >= 10).mean()), 3),
                'linked_share': round(float(x.linked.mean()), 3),
                'note10_linked': round(float((x[x.linked].note_len >= 10).mean()), 3) if x.linked.any() else None,
                'self_share': round(float(x.self.mean()), 3)} for q, x in g}
out['rev_reject_by_quarter_2022_2024'] = {k: v for k, v in qtab(rej[(rej.t >= '2021-10-01') & (rej.t < '2024-07-01')]).items()}
bad = post[post.note_len < 10]
out['rev_reject_post_launch'] = {'n': int(len(post)), 'without_note10': int(len(bad)),
    'without_note10_unlinked_to_activity': int((~bad.linked).sum()),
    'without_note10_linked_empty_note': int((bad.linked & (bad.note_len == 0)).sum()),
    'without_note10_linked_short_note': int((bad.linked & (bad.note_len > 0)).sum()),
    'without_note10_self_withdrawal': int(bad.self.sum()),
    'by_quarter': bad.q.value_counts().sort_index().to_dict(),
    'subject_types': bad.st.value_counts().to_dict(),
    'last': str(bad.t.max())[:10] if len(bad) else None}
# 2022Q2 deep-dive: are the unnoted events bulk (many events in one activity) or same-second clusters?
q2 = post[(post.q == '2022Q2')]
q2b = q2[q2.note_len < 10]
out['rev_reject_2022Q2'] = {'n': int(len(q2)), 'without_note10': int(len(q2b)), 'unlinked': int((~q2b.linked).sum()),
    'first_week_after_launch_share_of_unnoted': round(float((q2b.t < V2 + pd.Timedelta(days=7)).mean()), 3) if len(q2b) else None,
    'in_multi_event_activities': int((q2b.n_in_act > 1).sum()),
    'distinct_rejectors_band': '<5' if q2b.u.nunique() < 5 else '>=5'}
# Unlinked events: check whether any linked activity exists for the same revision at all, and time gap to nearest REJECT_REVISIONS activity
acts = pd.DataFrame([{'act_t': pd.Timestamp(v['act_t']).tz_localize(None), 'act_id': v['act_id']} for v in act.values() if v['type'] == 'REJECT_REVISIONS']).drop_duplicates('act_id').sort_values('act_t')
out['reject_revisions_activities_first'] = str(acts.act_t.min())[:10]
out['rev_reject_linked_share_pre_launch'] = round(float(rej[rej.t < V2].linked.mean()), 3)
# ---------- self-acceptance of revisions against R(t) (v1: blocked from 2016-07-20; v2: allowed only on own pending submission)
status, submitter = {}, {}
STAT = {'SUBMITTED': 'submitted', 'ASSERTION_SUBMITTED': 'submitted', 'ACCEPTED': 'accepted', 'ASSERTION_ACCEPTED': 'accepted',
        'REJECTED': 'rejected', 'ASSERTION_REJECTED': 'rejected', 'REVERTED': 'submitted', 'ASSERTION_REVERTED': 'submitted'}
revsug = {}; viol = []; tot_acc = 0
for r in E.itertuples():
    k = (r.st, r.sid)
    if r.act in STAT and r.sid is not None:
        if r.act.endswith('SUBMITTED') and k not in submitter: submitter[k] = r.u
        status[k] = STAT[r.act]
    if r.act == 'REVISION_SUGGESTED': revsug[r.oid] = (r.u, r.t)
    if r.act == 'REVISION_ACCEPTED' and r.u not in BOT:
        tot_acc += 1
        if revsug.get(r.oid, (None,))[0] != r.u: continue
        own_pending = submitter.get(k) == r.u and status.get(k) == 'submitted'
        if r.t >= V2 and not own_pending or (r.t < V2 and r.t >= pd.Timestamp('2016-07-20')):
            gap = (r.t - revsug[r.oid][1]).total_seconds()
            viol.append({'year': r.t.year, 'platform': 'v2' if r.t >= V2 else 'v1', 'subject_type': r.st,
                         'subject_status': status.get(k), 'own_subject': submitter.get(k) == r.u,
                         'role_now': (users.get(r.u) or {}).get('role'), 'accept_within_60s': gap <= 60, 'u': r.u})
V = pd.DataFrame(viol)
out['rev_self_accept_nonconforming'] = {'n': int(len(V)), 'of_revision_acceptances': tot_acc,
    'rate': round(len(V) / tot_acc, 6), 'by_platform': V.platform.value_counts().to_dict(), 'by_year': V.year.value_counts().sort_index().to_dict(),
    'by_subject_type': V.subject_type.value_counts().to_dict(), 'by_subject_status': V.subject_status.fillna('no status (non-submittable entity)').value_counts().to_dict(),
    'by_current_role': V.role_now.value_counts().to_dict(), 'accepted_within_60s_of_suggestion': int(V.accept_within_60s.sum()),
    'distinct_users_band': '<5' if V.u.nunique() < 5 else '>=5'}
# ---------- evidence-item decisions against R(t): editor-only + no self-accept (2016-07-20), reason for rejection (2025-04-07)
ei = E[E.st == 'EvidenceItem']
subm = ei[ei.act == 'SUBMITTED'].drop_duplicates('sid').set_index('sid').u
eacc = ei[(ei.act == 'ACCEPTED') & ~ei.u.isin(BOT)]
selfacc = eacc[eacc.sid.map(subm) == eacc.u]
erej = ei[(ei.act == 'REJECTED') & ~ei.u.isin(BOT)].copy(); erej['note_len'] = erej.eid.map(lambda i: len(act[i]['note']) if i in act else -1)
erej_post = erej[erej.t >= '2025-04-07']
out['eid'] = {'self_accept_total': int(len(selfacc)), 'self_accept_after_2016-07-20': int((selfacc.t >= '2016-07-20').sum()),
              'rejections_after_2025-04-07': int(len(erej_post)), 'without_note10': int((erej_post.note_len < 10).sum()),
              'unlinked': int((erej_post.note_len < 0).sum())}
# ---------- supersession events by year (v1 job 2015-04-29..2016-02-24; v2 from 2022-04)
sup = E[E.act == 'REVISION_SUPERSEDED']
out['revision_superseded_events_by_year'] = sup.t.dt.year.value_counts().sort_index().to_dict()
out['revision_superseded_actor'] = {'bot_or_null': int((sup.u.isna() | sup.u.isin(BOT)).sum()), 'human_account': int((~(sup.u.isna() | sup.u.isin(BOT))).sum())}
# superseded: same-second as an acceptance by the same user (side effect of acceptance)?
acc_t = E[E.act == 'REVISION_ACCEPTED'].groupby('u').t.apply(set)
out['revision_superseded_same_second_as_acceptance_by_same_account'] = round(float(sup.apply(lambda r: r.t in acc_t.get(r.u, set()), axis=1).mean()), 3) if len(sup) else None
json.dump(out, open(os.path.join(H, 'res_t2.json'), 'w', encoding='utf-8'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
# ---------- addendum: raw (unstripped) note length as the code checks it; null notes vs attached comments
raw = {}
for a in json.load(open(os.path.join(R, 'A6', 'cache', 'act_REJECT_REVISIONS.json'), encoding='utf-8')):
    for x in a['events']: raw[x['id']] = a.get('note')
post = post.copy()
post['raw_len'] = post.eid.map(lambda i: -1 if raw.get(i) is None else len(raw[i]))
post['note_null'] = post.raw_len < 0
cmr = E[(E.act == 'COMMENTED') & (E.st == 'Revision')]
cm_by = {k: g for k, g in cmr.groupby('sid')}
def has_cm(r):
    g = cm_by.get(r.oid)
    return g is not None and bool(((g.u == r.u) & ((g.t - r.t).abs() <= pd.Timedelta(minutes=2))).any())
post['cm_attached'] = [has_cm(r) for r in post.itertuples()]
V23 = pd.Timestamp('2024-01-05')  # v2.3.0: notes stored on activities (d0f9adfeb, 1eeae6a75); earlier notes are back-filled
qq = {}
for q, x in post.groupby('q'):
    if q > '2023Q4': continue
    qq[q] = {'n': int(len(x)), 'note_raw10': round(float((x.raw_len >= 10).mean()), 3), 'note_null': int(x.note_null.sum())}
nul = post[post.note_null]
out['addendum'] = {
    'rev_reject_2022Q2_pre_launch_days': {'n': int(len(rej[(rej.q == '2022Q2') & (rej.t < V2)])), 'note10': int((rej[(rej.q == '2022Q2') & (rej.t < V2)].note_len >= 10).sum())},
    'post_launch_by_quarter_raw_length': qq,
    'post_launch_raw_length_ge10': int((post.raw_len >= 10).sum()), 'post_launch_n': int(len(post)),
    'null_note_n': int(len(nul)), 'null_note_before_v2.3.0': int((nul.t < V23).sum()), 'null_note_with_comment_by_rejector_within_2min': int(nul.cm_attached.sum()),
    'null_note_self_withdrawal': int(nul.self.sum()),
    'whitespace_padded_10char_notes': int(((post.raw_len >= 10) & (post.note_len < 10)).sum())}
print(json.dumps(out['addendum'], indent=1))
json.dump(out, open(os.path.join(H, 'res_t2.json'), 'w', encoding='utf-8'), indent=1, default=str)
