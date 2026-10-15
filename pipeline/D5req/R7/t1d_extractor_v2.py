# R7 task 1d (follow-up): revised extractor (Algorithm 1, step 3) addressing the seeded-test misses and decoy hits, then
# re-run on the seeded copy and on the two v1 snapshots where the second coder found controls the R6 scan missed.
# Changes vs R6 t1_code_scan.extract: strip Ruby comment lines; GUARD also matches ExecutionError.new('...') and custom
# *Error raises; VALID also matches `validate :method`; AUTO requires an assignment context (x.status = '..',
# update*(status: '..'), create/new(... status: '..')) and ignores where/find_by/logger lines; stage rules add
# exit (job writing a moderated status to a terminal value) and re-entry (status reset to submitted outside a mutation).
import sys, os, re, json, importlib.util
H = os.path.dirname(os.path.abspath(__file__))
SEED, V1 = sys.argv[1], sys.argv[2]
sys.argv = ['x', SEED, V1]
spec = importlib.util.spec_from_file_location('scan', os.path.join(H, '..', 'R6_formal', 't1_code_scan.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
old_extract = m.extract
def strip_comments(text):
    return '\n'.join('' if re.match(r'^\s*#', l) else l for l in text.splitlines())
def extract2(path, text, ver):
    if path.endswith('.rb'): text = strip_comments(text)
    sigs = {s for s in old_extract(path, text, ver) if s[0] != 'AUTO'}
    stem = os.path.basename(path).rsplit('.', 1)[0]
    for mm in re.finditer(r'''raise\s+GraphQL::ExecutionError\.new\(\s*(["'])(.*?)\1''', text): sigs.add(('GUARD', stem, m.norm(mm.group(2))))
    for mm in re.finditer(r'raise\s+(\w+(?:Error|Exception))(?:\.new)?\b', text):
        if mm.group(1) not in ('StandardError',) and 'GraphQL' not in mm.group(0): sigs.add(('GUARD', stem, 'raise:' + mm.group(1)))
    if re.search(r'app/models/\w+\.rb$', path):
        for mm in re.finditer(r'^\s*(validate\s+:\w+[^\n]*)', text, re.M): sigs.add(('VALID', stem, m.norm(mm.group(1))))
    if '/mutations/' not in path and '/policies/' not in path and '/controllers/' not in path:
        for line in text.splitlines():
            if re.search(r'logger|puts|Rails\.log', line): continue
            line = re.sub(r'(?:where|find_by|where\.not)\([^)]*\)', '', line)
            for mm in re.finditer(r'''\.status\s*=\s*['"](\w+)['"]''', line): sigs.add(('AUTO', stem, 'status->' + mm.group(1)))
            for mm in re.finditer(r'''(?:update|update!|update_all|update_columns|create|create!|new)\([^)]*status:\s*['"](\w+)['"]''', line): sigs.add(('AUTO', stem, 'status->' + mm.group(1)))
    return sigs
m.extract = extract2
m.STAGE_RULES = [(r'(job|expire|stale|scheduled).*status->(rejected|closed|expired|withdrawn)|^\w*expire\w*\|status->', 'exit (automatic)'),
                 (r'^(evidence_item|assertion)\|status->submitted', 're-entry (automatic)')] + m.STAGE_RULES
def run(repo, snaps, dirs, models, prefix, ver):
    pres = m.scan(repo, snaps, dirs, models, prefix, ver)
    return [dict(kind=k, stem=s, key=key, path=p, stage=m.stage_of(s, key), ids=ids) for (k, s, key, p), ids in pres.items()]
out = {}
rows = run(SEED, [{'id': 'v2.7.6', 'date': '', 'ref': 'v2.7.6'}, {'id': 'v9.9.9', 'date': '', 'ref': 'v9.9.9'}], m.V2DIRS, m.V2MODELS, 'server/', 'v2')
new = [r for r in rows if r['ids'] == ['v9.9.9']]
tests = {'SEED1': ('evidence_item_policy', 'age_in_days'), 'SEED2': ('moderate_evidence_item', 'SEED2'), 'SEED3': ('evidence_item', 'seed3'),
         'SEED4': ('seed4|scheduled', 'rejected|Seed4'), 'SEED5': ('moderate_evidence_item', 'SEED5'),
         'DECOY1': ('moderate_evidence_item', 'DECOY1'), 'DECOY2': ('notify_subscribers', 'status->accepted'), 'DECOY3': ('update_notification_status', 'DECOY3')}
out['seeded_v2_extractor'] = {k: [(r['kind'], r['stem'], r['key'][:70], r['stage']) for r in new if re.search(a, r['stem']) and re.search(b, r['key'], re.I)] for k, (a, b) in tests.items()}
out['seeded_v2_other_new'] = [(r['kind'], r['stem'], r['key'][:70], r['stage']) for r in new if not any(re.search(a, r['stem']) and re.search(b, r['key'], re.I) for a, b in tests.values())]
# v1 snapshots where coder 2 found missed controls
v1s = [{'id': 'v1@2016-06', 'date': '', 'ref': '79df8f24'}, {'id': 'v1@2020-06', 'date': '', 'ref': 'bb87f18e'}]
r1 = run(V1, v1s, m.V1DIRS, m.V1MODELS, '', 'v1')
out['v1_fit_stale_guard'] = [(r['kind'], r['stem'], r['key'][:70], r['stage'], r['ids']) for r in r1 if 'ChangeApplicationConflict' in r['key'] or 'SuggestedChangeError' in r['key']]
out['v1_reentry_auto'] = [(r['kind'], r['stem'], r['key'][:70], r['stage'], r['ids']) for r in r1 if r['kind'] == 'AUTO' and r['stem'] == 'evidence_item']
json.dump(out, open(os.path.join(H, 'res_t1d_extractor_v2.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps(out, indent=1))
