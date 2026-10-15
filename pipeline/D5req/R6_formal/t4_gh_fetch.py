# R6 task 4: second R(t) on content gates for GO and HPO.
# Fetches (a) branch protection / rules visible to a read-only token, (b) history of .github/workflows/*,
# (c) CODEOWNERS history, (d) for term-adding merges linked from sampled NTR tickets (W2 timelines):
# associated PR, head sha, workflow runs and commit statuses on the head sha.
# Token is read from env GITHUB_TOKEN and only sent as Authorization header to api.github.com. Never logged.
import json, os, sys, time, hashlib, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'gh_cache'); os.makedirs(CACHE, exist_ok=True)
W2 = os.path.join(HERE, '..', 'W2')
TOK = os.environ.get('GITHUB_TOKEN')
UA = 'pm-curation-rule-sets-research (contact via GitHub thieuanhvan)'
NREQ = [0]; MAXREQ = int(os.environ.get('R6_MAXREQ', '1800'))
REPOS = {'go': 'geneontology/go-ontology', 'hpo': 'obophenotype/human-phenotype-ontology'}

def get(path, accept='application/vnd.github+json'):
    key = hashlib.sha1(path.encode()).hexdigest()[:20]
    fp = os.path.join(CACHE, key + '.json')
    if os.path.exists(fp):
        return json.load(open(fp, encoding='utf-8'))
    if NREQ[0] >= MAXREQ:
        return {'_status': 'budget'}
    req = urllib.request.Request('https://api.github.com' + path, headers={'User-Agent': UA, 'Accept': accept, 'X-GitHub-Api-Version': '2022-11-28'})
    if TOK: req.add_header('Authorization', 'Bearer ' + TOK)
    NREQ[0] += 1
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode('utf-8') or 'null'); out = {'_status': r.status, 'body': body, 'link': r.headers.get('Link')}
    except urllib.error.HTTPError as e:
        out = {'_status': e.code, 'body': None, 'msg': e.read().decode('utf-8', 'ignore')[:300]}
    except Exception as e:
        return {'_status': 'err', 'msg': str(e)[:200]}
    out['_path'] = path
    json.dump(out, open(fp, 'w', encoding='utf-8'))
    time.sleep(0.15)
    return out

def paged(path, maxpages=20):
    res = []
    for p in range(1, maxpages + 1):
        sep = '&' if '?' in path else '?'
        r = get(f'{path}{sep}per_page=100&page={p}')
        b = r.get('body')
        if not isinstance(b, list) or not b: break
        res += b
        if len(b) < 100: break
    return res

def main():
    out = {}
    for sp, repo in REPOS.items():
        o = out[sp] = {'repo': repo}
        info = get(f'/repos/{repo}')
        db = (info.get('body') or {}).get('default_branch', 'master'); o['default_branch'] = db
        br = get(f'/repos/{repo}/branches/{db}')
        b = br.get('body') or {}
        o['branch_api'] = {'status': br['_status'], 'protected': b.get('protected'), 'protection': b.get('protection')}
        pr_ = get(f'/repos/{repo}/branches/{db}/protection'); o['protection_api_status'] = pr_['_status']
        rules = get(f'/repos/{repo}/rules/branches/{db}'); o['rules_api'] = {'status': rules['_status'], 'body': rules.get('body')}
        rs = get(f'/repos/{repo}/rulesets'); o['rulesets_api'] = {'status': rs['_status'], 'n': len(rs.get('body') or []) if isinstance(rs.get('body'), list) else None}
        # workflow + CODEOWNERS history (commits touching the path)
        wf = paged(f'/repos/{repo}/commits?path=.github/workflows&sha={db}')
        o['workflow_commits'] = [{'sha': c['sha'], 'date': c['commit']['committer']['date'], 'msg': c['commit']['message'].split('\n')[0][:120]} for c in wf]
        for pth in ['.github/CODEOWNERS', 'CODEOWNERS', 'docs/CODEOWNERS', '.travis.yml']:
            cc = paged(f'/repos/{repo}/commits?path={pth}&sha={db}', 5)
            o['commits_' + pth] = [{'sha': c['sha'], 'date': c['commit']['committer']['date'], 'msg': c['commit']['message'].split('\n')[0][:120]} for c in cc]
        # contents of workflow dir at each workflow commit (tree listing of .github/workflows)
        snaps = []
        for c in o['workflow_commits']:
            t = get(f'/repos/{repo}/contents/.github/workflows?ref={c["sha"]}')
            files = [f['name'] for f in (t.get('body') or []) if isinstance(t.get('body'), list)]
            snaps.append({'sha': c['sha'], 'date': c['date'], 'files': files})
        o['workflow_snapshots'] = snaps
        # term-adding merges linked from sampled NTR tickets
        units = {}
        for l in open(os.path.join(W2, f'tl_w2_{sp}.jsonl'), encoding='utf-8'):
            t = json.loads(l)
            if t.get('s') != 'closed' and not t.get('x'): continue
            for e in t['events']:
                s = e.get('src')
                if s and s.get('pr') and s.get('repo') == repo and s.get('merged'):
                    units.setdefault(('pr', s['n']), {'ticket': t['n'], 'kind': 'pr_xref', 'merged': s['merged']})
                if e['ev'] == 'closed' and e.get('commit'):
                    units.setdefault(('commit', e['commit']), {'ticket': t['n'], 'kind': 'closed_by_commit', 't': e['t']})
        o['n_units_raw'] = len(units)
        rows = []
        prs_done = set()
        for (k, v), meta in list(units.items())[:300]:
            row = dict(meta)
            if k == 'commit':
                ap = get(f'/repos/{repo}/commits/{v}/pulls')
                pl = [p for p in (ap.get('body') or []) if isinstance(ap.get('body'), list) and p.get('merged_at')]
                if pl:
                    p = pl[0]; row.update(pr=p['number'], head=p['head']['sha'], merged_at=p['merged_at'], base=p['base']['ref'])
                else:
                    cm = get(f'/repos/{repo}/commits/{v}')
                    cb = cm.get('body') or {}
                    row.update(pr=None, head=v, merged_at=((cb.get('commit') or {}).get('committer') or {}).get('date'), direct_push=True, parents=len(cb.get('parents') or []))
            else:
                p = get(f'/repos/{repo}/pulls/{v}').get('body') or {}
                if not p: continue
                row.update(pr=v, head=p['head']['sha'], merged_at=p.get('merged_at'), base=p['base']['ref'])
            if row.get('pr') in prs_done and row.get('pr') is not None: continue
            prs_done.add(row.get('pr'))
            h = row['head']
            runs = get(f'/repos/{repo}/actions/runs?head_sha={h}&per_page=50')
            rb = runs.get('body') or {}
            row['runs'] = [{'path': r.get('path'), 'name': r.get('name'), 'event': r.get('event'), 'conclusion': r.get('conclusion'), 'created': r.get('created_at')} for r in rb.get('workflow_runs', [])]
            st = get(f'/repos/{repo}/commits/{h}/status')
            sb = st.get('body') or {}
            row['status_state'] = sb.get('state'); row['statuses'] = [{'context': s.get('context'), 'state': s.get('state'), 'created': s.get('created_at')} for s in sb.get('statuses', [])]
            if not row['runs']:
                cr = get(f'/repos/{repo}/commits/{h}/check-runs?per_page=50')
                cb = cr.get('body') or {}
                row['check_runs'] = [{'name': c.get('name'), 'app': (c.get('app') or {}).get('slug'), 'conclusion': c.get('conclusion')} for c in cb.get('check_runs', [])]
            rows.append(row)
        o['units'] = rows
    out['_requests_this_run'] = NREQ[0]
    json.dump(out, open(os.path.join(HERE, 't4_gh_raw.json'), 'w', encoding='utf-8'), indent=1)
    print('requests', NREQ[0], {sp: len(out[sp]['units']) for sp in REPOS})

if __name__ == '__main__':
    main()
