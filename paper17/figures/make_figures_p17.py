"""Draw the P17 manuscript figures from existing result files only (no new analyses).

Inputs live under outputs/reviews/nhan_ideas_20261006/D5req/ (A2, A3, W3, W4, W7).
Outputs: fig1_protocol, fig4_throughput_intensity, fig5_service_age (main) and figS1-figS3 (supplement) in this folder, 400 dpi.
Images carry no figure number or caption; captions are in the manuscript text.
Run: python make_figures_p17.py
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NI = (__import__("os").environ.get("P17_PIPELINE", str(next(p for p in __import__("pathlib").Path(__file__).resolve().parents if (p / "pipeline").is_dir()) / "pipeline")) + "/D5req")
DPI = 400
# as-is legacy share 0.043 [0.032, 0.056]: W4/outcomes_log.txt, section EAimp_legacyAcceptedShare, ASIS_logit
ASIS_LEGACY = 0.043
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.03})
C_MAIN, C_ALT, C_GREY, C_ACC = "#1f4e79", "#c55a11", "#7f7f7f", "#548235"


def load(rel):
    with open(os.path.join(NI, rel), encoding="utf-8") as f:
        return json.load(f)


def save(fig, name):
    fig.savefig(os.path.join(HERE, name), dpi=DPI)
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------- Fig 1 research design
def box(ax, x, y, w, h, text, fc="#ffffff", ec=C_MAIN, fs=6.5, weight="normal", ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.01",
                                fc=fc, ec=ec, lw=0.9, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight=weight)


def arrow(ax, p, q, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, lw=0.8, color="#404040",
                                 connectionstyle=f"arc3,rad={rad}"))


def fig1():
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    ax.set_xlim(-0.012, 1.0)
    ax.set_ylim(0.04, 1)
    ax.axis("off")
    cols = [(0.0, 0.22, "Inputs"), (0.265, 0.40, "Measurement protocol"), (0.71, 0.29, "Outputs")]
    for x, w, t in cols:
        ax.text(x + w / 2, 0.985, t, fontsize=7.5, weight="bold", va="top", ha="center")
    box(ax, 0.0, 0.70, 0.22, 0.22, "Public event history\n(status, revision, comment,\nflag events; actor and\norganisation at event time)", fc="#f2f2f2")
    box(ax, 0.0, 0.43, 0.22, 0.22, "Source-code and release\nhistory of the platform\n(dates at which each\ncontrol reached users)", fc="#f2f2f2")
    box(ax, 0.0, 0.16, 0.22, 0.22, "Documented procedure\n(standard operating\nprocedure, guidelines,\nrole definitions)", fc="#f2f2f2")
    box(ax, 0.265, 0.16, 0.40, 0.76,
        "D1  OCEL 2.0 log: object types and qualifiers\n\n"
        "D2  Time-indexed rule set R(t) from code history\n\n"
        "D3  Conformance against R(t) and against the\n      documented rules; control coverage by stage\n\n"
        "D4  Decision intensity per active decider-day\n      (event types present in all platform versions)\n\n"
        "D5  Service position u against a permutation null\n\n"
        "D6  Liveness at landmarks (30, 90, 365 days)\n\n"
        "D7  Age hazard of acceptance (calendar scale,\n      stratified by submitter)\n\n"
        "Sanity check: flattened vs object-centric conformance", fs=6.3)
    box(ax, 0.71, 0.70, 0.29, 0.22, "Configured vs unconfigured\nstages: which controls the\ncode enforces, and when", fc="#e2efda", ec=C_ACC)
    box(ax, 0.71, 0.43, 0.29, 0.22, "Regime description: intensity,\nservice order and age,\nliveness, composition of\nthe pending stock", fc="#e2efda", ec=C_ACC)
    box(ax, 0.71, 0.16, 0.29, 0.22, "Applied to CIViC; illustrated\non GO, HPO and Wikidata;\nported to a second\ncuration application", fc="#fbe5d6", ec=C_ALT)
    for y in (0.81, 0.54, 0.27):
        arrow(ax, (0.225, y), (0.26, y))
        arrow(ax, (0.67, y), (0.705, y))
    save(fig, "fig1_protocol.png")


# ---------------------------------------------------------------- Fig 2 status skeleton and revision lifecycle
def draw_graph(ax, pos, edges, labels, title, rads, lt=None):
    lt = lt or {}
    ax.set_xlim(-0.24, 1.12)
    ax.set_ylim(-0.08, 1.02)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(-0.24, 1.02, title, fontsize=8, weight="bold", va="top")
    import math
    for (a, b), n in edges.items():
        if a == b:
            continue
        lw = 0.5 + 0.9 * math.log10(max(n, 1))
        rad = rads.get((a, b), 0.0)
        ax.add_patch(FancyArrowPatch(pos[a], pos[b], arrowstyle="-|>", mutation_scale=8, lw=lw,
                                     color="#6e6e6e", shrinkA=16, shrinkB=16,
                                     connectionstyle=f"arc3,rad={rad}"))
        (x1, y1), (x2, y2) = pos[a], pos[b]
        dx, dy = x2 - x1, y2 - y1
        cx, cy = (x1 + x2) / 2 + rad * dy, (y1 + y2) / 2 - rad * dx
        t = lt.get((a, b), 0.5)
        lx = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2
        ly = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2
        ax.text(lx, ly, f"{n:,}", fontsize=6.3, ha="center", va="center", color="#1a1a1a",
                bbox=dict(fc="white", ec="none", pad=0.6))
    for k, (x, y) in pos.items():
        ax.add_patch(FancyBboxPatch((x - 0.1, y - 0.045), 0.2, 0.09, boxstyle="round,pad=0.008",
                                    fc="#eaf1fb" if k not in ("start", "end") else "#f2f2f2", ec=C_MAIN, lw=0.8,
                                    zorder=3))
        ax.text(x, y, labels.get(k, k), ha="center", va="center", fontsize=6.6, zorder=4)


def fig2():
    d = load("A2/out/discovery.json")
    top = d["variants_status_projection"]["top"]
    edges = {}
    for variant, n, _ in top:
        steps = ["start"] + variant.split(" > ")
        if steps[-1] == "SUBMITTED":
            steps.append("end")
        for a, b in zip(steps[:-1], steps[1:]):
            edges[(a, b)] = edges.get((a, b), 0) + n
    pos = {"start": (-0.12, 0.5), "SUBMITTED": (0.3, 0.5), "ACCEPTED": (0.62, 0.88), "REJECTED": (0.62, 0.12),
           "REVERTED": (0.98, 0.5), "end": (0.3, 0.06)}
    labels = {"start": "start", "SUBMITTED": "submitted", "ACCEPTED": "accepted", "REJECTED": "rejected",
              "REVERTED": "reverted", "end": "still submitted"}
    rads = {("ACCEPTED", "REJECTED"): -0.35, ("REJECTED", "ACCEPTED"): -0.35, ("start", "ACCEPTED"): -0.25,
            ("REVERTED", "REJECTED"): 0.25, ("REJECTED", "REVERTED"): 0.25}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    draw_graph(axes[0], pos, edges, labels, "(a) Evidence-item status lifecycle", rads)
    r = d["revision_object_lifecycles"]["top"]
    redges = {}
    for variant, n, _ in r:
        steps = ["start"] + variant.split(" > ")
        if steps[-1] == "REVISION_SUGGESTED":
            steps.append("end")
        for a, b in zip(steps[:-1], steps[1:]):
            redges[(a, b)] = redges.get((a, b), 0) + n
    rpos = {"start": (-0.12, 0.5), "REVISION_SUGGESTED": (0.3, 0.5), "REVISION_ACCEPTED": (0.62, 0.88),
            "REVISION_REJECTED": (0.62, 0.12), "REVISION_SUPERSEDED": (0.98, 0.5), "end": (0.3, 0.06)}
    rlabels = {"start": "start", "REVISION_SUGGESTED": "suggested", "REVISION_ACCEPTED": "accepted",
               "REVISION_REJECTED": "rejected", "REVISION_SUPERSEDED": "superseded", "end": "still pending"}
    rrads = {("REVISION_ACCEPTED", "REVISION_REJECTED"): -0.45, ("start", "REVISION_ACCEPTED"): -0.25,
             ("start", "REVISION_REJECTED"): 0.25}
    draw_graph(axes[1], rpos, redges, rlabels, "(b) Revision object lifecycle", rrads,
               lt={("REVISION_ACCEPTED", "REVISION_REJECTED"): 0.3, ("start", "REVISION_REJECTED"): 0.3})
    fig.tight_layout(w_pad=0.5)
    save(fig, "figS1_lifecycles.png")
    return edges, redges


# ---------------------------------------------------------------- Fig 3 throughput and decision effort
def fig3():
    t1 = load("W3/res_t1_rho.json")
    w7 = load("W7/res_w7_t1_attention.json")
    years = [y for y in sorted(t1["by_year_rho"]) if int(y) >= 2016]
    yr = [int(y) for y in years]
    rho_all = [t1["by_year_rho"][y]["rho_all"] for y in years]
    rho_live = [t1["by_year_rho"][y]["rho_live365"] for y in years]
    complete = [t1["by_year_rho"][y]["followup_complete"] for y in years]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), gridspec_kw={"width_ratios": [1.05, 1.15, 1.0]})
    ax = axes[0]
    for series, c, lab in [(rho_all, C_MAIN, "all arrivals")]:
        ax.plot(yr, series, color=c, lw=1.1, label=lab)
        ax.scatter([x for x, k in zip(yr, complete) if k], [s for s, k in zip(series, complete) if k], color=c, s=12, zorder=3)
        ax.scatter([x for x, k in zip(yr, complete) if not k], [s for s, k in zip(series, complete) if not k],
                   facecolor="white", edgecolor=c, s=12, zorder=3)
    ax.axhline(1, color=C_GREY, lw=0.7, ls=":")
    ax.set_ylabel("Decisions per arrival")
    ax.set_xticks([2016, 2019, 2022, 2025])
    ax.set_ylim(0, 1.05)
    ax.set_title("(a) Throughput ratio", fontsize=8, loc="left")
    ax = axes[1]
    eff = t1["decider_effort_by_year"]
    mods = [eff[y]["active_moderators"] for y in years]
    # point estimate with the 95 % bootstrap interval clustered by moderator
    dpd = [[eff[y]["ev_decisions_per_moderator_active_day"][0]] + eff[y]["ev_decisions_per_active_day_CI_cluster_moderator"]
           for y in years]
    ax.bar(yr, mods, color="#d9d9d9", width=0.7, label="active moderators")
    ax.set_ylabel("Active moderators")
    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.errorbar(yr, [v[0] for v in dpd], yerr=[[v[0] - v[1] for v in dpd], [v[2] - v[0] for v in dpd]],
                 color=C_MAIN, lw=1.1, marker="o", ms=3, capsize=1.5, elinewidth=0.7,
                 label="evidence decisions per\nactive moderator-day")
    ax2.set_ylabel("Evidence decisions per\nactive moderator-day")
    ax2.set_ylim(0, 4.6)
    ax.set_ylim(0, 27)
    ax.set_xticks([2016, 2019, 2022, 2025])
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=6.2, loc="upper right", ncol=1)
    ax.set_title("(b) Headcount and decision intensity", fontsize=8, loc="left")
    ax = axes[2]
    r3 = load("R3_civic/res_r3_t3.json")["ev_decision"]["decomp"]
    ss = {"stayers": r3["mp_stayers"], "stayers_CI": r3["mp_stayers_CI"],
          "turnover": r3["mp_entry_plus_exit"], "turnover_CI": r3["mp_entry_plus_exit_CI"],
          "total": r3["delta"], "total_CI": r3["delta_CI"]}
    terms = [("total", "total change"), ("stayers", "stayers"), ("turnover", "turnover\n(entry and exit)")]
    vals = [ss[k] for k, _ in terms]
    lo = [ss[k] - ss[k + "_CI"][0] for k, _ in terms]
    hi = [ss[k + "_CI"][1] - ss[k] for k, _ in terms]
    ax.barh(range(len(terms)), vals, color=[C_GREY, C_MAIN, C_ALT], height=0.55)
    ax.errorbar(vals, range(len(terms)), xerr=[lo, hi], fmt="none", ecolor="#404040", elinewidth=0.7, capsize=1.5)
    ax.set_yticks(range(len(terms)))
    ax.set_yticklabels([t for _, t in terms])
    ax.invert_yaxis()
    ax.axvline(0, color=C_GREY, lw=0.7)
    ax.set_xlim(-2.8, 0.8)
    ax.set_xlabel("Contribution to change (2.06 to 0.60)")
    ax.set_title("(c) Decomposition, 2016-18 to 2023-26", fontsize=8, loc="left")
    fig.tight_layout(w_pad=0.6)
    save(fig, "fig4_throughput_intensity.png")
    return dict(zip(years, zip(rho_all, rho_live, mods, [v[0] for v in dpd]))), ss


# ---------------------------------------------------------------- Fig 4 service position and age hazard
def fig4():
    a = load("A3/res_a4_discipline.json")["civic_all_by_year"]
    h = load("A3/res_a2_hazard.json")
    years = sorted(a)
    yr = [int(y) for y in years]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7))
    ax = axes[0]
    ax.fill_between(yr, [a[y]["null_meanU_95"][0] for y in years], [a[y]["null_meanU_95"][1] for y in years],
                    color="#d9d9d9", label="random service (95 % null band)")
    m = [a[y]["meanU"] for y in years]
    ax.errorbar(yr, [v[0] for v in m], yerr=[[v[0] - v[1] for v in m], [v[2] - v[0] for v in m]], color=C_MAIN,
                marker="o", ms=3, lw=1.1, capsize=1.5, elinewidth=0.7, label="observed mean u")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Relative queue position u\n(0 newest-first, 1 oldest-first)")
    ax.set_xticks([2015, 2017, 2019, 2021, 2023, 2025])
    ax.legend(frameon=False, fontsize=6.8, loc="upper right")
    ax.set_title("(a) Service position of decisions, all pending items", fontsize=8, loc="left")
    ax = axes[1]
    r5 = load("R5/results_r5.json")
    c = r5["c_age"]
    fr = r5["c2_item_frailty"]["pem_item_gamma_frailty"]["HR_per_year_of_age"]
    rows = [("Stratified Cox, main\n(cluster bootstrap)", [c["strat_submitter_point"][0]] + c["cluster_bootstrap"]["ci95"]),
            ("Same, model-based interval", c["strat_submitter_point"]),
            ("Without quality covariates", c["strat_submitter_no_quality_covariates"]),
            ("Strata submitter x level", c["strat_submitter_x_level"]),
            ("High-quality items only", c["strat_submitter_high_quality_subset"]["HR"]),
            ("Item-level gamma frailty", fr)]
    for i, (lab, v) in enumerate(rows):
        ax.errorbar([v[0]], [i], xerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="o", ms=3,
                    color=C_MAIN if i == 0 else C_GREY, capsize=1.5, elinewidth=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=6.6)
    ax.invert_yaxis()
    ax.axvline(1, color=C_GREY, lw=0.7, ls=":")
    ax.set_xlim(0.3, 1.1)
    ax.set_xlabel("Acceptance hazard ratio per year of item age\n(items at least one year old)")
    ax.set_title("(b) Age dependence of acceptance", fontsize=8, loc="left")
    fig.tight_layout(w_pad=1.0)
    save(fig, "fig5_service_age.png")
    return {y: a[y]["meanU"] for y in years}


# ---------------------------------------------------------------- Fig 5 flattened vs object-centric deviations
def fig5():
    s = load("W3/res_t4_sop.json")
    pf = s["petri_fitness_precision_excl_bot"]
    acts = ["REVISION_ACCEPTED", "REVISION_SUGGESTED", "REVISION_REJECTED", "REVISION_SUPERSEDED", "COMMENTED",
            "FLAG_RESOLVED", "REVISION_COMMENTED", "ACCEPTED", "REJECTED", "REVERTED", "FLAGGED"]
    nice = {a: a.lower().replace("_", " ") for a in acts}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [1.25, 1.0]})
    ax = axes[0]
    series = [("TEXT_strict", "flattened, documentation model", "#9dc3e6"),
              ("CODE_strict", "flattened, code model", C_MAIN),
              ("CODE_interleaved", "lifecycles interleaved, code model", C_ALT)]
    width = 0.27
    for i, (k, lab, c) in enumerate(series):
        share = pf[k]["cases_with_log_move_by_activity(share)"]
        ax.barh([j + (i - 1) * width for j in range(len(acts))], [100 * share.get(a, 0.0) for a in acts],
                height=width, color=c, label=lab)
    ax.set_yticks(range(len(acts)))
    ax.set_yticklabels([nice[a] for a in acts])
    ax.invert_yaxis()
    ax.set_xlabel("Decided items with a deviation on the activity (%)")
    ax.legend(frameon=False, fontsize=6.4, loc="lower right")
    ax.set_title("(a) Deviations per activity", fontsize=8, loc="left")
    ax = axes[1]
    ev = s["oc_vs_flattened_event_level"]["CODE_strict"]
    objs = ["revision", "comment", "flag"]
    cats = [("diverge_flat_only(flattening artefact)", "flattened view only", "#9dc3e6"),
            ("converge_dev", "both views", C_MAIN),
            ("diverge_oc_only(masked by flattening)", "object-centric view only", C_ALT)]
    width = 0.26
    for i, (k, lab, c) in enumerate(cats):
        vals = [ev[o][k] for o in objs]
        xs = [j + (i - 1) * width for j in range(len(objs))]
        ax.bar(xs, [max(v, 0.6) if v > 0 else 0 for v in vals], width=width, color=c, label=lab)
        for x, v in zip(xs, vals):
            ax.text(x, max(v, 0.6) * 1.15 if v > 0 else 0.7, f"{v:,}", ha="center", fontsize=6.2)
    ax.set_yscale("log")
    ax.set_ylim(0.5, 30000)
    ax.set_xticks(range(len(objs)))
    ax.set_xticklabels(objs)
    ax.set_ylabel("Deviating events (log scale)")
    ax.legend(frameon=False, fontsize=6.4, loc="upper right")
    ax.set_title("(b) Event-level comparison, code model", fontsize=8, loc="left")
    fig.tight_layout(w_pad=1.0)
    save(fig, "figS2_flattening.png")
    return ev


# ---------------------------------------------------------------- Fig 6 policy bounds frontier
def fig6():
    b = load("W4/results_bounds.json")
    w = load("W7/res_w7_t4_logvalues.json")
    obs_leg = sum(w["legacy"]["observed_share_of_EAimp_decided_in_holdout_by_draw"]) / 5
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharex=True)
    styles = {cap: (c, ls, f"{lab} ({b[cap]['tokens']:,} tokens)") for cap, c, ls, lab in [
        ("cap0.75", "#9dc3e6", "--", "lower capacity"), ("cap1", C_MAIN, "-", "observed capacity"),
        ("cap1.25", "#2e75b6", ":", "higher capacity")]}
    out = {}
    for ax, D, key, obs, asis in [(axes[0], 90, "new_by90", w["observed_log"]["share_by90_full_followup"]["share"],
                                   w["asis_model"]["share_by90_full_followup"][0]),
                                  (axes[1], 365, "new_by365", w["observed_log"]["share_by365_full_followup"]["share"],
                                   w["asis_model"]["share_by365_full_followup"][0])]:
        for cap, (c, ls, lab) in styles.items():
            fr = [f for f in b[cap]["frontier"] if f["D"] == D]
            fr.sort(key=lambda f: f["legacyShareOfTokens"])
            xs = [100 * f["legacyAcceptedShare"][0] for f in fr]
            ys = [100 * f[key][0] for f in fr]
            ax.plot(xs, ys, color=c, ls=ls, lw=1.2, marker="o" if cap == "cap1" else None, ms=2.5, label=lab)
            if cap == "cap1":
                out[D] = list(zip([f["legacyShareOfTokens"] for f in fr], xs, ys))
                for f, x, y in zip(fr, xs, ys):
                    if f["legacyShareOfTokens"] in (0, 0.1, 0.5, 1):
                        ax.annotate(f"{int(100 * f['legacyShareOfTokens'])} %", (x, y), textcoords="offset points",
                                    xytext=(4, 3), fontsize=6.2, color=C_MAIN)
        ax.scatter([100 * obs_leg], [100 * obs], marker="s", color=C_ALT, s=16, zorder=4, label="observed log")
        ax.scatter([100 * ASIS_LEGACY], [100 * asis], marker="^", color=C_ACC, s=18, zorder=4, label="as-is model")
        ax.set_xlabel("Legacy items that would be accepted,\naccepted within the hold-out (%)")
        ax.set_ylabel(f"New arrivals decided within {D} days (%)")
        ax.set_ylim(0, 85)
        ax.set_title(f"({'a' if D == 90 else 'b'}) Timeliness target {D} days", fontsize=8, loc="left")
    axes[0].legend(frameon=False, fontsize=6.2, loc="upper right")
    fig.tight_layout(w_pad=1.2)
    save(fig, "figS3_policy_frontier.png")
    return out, obs_leg


if __name__ == "__main__":
    import sys
    if "--r3" in sys.argv:  # round-3 update: redraw only Fig. 1 and Fig. 3
        fig1()
        print(fig3())
        sys.exit()
    fig1()
    t2 = fig2()
    t3 = fig3()
    t4 = fig4()
    t5 = fig5()
    t6 = fig6()
    print("fig2 edges", t2)
    print("fig3", t3)
    print("fig4", t4)
    print("fig6", t6)
