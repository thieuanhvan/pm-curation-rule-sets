"""H2 check within CIViC (14/10/2026). H2: with no guarded or automatic exit without a judgement (kappa_exit = 0) and
arrivals exceeding decisions, the judgement exit (rejection) is used for clearing: rejections concentrate on old items and
arrive in bursts. Refuted if the age profile of rejections matches that of acceptances and rejections are not clustered.
Periods: first version 2015 to 8 April 2022 (deletion guard in code, used almost only in bulk), second version 2022-04 to 2025-03,
and after the April 2025 reason requirement. Only first decisions on other users' evidence items, bot excluded."""
import json
import os
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

B = (__import__("os").environ.get("P17_PIPELINE", str(next(p for p in __import__("pathlib").Path(__file__).resolve().parents if (p / "pipeline").is_dir()) / "pipeline")) + "/D5b/")
OUT = os.path.dirname(os.path.abspath(__file__))
BOT = {385}
ev = {}
for f in os.listdir(B + "cache"):
    for e in json.load(open(B + "cache/" + f, encoding="utf-8")):
        ev[e["id"]] = e
ev = sorted(ev.values(), key=lambda e: (e["createdAt"], e["id"]))
sub_t, sub_u, first = {}, {}, {}
for e in ev:
    s = e.get("subject") or {}
    if s.get("__typename") != "EvidenceItem":
        continue
    i = s.get("id"); u = (e.get("originatingUser") or {}).get("id")
    t = pd.Timestamp(e["createdAt"])
    if e["action"] == "SUBMITTED" and i not in sub_t:
        sub_t[i], sub_u[i] = t, u
    if e["action"] in ("ACCEPTED", "REJECTED") and i in sub_t and i not in first and u not in BOT and u != sub_u[i]:
        first[i] = (e["action"], t, (t - sub_t[i]).days, u)
rows = [dict(item=i, act=a, t=t, age=d, editor=ed) for i, (a, t, d, ed) in first.items()]
D = pd.DataFrame(rows)
D["period"] = pd.cut(D.t.dt.tz_localize(None), [pd.Timestamp("2015-01-01"), pd.Timestamp("2022-04-09"), pd.Timestamp("2025-04-07"), pd.Timestamp("2027-01-01")],
                     labels=["v1 2015-22", "v2 2022-25", "v2 after 2025 rule"], right=False)
res = {}
for p, g in D.groupby("period", observed=True):
    acc, rej = g[g.act == "ACCEPTED"], g[g.act == "REJECTED"]
    # burstiness: share of the period's rejections that fall in its busiest 10 % of months; Fano factor of monthly counts
    m = rej.t.dt.tz_localize(None).dt.to_period("M").value_counts()
    months = pd.period_range(g.t.min().tz_localize(None), g.t.max().tz_localize(None), freq="M")
    counts = np.array([m.get(x, 0) for x in months])
    top = np.sort(counts)[::-1][:max(1, int(round(0.1 * len(counts))))]
    res[str(p)] = {
        "acceptances": int(len(acc)), "rejections": int(len(rej)),
        "rejection_share": float(len(rej) / len(g)) if len(g) else None,
        "median_age_days_acceptance": float(acc.age.median()) if len(acc) else None,
        "median_age_days_rejection": float(rej.age.median()) if len(rej) else None,
        "share_over_1y_acceptance": float((acc.age > 365).mean()) if len(acc) else None,
        "share_over_1y_rejection": float((rej.age > 365).mean()) if len(rej) else None,
        "months": int(len(counts)), "rejections_in_busiest_10pct_months": float(top.sum() / counts.sum()) if counts.sum() else None,
        "fano_monthly_rejections": float(counts.var(ddof=1) / counts.mean()) if counts.mean() else None,
    }
json.dump(res, open(os.path.join(OUT, "res_h2_test.json"), "w", encoding="utf-8"), indent=1)
for k, v in res.items():
    print(k, json.dumps({a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()}))

# ---- queue position at decision (all pending items, h = infinity): 0 newest-first, 1 oldest-first
a_all = {i: t.tz_localize(None).value for i, t in sub_t.items()}
d_all = {i: first[i][1].tz_localize(None).value if i in first else np.inf for i in sub_t}
# any first decision (incl. own items) closes the pending spell; rebuild with all first decisions
any_first = {}
for e in ev:
    s = e.get("subject") or {}
    if s.get("__typename") == "EvidenceItem" and e["action"] in ("ACCEPTED", "REJECTED"):
        i = s.get("id")
        if i in sub_t and i not in any_first:
            any_first[i] = pd.Timestamp(e["createdAt"]).tz_localize(None).value
ids = list(sub_t)
A = np.array([a_all[i] for i in ids], dtype=float)
Dd = np.array([any_first.get(i, np.inf) for i in ids], dtype=float)
pos = []
for r in D.itertuples():
    t = r.t.tz_localize(None).value; ai = a_all[r.item]
    pend = (A < t) & (Dd >= t)
    n = pend.sum() - 1
    if n <= 0:
        continue
    newer = ((A > ai) & pend).sum()
    pos.append(dict(period=r.period, act=r.act, u=newer / n, editor=r.editor, t=r.t))
P = pd.DataFrame(pos)
res_u = P.groupby(["period", "act"], observed=True).u.agg(["mean", "median", "count"]).round(3)
print(res_u)
res["queue_position_by_period_and_action"] = {f"{p}|{a}": {"mean_u": float(v["mean"]), "median_u": float(v["median"]), "n": int(v["count"])}
                                             for (p, a), v in res_u.iterrows()}
json.dump(res, open(os.path.join(OUT, "res_h2_test.json"), "w", encoding="utf-8"), indent=1)

# ---- difference in mean queue position (rejection minus acceptance) by period: bootstrap CI and Mann-Whitney
from scipy.stats import mannwhitneyu
rng = np.random.default_rng(29)
diff = {}
for p, g in P.groupby("period", observed=True):
    r = g[g.act == "REJECTED"].u.values; a = g[g.act == "ACCEPTED"].u.values
    boots = [rng.choice(r, len(r)).mean() - rng.choice(a, len(a)).mean() for _ in range(4000)]
    diff[str(p)] = {"diff_mean_u": float(r.mean() - a.mean()), "ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
                    "mannwhitney_p": float(mannwhitneyu(r, a, alternative="greater").pvalue), "n_rej": int(len(r)), "n_acc": int(len(a))}
g1 = P[P.period == "v1 2015-22"]; g2 = P[P.period != "v1 2015-22"]
d1 = lambda g: g[g.act == "REJECTED"].u.mean() - g[g.act == "ACCEPTED"].u.mean()
boots = []
for _ in range(4000):
    s1 = pd.concat([g1[g1.act == k].sample(frac=1, replace=True, random_state=int(rng.integers(1e9))) for k in ("REJECTED", "ACCEPTED")])
    s2 = pd.concat([g2[g2.act == k].sample(frac=1, replace=True, random_state=int(rng.integers(1e9))) for k in ("REJECTED", "ACCEPTED")])
    boots.append(d1(s2) - d1(s1))
diff["v2_minus_v1_gap"] = {"estimate": float(d1(g2) - d1(g1)), "ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))]}
res["queue_position_difference"] = diff
json.dump(res, open(os.path.join(OUT, "res_h2_test.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(diff, indent=1))

# ---- 14/10 night: clustered by deciding editor, and a permutation null for bursts
def boot_gap_clustered(g, B=4000, seed=31):
    rng2 = np.random.default_rng(seed)
    eds = g.editor.unique()
    by = {e: g[g.editor == e] for e in eds}
    vals = []
    for _ in range(B):
        smp = pd.concat([by[e] for e in rng2.choice(eds, len(eds))])
        r = smp[smp.act == "REJECTED"].u; a = smp[smp.act == "ACCEPTED"].u
        if len(r) and len(a):
            vals.append(r.mean() - a.mean())
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975)), int(len(eds))]


clus = {}
for p, g in P.groupby("period", observed=True):
    clus[str(p)] = {"diff_mean_u": float(g[g.act == "REJECTED"].u.mean() - g[g.act == "ACCEPTED"].u.mean()),
                    "ci95_clustered_by_editor_and_n_editors": boot_gap_clustered(g),
                    "editors_with_rejections": int(g[g.act == "REJECTED"].editor.nunique())}
# gap change v2 - v1, clustered by editor within each period
rng3 = np.random.default_rng(37)
def one(g):
    eds = g.editor.unique(); by = {e: g[g.editor == e] for e in eds}
    smp = pd.concat([by[e] for e in rng3.choice(eds, len(eds))])
    r = smp[smp.act == "REJECTED"].u; a = smp[smp.act == "ACCEPTED"].u
    return r.mean() - a.mean() if len(r) and len(a) else np.nan
vals = [one(g2) - one(g1) for _ in range(4000)]
vals = [v for v in vals if not np.isnan(v)]
clus["v2_minus_v1_gap_clustered"] = {"estimate": float(d1(g2) - d1(g1)), "ci95": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]}

# bursts: share of decisions in the busiest 10 % of months, rejections vs acceptances, with a permutation null
burst = {}
for p, g in P.groupby("period", observed=True):
    g = g.copy(); g["m"] = g.t.dt.tz_localize(None).dt.to_period("M")
    months = pd.period_range(g.m.min(), g.m.max(), freq="M"); k = max(1, int(round(0.1 * len(months))))
    def topshare(x):
        c = x.m.value_counts().reindex(months, fill_value=0).values
        return np.sort(c)[::-1][:k].sum() / c.sum()
    rej = g[g.act == "REJECTED"]; obs = topshare(rej)
    rng4 = np.random.default_rng(41); null = []
    for _ in range(2000):
        idx = rng4.choice(len(g), len(rej), replace=False)
        null.append(topshare(g.iloc[idx]))
    burst[str(p)] = {"rejections_top10pct_months": float(obs), "acceptances_top10pct_months": float(topshare(g[g.act == "ACCEPTED"])),
                     "null_mean_random_decisions": float(np.mean(null)), "permutation_p": float((np.sum(np.array(null) >= obs) + 1) / 2001)}
res["clustered"] = clus; res["bursts"] = burst
json.dump(res, open(os.path.join(OUT, "res_h2_test.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps({"clustered": clus, "bursts": burst}, indent=1))

# ---- 14/10 night, round 11: editors resampled jointly across periods; rebuild contrast 2022-25 only; dropped draws counted
rng5 = np.random.default_rng(43)
P2 = P.copy(); P2["per"] = P2.period.astype(str)
eds_all = P2.editor.unique(); byE = {e: P2[P2.editor == e] for e in eds_all}
def gap(g):
    r = g[g.act == "REJECTED"].u; a = g[g.act == "ACCEPTED"].u
    return r.mean() - a.mean() if len(r) and len(a) else np.nan
joint = {"v2 2022-25 minus v1": [], "after 2025 rule minus v1": [], "v2 pooled minus v1": []}
dropped = 0; B5 = 4000
for _ in range(B5):
    smp = pd.concat([byE[e] for e in rng5.choice(eds_all, len(eds_all))])
    g1_ = gap(smp[smp.per == "v1 2015-22"]); g2_ = gap(smp[smp.per == "v2 2022-25"]); g3_ = gap(smp[smp.per == "v2 after 2025 rule"])
    gp_ = gap(smp[smp.per != "v1 2015-22"])
    if np.isnan(g1_) or np.isnan(g2_) or np.isnan(g3_):
        dropped += 1; continue
    joint["v2 2022-25 minus v1"].append(g2_ - g1_); joint["after 2025 rule minus v1"].append(g3_ - g1_); joint["v2 pooled minus v1"].append(gp_ - g1_)
est = {"v2 2022-25 minus v1": gap(P2[P2.per == "v2 2022-25"]) - gap(P2[P2.per == "v1 2015-22"]),
       "after 2025 rule minus v1": gap(P2[P2.per == "v2 after 2025 rule"]) - gap(P2[P2.per == "v1 2015-22"]),
       "v2 pooled minus v1": gap(P2[P2.per != "v1 2015-22"]) - gap(P2[P2.per == "v1 2015-22"])}
res["joint_editor_bootstrap"] = {k: {"estimate": float(est[k]), "ci95": [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))]} for k, v in joint.items()}
res["joint_editor_bootstrap"]["draws"] = B5; res["joint_editor_bootstrap"]["dropped_draws_without_a_rejection_in_some_period"] = dropped
res["joint_editor_bootstrap"]["n_editors_all_periods"] = int(len(eds_all))
# dropped draws of the per-period clustered intervals
drop_pp = {}
for p, g in P.groupby("period", observed=True):
    rng6 = np.random.default_rng(31); eds = g.editor.unique(); by = {e: g[g.editor == e] for e in eds}; d = 0
    for _ in range(4000):
        smp = pd.concat([by[e] for e in rng6.choice(eds, len(eds))])
        if not (len(smp[smp.act == "REJECTED"]) and len(smp[smp.act == "ACCEPTED"])):
            d += 1
    drop_pp[str(p)] = d
res["per_period_dropped_draws"] = drop_pp
json.dump(res, open(os.path.join(OUT, "res_h2_test.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps({"joint": res["joint_editor_bootstrap"], "dropped": drop_pp}, indent=1))
