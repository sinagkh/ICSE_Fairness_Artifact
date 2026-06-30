# HMDA Source-Normalized Cross-State Transfer Audit

Exploratory audit only. This folder is separate from the shipped main-result summaries and does not modify them.

Protocol: load each source-state checkpoint and source-state preprocessing specification; transform raw target-state applicants with the source medians/IQR scales, source one-hot schema, and source finite-difference corner values; then evaluate on the target state's held-out split. This is stricter than the target-local transfer audit because preprocessing/scaling is transferred with the model.

## Cross-State Mean Over Source-Target Pairs

| Model | AUC | Acc | AOD | EOD | EOmax | DP | Pair | Main | Proxy score | Proxy effect |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| repair_main05 | 0.8381 +/- 0.0114 | 0.8555 +/- 0.0131 | 0.0181 +/- 0.0130 | 0.0071 +/- 0.0078 | 0.0294 +/- 0.0206 | 0.0634 +/- 0.0247 | 0.0039 +/- 0.0016 | 0.0079 +/- 0.0064 | 0.1107 +/- 0.0615 | 0.0398 +/- 0.0109 |
| repair_main0 | 0.8378 +/- 0.0142 | 0.8549 +/- 0.0172 | 0.0195 +/- 0.0149 | 0.0091 +/- 0.0106 | 0.0307 +/- 0.0223 | 0.0678 +/- 0.0272 | 0.0063 +/- 0.0020 | 0.0562 +/- 0.0360 | 0.1143 +/- 0.0579 | 0.0427 +/- 0.0148 |
| no_interaction | 0.8404 +/- 0.0093 | 0.8558 +/- 0.0118 | 0.0247 +/- 0.0199 | 0.0114 +/- 0.0139 | 0.0385 +/- 0.0289 | 0.0655 +/- 0.0345 | 0.1434 +/- 0.0362 | 0.2026 +/- 0.0596 | 0.1412 +/- 0.0831 | 0.2267 +/- 0.0476 |
| reweight | 0.8353 +/- 0.0109 | 0.8072 +/- 0.0294 | 0.0330 +/- 0.0220 | 0.0250 +/- 0.0220 | 0.0441 +/- 0.0281 | 0.0866 +/- 0.0440 | 0.2574 +/- 0.1272 | 0.3349 +/- 0.1836 | 0.1972 +/- 0.1348 | 0.2698 +/- 0.0750 |
| score_only | 0.8414 +/- 0.0091 | 0.8568 +/- 0.0122 | 0.0416 +/- 0.0331 | 0.0237 +/- 0.0243 | 0.0598 +/- 0.0439 | 0.0956 +/- 0.0448 | 0.1689 +/- 0.0464 | 0.2536 +/- 0.0649 | 0.1611 +/- 0.0938 | 0.2498 +/- 0.0480 |
| blind | 0.8437 +/- 0.0120 | 0.8580 +/- 0.0134 | 0.0478 +/- 0.0267 | 0.0292 +/- 0.0206 | 0.0670 +/- 0.0351 | 0.1067 +/- 0.0382 | 0.0000 +/- 0.0000 | 0.0000 +/- 0.0000 | 0.3705 +/- 0.1297 | 0.2423 +/- 0.0482 |
| adv | 0.8459 +/- 0.0102 | 0.8583 +/- 0.0128 | 0.0898 +/- 0.0394 | 0.0589 +/- 0.0326 | 0.1210 +/- 0.0493 | 0.1454 +/- 0.0474 | 0.2547 +/- 0.0584 | 0.5236 +/- 0.1350 | 0.6013 +/- 0.1952 | 0.2890 +/- 0.0577 |
| erm | 0.8463 +/- 0.0106 | 0.8594 +/- 0.0120 | 0.0940 +/- 0.0378 | 0.0610 +/- 0.0315 | 0.1271 +/- 0.0474 | 0.1488 +/- 0.0458 | 0.2924 +/- 0.0516 | 0.7194 +/- 0.1086 | 0.7883 +/- 0.1727 | 0.3197 +/- 0.0541 |
| wrong_spec | 0.8317 +/- 0.0105 | 0.8490 +/- 0.0118 | 0.2228 +/- 0.0657 | 0.1503 +/- 0.0688 | 0.2952 +/- 0.0743 | 0.2428 +/- 0.0852 | 0.6543 +/- 0.1269 | 0.9662 +/- 0.2451 | 1.0735 +/- 0.2877 | 0.5958 +/- 0.1072 |

## Difference From Target-Local Transfer

See `source_vs_target_local_delta_by_model.csv`. Positive deltas mean source-normalized is larger than target-local; for gaps/residuals this is worse, for AUC/accuracy this is better.

## Files

- `cross_state_source_normalized_raw.csv`: one row per source, target, seed, and model variant.
- `cross_state_source_normalized_summary_by_pair_model.csv`: mean/std over seeds for each source-target-model.
- `cross_state_source_normalized_summary_by_model.csv`: mean/std over all source!=target rows for each model.
- `source_vs_target_local_delta_by_model.csv`: optional comparison to target-local transfer if available.
