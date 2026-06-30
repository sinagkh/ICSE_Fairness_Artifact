# Confirmatory Rerun Instructions for the ICSE Fairness Debugging Paper

This file is for the Codex thread that has already run the earlier fairness
experiments. It does not re-explain the codebase. The purpose is to document why
we are rerunning the experiments, what must change, and the checklist for moving
from one-seed calibration to paper-facing 10-seed results.

## Why These Reruns Are Needed

The earlier runs established the empirical story, but several methodology choices
need to be cleaned up before the results can be used as confirmatory ICSE paper
evidence:

- Baseline ERM, blind, reweighting, and adversarial models should not be selected
  using endpoint fairness metrics. ERM and blind should be selected using task
  utility only. Other baselines should use the selection criterion implied by the
  method, not our interaction audit metrics.
- The neural architecture/training protocol should be frozen and simplified:
  remove incidental dropout, use one batch size across datasets if memory allows,
  and use a fixed adversarial weight.
- Interaction steering should be selected by validation utility plus the intended
  mechanism residual. It should not be selected directly by test metrics or by
  endpoint fairness metrics such as AOD/EOD/DP.
- The final paper should report statistical grouping over repeated runs using a
  Scott-Knott procedure with Cliff's Delta and a bootstrap test. That requires
  more than the current 3-seed evidence. Target 10 seeds for paper-facing tables.

The goal is not to search until every table looks ideal. The goal is to do a
small, logged, validation-only calibration pass under the cleaned protocol, freeze
the chosen configurations, and then run confirmatory seeds.

## Frozen Primary Training Protocol

Use this protocol unless a command explicitly documents a necessary exception:

- Predictor: MLP with 3 hidden layers, 128 units per layer, ReLU.
- Dropout: `0.0`.
- Batch size: `512` for every dataset if memory allows.
- Optimizer: AdamW.
- Learning rate: `7e-4`.
- Weight decay: `1e-4`.
- Max epochs: `100`.
- Patience: `12`.
- Threshold for reported endpoint metrics: `0.5`.
- Adversarial hidden dim: `64`.
- Adversarial loss weight: `0.1`, fixed for every dataset.
- Confirmatory seeds: `0 1 2 3 4 5 6 7 8 9`.

Do not use the DICE-style small network as the primary architecture. Keep the
DICE-style architecture as an optional robustness check after the main 10-seed
results are complete.

## Phase 3 Frozen Row Set

Phase 3 runs the nine remaining seeds, `1 2 3 4 5 6 7 8 9`, under the cleaned
checkpoint-selection protocol. Seed `0` remains the calibration/check source.

The global training budget is fixed everywhere:

- Max epochs: `100`.
- Patience: `12`.
- Batch size: `512`.
- Anchor batch size: `512`.
- Dropout: `0.0`.
- Optimizer: AdamW, learning rate `7e-4`, weight decay `1e-4`.
- Baselines use utility-only checkpoint selection.
- Correct interaction repairs use utility guard plus intended mechanism residual.
- Wrong-specification controls use a bounded wrong target plus utility guard.

Paper-facing rows:

- HMDA main states (`MD`, `VA`, `PA`, `OH`): shared baselines
  `erm`, `blind`, `reweight`, `adv`, plus score/wrong controls. For `MD`,
  `VA`, and `PA`, the launcher folds these shared rows into the `repair_main0`
  invocation. For `OH`, the Ohio ladder is the main0 superset and should be used
  as the OH source for shared baselines and `repair_main0`. Run two
  `direct_spec_boundary` repair variants for every state:
  - `repair_main0`: `lambda_main=0.0`, interaction repair without protected-main
    suppression.
  - `repair_main05`: `lambda_main=0.50`, same interaction repair with the
    protected-main guard active.
  Both HMDA repair variants use the calibrated `boundary_band=0.10`; the
  cross-state comparison must not confound `lambda_main` with a different
  boundary band.
  The final paper row can be chosen after comparing the aggregate 10-seed
  frontier, rather than state-by-state cherry-picking.
- Adult gender: shared baselines plus one primary repair,
  `direct_spec_boundary` with `lambda_main=0.0`.
- ACS Employment age: shared baselines plus two repairs,
  `proxy_exhaustive` and `direct_spec_boundary` with `lambda_main=0.0`.
- HMDA Ohio ladder: run the explicit ladder rows because this is the ablation
  experiment: score-only, proxy/effect repair, boundary repair, full repair, and
  wrong-specification control, alongside the shared baselines.
- ACS Employment age x race intersectional: shared baselines used for this
  table are `erm`, `blind`, `reweight`, and `adv`; matched repair/control rows are
  `r1_joint_marginal`, `r3_intersectional`, `r4_r1plus`, `no_effect`, and
  `wrong_d3`. `r4_r1plus` is the primary R4 row.

The runnable dry-run launcher is:

```bash
DRY_RUN=1 bash reproduce/run_phase3_confirmatory.sh
```

To execute with controlled parallelism:

```bash
DRY_RUN=0 MAX_JOBS=3 bash reproduce/run_phase3_confirmatory.sh
```

Start with `MAX_JOBS=2` or `3` and watch `nvidia-smi`, CPU load, and log
progress. Increase only if GPU memory and CPU contention remain healthy.

## Phase-3 Runtime Plan

The seed-0 confirmatory runs showed that the A10 is not saturated by a single
tabular interaction job. The active HMDA runs used the GPU, but utilization was
only about 15--20% while one Python process held one CPU core at roughly 100%.
The bottleneck is the interaction/audit loop: repeated finite-difference corner
construction, feature/slice/context loops, and validation mechanism audits. More
PyTorch CPU threads alone will not fix this because much of the hot path is
serial Python control flow.

Before launching the full 10-seed sweep:

- [x] Prefer parallel independent jobs over one long serial job. The Phase 3
  launcher now schedules one job per experiment x seed, writes seed-isolated
  output directories to avoid JSON/report races, and uses `MAX_JOBS` as the
  concurrency cap.
- [ ] Check larger fair batches on seed 0 before freezing Phase 3, e.g.
  `batch-size=2048` and `anchor-batch-size=1024` or `2048`, as long as selected
  metrics and checkpoint choices remain comparable.
  Phase 3 currently keeps `512/512` to preserve exact comparability with the
  seed-0 confirmatory artifacts; the practical speed lever is running multiple
  independent jobs with `MAX_JOBS`.
- [x] Cache preprocessed train/validation/test arrays and splits with
  `--prepared-cache-dir`, keyed by dataset/state/seed/config. This avoids
  repeated HMDA CSV reads and preprocessing across paired main0/main05 jobs.
- [ ] Precompute/vectorize true finite-difference corner tensors where possible.
  The current cache stores prepared arrays/splits; the repair loop still builds
  model-dependent corner tensors on sampled anchors.
- [ ] Vectorize interaction evaluation over axes/slices/context pairs into
  larger GPU batches rather than looping over many small model calls.
- [ ] Consider evaluating expensive mechanism audits every few epochs, while
  keeping validation utility every epoch, if a seed-0 equivalence check shows the
  selected checkpoints are stable.
- [x] Add a predeclared `min_delta` and/or row-specific maximum epoch cap for
  wrong-specification controls. These controls often preserve utility while
  continuously improving their wrong objective, so patience can reset for many
  epochs even though they are not candidate repairs. The scripts now expose
  `--selection-min-delta`; Phase 3 uses `1e-4`.
- [x] Revisit wrong-specification loss design before Phase 3. The wrong-spec
  controls use bounded margin targets: once the wrong interaction reaches the
  requested margin, additional amplification is not rewarded by the selector.
  The ACS intersectional `wrong_d3` row now also uses
  `utility_guard_plus_wrong_spec` rather than utility-only selection.
- [ ] Record the concurrency, batch sizes, audit frequency, and any wrong-control
  cap in the final artifact manifest so the runtime protocol is reproducible.

## Required Selection Criteria

Update or wrap the scripts as needed so every selected checkpoint records its
effective selection policy in the artifact manifest.

Selector AUC floors are predeclared in the Phase 3 launcher and can be
overridden only by environment variables before the sweep starts:

- HMDA: `HMDA_MIN_AUC=0.84`.
- Adult: `ADULT_MIN_AUC=0.895`, matching the seed-0 Adult freeze.
- ACS age: `ACS_AGE_MIN_AUC=0.748`.
- ACS intersectional: `ACS_INTERSECTIONAL_MIN_AUC=0.73`.

Phase 4 must sanity-check that all completed seeds cleared their task's utility
floor; any seed that fails the floor should be reported rather than silently
dropped.

- ERM, protected attribute present: validation task utility only. Prefer lowest
  validation BCE/cross-entropy because it matches the training objective and is
  threshold-independent. Record validation AUC and accuracy.
- Blind/protected attribute removed: same as ERM, utility-only.
- Reweighting: train with group-label weights; select by task utility only, or by
  weighted validation loss if that is declared in the report. Do not select by
  validation AOD/EOD/DP.
- Adversarial debiasing: fixed adversarial objective with `lambda_adv=0.1`.
  Select by validation BCE/task utility, unless a cited implementation prescribes
  a different validation objective. Do not tune adversarial strength per dataset.
- Score-only/endpoint control: select by its own score/endpoint objective plus
  utility guard. Do not use interaction residuals.
- No-effect/scaffold control: if it has no fairness objective, select utility
  only; if it has score guards, select by its own stated guard objective plus
  utility. Do not give a scaffold/no-effect control AOD/EOD/DP selection unless
  the row is explicitly defined as an endpoint-fairness control.
- Wrong-spec control: select by the wrong specification's own objective plus
  utility guard; evaluate it on the true/correct audit metrics.
- Interaction repair: select by validation utility guard plus the intended
  interaction/mechanism residual. Operationally, reject checkpoints below the
  declared validation utility floor or heavily penalize them; among surviving
  checkpoints, select the lowest intended mechanism residual; use validation BCE
  only as a tie-breaker. Do not include AOD/EOD/DP in the selector unless a row is
  explicitly an endpoint-fairness baseline/control.

Use the same train/validation/test split for all rows within a seed. Never choose
models based on test metrics.

## Common Baseline Block

For every paper-facing dataset/task, run this baseline block under the cleaned
protocol:

- [ ] ERM with protected attribute present.
- [ ] Protected attribute removed / blind.
- [ ] Reweighting.
- [ ] Adversarial debiasing with fixed `lambda_adv=0.1`.
- [ ] Score-only or endpoint control where it is part of the RQ/table.
- [ ] No-effect/scaffold control where it is part of the attribution story.
- [ ] Wrong-spec control where it is part of the attribution story.

The baseline block should be runnable as one command per dataset/task and should
write a consolidated result JSON plus a report table.

## Baseline Matrix by Experiment

The following rows make the baseline plan explicit. The first four baselines are
required for every paper-facing experiment. Additional rows depend on the RQ and
the attribution story for that experiment.

### Required for Every Experiment/Dataset

Run these for every HMDA state, Adult, ACS-age, ACS age x race, and Ohio ladder
setting:

- [ ] `erm`: protected attribute present, utility-selected ERM.
- [ ] `blind`: protected attribute removed, utility-selected ERM on the reduced
  input.
- [ ] `reweight`: group-label reweighted ERM, utility/weighted-utility selected.
- [ ] `adv`: adversarial debiasing, fixed `lambda_adv=0.1`, validation
  BCE/task-utility selected.

If a task has both protected-present and protected-removed versions of a baseline
from older exploratory runs, keep the paper-facing baseline simple unless there
is a specific RQ reason to include both. The default paper-facing comparison is
protected-present ERM/reweight/adv plus protected-removed blind.

### HMDA Race Main States

Core baselines:

- [ ] `erm`.
- [ ] `blind`.
- [ ] `reweight`.
- [ ] `adv`.

Additional baseline/control rows for the main HMDA table:

- [ ] `proxy_score_only` or the corresponding score-only/endpoint control used
  in the prior HMDA main table.
- [ ] `no_effect` / scaffold control if used to show the gain is not just from
  the training scaffold or guards.
- [ ] `wrong_spec` if used to show specification attribution.

Repair rows:

- [ ] `direct_spec_boundary` with `lambda_main=0.0`.
- [ ] `direct_spec_boundary` with `lambda_main=0.50`.

### HMDA Ohio Ladder

Core baselines:

- [ ] `erm`.
- [ ] `blind`.
- [ ] `reweight`.
- [ ] `adv`.

Additional ladder baseline/control rows:

- [ ] Score-only/endpoint row for the ladder.
- [ ] Full score-only/no-effect scaffold row.
- [ ] Wrong-specification row.

Repair/ablation rows:

- [ ] Every frozen protected-present ladder step, e.g. score-only control,
  core proxy/effect repair, boundary-local repair, slice/worst-slice repair, and
  full specification repair.

Do not collapse Ohio to a single repair row. Ohio is the RQ3 ablation.

### Adult Gender

Core baselines:

- [ ] `erm`.
- [ ] `blind`.
- [ ] `reweight`.
- [ ] `adv`.

Additional baseline/control rows:

- [ ] Score-only/endpoint control if it appears in the Adult paper table.
- [ ] No-effect/scaffold control if used for attribution.
- [ ] Wrong-specification control if used for attribution.

Repair rows:

- [ ] `direct_spec_boundary` with `lambda_main=0.0`.

### ACS Age

Core baselines:

- [ ] `erm`.
- [ ] `blind`.
- [ ] `reweight`.
- [ ] `adv`.

Additional baseline/control rows:

- [ ] Score-only/endpoint control if included in the ACS-age table.
- [ ] No-effect/scaffold control if used for attribution.
- [ ] Wrong-specification control if used for attribution.

Repair rows:

- [ ] `proxy_exhaustive`.
- [ ] `direct_spec_boundary` with `lambda_main=0.0`.

### ACS Age x Race Intersectional

Core baselines:

- [ ] `erm`.
- [ ] `blind`.
- [ ] `reweight`.
- [ ] `adv`: four-way label-conditioned adversarial debiasing with fixed
  `lambda_adv=0.1`.

Intersectional additional baselines/controls:

- [ ] `r1_joint_marginal`: joint marginal age/race repair. Treat this as the
  matched baseline/control for the intersectional claim because it tests whether
  marginal repair alone leaves the intersectional bug.
- [ ] `no_effect`: scaffold/guard-only control.
- [ ] `wrong_d3`: wrong intersectional-specification control.

Repair rows:

- [ ] `r4_r1plus`: frozen full guarded intersectional repair. This is R1's
  marginal repair/guards plus `D3`, `D2ar`, and subgroup preservation.
- [ ] `r3_intersectional` only if it is needed to explain the mechanism or if it
  is frozen into the paper plan.

The key comparison here is not only repair vs ERM. It is also full
intersectional repair vs `r1_joint_marginal`: R1 should show what marginal
fairness misses, and R4 should show that steering the intersectional relation
fixes it.

## Phase 3 Repair Variant Matrix

Seed `0` has already served as the calibration/check seed. Phase 3 should run
the frozen row set below on seeds `1 2 3 4 5 6 7 8 9`; do not reopen broad
variant search during the 9-seed sweep.

Use protected-present repair variants as the paper-primary variants. Protected
attribute removed repair rows, such as older `spec_*_blind` ladder rows, should
be used only when the RQ explicitly asks for a blind-repair ablation or robustness
check. The main blind row is a baseline, not the primary repair story.

No-effect/scaffold and wrong-spec rows are controls, not repair candidates. Run
them when they are part of the table, but do not count them as the 2-3 repair
variants used to choose the frozen repair.

### Repair Variants by Experiment

HMDA race main states:

- [ ] `direct_spec_boundary`, `lambda_main=0.0`.
- [ ] `direct_spec_boundary`, `lambda_main=0.50`.
- [ ] Controls: `proxy_score_only` and `direct_spec_boundary_wrong_effect`.

Adult gender:

- [ ] `direct_spec_boundary`, `lambda_main=0.0`.
- [ ] Controls: `proxy_score_only` and `direct_spec_boundary_wrong_effect`.

ACS age:

- [ ] V1 `proxy_exhaustive`.
- [ ] V2 `direct_spec_boundary`, `lambda_main=0.0`.
- [ ] Controls: `proxy_score_only` and `direct_spec_boundary_wrong_effect`.

HMDA Ohio ladder:

- [ ] Run the full ladder because Ohio is the RQ3 ablation, not a compact
  one-repair comparison.
- [ ] Protected-present ladder candidates should include the score-only control,
  core proxy/effect repair, boundary repair, and full specification repair, e.g.
  `proxy_score_only`, `proxy_exhaustive` or `proxy_effect`,
  `direct_spec_boundary`, and `direct_spec_full`.
- [ ] Include wrong-spec/no-effect controls for attribution.
- [ ] If older `spec_*_blind` rows are rerun, label them as blind-ladder
  robustness rather than the primary protected-present ladder.

ACS age x race intersectional:

- [ ] `r1_joint_marginal`: matched marginal repair/control.
- [ ] `r3_intersectional`: intersectional-only repair.
- [ ] `r4_r1plus`: primary full guarded intersectional repair.
- [ ] Controls: `no_effect` and `wrong_d3`.

### Choosing Paper Rows After Phase 3

After Phase 3 completes, choose paper rows from aggregate 10-seed behavior and
mechanism results:

- [ ] HMDA: compare `main0` vs `main05` over all four states and choose the
  paper-facing repair variant from the aggregate frontier.
- [ ] Adult: use `direct_spec_boundary`.
- [ ] ACS age: compare `proxy_exhaustive` and `direct_spec_boundary`.
- [ ] Ohio: keep the ladder rows for the ablation/RQ3 evidence.
- [ ] ACS intersectional: compare `r1_joint_marginal`, `r3_intersectional`, and
  `r4_r1plus`; the expected primary row is `r4_r1plus`.

## Repair Block Policy

Use the previous successful repair configurations as the center point for the new
protocol. Do not discard them. Removing `0.05` dropout and changing checkpoint
selection may change the chosen checkpoint, but the old lambda scales are still
the best starting point.

For each experiment/dataset, finish the seed-0 baseline block first. Only after
the baselines for that setting are complete should you run the repair row(s) for
that same seed. The repair decision is comparative: compare the repair against
ERM and the other baselines in the same dataset, same seed, same split, and same
audit bank before moving to the next experiment.

The repair must show a paper-usable win, not only a lower mechanism residual.
The intended mechanism residual should go down, but the result also needs to
improve fairness behavior metrics such as AOD, EOdds-max/TPR-FPR gaps, DP,
counterfactual flip rate, subgroup AOD/sAOD, or the task-specific behavior
metrics used in that table. Utility may trade off, but the utility cost must be
bounded and explainable.

The minimum win standard is:

- Against ERM, the repair should improve almost all relevant fairness behavior
  metrics. Utility is the expected exception, because repair can trade some AUC
  or accuracy for fairness.
- Against other baselines, the repair should generally win on the behavior
  metrics. If it loses one behavior metric to a baseline, there must be a clear
  tradeoff: that baseline should lose worse on another important behavior metric
  or on the interaction/mechanism metric that motivates the paper.
- A repair that only lowers the interaction residual but does not improve the
  fairness behavior story is not ready for the paper table. Calibrate it before
  marking the experiment done.

For each experiment family, decide whether the paper table needs only the best
repair row or multiple repair rows:

- Main HMDA state experiments, Adult gender, and ACS age: in seed `0`, run the
  2-3 repair candidates in the repair variant matrix. After seed `0`, freeze the
  winning primary row for 10 seeds, plus a second row only if the RQ needs the
  tradeoff. Also run the matched no-effect and wrong-spec controls when they are
  needed for attribution.
- Ohio ladder: run the full ladder. This is the ablation/RQ3 evidence, so do not
  collapse it to one repair row.
- ACS age x race intersectional: run the intersectional rows needed for the RQ4
  story. At minimum include ERM, blind, reweighting, R1 joint-marginal, R4/full
  guarded intersectional repair, no-effect, and wrong-D3. Include R3
  intersectional-only if it helps explain the mechanism.

## Phase 0: Script Readiness Checklist

- [x] Confirm `run_fairness_interactions.py` can run with dropout `0.0`, batch
  size `512`, max epochs `100`, patience `12`, and `lambda_adv=0.1`.
- [x] Confirm `run_acs_intersectional.py` can run with the same architecture and
  training settings.
- [x] Add or verify utility-only selection for ERM/blind/reweighting.
- [x] Add or verify validation BCE/task-utility selection for adversarial
  debiasing under fixed `lambda_adv=0.1`, unless a cited implementation
  prescribes a different validation objective.
- [x] Add or verify mechanism-plus-utility selection for interaction repair.
- [x] Ensure artifact manifests record architecture, optimizer settings,
  selection policy, selection metric values, seed, dataset, protected attribute,
  and model name.
- [x] Ensure result JSONs include both validation and test metrics for the
  selected checkpoint.
- [x] Ensure reported metric names distinguish:
  - `TPR gap / equal opportunity gap`.
  - `FPR gap`.
  - `AvgAbsOdds / AOD`.
  - `EOdds max = max(TPR gap, FPR gap)` when reported.
- [x] Ensure test metrics are never used in selection.

## Phase 1: One-Seed Calibration Pass

Run seed `0` first for every experiment family. This pass answers: do the cleaned
settings still reproduce the empirical story, and do the previous repair configs
still work?

Within each experiment/dataset, use this order:

- [ ] Run and summarize all baselines for seed `0`.
- [ ] Run the planned repair row(s) for seed `0`.
- [ ] Compare repair against ERM and every baseline on utility, mechanism, and
  fairness behavior metrics.
- [ ] If the repair wins under the criteria above, mark that experiment/dataset
  ready for the freeze step and move to the next experiment.
- [ ] If the repair does not win, calibrate the repair configuration using
  validation metrics, rerun the repair for seed `0`, and repeat the comparison.
- [ ] Stop calibration only when the repair has a usable win or the logged
  calibration grid is exhausted.

### HMDA Race: Multi-State Main Experiments

Target states: use the states already planned for the paper-facing HMDA race
table, including the prior MD/VA/PA-style main table states.

- [ ] Run the common baseline block for seed `0` in each state.
- [ ] Run the seed-0 repair candidates from the repair variant matrix in each
  state.
- [ ] Run no-effect and wrong-spec controls where needed.
- [ ] Check utility-selected ERM behavior. Record whether AOD/EOD/DP changed
  materially relative to the older behavior-selected ERM.
- [ ] Check that interaction repair reduces the intended interaction residual
  while preserving bounded utility.
- [ ] Mark the state ready for 10 seeds only after the seed-0 report is coherent.

### HMDA Ohio Ladder

Ohio is the full ablation/ladder experiment.

- [ ] Run the common baseline rows needed by the ladder.
- [ ] Run every ladder row under the cleaned protocol.
- [ ] Verify that the ladder tells the intended story: each added specification
  targets the corresponding residual, and the final/full repair is best or
  statistically competitive on the main mechanism metric.
- [ ] If the ladder shape breaks, calibrate only the repair/loss weights; do not
  change baseline selection or architecture.

### Adult Gender

- [ ] Run the common baseline block for seed `0`.
- [ ] Run the seed-0 Adult repair candidates from the repair variant matrix.
- [ ] Run no-effect and wrong-spec controls if they are used in the Adult table.
- [ ] Check that the repair reduces the protected-feature interaction residual
  without simply flattening the classifier or losing unacceptable utility.

### ACS Age

- [ ] Run the common baseline block for seed `0`.
- [ ] Run the seed-0 ACS-age repair candidates from the repair variant matrix.
- [ ] Run no-effect and wrong-spec controls if they are used in the ACS-age table.
- [ ] Check endpoint metrics and interaction residuals separately. Do not tune
  directly on AOD/EOD/DP unless the row is an endpoint baseline/control.

### ACS Age x Race Intersectional

- [ ] Run ERM, blind, reweighting, and the four-way label-conditioned
  adversarial baseline.
- [ ] Run R1 joint-marginal.
- [ ] Run R4/full guarded intersectional repair.
- [ ] Run no-effect and wrong-D3 controls.
- [ ] Optionally run R3 intersectional-only if needed for the mechanism story.
- [ ] Confirm the headline condition: marginal metrics can look acceptable while
  subgroup/intersectional metrics expose the bug; R4 should reduce the
  intersectional residual and subgroup disparity better than R1.

## Calibration Rules

Calibration is allowed only during the one-seed pass and only using validation
metrics.

Start from the previous successful repair settings. If the seed-0 repair is not
good enough, use a small logged grid around the previous settings:

- Interaction loss scale: `0.5x`, `1.0x`, `2.0x`.
- Boundary/slice loss scale: `0.5x`, `1.0x`, `2.0x`.
- Utility guard/floor: keep fixed unless the run clearly collapses utility; if
  adjusted, record the reason.
- Selector implementation: prefer an explicit guard-first selector. Reject or
  heavily penalize checkpoints below the utility floor; among surviving
  checkpoints, select the lowest intended mechanism residual; use validation BCE
  only as a tie-breaker.

For each calibration attempt, log:

- [ ] Dataset/task/state.
- [ ] Seed.
- [ ] Model row.
- [ ] Full command.
- [ ] Lambda/config changes from default.
- [ ] Validation utility.
- [ ] Validation mechanism residuals.
- [ ] Test utility and test metrics, for audit only.
- [ ] Whether the attempt passed or failed, and why.

Success criteria for a repair row:

- [ ] The intended mechanism residual decreases meaningfully against ERM and the
  matched controls.
- [ ] Fairness behavior metrics improve against ERM on almost all relevant
  columns, except for bounded utility tradeoff.
- [ ] Against other baselines, the repair generally wins on behavior metrics. If
  it loses one behavior metric, the competing baseline must lose clearly on
  another important behavior metric or on the mechanism metric.
- [ ] Utility remains within the declared guard or within the acceptable paper
  tradeoff.
- [ ] The result is not just classifier flattening. If mechanism residual improves
  but AUC/accuracy collapses or behavior metrics worsen badly, lower repair
  strength or strengthen guards.
- [ ] The row beats the relevant control on the mechanism it claims to repair.
- [ ] If these conditions are met, mark the experiment/dataset done for seed `0`
  and move to the next experiment. If not, continue the logged calibration pass.

Do not do open-ended test-set tuning. If a repair row fails after a reasonable
logged grid, keep the best result and note the limitation.

## Phase 2: Freeze the Protocol

After seed-0 calibration is complete for all experiment families:

- [ ] Write a frozen config summary listing the chosen command/options for every
  dataset/task/model row.
- [ ] Record which repair config was chosen for each experiment family and why.
- [ ] Confirm no paper-facing row is selected using test metrics.
- [ ] Confirm no baseline is selected using our interaction audit metrics.
- [ ] Confirm all rows use dropout `0.0`, batch size `512`, and the primary
  `3x128` architecture unless explicitly marked otherwise.
- [ ] Confirm adversarial debiasing uses fixed `lambda_adv=0.1`.
- [ ] Commit or otherwise preserve the frozen config summary before launching
  10-seed runs.

Once this phase is checked off, do not change hyperparameters for the
confirmatory 10-seed runs unless there is a documented bug fix.

## Phase 3: Confirmatory 10-Seed Runs

Run seeds `1 2 3 4 5 6 7 8 9` using the frozen protocol, then merge with the
already-curated seed-0 confirmatory artifacts for 10-seed paper tables.

### Main Runs

- [ ] HMDA race main states: common baselines plus `direct_spec_boundary`
  `main0` and `main05`.
- [ ] HMDA Ohio ladder: full ladder plus required baselines.
- [ ] Adult gender: common baselines plus `direct_spec_boundary`.
- [ ] ACS age: common baselines plus `proxy_exhaustive` and
  `direct_spec_boundary`.
- [ ] ACS age x race intersectional: baselines (`erm`, `blind`, `reweight`,
  `adv`) plus `r1_joint_marginal`, `r3_intersectional`, `r4_r1plus`,
  `no_effect`, and `wrong_d3`.

### Run Hygiene

- [ ] Use the same seed list for every row in a task.
- [ ] Use the same split per seed across all rows in a task.
- [ ] Save every selected checkpoint artifact and manifest.
- [ ] Save per-seed result JSONs.
- [ ] Save consolidated `all_results.json` or equivalent per task.
- [ ] Generate mean, standard deviation, and per-seed tables.
- [ ] Keep failed runs visible in a log; do not silently omit bad seeds.
- [ ] Join seed-isolated Phase 3 directories during aggregation. For HMDA, merge
  `main0_with_baselines/seed_*`, `repair_main05/seed_*`, and for OH use
  `hmda_oh_ladder/seed_*` as the main0/ladder source.

## Phase 4: Statistical Ranking and Paper Tables

After 10-seed results are available:

- [ ] Build a Scott-Knott ranking script over the final per-seed test metrics.
- [ ] Use the independent run as the statistical unit: seed within a task, or
  dataset/state x seed for aggregate HMDA tables.
- [ ] Use bootstrap test with `alpha = 0.05`.
- [ ] Use Cliff's Delta to reject practically negligible differences. Use
  `|delta| < 0.147` as negligible unless the paper decides otherwise.
- [ ] Apply ranking only to primary metrics, not every column.
- [ ] For lower-is-better metrics, rank lower values better. For AUC/accuracy,
  rank higher values better.
- [ ] Emit LaTeX-ready cells such as `mean +- std` plus rank letters.
- [ ] Phase 4 aggregation must join the separate Phase 3 directories:
  `main0_with_baselines`, `repair_main05`, `hmda_oh_ladder`, `adult_gender`,
  `acs_age`, and `acs_intersectional_age_race`.

Primary metrics by RQ:

- RQ1/RQ2 main experiments: AUC/accuracy, AOD or EOdds-max, DP if relevant,
  target interaction residual, and counterfactual/proxy residual when used.
- RQ3 Ohio ladder: target ladder residuals plus AUC.
- RQ4 intersectional: AUC, `sAOD`, `aod_excess`, `D3`, and the main marginal
  metrics needed to show the gerrymandering result.

## Deliverables

- [ ] Updated scripts or wrappers implementing the cleaned selection policies.
- [ ] A frozen config summary for all 10-seed runs.
- [ ] Seed-0 calibration reports for every experiment family.
- [ ] 10-seed consolidated result JSONs.
- [ ] 10-seed Markdown reports with mean +- std.
- [ ] Scott-Knott/Cliff/bootstrap rank tables.
- [ ] A short paper-facing methodology note describing the rerun protocol,
  checkpoint selection policy, architecture, seed count, and statistical test.

## Stop Conditions

Stop and report before launching 10-seed runs if any of these happen:

- Utility-only ERM or blind cannot be selected cleanly from the current script.
- A baseline still uses AOD/EOD/DP or interaction residuals for checkpoint
  selection.
- The seed-0 repair result depends on test-set tuning.
- A task requires a different architecture, dropout, batch size, or adversarial
  weight without a clear documented reason.
- The selected repair only wins by collapsing task utility.

The final confirmatory results should be boring to reproduce: fixed scripts,
fixed configs, fixed seeds, saved manifests, and no hidden tuning after seed 0.
