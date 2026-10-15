"""Held-out seeded-control test (PROTOCOL.md, pre-registered 2026-10-15 14:04). Written before the plants were seen.
  python plant_and_score.py <bare civic-v2 clone> <plants dir> <work dir>
1. Copy the bare clone, check out v2.7.6 in a worktree, overlay plants/files, commit, tag v9.9.9-seed (original clone untouched).
2. Run the FROZEN extractor (t1d_extractor_v2.py definitions executed verbatim; its own test block is not run, its result file is not touched).
3. Score by the fixed rules; write res_seeded_v3.json next to this script."""
import hashlib, json, math, os, re, shutil, subprocess, sys
from pathlib import Path

H = Path(__file__).resolve().parent
BARE, PLANTS, WORK = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
D5 = Path((__import__("os").environ.get("P17_PIPELINE", str(next(p for p in __import__("pathlib").Path(__file__).resolve().parents if (p / "pipeline").is_dir()) / "pipeline")) + "/D5req"))
FROZEN = {D5 / "R6_formal/t1_code_scan.py": "1515bc5eff59d6748bcfccf3dae0053e5fcbb28ed25f156a50fc4e44637b9677",
          D5 / "R7/t1d_extractor_v2.py": "57ffd16fafd764839c15286b93d2b9c78683a700be0194a51db2d8201ab058d7"}
for f, h in FROZEN.items():
    assert hashlib.sha256(f.read_bytes()).hexdigest() == h, f"extractor changed after pre-registration: {f}"


def git(repo, *a, check=True):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, encoding="utf-8", errors="replace", check=check).stdout


# ---------------------------------------------------------------- 1. plant
repo = WORK / "seeded.git"; wt = WORK / "wt"
if repo.exists(): shutil.rmtree(repo, ignore_errors=True)
if wt.exists(): shutil.rmtree(wt, ignore_errors=True)
subprocess.run(["git", "clone", "--bare", "--shared", str(BARE), str(repo)], check=True, capture_output=True)
git(repo, "worktree", "add", "--detach", "--no-checkout", str(wt), "v2.7.6")
git(wt, "sparse-checkout", "set", "--no-cone", "/server/")   # the client tree holds a path Windows cannot create; the scan reads server/ only
git(wt, "-c", "core.protectNTFS=false", "reset", "-q", "--hard", "v2.7.6")   # per-command: the index must hold the client path; sparse checkout keeps it off disk
n_files = 0
for f in (PLANTS / "files").rglob("*"):
    if f.is_file():
        dst = wt / f.relative_to(PLANTS / "files"); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(f, dst); n_files += 1
git(wt, "-c", "core.protectNTFS=false", "add", "-A")
git(wt, "-c", "core.protectNTFS=false", "-c", "user.name=seed", "-c", "user.email=seed@example.invalid", "commit", "-q", "-m", "planted controls (held-out seeded test)")
git(wt, "tag", "v9.9.9-seed")

# ---------------------------------------------------------------- 2. frozen extractor
src = (D5 / "R7/t1d_extractor_v2.py").read_text(encoding="utf-8")
defs = src[:src.index("out = {}")]            # imports, module load, extract2, STAGE_RULES, run(); stops before the R7 test block
sys.argv = ["x", str(repo), str(repo)]
ns = {"__file__": str(D5 / "R7/t1d_extractor_v2.py"), "__name__": "frozen_v2"}
exec(compile(defs, "t1d_extractor_v2.py", "exec"), ns)
rows = ns["run"](str(repo), [{"id": "base", "date": "", "ref": "v2.7.6"}, {"id": "seed", "date": "", "ref": "v9.9.9-seed"}],
                 ns["m"].V2DIRS, ns["m"].V2MODELS, "server/", "v2")
new = [r for r in rows if r["ids"] == ["seed"]]

# ---------------------------------------------------------------- 3. score
gt = json.load(open(PLANTS / "ground_truth.json", encoding="utf-8"))
per_path = {}
for g in gt: per_path.setdefault(g["path"], []).append(g["id"])
STAGE_MAP = {"decision": "decision", "intake": "intake", "exit (revision, automatic)": "exit", "exit (automatic)": "exit", "re-entry (automatic)": "re-review",
             "flag raising (intake of flags)": "flag raising", "flag resolution": "flag resolution"}


def attributed(g):
    hits = [r for r in new if r["path"] == g["path"] and (g["id"] in (r["key"] + r["stem"]).lower() or per_path[g["path"]] == [g["id"]])]
    return hits


def wilson(k, n):
    if n == 0: return [None, None]
    z = 1.959963984540054; p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - w, c + w]


def tr(x): return None if x is None else int(x * 10000) / 10000


items = []
for g in gt:
    hits = attributed(g)
    stages = sorted({STAGE_MAP.get(h["stage"], h["stage"]) for h in hits})
    items.append({**{k: g.get(k) for k in ("id", "path", "category", "is_control", "stage", "mode", "syntax")},
                  "detected": bool(hits) if g.get("is_control") else None,
                  "false_positive": (any(h["stage"] not in ("other", "scheduled job") for h in hits) if not g.get("is_control") else None),
                  "stage_correct": (g.get("stage") in stages) if (g.get("is_control") and hits) else None,
                  "signatures": [(h["kind"], h["stem"], h["key"][:80], h["stage"]) for h in hits]})
ctrl = [i for i in items if i["is_control"]]; dec = [i for i in items if not i["is_control"]]


def rate(sub, key):
    k = sum(1 for i in sub if i[key]); n = len(sub)
    return {"k": k, "n": n, "rate": tr(k / n) if n else None, "ci95": [tr(x) for x in wilson(k, n)]}


res = {"protocol": "PROTOCOL.md (pre-registered 2026-10-15 14:04)", "frozen_sha256": {str(k.name): v for k, v in FROZEN.items()}, "files_planted": n_files,
       "recall_in_scope": rate([i for i in ctrl if i["category"] == "in_scope_layer"], "detected"),
       "recall_other_layers": rate([i for i in ctrl if i["category"] == "other_layer"], "detected"),
       "recall_all": rate(ctrl, "detected"),
       "recall_by_mode": {m: rate([i for i in ctrl if i["mode"] == m and i["category"] == "in_scope_layer"], "detected") for m in sorted({i["mode"] for i in ctrl})},
       "recall_by_stage": {s: rate([i for i in ctrl if i["stage"] == s and i["category"] == "in_scope_layer"], "detected") for s in sorted({i["stage"] for i in ctrl})},
       "false_positive_decoys": rate(dec, "false_positive"),
       "stage_accuracy_detected": rate([i for i in ctrl if i["detected"]], "stage_correct"),
       "unattributed_new_signatures": [(r["kind"], r["stem"], r["key"][:80], r["stage"], r["path"]) for r in new
                                       if not any(r in attributed(g) for g in gt)],
       "items": items}
json.dump(res, open(H / "res_seeded_v3.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k not in ("items", "unattributed_new_signatures")}, indent=1, ensure_ascii=False))
print("unattributed new signatures:", len(res["unattributed_new_signatures"]))
