# R3 T5: projection / OC-DFG comparison (van der Aalst 2019 convergence and divergence) for the CIViC evidence-item scope,
# plus the count reconciliation of revision objects (67,957 in the full OCEL vs 25,380 in Fig. 2b).
import pickle, json, collections as C, numpy as np, pandas as pd, pm4py
from pm4py.objects.ocel.obj import OCEL
R = {}
d = pickle.load(open('../A2/out/ocel_ei_hmac.pkl', 'rb'))
ev = d['events'][~d['events']['is_bot']]; rel = d['relations'][d['relations']['ocel:eid'].isin(set(ev['ocel:eid']))]
ob = d['objects'][d['objects']['ocel:oid'].isin(set(rel['ocel:oid']))]
ocel = OCEL(events=ev.copy(), objects=ob.copy(), relations=rel.copy())
# ---- revision count reconciliation
E = pd.read_pickle('../W3/w3_events_hmac.pkl')
rv = E[E.ot == 'Revision']
first = rv.drop_duplicates('oid').set_index('oid')
ei_rev = set(rv[rv.tt == 'EvidenceItem'].oid)
nonbot_ei_rev = set(rv[(rv.tt == 'EvidenceItem') & ~rv.bot].oid)
sugg_bot = set(rv[(rv.act == 'REVISION_SUGGESTED') & rv.bot].oid)
R['revision_counts'] = {'all_revision_objects_full_log': int(rv.oid.nunique()), 'by_target_type': first.tt.value_counts().to_dict(),
                        'on_evidence_items': len(ei_rev), 'on_evidence_items_with_any_nonbot_event(Fig2b scope)': len(nonbot_ei_rev),
                        'on_evidence_items_suggested_by_bot': len(ei_rev & sugg_bot),
                        'ocel_ei_excl_bot_revision_objects': int((ob['ocel:type'] == 'revision').sum())}
# ---- convergence: events related to more than one evidence item (duplicated by flattening)
ei_rel = rel[rel['ocel:type'] == 'evidence_item']
k = ei_rel.groupby('ocel:eid')['ocel:oid'].nunique()
R['convergence'] = {'events_with_evidence_item': int(len(k)), 'events_linked_to_>1_evidence_item': int((k > 1).sum()), 'max_items_per_event': int(k.max())}
# ---- divergence: directly-follows pairs in the flattened evidence-item log
fl = pm4py.ocel_flattening(ocel, 'evidence_item').sort_values(['case:concept:name', 'time:timestamp', 'ocel:eid'])
sub = rel[rel['ocel:type'].isin(['revision', 'comment', 'flag'])][['ocel:eid', 'ocel:oid', 'ocel:type']]
sub = sub.sort_values('ocel:type').drop_duplicates('ocel:eid')            # one sub-object per event (revision first)
m = dict(zip(sub['ocel:eid'], sub['ocel:oid'])); fl['sub'] = fl['ocel:eid'].map(m)
pairs = C.Counter(); tot = 0; same = 0; diffobj = 0; status_involved = 0
src = fl['concept:name'].values; obj = fl['sub'].values; case = fl['case:concept:name'].values
for i in range(1, len(fl)):
    if case[i] != case[i - 1]: continue
    tot += 1; a, b = obj[i - 1], obj[i]
    if isinstance(a, str) and isinstance(b, str):
        if a == b: same += 1
        else: diffobj += 1; pairs[(src[i - 1], src[i])] += 1
    else: status_involved += 1
R['divergence_flattened_evidence_item_DFG'] = {'df_pairs': tot, 'within_same_sub_object': same, 'between_different_sub_objects(divergent)': diffobj,
    'involving_status_event': status_involved, 'share_divergent': round(diffobj / tot, 3),
    'top_divergent_pairs': [(f'{a} -> {b}', n) for (a, b), n in pairs.most_common(8)]}
# ---- edges of flattened DFG absent from every per-object-type DFG (OC-DFG)
dfg_flat, _, _ = pm4py.discover_dfg(fl)
oc = pm4py.discover_ocdfg(ocel)
oc_edges = set()
for ot, edges in oc['edges']['event_couples'].items(): oc_edges |= set(edges.keys())
spur = {e: n for e, n in dfg_flat.items() if e not in oc_edges}
R['flattened_vs_ocdfg_edges'] = {'flat_edges': len(dfg_flat), 'flat_edges_absent_from_ocdfg': len(spur),
    'share_of_flat_df_frequency_on_absent_edges': round(sum(spur.values()) / sum(dfg_flat.values()), 3),
    'top_absent': [(f'{a} -> {b}', n) for (a, b), n in sorted(spur.items(), key=lambda x: -x[1])[:8]],
    'ocdfg_edges_by_type': {ot: len(e) for ot, e in oc['edges']['event_couples'].items()}}
json.dump(R, open('res_r3_t5.json', 'w'), indent=1, default=str); print(json.dumps(R, indent=1, default=str))
# edges between lifecycle activities (revision/comment/flag) in the flattened DFG that no per-object lifecycle DFG contains
LC = set(a for t in ('revision', 'comment', 'flag') for a in pm4py.ocel_object_type_activities(ocel)[t])
lc_edges = set(); [lc_edges.update(oc['edges']['event_couples'][t].keys()) for t in ('revision', 'comment', 'flag')]
fe = {e: n for e, n in dfg_flat.items() if e[0] in LC and e[1] in LC}
ab = {e: n for e, n in fe.items() if e not in lc_edges}
R['flattened_lifecycle_edges_vs_object_lifecycle_dfgs'] = {'flat_edges_among_lifecycle_activities': len(fe), 'absent_from_object_dfgs': len(ab),
    'share_of_their_df_frequency': round(sum(ab.values()) / sum(fe.values()), 3), 'top_absent': [(f'{a} -> {b}', n) for (a, b), n in sorted(ab.items(), key=lambda x: -x[1])[:6]]}
print(R['flattened_lifecycle_edges_vs_object_lifecycle_dfgs'])
json.dump(R, open('res_r3_t5.json', 'w'), indent=1, default=str)
