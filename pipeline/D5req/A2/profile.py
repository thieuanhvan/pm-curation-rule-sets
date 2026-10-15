import json, os, collections as C
B='../../D5b/'
ev={};raw=0
for f in sorted(os.listdir(B+'cache')):
    for e in json.load(open(B+'cache/'+f,encoding='utf-8')):
        raw+=1; ev[e['id']]=e
ev=list(ev.values()); print('raw',raw,'unique',len(ev))
print('actions',len(set(e['action'] for e in ev)))
bot=[e for e in ev if (e.get('originatingUser') or {}).get('id')==385]
print('bot385',len(bot),C.Counter(e['action'] for e in bot).most_common(), C.Counter((e['subject'] or {}).get('__typename') for e in bot).most_common(5), min(e['createdAt'] for e in bot), max(e['createdAt'] for e in bot))
c=C.Counter((e['action'],(e.get('subject') or {}).get('__typename'),(e.get('originatingObject') or {}).get('__typename')) for e in ev)
for k,v in sorted(c.items(),key=lambda x:-x[1]): print(k,v)
print('nouser',sum(1 for e in ev if not e.get('originatingUser')),'noorg',sum(1 for e in ev if not e.get('organization')))
