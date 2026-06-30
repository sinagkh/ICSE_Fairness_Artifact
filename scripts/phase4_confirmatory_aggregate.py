#!/usr/bin/env python3
"""Aggregate ten-seed fairness runs into submission result tables.

The launcher intentionally writes seed-isolated result trees. This script joins
those trees into summary files and performs the following checks:

* normalize row names across split HMDA directories;
* check validation AUC utility floors;
* emit long and summary CSV files;
* emit a lightweight Scott-Knott-style grouping table using bootstrap and
  Cliff's Delta thresholds.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Iterable


SEEDS = list(range(10))

UTILITY_FLOORS = {
    "hmda_race": 0.84,
    "adult_gender": 0.895,
    "acs_age": 0.748,
    "acs_intersectional_age_race": 0.73,
}

PRIMARY_BEHAVIOR = {
    "single": [
        "auc",
        "accuracy",
        "aod_gap",
        "eod_gap",
        "eodds_max_gap",
        "fpr_gap",
        "dp_gap",
    ],
    "intersectional": [
        "auc",
        "accuracy",
        "aod_age",
        "aod_race",
        "sAOD",
        "aod_excess",
        "eod_age",
        "eod_race",
        "sEOD",
        "eod_excess",
        "sEOdds_max",
    ],
}

PRIMARY_MECHANISM = {
    "single": [
        "pair_abs_mean",
        "pair_abs_q95",
        "pair_abs_max",
        "main_abs_logit_mean",
        "cf_flip_rate",
        "cf_abs_prob_mean",
        "proxy_effect_gap_mean",
        "proxy_effect_gap_max",
        "proxy_score_gap_cond_mean",
        "boundary_proxy_effect_gap_mean",
        "boundary_proxy_effect_gap_max",
        "boundary_proxy_score_gap_cond_mean",
        "higher_order_boundary_proxy_gap_scope_mean",
        "higher_order_boundary_proxy_gap_scope_max",
    ],
    "intersectional": ["D2age", "D2race", "D3", "D2ar", "Gsub"],
}


HIGHER_IS_BETTER = {"auc", "accuracy"}


def is_degenerate_blind_direct_metric(experiment: str, model: str, metric: str) -> bool:
    """Return true for direct protected-attribute mechanisms where blind is trivial.

    The protected-attribute-removed baseline is behaviorally meaningful, but for
    direct main-effect and protected x feature finite differences it can obtain a
    zero residual by construction because the protected input is absent. Keep it
    in behavior/proxy groupings, but exclude it from these direct mechanism
    Scott-Knott comparisons.
    """

    if model != "blind" or experiment == "acs_intersectional_age_race":
        return False
    return metric.startswith("main_") or metric.startswith("cf_") or metric.startswith(
        "pair_abs_"
    )


@dataclass
class Row:
    experiment: str
    dataset: str
    state: str
    seed: int
    source: str
    model: str
    raw_model: str
    label: str
    selector: str
    source_path: str
    test_behavior: dict[str, float]
    test_mechanism: dict[str, float]
    val_behavior: dict[str, float]
    val_mechanism: dict[str, float]
    train_seconds: float | None


def read_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def rows_from_json(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, dict) and "results" in data:
        return list(data["results"])
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected result JSON schema: {path}")


def numeric_dict(d: dict[str, Any] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in (d or {}).items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)) and math.isfinite(float(v)):
            out[k] = float(v)
    return out


def canonical_model(experiment: str, source: str, raw_model: str) -> str:
    if experiment == "hmda_race":
        if raw_model == "direct_spec_boundary":
            return "repair_main05" if source == "repair_main05" else "repair_main0"
        if raw_model == "direct_spec_boundary_wrong_effect":
            return "wrong_spec"
        if raw_model == "proxy_score_only":
            return "score_only"
        if raw_model == "direct_spec_full":
            return "repair_full"
        return raw_model
    if experiment == "adult_gender":
        if raw_model == "direct_spec_boundary":
            return "repair_direct"
        if raw_model == "direct_spec_boundary_wrong_effect":
            return "wrong_spec"
        if raw_model == "proxy_score_only":
            return "score_only"
        return raw_model
    if experiment == "acs_age":
        if raw_model == "direct_spec_boundary":
            return "repair_direct"
        if raw_model == "direct_spec_boundary_wrong_effect":
            return "wrong_spec"
        if raw_model == "proxy_score_only":
            return "score_only"
        return raw_model
    return raw_model


def add_rows(
    rows: list[Row],
    *,
    path: Path,
    experiment: str,
    dataset: str,
    state: str,
    seed: int,
    source: str,
) -> None:
    for raw in rows_from_json(path):
        raw_model = str(raw.get("model", "unknown"))
        best = raw.get("best", {}) or {}
        model = canonical_model(experiment, source, raw_model)
        rows.append(
            Row(
                experiment=experiment,
                dataset=dataset,
                state=state,
                seed=seed,
                source=source,
                model=model,
                raw_model=raw_model,
                label=str(raw.get("label", model)),
                selector=str(raw.get("effective_selector", "")),
                source_path=str(path),
                test_behavior=numeric_dict(raw.get("test_behavior")),
                test_mechanism=numeric_dict(raw.get("test_mechanism")),
                val_behavior=numeric_dict(best.get("val_behavior")),
                val_mechanism=numeric_dict(best.get("val_mechanism")),
                train_seconds=(
                    float(raw["train_seconds"])
                    if isinstance(raw.get("train_seconds"), (int, float))
                    else None
                ),
            )
        )


def add_rows_if_exists(
    rows: list[Row],
    *,
    path: Path,
    experiment: str,
    dataset: str,
    state: str,
    seed: int,
    source: str,
) -> None:
    if path.exists():
        add_rows(
            rows,
            path=path,
            experiment=experiment,
            dataset=dataset,
            state=state,
            seed=seed,
            source=source,
        )


def collect_rows(root: Path) -> list[Row]:
    rows: list[Row] = []
    for state in ["md", "va", "pa"]:
        for seed in SEEDS:
            add_rows(
                rows,
                path=root
                / f"hmda_{state}"
                / "main0_with_baselines"
                / f"seed_{seed}"
                / "hmda"
                / "all_results.json",
                experiment="hmda_race",
                dataset="hmda",
                state=state.upper(),
                seed=seed,
                source="main0_with_baselines",
            )
            add_rows(
                rows,
                path=root
                / f"hmda_{state}"
                / "repair_main05"
                / f"seed_{seed}"
                / "hmda"
                / "all_results.json",
                experiment="hmda_race",
                dataset="hmda",
                state=state.upper(),
                seed=seed,
                source="repair_main05",
            )
            add_rows_if_exists(
                rows,
                path=root
                / f"hmda_{state}"
                / "no_interaction"
                / f"seed_{seed}"
                / "hmda"
                / "all_results.json",
                experiment="hmda_race",
                dataset="hmda",
                state=state.upper(),
                seed=seed,
                source="no_interaction",
            )

    for seed in SEEDS:
        add_rows(
            rows,
            path=root / "hmda_oh_ladder" / f"seed_{seed}" / "hmda" / "all_results.json",
            experiment="hmda_race",
            dataset="hmda",
            state="OH",
            seed=seed,
            source="oh_ladder",
        )
        add_rows(
            rows,
            path=root
            / "hmda_oh"
            / "repair_main05"
            / f"seed_{seed}"
            / "hmda"
            / "all_results.json",
            experiment="hmda_race",
            dataset="hmda",
            state="OH",
            seed=seed,
            source="repair_main05",
        )
        add_rows_if_exists(
            rows,
            path=root / "hmda_oh" / "no_interaction" / f"seed_{seed}" / "hmda" / "all_results.json",
            experiment="hmda_race",
            dataset="hmda",
            state="OH",
            seed=seed,
            source="no_interaction",
        )

        add_rows(
            rows,
            path=root / "adult_gender" / f"seed_{seed}" / "adult" / "all_results.json",
            experiment="adult_gender",
            dataset="adult",
            state="-",
            seed=seed,
            source="adult_gender",
        )
        add_rows_if_exists(
            rows,
            path=root / "adult_gender" / "no_interaction" / f"seed_{seed}" / "adult" / "all_results.json",
            experiment="adult_gender",
            dataset="adult",
            state="-",
            seed=seed,
            source="no_interaction",
        )
        add_rows(
            rows,
            path=root
            / "acs_age"
            / f"seed_{seed}"
            / "acs_employment_md"
            / "all_results.json",
            experiment="acs_age",
            dataset="acs_employment",
            state="MD",
            seed=seed,
            source="acs_age",
        )
        add_rows_if_exists(
            rows,
            path=root
            / "acs_age"
            / "no_interaction"
            / f"seed_{seed}"
            / "acs_employment_md"
            / "all_results.json",
            experiment="acs_age",
            dataset="acs_employment",
            state="MD",
            seed=seed,
            source="no_interaction",
        )
        add_rows(
            rows,
            path=root
            / "acs_intersectional_age_race"
            / f"seed_{seed}"
            / "results.json",
            experiment="acs_intersectional_age_race",
            dataset="acs_employment",
            state="MD",
            seed=seed,
            source="acs_intersectional_age_race",
        )
    return rows


def collect_fairsmote_rows(root: Path) -> list[Row]:
    """Collect Fair-SMOTE rows for the paired-bias experiments."""

    rows: list[Row] = []
    for state in ["md", "va", "pa", "oh"]:
        for seed in SEEDS:
            add_rows(
                rows,
                path=root
                / f"hmda_{state}"
                / f"seed_{seed}"
                / "hmda"
                / "all_results.json",
                experiment="hmda_race",
                dataset="hmda",
                state=state.upper(),
                seed=seed,
                source="fairsmote",
            )

    for seed in SEEDS:
        add_rows(
            rows,
            path=root
            / "adult_gender"
            / f"seed_{seed}"
            / "adult"
            / "all_results.json",
            experiment="adult_gender",
            dataset="adult",
            state="-",
            seed=seed,
            source="fairsmote",
        )
        add_rows(
            rows,
            path=root
            / "acs_age"
            / f"seed_{seed}"
            / "acs_employment_md"
            / "all_results.json",
            experiment="acs_age",
            dataset="acs_employment",
            state="MD",
            seed=seed,
            source="fairsmote",
        )
    return rows


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def metric_direction(metric: str) -> str:
    return "higher" if metric in HIGHER_IS_BETTER else "lower"


def flatten_long(rows: list[Row]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        base = {
            "experiment": row.experiment,
            "dataset": row.dataset,
            "state": row.state,
            "seed": row.seed,
            "source": row.source,
            "model": row.model,
            "raw_model": row.raw_model,
            "label": row.label,
            "selector": row.selector,
        }
        for split, group, metrics in [
            ("test", "behavior", row.test_behavior),
            ("test", "mechanism", row.test_mechanism),
            ("validation", "behavior", row.val_behavior),
            ("validation", "mechanism", row.val_mechanism),
        ]:
            for metric, value in metrics.items():
                out.append(
                    {
                        **base,
                        "split": split,
                        "metric_group": group,
                        "metric": metric,
                        "value": value,
                        "direction": metric_direction(metric),
                    }
                )
        if row.train_seconds is not None:
            out.append(
                {
                    **base,
                    "split": "train",
                    "metric_group": "runtime",
                    "metric": "train_seconds",
                    "value": row.train_seconds,
                    "direction": "lower",
                }
            )
    return out


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    if len(values) == 1:
        return (values[0], 0.0)
    return (mean(values), stdev(values))


def summarize(rows: list[Row]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        for group, metrics in [
            ("behavior", row.test_behavior),
            ("mechanism", row.test_mechanism),
        ]:
            for metric, value in metrics.items():
                buckets[
                    (row.experiment, row.dataset, row.state, row.model, group, metric)
                ].append(value)
    out = []
    for key, values in sorted(buckets.items()):
        m, s = mean_std(values)
        out.append(
            {
                "experiment": key[0],
                "dataset": key[1],
                "state": key[2],
                "model": key[3],
                "metric_group": key[4],
                "metric": key[5],
                "n": len(values),
                "mean": m,
                "std": s,
                "direction": metric_direction(key[5]),
            }
        )
    return out


def utility_floor_audit(rows: list[Row]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        floor = UTILITY_FLOORS[row.experiment]
        val_auc = row.val_behavior.get("auc", float("nan"))
        test_auc = row.test_behavior.get("auc", float("nan"))
        out.append(
            {
                "experiment": row.experiment,
                "dataset": row.dataset,
                "state": row.state,
                "seed": row.seed,
                "source": row.source,
                "model": row.model,
                "selector": row.selector,
                "val_auc": val_auc,
                "test_auc": test_auc,
                "floor": floor,
                "pass": bool(math.isfinite(val_auc) and val_auc >= floor),
            }
        )
    return out


def cliff_delta(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    gt = lt = 0
    for x in a:
        for y in b:
            if x > y:
                gt += 1
            elif x < y:
                lt += 1
    return (gt - lt) / (len(a) * len(b))


def fast_mean(values: list[float]) -> float:
    return sum(values) / len(values)


def bootstrap_p(a: list[float], b: list[float], rng: random.Random, reps: int = 500) -> float:
    if not a or not b:
        return 1.0
    le = ge = 0
    for _ in range(reps):
        aa = [rng.choice(a) for _ in a]
        bb = [rng.choice(b) for _ in b]
        d = fast_mean(aa) - fast_mean(bb)
        if d <= 0:
            le += 1
        if d >= 0:
            ge += 1
    return min(1.0, 2.0 * min(le / reps, ge / reps))


def sk_groups_for_metric(
    model_values: dict[str, list[float]], *, higher_better: bool, rng: random.Random
) -> dict[str, int]:
    scored = {
        model: ([v if higher_better else -v for v in values])
        for model, values in model_values.items()
        if values
    }
    ordered = sorted(scored, key=lambda m: mean(scored[m]), reverse=True)
    groups: dict[str, int] = {}

    def recurse(models: list[str], rank: int) -> int:
        if len(models) <= 1:
            for m in models:
                groups[m] = rank
            return rank + 1

        all_values = [v for m in models for v in scored[m]]
        grand = fast_mean(all_values)
        best_i = None
        best_ss = -1.0
        for i in range(1, len(models)):
            left = [v for m in models[:i] for v in scored[m]]
            right = [v for m in models[i:] for v in scored[m]]
            ss = len(left) * (fast_mean(left) - grand) ** 2 + len(right) * (fast_mean(right) - grand) ** 2
            if ss > best_ss:
                best_ss = ss
                best_i = i

        if best_i is None:
            for m in models:
                groups[m] = rank
            return rank + 1

        left_models = models[:best_i]
        right_models = models[best_i:]
        left = [v for m in left_models for v in scored[m]]
        right = [v for m in right_models for v in scored[m]]
        delta = abs(cliff_delta(left, right))
        p = bootstrap_p(left, right, rng)
        if p < 0.05 and delta >= 0.147:
            next_rank = recurse(left_models, rank)
            return recurse(right_models, next_rank)
        for m in models:
            groups[m] = rank
        return rank + 1

    recurse(ordered, 1)
    return groups


def scott_knott(rows: list[Row]) -> list[dict[str, Any]]:
    rng = random.Random(20260627)
    values: dict[tuple[str, str, str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    primary_metrics = set(PRIMARY_BEHAVIOR["single"]) | set(PRIMARY_MECHANISM["single"])
    primary_metrics |= set(PRIMARY_BEHAVIOR["intersectional"]) | set(
        PRIMARY_MECHANISM["intersectional"]
    )
    for row in rows:
        for metric, value in {**row.test_behavior, **row.test_mechanism}.items():
            if metric in primary_metrics:
                if is_degenerate_blind_direct_metric(row.experiment, row.model, metric):
                    continue
                values[(row.experiment, row.dataset, row.state, metric)][row.model].append(
                    value
                )

    out = []
    for (experiment, dataset, state, metric), model_values in sorted(values.items()):
        groups = sk_groups_for_metric(
            model_values,
            higher_better=(metric in HIGHER_IS_BETTER),
            rng=rng,
        )
        for model, vals in sorted(model_values.items(), key=lambda kv: groups[kv[0]]):
            m, s = mean_std(vals)
            out.append(
                {
                    "experiment": experiment,
                    "dataset": dataset,
                    "state": state,
                    "metric": metric,
                    "direction": metric_direction(metric),
                    "model": model,
                    "n": len(vals),
                    "mean": m,
                    "std": s,
                    "sk_group": groups[model],
                }
            )
    return out


def primary_summary(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = set(PRIMARY_BEHAVIOR["single"]) | set(PRIMARY_BEHAVIOR["intersectional"])
    allowed |= set(PRIMARY_MECHANISM["single"]) | set(PRIMARY_MECHANISM["intersectional"])
    return [r for r in summary_rows if r["metric"] in allowed]


def fmt(x: Any) -> str:
    if isinstance(x, float):
        if math.isnan(x):
            return "nan"
        return f"{x:.4f}"
    return str(x)


def write_report(
    path: Path,
    rows: list[Row],
    floor_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    sk_rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    failed = [r for r in floor_rows if not r["pass"]]
    by_experiment: dict[str, int] = defaultdict(int)
    for row in rows:
        by_experiment[row.experiment] += 1

    report: list[str] = []
    report.append("# Phase 4 Confirmatory Aggregation Report\n")
    report.append("## Inventory\n")
    report.append(f"- Model rows aggregated: `{len(rows)}`.")
    report.append(f"- Test/validation metric rows emitted: see `confirmatory_long_metrics.csv`.")
    for exp, n in sorted(by_experiment.items()):
        report.append(f"- `{exp}`: `{n}` rows.")
    report.append("")
    report.append("## Utility-Floor Audit\n")
    if failed:
        report.append(f"`{len(failed)}` selected rows failed their declared validation AUC floor.")
        report.append("")
        report.append("| Experiment | State | Seed | Model | Val AUC | Floor |")
        report.append("|---|---:|---:|---|---:|---:|")
        for r in failed[:40]:
            report.append(
                f"| {r['experiment']} | {r['state']} | {r['seed']} | {r['model']} | {fmt(r['val_auc'])} | {fmt(r['floor'])} |"
            )
        if len(failed) > 40:
            report.append(f"| ... | ... | ... | ... | `{len(failed) - 40}` more | ... |")
    else:
        report.append("All selected rows cleared their declared validation AUC floors.")
    report.append("")

    report.append("## Primary Behavior Summaries\n")
    for experiment, state in sorted({(r.experiment, r.state) for r in rows}):
        metrics = (
            PRIMARY_BEHAVIOR["intersectional"]
            if experiment == "acs_intersectional_age_race"
            else PRIMARY_BEHAVIOR["single"]
        )
        models = sorted(
            {
                r["model"]
                for r in primary_rows
                if r["experiment"] == experiment
                and r["state"] == state
                and r["metric"] in metrics
            }
        )
        if not models:
            continue
        report.append(f"### {experiment} {state}\n")
        shown_metrics = metrics[:6]
        report.append("| Model | " + " | ".join(shown_metrics) + " |")
        report.append("|---" + "|---:" * len(shown_metrics) + "|")
        lookup = {
            (r["experiment"], r["state"], r["model"], r["metric"]): r
            for r in primary_rows
        }
        for model in models:
            vals = []
            for metric in shown_metrics:
                r = lookup.get((experiment, state, model, metric))
                vals.append("" if r is None else f"{fmt(r['mean'])} +/- {fmt(r['std'])}")
            report.append(f"| {model} | " + " | ".join(vals) + " |")
        report.append("")

    report.append("## Files\n")
    report.append("- `confirmatory_long_metrics.csv`: one row per metric/model/seed/split.")
    report.append("- `confirmatory_summary_all_metrics.csv`: mean/std for every test metric.")
    report.append("- `confirmatory_primary_summary.csv`: behavior and mechanism metrics used in the submission.")
    report.append("- `utility_floor_audit.csv`: validation AUC floor check.")
    report.append(
        "- `scott_knott_esd_groups.csv`: statistical grouping over primary metrics using the standard CRAN `ScottKnottESD` implementation."
    )
    report.append("- `SCOTT_KNOTT_ESD_VALIDATION_REPORT.md`: R/package version and validation notes.")
    report.append("- `scott_knott_esd_exclusions.csv`: rows intentionally excluded from official grouping.")
    report.append("- `scott_knott_groups.csv`: lightweight in-repo diagnostic grouping.")
    report.append("")
    report.append("## Notes\n")
    report.append(
        "Use `scott_knott_esd_groups.csv` for paper tables after running "
        "`phase4_scottknott_esd_validate.R`. The older `scott_knott_groups.csv` "
        "file is produced by a lightweight in-repo implementation and is retained only "
        "as a diagnostic ledger."
    )
    report.append(
        "\nFor direct protected-attribute mechanism metrics (`main_*`, `cf_*`, and "
        "`pair_abs_*`), the protected-attribute-removed `blind` row is excluded from "
        "Scott-Knott grouping because its protected-main/pair residual is zero by "
        "construction. The row remains included for behavior metrics and proxy/group-"
        "conditioned mechanism diagnostics."
    )
    path.write_text("\n".join(report) + "\n")


def write_manifest(path: Path, args: argparse.Namespace, rows: list[Row]) -> None:
    experiments = sorted({r.experiment for r in rows})
    report_count = sum(1 for _ in args.root.rglob("*report.md")) + sum(
        1 for _ in args.root.rglob("ACS_INTERSECTIONAL_PHASE3_REPORT.md")
    )
    json_count = sum(1 for _ in args.root.rglob("all_results.json")) + sum(
        1 for _ in args.root.rglob("results.json")
    )
    checkpoint_count = sum(1 for _ in args.root.rglob("*.pt"))
    text = f"""# Paper Artifact Final Manifest

Generated by `scripts/phase4_confirmatory_aggregate.py`.

## Source

- Raw result root: `{args.root}`
- Fair-SMOTE result root: `{args.fairsmote_root if args.fairsmote_root else 'not included'}`
- Output root: `{args.output}`
- Experiments: `{', '.join(experiments)}`

## Inventory

- Aggregated selected model rows: `{len(rows)}`
- Result JSON files under raw root: `{json_count}`
- Markdown reports under raw root: `{report_count}`
- Selected checkpoint files under raw root: `{checkpoint_count}`

## Protocol Summary

- Confirmatory seeds: `0..9`.
- Max epochs / patience: `100/12`.
- Batch size / anchor batch size: `512/512`.
- Optimizer: AdamW, learning rate `7e-4`, weight decay `1e-4`.
- HMDA repair variants: `repair_main0` and `repair_main05`, both with `boundary_band=0.10`.
- Adult repair: `repair_direct`.
- ACS age repairs: `proxy_exhaustive` and `repair_direct`.
- ACS intersectional repairs/controls: `r1_joint_marginal`, `r3_intersectional`, `r4_r1plus`, `no_effect`, `wrong_d3`.
- Baseline checkpoint selection: utility-only for ERM/blind/reweight/adversarial.
- Interaction repair selection: utility guard plus intended mechanism residual.
- Wrong controls: bounded wrong-target objective plus utility guard.

## Submission Outputs

- `results/main/CONFIRMATORY_REPORT.md`
- `phase4/confirmatory_long_metrics.csv`
- `phase4/confirmatory_summary_all_metrics.csv`
- `phase4/confirmatory_primary_summary.csv`
- `phase4/utility_floor_audit.csv`
- `phase4/scott_knott_esd_groups.csv` (standard `ScottKnottESD` grouping)
- `phase4/SCOTT_KNOTT_ESD_VALIDATION_REPORT.md`
- `phase4/scott_knott_esd_exclusions.csv`
- `phase4/scott_knott_esd_comparison.csv`
- `phase4/scott_knott_groups.csv` (lightweight diagnostic grouping; not the submission statistical result)

## Scott-Knott Exclusion Rule

For direct protected-attribute mechanism metrics (`main_*`, `cf_*`, and
`pair_abs_*`), the protected-attribute-removed `blind` row is excluded from
Scott-Knott grouping because its protected-main/pair residual is zero by
construction. The row remains included for behavior metrics and proxy/group-
conditioned mechanism diagnostics.
"""
    path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(
            "runs/phase3_confirmatory_10seeds_v1"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/main"),
    )
    parser.add_argument(
        "--fairsmote-root",
        type=Path,
        default=None,
        help=(
            "Optional Fair-SMOTE result root. When provided, Fair-SMOTE "
            "rows are appended for HMDA MD/VA/PA/OH, Adult gender, and ACS age."
        ),
    )
    args = parser.parse_args()

    rows = collect_rows(args.root)
    if args.fairsmote_root is not None:
        rows.extend(collect_fairsmote_rows(args.fairsmote_root))
    args.output.mkdir(parents=True, exist_ok=True)

    long_rows = flatten_long(rows)
    write_csv(
        args.output / "confirmatory_long_metrics.csv",
        long_rows,
        [
            "experiment",
            "dataset",
            "state",
            "seed",
            "source",
            "model",
            "raw_model",
            "label",
            "selector",
            "split",
            "metric_group",
            "metric",
            "value",
            "direction",
        ],
    )

    summary_rows = summarize(rows)
    write_csv(
        args.output / "confirmatory_summary_all_metrics.csv",
        summary_rows,
        [
            "experiment",
            "dataset",
            "state",
            "model",
            "metric_group",
            "metric",
            "n",
            "mean",
            "std",
            "direction",
        ],
    )

    primary_rows = primary_summary(summary_rows)
    write_csv(
        args.output / "confirmatory_primary_summary.csv",
        primary_rows,
        [
            "experiment",
            "dataset",
            "state",
            "model",
            "metric_group",
            "metric",
            "n",
            "mean",
            "std",
            "direction",
        ],
    )

    floor_rows = utility_floor_audit(rows)
    write_csv(
        args.output / "utility_floor_audit.csv",
        floor_rows,
        [
            "experiment",
            "dataset",
            "state",
            "seed",
            "source",
            "model",
            "selector",
            "val_auc",
            "test_auc",
            "floor",
            "pass",
        ],
    )

    sk_rows = scott_knott(rows)
    write_csv(
        args.output / "scott_knott_groups.csv",
        sk_rows,
        [
            "experiment",
            "dataset",
            "state",
            "metric",
            "direction",
            "model",
            "n",
            "mean",
            "std",
            "sk_group",
        ],
    )

    write_report(
        args.output / "CONFIRMATORY_REPORT.md",
        rows,
        floor_rows,
        primary_rows,
        sk_rows,
    )
    write_manifest(args.output.parent / "MANIFEST.md", args, rows)


if __name__ == "__main__":
    main()
