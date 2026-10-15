"""POST HOC (not pre-registered), 2026-10-15: manual attribution of new signatures whose key does not carry the plant token
(normalised keys drop comments and truncate at 140 characters; several plants share one file). The pre-registered result stays primary.
Each mapping was checked against the plant snippet in ground_truth.json. Writes res_seeded_v3_posthoc.json."""
import json, math
from pathlib import Path

H = Path(__file__).resolve().parent
r = json.load(open(H / "res_seeded_v3.json", encoding="utf-8"))
MANUAL = {  # plant id -> new signature (kind, stem, key prefix) that the plant's code produced
    "zq06": ("POLICY", "evidence_item_policy", "accept?"),
    "zq07": ("POLICY", "evidence_item_policy", "withdraw?"),
    "zq12": ("AUTO", "accept_revisions", "status->submitted"),
    "zq16": ("AUTO", "expire_stale_source_suggestions", "status->rejected"),
    "zq17": ("SCHED", "scheduled_tasks", "ExpireStaleSourceSuggestions"),
    "zq19": ("SCHED", "scheduled_tasks", "EscalateOverdueEvidenceReviews"),
    "zq21": ("SCHED", "scheduled_tasks", "CloseAbandonedRevisions"),
    "zq23": ("VALID", "evidence_item", "validates :description, length"),
}
un = r["unattributed_new_signatures"]
for pid, (k, s, key) in MANUAL.items():
    assert any(u[0] == k and u[1] == s and u[2].startswith(key) for u in un), pid


def wilson(k, n):
    z = 1.959963984540054; p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [int((c - w) * 10000) / 10000, int((c + w) * 10000) / 10000]


ins = [i for i in r["items"] if i["is_control"] and i["category"] == "in_scope_layer"]
det = [i for i in ins if i["detected"] or i["id"] in MANUAL]
miss = [i for i in ins if not (i["detected"] or i["id"] in MANUAL)]
out = {"note": "post hoc manual attribution; primary result is res_seeded_v3.json",
       "recall_in_scope_posthoc": {"k": len(det), "n": len(ins), "rate": int(len(det) / len(ins) * 10000) / 10000, "ci95": wilson(len(det), len(ins))},
       "manual_attributions": MANUAL,
       "true_misses": [{"id": i["id"], "stage": i["stage"], "mode": i["mode"], "syntax": i["syntax"]} for i in miss]}
json.dump(out, open(H / "res_seeded_v3_posthoc.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
