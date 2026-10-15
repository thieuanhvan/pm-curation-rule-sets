import json
R=json.load(open('results_r3_causal.json'))
for e in ['E2022_rev_reason','E2025_eid_reason']:
    print('==',e)
    for c in ['rej_share','wd_share','wdsup_share','log_ttd','stock_growth','rej_per_md','acc_per_md','rej','acc_other','log_arr']:
        d=R[e]['did'][c]; es=R[e]['event_study'][c]
        print(f"{c:13s} DiD level {d['post']} slope {d.get('t_post')} | lvlonly {d.get(c) or R[e]['did'][c+'_levelonly']} | RI {R[e]['placebo'][c+'_ri']} | preslope {es['pre_slope_per_month_HAC']} | plc {R[e]['placebo'][c]}")
    for k in ['did_pre_MP_migration','did_rev_on_eid_only']:
        if k in R[e]: print(k, {c:v['post'] for c,v in R[e][k].items()})
    print('its_treated', {c:R[e]['its_treated'][c]['post'] for c in ['rej_pois','acc_other_pois','rej_share','wd_share','log_ttd']})
    print('prepost', json.dumps(R[e]['prepost_means']))
