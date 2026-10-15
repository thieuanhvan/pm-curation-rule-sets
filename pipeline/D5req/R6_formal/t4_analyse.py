# R6 task 4 analysis: second R(t) on the content gates of GO and HPO and Definition 3 on term-adding merges.
# Inputs: t4_gh_raw.json (W2-linked merges, workflow/CODEOWNERS/Travis history, branch API), t4b_window_raw.json (window sample).
# R(t) for the content gate: c_QC = "the change reaching the default branch has a passing run of the repository's QC workflow".
#   tau_c(workflow) = first commit adding .github/workflows/qc.yml (detective control: it runs, it does not refuse);
#   Travis predecessor = .travis.yml lifetime; preventive form (required status check in branch protection) is observable only
#   as the current state via GET /branches/{b} (protection history requires admin: GET /branches/{b}/protection -> 403).
# Definition 3: share of term-adding merges (head sha of the merged PR, or the pushed commit) with a successful run of qc.yml,
#   among merges with time >= tau_c; measurable only where GitHub still retains check data (about 400 days).
import os, json, collections
H = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(os.path.join(H, 't4_gh_raw.json'), encoding='utf-8'))
win = json.load(open(os.path.join(H, 't4b_window_raw.json'), encoding='utf-8')) if os.path.exists(os.path.join(H, 't4b_window_raw.json')) else {}
res = {}
def qc_ok(row):
    runs = row.get('runs') or []
    return any((r.get('path') or '').endswith('/qc.yml') and r.get('conclusion') == 'success' for r in runs)
def qc_any(row):
    return any((r.get('path') or '').endswith('/qc.yml') for r in (row.get('runs') or []))
for tag in ('go', 'hpo'):
    o = raw[tag]; wc = o['workflow_commits']; tr = o['commits_.travis.yml']
    first_qc = min(c['date'] for c in wc if 'qc' in c['msg'].lower() or True) if wc else None
    snaps = o['workflow_snapshots']
    qc_first = min((s['date'] for s in snaps if 'qc.yml' in s['files']), default=None)
    r = res[tag] = {
        'branch_protection_current': {'protected': o['branch_api']['protected'], 'required_checks': (o['branch_api'].get('protection') or {}).get('required_status_checks'),
                                      'protection_history_visible': o['protection_api_status'] == 200, 'protection_endpoint_status': o['protection_api_status'],
                                      'rulesets': o['rulesets_api']['n']},
        'travis_yml': {'first_commit': tr[-1]['date'][:10] if tr else None, 'deleted': tr[0]['date'][:10] if tr and 'delete' in tr[0]['msg'].lower() else None, 'n_commits': len(tr)},
        'qc_workflow_first': qc_first[:10] if qc_first else None,
        'workflow_commits': len(wc), 'workflow_files_now': snaps[0]['files'] if snaps else [],
        'workflow_files_added': {}, 'codeowners_commits': sum(len(o[k]) for k in o if k.startswith('commits_') and 'CODEOWNERS' in k)}
    seen = set()
    for s in sorted(snaps, key=lambda s: s['date']):
        for f in s['files']:
            if f not in seen: seen.add(f); r['workflow_files_added'][f] = s['date'][:10]
    U = o['units']
    r['w2_linked_units'] = {'n': len(U), 'with_pr': sum(1 for u in U if u.get('pr')), 'direct_push': sum(1 for u in U if u.get('direct_push')),
                            'merge_year_range': [min((u.get('merged_at') or '9')[:4] for u in U), max((u.get('merged_at') or '0')[:4] for u in U)] if U else None,
                            'with_any_retained_check_data': sum(1 for u in U if u.get('runs') or u.get('check_runs') or u.get('statuses')),
                            'earliest_merge_with_retained_runs': min((u['merged_at'] for u in U if u.get('runs')), default=None),
                            'qc_success_among_retained': [sum(1 for u in U if qc_ok(u)), sum(1 for u in U if u.get('runs'))]}
    if tag in win:
        w = win[tag]; rows = w['rows']; units = [x for x in rows if x.get('unit')]
        tau = r['qc_workflow_first']
        ins = [x for x in units if (x.get('merged_at') or '') >= (tau or '9')]
        r['window_sample'] = {'window_from': '2025-08-23', 'population_closed_in_window': w['window_population'], 'sampled_tickets': w['sampled'],
                              'tickets_with_term_adding_merge': len(units), 'tickets_closed_without_linked_merge': len(rows) - len(units),
                              'closed_as_not_planned_or_duplicate': sum(1 for x in rows if x.get('state_reason') in ('not_planned', 'duplicate')),
                              'merges_via_pr': sum(1 for x in units if x.get('has_pr')), 'direct_pushes': sum(1 for x in units if x.get('direct_push')),
                              'with_qc_run': sum(1 for x in ins if qc_any(x)), 'with_qc_success': sum(1 for x in ins if qc_ok(x)), 'n_after_tau': len(ins),
                              'F_R': round(sum(1 for x in ins if qc_ok(x)) / len(ins), 3) if ins else None,
                              'other_workflows_seen': dict(collections.Counter(os.path.basename(rr.get('path') or '') for x in ins for rr in (x.get('runs') or []))),
                              'qc_workflow_first': w.get('qc_first'), 'qc_workflow_current': w.get('qc_current')}
json.dump(res, open(os.path.join(H, 'res_t4.json'), 'w'), indent=1)
print(json.dumps(res, indent=1)[:6000])
