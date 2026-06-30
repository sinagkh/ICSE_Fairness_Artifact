# Compact Ladder Row Audit

This audit checks row availability before building the compact ladder reports.

- Base long-metrics source: `results/main/confirmatory_long_metrics.csv.gz`
- Score-guard global-interaction row source: `runs/score_guard_global_interaction_ladder_v1`
- Added score-guard global-interaction metric rows: `51890`.

- Boundary direct-interaction metric source: `results/ladder/boundary_pair_ladder_metrics.csv`
- Added boundary direct-interaction metric rows: `11880`.

| Dataset | Role | Model | Seeds present | Status |
|---|---|---|---:|---|
| Adult Gender | ERM | `erm` | 10 | ok |
| Adult Gender | Global score guard | `score_only` | 10 | ok |
| Adult Gender | Global + boundary score guards | `no_interaction` | 10 | ok |
| Adult Gender | Score guards + global interaction | `score_guard_global_interaction` | 10 | ok |
| Adult Gender | Final interaction steering | `repair_direct` | 10 | ok |
| Adult Gender | Wrong-spec | `wrong_spec` | 10 | ok |
| ACS Employment Age | ERM | `erm` | 10 | ok |
| ACS Employment Age | Global score guard | `score_only` | 10 | ok |
| ACS Employment Age | Global + boundary score guards | `no_interaction` | 10 | ok |
| ACS Employment Age | Score guards + global interaction | `score_guard_global_interaction` | 10 | ok |
| ACS Employment Age | Final interaction steering | `repair_direct` | 10 | ok |
| ACS Employment Age | Wrong-spec | `wrong_spec` | 10 | ok |
| HMDA-OH Race | ERM | `erm` | 10 | ok |
| HMDA-OH Race | Global score guard | `score_only` | 10 | ok |
| HMDA-OH Race | Global + boundary score guards | `no_interaction` | 10 | ok |
| HMDA-OH Race | Score guards + global interaction | `score_guard_global_interaction` | 10 | ok |
| HMDA-OH Race | Final interaction steering | `repair_main05` | 10 | ok |
| HMDA-OH Race | Wrong-spec | `wrong_spec` | 10 | ok |
| HMDA-MD Race | ERM | `erm` | 10 | ok |
| HMDA-MD Race | Global score guard | `score_only` | 10 | ok |
| HMDA-MD Race | Global + boundary score guards | `no_interaction` | 10 | ok |
| HMDA-MD Race | Score guards + global interaction | `score_guard_global_interaction` | 10 | ok |
| HMDA-MD Race | Final interaction steering | `repair_main05` | 10 | ok |
| HMDA-MD Race | Wrong-spec | `wrong_spec` | 10 | ok |
| HMDA-VA Race | ERM | `erm` | 10 | ok |
| HMDA-VA Race | Global score guard | `score_only` | 10 | ok |
| HMDA-VA Race | Global + boundary score guards | `no_interaction` | 10 | ok |
| HMDA-VA Race | Score guards + global interaction | `score_guard_global_interaction` | 10 | ok |
| HMDA-VA Race | Final interaction steering | `repair_main05` | 10 | ok |
| HMDA-VA Race | Wrong-spec | `wrong_spec` | 10 | ok |
| HMDA-PA Race | ERM | `erm` | 10 | ok |
| HMDA-PA Race | Global score guard | `score_only` | 10 | ok |
| HMDA-PA Race | Global + boundary score guards | `no_interaction` | 10 | ok |
| HMDA-PA Race | Score guards + global interaction | `score_guard_global_interaction` | 10 | ok |
| HMDA-PA Race | Final interaction steering | `repair_main05` | 10 | ok |
| HMDA-PA Race | Wrong-spec | `wrong_spec` | 10 | ok |
