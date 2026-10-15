"""Export server/ of the seeded commit for the blind coders: record each plant's lines, then remove the zqNN tokens (line count unchanged).
  python prep_coder_view.py <seeded worktree> <plants dir> <out dir>"""
import json, re, shutil, sys
from pathlib import Path

WT, PLANTS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
H = Path(__file__).resolve().parent
gt = json.load(open(PLANTS / "ground_truth.json", encoding="utf-8"))
if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(WT / "server", OUT / "server", ignore=shutil.ignore_patterns(".git", "node_modules", "tmp", "log"))

lines = {}
for g in gt:
    f = OUT / g["path"]
    t = f.read_text(encoding="utf-8", errors="replace").splitlines()
    hit = [i + 1 for i, l in enumerate(t) if g["id"] in l]
    if not hit:   # token only in the file name (e.g. a new job file): the whole file is the plant
        hit = list(range(1, len(t) + 1)) if g["id"] in g["path"] else []
    lines[g["id"]] = {"path": g["path"], "lines": hit}
missing = [k for k, v in lines.items() if not v["lines"]]
json.dump(lines, open(H / "plant_lines.json", "w", encoding="utf-8"), indent=1)

TOK = re.compile(r"[ _\-]?\(?zq\d\d\)?:?")
renamed = 0
for f in OUT.rglob("*"):
    if f.is_file():
        try: t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        if "zq" in t:
            f.write_text(TOK.sub("", t), encoding="utf-8")
    if f.is_file() and re.search(r"zq\d\d", f.name):
        f.rename(f.with_name(TOK.sub("", f.name))); renamed += 1
left = [str(f) for f in OUT.rglob("*") if f.is_file() and re.search(r"zq\d\d", f.read_text(encoding="utf-8", errors="ignore"))]
print("plants located:", len(lines) - len(missing), "of", len(lines), "| missing:", missing, "| files renamed:", renamed, "| tokens left in:", left[:5])
