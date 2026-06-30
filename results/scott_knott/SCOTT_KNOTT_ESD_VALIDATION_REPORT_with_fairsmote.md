# ScottKnottESD Validation Report

## Implementation

- R version: `R version 4.1.2 (2021-11-01)`
- Package: `ScottKnottESD` `2.0.3`
- Input: `confirmatory_long_metrics.csv`
- Rule: group 1 is best; lower-is-better metrics are negated before `sk_esd()`.

## Outputs

- `scott_knott_esd_groups.csv`: standard ScottKnottESD groups.
- `scott_knott_esd_errors.csv`: metrics skipped or errored by the package.
- `scott_knott_esd_exclusions.csv`: rows intentionally excluded from grouping.
- `scott_knott_esd_comparison.csv`: comparison with the lightweight in-repo grouping.

## Summary

- Group rows written: `1410`.
- Error/skipped metric cases: `0`.
- Excluded seed-level metric rows: `360`.
- Exclusion rule: `blind` is omitted for non-intersectional direct protected-attribute mechanism metrics matching `main_*`, `cf_*`, or `pair_abs_*`, because the protected attribute is removed and these residuals are zero by construction.
- Lightweight-vs-ScottKnottESD exact group matches: `378/1410`.
- Exact group mismatches: `1032`.
