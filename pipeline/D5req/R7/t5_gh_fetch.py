# R7 task 5: GO merge gate over time (merged PRs to master + check runs of head) and HPO term_tracker_item feasibility.
# Token from env GITHUB_TOKEN (process only), sent only as Authorization header to api.github.com; never printed or stored.
# Raw responses cached in gh_cache/ (internal). Hard cap MAXREQ requests.
import os, json, hashlib, urllib.request, urllib.error, re, sys, random
H = os.path.dirname(os.path.abspath(__file__)); CD = os.path.join(H, 'gh_cache'); os.makedirs(CD, exist_ok=True)
MAXREQ = int(os.environ.get('R7_MAXREQ', '600')); NREQ = 0  # run 1: 68 requests (network error), run 2: 464 (stopped), run 3: R7_MAXREQ=45; total < 600
def get(path, accept='application/vnd.github+json'):
    global NREQ
    f = os.path.join(CD, hashlib.sha1((path + accept).encode()).hexdigest()[:20] + '.json')
    if os.path.exists(f): return json.load(open(f, encoding='utf-8'))
    if NREQ >= MAXREQ: return {'_status': 'cap'}
    req = urllib.request.Request('https://api.github.com' + path, headers={'Accept': accept, 'User-Agent': 'r7-audit', 'X-GitHub-Api-Version': '2022-11-28'})
    if os.environ.get('GITHUB_TOKEN'): req.add_header('Authorization', 'Bearer ' + os.environ['GITHUB_TOKEN'])
    o = None
    for attempt in range(3):
        NREQ += 1; open(os.path.join(CD, 'requests.log'), 'a').write('1' + chr(10))
        try:
            with urllib.request.urlopen(req, timeout=60) as r: o = {'_status': r.status, 'body': json.loads(r.read().decode('utf-8'))}
            break
        except urllib.error.HTTPError as e: o = {'_status': e.code, 'body': None}; break
        except Exception as e: o = {'_status': 'neterr', 'body': None}
    if o['_status'] == 'neterr': return o
    json.dump(o, open(f, 'w', encoding='utf-8')); return o
out = {}
# ---- GO: merged PRs into master, newest first, until merged before 2025-06-01
GO = 'geneontology/go-ontology'; prs = []
for page in range(1, 15):
    r = get(f'/repos/{GO}/pulls?state=closed&base=master&sort=updated&direction=desc&per_page=100&page={page}')
    b = r.get('body') or []
    prs += [{'n': p['number'], 'merged_at': p['merged_at'], 'head': p['head']['sha'], 'assoc': p.get('author_association'), 'updated': p['updated_at']} for p in b if p.get('merged_at')]
    if not b or min(p['updated_at'] for p in b) < '2025-06-01': break
prs = [p for p in prs if p['merged_at'] >= '2025-06-01']
for p in prs:
    path = f'/repos/{GO}/commits/{p["head"]}/check-runs?per_page=100'
    fc = os.path.join(CD, hashlib.sha1((path + 'application/vnd.github+json').encode()).hexdigest()[:20] + '.json')
    if not os.path.exists(fc): p['qc'] = 'not_fetched'; continue
    cr = get(path)
    runs = (cr.get('body') or {}).get('check_runs', []) if cr.get('_status') == 200 else None
    p['cr_status'] = cr.get('_status')
    if runs is None: p['qc'] = 'unknown'; continue
    q = [x for x in runs if x['name'] == 'ontology_qc']
    p['n_runs'] = len(runs)
    p['qc'] = 'success' if any(x['conclusion'] == 'success' for x in q) else ('failure' if any(x['conclusion'] in ('failure', 'cancelled', 'timed_out') for x in q) else ('pending' if q else 'missing'))
out['go_prs'] = [{k: v for k, v in p.items() if k != 'head'} for p in prs]
# ---- HPO: commits touching hp-edit.owl since 2025-08-01, sample 40, look for added term_tracker_item and new class declarations
HPO = 'obophenotype/human-phenotype-ontology'; cm = []
for page in range(1, 4):
    r = get(f'/repos/{HPO}/commits?path=src/ontology/hp-edit.owl&sha=master&since=2025-08-01T00:00:00Z&per_page=100&page={page}')
    b = r.get('body') or []; cm += [{'sha': c['sha'], 'date': c['commit']['committer']['date'], 'msg': c['commit']['message'][:200]} for c in b]
    if len(b) < 100: break
random.seed(20261007); samp = random.sample(cm, min(35, len(cm)))
for c in samp:
    d = get(f'/repos/{HPO}/commits/{c["sha"]}')
    fs = [f for f in ((d.get('body') or {}).get('files') or []) if f['filename'].endswith('hp-edit.owl')]
    patch = fs[0].get('patch') if fs else None
    c['patch_available'] = patch is not None
    if patch:
        add = [l for l in patch.splitlines() if l.startswith('+')]
        c['added_class_decl'] = sum(bool(re.search(r'Declaration\(Class\(', l)) for l in add)
        c['added_term_tracker'] = sum('term_tracker_item' in l or 'IAO_0000233' in l for l in add)
        c['tracker_issue_refs'] = len(set(re.findall(r'human-phenotype-ontology/issues/(\d+)', '\n'.join(add))))
    c['msg_issue_ref'] = bool(re.search(r'#\d+|issues/\d+', c['msg']))
    c.pop('msg'); c.pop('sha')
out['hpo_commits_total_since_2025-08'] = len(cm); out['hpo_sample'] = samp
out['requests_this_run'] = NREQ
json.dump(out, open(os.path.join(H, 'gh_cache', 't5_raw.json'), 'w', encoding='utf-8'), indent=1)
print('requests', NREQ, 'go merged PRs', len(prs), 'hpo commits', len(cm))
