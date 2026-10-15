# R6 task 4b: GitHub retains check runs / workflow runs for about 400 days, so Definition 3 on the content gate is only
# measurable for merges inside the retention window. This script draws a seeded sample of NTR tickets closed inside the window
# (from the full population ../../D5k4/issues_<tag>.json), reads each ticket timeline, finds the closing commit / merged PR,
# and records workflow runs and commit statuses on the PR head (or the pushed commit). Also fetches the QC workflow file at its
# first and current version (job names = required-check contexts). Shares t4_gh_fetch.get() and its cache and budget.
import os, json, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t4_gh_fetch as G
H = os.path.dirname(os.path.abspath(__file__))
WIN0 = '2025-08-23'; NPER = int(os.environ.get('R6_NPER', '90'))
G.MAXREQ = int(os.environ.get('R6_MAXREQ', '1850'))
out = {}
raw = json.load(open(os.path.join(H, 't4_gh_raw.json'), encoding='utf-8'))
for tag, repo in G.REPOS.items():
    o = out[tag] = {}
    wc = raw[tag]['workflow_commits']
    first = wc[-1]['sha']; last = wc[0]['sha']
    for lab, sha in (('qc_first', first), ('qc_current', last)):
        r = G.get(f'/repos/{repo}/contents/.github/workflows/qc.yml?ref={sha}')
        txt = r.get('body') if isinstance(r.get('body'), str) else None
        if txt is None and r.get('_status') == 200 and isinstance(r.get('body'), dict):
            import base64; txt = base64.b64decode(r['body'].get('content', '')).decode('utf-8', 'ignore')
        o[lab] = {'sha': sha[:10], 'status': r.get('_status'), 'jobs': [l.strip()[:-1] for l in (txt or '').split('\n') if l.startswith('  ') and not l.startswith('   ') and l.strip().endswith(':')],
                  'on': [l.strip() for l in (txt or '').split('\n') if l.startswith('  ') and ('push' in l or 'pull_request' in l)][:4]}
    pop = json.load(open(os.path.join(H, '..', '..', 'D5k4', f'issues_{tag}.json'), encoding='utf-8'))
    win = sorted([x['n'] for x in pop.values() if not x.get('pr') and x['s'] == 'closed' and (x.get('x') or '') >= WIN0])
    random.Random(20261007).shuffle(win); samp = win[:NPER]
    o['window_population'] = len(win); o['sampled'] = len(samp)
    rows = []
    for n in samp:
        tl = G.get(f'/repos/{repo}/issues/{n}/timeline?per_page=100')
        evs = tl.get('body') if isinstance(tl.get('body'), list) else []
        closes = [e for e in evs if e.get('event') == 'closed']
        fin = closes[-1] if closes else None
        prs = [e for e in evs if e.get('event') == 'cross-referenced' and ((e.get('source') or {}).get('issue') or {}).get('pull_request')
               and (((e.get('source') or {}).get('issue') or {}).get('repository') or {}).get('full_name') == repo
               and (((e.get('source') or {}).get('issue') or {}).get('pull_request') or {}).get('merged_at')]
        row = {'ticket_closed': (fin or {}).get('created_at'), 'closed_by_commit': bool((fin or {}).get('commit_id')), 'state_reason': (fin or {}).get('state_reason')}
        unit = None
        if fin and fin.get('commit_id'):
            ap = G.get(f'/repos/{repo}/commits/{fin["commit_id"]}/pulls')
            pl = [p for p in (ap.get('body') or []) if isinstance(ap.get('body'), list) and p.get('merged_at')]
            unit = {'pr': pl[0]['number'], 'head': pl[0]['head']['sha'], 'merged_at': pl[0]['merged_at']} if pl else {'pr': None, 'head': fin['commit_id'], 'merged_at': fin.get('created_at'), 'direct_push': True}
        elif prs:
            p = prs[-1]['source']['issue']
            pr = G.get(f'/repos/{repo}/pulls/{p["number"]}').get('body') or {}
            if pr: unit = {'pr': pr['number'], 'head': pr['head']['sha'], 'merged_at': pr.get('merged_at')}
        if unit is None and fin:
            # fallback: last commit in this repository that references the ticket before (or up to 1 day after) the final close
            refs = [e for e in evs if e.get('event') == 'referenced' and e.get('commit_id') and f'/repos/{repo}/' in (e.get('commit_url') or '')
                    and (e.get('created_at') or '') <= (fin.get('created_at') or '')]
            if refs:
                c = refs[-1]['commit_id']
                ap = G.get(f'/repos/{repo}/commits/{c}/pulls')
                pl = [p for p in (ap.get('body') or []) if isinstance(ap.get('body'), list) and p.get('merged_at')]
                unit = ({'pr': pl[0]['number'], 'head': pl[0]['head']['sha'], 'merged_at': pl[0]['merged_at'], 'via': 'referenced'} if pl
                        else {'pr': None, 'head': c, 'merged_at': refs[-1].get('created_at'), 'direct_push': True, 'via': 'referenced'})
        row['unit'] = unit is not None
        row['via'] = (unit or {}).get('via', 'closing' if unit else None)
        if unit:
            runs = G.get(f'/repos/{repo}/actions/runs?head_sha={unit["head"]}&per_page=50').get('body') or {}
            row['runs'] = [{'path': r.get('path'), 'event': r.get('event'), 'conclusion': r.get('conclusion')} for r in runs.get('workflow_runs', [])]
            st = G.get(f'/repos/{repo}/commits/{unit["head"]}/status').get('body') or {}
            row['statuses'] = [{'context': s.get('context'), 'state': s.get('state')} for s in st.get('statuses', [])]
            row.update({k: unit.get(k) for k in ('merged_at', 'direct_push')}); row['has_pr'] = unit.get('pr') is not None
        rows.append(row)
    o['rows'] = rows
out['_requests_total_including_t4'] = G.NREQ[0]
json.dump(out, open(os.path.join(H, 't4b_window_raw.json'), 'w', encoding='utf-8'), indent=1)
print('requests this run', G.NREQ[0])
