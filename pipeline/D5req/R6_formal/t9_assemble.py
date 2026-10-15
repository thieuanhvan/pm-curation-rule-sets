# R6: assemble results.json from the per-task outputs (aggregates only).
import os, json, glob
H = os.path.dirname(os.path.abspath(__file__))
R = {}
for k, f in (('t1_controls', 'res_t1_controls.json'), ('t2_nonconforming', 'res_t2.json'), ('t3_service_position', 'res_t3.json'),
             ('t4_content_gates', 'res_t4.json'), ('t5_did', 'res_t5.json'), ('t6_numbers', 'res_t6_numbers.json')):
    p = os.path.join(H, f)
    if os.path.exists(p): R[k] = json.load(open(p, encoding='utf-8'))
s = json.load(open(os.path.join(H, 't1_signatures.json'), encoding='utf-8'))
R['t1_scan_meta'] = s['meta']
w = os.path.join(H, 't4b_window_raw.json')
R['github_requests'] = {'cache_entries': len(glob.glob(os.path.join(H, 'gh_cache', '*.json'))),
                        'note': 'every API call is cached once; cache entries = requests made (t4 + t4b), well under 2,000'}
json.dump(R, open(os.path.join(H, 'results.json'), 'w', encoding='utf-8'), indent=1, default=str)
print(list(R), R['github_requests'])
