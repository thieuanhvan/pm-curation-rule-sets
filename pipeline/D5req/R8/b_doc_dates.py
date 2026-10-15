# R8 analysis B: documented-from dates for C_doc controls.
# Sources (public, read-only clones in the a local folder):
#   civic-client (v1 front end; help pages src/app/pages/help*.tpl.html, faq.tpl.html; 2014-2022)
#   civic-docs (civic.readthedocs.io sources, from 2018-10-26)
# plus Danos et al. 2019 SOP (Genome Med 11:76, epub 2019-11-29).
# For each control: first commit at which a doc file matches the pattern. Output res_b_docdates.json
import subprocess, json, re, os
SP = __import__("os").environ["CIVIC_CLONES_DIR"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "res_b_docdates.json")
REPOS = {
    "civic-client": (SP + "/civic-client", ["src/app/pages/help*.tpl.html", "src/app/pages/faq.tpl.html", "src/app/pages/help*.html"]),
    "civic-docs": (SP + "/civic-docs", ["docs/*.rst", ":(exclude)docs/_build"]),
}
# patterns are case-insensitive extended regexes over doc text
CTRL = {
    "C1_account_to_submit": r"(log ?in|sign ?in|account)[^.]{0,80}(submit|add evidence|contribut)|(submit|contribut)[^.]{0,80}(log ?in|sign ?in|account)",
    "C4C6_editor_accepts": r"editors?[^.]{0,120}(accept|approv|moderat)|(accept|approv|moderat)[^.]{0,120}by[^.]{0,30}editor",
    "C5C7_no_self_acceptance": r"(own|their) (submission|contribution|evidence|revision|suggest)[^.]{0,120}(accept|approv|moderat)|(accept|approv|moderat)[^.]{0,120}(own|their) (submission|contribution|evidence|revision|suggest)|cannot (accept|approve|moderate) (their|your) own",
    "C8C9_coi_statement": r"conflicts? of interest|\bCOI\b",
    "C10C11_reason_on_reject": r"reject[^.]{0,160}(reason|comment|explain|justif)|(reason|comment|explain|justif)[^.]{0,160}reject",
    "C2_C13_comment_required": r"(comment|explanation)[^.]{0,80}(required|must)|(required|must)[^.]{0,80}(comment|explanation)",
    "C18_withdraw_own": r"withdraw|(reject|remove)[^.]{0,40}(their|your) own",
    "C25_account_to_flag": r"flag[^.]{0,100}(log|sign|account)|(log|sign|account)[^.]{0,100}flag",
    "C3_pending_revision_rule": r"(pending|outstanding) (revision|suggest|change)s?[^.]{0,160}(before|prior|accept|resolv)|(accept|approv)[^.]{0,160}(pending|outstanding) (revision|suggest|change)",
}

def git(repo, *a):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout

res = {}
for name, (repo, paths) in REPOS.items():
    commits = git(repo, "log", "--reverse", "--format=%h %cs", "--", *[p for p in paths if not p.startswith(":(")]).split("\n")
    commits = [c.split() for c in commits if c.strip()]
    first = {}
    # binary-ish search is unsafe (text can disappear); scan every k-th commit then refine backwards
    step = max(1, len(commits) // 120)
    sampled = list(range(0, len(commits), step)) + [len(commits) - 1]
    for k in CTRL:
        hit = None
        for idx in sampled:
            h, d = commits[idx]
            out = git(repo, "grep", "-i", "-E", "-l", CTRL[k], h, "--", *paths)
            if out.strip():
                hit = idx
                break
        if hit is not None:
            lo = max(0, hit - step)
            for idx in range(lo, hit + 1):
                h, d = commits[idx]
                out = git(repo, "grep", "-i", "-E", "-l", CTRL[k], h, "--", *paths)
                if out.strip():
                    files = [x.split(":", 1)[1] for x in out.split()]
                    m = git(repo, "grep", "-i", "-E", "-h", "-o", "-m1", CTRL[k], h, "--", files[0])
                    first[k] = {"commit": h, "date": d, "files": files[:3], "match": m.strip()[:160]}
                    break
        else:
            first[k] = None
    res[name] = {"n_commits_touching_docs": len(commits), "first_date": commits[0][1], "last_date": commits[-1][1], "first_match": first}
res["danos_2019_sop"] = {"epub": "2019-11-29", "doi": "10.1186/s13073-019-0687-x"}
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1)
print(json.dumps(res, indent=1))
