# R6 task 1 (step 2): curated control set C = C_doc U C_code for CIViC with tau_c, and kappa_s(t) per stage.
# Each code control below is backed by signatures in t1_signatures.json (scan of every v2 release tag and monthly v1
# master snapshots) and by a first commit found with `git log -S` (commit ids given). v1 had no release tags; deployment
# was continuous, so tau_c(v1) = first-commit date, cross-checked against the first monthly snapshot containing it.
# Documented status (doc): 'yes' = stated in CIViC documentation / SOP (W3/sop_src, manuscript Table 2 sources);
# 'no' = code only; 'n/a' = automatic behaviour that the documentation neither states nor forbids.
import os, json, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
STAGES = ['intake', 'fit', 'selection', 'allocation', 'decision', 'flag raising', 'flag resolution', 'exit (no judgement)', 're-review']
C = [
 # id, stage, object, mode, predicate, doc, tau_commit, first_commit, tau_release, release, removed, removed_by
 ('D1', 'decision', 'evidence item', 'guard', 'acceptance only by editor role (admin/moderator/editor ladder in v1)', 'yes', '2015-01-27', 'f13b7252 (v1)', '2015-01-27', 'v1 continuous', None, None),
 ('D2', 'decision', 'evidence item', 'guard', 'no self-acceptance of own submission', 'yes', '2016-07-20', '313586fa (v1)', '2016-07-20', 'v1 continuous; v2.0.0 keeps it', None, None),
 ('D3', 'decision', 'revision', 'guard', 'acceptance of suggested change/revision only by editor role', 'yes', '2015-01-12', 'a491b3bc (v1)', '2015-01-12', 'v1 continuous', None, None),
 ('D4', 'decision', 'revision', 'guard', 'no self-acceptance of own revision (v2: except own pending submission)', 'yes', '2016-07-20', '313586fa (v1)', '2016-07-20', 'v1 continuous; v2.0.0', None, None),
 ('D5', 'decision', 'all moderated objects (v1)', 'guard', 'valid conflict-of-interest statement for moderation (editor_without_coi)', 'yes', '2019-09-10', 'ca3bb805 (v1)', '2019-09-10', 'v1 continuous', '2022-04-09', 'v2.0.0 keeps COI for revisions, flags, source suggestions, NOT for evidence-item or assertion moderation (approve_assertion only from v2.7.2, 2026-04-07)'),
 ('D5b', 'decision', 'revision, flag, source suggestion (v2)', 'guard', 'valid COI statement (has_valid_coi_statement)', 'yes', '2021-10-18', 'civic-v2 dev history', '2022-04-09', 'v2.0.0', None, None),
 ('D6', 'decision', 'revision', 'guard', 'reason (comment, >= 10 characters) required to reject a revision', 'yes', '2021-10-18', '46029db58a (v2 dev)', '2022-04-09', 'v2.0.0', None, None),
 ('D7', 'decision', 'evidence item, assertion', 'guard', 'reason required to reject or revert; no comment on acceptance', 'yes', '2025-03-20', 'ff10f7e00', '2025-04-07', 'v2.5.13', None, None),
 ('D8', 'decision', 'all moderated objects', 'guard', 'acting organisation must be one of the user\'s organisations', 'no', '2020-04-30', 'aba69766 (v1)', '2020-04-30', 'v1 continuous; v2.0.0', None, None),
 ('I1', 'intake', 'revision', 'guard', 'comment (>= 10 characters) required when suggesting a revision', 'yes (SOP: "should always include a comment")', '2021-10-18', 'civic-v2 dev history', '2022-04-09', 'v2.0.0', None, None),
 ('I2', 'intake', 'evidence item', 'guard', 'submission requires a logged-in user (any role); optional comment >= 10 chars if given', 'yes', '2015-02-20', 'f11d973e (v1)', '2015-02-20', 'v1 continuous', None, None),
 ('I3', 'intake', 'revision', 'automatic', 'bot creates revisions replacing preprint sources (UpdatePreprints, scheduled daily)', 'no', '2026-08-10', '41fad47b2', None, 'not in any release tag up to v2.7.6', None, None),
 ('F1', 'flag raising', 'any entity', 'guard', 'comment (>= 10 characters) required to raise a flag', 'yes (SOP: curators "should flag")', '2021-03-06', 'civic-v2 dev history', '2022-04-09', 'v2.0.0', None, None),
 ('F2', 'flag raising', 'variant', 'automatic', 'bot raises flags on duplicate allele-registry ids (scheduled weekly)', 'no', '2023-10-04', '21b6fcbbe', '2023-11-08', 'v2.2.29', None, None),
 ('R1', 'flag resolution', 'flag', 'guard', 'resolution only by flagging user or editor (v1), editor + COI + comment >= 10 chars (v2)', 'no', '2017-03-31', '85a48178 (v1)', '2017-04-04', 'v1 continuous; v2.0.0 adds COI and comment', None, None),
 ('X1', 'exit (no judgement)', 'revision (suggested change)', 'automatic', 'conflicting pending changes marked superseded after an accepted change (job FindSupersededChanges)', 'n/a', '2015-04-29', '86b02248 (v1)', '2015-04-29', 'v1 continuous', '2016-02-24', '3335e4e9 "remove unneeded background task"; status value superseded kept but never set until v2'),
 ('X2', 'exit (no judgement)', 'revision', 'automatic', 'pending revisions of the same field superseded on acceptance (AcceptRevisions)', 'n/a', '2021-10-18', 'civic-v2 dev history', '2022-04-09', 'v2.0.0', None, None),
 ('X3', 'exit (no judgement)', 'evidence item', 'permission', 'submitter may withdraw (reject) own item (enabling, not refusing)', 'yes', '2019-01-29', 'ebfee72417 (v1)', '2019-01-29', 'v1 continuous', None, None),
 ('RR1', 're-review', 'assertion approval', 'automatic', 'active organisational approvals set to requires_review when the assertion is flagged or a supporting evidence item rejected', 'no', '2025-03-19', 'ef697a340', '2025-06-03', 'v2.5.17', None, None),
 ('Fit1', 'fit', 'evidence item', 'documented only', 'no acceptance while a revision is pending (UI shows fields with pending changes; not enforced)', 'yes', None, None, None, 'never configured', None, None),
 ('S1', 'selection', 'evidence item', 'none', 'no ordering rule, priority or worklist (search: assign/priority/due_date/worklist in server code: none)', 'no rule', None, None, None, 'never configured', None, None),
 ('A1', 'allocation', 'evidence item', 'none', 'no owner, assignment or due date', 'no rule', None, None, None, 'never configured', None, None),
 ('X4', 'exit (no judgement)', 'evidence item', 'none', 'no expiry, stale or timer exit; no scheduled job writes evidence-item status (21 v1 and 23 v2 scheduled tasks inspected)', 'no rule', None, None, None, 'never configured', None, None),
 ('X5', 'exit (no judgement)', 'flag', 'none', 'no automatic flag closure; bulk closure Jan 2023 was a one-off data operation (no job in any release)', 'no rule', None, None, None, 'never configured', None, None),
]
cols = ['id', 'stage', 'object', 'mode', 'predicate', 'doc', 'tau_commit', 'first_commit', 'tau_release', 'release', 'removed', 'removed_note']
T = pd.DataFrame(C, columns=cols)
T['in_C_doc'] = T.doc.str.startswith('yes'); T['in_C_code'] = T.tau_release.notna()
# kappa_s(t): 1 if some code control of stage s is in force at t (tau_release <= t < removed). Two variants: any mode; guard (refusing) only.
qs = pd.period_range('2014Q4', '2026Q3', freq='Q')
K = {'any': {}, 'guard_only': {}, 'automatic_only': {}, 'evidence_item_queue_only': {}}
for q in qs:
    t = q.end_time.strftime('%Y-%m-%d')
    for var in K:
        row = {}
        for s in STAGES:
            m = (T.stage == s) & T.tau_release.notna() & (T.tau_release <= t) & (T.removed.isna() | (T.removed > t))
            m &= T['mode'].isin(['guard', 'automatic'])
            if var == 'evidence_item_queue_only': m &= T.object.str.contains('evidence item|all moderated')
            if var == 'guard_only': m &= T['mode'] == 'guard'
            if var == 'automatic_only': m &= T['mode'] == 'automatic'
            row[s] = int(m.any())
        K[var][str(q)] = row
# compress to change points
def changes(series):
    out, prev = [], None
    for q, row in series.items():
        if row != prev: out.append({'from': q, **row}); prev = row
    return out
res = {'controls': T.to_dict('records'), 'kappa_change_points': {k: changes(v) for k, v in K.items()},
       'counts': {'C_doc': int(T.in_C_doc.sum()), 'C_code': int(T.in_C_code.sum()), 'C_doc_and_code': int((T.in_C_doc & T.in_C_code).sum()),
                  'code_only': int((~T.in_C_doc & T.in_C_code).sum()), 'doc_only_never_configured': int((T.in_C_doc & ~T.in_C_code).sum())},
       'v1_superseded_status': 'yes: status "superseded" added to SuggestedChange.valid_statuses on 2015-04-29 (86b02248) with job FindSupersededChanges; job removed 2016-02-24 (3335e4e9); the status value remained valid in v1 but no code set it afterwards; REVISION_SUPERSEDED events in the public log occur only from 2022 (v2).'}
json.dump(res, open(os.path.join(H, 'res_t1_controls.json'), 'w', encoding='utf-8'), indent=1, default=str)
for k, v in res['kappa_change_points'].items():
    print(k); print(pd.DataFrame(v).to_string(index=False))
print(res['counts'])
