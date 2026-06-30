# Intersectional Fairness — Experiment Instructions (race × sex)

## Context (you already know the codebase)
You built and audited the HMDA direct-interaction fairness experiments
(`run_fairness_interactions.py`, the direct/proxy finite-difference machinery, the
S0–S5 specification ladder, the baselines, the wrong-spec controls, frozen audit banks,
behavior-vs-mechanism reporting). This is a **new experiment** that extends that work to
**intersectional** bias: race × sex. Reuse the existing machinery — this doc specifies only
what is new: the setting, the interaction objects, the questions, the run plan, and the
tuning protocol.

**Do seed 0 fully first, then replicate seeds 1–2.**

---

## 1. Setting & dataset
- **Dataset: HMDA.** Keep **both** protected attributes as model inputs:
  race ∈ {White=0, Black=1} and sex ∈ {Male=0, Female=1}. Filter sex to Male/Female (drop
  Joint/NA), as race is already filtered to White/Black. This gives **four subgroups**:
  WM, WF, BM, BF.
- This is a **different input setting** than the race-only HMDA runs (sex is now an input and
  the population is re-filtered), so **baselines must be retrained in this setting.** Do **not**
  reuse the race-only baselines.
- **Subgroup cell size is the binding constraint.** Black-female × label × feature-quantile
  cells are the smallest. Maryland has the highest Black share and the large states (PA/OH)
  have the most rows — **count cells and pick the state with adequate BF cells under the
  min-cell-size-8 guard.** Do seed-0 development on the **single best state**, then extend the
  winning recipe to the others.
- Adult has race+sex too but is small; treat it as an **optional stretch** only if its BF cells
  survive the size guard. ACS is a later extension.

---

## 2. The interaction objects (all forbidden targets = 0)
Score (logit) `s(r,g,x)`; feature `j` toggled `lo=q10 → hi=q90`;
feature effect at subgroup `(r,g)`: `e_j^{r,g} = s(r,g, X_j=hi) − s(r,g, X_j=lo)`.
Means over held-out anchors; aggregate per-feature objects over the 7 HMDA features (mean),
exactly as the existing proxy-effect metric does. Direct setting → toggle r, g, X_j on the
**same anchor**.

| Object | Definition | Maps to |
|---|---|---|
| **D2race_j** marginal race×feature | `E[ ē_j^{B,·} − ē_j^{W,·} ]` (avg over sex) | Option 1 component |
| **D2sex_j** marginal sex×feature | `E[ ē_j^{·,F} − ē_j^{·,M} ]` (avg over race) | Option 1 component |
| **D3_j** intersectional 3rd-order | `E[ (e_j^{B,F} − e_j^{W,F}) − (e_j^{B,M} − e_j^{W,M}) ]` | **Option 3 (headline)** |
| **D2rs** race×sex on outcome | `E[ (s^{B,F} − s^{W,F}) − (s^{B,M} − s^{W,M}) ]` (no feature) | Option 2 (side-rule) |
| **Gsub_j** worst-subgroup feature gap | worst pairwise `|e_j^{sg} − e_j^{sg'}|` over the 4 subgroups | interpretable mechanism |

`D3_j` reads as: *race modulates feature X_j's effect differently for women than for men.*
It is the part of the subgroup feature-effect variation **not** explained by the two marginals,
which is why joint-marginal repair cannot pin it.

**Direct vs proxy:** primary = **direct** (both attributes present, same-anchor `D3`). The
attribute-removed twin (4 matched subgroup banks → worst-subgroup gap) is an **optional**
complementary result; do it only after the direct path is done.

---

## 3. Behavior metrics (the consequence — report beside the mechanism)
The mechanism residuals above show the bug; we also need the **behavioral consequence**:
- **AOD_race**, **AOD_sex** — standard marginal average-odds disparities.
- **sAOD (worst-subgroup AOD)** and **sEOD (worst-subgroup EOD)** — disparity computed over the
  **4 subgroups**, taking the worst cell/pair. **This is the consequence metric.** The
  gerrymandering signature is: **AOD_race and AOD_sex small, but sAOD/sEOD large.**
- (optional) subgroup counterfactual flip rate (flip race & sex jointly).
- Utility: **AUC, accuracy**; enforce the validation-AUC floor used in prior runs.

---

## 4. Questions to answer

**A — Is there an intersectional bug, and what does it cost? (audit)**
- A1: With race+sex present, does **ERM** show nonzero D2race, D2sex, **D3**, D2rs?
- A2: Is the **intersectional D3** component non-trivial *beyond* the two marginals?
- A3 (consequence): Is **sAOD/sEOD ≫ AOD_race/AOD_sex** for ERM — i.e., the harm sits at the
  subgroup the marginal metrics miss?

**B — Do marginal/standard fixes leave it? (insufficiency → motivates Option 3)**
- B1: Does **joint-marginal repair (Option 1)** drive D2race, D2sex → 0 but **leave D3 and sAOD
  large**? (the gerrymandering result — the load-bearing finding)
- B2: Do **blind / reweight / adversarial** reduce sAOD? (expected: no)
- B3: Does suppressing only **race×sex (Option 2)** fix sAOD but **not** D3 (feature-use subgroup
  disparity)?

**C — Does intersectional repair fix it? (repair)**
- C1: Does **Option 3 (D3→0)** drive D3 and sAOD to ~0?
- C2: Is Option 3 **alone** enough, or do the marginals drift unless you steer
  **joint-marginal + intersectional together**?
- C3: Utility cost vs the AUC floor.
- C4 (**RQ5 headline**): Can **one model** hold marginal-race, marginal-sex, and intersectional
  specs **simultaneously** at bounded utility?

**D — Attribution**
- D1 (**matched control**): all-together (R4) **vs** joint-marginal (R1) isolates the
  intersectional terms — same setup, only the 3rd-order term differs.
- D2 (**placebo**): wrong-spec that amplifies/flips D3 → sAOD and D3 worsen.

---

## 5. Run plan (seed 0 first)

**Phase 0 — Pre-screen (saturation gate).** Count subgroup cells; pick state(s). Train **ERM**
and **R1 (joint-marginal)**. Confirm D3 and sAOD are **non-trivial AND survive R1.**
- If R1 already kills them, the chosen features show no intersectional bug → try other
  features/state, or record a negative result.
- **Do not invest in repair until the bug is confirmed to survive marginal repair.**

**Phase 1 — Baselines + bug identification (race+sex-present setting).** Train and audit
**ERM, blind (both attributes removed), reweighting, adversarial debiasing.** Report the full
mechanism + behavior columns. Establish that ERM carries the intersectional bug (large D3) and
its consequence (large sAOD) behind acceptable *marginal* metrics, and that standard baselines
don't fix the subgroup.

**Phase 2 — Interaction-repair variants (each tuned; see §6).** All **guarded** (score-gap +
boundary + AUC floor), corners-as-probes (no labels on corners):

| Variant | Loss | Role |
|---|---|---|
| **R1 joint-marginal** (Option 1) | `L_race + L_sex` | matched control / baseline to beat |
| **R2 race×sex** (Option 2) | `L_rs` | characterize the side-rule |
| **R3 intersectional-only** (Option 3) | `L_inter` (sum_j D3_j²) | 3rd-order alone |
| **R4 all-together** (full spec) | `L_race + L_sex + L_inter` (+ optional `L_rs`) | **headline** |
| wrong-spec control | flip/amplify D3, behavior-only selection | attribution |
| no-effect control | guards only, drop interaction terms | attribution |

**Priority order if time is short:** ERM + baselines → **R1** → **R4** → wrong-spec. R2, R3, and
the proxy/attribute-removed twin are characterization extras.

**Phase 3 — Synthesis.** Headline table; confirm **R4 (one model)** satisfies all specs and
minimizes sAOD; confirm **R1 leaves D3/sAOD** (gerrymandering); confirm matched-control
attribution (R4 vs R1) and the placebo.

**Phase 4 — Seeds 1, 2.** Replicate at minimum **baselines + R1 + R4 + wrong-spec** on two more
seeds; report mean ± std.

---

## 6. Tuning protocol for repair runs (important)
Repair runs usually need tuning. For **each** repair variant:
1. **Success** = its target mechanism residual driven low **AND** its behavior metric
   (for the intersectional variants: **sAOD**) **beats the relevant baseline/control** **AND**
   AUC ≥ floor.
2. **Iterate** over: per-term λ weights, guard weights (score-gap, boundary), AUC floor, and
   selection (behavior+mechanism for repair).
3. **Watch the flatten failure** (the Adult lesson): if a variant drives the mechanism to ~0 but
   **worsens** behavior (sAOD/AOD up), it is flattening the protected pathway — strengthen
   guards, lower the interaction λ, or raise the AUC floor, then retry.
4. **If a variant is losing to a baseline, retry** (≈6–8 configs) before giving up. Only after a
   clear win — or an exhausted, logged search — move to the next variant.
5. **Log every attempt** (config + all metrics); keep the best checkpoint per variant.

---

## 7. Fair-comparison rules (unchanged from prior runs)
- Baselines and wrong-spec/no-effect selected on **behavior only**; repair may select on
  behavior + mechanism.
- **Freeze** the audit/corner banks before comparison; apply the **same** frozen audits to every
  row, including baselines.
- Minimum subgroup-cell size 8; report per-feature and aggregated.
- Same train/val/test split per seed across all rows.

---

## 8. Deliverable
A report MD (mirror the existing HMDA reports): **seed-0 table first**, then **3-seed mean ± std**,
with columns:

```
State | Model | AUC | Acc | AOD_race | AOD_sex | sAOD | sEOD | D2race | D2sex | D3(inter) | D2rs | Gsub
```

plus a short narrative answering **A–D** and stating the **RQ5 headline**: one model satisfies
the marginal-race, marginal-sex, and intersectional specs at once, gerrymandering is shown
(R1/standard baselines leave sAOD), and the intersectional repair removes it at bounded utility.
Save under `runs/reports/` and note the result paths.
