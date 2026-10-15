# R8 analysis E: number reconciliations for the round-7 list. Aggregates only.
import os, sys, json, subprocess, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
os.environ['OUTNAME'] = 'tmp_c_rerun.json'
sys.path.insert(0, H)
import c_decomp_drift as C  # rebuilds the evaluable-event table D (same code as R7 t2_baselines.py)
D = C.D; V2 = C.V2
out = {}
tot = len(D)
op_v2 = int(((D.c == 'SA_rev') & D.own_pending & (D.t >= V2)).sum())
op_v1 = int(((D.c == 'SA_rev') & D.own_pending & (D.t < V2)).sum())
fit = int((D.c == 'FIT1').sum())
out['57718_documented_constant'] = {'all_evaluable_events': tot, 'FIT1_C3': fit, 'SA_rev': int((D.c == 'SA_rev').sum()), 'SA_ei': int((D.c == 'SA_ei').sum()),
                                    'RSN_rev': int((D.c == 'RSN_rev').sum()), 'RSN_ei': int((D.c == 'RSN_ei').sum())}
out['table4_sum_56746'] = {'equals_57718_minus_v2_own_pending_revision_acceptances': tot - op_v2,
                           'v2_own_pending_revision_acceptances': op_v2,
                           'other_gap': 56746 - (tot - op_v2)}
out['51659_latest_code'] = {'equals_57718_minus_FIT1_minus_all_own_pending_SA_rev': tot - fit - op_v1 - op_v2,
                            'own_pending_SA_rev_v1_era': op_v1, 'own_pending_SA_rev_v2_era': op_v2}
TS = C.TAU_SA; COMMIT = pd.Timestamp('2016-07-20 21:57:45')
for c in ('SA_rev', 'SA_ei'):
    x = D[(D.c == c) & ~D.holds]
    out[f'{c}_self_acceptances'] = {'before_monthly_tau_2016-07-20': int((x.t < TS).sum()), 'before_commit_tau': int((x.t < COMMIT).sum()),
                                     'before_commit_tau_not_own_pending': int(((x.t < COMMIT) & ~x.own_pending).sum()),
                                     'before_2016-02-24': int((x.t < C.TAU_SA_PART).sum())}
out['F_R'] = {'monthly_tau': [int(D.violR_month.sum()), int(D.inR_month.sum())], 'commit_tau': [int(D.violR.sum()), int(D.inR.sum())]}
x = D[(D.c == 'SA_rev') & D.inR_month]; out['SA_rev_in_force_conformance_monthly_tau'] = [int(x.holds.sum()), int(len(x)), round(x.holds.mean() * 100, 3)]
x = D[(D.c == 'SA_rev') & D.inR]; out['SA_rev_in_force_conformance_commit_tau'] = [int(x.holds.sum()), int(len(x)), round(x.holds.mean() * 100, 3)]
REPO = __import__("os").environ["CIVIC_V2_REPO"]
tags = subprocess.run(['git', '-C', REPO, 'tag'], capture_output=True, text=True).stdout.split()
out['releases_109_vs_110'] = {'tags_total': len(tags), 'pre_release_tags_skipped': [t for t in tags if 'pre' in t], 'scanned': len([t for t in tags if 'pre' not in t]),
                              'irregular_name_included': [t for t in tags if not t.startswith('v2')]}
out['units_25_vs_controls_26'] = '25 harmonised units of the second coding = C1-C26 minus C3 (documented only, not coded) with C16+C17 as one unit (supersession), plus I3 (now absence record N5)'
out['26.5_vs_19.5'] = '26.5 %: any first decision (accept or reject) within 365 days, liveness cohort Oct 2022-Oct 2025 (S2.1); 19.5 %: cumulative incidence of acceptance within one year, items submitted since 2021 (competing risks, S2.7/Table S-regime)'
json.dump(out, open(os.path.join(H, 'res_e_numbers.json'), 'w', encoding='utf-8'), indent=1, default=str)
os.remove(os.path.join(H, 'tmp_c_rerun.json'))
print(json.dumps(out, indent=1, default=str))
