# R6 task 1: systematic, reproducible code scan for enforced controls in CIViC (v1 civic-server, v2 civic-v2).
# Usage: python t1_code_scan.py <path-to-civic-v2-clone> <path-to-civic-server-clone>
# Clones: git clone --no-checkout https://github.com/griffithlab/civic-v2.git ; same for civic-server.
# Algorithm (see notes.md, Algorithm 1):
#  1. Snapshots S: v2 = every release tag (ordered by tag date; first deployed tag v2.0.0);
#     v1 = last master commit of every month (v1 had no release tags; deployment was continuous, so tau_c(v1) = commit month).
#  2. Control-relevant files F(s): mutations, policies, activities/actions, moderated models, jobs, scheduled_tasks.yml.
#  3. Extractors produce signatures sigma = (kind, file-stem, normalised key):
#       GUARD   raise GraphQL::ExecutionError "msg" (v2) / Pundit policy method body (v1)
#       ROLE    Role.user_is_at_least_a?(_, :role) and editor?/admin? checks
#       ARGREQ  argument :x ... required: true / validates length minimum N
#       AUTO    status := literal assigned outside a mutation (models/activities/actions/jobs) -> transition without human decision
#       SCHED   scheduled task entry (class, cron) + whether the job writes status of a moderated object
#       VALID   model validations on moderated object types
#  4. tau_c(release) = first snapshot containing sigma; removal = first later snapshot without it;
#     tau_c(commit) = first commit adding the key string on that path (git log -S, reverse).
#  5. Stage map by rule table (STAGE_RULES) on file stem and key; controls = signatures that can refuse or perform a
#     state transition of a moderated object (item, revision, flag, assertion); others = 'infrastructure'.
import subprocess, sys, re, json, os, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
V2, V1 = sys.argv[1], sys.argv[2]

def git(repo, *a):
    return subprocess.run(['git', '-C', repo] + list(a), capture_output=True, text=True, encoding='utf-8', errors='replace').stdout

def snapshots_v2():
    out = []
    for l in git(V2, 'for-each-ref', '--sort=creatordate', '--format=%(refname:short)|%(creatordate:iso-strict)|%(objectname)', 'refs/tags').splitlines():
        n, d, sha = l.split('|');
        if 'pre' in n: continue
        out.append({'id': n, 'date': d[:10], 'ref': n})
    return out

def snapshots_v1():
    out = []; seen = set()
    for l in git(V1, 'log', '--first-parent', '--format=%H|%cI', 'HEAD').splitlines():
        sha, d = l.split('|'); m = d[:7]
        if m in seen: continue
        seen.add(m); out.append({'id': 'v1@' + m, 'date': d[:10], 'ref': sha})
    return sorted(out, key=lambda s: s['date'])

V2DIRS = ['server/app/graphql/mutations/', 'server/app/models/activities/', 'server/app/models/actions/', 'server/app/jobs/', 'server/app/policies/']
V2MODELS = ['evidence_item', 'revision', 'flag', 'assertion', 'source_suggestion', 'revision_set', 'conflict_of_interest_statement', 'role', 'user']
V1DIRS = ['app/policies/', 'app/models/actions/', 'app/jobs/', 'app/controllers/']
V1MODELS = ['evidence_item', 'suggested_change', 'flag', 'assertion', 'source_suggestion', 'conflict_of_interest_statement', 'user']

def files_at(repo, ref, dirs, models, prefix):
    res = {}
    for l in git(repo, 'ls-tree', '-r', ref).splitlines():
        meta, path = l.split('\t'); sha = meta.split()[2]
        if not path.endswith(('.rb', '.yml')): continue
        if any(path.startswith(d) for d in dirs) or path in [f'{prefix}app/models/{m}.rb' for m in models] or path.endswith('config/scheduled_tasks.yml'):
            res[path] = sha
    return res

BLOB = {}
def blob(repo, sha):
    if sha not in BLOB:
        BLOB[sha] = git(repo, 'cat-file', '-p', sha)
    return BLOB[sha]

def norm(s):
    s = re.sub(r'#\{[^}]*\}', '<x>', s); s = re.sub(r'\s+', ' ', s).strip(); return s[:140]

MOD_OBJ = re.compile(r'EvidenceItem|Revision|SuggestedChange|Flag|Assertion|SourceSuggestion|evidence_item|revision|suggested_change|flag|assertion', re.I)

def extract(path, text, ver):
    stem = os.path.basename(path).rsplit('.', 1)[0]
    sigs = set()
    if path.endswith('scheduled_tasks.yml'):
        cur = None
        for line in text.splitlines():
            m = re.match(r'^(\w+):\s*$', line)
            if m: cur = m.group(1)
            m = re.match(r'^\s+class:\s*[\'"]?(\w+)', line)
            if m and cur: sigs.add(('SCHED', 'scheduled_tasks', cur + '->' + m.group(1)))
        return sigs
    for m in re.finditer(r'''raise\s+GraphQL::ExecutionError,\s*(["'])(.*?)\1''', text):
        sigs.add(('GUARD', stem, norm(m.group(2))))
    for m in re.finditer(r'''raise\s+StandardError,\s*(["'])(.*?)\1''', text):
        sigs.add(('GUARD', stem, norm(m.group(2))))
    for m in re.finditer(r'user_is_at_least_a\?\([^,]+,\s*:(\w+)\)', text):
        sigs.add(('ROLE', stem, 'at_least:' + m.group(1)))
    for m in re.finditer(r'(valid_coi_statement|most_recent_conflict_of_interest_statement|coi_valid|conflict_of_interest)', text):
        sigs.add(('ROLE', stem, 'coi:' + m.group(1)))
    for m in re.finditer(r'argument\s+:(\w+),\s*[^\n]*?required:\s*true[^\n]*(?:\n[^\n]*validates:\s*\{\s*length:\s*\{\s*minimum:\s*(\d+))?', text):
        if re.search(r'comment|note|reason|justif', m.group(1)):
            sigs.add(('ARGREQ', stem, m.group(1) + (':min' + m.group(2) if m.group(2) else '')))
    for m in re.finditer(r'argument\s+:(\w+)[^\n]*\n?[^\n]*validates:\s*\{\s*length:\s*\{\s*minimum:\s*(\d+)', text):
        sigs.add(('ARGLEN', stem, m.group(1) + ':min' + m.group(2)))
    if '/mutations/' not in path and '/policies/' not in path and '/controllers/' not in path:
        for m in re.finditer(r'status\s*(?:=|:)\s*[\'"](\w+)[\'"]', text):
            sigs.add(('AUTO', stem, 'status->' + m.group(1)))
        for m in re.finditer(r'(\w+)\.(?:update|update!|update_all|update_columns)\(\s*status:\s*[\'"](\w+)[\'"]', text):
            sigs.add(('AUTO', stem, 'status->' + m.group(2)))
    if '/policies/' in path:  # v1 Pundit: one signature per predicate method with body
        for m in re.finditer(r'def\s+(\w+\?)\s*\n(.*?)\n\s*end\b', text, re.S):
            sigs.add(('POLICY', stem, m.group(1) + ' :: ' + norm(m.group(2))))
    if re.search(r'app/models/\w+\.rb$', path):
        for m in re.finditer(r'^\s*(validates\w*\s+[^\n]+)', text, re.M):
            sigs.add(('VALID', stem, norm(m.group(1))))
    if '/jobs/' in path:
        writes = bool(re.search(r'status', text)) and bool(MOD_OBJ.search(text))
        sigs.add(('JOB', stem, 'writes_moderated_status' if writes else 'no_moderated_status'))
        if re.search(r'Flag|flag_entity|FlagEntity', text): sigs.add(('JOB', stem, 'raises_flags'))
        if re.search(r'Revision|suggest_revision|SuggestRevision', text): sigs.add(('JOB', stem, 'creates_revisions'))
    return sigs

def scan(repo, snaps, dirs, models, prefix, ver):
    presence = collections.defaultdict(list)
    for s in snaps:
        fs = files_at(repo, s['ref'], dirs, models, prefix)
        cur = set()
        for p, sha in fs.items():
            for sig in extract(p, blob(repo, sha), ver):
                cur.add(sig + (p,))
        for sig in cur: presence[sig].append(s['id'])
        s['n_files'] = len(fs)
    return presence

STAGE_RULES = [  # (regex on stem|key, stage)
    (r'supersed', 'exit (revision, automatic)'),
    (r'resolve_flag|flag_resolv|FlagResolv', 'flag resolution'),
    (r'flag_entity|raises_flags|FlagDuplicate', 'flag raising (intake of flags)'),
    (r'moderate_evidence_item|evidence_item_policy|moderate_assertion|assertion_policy|approve_assertion|revoke_approval|accept_revisions|reject_revisions|suggested_change_policy|update_suggested_change_status|update_source_suggestion_status|source_suggestion', 'decision'),
    (r'submit_|suggest_|add_|create_|creates_revisions', 'intake'),
    (r'scheduled_tasks', 'scheduled job'),
]
def stage_of(stem, key):
    s = stem + '|' + key
    for rx, st in STAGE_RULES:
        if re.search(rx, s, re.I): return st
    return 'other'

def first_commit(repo, path, key):
    k = key.split('->')[-1].split(' :: ')[0].replace('status->', '')
    k = re.sub(r'<x>.*', '', k).strip()[:60]
    if len(k) < 4: return None
    out = git(repo, 'log', '--reverse', '--format=%h|%cI', '-S', k, '--', path).splitlines()
    return out[0] if out else None

def main():
    s2, s1 = snapshots_v2(), snapshots_v1()
    rel = {r['tag']: r['published_at'][:10] for r in json.load(open(os.path.join(HERE, '..', 'W3', 'gh', 'civic_v2_release_dates.json'), encoding='utf-8'))['releases']} if os.path.exists(os.path.join(HERE, '..', 'W3', 'gh', 'civic_v2_release_dates.json')) else {}
    date2 = {s['id']: rel.get(s['id'], s['date']) for s in s2}; date1 = {s['id']: s['date'] for s in s1}
    p2 = scan(V2, s2, V2DIRS, V2MODELS, 'server/', 'v2'); p1 = scan(V1, s1, V1DIRS, V1MODELS, '', 'v1')
    rows = []
    for ver, pres, snaps, dmap, repo in [('v2', p2, s2, date2, V2), ('v1', p1, s1, date1, V1)]:
        order = [s['id'] for s in snaps]
        for sig, ids in pres.items():
            kind, stem, key, path = sig
            first = ids[0]; last = ids[-1]
            removed = order[order.index(last) + 1] if last != order[-1] else None
            rows.append({'ver': ver, 'kind': kind, 'stem': stem, 'key': key, 'path': path, 'stage': stage_of(stem, key),
                         'first_snapshot': first, 'tau_release': dmap[first], 'removed_at': dmap[removed] if removed else None,
                         'n_snapshots': len(ids)})
    # first commits only for rows that are candidate controls (not infrastructure)
    for r in rows:
        if r['kind'] in ('GUARD', 'ROLE', 'ARGREQ', 'ARGLEN', 'AUTO', 'POLICY') and r['stage'] != 'other':
            repo = V2 if r['ver'] == 'v2' else V1
            fc = first_commit(repo, r['path'], r['key'])
            r['tau_commit'] = fc.split('|')[1][:10] if fc else None; r['first_commit'] = fc.split('|')[0] if fc else None
    rows.sort(key=lambda r: (r['ver'], r['stage'], r['kind'], r['stem'], r['key']))
    meta = {'v2_snapshots': len(s2), 'v2_first': s2[0]['id'], 'v2_last': s2[-1]['id'], 'v1_snapshots': len(s1), 'v1_first': s1[0]['date'], 'v1_last': s1[-1]['date'],
            'v2_head': git(V2, 'rev-parse', '--short', 'HEAD').strip(), 'v1_head': git(V1, 'rev-parse', '--short', 'HEAD').strip(), 'n_signatures': len(rows)}
    json.dump({'meta': meta, 'signatures': rows}, open(os.path.join(HERE, 't1_signatures.json'), 'w', encoding='utf-8'), indent=1)
    print(json.dumps(meta)); print(collections.Counter((r['ver'], r['stage']) for r in rows))

if __name__ == '__main__':
    main()
