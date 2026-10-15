import pandas as pd
o=pd.read_pickle('objs.pkl'); d=o['dec']
for lab,(a,b) in {'pre':('2023-09-01','2025-04-01'),'post':('2025-04-01','2026-10-01')}.items():
    x=d[(d.t>=a)&(d.t<b)]
    for k in ['rej','wd','acc']:
        y=x[x.kind==k]; 
        if len(y)==0: continue
        print(lab,k,len(y),'rejectors',y.u.nunique(),'top1 share',round(y.u.value_counts().iloc[0]/len(y),2),'top day share',round(y.t.dt.date.value_counts().iloc[0]/len(y),2),'med ttd',round(y.ttd.median(),1), 'item age>365d share', round((y.ttd>365).mean(),2))
r=o['rdec']
for lab,(a,b) in {'pre':('2019-02-01','2022-04-01'),'post':('2022-05-01','2024-12-31')}.items():
    x=r[(r.t>=a)&(r.t<b)]
    for k in ['rej','wd']:
        y=x[x.kind==k]; print('REV',lab,k,len(y),'deciders',y.u.nunique(),'top day share',round(y.t.dt.date.value_counts().iloc[0]/len(y),2),'acts',y.act_id.nunique())
