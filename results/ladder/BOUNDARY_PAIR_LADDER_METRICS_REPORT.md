# Boundary Pair Metric Report

Evaluation-only boundary-local direct interaction metrics for the compact ladder artifacts. No models were trained.

Boundary convention: the same hard near-boundary evaluation mask used by `boundary_proxy_effect_gap_mean`, `abs(sigmoid(logit)-0.5) <= boundary_eval_margin` from each checkpoint's saved args.

| Experiment | Model | Bnd-Delta2 mean | Std | n |
|---|---|---:|---:|---:|
| acs_age | `erm` | 0.3096 | 0.0325 | 10 |
| acs_age | `no_interaction` | 0.2219 | 0.0496 | 10 |
| acs_age | `repair_direct` | 0.0409 | 0.0028 | 10 |
| acs_age | `score_guard_global_interaction` | 0.0414 | 0.0025 | 10 |
| acs_age | `score_only` | 0.2458 | 0.0240 | 10 |
| acs_age | `wrong_spec` | 0.4711 | 0.1730 | 10 |
| adult_gender | `erm` | 0.3137 | 0.0571 | 10 |
| adult_gender | `no_interaction` | 0.2331 | 0.0829 | 10 |
| adult_gender | `repair_direct` | 0.0328 | 0.0020 | 10 |
| adult_gender | `score_guard_global_interaction` | 0.0331 | 0.0022 | 10 |
| adult_gender | `score_only` | 0.2894 | 0.0803 | 10 |
| adult_gender | `wrong_spec` | 0.4378 | 0.0460 | 10 |
| hmda_md_race | `erm` | 0.3071 | 0.0434 | 10 |
| hmda_md_race | `no_interaction` | 0.1605 | 0.0420 | 10 |
| hmda_md_race | `repair_main05` | 0.0048 | 0.0018 | 10 |
| hmda_md_race | `score_guard_global_interaction` | 0.0099 | 0.0063 | 10 |
| hmda_md_race | `score_only` | 0.1916 | 0.0499 | 10 |
| hmda_md_race | `wrong_spec` | 0.6382 | 0.0697 | 10 |
| hmda_pa_race | `erm` | 0.4152 | 0.0389 | 10 |
| hmda_pa_race | `no_interaction` | 0.2000 | 0.0407 | 10 |
| hmda_pa_race | `repair_main05` | 0.0036 | 0.0011 | 10 |
| hmda_pa_race | `score_guard_global_interaction` | 0.0073 | 0.0017 | 10 |
| hmda_pa_race | `score_only` | 0.2342 | 0.0556 | 10 |
| hmda_pa_race | `wrong_spec` | 0.8368 | 0.1047 | 10 |
| hmda_race | `erm` | 0.3233 | 0.0399 | 10 |
| hmda_race | `no_interaction` | 0.1544 | 0.0320 | 10 |
| hmda_race | `repair_main05` | 0.0039 | 0.0017 | 10 |
| hmda_race | `score_guard_global_interaction` | 0.0068 | 0.0017 | 10 |
| hmda_race | `score_only` | 0.1866 | 0.0457 | 10 |
| hmda_race | `wrong_spec` | 0.8053 | 0.1491 | 10 |
| hmda_va_race | `erm` | 0.3430 | 0.0393 | 10 |
| hmda_va_race | `no_interaction` | 0.1559 | 0.0388 | 10 |
| hmda_va_race | `repair_main05` | 0.0048 | 0.0023 | 10 |
| hmda_va_race | `score_guard_global_interaction` | 0.0089 | 0.0031 | 10 |
| hmda_va_race | `score_only` | 0.2210 | 0.0568 | 10 |
| hmda_va_race | `wrong_spec` | 0.6412 | 0.0661 | 10 |
