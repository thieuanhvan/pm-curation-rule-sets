# Blind coding of review controls in a curation platform's server code (one snapshot)

You are an independent coder. Your task is to find, from source code only, the **controls** that the platform's code applies to the review (moderation) of contributed content, with the file and line where each is implemented.

## Strict blinding rules
- Read ONLY the folder `SERVER_DIR` (a plain copy of a Rails server; no git history). Use file listing, reading and text search inside it.
- Do NOT open any other file or folder on this computer and do not search the web.
- Do not try to guess what another coder found. Code what the code shows.

## Platform
CIViC, a cancer-variant knowledge base. Registered users submit **evidence items**, suggest **revisions** (changes to fields of existing objects), add **comments**, raise **flags**, make **source suggestions**; editors moderate. There are also **assertions** (aggregate claims) that are moderated. The server is Ruby on Rails with a GraphQL API.

## What counts as a control
A control is a rule on a review-related event whose truth the code checks or brings about. Record a control when the server-side code does one of these:
- **guard (G):** refuses an event when a predicate fails (raises an error, returns a validation error, denies authorisation), e.g. "only users with role X may accept", "a comment of at least N characters is required";
- **automatic (A):** changes the status of a moderated object without a human decision on that object (callbacks, side effects of another action, scheduled tasks, background jobs);
- **permission (P):** explicitly enables an action for a specific party that otherwise could not do it, without refusing anything else.

Look at every server layer on the path (mutation/controller, authorisation hooks, base classes and shared modules, policies, model validations and callbacks), and at scheduled-task configuration and background jobs. Do not record generic infrastructure (CSRF, rate limits, generic login for viewing) unless it is specific to contributing or moderating content.

## Stages (assign one per control)
intake (submitting content or suggestions), fit (preconditions on the state of related objects at decision time), selection (which pending item gets reviewed next), allocation (who must review it, assignment, due dates), decision (accept/reject and who may do it), flag raising, flag resolution, exit (an item leaves the queue without a judgement of its correctness: expiry, withdrawal, supersession, timers), re-review (a decided item returns to review).

## Output
Write a JSON file `OUTPUT_PATH`:
```json
{"coder": "CODER_ID",
 "controls": [{"id": "K1", "object_type": "evidence_item|revision|flag|comment|assertion|source_suggestion|cross_cutting",
   "stage": "...", "mode": "G|A|P", "rule": "one sentence in plain English",
   "path": "server/... (starting with server/)", "line": 123}],
 "notes": "anything uncertain"}
```
Use one entry per distinct rule and object type. `line` is the line where the rule's predicate or state change is written. Be thorough: read the mutation/controller for every moderation action (accept, reject, approve, resolve, withdraw, suggest, flag, comment). Aim for completeness over speed. When finished, reply with a short summary (number of controls by stage and mode) and the path of the JSON file.
