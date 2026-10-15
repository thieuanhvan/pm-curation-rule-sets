# Brief: write realistic planted controls for a curation platform (blind generator)

You are writing test material for a code-analysis study. Write realistic Ruby (Rails + graphql-ruby) code that a developer of the CIViC curation platform might add, so that we can test whether an automatic scanner finds it.

## Rules
- You may read ONLY the repository given to you (a git repository of civic-v2; use `git -C <repo> show v2.7.6:<path>`, `git -C <repo> ls-tree -r --name-only v2.7.6`, `git grep ... v2.7.6`). Do not open any other folder on this computer, do not search the web.
- Do not try to guess how the scanner works. Write code the way the code base is written, with the variety a real team would produce.

## What a "control" is
A rule in server-side code that refuses an event on a moderated object (evidence item, assertion, revision, flag, source suggestion, molecular profile) or changes its state without a human decision. Moderated workflow: users submit items and suggest revisions; editors accept or reject them; flags are raised and resolved; items can be deprecated or withdrawn.

Modes: **guard** (refuses when a predicate fails), **automatic** (changes state without a decision: job, callback, side effect), **permission** (enables an action for a specific party).
Stages: intake, fit (precondition on related objects at decision time), selection (which pending item is reviewed next), allocation (who must review it, due dates), decision, flag raising, flag resolution, exit (item leaves the queue without a judgement: expiry, withdrawal, deletion), re-review (decided item returns to the queue).

## What to produce (in the output folder you are given)
1. About **40 controls**, spread roughly as:
   - 26 in these layers: `server/app/graphql/mutations/`, `server/app/policies/`, `server/app/models/activities/`, `server/app/models/actions/`, `server/app/jobs/`, the model files of moderated objects (`server/app/models/evidence_item.rb`, `assertion.rb`, `revision.rb`, `flag.rb`, `source_suggestion.rb`), and `server/config/scheduled_tasks.yml`;
   - 14 in other server layers: controllers and concerns, service objects or `lib/`, base classes, `db/migrate` (constraints, defaults, triggers), validators in other folders.
   Vary the syntax: different ways to raise or return errors, inline and block conditionals, early returns, custom error classes, Pundit-style or role-helper checks, `validates` / `validate :method` / custom validators, callbacks (`before_save`, `after_commit`), status changes by assignment, `update`, `update_columns`, `transition`/enum methods, scheduled jobs, ActiveJob classes. Cover all stages and all three modes; include several for selection, allocation and exit (rarely seen in practice but plausible: ordering scopes used by the moderation queue, assignment fields, due dates, expiry jobs).
2. About **15 decoys** that do NOT enforce anything on a moderated object: commented-out guards, log or notification strings that mention statuses, code under `spec/`, read-only queries such as `where(status: 'submitted')`, guards on non-moderated objects (notifications, user preferences), dead code (`if false`), documentation strings.
3. Each plant and decoy contains a unique lowercase token `zq01` … `zq99` placed naturally (in an error message, method name, field name, class or file name). One token per plant.
4. Write the files as a tree mirroring repository paths under `files/` (for edits to an existing file, write the WHOLE modified file at its path, starting from the v2.7.6 version; several plants may share an existing file). New files are allowed.
5. Write `ground_truth.json`: a list of objects
   `{"id": "zq01", "path": "server/app/...", "category": "in_scope_layer | other_layer | decoy", "is_control": true|false, "stage": "...", "mode": "guard|automatic|permission|none", "syntax": "short description", "snippet": "the planted lines"}`.
6. Keep the Ruby syntactically valid.

When done, reply with counts by category, stage and mode.
