# R7 task 1b: agreement between the R6 control table (coder 1) and the independent second coding (coder2_controls.json)
# over control x snapshot presence cells at S1=v1@2016-06, S2=v1@2020-06, S3=v2.0.0, S4=v2.7.6.
# Harmonised units: one row per control as the finer coder defines it; R6 presence derived from tau_release/removed.
import json, os
H = os.path.dirname(os.path.abspath(__file__))
SNAP = {'S1': '2016-06-30', 'S2': '2020-06-23', 'S3': '2022-04-09', 'S4': '2026-08-27'}
r6 = {c['id']: c for c in json.load(open(os.path.join(H, '..', 'R6_formal', 'res_t1_controls.json'), encoding='utf-8'))['controls']}
c2 = {c['id']: c for c in json.load(open(os.path.join(H, 'coder2_controls.json'), encoding='utf-8'))['controls']}
def pres6(ids):
    v = []
    for s, d in SNAP.items():
        v.append(int(any(r6[i]['tau_release'] and r6[i]['tau_release'] <= d and (not r6[i]['removed'] or r6[i]['removed'] > d) for i in ids)))
    return v
def pres2(ids):
    return [int(any(c2[i]['S'][k] for i in ids)) for k in range(4)]
STG = lambda s: s.split(' (')[0]
# (unit, R6 ids, coder-2 ids)
U = [('account to submit', ['I2'], ['intake_account']), ('revision comment>=10', ['I1'], ['intake_rev_comment10']),
     ('acting organisation', ['D8'], ['acting_org']), ('editor accepts EI', ['D1'], ['dec_editor_ei']), ('editor accepts revision', ['D3'], ['dec_editor_rev']),
     ('no self-acceptance EI', ['D2'], ['dec_noself_ei']), ('no self-acceptance revision', ['D4'], ['dec_noself_rev']),
     ('assertion accept: editor, not submitter', [], ['dec_assertion_editor_noself']),
     ('COI for EI/assertion moderation', ['D5'], ['dec_coi_ei', 'dec_coi_assertion_moderation']),
     ('COI for revision/flag/source-suggestion moderation', ['D5', 'D5b'], ['dec_coi_rev', 'source_suggestion_coi']),
     ('reason>=10 to reject revision', ['D6'], ['dec_reason_rev_reject']), ('reason to reject EI/assertion', ['D7'], ['dec_reason_ei_reject']),
     ('assertion approval: org approver + COI', [], ['approval_coi_org']),
     ('fit: stale base value refuses revision acceptance (v1, force override)', [], ['fit_stale_revision']),
     ('fit: approval refused if assertion flagged/not accepted', [], ['fit_approval_state']),
     ('account to raise flag', [], ['flag_raise_account']), ('flag comment>=10', ['F1'], ['flag_raise_comment10']), ('bot duplicate flags', ['F2'], ['flag_raise_bot_dup']),
     ('flag resolution permission (+comment v2)', ['R1'], ['flag_resolve_perm', 'flag_resolve_comment10']),
     ('revision superseded on acceptance', ['X1', 'X2'], ['exit_rev_superseded']),
     ('source suggestion auto-curated on EI submission (v1)', [], ['exit_source_suggestion_curated']),
     ('rejected EI re-opened on revision suggestion/acceptance (v1)', [], ['reopen_rejected_ei']),
     ('assertion approvals reset to requires_review', ['RR1'], ['rereview_assertion_approval']),
     ('withdrawal permission', ['X3'], ['withdrawal_permission']), ('bot preprint revisions (unreleased)', ['I3'], [])]
ABS = ['Fit1', 'S1', 'A1', 'X4', 'X5']  # absence records, both coders: never in code at any snapshot
rows = []
for name, a, b in U:
    p1, p2 = pres6(a) if a else [0]*4, pres2(b) if b else [0]*4
    st1 = STG(r6[a[-1]]['stage']) if a else None; st2 = STG(c2[b[0]]['stage']) if b else None
    m1 = r6[a[-1]]['mode'] if a else None; m2 = c2[b[0]]['mode'] if b else None
    rows.append({'unit': name, 'R6': a, 'coder2': b, 'pres_R6': p1, 'pres_coder2': p2, 'stage_R6': st1, 'stage_coder2': st2, 'mode_R6': m1, 'mode_coder2': m2})
def kappa(pairs):
    n = len(pairs); po = sum(x == y for x, y in pairs) / n
    p1 = sum(x for x, _ in pairs) / n; p2 = sum(y for _, y in pairs) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return round((po - pe) / (1 - pe), 3), round(po, 3), n
cells = [(x, y) for r in rows for x, y in zip(r['pres_R6'], r['pres_coder2'])]
cells_abs = cells + [(0, 0)] * (4 * len(ABS))
both = [r for r in rows if r['R6'] and r['coder2']]
stage_agree = sum(r['stage_R6'] == r['stage_coder2'] or (r['stage_R6'] or '').startswith('exit') and (r['stage_coder2'] or '').startswith('exit') for r in both)
mode_agree = sum(r['mode_R6'] == r['mode_coder2'] for r in both)
dis = [{'unit': r['unit'], 'R6': r['pres_R6'], 'coder2': r['pres_coder2']} for r in rows if r['pres_R6'] != r['pres_coder2']]
stage_dis = [{'unit': r['unit'], 'R6': r['stage_R6'], 'coder2': r['stage_coder2']} for r in both if not (r['stage_R6'] == r['stage_coder2'] or (r['stage_R6'] or '').startswith('exit') and (r['stage_coder2'] or '').startswith('exit'))]
k, po, n = kappa(cells); ka, poa, na = kappa(cells_abs)
res = {'units': rows, 'n_units': len(rows), 'n_absence_records': len(ABS),
       'presence_kappa_controls_only': {'kappa': k, 'p_agree': po, 'cells': n},
       'presence_kappa_with_absence_records': {'kappa': ka, 'p_agree': poa, 'cells': na},
       'units_matched_both': len(both), 'stage_agreement': f'{stage_agree}/{len(both)}', 'mode_agreement': f'{mode_agree}/{len(both)}',
       'presence_disagreements': dis, 'stage_disagreements': stage_dis,
       'units_only_coder2': [r['unit'] for r in rows if not r['R6']], 'units_only_R6': [r['unit'] for r in rows if not r['coder2']]}
json.dump(res, open(os.path.join(H, 'res_t1b_agreement.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'units'}, indent=1))
