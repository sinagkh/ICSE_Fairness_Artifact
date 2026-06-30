# Fair-SMOTE Implementation Audit

This note records the Fair-SMOTE baseline implementation used for the additional
ICSE fairness-debugging runs.

## Source Checked

I inspected the public Fair-SMOTE repository
`https://github.com/joymallyac/Fair-SMOTE`, especially:

- `README.md`
- `Generate_Samples.py`
- `SMOTE.py`
- `Fair-SMOTE/Adult_Sex.py`
- `Fair_Situation_Testing/Adult_Situation_Sex.ipynb`

The experiment scripts compute the four training cells induced by class label and
protected attribute, oversample the smaller cells to the largest cell count, and
generate synthetic samples from within the same cell using nearest-neighbor
candidates and the Fair-SMOTE differential mutator with `cr=0.8` and `f=0.8`.
The situation-testing notebook then trains a logistic regression on the
resampled training data, toggles the protected attribute in each row, and removes
rows whose predicted label changes.

## Implemented Baseline

The `fairsmote` row in
`scripts/run_fairness_interactions.py` is a
training-only preprocessing baseline:

- The training split is grouped by protected attribute `s` and binary label `y`.
- Each `(s, y)` cell is oversampled to the largest training-cell count.
- Synthetic rows are generated within the same `(s, y)` cell using the
  Fair-SMOTE generator: choose a parent row and two nearest-neighbor candidates,
  then mutate numeric columns as `parent + f * (neighbor_1 - neighbor_2)` with
  `f=0.8`. Categorical and binary columns use schema-aware adaptations of the
  repo's string/boolean handling.
- The protected attribute and label are fixed to the cell values for every
  synthetic row.
- After balancing, a logistic regression situation tester is fit on the
  resampled training split. Rows whose predicted label changes when the
  protected attribute is toggled are removed.
- Validation, test, audit anchors, and repair/evaluation corner banks are not
  modified.
- The downstream model is the same `3x128` MLP used by the other baselines.
- Checkpoint selection is validation utility only, matching ERM/reweighting.

Schema repair after mutation:

- One-hot categorical blocks are sampled from the parent or either neighbor.
- Binary indicators use the Fair-SMOTE boolean-style mutation; missing indicators
  are sampled from parent/neighbor rows.
- Continuous processed columns are clipped to the training processed range.
- The repo applies `abs(...)` because its features are min-max normalized. Our
  pipeline has signed z-score columns, so the nonnegativity projection is applied
  only to processed columns whose training values are nonnegative; signed columns
  are clipped without absolute-value projection.

The initial random-within-cell pilot, the balancing-only nearest-neighbor pilot,
and the full-but-interpolating pilot have been superseded by the DE-faithful full
Fair-SMOTE outputs under `results_full_de_v1`.

## Checks Passed

- Syntax checks passed for `run_fairness_interactions.py` and
  `run_additional_fairsmote.sh`.
- Adult one-epoch smoke run completed on GPU.
- Determinism check passed: calling the Fair-SMOTE preprocessing twice with the
  same seed produced identical arrays.
- Adult one-hot, sensitive-column, and label validity checks passed.
- ACS sensitive-column and label validity checks passed.
- All seed-0 corrected runs have balanced `(s, y)` cells before situation-testing
  removal in the saved metadata. Final counts can differ because the
  situation-testing step removes rows after balancing, matching the notebook.

## Corrected Seed-0 Results

Fresh full DE-faithful Fair-SMOTE results live in:

`runs/fairsmote/results_full_de_v1`

| Dataset | Val AUC | Floor | Pass | Test AUC | Acc | AOD | EOD | FPR | EOmax | DP | Pair | Proxy score | Proxy effect | Balanced n | Removed | Final n |
|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HMDA-MD | 0.8502 | 0.840 | yes | 0.8499 | 0.8244 | 0.0126 | 0.0056 | 0.0197 | 0.0197 | 0.0641 | 0.5050 | 0.2830 | 0.5103 | 271060 | 6656 | 264404 |
| HMDA-VA | 0.8552 | 0.840 | yes | 0.8517 | 0.8443 | 0.0255 | 0.0197 | 0.0313 | 0.0313 | 0.0454 | 0.4560 | 0.2863 | 0.5430 | 459620 | 11986 | 447634 |
| HMDA-PA | 0.8307 | 0.840 | no | 0.8298 | 0.8003 | 0.0315 | 0.0387 | 0.0244 | 0.0387 | 0.0644 | 0.4388 | 0.3172 | 0.4762 | 683860 | 58739 | 625121 |
| HMDA-OH | 0.8414 | 0.840 | yes | 0.8412 | 0.8088 | 0.0390 | 0.0404 | 0.0375 | 0.0404 | 0.0402 | 0.3699 | 0.2230 | 0.4175 | 714836 | 49655 | 665181 |
| Adult | 0.8818 | 0.895 | no | 0.8914 | 0.8408 | 0.1061 | 0.1394 | 0.0728 | 0.1394 | 0.1821 | 0.7170 | 0.7765 | 0.4464 | 54568 | 5162 | 49406 |
| ACS age | 0.7586 | 0.748 | yes | 0.7490 | 0.7081 | 0.1041 | 0.0588 | 0.1494 | 0.1494 | 0.1299 | 0.3339 | 0.6390 | 0.2221 | 46272 | 9930 | 36342 |

## Interpretation

Fair-SMOTE is now implemented as a fair, utility-selected preprocessing
baseline. It can improve some endpoint fairness metrics, but it does not
explicitly optimize the direct interaction audit, so large residuals remain on
some datasets. That is the expected comparison point for the paper: data
balancing can help endpoint behavior, while interaction steering targets the
learned feature-use rule directly.
