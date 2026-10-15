# A2 step 4: same discovery + DECLARE subset for GO / HPO term trackers (classified 100-ticket samples, D5k4b timelines)
# and Wikidata property proposals (wikitext signatures + vote templates from D5k4/wd raw pages; decision from wd_cases.json).
import json, os, re, hashlib, collections as C, numpy as np, pandas as pd, pm4py
OUT = 'out/'; RES = {}; rng = np.random.default_rng(20261007)
K4, K4B = '../../D5k4/', '../../D5k4b/'
def P(k, v): RES[k] = v; print(k, json.dumps(v, default=str)[:1500], flush=True)
def wilson(k, n, z=1.96):
    if n == 0: return [None, None, None, 0]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 4), round(c - h, 4), round(c + h, 4), n]

def discover(df, name):
    df = pm4py.format_dataframe(df, case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
    dfg, sa, ea = pm4py.discover_dfg(df)
    v = pm4py.get_variants(df); n = sum(v.values()); s = sorted(v.items(), key=lambda x: -x[1])
    cc = df.copy(); cc['prev'] = cc.groupby('case:concept:name')['concept:name'].shift(); cc = cc[cc['concept:name'] != cc['prev']].drop(columns='prev')
    v2 = pm4py.get_variants(cc); s2 = sorted(v2.items(), key=lambda x: -x[1])
    net, im, fm = pm4py.discover_petri_net_inductive(df, noise_threshold=0.2); pm4py.write_pnml(net, im, fm, OUT + f'imf_{name}.pnml')
    method = 'alignments' if n <= 200 else 'token_replay'
    try:
        if method == 'alignments': fit = pm4py.fitness_alignments(df, net, im, fm)['average_trace_fitness']; prec = pm4py.precision_alignments(df, net, im, fm)
        else: fit = pm4py.fitness_token_based_replay(df, net, im, fm)['log_fitness']; prec = pm4py.precision_token_based_replay(df, net, im, fm)
    except Exception as e: fit = prec = f'ERR {e}'
    P('discovery_' + name, {'cases': int(n), 'events': len(df), 'activities': df['concept:name'].value_counts().to_dict(),
        'top_edges': [(a + ' -> ' + b, c) for (a, b), c in sorted(dfg.items(), key=lambda x: -x[1])[:12]], 'start': sa, 'end': ea,
        'variants_distinct': len(s), 'top1': wilson(s[0][1], n), 'variants_selfloops_collapsed': len(s2),
        'top_variants_collapsed': [(' > '.join(k[:10]), c) for k, c in s2[:6]], 'imf': {'method': method, 'transitions': len(net.transitions), 'align_fitness': fit if isinstance(fit, str) else round(fit, 4), 'align_precision': prec if isinstance(prec, str) else round(prec, 4)},
        'process_tree': str(pm4py.discover_process_tree_inductive(df, noise_threshold=0.2))[:600]})
    return df

# ------------------------------------------------------------------ GO / HPO
def gh(tag):
    tl = json.load(open(K4B + f'tl_{tag}.json', encoding='utf-8')); rows = {r['n']: r for r in json.load(open(K4B + f'rows_{tag}_v2_all.json', encoding='utf-8'))}
    E = []
    for n, t in tl.items():
        n = int(n); cls = rows.get(n, {}).get('cls', 'UNCLEAR'); sub = t['sub']; case = f'{tag}#{n}'
        E.append((case, 'OPENED', t['c'], sub))
        closes = [i for i, e in enumerate(t['events']) if e['ev'] == 'closed']; last = closes[-1] if closes else None
        for i, e in enumerate(t['events']):
            k = e['ev']; a = None
            if k == 'commented': a = 'COMMENT_SUBMITTER' if e['actor'] == sub else ('COMMENT_BOT' if e.get('bot') else 'COMMENT_OTHER')
            elif k == 'assigned': a = 'ASSIGNED'
            elif k == 'labeled' and e['t'] > t['c']: a = 'LABELED_LATER'
            elif k == 'referenced' and e.get('commit'): a = 'COMMIT_REFERENCE'
            elif k == 'cross-referenced': a = 'PR_LINKED' if (e.get('src') or {}).get('pr') else 'ISSUE_LINKED'
            elif k == 'closed': a = f'CLOSED_{cls}' if i == last else 'CLOSED_INTERIM'
            elif k == 'reopened': a = 'REOPENED'
            elif k == 'renamed': a = 'RENAMED'
            if a and e['t']: E.append((case, a, e['t'], e['actor']))
    df = pd.DataFrame(E, columns=['case:concept:name', 'concept:name', 'time:timestamp', 'org:resource'])
    df['time:timestamp'] = pd.to_datetime(df['time:timestamp'], utc=True)
    df['ord'] = df['concept:name'].map(lambda a: 0 if a == 'OPENED' else (2 if a.startswith('CLOSED_') and a != 'CLOSED_INTERIM' else 1))
    df = df.sort_values(['case:concept:name', 'time:timestamp', 'ord']).drop(columns='ord').reset_index(drop=True)
    df.to_csv(OUT + f'{tag}_ticket_eventlog.csv', index=False)
    return df
for tag in ('go', 'hpo'):
    df = gh(tag); discover(df, tag)
    cases = {k: g.reset_index(drop=True) for k, g in df.groupby('case:concept:name')}; n = len(cases); R = {}
    def rep(name, act, ful, tra, tro, extra=None):
        R[name] = {'event_confidence': wilson(ful, act), 'activated_traces': tra, 'trace_confidence': wilson(tro, tra), 'vacuous_share': round(1 - tra / n, 3)}
        if extra: R[name].update(extra)
    # reasoned rejection: precedence(COMMENT_OTHER, CLOSED_REJ); four-eyes: closer != opener for ACC closures; implementation evidence before ACC close
    for d in ('CLOSED_ACC', 'CLOSED_REJ'):
        act = sum(1 for g in cases.values() if d in set(g['concept:name']))
        ok = sum(1 for g in cases.values() if d in set(g['concept:name']) and any(x in ('COMMENT_OTHER',) for x in g['concept:name'][:g['concept:name'].tolist().index(d)]))
        rep(f'precedence(COMMENT_OTHER, {d})', act, ok, act, ok)
        ok = 0; act2 = 0
        for g in cases.values():
            a = g['concept:name'].tolist()
            if d in a: act2 += 1; ok += g['org:resource'][a.index(d)] != g['org:resource'][0]
        rep(f'four-eyes: closer({d}) != opener', act2, ok, act2, ok)
    act = ok = 0
    for g in cases.values():
        a = g['concept:name'].tolist()
        if 'CLOSED_ACC' in a: act += 1; i = a.index('CLOSED_ACC'); ok += any(x in ('COMMIT_REFERENCE', 'PR_LINKED') for x in a[:i])
    rep('precedence(COMMIT_REFERENCE|PR_LINKED, CLOSED_ACC) [visible implementation trace]', act, ok, act, ok, {'note': 'commit-closure (closed event carrying a commit id) is folded into CLOSED_ACC and not counted here'})
    act = sum(1 for g in cases.values() if 'REOPENED' in set(g['concept:name'])); rep('response(REOPENED, CLOSED_final)', act, act, act, act, {'note': 'true by sample design (closed tickets only)'})
    act = ok = 0
    for g in cases.values():
        a = g['concept:name'].tolist(); act += 1; ok += 'ASSIGNED' in a
    rep('existence(ASSIGNED)', act, ok, act, ok)
    rep('response(OPENED, CLOSED_*)', n, n, n, n, {'note': 'vacuous by design: sample drawn among closed tickets; pending tickets have no timeline'})
    # time-to-close by presence of other-person comment / assignment (descriptive; n small, closed-only)
    ttd = {}
    for x in ('COMMENT_OTHER', 'ASSIGNED', 'PR_LINKED'):
        e1 = []; e0 = []
        for g in cases.values():
            a = g['concept:name'].tolist(); fin = [i for i, y in enumerate(a) if y.startswith('CLOSED_') and y != 'CLOSED_INTERIM']
            if not fin: continue
            dd = (g['time:timestamp'][fin[0]] - g['time:timestamp'][0]).total_seconds() / 86400
            (e1 if x in a[:fin[0]] else e0).append(dd)
        bs = [np.median(rng.choice(e1, len(e1))) - np.median(rng.choice(e0, len(e0))) for _ in range(1000)] if e1 and e0 else [np.nan]
        ttd[x] = {'n_with': len(e1), 'med_with': round(float(np.median(e1)), 1) if e1 else None, 'n_without': len(e0), 'med_without': round(float(np.median(e0)), 1) if e0 else None, 'diff_ci95': [round(float(np.nanpercentile(bs, 2.5)), 1), round(float(np.nanpercentile(bs, 97.5)), 1)]}
    R['time_to_close_by_presence_descriptive'] = ttd
    P('declare_' + tag, R)

# ------------------------------------------------------------------ Wikidata property proposals
ps = lambda s: 'u_' + hashlib.sha256((__import__("os").environ["P17_SALT"] + s.strip().lower().replace('_', ' ')).encode()).hexdigest()[:10] if s else None
M = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])}
TS = re.compile(r'(\d{1,2}):(\d{2}), (\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4}) \(UTC\)')
USER = re.compile(r'\[\[\s*(?:User|Benutzer|Utilisateur|Usuario|Utente|Gebruiker|Special:Contributions/)[: ]?([^|\]/#]+)', re.I)
SUP = re.compile(r'\{\{\s*(s|support|strong support|weak support|conditional support|pro|pour|ss|agree|st)\s*[|}]', re.I)
OPP = re.compile(r'\{\{\s*(o|oppose|strong oppose|weak oppose|contra|wo)\s*[|}]', re.I)
QST = re.compile(r'\{\{\s*(question|comment|c|neutral|wait|info|n)\s*[|}]', re.I)
cases = {c['id']: c for c in json.load(open(K4 + 'wd_cases.json', encoding='utf-8'))}
E = []; stat = C.Counter(); seen_pages = set()
for f in sorted(os.listdir(K4 + 'wd')):
    for p in json.load(open(K4 + 'wd/' + f, encoding='utf-8')):
        cid = p['t'][27:]; c = cases.get(cid)
        if not c or cid in seen_pages: continue
        seen_pages.add(cid)
        body = p['c'].split(';{{int:Talk}}')[-1] if ';{{int:Talk}}' in p['c'] else p['c'].split('{{int:Talk}}')[-1]
        for line in body.split('\n'):
            for m in TS.finditer(line):
                t = pd.Timestamp(year=int(m.group(5)), month=M[m.group(4)] + 1, day=int(m.group(3)), hour=int(m.group(1)), minute=int(m.group(2)), tz='UTC')
                us = USER.findall(line[:m.start()]); u = ps(us[-1]) if us else None
                a = 'VOTE_SUPPORT' if SUP.search(line) else 'VOTE_OPPOSE' if OPP.search(line) else 'COMMENT'
                E.append([cid, a, t, u]); stat[a] += 1
                break  # one event per signed line
        E.append([cid, 'PROPOSED', pd.Timestamp(c['arr'], unit='ms', tz='UTC'), c['prop']])
        if c['dec']:
            lab = {'done': 'CREATED', 'notdone': 'NOT_DONE', 'withdrawn': 'WITHDRAWN'}.get(c['kind'])
            if lab: E.append([cid, lab, pd.Timestamp(c['dec'], unit='ms', tz='UTC'), c['decU']])
wd = pd.DataFrame(E, columns=['case:concept:name', 'concept:name', 'time:timestamp', 'org:resource'])
# drop the closing signature duplicated as COMMENT (same case, same minute, same user as decision)
dec = wd[wd['concept:name'].isin(['CREATED', 'NOT_DONE', 'WITHDRAWN'])][['case:concept:name', 'time:timestamp', 'org:resource']]
key = set(map(tuple, dec.values.tolist()))
wd = wd[~((wd['concept:name'].isin(['COMMENT', 'VOTE_SUPPORT', 'VOTE_OPPOSE'])) & wd[['case:concept:name', 'time:timestamp', 'org:resource']].apply(tuple, axis=1).isin(key))]
# drop the proposer's opening signature (same minute as PROPOSED)
prop = set(map(tuple, wd[wd['concept:name'] == 'PROPOSED'][['case:concept:name', 'time:timestamp']].values.tolist()))
wd = wd[~((wd['concept:name'] == 'COMMENT') & wd[['case:concept:name', 'time:timestamp']].apply(tuple, axis=1).isin(prop))]
wd['ord'] = wd['concept:name'].map({'PROPOSED': 0, 'CREATED': 2, 'NOT_DONE': 2, 'WITHDRAWN': 2}).fillna(1)
wd = wd.sort_values(['case:concept:name', 'time:timestamp', 'ord']).drop(columns='ord').reset_index(drop=True)
wd.to_csv(OUT + 'wikidata_proposal_eventlog.csv', index=False)
P('wd_parse', {'signed_lines_by_type': dict(stat), 'cases': wd['case:concept:name'].nunique(), 'events': len(wd)})
discover(wd.copy(), 'wikidata')
WC = {k: g.reset_index(drop=True) for k, g in wd.groupby('case:concept:name')}; R = {}; n = len(WC)
def rep(name, act, ful, extra=None):
    R[name] = {'trace_confidence': wilson(ful, act), 'vacuous_share': round(1 - act / n, 3)}
    if extra: R[name].update(extra)
def before(g, d, xs):
    a = g['concept:name'].tolist(); i = a.index(d); return any(x in xs for x in a[:i])
for d, xs, lab in (('CREATED', ('VOTE_SUPPORT',), 'precedence(VOTE_SUPPORT, CREATED) [consensus trace]'), ('NOT_DONE', ('VOTE_OPPOSE', 'COMMENT'), 'precedence(VOTE_OPPOSE|COMMENT, NOT_DONE) [reasoned rejection]'),
                   ('CREATED', ('VOTE_OPPOSE',), 'responded: CREATED despite >=1 VOTE_OPPOSE before (descriptive)')):
    act = [g for g in WC.values() if d in set(g['concept:name'])]; ok = sum(before(g, d, xs) for g in act); rep(lab, len(act), ok)
act = [g for g in WC.values() if 'CREATED' in set(g['concept:name'])]
ok2 = sum(sum(1 for x in g['concept:name'][:g['concept:name'].tolist().index('CREATED')] if x == 'VOTE_SUPPORT') >= 2 for g in act); rep('existence2(VOTE_SUPPORT) before CREATED', len(act), ok2)
ok = sum(g['org:resource'][g['concept:name'].tolist().index('CREATED')] != g['org:resource'][0] for g in act if g['org:resource'][0] and g['org:resource'][g['concept:name'].tolist().index('CREATED')]); kn = sum(1 for g in act if g['org:resource'][0] and g['org:resource'][g['concept:name'].tolist().index('CREATED')])
rep('four-eyes: creator != proposer', kn, ok)
ok = sum((g['time:timestamp'][g['concept:name'].tolist().index('CREATED')] - g['time:timestamp'][0]).days >= 7 for g in act); rep('min-duration: CREATED >= 7 days after PROPOSED', len(act), ok)
pend = [g for g in WC.values() if not any(x in ('CREATED', 'NOT_DONE', 'WITHDRAWN') for x in g['concept:name'])]
rep('response(PROPOSED, CREATED|NOT_DONE|WITHDRAWN) [timestamp found]', n, n - len(pend), {'note': 'decided proposals without parsable closing signature count as violations here'})
# voting effect on time-to-decision (decided only, descriptive): number of support votes before decision
rows = []
for g in WC.values():
    a = g['concept:name'].tolist(); fin = [i for i, x in enumerate(a) if x in ('CREATED', 'NOT_DONE', 'WITHDRAWN')]
    if not fin: continue
    i = fin[-1]; rows.append({'out': a[i], 'd': (g['time:timestamp'][i] - g['time:timestamp'][0]).total_seconds() / 86400, 'opp': 'VOTE_OPPOSE' in a[:i], 'nsup': a[:i].count('VOTE_SUPPORT')})
rr = pd.DataFrame(rows)
R['outcome_by_oppose_vote'] = {f'oppose={k}': {'n': int(len(g)), 'created_share': wilson(int((g['out'] == 'CREATED').sum()), len(g)), 'med_days': round(float(g['d'].median()), 1)} for k, g in rr.groupby('opp')}
P('declare_wikidata', R)
json.dump(RES, open(OUT + 'other_cases.json', 'w'), indent=1, default=str)
