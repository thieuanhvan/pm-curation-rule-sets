# Blind coding of review controls in the Canto curation tool

You are an independent coder. From source code only, find the **controls** that Canto's code applies to the review of contributed curation, record at which of four snapshots each is present, and date when each entered (and, if so, left) the code.

## Strict blinding rules

- Read ONLY the repository in this folder (`canto/`), using `git show <rev>:<path>`, `git grep <pattern> <rev>`, `git ls-tree`, `git log` (including `git log -S` / `-G` to date changes).
- Do NOT open any other file or folder on this computer and do not look at other coders' output.
- Do NOT search the web or read Canto's documentation sites, papers or mailing lists. Commit messages and files inside the repository (including its own docs folder) are allowed.

## Platform

Canto (PomBase and other model-organism databases) is a web tool in which a **community curator** (typically a paper's author) curates a paper in a **curation session** (gene annotations: GO, phenotypes, interactions, genotypes, alleles), submits it, and a **professional curator / administrator** approves it before the annotations are exported to the database. Sessions move through states (for example SESSION_CREATED, SESSION_ACCEPTED, CURATION_IN_PROGRESS, CURATION_PAUSED, NEEDS_APPROVAL, APPROVAL_IN_PROGRESS, APPROVED, EXPORTED). Administrators also triage papers and may assign sessions to curators. Perl / Catalyst code is mainly under `lib/Canto/`, templates under `root/`, scripts under `script/` and `etc/`.

## The four snapshots

| Snapshot | Revision |
|---|---|
| S1 (January 2012) | v243 |
| S2 (January 2016) | v911 |
| S3 (January 2020) | v1435 |
| S4 (August 2026) | v1878 |

## What counts as a control

A rule on a review-related event whose truth the server-side code checks or brings about:

- **guard (G):** refuses an event when a predicate fails (croak/die, error page, permission denied, state-transition check), e.g. "only admin users can approve sessions";
- **automatic (A):** changes the state of a session or annotation without a human decision on it (scheduled scripts, cron jobs, side effects, reminder or expiry jobs that change state);
- **permission (P):** explicitly enables an action for a specific party that otherwise could not do it, without refusing anything else.

Record checks that exist only in templates or JavaScript (the server does not enforce them) as mode **client (C)**. Do not record generic infrastructure (login for viewing, CSRF), unless specific to contributing or approving curation.

## Stages (assign one per control)

intake (creating or submitting a session or annotations), fit (preconditions on the state of related objects at approval time), selection (which pending session is reviewed next: ordering, priority, worklists), allocation (who must review or curate it: assignment, ownership, due dates, reminders), decision (approve / reject and who may do it), flag raising, flag resolution, exit (a session leaves the queue without a judgement of its correctness: expiry, withdrawal, deletion, timers), re-review (an approved or exported session returns to review or is reactivated).

Also give **absence records** for selection, allocation and exit: for each snapshot, does ANY control exist (ordering rule, assignment field or logic, due date, reminder that changes state, expiry, scheduled task writing session state)? Note reminder e-mails separately if they do not change state.

## Dating

For each control, give `tau`: the date of the first commit that introduced the code implementing it (use `git log -S'<distinctive snippet>' --reverse --format='%h %ad' --date=short -- <path>`), and `rho`: the date of the commit that removed it, or null. If you cannot date it reliably, give the first snapshot where present and say "bounded".

## Output

Write a JSON file `OUTPUT_PATH`:

```json
{
  "coder": "CODER_ID",
  "controls": [
    {"id": "K1", "object_type": "session|annotation|gene_list|paper|user|cross_cutting",
     "stage": "...", "mode": "G|A|P|C", "rule": "one sentence in plain English",
     "present": {"S1": true, "S2": true, "S3": true, "S4": true},
     "tau": "YYYY-MM-DD or bounded: ...", "rho": null,
     "evidence": {"S4": "path:symbol", "dating": "commit hash and how found"}}
  ],
  "absences": [
    {"stage": "selection|allocation|exit", "object_type": "session",
     "any_control": {"S1": false, "S2": false, "S3": false, "S4": false}, "note": "what you checked"}
  ],
  "notes": "uncertainties"
}
```

Be thorough: read the state machine, every controller action that changes session state, the admin/triage pages, scheduled scripts (`script/`, `etc/`, crontab examples) and any reminder or expiry logic, at every snapshot. When finished, reply with a short summary (controls by stage and mode, absences) and the path of the JSON file.
