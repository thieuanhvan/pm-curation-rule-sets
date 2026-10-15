# Tables, figures and numbers: script and result file

Paths: `D/` = `pipeline/D5req/`, `B/` = `pipeline/D5b/`, `K/` = `pipeline/D5k4/`, `KB/` = `pipeline/D5k4b/`, `P/` = `paper17/`.
Printed values are the stored values cut off (not rounded) at the printed precision; some result files store rounded values, so the last printed digit can only be checked by rerunning the script.

## Article

| Item | Script | Result |
|---|---|---|
| Table 1 | literature comparison | none |
| Table 2 | controls C1–C31 with dates: `P/analysis/d_graded_coverage_blind.py` (list `C`); scan `D/R6_formal/t1_code_scan.py`, `t1_controls.py`; COI pass `D/R8/a_coi_scan.py`; documentation dates `D/R8/b_doc_dates.py`; second and blind coding `D/R7/t1b_compare.py`, `P/analysis/blind_recoding/` | `D/R6_formal/t1_signatures.json`, `res_t1_controls.json`, `D/R8/res_a_coi.json`, `res_b_docdates.json`, `D/R7/res_t1b_agreement.json`, `P/analysis/blind_recoding/mapping.json` |
| Table 3 | `D/R8/c_decomp_drift.py` | `D/R8/res_c_decomp_drift.json` (`table3_decomposition`) |
| Table 4 | `P/analysis/enactment_cluster.py` | `P/analysis/res_enactment_cluster.json` |
| Table 5 | `D/R6_formal/t4_gh_fetch.py`, `t4_analyse.py`; `D/R7/t5_gh_fetch.py`, `t5_analyse.py` | `D/R6_formal/res_t4.json`, `D/R7/res_t5_go_hpo.json` |
| Fig. 1 | `P/figures/make_fig1_v3.py` | schematic |
| Fig. 2 | `P/figures/make_fig2_r10.py` (patches `make_figures_isad.py`) | annotations from `D/R6_formal/res_t3.json`, `D/A3/res_a3_pending.json`, Table 4 |
| Fig. 3 | `P/analysis/d_graded_coverage_blind.py` | `P/analysis/res_d_graded_coverage_blind.json` |
| Fig. 4 | `P/figures/make_figures_p17.py` (`fig4`) | `D/A3/res_a4_discipline.json`, `D/A3/res_a2_hazard.json`, `D/R5/res_c_age.json`, `D/R5/res_c2_item_frailty.json` |
| Log size (§4.2) | `D/R5/h_numbers.py` | `D/R5/res_h_numbers.json` |
| Deleted items | `P/analysis/deleted_items_bounds.py` | `P/analysis/res_deleted_items_bounds.json` |
| 821 to 1,581 flagged; 8 residuals | `D/R8/c_decomp_drift.py` | `D/R8/res_c_decomp_drift.json` |
| 68.5 to 99.1 % enactment | `P/analysis/enactment_cluster.py` | `P/analysis/res_enactment_cluster.json` |
| Throughput 0.46; ū 0.15; 55.3 % pending | `D/R5/h_numbers.py`; `D/R6_formal/t3_u_def5.py`; `D/R6_formal/t6_numbers.py` | `res_h_numbers.json`; `res_t3.json`; `res_t6_numbers.json` |
| Age hazard 0.64; frailty 0.74 / 0.73 | `D/R5/c_age.py`; `D/R5/c2_item_frailty.py` | `D/R5/res_c_age.json`; `D/R5/res_c2_item_frailty.json` |
| Intensity 3.41-fold | `D/R5/d_intensity.py`; intervals `D/R7/t6_its_2025.py` | `D/R5/res_d_intensity.json`; `D/R7/res_t6_its.json` |
| H2 (§6.1) | `P/analysis/h2_test.py` | `P/analysis/res_h2_test.json` |
| Commit-level check of the monthly scan | `P/analysis/commit_level_v1.py` (frozen extractor on every first-parent commit of civic-server; needs a bare clone) | `P/analysis/res_commit_level_v1.json` |
| Held-out seeded test | `P/analysis/seeded_v3/plant_and_score.py`, `posthoc_attribution.py` | `res_seeded_v3.json`, `res_seeded_v3_posthoc.json` |
| Canto | blind coders (instructions in `P/analysis/blind_recoding_canto/`) | `coder_A.json`, `coder_B.json`, `summary.json` |

## Supplementary

| Item | Script | Result |
|---|---|---|
| S1 extractors, S2 stage table | `D/R6_formal/t1_code_scan.py`, `D/R7/t1d_extractor_v2.py` | rules in code |
| S3 controls and absence records | assembled from Table 2 sources | as Table 2 |
| S4 documentation dates | `D/R8/b_doc_dates.py` (C4/C6 and the implicit C5/C7 date read from civic-client commit 0cebebb0) | `D/R8/res_b_docdates.json` |
| S5 binary coverage | `P/analysis/make_table_coverage_binary.py` | `P/analysis/table_coverage_binary.md` |
| S6 graded coverage | `P/analysis/d_graded_coverage_blind.py`, `make_table_graded_coverage.py` | `res_d_graded_coverage_blind.json`, `table_graded_coverage.md` |
| S7 held-out seeded test | `P/analysis/seeded_v3/` | `res_seeded_v3*.json` |
| S8 reason shares by quarter | `D/R6_formal/t2_nonconforming.py` | `D/R6_formal/res_t2.json` |
| S9 reason shares before v2 | `D/R6_formal/t6_numbers.py` | `res_t6_numbers.json` |
| S10 reason requirement (DiD, ITS) | `D/R6_formal/t5_did_2025.py`; `D/R7/t7_numbers.py`; `D/R7/t6_its_2025.py` | `res_t5.json`; `res_t7_numbers.json`; `res_t6_its.json` |
| Fig. S1 | `P/figures/` (from `D/R6_formal/res_t5.json`) | `figS1.png` |
| S11 H2 | `P/analysis/h2_test.py` | `res_h2_test.json` |
| S12 liveness and throughput | `D/R5/b_liveness.py`, `h_numbers.py` | `res_b_liveness.json`, `res_h_numbers.json` |
| S13 service position by stratum | `D/R8/d_service_strata.py` | `res_d_service_strata.json` |
| S14 age hazard | `D/R5/c_age.py`, `c2_item_frailty.py`; `D/R3_civic/r3_t4_survival.py`, `r3_t4b_cox_se.py`, `r3_t4c_boot.py` (all three write `res_r3_t4.json`; run in that order) | `res_c_age.json`, `res_c2_item_frailty.json`, `res_r3_t4.json` |
| S15 decision intensity; Fig. S2 | `D/R5/d_intensity.py`; `D/R7/t6_its_2025.py`; figure `P/figures/make_figs_r8.py` | `res_d_intensity.json`; `res_t6_its.json`; `D/W3/res_t1_rho.json` |
| S16 decomposition | `D/R6_formal/t6_decomp_astar.py`; `D/R3_civic/r3_t3_effort.py` | `res_t6_decomp.json`; `res_r3_t3.json` |
| S17 same-day displacement | `D/R5/d_intensity.py`; `D/W7/w7_t1_attention.py` | `res_d_intensity.json`; `res_w7_t1_attention.json` |
| S18 campaign definitions | `D/W7/w7_t5_campaign_window.py`; first row `D/R5/h_numbers.py`; share `D/A6/a6_campaign.py` | `res_w7_t5_campaign_window.json`; `res_h_numbers.json`; `res_a6_campaign.json` |
| S19 same-organisation share | `D/R3_civic/r3_t6_numbers.py` | `res_r3_t6.json` |
| S20 activity and decisions | `D/W3/t2_cox.py`; `D/W7/w7_t2_comment_rejection.py` | `res_t2_cox.json`; `res_w7_t2_comment_rejection.json` |
| Pending states, bot flags, deleted items (S2.7, S2.8) | `D/A3/a3_pending.py`; `D/W3/t5_botflags.py`; `P/analysis/deleted_items_bounds.py` | `res_a3_pending.json`; `res_t5_botflags.json`; `res_deleted_items_bounds.json` |
| Fig. S3 lifecycles | `P/figures/make_figures_p17.py` (`fig2`) | `D/A2/out/discovery.json` |
| Fig. S4 flattening | `P/figures/make_figures_p17.py` (`fig5`) | `D/W3/res_t4_sop.json` |
| Reordering bounds (S4) | `D/R5/sim/e_sim.mjs`; check `D/R3_civic/r3_t2_sim_checks.py`; observed share `D/R7/t7_numbers.py` | `D/R5/res_e_bounds.json`; `res_r3_t2.json`; `res_t7_numbers.json` |
| S21 cases: data, protocol steps and scope of inference | Section 4.1 of the article | none |
| S22 trackers: sample, inference, corroboration | `D/W2/analyze_w2.py`; `D/R3_trackers/r3_t1_t2.mjs`, `r3_t5_corrob.mjs`; frames `K/run_gh.mjs`; label timing `D/R5/g_period.py` | `D/W2/out/results_w2.json`; `D/R3_trackers/*.json`; `K/results_gh.json`; `D/R5/res_g_period.json` |
| S23 comparison systems | assembled from `res_h_numbers.json`, `results_w2.json`, `res_g_period.json`, `res_t3.json`, `r3_t4_u_null.json`, `D/R5_wikidata/results*.json`, `res_t6_numbers.json`, `K/results_gh.json` | as listed |
| S24 tracker regime measures | `D/W2/analyze_w2.py`; `D/R3_trackers/r3_t3_hpo_bursts.py`, `r3_t4_u_null.py`, `r3_t4b_self.py` | `results_w2.json`; `r3_t3_bursts.json`, `r3_t4_u_null.json`, `r3_t4b_self.json` |
| S25 acceptance within 365 days | `D/R5/g_period.py` | `res_g_period.json` |
| S26 discovery and conformance; S27 declarative constraints | `D/W2/analyze_w2.py` | `D/W2/out/results_w2.json` |
| S28 Wikidata census | `D/R5_wikidata/s1`–`s7` (`.mjs`), `s6_u.py` | `D/R5_wikidata/results.json`, `results_u.json` |
| S29 Canto controls | blind coders | `P/analysis/blind_recoding_canto/` |
| S30 design principles; Figs. S5, S6 | design artefacts (`P/figures/make_figures_isad.py`) | none |

Values derived by hand from stored counts (no separate result field): the binomial p of change points, 87 % (65 of 74), Canto 28 of 45 and Cohen's κ, the scan's 18 of 30 controls, GO 75 of 75, tracker stocks 4.3 % and 2.8 %, the 22 smaller-batch deletions, the observed 29.2 % within 365 days in S4.
