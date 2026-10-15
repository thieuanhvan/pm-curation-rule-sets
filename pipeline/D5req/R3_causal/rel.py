import json
d=json.load(open('../W3/gh/civic_v2_release_dates.json',encoding='utf-8'))
for r in d['releases']:
    if r['published_at'][:7] in ('2023-09','2023-10','2023-11','2025-03','2025-04','2023-08'):
        print(r['tag'],r['published_at'],r['first_line'][:600].replace('\r',' ').replace('\n',' '))
print(min(r['published_at'] for r in d['releases']))
