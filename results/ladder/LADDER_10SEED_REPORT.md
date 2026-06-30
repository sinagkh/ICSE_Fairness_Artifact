# Compact Ladder 10-Seed Report

The compact ladder isolates the contribution of the interaction rule: ERM, endpoint/guard controls, global interaction steering, the final interaction steering row used in the paper tables, and wrong-specification control.

Metrics are mean +/- std over 10 seeds. Lower is better except AUC/Acc.

## Adult Gender

| Role | Model | AUC | Acc | AOD | EOD | DP | Sgap | Delta2 | Proxy | Bnd-Delta2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ERM | `erm` | 0.9102 +/- 0.0020 | 0.8514 +/- 0.0027 | 0.0840 +/- 0.0150 | 0.0903 +/- 0.0264 | 0.1845 +/- 0.0099 | 0.2005 +/- 0.0071 | 0.2752 +/- 0.0481 | 0.2284 +/- 0.0283 | 0.3137 +/- 0.0571 |
| Global score guard | `score_only` | 0.9047 +/- 0.0033 | 0.8492 +/- 0.0035 | 0.0444 +/- 0.0124 | 0.0359 +/- 0.0249 | 0.1476 +/- 0.0200 | 0.1340 +/- 0.0158 | 0.2957 +/- 0.1056 | 0.2624 +/- 0.0816 | 0.2894 +/- 0.0803 |
| Global + boundary score guards | `no_interaction` | 0.9020 +/- 0.0029 | 0.8479 +/- 0.0039 | 0.0382 +/- 0.0189 | 0.0361 +/- 0.0416 | 0.1298 +/- 0.0178 | 0.1139 +/- 0.0149 | 0.1983 +/- 0.0715 | 0.1769 +/- 0.0451 | 0.2331 +/- 0.0829 |
| Score guards + global interaction | `score_guard_global_interaction` | 0.9014 +/- 0.0034 | 0.8466 +/- 0.0033 | 0.0357 +/- 0.0128 | 0.0356 +/- 0.0272 | 0.1251 +/- 0.0156 | 0.1083 +/- 0.0135 | 0.0319 +/- 0.0020 | 0.0207 +/- 0.0036 | 0.0331 +/- 0.0022 |
| Final interaction steering | `repair_direct` | 0.9013 +/- 0.0034 | 0.8466 +/- 0.0028 | 0.0353 +/- 0.0136 | 0.0349 +/- 0.0289 | 0.1248 +/- 0.0151 | 0.1082 +/- 0.0135 | 0.0317 +/- 0.0020 | 0.0186 +/- 0.0038 | 0.0328 +/- 0.0020 |
| Wrong-spec | `wrong_spec` | 0.9059 +/- 0.0021 | 0.8472 +/- 0.0019 | 0.1467 +/- 0.0248 | 0.1964 +/- 0.0413 | 0.2136 +/- 0.0198 | 0.2250 +/- 0.0151 | 0.4238 +/- 0.0381 | 0.5170 +/- 0.0264 | 0.4378 +/- 0.0460 |

- Final vs no-interaction: AOD 0.0353 vs 0.0382, Delta2 0.0317 vs 0.1983.
- Wrong-spec attribution: AOD 0.1467, Delta2 0.4238.

## ACS Employment Age

| Role | Model | AUC | Acc | AOD | EOD | DP | Sgap | Delta2 | Proxy | Bnd-Delta2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ERM | `erm` | 0.7561 +/- 0.0031 | 0.7153 +/- 0.0042 | 0.0717 +/- 0.0236 | 0.0488 +/- 0.0196 | 0.1078 +/- 0.0215 | 0.1292 +/- 0.0068 | 0.2996 +/- 0.0314 | 0.2587 +/- 0.0202 | 0.3096 +/- 0.0325 |
| Global score guard | `score_only` | 0.7473 +/- 0.0044 | 0.7129 +/- 0.0045 | 0.0486 +/- 0.0276 | 0.0414 +/- 0.0195 | 0.0205 +/- 0.0108 | 0.0213 +/- 0.0110 | 0.2247 +/- 0.0201 | 0.2061 +/- 0.0172 | 0.2458 +/- 0.0240 |
| Global + boundary score guards | `no_interaction` | 0.7467 +/- 0.0058 | 0.7127 +/- 0.0055 | 0.0407 +/- 0.0171 | 0.0332 +/- 0.0156 | 0.0192 +/- 0.0184 | 0.0231 +/- 0.0119 | 0.2039 +/- 0.0436 | 0.1913 +/- 0.0314 | 0.2219 +/- 0.0496 |
| Score guards + global interaction | `score_guard_global_interaction` | 0.7423 +/- 0.0053 | 0.7127 +/- 0.0054 | 0.0201 +/- 0.0109 | 0.0185 +/- 0.0101 | 0.0333 +/- 0.0199 | 0.0215 +/- 0.0097 | 0.0388 +/- 0.0024 | 0.0312 +/- 0.0020 | 0.0414 +/- 0.0025 |
| Final interaction steering | `repair_direct` | 0.7420 +/- 0.0049 | 0.7122 +/- 0.0047 | 0.0201 +/- 0.0110 | 0.0190 +/- 0.0099 | 0.0334 +/- 0.0190 | 0.0206 +/- 0.0089 | 0.0383 +/- 0.0026 | 0.0293 +/- 0.0019 | 0.0409 +/- 0.0028 |
| Wrong-spec | `wrong_spec` | 0.7480 +/- 0.0056 | 0.7097 +/- 0.0046 | 0.1492 +/- 0.0302 | 0.0898 +/- 0.0204 | 0.1702 +/- 0.0254 | 0.1513 +/- 0.0124 | 0.4639 +/- 0.1806 | 0.5104 +/- 0.1278 | 0.4711 +/- 0.1730 |

- Final vs no-interaction: AOD 0.0201 vs 0.0407, Delta2 0.0383 vs 0.2039.
- Wrong-spec attribution: AOD 0.1492, Delta2 0.4639.

## HMDA-OH Race

| Role | Model | AUC | Acc | AOD | EOD | DP | Sgap | Delta2 | Proxy | Bnd-Delta2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ERM | `erm` | 0.8594 +/- 0.0014 | 0.8761 +/- 0.0008 | 0.0891 +/- 0.0150 | 0.0449 +/- 0.0096 | 0.1401 +/- 0.0125 | 0.1505 +/- 0.0103 | 0.2837 +/- 0.0417 | 0.3204 +/- 0.0326 | 0.3233 +/- 0.0399 |
| Global score guard | `score_only` | 0.8534 +/- 0.0040 | 0.8731 +/- 0.0027 | 0.0293 +/- 0.0130 | 0.0107 +/- 0.0062 | 0.0857 +/- 0.0131 | 0.0657 +/- 0.0117 | 0.1539 +/- 0.0300 | 0.2458 +/- 0.0326 | 0.1866 +/- 0.0457 |
| Global + boundary score guards | `no_interaction` | 0.8521 +/- 0.0030 | 0.8709 +/- 0.0022 | 0.0062 +/- 0.0044 | 0.0031 +/- 0.0031 | 0.0555 +/- 0.0056 | 0.0556 +/- 0.0073 | 0.1342 +/- 0.0209 | 0.2273 +/- 0.0194 | 0.1544 +/- 0.0320 |
| Score guards + global interaction | `score_guard_global_interaction` | 0.8541 +/- 0.0022 | 0.8714 +/- 0.0019 | 0.0066 +/- 0.0036 | 0.0019 +/- 0.0014 | 0.0580 +/- 0.0038 | 0.0594 +/- 0.0066 | 0.0052 +/- 0.0011 | 0.0308 +/- 0.0066 | 0.0068 +/- 0.0017 |
| Final interaction steering | `repair_main05` | 0.8519 +/- 0.0029 | 0.8697 +/- 0.0020 | 0.0048 +/- 0.0030 | 0.0016 +/- 0.0011 | 0.0563 +/- 0.0033 | 0.0551 +/- 0.0048 | 0.0036 +/- 0.0014 | 0.0214 +/- 0.0053 | 0.0039 +/- 0.0017 |
| Wrong-spec | `wrong_spec` | 0.8420 +/- 0.0034 | 0.8638 +/- 0.0017 | 0.2150 +/- 0.0456 | 0.1173 +/- 0.0719 | 0.2017 +/- 0.0999 | 0.1570 +/- 0.0982 | 0.7649 +/- 0.1594 | 0.6711 +/- 0.1259 | 0.8053 +/- 0.1491 |

- Final vs no-interaction: AOD 0.0048 vs 0.0062, Delta2 0.0036 vs 0.1342.
- Wrong-spec attribution: AOD 0.2150, Delta2 0.7649.

## HMDA-MD Race

| Role | Model | AUC | Acc | AOD | EOD | DP | Sgap | Delta2 | Proxy | Bnd-Delta2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ERM | `erm` | 0.8635 +/- 0.0023 | 0.8673 +/- 0.0014 | 0.0611 +/- 0.0117 | 0.0366 +/- 0.0063 | 0.1127 +/- 0.0096 | 0.1334 +/- 0.0062 | 0.2524 +/- 0.0339 | 0.3262 +/- 0.0203 | 0.3071 +/- 0.0434 |
| Global score guard | `score_only` | 0.8509 +/- 0.0047 | 0.8628 +/- 0.0034 | 0.0210 +/- 0.0107 | 0.0148 +/- 0.0050 | 0.0777 +/- 0.0088 | 0.0612 +/- 0.0070 | 0.1518 +/- 0.0326 | 0.2393 +/- 0.0290 | 0.1916 +/- 0.0499 |
| Global + boundary score guards | `no_interaction` | 0.8512 +/- 0.0052 | 0.8619 +/- 0.0039 | 0.0077 +/- 0.0060 | 0.0035 +/- 0.0033 | 0.0591 +/- 0.0059 | 0.0519 +/- 0.0042 | 0.1334 +/- 0.0313 | 0.2231 +/- 0.0249 | 0.1605 +/- 0.0420 |
| Score guards + global interaction | `score_guard_global_interaction` | 0.8503 +/- 0.0038 | 0.8624 +/- 0.0037 | 0.0099 +/- 0.0047 | 0.0055 +/- 0.0031 | 0.0623 +/- 0.0065 | 0.0537 +/- 0.0077 | 0.0081 +/- 0.0054 | 0.0201 +/- 0.0035 | 0.0099 +/- 0.0063 |
| Final interaction steering | `repair_main05` | 0.8499 +/- 0.0022 | 0.8616 +/- 0.0025 | 0.0081 +/- 0.0044 | 0.0039 +/- 0.0026 | 0.0586 +/- 0.0068 | 0.0488 +/- 0.0063 | 0.0040 +/- 0.0015 | 0.0171 +/- 0.0027 | 0.0048 +/- 0.0018 |
| Wrong-spec | `wrong_spec` | 0.8426 +/- 0.0057 | 0.8494 +/- 0.0026 | 0.1775 +/- 0.0323 | 0.1049 +/- 0.0263 | 0.1956 +/- 0.0310 | 0.1830 +/- 0.0175 | 0.6183 +/- 0.0672 | 0.5858 +/- 0.0621 | 0.6382 +/- 0.0697 |

- Final vs no-interaction: AOD 0.0081 vs 0.0077, Delta2 0.0040 vs 0.1334.
- Wrong-spec attribution: AOD 0.1775, Delta2 0.6183.

## HMDA-VA Race

| Role | Model | AUC | Acc | AOD | EOD | DP | Sgap | Delta2 | Proxy | Bnd-Delta2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ERM | `erm` | 0.8688 +/- 0.0019 | 0.8828 +/- 0.0007 | 0.0653 +/- 0.0076 | 0.0313 +/- 0.0056 | 0.1082 +/- 0.0065 | 0.1280 +/- 0.0061 | 0.2814 +/- 0.0400 | 0.3483 +/- 0.0269 | 0.3430 +/- 0.0393 |
| Global score guard | `score_only` | 0.8610 +/- 0.0034 | 0.8801 +/- 0.0029 | 0.0245 +/- 0.0147 | 0.0107 +/- 0.0057 | 0.0740 +/- 0.0131 | 0.0623 +/- 0.0113 | 0.1745 +/- 0.0417 | 0.2554 +/- 0.0417 | 0.2210 +/- 0.0568 |
| Global + boundary score guards | `no_interaction` | 0.8599 +/- 0.0030 | 0.8771 +/- 0.0026 | 0.0130 +/- 0.0073 | 0.0028 +/- 0.0019 | 0.0496 +/- 0.0102 | 0.0503 +/- 0.0086 | 0.1419 +/- 0.0310 | 0.2272 +/- 0.0479 | 0.1559 +/- 0.0388 |
| Score guards + global interaction | `score_guard_global_interaction` | 0.8609 +/- 0.0023 | 0.8779 +/- 0.0019 | 0.0116 +/- 0.0075 | 0.0029 +/- 0.0021 | 0.0561 +/- 0.0081 | 0.0530 +/- 0.0102 | 0.0069 +/- 0.0020 | 0.0242 +/- 0.0070 | 0.0089 +/- 0.0031 |
| Final interaction steering | `repair_main05` | 0.8583 +/- 0.0029 | 0.8765 +/- 0.0025 | 0.0078 +/- 0.0061 | 0.0025 +/- 0.0019 | 0.0538 +/- 0.0064 | 0.0482 +/- 0.0079 | 0.0039 +/- 0.0017 | 0.0183 +/- 0.0055 | 0.0048 +/- 0.0023 |
| Wrong-spec | `wrong_spec` | 0.8469 +/- 0.0039 | 0.8675 +/- 0.0016 | 0.1599 +/- 0.0284 | 0.0931 +/- 0.0177 | 0.1766 +/- 0.0241 | 0.1683 +/- 0.0154 | 0.5967 +/- 0.0716 | 0.5946 +/- 0.0563 | 0.6412 +/- 0.0661 |

- Final vs no-interaction: AOD 0.0078 vs 0.0130, Delta2 0.0039 vs 0.1419.
- Wrong-spec attribution: AOD 0.1599, Delta2 0.5967.

## HMDA-PA Race

| Role | Model | AUC | Acc | AOD | EOD | DP | Sgap | Delta2 | Proxy | Bnd-Delta2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ERM | `erm` | 0.8525 +/- 0.0022 | 0.8609 +/- 0.0012 | 0.1215 +/- 0.0206 | 0.0732 +/- 0.0154 | 0.1948 +/- 0.0191 | 0.1919 +/- 0.0147 | 0.3705 +/- 0.0357 | 0.3181 +/- 0.0487 | 0.4152 +/- 0.0389 |
| Global score guard | `score_only` | 0.8470 +/- 0.0039 | 0.8581 +/- 0.0023 | 0.0447 +/- 0.0196 | 0.0207 +/- 0.0115 | 0.1210 +/- 0.0205 | 0.0904 +/- 0.0143 | 0.1986 +/- 0.0428 | 0.2978 +/- 0.0216 | 0.2342 +/- 0.0556 |
| Global + boundary score guards | `no_interaction` | 0.8452 +/- 0.0039 | 0.8556 +/- 0.0025 | 0.0087 +/- 0.0048 | 0.0032 +/- 0.0024 | 0.0767 +/- 0.0090 | 0.0764 +/- 0.0093 | 0.1737 +/- 0.0353 | 0.2770 +/- 0.0339 | 0.2000 +/- 0.0407 |
| Score guards + global interaction | `score_guard_global_interaction` | 0.8474 +/- 0.0029 | 0.8574 +/- 0.0011 | 0.0121 +/- 0.0081 | 0.0035 +/- 0.0026 | 0.0873 +/- 0.0102 | 0.0841 +/- 0.0086 | 0.0060 +/- 0.0015 | 0.0361 +/- 0.0067 | 0.0073 +/- 0.0017 |
| Final interaction steering | `repair_main05` | 0.8447 +/- 0.0036 | 0.8546 +/- 0.0020 | 0.0070 +/- 0.0062 | 0.0021 +/- 0.0019 | 0.0810 +/- 0.0043 | 0.0739 +/- 0.0062 | 0.0033 +/- 0.0008 | 0.0245 +/- 0.0053 | 0.0036 +/- 0.0011 |
| Wrong-spec | `wrong_spec` | 0.8416 +/- 0.0035 | 0.8512 +/- 0.0019 | 0.2844 +/- 0.0312 | 0.2204 +/- 0.0446 | 0.3427 +/- 0.0369 | 0.2665 +/- 0.0244 | 0.8102 +/- 0.1021 | 0.6629 +/- 0.1072 | 0.8368 +/- 0.1047 |

- Final vs no-interaction: AOD 0.0070 vs 0.0087, Delta2 0.0033 vs 0.1737.
- Wrong-spec attribution: AOD 0.2844, Delta2 0.8102.

## Files

- `adult_ladder_10seed.csv`: per-seed compact ladder rows for Adult Gender.
- `adult_ladder_10seed_summary.csv`: mean/std summary.
- `acs_age_ladder_10seed.csv`: per-seed compact ladder rows for ACS Employment Age.
- `acs_age_ladder_10seed_summary.csv`: mean/std summary.
- `hmda_oh_compact_ladder_10seed.csv`: per-seed compact ladder rows for HMDA-OH Race.
- `hmda_oh_compact_ladder_10seed_summary.csv`: mean/std summary.
- `hmda_md_compact_ladder_10seed.csv`: per-seed compact ladder rows for HMDA-MD Race.
- `hmda_md_compact_ladder_10seed_summary.csv`: mean/std summary.
- `hmda_va_compact_ladder_10seed.csv`: per-seed compact ladder rows for HMDA-VA Race.
- `hmda_va_compact_ladder_10seed_summary.csv`: mean/std summary.
- `hmda_pa_compact_ladder_10seed.csv`: per-seed compact ladder rows for HMDA-PA Race.
- `hmda_pa_compact_ladder_10seed_summary.csv`: mean/std summary.
- `compact_ladder_long_metrics.csv`: long metrics table for ScottKnottESD.
- `boundary_pair_ladder_metrics.csv`: evaluation-only boundary-local direct interaction metrics.
- `scott_knott_esd_groups.csv`: standard ScottKnottESD groups where generated.
