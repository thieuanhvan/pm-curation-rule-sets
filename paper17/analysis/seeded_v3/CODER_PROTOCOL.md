# Blind coders on the seeded code base (pre-registered 2026-10-15 16:23, before any coder ran)

## Purpose
The held-out seeded test measures the extractors alone. Algorithm 1 ends with a coding step (step 6): coders read the code and curate controls, which is how C20 to C31 entered the catalogue. This test measures that step on the same 41 planted controls and 15 decoys, with the same objective answer key and no human coder.

## Material
- `server/` of the seeded commit (v2.7.6 plus the plants), exported as plain files: no git history, so no diff against v2.7.6.
- Every plant token (`zq01` to `zq56`) is removed from the exported files before the coders see them (`prep_coder_view.py`); the line of each plant is recorded first (`plant_lines.json`). Line numbers do not change.
- Coders: two language-model agents (A and B), blind to each other, to the plants, the answer key, the extractors and the article. Instructions: `CODER_BRIEF.md` (the stage set and modes of the article, one snapshot).

## Scoring (fixed)
- A coder item is a control the coder reports, with `path` and `line`.
- A control plant is **found** if some coder item has the plant's path and a line within ±5 of a recorded plant line.
- A decoy is a **false positive** if some coder item matches it by the same rule.
- Report, per coder and for the union of A and B (the protocol's coding step): recall on the 27 controls in the scanned layers, on the 14 in other layers and on all 41; false positives on the 15 decoys; recall on the 12 in-scope controls the frozen extractors missed under the pre-registered rule, and on the 4 they missed even with post hoc attribution. 95 % Wilson intervals; numbers truncated.
- Coder items that match no plant are listed (most are genuine controls of the code base) and not scored.

## Note added before the coders ran (16:35)
`CODER_BRIEF.md` keeps the scope and wording of the instructions the article's blind coders received (`../blind_recoding/CODING_INSTRUCTIONS.md`): the same definitions of control, mode and stage and the same list of server layers to read, reduced to one snapshot and with a file and line per control. A first draft of the brief listed further layers (services, `lib/`, migrations) and was replaced so as not to cue the coders beyond what the article's coding step used.
