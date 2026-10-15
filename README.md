# Curation rule sets: reproducibility package

Code, rule catalogue, coder outputs and aggregate results for the article *Which Stages Does the Code Control? Conformance Against Time-Indexed Rule Sets in Expert-Gated Knowledge Curation* (Van Thieu and Nhan T. Cao).

The package lets a reader (1) rerun the code scan of Algorithm 1 on the public CIViC repositories, (2) rebuild the CIViC object-centric log and the measures from the public APIs, (3) check every table against the stored aggregate results, and (4) rerun the held-out seeded test of the extractors.

## Layout

| Folder | Content |
|---|---|
| `pipeline/D5b/` | CIViC GraphQL harvest of the full event history and item metadata (`pull_events.mjs`, `pull_meta.mjs`, `pull_tail.mjs`), first descriptive analyses |
| `pipeline/D5k4/`, `pipeline/D5k4b/` | GO and HPO new-term trackers (GitHub) and Wikidata property proposals: harvest, ticket classification, regime measures |
| `pipeline/D5sim/` | Item traces and the reordering simulation |
| `pipeline/D5req/R6_formal/` | Algorithm 1 code scan (`t1_code_scan.py`), control list, static references, GO/HPO continuous-integration history |
| `pipeline/D5req/R7/` | Revised extractors (`t1d_extractor_v2.py`), second coding agreement, release-note recall, baselines, graded coverage, interrupted time series |
| `pipeline/D5req/R8/` | Conflict-of-interest pass, documentation dates, decomposition of static references (Table 3), service position by stratum |
| `pipeline/D5req/A2`, `A3`, `A4`, `A6`, `R3_*`, `R5*`, `W2`–`W7` | Object-centric log, conformance and discovery, age hazard, liveness, intensity, campaigns, comparison systems |
| `paper17/analysis/` | Scripts behind Tables 4, S5, S6, S11 and the deleted-item bounds; blind recoding of CIViC and Canto (instructions and coder outputs); held-out seeded test (`seeded_v3/`) |
| `paper17/figures/` | Figure scripts and the final figures |
| `TABLE_MAP.md` | Which script and result file give each table, figure and headline number |

Each pipeline script reads and writes relative to its own folder, as in the original working tree. Aggregate results (`res_*.json`, `results*.json`, `*.pnml`) are included, so tables can be checked without rerunning anything.

## What is not included, and why

Event-level data are not redistributed: raw API caches (CIViC events and users, GitHub timelines and comments, Wikidata pages), pseudonymised event logs and the keys or salts used to pseudonymise them. The CIViC data are public (CC0) and can be harvested again with the scripts in `pipeline/D5b/` and `pipeline/D5req/A6/`; the GitHub and Wikidata data with the scripts in `pipeline/D5k4*`, `pipeline/D5req/W2/` and `pipeline/D5req/R5_wikidata/`. Reported aggregates keep the rule of at least five individuals per cell.

Git clones are not included either; clone them yourself:

```
git clone --bare https://github.com/griffithlab/civic-v2.git
git clone --bare https://github.com/griffithlab/civic-server.git
git clone --bare https://github.com/griffithlab/civic-client.git
git clone --bare https://github.com/griffithlab/civic-docs.git
```

On Windows, civic-v2 contains a client path that cannot be checked out; the scan reads `server/` only and works on a bare clone.

## Environment

- Python 3.11 or later with the packages in `requirements.txt`; Node.js 18 or later (no npm packages); git.
- Environment variables:
  - `P17_PIPELINE`: absolute path of `pipeline/` (scripts under `paper17/` read pipeline results through it; defaults to the copy in this package).
  - `CIVIC_V2_REPO`: bare clone of civic-v2 (conflict-of-interest pass, release tags).
  - `CIVIC_CLONES_DIR`: folder holding `civic-client` and `civic-docs` clones (documentation dates).
  - `P17_SALT`, `P17_SALT_WD`: your own secret salts for pseudonymising GitHub and Wikidata user names during harvest. Choose new values; the original salts are not published.
  - `P17_HMAC_KEY_FILE` or `D5_HMAC_KEY`: your own key for keyed pseudonyms of event logs (optional).
  - `GITHUB_TOKEN` (optional): raises the GitHub API rate limit.
- Scripts that call literature APIs expect a contact address; replace `you@example.org`.

## Rerunning the core

```
python pipeline/D5req/R6_formal/t1_code_scan.py <civic-v2 bare clone> <civic-server bare clone>
python paper17/analysis/seeded_v3/plant_and_score.py <civic-v2 bare clone> paper17/analysis/seeded_v3/plants <work dir>
```

The seeded test checks the SHA-256 of the frozen extractor files before running; its protocol, registered before the plants were written, is `paper17/analysis/seeded_v3/PROTOCOL.md`. The planted files are modified copies of civic-v2 (MIT licence, `plants/LICENSE-civic-v2.txt`).

## Licence

Code: MIT (`LICENSE`). Rule catalogue, coder outputs and aggregate results: CC BY 4.0. Cite the article (see `CITATION.cff`).
