# Confirmatory Baseline and Repair Matrix

Date: June 24, 2026.

This file is the paper-facing source of truth for which rows belong in each
confirmatory fairness experiment. It complements
`CONFIRMATORY_RERUN_INSTRUCTIONS.md` by making the row set explicit.

## Shared Rules

- Protected attribute is present for `erm`, `reweight`, `adv`, and all primary
  repair rows.
- `blind` is the protected-attribute-removed baseline.
- Checkpoint selection:
  - `erm`, `blind`, `reweight`, `adv`: validation task utility only.
  - Score-only/endpoint controls: their own endpoint/score objective plus a
    utility guard.
  - Wrong-spec controls: wrong-spec objective plus a utility guard; evaluate on
    the correct audit metrics.
  - Correct repair rows: utility guard first, then intended mechanism residual,
    with validation BCE only as a tie-breaker.
- Endpoint fairness metrics are held-out outcomes for ordinary baselines and
  correct repairs; they are not checkpoint selectors except for rows explicitly
  defined as endpoint controls.
- Frozen primary architecture: MLP `3x128`, dropout `0.0`, batch size `512`,
  AdamW, learning rate `7e-4`, weight decay `1e-4`, max epochs `100`, patience
  `12`, adversarial weight `lambda_adv=0.1`.

## Required Core Baselines

These four rows are required for every paper-facing experiment:

| Row | Meaning | Selection |
|---|---|---|
| `erm` | Protected attribute present ERM | validation BCE/task utility |
| `blind` | Protected attribute removed ERM | validation BCE/task utility |
| `reweight` | Group-label reweighted ERM | validation BCE/task utility, or weighted utility if declared |
| `adv` | Adversarial debiasing with fixed `lambda_adv=0.1` | validation BCE/task utility |

## HMDA Race Main States

Target states: MD, VA, PA, and OH unless the paper later narrows the main table.

Core baselines:

- `erm`
- `blind`
- `reweight`
- `adv`

Controls:

- `proxy_score_only`: endpoint/score control.
- `direct_spec_boundary_wrong_effect`: matched wrong-boundary control for V2.
- `direct_spec_wrong_effect`: wrong-full-specification control for V3/full-spec
  rows only; do not use it as the matched control for V2.
- No-effect/scaffold control: include only if we define a protected-present
  scaffold row for HMDA; otherwise do not invent an extra row.

Seed-0 repair candidates:

- `direct_spec_boundary` with `lambda_main=0.0`.
- `direct_spec_boundary` with `lambda_main=0.50`.

Default Phase-3 freeze:

- Run both variants for all four states. Choose the paper-facing repair row
  after comparing the aggregate 10-seed behavior/mechanism frontier.
- `main0` uses `lambda_main=0.0`, `boundary_band=0.10`.
- `main05` uses `lambda_main=0.50`, `boundary_band=0.10`. This keeps the
  cross-state main-effect policy comparison unconfounded: only `lambda_main`
  differs.
- Both variants use `lambda_pair=1.0`, `lambda_proxy_score=0.20`,
  `lambda_proxy_pair=0.40`, `lambda_boundary_score=0.20`, and
  `lambda_boundary_pair=0.30`.
- Launcher layout: for MD/VA/PA, shared baselines, score/wrong controls, and
  `main0` are folded into `main0_with_baselines/seed_*`; `main05` is in
  `repair_main05/seed_*`. Ohio uses the ladder as the `main0`/baseline superset
  plus a separate `repair_main05/seed_*`.

## HMDA Ohio Ladder

Ohio is the RQ3 ablation and should not collapse to one repair row.

Core baselines:

- `erm`
- `blind`
- `reweight`
- `adv`

Ladder/control rows:

- `proxy_score_only`: score-only endpoint control.
- `proxy_exhaustive` or `proxy_effect`: core proxy/effect repair.
- `direct_spec_boundary`: boundary-local repair.
- `direct_spec_full`: full specification repair.
- `direct_spec_wrong_effect`: wrong-specification control.

Optional robustness rows:

- Older `spec_*_blind` rows only if framed as blind-ladder robustness, not as
  the primary protected-present ladder.

Default Phase-3 freeze:

- Freeze the full protected-present ladder rows needed for RQ3:
  `proxy_score_only`, `proxy_effect`, `proxy_exhaustive`,
  `direct_spec_boundary`, `direct_spec_full`, and
  `direct_spec_boundary_wrong_effect`, alongside shared baselines.

## Adult Gender

Dataset/task: UCI Adult, protected attribute `sex`, preset
`gender_proxy_no_sparse`.

Core baselines:

- `erm`
- `blind`
- `reweight`
- `adv`

Controls:

- `proxy_score_only`: endpoint/score control.
- `direct_spec_boundary_wrong_effect`: matched wrong-boundary control for V2.
- `direct_spec_wrong_effect`: wrong-full-specification control for V3/full-spec
  rows only.
- No-effect/scaffold control: include only if a protected-present scaffold row is
  explicitly defined; otherwise omit.

Seed-0 repair candidates:

- `direct_spec_boundary` with `lambda_main=0.0`.

Default Phase-3 freeze:

- Run one compact primary repair row: `direct_spec_boundary`.

## ACS Employment Age

Dataset/task: ACS Employment MD, protected attribute `AGEP >= 40`.

Core baselines:

- `erm`
- `blind`
- `reweight`
- `adv`

Controls:

- `proxy_score_only`: endpoint/score control.
- `direct_spec_boundary_wrong_effect`: matched wrong-boundary control for V2.
- `direct_spec_wrong_effect`: wrong-full-specification control for V3/full-spec
  rows only.
- No-effect/scaffold control: include only if a protected-present scaffold row is
  explicitly defined; otherwise omit.

Seed-0 repair candidates:

- V1 `proxy_exhaustive`: core direct/proxy interaction repair.
- V2 `direct_spec_boundary`: boundary-guarded repair; prior ACS winner and
  default primary candidate.

Default Phase-3 freeze:

- Run both `proxy_exhaustive` and `direct_spec_boundary`.
- Both use `lambda_main=0.0`.

## ACS Employment Age x Race Intersectional

Dataset/task: ACS Employment MD, protected attributes `AGEP >= 40` and
Black-vs-White race.

Core baselines:

- `erm`
- `blind`
- `reweight`
- `adv`: four-way label-conditioned adversarial debiasing with fixed
  `lambda_adv=0.1`.

R1 remains the matched marginal-repair control for the intersectional claim.

Matched marginal/intersectional controls:

- `r1_joint_marginal`: matched marginal age/race repair. This is the key control
  for whether marginal repair leaves an intersectional bug. R1 must mean
  applying the single-protected repair separately to age and race: optimize
  `D2age + D2race`, include boundary-local `D2age/D2race`, and use marginal
  age/race behavior guards. It must not optimize `D3`, `D2ar`, subgroup behavior,
  or `sAOD` selection.
- `no_effect`: scaffold/guard-only control.
- `wrong_d3`: wrong third-order specification control.

Repair candidates:

- `r3_intersectional`: intersectional-only repair, optional if useful for
  mechanism explanation.
- `r4_r1plus`: primary full guarded intersectional repair. This is the literal
  R1-plus-intersectional calibration: R1 marginal age/race repair and guards,
  plus `D3`, `D2ar`, and subgroup preservation.
- `r4_full_guarded`: superseded seed-0 calibration; keep only as an internal
  tuning reference, not as the paper-facing primary row.
- `r4_full`: optional guard ablation only if needed.

Default Phase-3 freeze:

- Freeze at least `r1_joint_marginal` and `r4_r1plus`.
- Include `r3_intersectional` only if seed 0 shows it adds explanatory value.
- Use the curated paper-facing seed-0 source
  `confirmatory_phase1_acs_intersectional_seed0_paper`; the older fragmented
  v1/R1-fix/v2 folders are superseded because R1's boundary guard was
  unreachable in v1 and the final R4 row is now `r4_r1plus`.
