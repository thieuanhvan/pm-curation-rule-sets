# R7 task 5 analysis: GO merge-gate conformance over time within check-run retention; HPO term_tracker_item feasibility.
import os, json, collections, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); d = json.load(open(os.path.join(H, 'gh_cache', 't5_raw.json'), encoding='utf-8'))
P = pd.DataFrame(d['go_prs']); P['m'] = pd.to_datetime(P.merged_at).dt.to_period('M').astype(str)
F = P[P.qc != 'not_fetched'].copy()
out = {'go_merged_prs_since_2025-06': int(len(P)), 'with_check_runs_fetched': int(len(F)), 'fetched_window': [F.merged_at.min()[:10], F.merged_at.max()[:10]],
       'qc_outcome_counts': F.qc.value_counts().to_dict()}
tab = F.groupby('m').qc.apply(lambda s: {'n': int(len(s)), 'success': int((s == 'success').sum()), 'missing': int((s == 'missing').sum()), 'failure_or_pending': int(s.isin(['failure', 'pending']).sum())}).unstack().to_dict('index')
out['by_month'] = tab
bad = F[F.qc != 'success'].sort_values('merged_at')
out['last_merge_without_passing_qc'] = bad.merged_at.max()[:10] if len(bad) else None
out['first_fetched_merge_with_check_runs_present'] = F[F.n_runs.fillna(0) > 0].merged_at.min()[:10] if 'n_runs' in F else None
out['merges_without_any_check_run_record'] = int((F.n_runs.fillna(0) == 0).sum())
out['bad_by_author_association'] = bad.assoc.value_counts().to_dict()
S = d['hpo_sample']
out['hpo'] = {'commits_touching_hp-edit.owl_since_2025-08': d['hpo_commits_total_since_2025-08'], 'sample': len(S),
              'patch_available': sum(c['patch_available'] for c in S),
              'with_added_class_declaration': sum(c.get('added_class_decl', 0) > 0 for c in S),
              'with_added_term_tracker_item': sum(c.get('added_term_tracker', 0) > 0 for c in S),
              'class_adding_with_tracker_issue_ref': sum(c.get('added_class_decl', 0) > 0 and c.get('tracker_issue_refs', 0) > 0 for c in S),
              'commit_message_has_issue_ref': sum(c['msg_issue_ref'] for c in S)}
json.dump(out, open(os.path.join(H, 'res_t5_go_hpo.json'), 'w', encoding='utf-8'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
