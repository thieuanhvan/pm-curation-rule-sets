"""Rebuild Supplementary Table S6 (graded coverage by object type) from res_d_graded_coverage_blind.json (14/10/2026)."""
import json
import os

H = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(H, "res_d_graded_coverage_blind.json"), encoding="utf-8"))
STAGES = ["intake", "fit", "decision", "flag raising", "flag resolution", "exit", "re-review"]
fmt = lambda v: "" if v is None else (str(int(v)) if v in (0, 1) else f"{v:g}")
rows = ["| Object type | From | Intake | Fit | Decision | Flag raising | Flag resolution | Exit | Re-review |",
        "|---|---|---|---|---|---|---|---|---|"]
for obj in ("evidence item", "revision", "assertion", "flag"):
    half = res[f"{obj}|wp=0.5"]
    for r in half:
        cells = []
        for s in STAGES:
            v = r.get(s)
            if obj == "evidence item" and s == "exit":
                trip = [next(x for x in reversed(res[f"{obj}|wp={w}"]) if x["from"] <= r["from"])["exit"] for w in (0, 0.5, 1)]
                cells.append(f"{fmt(v)} ({' / '.join(fmt(t) for t in trip)})")
            else:
                cells.append(fmt(v))
        if all(c == "" or c.startswith("0") and c in ("0",) for c in cells) and obj == "flag" and r["from"] == "2015Q1":
            continue
        rows.append(f"| {obj.capitalize()} | {r['from']} | " + " | ".join(cells) + " |")
print("\n".join(rows))
