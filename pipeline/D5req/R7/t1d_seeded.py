# R7 task 1d: seeded-control test of the R6 extractor (t1_code_scan.py, unchanged) on a COPY of civic-v2.
# The copy is a bare --shared clone (a local folder) with commit v9.9.9 = v2.7.6 + 5 planted guards + 3 decoys
# (see coder notes); this script diffs extractor output between v2.7.6 and v9.9.9 and scores hits / misses.
import sys, os, json, importlib.util
H = os.path.dirname(os.path.abspath(__file__))
SEED = sys.argv[1]
sys.argv = ['x', SEED, SEED]
spec = importlib.util.spec_from_file_location('scan', os.path.join(H, '..', 'R6_formal', 't1_code_scan.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
snaps = [{'id': 'v2.7.6', 'date': '2026-08-27', 'ref': 'v2.7.6'}, {'id': 'v9.9.9', 'date': '2026-10-07', 'ref': 'v9.9.9'}]
pres = m.scan(SEED, snaps, m.V2DIRS, m.V2MODELS, 'server/', 'v2')
new = [dict(kind=k, stem=s, key=key, path=p, stage=m.stage_of(s, key)) for (k, s, key, p), ids in pres.items() if ids == ['v9.9.9']]
gone = [dict(kind=k, stem=s, key=key) for (k, s, key, p), ids in pres.items() if ids == ['v2.7.6']]
PLANT = {'SEED1 policy method (Pundit accept?, age < 730 d)': ('evidence_item_policy', 'age_in_days'),
         'SEED2 mutation guard, double quotes (pending revision blocks acceptance)': ('moderate_evidence_item', 'SEED2'),
         'SEED3 model validation, custom-method style (validate :m)': ('evidence_item', 'seed3'),
         'SEED4 scheduled job writing evidence-item status (stale exit)': ('seed4_expire_stale_evidence|scheduled_tasks', 'rejected|Seed4'),
         'SEED5 guard, ExecutionError.new with single quotes': ('moderate_evidence_item', 'SEED5'),
         'DECOY1 commented-out guard': ('moderate_evidence_item', 'DECOY1'),
         'DECOY2 log string resembling a status assignment': ('notify_subscribers', 'status->accepted'),
         'DECOY3 guard on a non-moderated object (notification)': ('update_notification_status', 'DECOY3')}
import re
res = {}
for lab, (stem, key) in PLANT.items():
    hits = [n for n in new if re.search(stem, n['stem']) and re.search(key, n['key'], re.I)]
    res[lab] = {'extracted': bool(hits), 'signatures': [(h['kind'], h['stem'], h['key'][:80], h['stage']) for h in hits]}
out = {'new_signatures_total': len(new), 'removed_signatures_total': len(gone), 'planted': res,
       'unexplained_new': [(n['kind'], n['stem'], n['key'][:80], n['stage']) for n in new if not any(n['key'][:80] == s[2] and n['stem'] == s[1] for v in res.values() for s in v['signatures'])]}
json.dump(out, open(os.path.join(H, 'res_t1d_seeded.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps(out, indent=1))
