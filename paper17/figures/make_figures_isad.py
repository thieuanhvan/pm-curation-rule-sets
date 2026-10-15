"""Draw the analysis-and-design figures (use cases, as-is and to-be BPMN, event-log ERD).

Diagrams only: every number shown is taken from the results already reported in the manuscript.
Images carry no figure number or caption; captions are in the section text. 400 dpi PNG.
Run: python make_figures_isad.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DPI = 400
plt.rcParams.update({"font.family": "Arial", "font.size": 6, "savefig.bbox": "tight", "savefig.pad_inches": 0.03})
C_MAIN, C_ALT, C_GREY, C_ACC = "#1f4e79", "#c55a11", "#7f7f7f", "#548235"
C_FILL, C_PART, C_LANE = "#ffffff", "#e8eef5", "#f7f7f7"


def canvas(w_in, h_in, xmax, ymax):
    fig, ax = plt.subplots(figsize=(w_in, h_in))
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def save(fig, name):
    fig.savefig(os.path.join(HERE, name), dpi=DPI)
    plt.close(fig)
    print("wrote", name)


def arrow(ax, p, q, ls="-", color="#333333", head="-|>", lw=0.6, rad=0.0, ms=5, fc=None):
    a = FancyArrowPatch(p, q, arrowstyle=head, mutation_scale=ms, lw=lw, ls=ls, color=color,
                        connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0)
    if fc is not None:
        a.set_facecolor(fc)
    ax.add_patch(a)


def poly(ax, pts, ls="-", color="#333333", lw=0.6, end_arrow=True):
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        ax.plot([x0, x1], [y0, y1], color=color, lw=lw, ls=ls, solid_capstyle="butt")
    if end_arrow:
        arrow(ax, pts[-2], pts[-1], ls=ls, color=color, lw=lw)
    else:
        ax.plot([pts[-2][0], pts[-1][0]], [pts[-2][1], pts[-1][1]], color=color, lw=lw, ls=ls)


# ------------------------------------------------------------------ Fig A use-case model
def actor(ax, x, y, label):
    ax.add_patch(Circle((x, y + 3.0), 1.1, fill=False, lw=0.7, ec="#222222"))
    ax.plot([x, x], [y + 1.9, y - 0.8], color="#222222", lw=0.7)
    ax.plot([x - 1.8, x + 1.8], [y + 1.1, y + 1.1], color="#222222", lw=0.7)
    ax.plot([x, x - 1.5], [y - 0.8, y - 3.0], color="#222222", lw=0.7)
    ax.plot([x, x + 1.5], [y - 0.8, y - 3.0], color="#222222", lw=0.7)
    ax.text(x, y - 4.2, label, ha="center", va="top", fontsize=5.8)


def usecase(ax, x, y, text, state="impl", w=21, h=6.2):
    ls = "--" if state == "prop" else "-"
    fc = C_PART if state == "part" else C_FILL
    ec = C_ALT if state == "prop" else C_MAIN
    ax.add_patch(Ellipse((x, y), w, h, fc=fc, ec=ec, lw=0.7, ls=ls, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=5.4, zorder=4)
    return (x, y, w / 2, h / 2)


def edge_pt(uc, toward):
    import math
    x, y, a, b = uc
    dx, dy = toward[0] - x, toward[1] - y
    t = 1.0 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2)
    return (x + dx * t, y + dy * t)


def assoc(ax, actor_xy, uc, side=1):
    ax_, ay = actor_xy
    start = (ax_ + 2.4 * side, ay + 1.0)
    end = edge_pt(uc, start)
    ax.plot([start[0], end[0]], [start[1], end[1]], color="#555555", lw=0.45, zorder=2)


def fig_usecase():
    fig, ax = canvas(7.2, 6.6, 110, 101)
    ax.add_patch(Rectangle((17, 0.5), 76, 100, fill=False, lw=0.9, ec="#222222"))
    ax.text(19, 99, "Review application (expert-gated curation)", ha="left", va="top", fontsize=6.2, style="italic")
    cur, edi, adm = (7, 76), (7, 46), (7, 16)
    bot, imp, sch, con = (103, 84), (103, 64), (103, 44), (103, 10)
    for xy, lab in [(cur, "Curator\n(submitter)"), (edi, "Editor\n(moderator)"), (adm, "Administrator"),
                    (bot, "Machine\n(extractor, bot)"), (imp, "Bulk importer"), (sch, "Scheduler\n(timer)"),
                    (con, "Consumer")]:
        actor(ax, xy[0], xy[1], lab)
    L, R = 37, 73
    u = {}
    u["submit"] = usecase(ax, L, 92, "Submit item\n(source claim, source)")
    u["revise"] = usecase(ax, L, 83, "Suggest revision\nwith rationale")
    u["flag"] = usecase(ax, L, 74, "Comment or flag")
    u["withdraw"] = usecase(ax, L, 65, "Withdraw own\nsubmission")
    u["queue"] = usecase(ax, L, 56, "Review machine\nproposal in queue")
    u["decide"] = usecase(ax, L, 46, "Accept or reject\nitem or revision", state="part")
    u["resolve"] = usecase(ax, L, 36, "Resolve flag", state="part")
    u["sign"] = usecase(ax, L, 27, "Sign assertion\n(valid COI)", state="part")
    u["accounts"] = usecase(ax, L, 7, "Manage accounts,\nroles, invite codes", state="part")
    u["propose"] = usecase(ax, R, 92, "Propose machine\nvalue")
    u["batch"] = usecase(ax, R, 72, "Load bulk batch within\npledged review capacity", state="part")
    u["stale"] = usecase(ax, R, 56, "Mark stale tier", state="prop")
    u["reason"] = usecase(ax, R, 46, "Record rejection\nreason code", state="part")
    u["monitor"] = usecase(ax, R, 34, "Monitor decision\neffort and intake", state="prop")
    u["ocel"] = usecase(ax, R, 24, "Export OCEL 2.0\nevent log", state="prop")
    u["release"] = usecase(ax, R, 15, "Release accepted\nrows")
    u["browse"] = usecase(ax, R, 6, "Browse released\ngraph")
    for k in ("submit", "revise", "flag", "withdraw", "queue"):
        assoc(ax, cur, u[k])
    for k in ("queue", "decide", "resolve", "sign", "monitor"):
        assoc(ax, edi, u[k])
    for k in ("accounts", "ocel", "release"):
        assoc(ax, adm, u[k])
    for k in ("propose", "flag"):
        assoc(ax, bot, u[k], side=-1)
    assoc(ax, imp, u["batch"], side=-1)
    assoc(ax, sch, u["stale"], side=-1)
    assoc(ax, con, u["browse"], side=-1)
    # include: decide -> reason; queue -> propose (machine value shown or hidden)
    arrow(ax, (L + 10.5, 46), (R - 10.5, 46), ls="--", head="->", lw=0.5)
    ax.text((L + R) / 2, 47.0, "«include»", ha="center", va="bottom", fontsize=5)
    # generalisation: Editor is a Curator, Administrator is an Editor
    arrow(ax, (cur[0], edi[1] + 4.6), (cur[0], cur[1] - 7.6), head="-|>", lw=0.6, ms=7, fc="white")
    arrow(ax, (adm[0], adm[1] + 4.6), (adm[0], edi[1] - 7.6), head="-|>", lw=0.6, ms=7, fc="white")
    # legend
    ly = -4.5
    for i, (st, lab) in enumerate([("impl", "implemented"), ("part", "partly implemented"), ("prop", "proposed")]):
        x0 = 22 + i * 26
        ax.add_patch(Ellipse((x0, ly), 7, 3, fc=C_PART if st == "part" else C_FILL,
                             ec=C_ALT if st == "prop" else C_MAIN, ls="--" if st == "prop" else "-", lw=0.7))
        ax.text(x0 + 4.5, ly, lab, va="center", fontsize=5.4)
    ax.set_ylim(-7, 101)
    save(fig, "figS4_usecase.png")


# ------------------------------------------------------------------ BPMN helpers
def lanes(ax, names, x0, x1, top, h, pool):
    n = len(names)
    ax.add_patch(Rectangle((x0, top - n * h), x1 - x0, n * h, fill=False, lw=0.8, ec="#222222"))
    ax.add_patch(Rectangle((x0, top - n * h), 5, n * h, fc="#e6e6e6", lw=0.8, ec="#222222"))
    ax.text(x0 + 2.5, top - n * h / 2, pool, rotation=90, ha="center", va="center", fontsize=6.2)
    centres = []
    for i, nm in enumerate(names):
        y = top - (i + 1) * h
        ax.add_patch(Rectangle((x0 + 5, y), x1 - x0 - 5, h, fc=C_LANE if i % 2 == 0 else "white", lw=0.5, ec="#444444"))
        ax.add_patch(Rectangle((x0 + 5, y), 5, h, fc="#f0f0f0", lw=0.5, ec="#444444"))
        ax.text(x0 + 7.5, y + h / 2, nm, rotation=90, ha="center", va="center", fontsize=5.6)
        centres.append(y + h / 2)
    return centres


def task(ax, x, y, text, w=17, h=9, prop=False, tag=None, fs=5.0):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=1.4",
                                fc="white", ec=C_ALT if prop else C_MAIN, lw=0.7, ls="--" if prop else "-", zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=4)
    if tag:
        ax.text(x + w / 2, y + h / 2 + 0.3, tag, ha="right", va="bottom", fontsize=4.4, color=C_ALT,
                fontweight="bold", zorder=5)
    return {"l": (x - w / 2, y), "r": (x + w / 2, y), "t": (x, y + h / 2), "b": (x, y - h / 2), "c": (x, y)}


def event(ax, x, y, kind="start", label=None, prop=False, r=2.4, timer=False, below=True):
    lw = {"start": 0.6, "end": 1.6, "inter": 0.6}[kind]
    ec = C_ALT if prop else "#222222"
    ax.add_patch(Circle((x, y), r, fc="white", ec=ec, lw=lw, ls="--" if prop else "-", zorder=3))
    if kind == "inter":
        ax.add_patch(Circle((x, y), r * 0.78, fill=False, ec=ec, lw=0.5, zorder=4))
    if timer:
        ax.add_patch(Circle((x, y), r * 0.55, fill=False, ec=ec, lw=0.4, zorder=4))
        ax.plot([x, x], [y, y + r * 0.45], color=ec, lw=0.4, zorder=5)
        ax.plot([x, x + r * 0.35], [y, y], color=ec, lw=0.4, zorder=5)
    if label:
        ax.text(x, y - r - 0.8 if below else y + r + 0.8, label, ha="center", va="top" if below else "bottom", fontsize=4.8)
    return {"l": (x - r, y), "r": (x + r, y), "t": (x, y + r), "b": (x, y - r), "c": (x, y)}


def gateway(ax, x, y, kind="xor", label=None, prop=False, s=3.2):
    ec = C_ALT if prop else "#222222"
    ax.add_patch(Polygon([(x - s, y), (x, y + s), (x + s, y), (x, y - s)], closed=True, fc="white", ec=ec, lw=0.7,
                         ls="--" if prop else "-", zorder=3))
    if kind == "xor":
        d = s * 0.38
        ax.plot([x - d, x + d], [y - d, y + d], color=ec, lw=0.7, zorder=4)
        ax.plot([x - d, x + d], [y + d, y - d], color=ec, lw=0.7, zorder=4)
    elif kind == "event":
        ax.add_patch(Circle((x, y), s * 0.5, fill=False, ec=ec, lw=0.4, zorder=4))
        ax.add_patch(Circle((x, y), s * 0.4, fill=False, ec=ec, lw=0.4, zorder=4))
        ax.add_patch(Polygon([(x, y + s * 0.25), (x + s * 0.24, y + s * 0.07), (x + s * 0.15, y - s * 0.2),
                              (x - s * 0.15, y - s * 0.2), (x - s * 0.24, y + s * 0.07)], closed=True, fill=False,
                             ec=ec, lw=0.35, zorder=5))
    if label:
        ax.text(x, y + s + 0.6, label, ha="center", va="bottom", fontsize=4.8)
    return {"l": (x - s, y), "r": (x + s, y), "t": (x, y + s), "b": (x, y - s), "c": (x, y)}


def dataobj(ax, x, y, text, prop=False, w=7, h=8.5):
    ec = C_ALT if prop else "#222222"
    ax.add_patch(Polygon([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2 - 2),
                          (x + w / 2 - 2, y + h / 2), (x - w / 2, y + h / 2)], closed=True, fc="white", ec=ec, lw=0.6,
                         ls="--" if prop else "-", zorder=3))
    ax.text(x, y - h / 2 - 0.8, text, ha="center", va="top", fontsize=4.8)
    return {"l": (x - w / 2, y), "r": (x + w / 2, y), "t": (x, y + h / 2), "b": (x, y - h / 2)}


def note(ax, x, y, text, w, h, anchor=None):
    ax.plot([x, x, x + 1.2], [y - h / 2, y + h / 2, y + h / 2], color="#555555", lw=0.5)
    ax.plot([x, x + 1.2], [y - h / 2, y - h / 2], color="#555555", lw=0.5)
    ax.text(x + 0.9, y, text, ha="left", va="center", fontsize=4.7, color="#333333")
    if anchor:
        ax.plot([x, anchor[0]], [y, anchor[1]], color="#777777", lw=0.45, ls=":")


def flow(ax, pts, ls="-", label=None, lpos=None, color="#333333"):
    poly(ax, pts, ls=ls, color=color)
    if label:
        lx, ly = lpos if lpos else pts[0]
        ax.text(lx, ly, label, fontsize=4.6, ha="left", va="bottom")


def msg(ax, pts, label=None, lpos=None):
    poly(ax, pts, ls=(0, (2.5, 1.5)), color="#555555")
    ax.add_patch(Circle(pts[0], 0.6, fc="white", ec="#555555", lw=0.5, zorder=4))
    if label:
        ax.text(lpos[0], lpos[1], label, fontsize=4.6, ha="left", va="bottom")


# ------------------------------------------------------------------ Fig B as-is BPMN (CIViC)
def fig_bpmn_asis():
    H = 25
    fig, ax = canvas(7.2, 4.5, 172, 104)
    ys = lanes(ax, ["Curator (submitter)", "CIViC platform", "Editor", "Bot"], 0, 172, 102, H, "CIViC")
    yc, yp, ye, yb = ys
    s = event(ax, 18, yc, "start", "evidence\nfound")
    t1 = task(ax, 33, yc, "Submit\nevidence item")
    flow(ax, [s["r"], t1["l"]])
    t2 = task(ax, 33, yp, "Store as submitted;\nlist publicly", w=21)
    flow(ax, [t1["b"], t2["t"]])
    g1 = gateway(ax, 52, yp, "event")
    flow(ax, [t2["r"], g1["l"]])
    # branch: submitter withdraws (coded as a rejection by the submitter)
    t3 = task(ax, 66, yc, "Withdraw\n(reject own item)", w=19)
    flow(ax, [g1["t"], (52, yc), t3["l"]])
    e1 = event(ax, 84, yc, "end", "withdrawn")
    flow(ax, [t3["r"], e1["l"]])
    # branch: an editor picks the item
    t4 = task(ax, 66, ye, "Select and\nreview item")
    flow(ax, [g1["b"], (52, ye), t4["l"]])
    g2 = gateway(ax, 84, ye, "xor")
    flow(ax, [t4["r"], g2["l"]])
    t5 = task(ax, 104, yp, "Check: role ≥ editor,\nnot the submitter", w=22)
    flow(ax, [g2["t"], (84, yp), t5["l"]], label="accept", lpos=(85, yp - 6))
    e2 = event(ax, 122, yp, "end", "accepted")
    flow(ax, [t5["r"], e2["l"]])
    t6 = task(ax, 104, ye, "Reject; reason not\nrequired until 2025", w=20)
    flow(ax, [g2["r"], t6["l"]], label="reject", lpos=(87, ye + 0.5))
    e3 = event(ax, 122, ye, "end", "rejected")
    flow(ax, [t6["r"], e3["l"]])
    # revision layer
    s2 = event(ax, 137, yc, "start", "change\nneeded")
    t7 = task(ax, 153, yc, "Suggest revision", w=18)
    flow(ax, [s2["r"], t7["l"]])
    t8 = task(ax, 153, ye, "Moderate revision;\nreason required\nsince 2022", w=19, h=10)
    flow(ax, [t7["b"], t8["t"]])
    e4 = event(ax, 168, ye, "end", "decided")
    flow(ax, [t8["r"], e4["l"]])
    # bot flags
    s3 = event(ax, 18, yb, "start", "scheduled\njob", timer=True)
    t9 = task(ax, 33, yb, "Raise flag")
    flow(ax, [s3["r"], t9["l"]])
    d1 = dataobj(ax, 49, yb, "open flag")
    flow(ax, [t9["r"], d1["l"]], ls=":")
    t10 = task(ax, 33, ye, "Resolve flag\n(optional)")
    flow(ax, [d1["t"], (49, ye - 7), (33, ye - 7), t10["b"]], ls=":")
    note(ax, 60, yb, "resolution logged for 10.7 % of bot flags;\n2,201 bot flags bulk-closed during the 2023\ndata-model migration without per-flag events", 40, 9)
    note(ax, 58, yp + 1, "no timer or expiry:\nitem stays submitted\n(68.6 % of pending:\nsubmitter-inactive)", 20, 12, anchor=g1["r"])
    note(ax, 127.5, yp + 1, "no acceptance while a\nrevision is pending:\ndocumented, not\nenforced (17.8 %)", 20, 12, anchor=e2["r"])
    note(ax, 58, ye - 8.5, "newest-first service (u = 0.18); same-organisation\nacceptances 37 % to 62 % (random 22-23 %)", 36, 6)
    save(fig, "fig2_bpmn_asis.png")


# ------------------------------------------------------------------ Fig C to-be BPMN (review app)
def fig_bpmn_tobe():
    H = 25
    fig, ax = canvas(7.2, 5.5, 172, 128)
    ys = lanes(ax, ["Curator", "Machine (bot,\nimporter)", "Review service", "Editor", "Scheduler"], 0, 172, 127, H,
               "Review application")
    yc, ym, ys_, ye, yt = ys
    # curator submits; the flow runs down the left margin to the service lane
    s = event(ax, 17, yc, "start", "claim found\nin a source")
    t1 = task(ax, 32, yc, "Submit item or\nrevision with\nrationale", h=10)
    flow(ax, [s["r"], t1["l"]])
    t4 = task(ax, 33, ys_, "Write event: role and\norganisation at event\ntime, actor type", w=25, h=10.5, prop=True, tag="DP1")
    flow(ax, [t1["b"], (32, yc - 8), (12.5, yc - 8), (12.5, ys_), t4["l"]])
    # machine lane: bulk intake behind a quota gateway
    sb = event(ax, 18, ym, "start", "loader run")
    t2 = task(ax, 33, ym, "Load rows from\nan extraction run", tag="DP6")
    flow(ax, [sb["r"], t2["l"]])
    g0 = gateway(ax, 50, ym, "xor", prop=True)
    ax.text(50, ym + 4.0, "within pledged\ncapacity?", ha="center", va="bottom", fontsize=4.6)
    flow(ax, [t2["r"], g0["l"]])
    t3 = task(ax, 66, ym, "Hold batch until\ncapacity pledged", prop=True, tag="DP6")
    flow(ax, [g0["r"], t3["l"]], label="no", lpos=(53.5, ym + 0.4))
    flow(ax, [g0["b"], (50, ys_ + 8.5), (40, ys_ + 8.5), (40, ys_ + 5.25)], label="yes", lpos=(50.8, ym - 9))
    t5 = task(ax, 64, ys_, "Route to owned queue\n(owner, due date)", w=25, prop=True, tag="DP3")
    flow(ax, [t4["r"], t5["l"]])
    # machine flag or proposal enters the same queue
    tb = task(ax, 106, ym, "Raise flag or\npropose value", w=17)
    sbot = event(ax, 124, ym, "start", "check\nrule fires")
    flow(ax, [sbot["l"], tb["r"]])
    flow(ax, [tb["b"], (106, ys_ + 8), (68, ys_ + 8), (68, ys_ + 4.5)])
    g1 = gateway(ax, 84, ys_, "event")
    flow(ax, [t5["r"], g1["l"]])
    # branch 1: withdrawal by the submitter
    t10 = task(ax, 100, yc, "Withdraw own\nsubmission")
    flow(ax, [g1["t"], (84, yc), t10["l"]])
    e2 = event(ax, 117, yc, "end", "withdrawn")
    flow(ax, [t10["r"], e2["l"]])
    # branch 2: an editor opens the item
    t6 = task(ax, 97, ye, "Open worklist item\n(opened at)", w=21)
    flow(ax, [g1["r"], (97, ys_), t6["t"]])
    g2 = gateway(ax, 113, ye, "xor")
    flow(ax, [t6["r"], g2["l"]])
    t7 = task(ax, 130, ye, "Select reason\ncode and note", w=19, tag="DP2")
    flow(ax, [g2["r"], t7["l"]])
    ax.text(116.5, ye - 3.2, "reject", fontsize=4.6, va="top")
    t8 = task(ax, 131, ys_, "Guard in store: not own\nitem, role valid now,\nreason present", w=26, h=10.5,
              prop=True, tag="DP2")
    flow(ax, [g2["t"], (113, ys_), t8["l"]])
    ax.text(108.2, ys_ + 0.6, "accept", fontsize=4.6)
    flow(ax, [t7["t"], (130, ys_ - 5.25)])
    t9 = task(ax, 158, ys_, "Write decision and\ntrace in one\ntransaction", w=20, h=10.5, tag="DP1")
    flow(ax, [t8["r"], t9["l"]])
    e1 = event(ax, 165, ye, "end", "accepted or\nrejected")
    flow(ax, [t9["b"], (158, ye), e1["l"]])
    # branch 3: timer, the item becomes stale but stays in the queue
    st = event(ax, 84, yt, "inter", "T days without\nactivity", prop=True, timer=True)
    flow(ax, [g1["b"], st["t"]])
    t11 = task(ax, 104, yt, "Mark stale tier\n(visible, kept)", w=18, prop=True, tag="DP5")
    flow(ax, [st["r"], t11["l"]])
    flow(ax, [t11["t"], (104, yt + 8), (74, yt + 8), (74, ys_ - 7), (64, ys_ - 7), t5["b"]], ls=(0, (3, 1.5)))
    # monitoring and export
    sm = event(ax, 17, yt, "start", "monthly", prop=True, timer=True)
    t12 = task(ax, 35, yt, "Compute team-level\nintensity and intake", w=21, prop=True, tag="DP4 DP6")
    flow(ax, [sm["r"], t12["l"]])
    d1 = dataobj(ax, 54, yt, "monitor view", prop=True)
    flow(ax, [t12["r"], d1["l"]], ls=":")
    sx = event(ax, 132, yt, "start", "nightly", prop=True, timer=True)
    t13 = task(ax, 151, yt, "Export OCEL 2.0\nevent log", w=19, prop=True, tag="DP1")
    flow(ax, [sx["r"], t13["l"]])
    # legend
    ly = -4
    ax.add_patch(FancyBboxPatch((10, ly - 2), 8, 4, boxstyle="round,pad=0,rounding_size=1", fc="white", ec=C_MAIN, lw=0.7))
    ax.text(19.5, ly, "implemented in the application", va="center", fontsize=5)
    ax.add_patch(FancyBboxPatch((62, ly - 2), 8, 4, boxstyle="round,pad=0,rounding_size=1", fc="white", ec=C_ALT, lw=0.7, ls="--"))
    ax.text(71.5, ly, "proposed (not yet implemented)", va="center", fontsize=5)
    ax.text(118, ly, "DPn: design principle realised", va="center", fontsize=5, color=C_ALT, fontweight="bold")
    ax.set_ylim(-7, 128)
    save(fig, "fig6_bpmn_tobe.png")


# ------------------------------------------------------------------ Fig D ERD of the event log
def entity(ax, x, y_top, w, name, sub, attrs, state="impl"):
    """attrs: list of (text, proposed: bool). state: impl | part | prop."""
    lh = 2.25
    h = 3.6 + lh * len(attrs) + (1.6 if sub else 0) + 0.6
    ec = C_ALT if state == "prop" else C_MAIN
    ls = "--" if state == "prop" else "-"
    ax.add_patch(Rectangle((x, y_top - h), w, h, fc="white", ec=ec, lw=0.8, ls=ls, zorder=3))
    ax.add_patch(Rectangle((x, y_top - 3.6), w, 3.6, fc=C_PART if state != "prop" else "#fbe9dc", ec=ec, lw=0.8,
                           ls=ls, zorder=3))
    ax.text(x + w / 2, y_top - 1.8, name, ha="center", va="center", fontsize=5.6, fontweight="bold", zorder=4)
    yy = y_top - 3.6 - 0.4
    if sub:
        ax.text(x + w / 2, yy - 0.7, sub, ha="center", va="center", fontsize=4.4, style="italic", color=C_GREY, zorder=4)
        yy -= 1.6
    for txt, prop in attrs:
        yy -= lh
        ax.text(x + 0.7, yy + lh / 2, txt, ha="left", va="center", fontsize=4.7, zorder=4,
                color=C_ALT if prop else "#222222", style="italic" if prop else "normal")
    return {"x": x, "y": y_top - h, "w": w, "h": h, "top": y_top}


def rel(ax, p, q, a="1", b="N", ls="-"):
    ax.plot([p[0], q[0]], [p[1], q[1]], color="#444444", lw=0.5, ls=ls, zorder=2)
    ax.text(p[0] + (q[0] - p[0]) * 0.08, p[1] + (q[1] - p[1]) * 0.08 + 0.5, a, fontsize=4.6, color="#444444")
    ax.text(p[0] + (q[0] - p[0]) * 0.88, p[1] + (q[1] - p[1]) * 0.88 + 0.5, b, fontsize=4.6, color="#444444")


def fig_erd():
    fig, ax = canvas(7.2, 7.4, 104, 108)
    ax.set_xlim(-5, 104)
    P = True
    ax.text(0, 107, "(a) Event-log core aligned with OCEL 2.0", fontsize=6.2, fontweight="bold", va="top")
    ax.plot([0, 104], [52.5, 52.5], color="#bbbbbb", lw=0.6, ls="--")
    ax.text(26, 51, "(b) Time-aware validity, queues and worklists", fontsize=6.2, fontweight="bold", va="top")
    actor_ = entity(ax, 0, 102, 21, "ACTOR", "Actor", [("actor_id  PK", 0), ("kind (current role)", 0), ("display_name", 0),
                                                         ("coi_statement, coi_date", 0), ("actor_type", P)], "part")
    org = entity(ax, 0, 76, 21, "ORGANISATION", "Organization", [("org_id  PK", 0), ("name, kind", 0), ("parent_id", 0)])
    ev = entity(ax, 26, 102, 24, "EVENT", "AuditLog", [("event_id  PK", 0), ("activity (action)", 0), ("at", 0),
                                                       ("actor_id  FK", 0), ("via (channel)", 0), ("note", 0),
                                                       ("role_at_event", P), ("org_at_event  FK", P), ("actor_type", P),
                                                       ("batch_id  FK", P), ("reason_code  FK", P)], "part")
    e2o = entity(ax, 55, 102, 21, "EVENT_OBJECT", "AuditLog table_name, row_id",
                 [("event_id  FK", 0), ("object_id  FK", 0), ("qualifier", P)], "part")
    obj = entity(ax, 81, 102, 23, "OBJECT", "SourceClaim, Revision, Comment ...",
                 [("object_id  PK", 0), ("object_type", 0), ("curation_status", 0), ("record_status (tombstone)", 0),
                  ("deprecation reason (log note)", 0)])
    chg = entity(ax, 55, 85, 21, "OBJECT_CHANGE", "AuditLog field, old, new",
                 [("event_id  FK", 0), ("object_id  FK", 0), ("field", 0), ("old_value, new_value", 0)])
    o2o = entity(ax, 81, 77, 23, "OBJECT_OBJECT", "Revision, Comment, edges",
                 [("source_id  FK", 0), ("target_id  FK", 0), ("qualifier: revises, flags,", 0), ("comments_on, part_of", 0)])
    batch = entity(ax, 26, 69, 24, "BATCH", None, [("batch_id  PK", 0), ("loader, code_version", 0), ("started_at, n_rows", 0),
                                                   ("pledged_capacity", 0)], "prop")
    rc = entity(ax, 55, 66, 21, "REASON_CODE", None, [("code  PK", 0), ("applies_to (queue)", 0), ("label", 0)], "prop")
    # relations (a)
    rel(ax, (21, 95), (26, 95))
    rel(ax, (21, 70), (26, 86))
    rel(ax, (50, 98), (55, 98))
    rel(ax, (81, 98), (76, 98))
    rel(ax, (50, 82), (55, 80))
    rel(ax, (81, 89), (76, 80))
    rel(ax, (92.5, obj["y"]), (92.5, o2o["top"]), "1", "N")
    rel(ax, (38, batch["top"]), (38, ev["y"]), "1", "N", ls="--")
    rel(ax, (55, 62), (50, 75), "1", "N", ls="--")
    # (b)
    role = entity(ax, 0, 20, 21, "ACTOR_ROLE", None, [("actor_id  FK", 0), ("role", 0), ("valid_from", 0), ("valid_until", 0)], "prop")
    mem = entity(ax, 0, 46, 21, "MEMBER_OF", "MEMBER_OF", [("actor_id  FK", 0), ("org_id  FK", 0), ("role", 0),
                                                            ("from_date", 0), ("to_date (valid until)", 0)])
    coi = entity(ax, 25, 46, 22, "COI_STATEMENT", "Actor coi_statement, coi_date",
                 [("actor_id  FK", 0), ("statement", 0), ("signed_at", 0), ("valid_until", P)], "part")
    q = entity(ax, 25, 23, 22, "QUEUE", None, [("queue_id  PK", 0), ("object_type", 0), ("owner_id  FK", 0),
                                               ("service_rule", 0), ("due_days, stale_after", 0)], "prop")
    wl = entity(ax, 51, 46, 23, "WORKLIST_ITEM", "app_round, app_round_item",
                [("round; item_id (object FK)", 0), ("assigned_to  FK", 0), ("queue_id  FK", P), ("valid_from", P), ("valid_until", P),
                 ("due_at", P), ("tier: live, dormant, stale", P), ("tier_since", P)], "part")
    tr = entity(ax, 78, 46, 26, "DECISION_TRACE", "app_decision_trace",
                [("trace_id  PK", 0), ("queue; row_id (object FK), field", 0), ("machine_value, machine_actor", 0),
                 ("final_value, action", 0), ("reason_code, note", 0), ("actor", 0), ("opened_at, decided_at, seconds", 0),
                 ("blind, open_event", 0)])
    # ACTOR (left edge) -> ACTOR_ROLE, ORGANISATION (left edge) -> MEMBER_OF, ACTOR -> MEMBER_OF (elbow on the left margin)
    elbow = lambda pts, ls="-": ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#444444", lw=0.5, ls=ls, zorder=2)
    elbow([(0, actor_["y"] + 3), (-2, actor_["y"] + 3), (-2, role["top"] - 3), (0, role["top"] - 3)], ls="--")
    ax.text(-1.8, actor_["y"] + 3.4, "1", fontsize=4.6, color="#444444")
    ax.text(-1.8, role["top"] - 2.6, "N", fontsize=4.6, color="#444444")
    elbow([(0, actor_["y"] + 6), (-3.5, actor_["y"] + 6), (-3.5, mem["top"] - 3), (0, mem["top"] - 3)])
    ax.text(-3.3, mem["top"] - 2.6, "N", fontsize=4.6, color="#444444")
    rel(ax, (18, org["y"]), (18, mem["top"]))
    elbow([(21, actor_["y"] + 1), (23.5, actor_["y"] + 1), (23.5, coi["top"] - 2), (25, coi["top"] - 2)])
    ax.text(21.3, actor_["y"] + 1.4, "1", fontsize=4.6, color="#444444")
    ax.text(23.8, coi["top"] - 1.6, "N", fontsize=4.6, color="#444444")
    rel(ax, (47, 16), (51, wl["y"] + 4), ls="--")
    # legend
    ly = -3.5
    ax.add_patch(Rectangle((0, ly - 1.5), 6, 3, fc="white", ec=C_MAIN, lw=0.8))
    ax.text(7, ly, "implemented", va="center", fontsize=5)
    ax.add_patch(Rectangle((22, ly - 1.5), 6, 3, fc="white", ec=C_ALT, lw=0.8, ls="--"))
    ax.text(29, ly, "proposed entity", va="center", fontsize=5)
    ax.text(48, ly, "italic attribute", va="center", fontsize=5, color=C_ALT, style="italic")
    ax.text(62, ly, "= proposed attribute; grey italic = current table", va="center", fontsize=5)
    ax.set_ylim(-6, 108)
    save(fig, "figS5_erd_eventlog.png")


if __name__ == "__main__":
    fig_usecase()
    fig_bpmn_asis()
    fig_bpmn_tobe()
    fig_erd()
