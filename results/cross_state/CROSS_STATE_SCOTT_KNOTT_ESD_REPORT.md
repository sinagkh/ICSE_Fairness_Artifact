# Cross-State ScottKnottESD Report

## Implementation

- R version: `R version 4.1.2 (2021-11-01)`
- Package: `ScottKnottESD` `2.0.3`
- Input: `results/cross_state/cross_state_source_normalized_raw.csv`
- Filter: `transfer_kind == cross`.
- Aggregate grouping: one ScottKnottESD test per metric over all cross-state source-target-seed values.
- Pair grouping: one ScottKnottESD test per source-target pair and metric.
- Direction: group 1 is best for `higher`/`lower` objective metrics. For `descriptive_higher` metrics, group 1 means the highest value, not necessarily best.

## Outputs

- `cross_state_scott_knott_esd_groups.csv`: aggregate cross-state groups.
- `cross_state_pair_scott_knott_esd_groups.csv`: per source-target groups.
- `cross_state_scott_knott_esd_errors.csv`: aggregate skipped/error metrics.
- `cross_state_pair_scott_knott_esd_errors.csv`: pair-level skipped/error metrics.
- `cross_state_scott_knott_esd_exclusions.csv`: rows intentionally excluded from direct mechanism metrics.

## Summary

- Numeric metrics considered: `365`.
- Aggregate group rows: `3234`.
- Aggregate skipped/error metrics: `3`.
- Pair-level group rows: `38808`.
- Pair-level skipped/error metric cases: `1496`.
- Excluded blind direct-mechanism seed-level cells: `2880`.
- Exclusion rule: `blind` is omitted for `mechanism_main_*`, `mechanism_cf_*`, and `mechanism_pair_abs_*`, because the protected attribute is removed and those residuals are zero by construction.

## Primary Aggregate Groups

| Metric | Direction | Group | Model | Mean | Std | n |
|---|---|---:|---|---:|---:|---:|
| `behavior_accuracy` | higher | 1 | `blind` | 0.857993 | 0.013400 | 120 |
| `behavior_accuracy` | higher | 1 | `adv` | 0.858302 | 0.012786 | 120 |
| `behavior_accuracy` | higher | 1 | `erm` | 0.859388 | 0.012050 | 120 |
| `behavior_accuracy` | higher | 2 | `repair_main0` | 0.854941 | 0.017211 | 120 |
| `behavior_accuracy` | higher | 2 | `repair_main05` | 0.855470 | 0.013111 | 120 |
| `behavior_accuracy` | higher | 2 | `no_interaction` | 0.855811 | 0.011819 | 120 |
| `behavior_accuracy` | higher | 2 | `score_only` | 0.856799 | 0.012234 | 120 |
| `behavior_accuracy` | higher | 3 | `wrong_spec` | 0.849036 | 0.011844 | 120 |
| `behavior_accuracy` | higher | 4 | `reweight` | 0.807240 | 0.029376 | 120 |
| `behavior_aod_gap` | lower | 1 | `repair_main05` | 0.018071 | 0.013005 | 120 |
| `behavior_aod_gap` | lower | 1 | `repair_main0` | 0.019544 | 0.014932 | 120 |
| `behavior_aod_gap` | lower | 2 | `no_interaction` | 0.024728 | 0.019886 | 120 |
| `behavior_aod_gap` | lower | 3 | `reweight` | 0.033030 | 0.022014 | 120 |
| `behavior_aod_gap` | lower | 4 | `score_only` | 0.041576 | 0.033102 | 120 |
| `behavior_aod_gap` | lower | 5 | `blind` | 0.047817 | 0.026712 | 120 |
| `behavior_aod_gap` | lower | 6 | `adv` | 0.089818 | 0.039356 | 120 |
| `behavior_aod_gap` | lower | 6 | `erm` | 0.094029 | 0.037833 | 120 |
| `behavior_aod_gap` | lower | 7 | `wrong_spec` | 0.222754 | 0.065725 | 120 |
| `behavior_auc` | higher | 1 | `adv` | 0.845870 | 0.010228 | 120 |
| `behavior_auc` | higher | 1 | `erm` | 0.846322 | 0.010609 | 120 |
| `behavior_auc` | higher | 2 | `blind` | 0.843689 | 0.012037 | 120 |
| `behavior_auc` | higher | 3 | `no_interaction` | 0.840362 | 0.009309 | 120 |
| `behavior_auc` | higher | 3 | `score_only` | 0.841376 | 0.009051 | 120 |
| `behavior_auc` | higher | 4 | `repair_main0` | 0.837778 | 0.014151 | 120 |
| `behavior_auc` | higher | 4 | `repair_main05` | 0.838060 | 0.011403 | 120 |
| `behavior_auc` | higher | 5 | `reweight` | 0.835305 | 0.010873 | 120 |
| `behavior_auc` | higher | 6 | `wrong_spec` | 0.831656 | 0.010547 | 120 |
| `behavior_dp_gap` | lower | 1 | `repair_main05` | 0.063386 | 0.024733 | 120 |
| `behavior_dp_gap` | lower | 1 | `no_interaction` | 0.065517 | 0.034517 | 120 |
| `behavior_dp_gap` | lower | 1 | `repair_main0` | 0.067831 | 0.027244 | 120 |
| `behavior_dp_gap` | lower | 2 | `reweight` | 0.086614 | 0.043970 | 120 |
| `behavior_dp_gap` | lower | 3 | `score_only` | 0.095588 | 0.044798 | 120 |
| `behavior_dp_gap` | lower | 4 | `blind` | 0.106726 | 0.038181 | 120 |
| `behavior_dp_gap` | lower | 5 | `adv` | 0.145371 | 0.047437 | 120 |
| `behavior_dp_gap` | lower | 5 | `erm` | 0.148794 | 0.045836 | 120 |
| `behavior_dp_gap` | lower | 6 | `wrong_spec` | 0.242783 | 0.085200 | 120 |
| `behavior_eod_gap` | lower | 1 | `repair_main05` | 0.007085 | 0.007816 | 120 |
| `behavior_eod_gap` | lower | 2 | `repair_main0` | 0.009088 | 0.010642 | 120 |
| `behavior_eod_gap` | lower | 3 | `no_interaction` | 0.011383 | 0.013855 | 120 |
| `behavior_eod_gap` | lower | 4 | `score_only` | 0.023683 | 0.024301 | 120 |
| `behavior_eod_gap` | lower | 4 | `reweight` | 0.024969 | 0.021971 | 120 |
| `behavior_eod_gap` | lower | 5 | `blind` | 0.029235 | 0.020577 | 120 |
| `behavior_eod_gap` | lower | 6 | `adv` | 0.058871 | 0.032570 | 120 |
| `behavior_eod_gap` | lower | 6 | `erm` | 0.060967 | 0.031500 | 120 |
| `behavior_eod_gap` | lower | 7 | `wrong_spec` | 0.150302 | 0.068818 | 120 |
| `behavior_eodds_max_gap` | lower | 1 | `repair_main05` | 0.029369 | 0.020551 | 120 |
| `behavior_eodds_max_gap` | lower | 1 | `repair_main0` | 0.030665 | 0.022307 | 120 |
| `behavior_eodds_max_gap` | lower | 2 | `no_interaction` | 0.038488 | 0.028889 | 120 |
| `behavior_eodds_max_gap` | lower | 2 | `reweight` | 0.044107 | 0.028070 | 120 |
| `behavior_eodds_max_gap` | lower | 3 | `score_only` | 0.059804 | 0.043865 | 120 |
| `behavior_eodds_max_gap` | lower | 3 | `blind` | 0.066972 | 0.035118 | 120 |
| `behavior_eodds_max_gap` | lower | 4 | `adv` | 0.120952 | 0.049281 | 120 |
| `behavior_eodds_max_gap` | lower | 4 | `erm` | 0.127095 | 0.047426 | 120 |
| `behavior_eodds_max_gap` | lower | 5 | `wrong_spec` | 0.295207 | 0.074253 | 120 |
| `mechanism_main_abs_logit_mean` | lower | 1 | `repair_main05` | 0.007913 | 0.006418 | 120 |
| `mechanism_main_abs_logit_mean` | lower | 2 | `repair_main0` | 0.056173 | 0.035992 | 120 |
| `mechanism_main_abs_logit_mean` | lower | 3 | `no_interaction` | 0.202581 | 0.059564 | 120 |
| `mechanism_main_abs_logit_mean` | lower | 4 | `score_only` | 0.253552 | 0.064870 | 120 |
| `mechanism_main_abs_logit_mean` | lower | 5 | `reweight` | 0.334939 | 0.183633 | 120 |
| `mechanism_main_abs_logit_mean` | lower | 6 | `adv` | 0.523618 | 0.134976 | 120 |
| `mechanism_main_abs_logit_mean` | lower | 7 | `erm` | 0.719373 | 0.108551 | 120 |
| `mechanism_main_abs_logit_mean` | lower | 8 | `wrong_spec` | 0.966247 | 0.245063 | 120 |
| `mechanism_pair_abs_mean` | lower | 1 | `repair_main05` | 0.003854 | 0.001578 | 120 |
| `mechanism_pair_abs_mean` | lower | 2 | `repair_main0` | 0.006288 | 0.001968 | 120 |
| `mechanism_pair_abs_mean` | lower | 3 | `no_interaction` | 0.143429 | 0.036181 | 120 |
| `mechanism_pair_abs_mean` | lower | 4 | `score_only` | 0.168866 | 0.046401 | 120 |
| `mechanism_pair_abs_mean` | lower | 5 | `adv` | 0.254668 | 0.058391 | 120 |
| `mechanism_pair_abs_mean` | lower | 5 | `reweight` | 0.257372 | 0.127212 | 120 |
| `mechanism_pair_abs_mean` | lower | 6 | `erm` | 0.292359 | 0.051590 | 120 |
| `mechanism_pair_abs_mean` | lower | 7 | `wrong_spec` | 0.654295 | 0.126934 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 1 | `repair_main05` | 0.039783 | 0.010879 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 2 | `repair_main0` | 0.042714 | 0.014826 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 3 | `no_interaction` | 0.226739 | 0.047583 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 4 | `blind` | 0.242256 | 0.048172 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 4 | `score_only` | 0.249816 | 0.048036 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 5 | `reweight` | 0.269845 | 0.074962 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 6 | `adv` | 0.288966 | 0.057735 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 7 | `erm` | 0.319693 | 0.054056 | 120 |
| `mechanism_proxy_effect_gap_mean` | lower | 8 | `wrong_spec` | 0.595820 | 0.107193 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 1 | `repair_main05` | 0.110720 | 0.061484 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 1 | `repair_main0` | 0.114322 | 0.057941 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 2 | `no_interaction` | 0.141197 | 0.083098 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 3 | `score_only` | 0.161135 | 0.093797 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 4 | `reweight` | 0.197152 | 0.134754 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 5 | `blind` | 0.370506 | 0.129665 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 6 | `adv` | 0.601303 | 0.195168 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 7 | `erm` | 0.788326 | 0.172650 | 120 |
| `mechanism_proxy_score_gap_cond_mean` | lower | 8 | `wrong_spec` | 1.073461 | 0.287706 | 120 |
