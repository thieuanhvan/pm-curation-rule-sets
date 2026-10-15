# R3 task 3: HPO bulk-closure days (>= 20 term-request closures on one UTC day, population of labelled tickets) and the
# throughput ratio rho for arrivals 2023-25 with and without those closures. Sample = ../W2 (200 tickets). No network.
import json, collections, numpy as np, pandas as pd
rng = np.random.default_rng(20261007); B = 2000; R = {}
for tag in ('hpo', 'go'):
    iss = json.load(open(f'../../D5k4/issues_{tag}.json')); d = pd.DataFrame([v for v in iss.values() if not v.get('pr')])
    d['xT'] = pd.to_datetime(d.x, utc=True); d['cT'] = pd.to_datetime(d.c, utc=True)
    cl = d[d.s == 'closed']; day = cl.groupby(cl.xT.dt.date).size()
    burst = set(day[day >= 20].index)
    byY = {int(y): {'closures': int((cl.xT.dt.year == y).sum()), 'bulk_days': int(sum(1 for k in burst if k.year == y)), 'closures_on_bulk_days': int(sum(day[k] for k in burst if k.year == y))} for y in range(2016, 2027)}
    f = d[d.cT >= '2016']; W0, W1 = pd.Timestamp('2023-01-01', tz='UTC'), pd.Timestamp('2026-01-01', tz='UTC')
    arr = int(((f.cT >= W0) & (f.cT < W1)).sum()); inW = (f.s == 'closed') & (f.xT >= W0) & (f.xT < W1)
    onb = f.xT.dt.date.isin(burst)
    pop = {'arrivals_2023_25': arr, 'closures_2023_25': int(inW.sum()), 'rho_all': round(inW.sum() / arr, 3), 'rho_excl_bulk_closures': round((inW & ~onb).sum() / arr, 3),
           'bulk_closures_2023_25': int((inW & onb).sum())}
    stock = {str(q.date()): int(((f.cT < q) & ((f.s == 'open') | (f.xT >= q))).sum()) for q in pd.date_range('2022-01-01', '2025-07-01', freq='QS', tz='UTC')}
    oc = pd.DataFrame(json.load(open(f'../W2/outcomes_w2_{tag}.json'))); oc['openT'] = pd.to_datetime(oc.open, utc=True); oc['closeT'] = pd.to_datetime(oc.close, utc=True)
    oc['bulk'] = oc.closeT.dt.date.isin(burst) & oc.cls.notna()
    def rho(s, mode):
        a = ((s.openT >= W0) & (s.openT < W1)); dec = s.state.eq('closed') & (s.closeT >= W0) & (s.closeT < W1)
        if mode == 'all': return dec.sum() / a.sum()
        if mode == 'excl_bulk_as_decision': return (dec & ~s.bulk).sum() / a.sum()
        if mode == 'drop_bulk_tickets': return (dec & ~s.bulk).sum() / (a & ~s.bulk).sum()
    samp = {}
    for m in ('all', 'excl_bulk_as_decision', 'drop_bulk_tickets'):
        bs = [rho(oc.iloc[rng.integers(0, len(oc), len(oc))], m) for _ in range(B)]
        samp[m] = [round(float(rho(oc, m)), 3), round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]
    b = oc[oc.bulk]; nb = oc[oc.cls.notna() & ~oc.bulk]; w = lambda s: s[(s.closeT >= W0) & (s.closeT < W1)]
    samp['sample_bulk_closed'] = int(len(b)); samp['sample_bulk_closed_2023_25'] = int(len(w(b)))
    samp['cls_bulk'] = dict(collections.Counter(b.cls)); samp['cls_nonbulk'] = dict(collections.Counter(nb.cls))
    samp['corroborated_ACC_bulk'] = [int(b[b.cls == 'ACC'].corroborated.sum()), int((b.cls == 'ACC').sum())]
    samp['corroborated_ACC_nonbulk'] = [int(nb[nb.cls == 'ACC'].corroborated.sum()), int((nb.cls == 'ACC').sum())]
    samp['median_age_at_close_d'] = {'bulk': float(b.ttdD.median()) if len(b) else None, 'nonbulk': float(nb.ttdD.median())}
    cnt = b.closer.value_counts(); samp['bulk_closers_ge5_rule'] = 'fewer than five accounts' if len(cnt) < 5 else int(len(cnt))
    R[tag] = {'bulk_rule': '>=20 closures of labelled term-request tickets on one UTC day', 'by_year': byY, 'population_rho_2023_25_frame2016': pop, 'stock_by_quarter_frame2016': stock, 'sample': samp}
json.dump(R, open('r3_t3_bursts.json', 'w'), indent=1); print(json.dumps(R)[:4000])
