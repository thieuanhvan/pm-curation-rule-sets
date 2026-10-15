"""Score the blind coders on the seeded code base (CODER_PROTOCOL.md, pre-registered 2026-10-15 16:23). Written before any coder output was seen.
  python score_coders.py <plants dir> <coder_A.json> <coder_B.json>"""
import json, math, sys
from pathlib import Path

H = Path(__file__).resolve().parent
PLANTS = Path(sys.argv[1]); files = {"A": Path(sys.argv[2]), "B": Path(sys.argv[3])}
gt = {g["id"]: g for g in json.load(open(PLANTS / "ground_truth.json", encoding="utf-8"))}
pl = json.load(open(H / "plant_lines.json", encoding="utf-8"))
ext = json.load(open(H / "res_seeded_v3.json", encoding="utf-8"))
post = json.load(open(H / "res_seeded_v3_posthoc.json", encoding="utf-8"))
ext_missed = [i["id"] for i in ext["items"] if i["is_control"] and i["category"] == "in_scope_layer" and not i["detected"]]
ext_missed_post = [m["id"] for m in post["true_misses"]]


def norm(p): return str(p).replace("\\", "/").lstrip("./")


def matches(item, pid):
    v = pl[pid]
    if norm(item.get("path", "")) != norm(v["path"]): return False
    try: ln = int(item.get("line"))
    except (TypeError, ValueError): return False
    return any(abs(ln - x) <= 5 for x in v["lines"])


def wilson(k, n):
    if n == 0: return [None, None]
    z = 1.959963984540054; p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [int((c - w) * 10000) / 10000, int((c + w) * 10000) / 10000]


def rate(found, ids):
    k = sum(1 for i in ids if i in found); n = len(ids)
    return {"k": k, "n": n, "rate": int(k / n * 10000) / 10000 if n else None, "ci95": wilson(k, n)}


coders = {c: json.load(open(f, encoding="utf-8"))["controls"] for c, f in files.items()}
found = {c: {pid for pid in gt if any(matches(it, pid) for it in items)} for c, items in coders.items()}
found["A+B"] = found["A"] | found["B"]
ins = [p for p, g in gt.items() if g["is_control"] and g["category"] == "in_scope_layer"]
oth = [p for p, g in gt.items() if g["is_control"] and g["category"] == "other_layer"]
ctl = ins + oth; dec = [p for p, g in gt.items() if not g["is_control"]]
res = {"protocol": "CODER_PROTOCOL.md (pre-registered 2026-10-15 16:23)", "n_items": {c: len(v) for c, v in coders.items()}}
for c in ("A", "B", "A+B"):
    f = found[c]
    res[c] = {"recall_in_scope": rate(f, ins), "recall_other_layers": rate(f, oth), "recall_all": rate(f, ctl),
              "false_positive_decoys": rate(f, dec),
              "recall_on_extractor_misses_preregistered": rate(f, ext_missed), "recall_on_extractor_true_misses": rate(f, ext_missed_post),
              "found_controls": sorted(p for p in f if p in ctl), "decoys_flagged": sorted(p for p in f if p in dec)}
ext_found = {i["id"] for i in ext["items"] if i["detected"]} | set(post["manual_attributions"])
res["extractor_or_coders_in_scope"] = rate(ext_found | found["A+B"], ins)
res["extractor_or_coders_all"] = rate(ext_found | found["A+B"], ctl)
res["unmatched_coder_items"] = {c: sum(1 for it in items if not any(matches(it, p) for p in gt)) for c, items in coders.items()}
json.dump(res, open(H / "res_seeded_coders.json", "w", encoding="utf-8"), indent=1)
for c in ("A", "B", "A+B"):
    r = res[c]; print(c, {k: (v["k"], v["n"]) for k, v in r.items() if isinstance(v, dict)})
print("extractor or coders, in scope:", res["extractor_or_coders_in_scope"], "| all:", res["extractor_or_coders_all"])
