# R7 task 1c: fetch CIViC v2 GitHub release notes (bodies) into gh_cache/releases.json. Token (optional) from env GITHUB_TOKEN, never printed.
import os, json, urllib.request
H = os.path.dirname(os.path.abspath(__file__)); out = []; n = 0
for page in range(1, 6):
    req = urllib.request.Request(f'https://api.github.com/repos/griffithlab/civic-v2/releases?per_page=100&page={page}', headers={'Accept': 'application/vnd.github+json'})
    if os.environ.get('GITHUB_TOKEN'): req.add_header('Authorization', 'Bearer ' + os.environ['GITHUB_TOKEN'])
    d = json.load(urllib.request.urlopen(req)); n += 1
    out += [{'tag': r['tag_name'], 'published_at': r['published_at'], 'prerelease': r['prerelease'], 'name': r['name'], 'body': r['body'] or ''} for r in d]
    if len(d) < 100: break
json.dump({'requests': n, 'releases': out}, open(os.path.join(H, 'gh_cache', 'releases.json'), 'w', encoding='utf-8'), indent=1)
print(n, len(out))
