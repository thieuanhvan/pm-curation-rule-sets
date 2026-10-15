"""Commit-level check of the first platform version (15/10/2026): does the monthly-snapshot scan miss controls that lived for less than a month?
  python commit_level_v1.py <civic-server bare clone>
Runs the frozen extractors (t1d_extractor_v2 definitions, executed verbatim) on every first-parent commit, then lists control signatures
whose presence runs never include a monthly snapshot (the last commit of a month) and runs shorter than 31 days. Writes res_commit_level_v1.json."""
import json, os, sys, collections, datetime as dt
from pathlib import Path

H = Path(__file__).resolve().parent
V1 = sys.argv[1]
D5 = Path(os.environ.get("P17_PIPELINE", (__import__("os").environ.get("P17_PIPELINE", str(next(p for p in __import__("pathlib").Path(__file__).resolve().parents if (p / "pipeline").is_dir()) / "pipeline")) + "/"))) / "D5req"
src = (D5 / "R7/t1d_extractor_v2.py").read_text(encoding="utf-8")
defs = src[:src.index("out = {}")]
sys.argv = ["x", V1, V1]
ns = {"__file__": str(D5 / "R7/t1d_extractor_v2.py"), "__name__": "frozen_v2"}
exec(compile(defs, "t1d_extractor_v2.py", "exec"), ns)
m = ns["m"]

log = m.git(V1, "log", "--first-parent", "--reverse", "--format=%H|%cI", "HEAD").splitlines()
commits = [{"id": l.split("|")[0][:10], "ref": l.split("|")[0], "date": l.split("|")[1][:10]} for l in log]
monthly = {}
for c in commits: monthly[c["date"][:7]] = c["id"]          # last commit of each month
monthly_ids = set(monthly.values())
rows = ns["run"](V1, commits, m.V1DIRS, m.V1MODELS, "", "v1")
order = {c["id"]: i for i, c in enumerate(commits)}; date = {c["id"]: c["date"] for c in commits}
CONTROL_KINDS = {"GUARD", "ROLE", "ARGREQ", "ARGLEN", "AUTO", "POLICY", "VALID", "SCHED", "JOB"}
short = []
for r in rows:
    if r["kind"] not in CONTROL_KINDS or r["stage"] in ("other",): continue
    idx = sorted(order[i] for i in r["ids"])
    runs, start = [], idx[0]
    for a, b in zip(idx, idx[1:] + [None]):
        if b is None or b != a + 1:
            runs.append((start, a)); start = b
    for s0, s1 in runs:
        end_date = commits[s1 + 1]["date"] if s1 + 1 < len(commits) else commits[s1]["date"]
        days = (dt.date.fromisoformat(end_date) - dt.date.fromisoformat(commits[s0]["date"])).days
        seen_monthly = any(commits[k]["id"] in monthly_ids for k in range(s0, s1 + 1))
        if not seen_monthly:
            short.append({"kind": r["kind"], "stem": r["stem"], "key": r["key"][:100], "stage": r["stage"], "from": commits[s0]["date"],
                          "removed": end_date, "days": days, "commits": s1 - s0 + 1})
res = {"commits": len(commits), "monthly_snapshots": len(monthly_ids), "control_signatures": sum(1 for r in rows if r["kind"] in CONTROL_KINDS and r["stage"] != "other"),
       "runs_missed_by_monthly_snapshots": short}
json.dump(res, open(H / "res_commit_level_v1.json", "w", encoding="utf-8"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "runs_missed_by_monthly_snapshots"}), "| missed runs:", len(short))
for s in short: print(" ", s)
