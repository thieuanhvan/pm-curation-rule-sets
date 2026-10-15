# Assemble R7 result files into results.json (aggregates only).
import os, json, glob
H = os.path.dirname(os.path.abspath(__file__)); out = {}
for f in sorted(glob.glob(os.path.join(H, 'res_*.json'))):
    out[os.path.basename(f)[4:-5]] = json.load(open(f, encoding='utf-8'))
out['coder2_controls'] = json.load(open(os.path.join(H, 'coder2_controls.json'), encoding='utf-8'))
out['github_requests'] = {'releases': 2, 't5_run1_network_error': 68, 't5_run2_stopped': 464, 't5_run3': 38, 'total': 572}
json.dump(out, open(os.path.join(H, 'results.json'), 'w', encoding='utf-8'), indent=1, default=str)
print(list(out.keys()))
