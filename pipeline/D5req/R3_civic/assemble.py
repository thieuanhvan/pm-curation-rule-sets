# Merge per-task results into results_r3_civic.json (+ web/source facts for T7).
import json
R = {f't{i}': json.load(open(f'res_r3_t{i}.json')) for i in (1, 2, 3, 4, 5, 6)}
R['t7_facts'] = {
 'civic_release_files': {'checked': '2026-10-07 HTTP HEAD, read-only', 'HTTP_200': [
   'https://civicdb.org/downloads/nightly/nightly-AcceptedAndSubmittedClinicalEvidenceSummaries.tsv',
   'https://civicdb.org/downloads/nightly/nightly-AcceptedAndSubmittedAssertionSummaries.tsv',
   'https://civicdb.org/downloads/01-Oct-2026/01-Oct-2026-AcceptedAndSubmittedClinicalEvidenceSummaries.tsv',
   'https://civicdb.org/downloads/01-Sep-2026/01-Sep-2026-AcceptedAndSubmittedClinicalEvidenceSummaries.tsv'],
   'source': 'griffithlab/civic-v2 server/app/jobs/generate_tsvs.rb (tsvs_to_generate lists AcceptedAndSubmittedEvidenceItemTsvFormatter and AcceptedAndSubmittedAssertionTsvFormatter), commit 0488d61 (2026-09-25)'},
 'coi_scope': {'commit': '0488d61aeb0a5c45d2a1a7edc114ac085942939f',
   'requires_valid_COI': ['server/app/graphql/mutations/accept_revisions.rb (authorized?: editor + has_valid_coi_statement?)',
                          'server/app/graphql/mutations/reject_revisions.rb (others\' revisions: editor + has_valid_coi_statement?)',
                          'server/app/graphql/mutations/approve_assertion.rb (has_valid_coi_statement?)'],
   'no_COI_check': ['server/app/graphql/mutations/moderate_evidence_item.rb (editor role; no self-acceptance; submitter may reject own)',
                    'server/app/graphql/mutations/moderate_assertion.rb (editor role)'],
   'definition': 'server/app/models/user.rb has_valid_coi_statement?: most recent statement present and not expired'},
 'bot_flag_sample_api': 'cache/flags_sample.json: 12 random Aug-2021 bot flags, all state RESOLVED in the database, no comment text, no FLAG_RESOLVED event in the public event history (2 read-only requests, cache/requests.log)'}
json.dump(R, open('results_r3_civic.json', 'w'), indent=1, default=str); print('ok')
