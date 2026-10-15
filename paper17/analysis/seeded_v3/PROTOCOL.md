# Held-out seeded-control test of Algorithm 1 (pre-registered 2026-10-15 14:04, before any plant was written)

## Purpose
Estimate the recall and precision of the frozen Algorithm 1 extractors on controls they were not tuned on, with an objective answer key and no human coder. The earlier seeded test (5 seeds, 3 decoys) was used to revise the extractors and is a debugging result only.

## Frozen code (not changed after this point)
- `t1_code_scan.py` sha256 1515bc5eff59d6748bcfccf3dae0053e5fcbb28ed25f156a50fc4e44637b9677
- `t1d_extractor_v2.py` sha256 57ffd16fafd764839c15286b93d2b9c78683a700be0194a51db2d8201ab058d7
(extractor v2 = the revised extractors reported in Section 5.2; stage table as in the article.)

## Plants
- Written by a language-model agent that receives only `GENERATOR_BRIEF.md` and read access to the civic-v2 repository at tag v2.7.6. It does not see the extractor code, the article, the control list or earlier seeds.
- About 40 controls and 15 decoys, realistic for the code base, spread over categories: (A) in-scope layers read by the scan (GraphQL mutations, policies, activities, actions, jobs, moderated models, scheduled tasks); (B) other server layers the scan does not read (controllers and concerns, services, lib, base classes, database migrations and constraints); (C) decoys that enforce nothing on a moderated object (comments, logging, test files, reads of a status, guards on non-moderated objects, dead code).
- Each plant carries a unique lowercase token `zq<NN>` in a natural place (message, method, field, class or file name) and is described in `ground_truth.json`: id, path, category, layer_in_scope, is_control, expected stage (intake, fit, selection, allocation, decision, flag raising, flag resolution, exit, re-review) and mode (guard, automatic, permission).

## Procedure
1. Commit the plants on top of v2.7.6 in a copy of the repository as tag v9.9.9-seed (the original clone is not modified).
2. Run the frozen extractor on v2.7.6 and v9.9.9-seed; new signatures are those present only in v9.9.9-seed.
3. Score with `score.py` (written before the run).

## Scoring rules (fixed)
- A control plant is **detected** if at least one new signature has the plant's path and either contains the plant token or the plant is the only plant in that file.
- A decoy is a **false positive** if a new signature attributable to it (same rule) is staged as anything other than `other`/infrastructure.
- **Stage correct**: the extractor's stage label maps to the expected stage (decision -> decision; intake -> intake; exit (revision, automatic) / exit (automatic) -> exit; re-entry (automatic) -> re-review; flag raising -> flag raising; flag resolution -> flag resolution); `scheduled job` and `other` count as wrong for any expected stage.
- Report: recall for in-scope controls (primary), recall for all controls, recall by category and mode, false-positive rate on decoys, stage accuracy among detected plants; 95 % Wilson intervals; numbers truncated, not rounded.
- Unattributable new signatures are listed, not scored.

## Deviations (logged as they happened)
- 2026-10-15 14:50: the procedure step "check out v2.7.6" failed on Windows because the client tree contains a path with a trailing space. Fix: sparse checkout of `server/` only and `-c core.protectNTFS=false` on the git commands of the throwaway copy. The scan reads `server/` only; scoring rules unchanged.
- The generator found no `server/app/policies/` folder at v2.7.6 and created Pundit-style policies there; the folder is in the scan's file set, so these plants count as in-scope as pre-registered.
