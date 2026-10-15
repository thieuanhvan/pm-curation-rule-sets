# Blind coding of review controls in a curation platform's source code

You are an independent coder. Your task is to find, from source code only, the **controls** that the platform's code applies to the review (moderation) of contributed content, and to record at which of four code snapshots each control is present.

## Strict blinding rules

- Read ONLY files inside the two repositories in this folder (`civic-server/`, `civic-v2/`), using `git show <rev>:<path>`, `git grep <pattern> <rev>`, `git ls-tree`, `git log` on these repositories.
- Do NOT open any other file or folder on this computer (in particular nothing under `<local workspace>`, nothing in other temporary folders, nothing outside this `blind/` folder except the repos themselves).
- Do NOT search the web, do NOT read the platform's help pages, documentation sites, papers or release notes. Commit messages inside the repos are allowed.
- Do not try to guess what another coder found. Code what the code shows.

## Platform

CIViC, a cancer-variant knowledge base. Registered users submit **evidence items**, suggest **revisions** (changes to fields of existing objects), add **comments**, raise **flags**, make **source suggestions**; editors moderate. There are also **assertions** (aggregate claims) that are moderated. The first platform version is `civic-server` (Ruby on Rails, continuously deployed, no release tags used here); the second version is `civic-v2` (Rails GraphQL server + Angular client, released with tags).

## The four snapshots

| Snapshot | Repository | Revision |
|---|---|---|
| S1 (June 2016) | civic-server | dc8e4edd09ebe60bd0bd2b26b9f53956150b258c |
| S2 (June 2020) | civic-server | bef7ec50c54b162f1b568b8e4eddcc9b26000d3f |
| S3 (v2.0.0, April 2022) | civic-v2 | v2.0.0 |
| S4 (v2.7.6, 2026) | civic-v2 | v2.7.6 |

## What counts as a control

A control is a rule on a review-related event whose truth the code checks or brings about. Record a control when the server-side code does one of these:

- **guard (G):** refuses an event when a predicate fails (raises an error, returns a validation error, denies authorisation), e.g. "only users with role X may accept", "a comment of at least N characters is required";
- **automatic (A):** changes the status of a moderated object without a human decision on that object (callbacks, side effects of another action, scheduled tasks, background jobs);
- **permission (P):** explicitly enables an action for a specific party that otherwise could not do it, without refusing anything else.

Record checks that exist **only in the client** (UI hides or disables a button, but no server layer checks it) as mode **client (C)**, separately. To decide that a check is client-only, look at every server layer on the path (mutation/controller, authorisation hooks, base classes and shared modules, policies, model validations and callbacks).

Do not record generic infrastructure (CSRF, rate limits, generic login for viewing) unless it is specific to contributing or moderating content.

## Stages (assign one per control)

intake (submitting content or suggestions), fit (preconditions on the state of related objects at decision time), selection (which pending item gets reviewed next), allocation (who must review it, assignment, due dates), decision (accept/reject and who may do it), flag raising, flag resolution, exit (an item leaves the queue without a judgement of its correctness: expiry, withdrawal, supersession, timers), re-review (a decided item returns to review).

Also record **absence records**: for each of selection, allocation and exit, state for evidence items whether ANY control exists at each snapshot (e.g. ordering rule, assignment field, due date, expiry timer, scheduled task writing evidence-item status). Look at scheduled-task configuration and background jobs.

## Output

Write a JSON file `OUTPUT_PATH` with:

```json
{
  "coder": "CODER_ID",
  "controls": [
    {"id": "K1", "object_type": "evidence_item|revision|flag|comment|assertion|source_suggestion|cross_cutting",
     "stage": "...", "mode": "G|A|P|C",
     "rule": "one sentence in plain English",
     "present": {"S1": true, "S2": true, "S3": false, "S4": false},
     "evidence": {"S1": "path:approx line or symbol", "S2": "...", "S3": "...", "S4": "..."}}
  ],
  "absences": [
    {"stage": "selection|allocation|exit", "object_type": "evidence_item",
     "any_control": {"S1": false, "S2": false, "S3": false, "S4": false}, "note": "what you checked"}
  ],
  "notes": "anything uncertain"
}
```

Use one entry per distinct rule and object type (if the same rule applies to evidence items and to revisions through different code, record two entries). Be thorough: read the mutation/controller for every moderation action (accept, reject, approve, resolve, withdraw, suggest, flag, comment) at every snapshot. Aim for completeness over speed. When finished, reply with a short summary (number of controls by stage and mode) and the path of the JSON file.
