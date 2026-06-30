# HMDA Source-Normalized Transfer Insights

Exploratory audit only. This folder is separate from the shipped main-result summaries and does not modify them.

## Protocol

This run evaluates the same trained HMDA source-state checkpoints on held-out applicants from a different target state, but uses the source state's preprocessing instead of target-local preprocessing.

- Sources/targets: MD, OH, PA, VA.
- Seeds: 0--9.
- Cross-state rows: 12 source-target pairs x 10 seeds x 9 model variants = 1080 cross-state evaluations.
- Source-normalized preprocessing: target raw HMDA rows are transformed with the source state's medians/IQR scales, source one-hot schema, and source finite-difference corner values.
- Target-local comparison: the earlier transfer audit preprocesses each target state locally, then aligns target columns to the source checkpoint schema.

This is the stricter zero-shot deployment-style version: the source model carries its own preprocessing recipe into the target state.

## Aggregate Result

Cross-state mean over all source-target-seed evaluations:

| Model | AUC | Acc | AOD | EOD | EOmax | Pair | Main | Proxy effect |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `repair_main05` | 0.8381 | 0.8555 | **0.0181** | **0.0071** | **0.0294** | **0.0039** | **0.0079** | **0.0398** |
| `repair_main0` | 0.8378 | 0.8549 | 0.0195 | 0.0091 | 0.0307 | 0.0063 | 0.0562 | 0.0427 |
| `no_interaction` | 0.8404 | 0.8558 | 0.0247 | 0.0114 | 0.0385 | 0.1434 | 0.2026 | 0.2267 |
| `reweight` | 0.8353 | 0.8072 | 0.0330 | 0.0250 | 0.0441 | 0.2574 | 0.3349 | 0.2698 |
| `score_only` | 0.8414 | 0.8568 | 0.0416 | 0.0237 | 0.0598 | 0.1689 | 0.2536 | 0.2498 |
| `blind` | 0.8437 | 0.8580 | 0.0478 | 0.0292 | 0.0670 | 0.0000* | 0.0000* | 0.2423 |
| `adv` | 0.8459 | 0.8583 | 0.0898 | 0.0589 | 0.1210 | 0.2547 | 0.5236 | 0.2890 |
| `erm` | **0.8463** | **0.8594** | 0.0940 | 0.0610 | 0.1271 | 0.2924 | 0.7194 | 0.3197 |
| `wrong_spec` | 0.8317 | 0.8490 | 0.2228 | 0.1503 | 0.2952 | 0.6543 | 0.9662 | 0.5958 |

*Blind has zero direct protected-attribute mechanism values by construction because the protected attribute is removed. It is excluded from direct-mechanism ScottKnottESD rankings.

The source-normalized result preserves the core transfer story. `repair_main05` is best on AOD, EOD, EOmax, direct pair residual, main-effect residual, and proxy-effect residual. The `no_interaction` control is a useful endpoint competitor, but it leaves the direct pair residual two orders of magnitude larger than interaction steering. ERM and adversarial retain the best AUC/accuracy group, but their fairness gaps and interaction residuals are much larger.

## Difference From Target-Local Transfer

Positive deltas mean source-normalized is larger than target-local. For fairness gaps and residuals, lower is better; for AUC/accuracy, higher is better.

| Model | AUC delta | Acc delta | AOD delta | EOD delta | Pair delta | Proxy-effect delta |
|---|---:|---:|---:|---:|---:|---:|
| `repair_main05` | +0.0033 | +0.0019 | -0.0062 | -0.0082 | +0.0001 | -0.0080 |
| `repair_main0` | +0.0020 | +0.0013 | -0.0113 | -0.0124 | -0.0001 | -0.0074 |
| `reweight` | +0.0043 | +0.0120 | -0.0404 | -0.0548 | -0.0126 | -0.0149 |
| `score_only` | +0.0053 | +0.0045 | -0.0246 | -0.0265 | -0.0015 | -0.0147 |
| `blind` | +0.0083 | +0.0122 | -0.0711 | -0.0885 | +0.0000 | -0.0292 |
| `adv` | +0.0063 | +0.0082 | -0.0465 | -0.0582 | -0.0025 | -0.0210 |
| `erm` | +0.0058 | +0.0089 | -0.0492 | -0.0625 | -0.0077 | -0.0199 |
| `wrong_spec` | +0.0049 | +0.0038 | +0.0017 | -0.0049 | -0.0343 | -0.0225 |

Source-normalized preprocessing does not damage the conclusion. In aggregate, it slightly improves most endpoint disparity gaps relative to target-local preprocessing. The repair variants remain the lowest-gap models, and their direct interaction residuals remain near zero. The `no_interaction` source-normalized rows were added after the target-local transfer run, so this delta table omits `no_interaction` unless the target-local transfer audit is also regenerated with that control.

## Winner Counts

Winner counts over 120 source-target-seed cases:

- AOD: `repair_main05` 36, `no_interaction` 24, `repair_main0` 22, `score_only` 15, `reweight` 15, `blind` 7, `adv` 1.
- EOD: `repair_main05` 49, `repair_main0` 30, `no_interaction` 21, `score_only` 11, `reweight` 5, `blind` 3, `adv` 1.
- EOmax: `repair_main05` 28, `no_interaction` 25, `repair_main0` 22, `reweight` 20, `score_only` 15, `blind` 9, `adv` 1.
- Accuracy: `erm` 38, `blind` 24, `adv` 21, `repair_main0` 12, `score_only` 11, `repair_main05` 8, `no_interaction` 6.
- AUC: `erm` 60, `adv` 38, `blind` 13, `score_only` 4, `wrong_spec` 2, `repair_main05` 2, `no_interaction` 1.
- Proxy-effect mechanism: `repair_main05` 70, `repair_main0` 50.

For direct `pair_abs_mean`, blind wins all cases trivially because the protected attribute is absent. Among non-blind models, the repair variants dominate the direct pair residual: `repair_main05` wins 108/120 cases and `repair_main0` wins the remaining 12/120.

## Source-Target Pair Exceptions

Repair is the best-AOD model in 9/12 source-target pairs under source-normalized preprocessing.

The three exceptions are informative rather than damaging:

- MD -> OH: `reweight` has slightly lower AOD (0.0358) than the best repair (0.0381), but much worse accuracy (0.7703) and direct pair residual (0.2309 versus 0.0045).
- OH -> MD: `blind` has lower AOD (0.0157) than the best repair (0.0252), but blind's direct pair residual is zero by construction and its proxy mechanisms remain much larger.
- OH -> PA: `no_interaction` has slightly lower AOD (0.0173) than the best repair (0.0183), but leaves a much larger direct pair residual (0.1337 versus near zero for repair).

In all other source-target pairs, a repair variant is the best mean-AOD model.

## ScottKnottESD Summary

We ran the standard R `ScottKnottESD` package on the source-normalized cross-state values. Aggregate tests use source != target rows only, so each complete model contributes 120 values per metric. Blind is excluded only from direct protected-attribute mechanism rankings (`mechanism_main_*`, `mechanism_cf_*`, and `mechanism_pair_abs_*`) because those values are zero by construction.

Primary aggregate groups:

- AOD: `repair_main05` and `repair_main0` are group 1; `no_interaction` is group 2.
- EOD: `repair_main05` is group 1; `repair_main0` is group 2; `no_interaction` is group 3.
- EOmax: `repair_main05` and `repair_main0` are group 1; `no_interaction` and `reweight` are group 2.
- Accuracy: ERM, adversarial, and blind are group 1; repair variants, score-only, and `no_interaction` are group 2.
- AUC: ERM and adversarial are group 1; `no_interaction` and score-only are group 3; repair variants are group 4.
- Direct pair residual: `repair_main05` is group 1, `repair_main0` is group 2, and `no_interaction` is group 3 after excluding blind.
- Proxy-effect residual: `repair_main05` is group 1 and `repair_main0` is group 2.
- Conditional proxy score gap: both repair variants are group 1.

The source-normalized ScottKnottESD report is in `CROSS_STATE_SCOTT_KNOTT_ESD_REPORT.md`.

## Interpretation

The source-normalized audit is the stricter transfer test: the source model brings its own preprocessing recipe into the target state. The result still supports the paper's cross-state robustness story. Interaction repair transfers with low endpoint disparity and low learned-rule residuals; wrong-spec transfers badly; endpoint-only and conventional fairness baselines often preserve utility but leave larger interaction residuals and larger fairness gaps.

For the paper, the target-local audit remains the cleaner measure of a shared HMDA rule under state-local feature calibration. The source-normalized audit is useful as a robustness appendix/result: even under stricter preprocessing transfer, the repaired interaction topology is stable.

## Files

- `cross_state_source_normalized_raw.csv`: all source-target-seed-model metrics.
- `cross_state_source_normalized_summary_by_model.csv`: cross-state mean/std by model.
- `cross_state_source_normalized_summary_by_pair_model.csv`: source-target mean/std by model.
- `source_vs_target_local_delta_by_model.csv`: aggregate comparison against target-local transfer.
- `cross_state_scott_knott_esd_groups.csv`: aggregate ScottKnottESD groups.
- `cross_state_pair_scott_knott_esd_groups.csv`: source-target-pair ScottKnottESD groups.
- `CROSS_STATE_SCOTT_KNOTT_ESD_REPORT.md`: generated standard ScottKnottESD report.
