"""Fig. 1 for manuscript v3 (14/10/2026): protocol after the scope reduction (Definitions 1-5), C_inf in the control set,
right edge no longer cropped. Reuses the helpers of make_figures_p17.py. Run: python make_fig1_v3.py -> fig1.png"""
import shutil

import matplotlib.pyplot as plt

import make_figures_p17 as m

C_ACC, C_ALT = m.C_ACC, m.C_ALT


def fig1():
    fig, ax = plt.subplots(figsize=(7.4, 4.1))
    ax.set_xlim(-0.012, 1.012)
    ax.set_ylim(0.0, 1)
    ax.axis("off")
    for x, w, t in [(0.0, 0.22, "Inputs"), (0.265, 0.40, "Measurement protocol"), (0.71, 0.285, "Outputs")]:
        ax.text(x + w / 2, 0.985, t, fontsize=7.5, weight="bold", va="top", ha="center")
    m.box(ax, 0.0, 0.70, 0.22, 0.22, "Public event history\n(status, revision, comment,\nflag events; actor and\norganisation at event time)", fc="#f2f2f2")
    m.box(ax, 0.0, 0.43, 0.22, 0.22, "Source-code, release and\nCI/workflow history\n(every release tag or\nmonthly snapshot)", fc="#f2f2f2")
    m.box(ax, 0.0, 0.16, 0.22, 0.22, "Documented procedure\n(standard operating\nprocedure, guidelines,\nrole definitions)", fc="#f2f2f2")
    m.box(ax, 0.265, 0.47, 0.40, 0.45,
          "Core\n\n"
          "D1  OCEL 2.0 curation log\n"
          "Algorithm 1  code scan: C_code with entry and\n      removal dates τ_c, ρ_c and stage s(c)\n"
          "D2  Control set C = C_doc + C_code + C_inf;\n      time-indexed rule set R(t)\n"
          "D3  Conformance F_R against R(t); enactment f_c;\n      coverage κ_s(t) over nine stages", fc="#eaf1f8", fs=6.3)
    m.box(ax, 0.265, 0.10, 0.40, 0.30,
          "Standard measures, adapted\n\n"
          "D4  Service position u against a permutation null\n"
          "D5  Age hazard of acceptance (delayed entry)\n"
          "Sanity check: flattened vs object-centric", fs=6.3, ls="--")
    m.box(ax, 0.71, 0.70, 0.285, 0.22, "Coverage by stage over time:\nwhich controls the code\nenforces, from and until when", fc="#e2efda", ec=C_ACC)
    m.box(ax, 0.71, 0.43, 0.285, 0.22, "Behaviour where code does not\ndecide: enactment of uncoded\nrules; service order and age\non uncovered stages", fc="#e2efda", ec=C_ACC)
    m.box(ax, 0.71, 0.16, 0.285, 0.22, "CIViC (full); Canto (R(t),\ncoverage); GO and HPO content\ngates; comparison systems", fc="#fbe5d6", ec=C_ALT)
    for y in (0.81, 0.54, 0.27):
        m.arrow(ax, (0.225, y), (0.26, y))
    for y in (0.81, 0.54, 0.27):
        m.arrow(ax, (0.67, y), (0.705, y))
    m.save(fig, "fig1_protocol_v3.png")


if __name__ == "__main__":
    fig1()
    shutil.copy("fig1_protocol_v3.png", "fig1.png")
    print("fig1.png written")
