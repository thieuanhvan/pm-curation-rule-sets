"""Rebuild Supplementary Table S5 (binary coverage by quarter, guards and automatic controls) from the control list of
d_graded_coverage_blind.py, both for all object types and for the evidence-item queue (14/10/2026)."""
import ast
import os
import re

import pandas as pd

H = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(H, "d_graded_coverage_blind.py"), encoding="utf-8").read()
V2 = "2022-04-09"
C = ast.literal_eval(re.search(r"\nC = (\[.*?\])\n", src, re.S).group(1).replace("V2", repr(V2)))
STAGES = ["intake", "fit", "selection", "allocation", "decision", "flag raising", "flag resolution", "exit", "re-review"]


def kap(stage, t, obj=None):
    for _, s, objs, m, tau, rho in C:
        if s != stage or m not in ("guard", "automatic"):
            continue
        if obj and obj not in objs.split():
            continue
        if tau and tau <= t and not (rho and rho <= t):
            return 1
    return 0


for obj, label in ((None, "all object types"), ("EI", "evidence-item queue")):
    print(f"\n{label}\n")
    print("| From | " + " | ".join(s.capitalize() for s in STAGES) + " |")
    print("|---" * (len(STAGES) + 1) + "|")
    prev = None
    for q in pd.period_range("2014Q4", "2026Q3", freq="Q"):
        t = q.end_time.strftime("%Y-%m-%d")
        row = [kap(s, t, obj) for s in STAGES]
        if row != prev:
            print(f"| {q} | " + " | ".join(map(str, row)) + " |")
            prev = row
