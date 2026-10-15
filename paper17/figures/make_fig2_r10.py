"""Fig. 2 (as-is BPMN) with the deciding role named editor throughout. 14/10/2026 (v3): reason "not coded" until 2025, same-organisation annotation removed (review round 8).

Applies the round-7 wording of make_figs_r7.fig2 and replaces the remaining 'Moderate revision' label.
Run: python make_fig2_r10.py
"""
import inspect
import make_figures_isad as isad

NL = "\\n"
PAIRS = [
    ("documented, not" + NL + "enforced (17.8 %)", "inferred norm, never" + NL + "in code (17.8 %)"),
    ('"scheduled' + NL + 'job", timer=True', '"bot' + NL + 'run"'),
    ("Check: role ≥ editor,", "Code guard: editor,"),
    ("Moderate revision;", "Decide on revision;"),
    ("Reject; reason not" + NL + "required until 2025", "Reject; reason not" + NL + "coded until 2025"),
    ("newest-first service (u = 0.18); same-organisation" + NL + "acceptances 37 % to 62 % (random 22-23 %)",
     "newest-first service: ū = 0.18" + NL + "(all pending items, h = infinite)"),
    ("68.6 % of pending:" + NL + "submitter-inactive)", "68.6 % of pending items:" + NL + "no activity, submitter inactive)"),
    ("inferred norm, never" + NL + "in code (17.8 %)", "inferred norm, never" + NL + "in code (violated in 17.7 %)"),
    ("10.7 %", "10.6 %"),
    ('"fig2_bpmn_asis.png"', '"fig2_bpmn_asis_v3.png"'),
]


def main():
    src = inspect.getsource(isad.fig_bpmn_asis)
    for a, b in PAIRS:
        assert a in src, a
        src = src.replace(a, b)
    assert "oderat" not in src
    ns = dict(vars(isad))
    exec(src, ns)
    ns["fig_bpmn_asis"]()


if __name__ == "__main__":
    main()
