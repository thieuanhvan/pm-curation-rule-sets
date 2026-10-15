"""Round-8 figures: graded control coverage (Fig. 3) and Fig. 4 without the stayer/turnover panel.

Inputs: R7 graded coverage (res_t4_graded_kappa.json) and the throughput/intensity inputs of make_figures_p17.py.
Run: python make_figs_r8.py
"""
import json
import matplotlib.pyplot as plt
import make_figures_p17 as m
import make_figs_r7 as r7

C_MAIN, C_ALT, C_GREY, C_ACC = m.C_MAIN, m.C_ALT, m.C_GREY, m.C_ACC
R7 = (__import__("os").environ.get("P17_PIPELINE", str(next(p for p in __import__("pathlib").Path(__file__).resolve().parents if (p / "pipeline").is_dir()) / "pipeline")) + "/D5req/R7/res_t4_graded_kappa.json")


def qx(q):
    return int(q[:4]) + (int(q[-1]) - 1) / 4


def fig3():
    rows = json.load(open(R7, encoding="utf-8"))["ei_queue_R6"]
    end = 2026.75
    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    styles = [("decision", "share", C_MAIN, "-", "decision (5 controls)"),
              ("intake", "share", C_GREY, ":", "intake"),
              ("exit", "weighted", C_ALT, "--", "exit, permission weighted 0.5"),
              ("fit", "share", C_ACC, "-.", "fit, selection, allocation")]
    for stage, key, col, ls, lab in styles:
        xs, ys = [], []
        for r in rows:
            xs.append(qx(r["from"]))
            ys.append(r[stage][key])
        xs.append(end)
        ys.append(ys[-1])
        off = {"intake": 0.015, "fit": -0.015}.get(stage, 0)
        ax.step(xs, [y + off for y in ys], where="post", color=col, ls=ls, lw=1.4, label=lab)
    for x, t in [(2016.5, "no self-\nacceptance"), (2019.5, "COI"), (2020.25, "organisation"),
                 (2022.25, "COI removed\n(v2 launch)"), (2025.25, "reason")]:
        ax.axvline(x, color="#bbbbbb", lw=0.6)
        ax.text(x + 0.05, 1.08, t, fontsize=6.5, va="bottom")
    ax.set_xlim(2015, end)
    ax.set_ylim(-0.05, 1.3)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylabel("Share of identified controls\ncode-embedded in force")
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False)
    fig.tight_layout()
    m.save(fig, "fig3_graded_coverage_r8.png")


def fig4():
    t1 = m.load("W3/res_t1_rho.json")
    years = [y for y in sorted(t1["by_year_rho"]) if int(y) >= 2016]
    yr = [int(y) for y in years]
    rho_all = [t1["by_year_rho"][y]["rho_all"] for y in years]
    complete = [t1["by_year_rho"][y]["followup_complete"] for y in years]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.6))
    ax = axes[0]
    ax.plot(yr, rho_all, color=C_MAIN, lw=1.1)
    ax.scatter([x for x, k in zip(yr, complete) if k], [s for s, k in zip(rho_all, complete) if k], color=C_MAIN, s=12, zorder=3)
    ax.scatter([x for x, k in zip(yr, complete) if not k], [s for s, k in zip(rho_all, complete) if not k],
               facecolor="white", edgecolor=C_MAIN, s=12, zorder=3)
    ax.axhline(1, color=C_GREY, lw=0.7, ls=":")
    ax.set_ylabel("Decisions per arrival")
    ax.set_xticks([2016, 2019, 2022, 2025])
    ax.set_ylim(0, 1.05)
    ax.set_title("(a) Throughput ratio", fontsize=8, loc="left")
    ax = axes[1]
    eff = t1["decider_effort_by_year"]
    dpd = [[eff[y]["ev_decisions_per_moderator_active_day"][0]] + eff[y]["ev_decisions_per_active_day_CI_cluster_moderator"]
           for y in years]
    ax.errorbar(yr, [v[0] for v in dpd], yerr=[[v[0] - v[1] for v in dpd], [v[2] - v[0] for v in dpd]],
                color=C_MAIN, lw=1.1, marker="o", ms=3, capsize=1.5, elinewidth=0.7)
    ax.set_ylabel("Evidence decisions per\nactive editor-day")
    ax.set_ylim(0, 4.6)
    ax.set_xticks([2016, 2019, 2022, 2025])
    ax.set_title("(b) Decision intensity", fontsize=8, loc="left")
    fig.tight_layout(w_pad=0.8)
    m.save(fig, "fig4_throughput_intensity_r8.png")


if __name__ == "__main__":
    fig3()
    fig4()
