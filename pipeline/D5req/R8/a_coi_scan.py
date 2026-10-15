# R8 analysis A: where is the COI requirement for evidence-item / assertion moderation in each civic-v2 release?
# Read-only git plumbing on the session clone. Output: res_a_coi.json
import subprocess, json, re, os
REPO = __import__("os").environ["CIVIC_V2_REPO"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "res_a_coi.json")
COI = re.compile(r"coi|conflict_of_interest", re.I)

def git(*a):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout

def show(tag, path):
    return git("show", f"{tag}:{path}")

tags = [t for t in git("tag", "--sort=creatordate").split() if t.startswith("v2")]
dates = {}
for line in git("for-each-ref", "--format=%(refname:short) %(creatordate:short)", "refs/tags").splitlines():
    k, v = line.split()
    dates[k] = v

# server-side layers on the moderation path (GraphQL-Ruby: schema, base classes, ready?/authorized?, activities, concerns, models + callbacks, policies, controller)
def server_layers(tag):
    files = git("ls-tree", "-r", "--name-only", tag, "server/app", "server/config").splitlines()
    sel = []
    for f in files:
        fl = f.lower()
        if any(k in fl for k in ["mutations/moderate_evidence_item", "mutations/moderate_assertion", "mutations/base_mutation",
                                 "mutations/mutation_with_org", "activities/base.rb", "activities/moderate_evidence_item",
                                 "activities/moderate_assertion", "models/concerns/", "controllers/concerns/", "graphql_controller",
                                 "app/policies/", "models/evidence_item.rb", "models/assertion.rb", "models/user.rb",
                                 "models/role.rb", "civic2_schema", "graphql/types/base_", "validators/", "actions/"]):
            sel.append(f)
    return sel

res = []
for t in tags:
    layers = server_layers(t)
    hits = {}
    for f in layers:
        txt = show(t, f)
        if f.endswith("models/user.rb"):
            continue  # helper definition only; usage is what matters
        n = [i + 1 for i, l in enumerate(txt.splitlines()) if COI.search(l)]
        if n:
            hits[f] = n
    # where the COI helper is *called* anywhere in server/app
    callers = sorted(set(l.split(":")[1] for l in git("grep", "-n", "-i", "has_valid_coi\|coi_valid\|valid_coi", t, "--", "server/app").splitlines() if l))
    callers = [c for c in callers if "models/user.rb" not in c and "graphql/types" not in c]
    mod_chain_hits = {f: v for f, v in hits.items() if re.search(r"moderate_(evidence_item|assertion)|base_mutation|mutation_with_org|activities/base|concerns|policies|civic2_schema|graphql_controller|models/(evidence_item|assertion)\.rb|validators", f)}
    cv = show(t, "client/src/app/core/services/viewer/viewer.service.ts")
    m = re.search(r"function canModerate\([^)]*\)[^{]*\{([^}]*)\}", cv)
    client_gate = bool(m and re.search(r"Coi", m.group(1)))
    res.append({"tag": t, "date": dates.get(t), "n_server_layer_files": len(layers),
                "coi_in_moderation_chain_server": bool(mod_chain_hits), "chain_hits": mod_chain_hits,
                "server_coi_callers": callers, "client_canModerate_requires_coi": client_gate})

# v1 reference: where was the 2019 requirement?
summary = {
    "n_tags": len(res),
    "tags_with_server_coi_on_ei_or_assertion_moderation": [r["tag"] for r in res if r["coi_in_moderation_chain_server"]],
    "tags_client_gate": [r["tag"] for r in res if r["client_canModerate_requires_coi"]],
    "first_tag": res[0]["tag"], "last_tag": res[-1]["tag"],
    "callers_first": res[0]["server_coi_callers"], "callers_last": res[-1]["server_coi_callers"],
}
json.dump({"summary": summary, "per_tag": res}, open(OUT, "w", encoding="utf-8"), indent=1)
print(json.dumps(summary, indent=1))
