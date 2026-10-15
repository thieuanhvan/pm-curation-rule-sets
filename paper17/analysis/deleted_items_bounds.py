"""Worst-case bounds for the evidence items missing from CIViC's public history (14/10/2026).
Identifiers 1..max without a public record are treated as deleted items. Each is dated by the submission date of the
nearest lower existing identifier; runs of >= 20 consecutive missing identifiers created on one day are 'bulk'.
Bounds are computed for the paper's headline measures by adding the deleted items in the least favourable way."""
import bisect
import collections
import json
import os

B = (__import__("os").environ.get("P17_PIPELINE", str(__import__("pathlib").Path(__file__).resolve().parents[2] / "pipeline")) + "/D5b/")
OUT = os.path.dirname(os.path.abspath(__file__))
sub = {}
for f in os.listdir(B + "cache"):
    for e in json.load(open(B + "cache/" + f, encoding="utf-8")):
        if e.get("action") == "SUBMITTED" and e["subject"]["__typename"] == "EvidenceItem":
            sub[int(e["subject"]["id"])] = e["createdAt"][:10]
ids = sorted(sub)
present = set(ids)
missing = [i for i in range(1, ids[-1] + 1) if i not in present]
runs, st, pr = [], missing[0], missing[0]
for i in missing[1:]:
    if i != pr + 1:
        runs.append((st, pr)); st = i
    pr = i
runs.append((st, pr))
bulk = set()
for a, b in runs:
    if b - a + 1 >= 20:
        bulk.update(range(a, b + 1))
date = {}
for i in missing:
    j = bisect.bisect_left(ids, i) - 1
    date[i] = sub[ids[j]] if j >= 0 else "2015-01-01"
scattered = [i for i in missing if i not in bulk]
by_year = collections.Counter(date[i][:4] for i in scattered)
res = {"missing": len(missing), "bulk": len(bulk), "scattered": len(scattered), "scattered_by_year": dict(sorted(by_year.items()))}

# 1) pending share at the end of observation (paper: 6,685 of 12,085 submitted items pending = 55.3 %)
pend, n = 6685, 12085
res["pending_share"] = {"paper": pend / n, "all_deleted_pending": (pend + len(missing)) / (n + len(missing)),
                        "all_deleted_decided": pend / (n + len(missing))}
# 2) throughput 2023-25 (802 first decisions / 1,720 arrivals): deleted items dated 2023-25 added as undecided arrivals
d2325 = sum(1 for i in missing if "2023" <= date[i][:4] <= "2025")
res["throughput_2023_25"] = {"paper": 802 / 1720, "deleted_in_window": d2325, "worst": 802 / (1720 + d2325)}
# 3) service-position queues since 2021: deleted items that could have been pending in 2021 or later
res["queues_since_2021"] = {"deleted_dated_2021_or_later": sum(1 for i in missing if date[i] >= "2021-01-01"),
                            "decisions_scored_h365": 955}
# 4) enactment of no self-acceptance of evidence items (Dec 2015 - Apr 2022): 822 of 829 hold (99.2 %);
#    worst case: every scattered deleted item in the window had been self-accepted
win = [i for i in scattered if "2015-12-17" <= date[i] < "2022-04-09"]
res["enactment_SA_ei"] = {"paper": 822 / 829, "scattered_deleted_in_window": len(win), "worst": 822 / (829 + len(win)),
                          "worst_incl_bulk": 822 / (829 + len([i for i in missing if '2015-12-17' <= date[i] < '2022-04-09']))}
json.dump(res, open(os.path.join(OUT, "res_deleted_items_bounds.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(res, indent=1))

# ---- day-based classification on the metadata identifier set used in the paper (1,261 missing identifiers)
meta = {int(m["id"]) for m in json.load(open(B + "meta_evidence.json", encoding="utf-8"))}
miss_m = [i for i in range(1, max(meta) + 1) if i not in meta]
dm = {}
for i in miss_m:
    j = bisect.bisect_left(ids, i) - 1
    dm[i] = sub[ids[j]] if j >= 0 else "2015-01-01"
days = collections.Counter(dm.values())
bulk_days = {d for d, v in days.items() if v >= 20}
isolated = [i for i in miss_m if days[dm[i]] < 5]
res2 = {"missing_metadata_basis": len(miss_m),
        "on_bulk_days_ge20": sum(1 for i in miss_m if dm[i] in bulk_days),
        "bulk_days": sorted((d, days[d]) for d in bulk_days),
        "isolated_lt5_per_day": len(isolated),
        "isolated_by_year": dict(sorted(collections.Counter(dm[i][:4] for i in isolated).items()))}
win = [i for i in isolated if "2015-12-17" <= dm[i] < "2022-04-09"]
res2["enactment_SA_ei_worst_isolated"] = 822 / (829 + len(win))
res2["isolated_in_SA_ei_window"] = len(win)
res["metadata_basis"] = res2
json.dump(res, open(os.path.join(OUT, "res_deleted_items_bounds.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(res2, indent=1))
