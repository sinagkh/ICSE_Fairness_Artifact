#!/usr/bin/env python3
"""Build compact ladder artifacts for the fairness paper.

The compact ladders reuse the frozen 10-seed confirmatory artifacts and add the
missing score-guard-plus-global-interaction row produced under
additional_runs/ladders.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Iterable, List, Mapping, Tuple


ROOT = Path(".")
PHASE4 = ROOT / "results" / "main"
OUT = ROOT / "results" / "ladder"
BASE_LONG = PHASE4 / "confirmatory_long_metrics.csv"
GLOBAL_INTERACTION_ROOT = OUT / "score_guard_global_interaction_v1"


HIGHER_IS_BETTER = {"auc", "accuracy"}

SUMMARY_METRICS = [
    ("behavior", "auc", "AUC"),
    ("behavior", "accuracy", "Acc"),
    ("behavior", "aod_gap", "AOD"),
    ("behavior", "eod_gap", "EOD"),
    ("behavior", "dp_gap", "DP"),
    ("behavior", "score_gap", "Sgap"),
    ("mechanism", "pair_abs_mean", "Delta2"),
    ("mechanism", "proxy_effect_gap_mean", "Proxy"),
    ("mechanism", "proxy_score_gap_cond_mean", "ProxyScore"),
    ("mechanism", "boundary_proxy_effect_gap_mean", "BoundaryProxy"),
]

COMPACT = {
    "adult_gender": {
        "dataset": "adult",
        "state": "-",
        "title": "Adult Gender",
        "csv": "adult_ladder_10seed.csv",
        "roles": [
            ("ERM", "erm"),
            ("Global score guard", "score_only"),
            ("Global + boundary score guards", "no_interaction"),
            ("Score guards + global interaction", "score_guard_global_interaction"),
            ("Final interaction steering", "repair_direct"),
            ("Wrong-spec", "wrong_spec"),
        ],
    },
    "acs_age": {
        "dataset": "acs_employment",
        "state": "MD",
        "title": "ACS Employment Age",
        "csv": "acs_age_ladder_10seed.csv",
        "roles": [
            ("ERM", "erm"),
            ("Global score guard", "score_only"),
            ("Global + boundary score guards", "no_interaction"),
            ("Score guards + global interaction", "score_guard_global_interaction"),
            ("Final interaction steering", "repair_direct"),
            ("Wrong-spec", "wrong_spec"),
        ],
    },
    "hmda_race": {
        "dataset": "hmda",
        "state": "OH",
        "title": "HMDA-OH Race",
        "csv": "hmda_oh_compact_ladder_10seed.csv",
        "roles": [
            ("ERM", "erm"),
            ("Global score guard", "score_only"),
            ("Global + boundary score guards", "no_interaction"),
            ("Score guards + global interaction", "score_guard_global_interaction"),
            ("Final interaction steering", "repair_main05"),
            ("Wrong-spec", "wrong_spec"),
        ],
    },
}


def direction_for(metric: str) -> str:
    return "higher" if metric in HIGHER_IS_BETTER else "lower"


def read_base_long() -> List[dict]:
    with BASE_LONG.open(newline="") as f:
        return list(csv.DictReader(f))


GLOBAL_ROW_SOURCES = {
    "adult_gender": {
        "dataset": "adult",
        "state": "-",
        "subdir": "adult_gender",
        "inner": "adult",
    },
    "acs_age": {
        "dataset": "acs_employment",
        "state": "MD",
        "subdir": "acs_age",
        "inner": "acs_employment_md",
    },
    "hmda_race": {
        "dataset": "hmda",
        "state": "OH",
        "subdir": "hmda_oh",
        "inner": "hmda",
    },
}


def score_guard_global_interaction_rows() -> List[dict]:
    rows: List[dict] = []
    for experiment, meta in GLOBAL_ROW_SOURCES.items():
        for seed in range(10):
            path = (
                GLOBAL_INTERACTION_ROOT
                / meta["subdir"]
                / f"seed_{seed}"
                / meta["inner"]
                / f"seed_{seed}"
                / "score_guard_global_interaction.json"
            )
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            selector = data.get("effective_selector", "")
            for group_name, metrics in [
                ("behavior", data.get("test_behavior", {})),
                ("mechanism", data.get("test_mechanism", {})),
            ]:
                for metric, value in metrics.items():
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        continue
                    if not math.isfinite(float(value)):
                        continue
                    rows.append(
                        {
                            "experiment": experiment,
                            "dataset": meta["dataset"],
                            "state": meta["state"],
                            "seed": str(seed),
                            "source": "score_guard_global_interaction_addon",
                            "model": "score_guard_global_interaction",
                            "raw_model": "score_guard_global_interaction",
                            "label": "Score guards + global interaction",
                            "selector": selector,
                            "split": "test",
                            "metric_group": group_name,
                            "metric": metric,
                            "value": str(float(value)),
                            "direction": direction_for(metric),
                        }
                    )
    return rows


def compact_long_rows(all_rows: Iterable[dict]) -> List[dict]:
    wanted = {
        (experiment, meta["state"], model): role
        for experiment, meta in COMPACT.items()
        for role, model in meta["roles"]
    }
    out: List[dict] = []
    for row in all_rows:
        if row.get("split") != "test":
            continue
        key = (row.get("experiment"), row.get("state"), row.get("model"))
        role = wanted.get(key)
        if role is None:
            continue
        new_row = dict(row)
        new_row["ladder_role"] = role
        out.append(new_row)
    return out


def row_index(long_rows: Iterable[dict]) -> Dict[Tuple[str, str, str, str, str], dict]:
    idx: Dict[Tuple[str, str, str, str, str], dict] = {}
    for row in long_rows:
        key = (
            row["experiment"],
            row["state"],
            row["seed"],
            row["model"],
            row["metric"],
        )
        idx[key] = row
    return idx


def build_dataset_rows(experiment: str, long_rows: List[dict]) -> List[dict]:
    meta = COMPACT[experiment]
    idx = row_index(long_rows)
    records: List[dict] = []
    for seed in range(10):
        for role, model in meta["roles"]:
            rec = {
                "experiment": experiment,
                "dataset": meta["dataset"],
                "state": meta["state"],
                "seed": seed,
                "role": role,
                "model": model,
            }
            for _group, metric, label in SUMMARY_METRICS:
                row = idx.get((experiment, meta["state"], str(seed), model, metric))
                rec[label] = float(row["value"]) if row is not None else ""
            records.append(rec)
    return records


def summarize(records: List[dict]) -> List[dict]:
    by_role: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    for rec in records:
        by_role[(rec["role"], rec["model"], rec["state"])].append(rec)
    out: List[dict] = []
    for (role, model, state), rows in by_role.items():
        summary = {"state": state, "role": role, "model": model, "n": len(rows)}
        for _group, _metric, label in SUMMARY_METRICS:
            vals = [float(r[label]) for r in rows if r[label] != ""]
            summary[f"{label}_mean"] = mean(vals) if vals else ""
            summary[f"{label}_std"] = stdev(vals) if len(vals) > 1 else 0.0 if vals else ""
        out.append(summary)
    role_order = {
        role: i
        for meta in COMPACT.values()
        for i, (role, _model) in enumerate(meta["roles"])
    }
    out.sort(key=lambda r: role_order.get(r["role"], 999))
    return out


def write_csv(path: Path, rows: List[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt_mean_std(row: Mapping[str, object], label: str) -> str:
    m = row.get(f"{label}_mean", "")
    s = row.get(f"{label}_std", "")
    if m == "":
        return "-"
    return f"{float(m):.4f} +/- {float(s):.4f}"


def write_audit(long_rows: List[dict], added_rows: List[dict]) -> None:
    lines = ["# Compact Ladder Row Audit\n"]
    lines.append("This audit checks row availability before building the compact ladder reports.\n")
    lines.append(f"- Base long-metrics source: `{BASE_LONG}`")
    lines.append(f"- Score-guard global-interaction row source: `{GLOBAL_INTERACTION_ROOT}`")
    lines.append(f"- Added score-guard global-interaction metric rows: `{len(added_rows)}`.\n")
    lines.append("| Dataset | Role | Model | Seeds present | Status |")
    lines.append("|---|---|---|---:|---|")
    seen = defaultdict(set)
    for row in long_rows:
        seen[(row["experiment"], row["state"], row["model"])].add(int(row["seed"]))
    for experiment, meta in COMPACT.items():
        for role, model in meta["roles"]:
            seeds = seen[(experiment, meta["state"], model)]
            status = "ok" if seeds == set(range(10)) else f"missing {sorted(set(range(10)) - seeds)}"
            lines.append(
                f"| {meta['title']} | {role} | `{model}` | {len(seeds)} | {status} |"
            )
    (OUT / "LADDER_ROW_AUDIT.md").write_text("\n".join(lines) + "\n")


def write_report(dataset_summaries: Mapping[str, List[dict]]) -> None:
    lines = ["# Compact Ladder 10-Seed Report\n"]
    lines.append(
        "The compact ladder isolates the contribution of the interaction rule: ERM, "
        "endpoint/guard controls, global interaction steering, the final interaction "
        "steering row used in the paper tables, and wrong-specification control.\n"
    )
    lines.append("Metrics are mean +/- std over 10 seeds. Lower is better except AUC/Acc.\n")
    for experiment, summary in dataset_summaries.items():
        meta = COMPACT[experiment]
        lines.append(f"## {meta['title']}\n")
        lines.append("| Role | Model | AUC | Acc | AOD | EOD | DP | Sgap | Delta2 | Proxy | BoundaryProxy |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in summary:
            lines.append(
                "| {role} | `{model}` | {auc} | {acc} | {aod} | {eod} | {dp} | {sgap} | {delta} | {proxy} | {boundary} |".format(
                    role=row["role"],
                    model=row["model"],
                    auc=fmt_mean_std(row, "AUC"),
                    acc=fmt_mean_std(row, "Acc"),
                    aod=fmt_mean_std(row, "AOD"),
                    eod=fmt_mean_std(row, "EOD"),
                    dp=fmt_mean_std(row, "DP"),
                    sgap=fmt_mean_std(row, "Sgap"),
                    delta=fmt_mean_std(row, "Delta2"),
                    proxy=fmt_mean_std(row, "Proxy"),
                    boundary=fmt_mean_std(row, "BoundaryProxy"),
                )
            )
        lines.append("")
        final = next(r for r in summary if r["role"] == "Final interaction steering")
        no_int = next(r for r in summary if r["role"] == "Global + boundary score guards")
        wrong = next(r for r in summary if r["role"] == "Wrong-spec")
        lines.append(
            "- Final vs no-interaction: "
            f"AOD {float(final['AOD_mean']):.4f} vs {float(no_int['AOD_mean']):.4f}, "
            f"Delta2 {float(final['Delta2_mean']):.4f} vs {float(no_int['Delta2_mean']):.4f}."
        )
        lines.append(
            "- Wrong-spec attribution: "
            f"AOD {float(wrong['AOD_mean']):.4f}, "
            f"Delta2 {float(wrong['Delta2_mean']):.4f}.\n"
        )
    lines.append("## Files\n")
    for experiment, meta in COMPACT.items():
        lines.append(f"- `{meta['csv']}`: per-seed compact ladder rows for {meta['title']}.")
        lines.append(f"- `{meta['csv'].replace('.csv', '_summary.csv')}`: mean/std summary.")
    lines.append("- `compact_ladder_long_metrics.csv`: long metrics table for ScottKnottESD.")
    lines.append("- `scott_knott_esd_groups.csv`: standard ScottKnottESD groups where generated.\n")
    (OUT / "LADDER_10SEED_REPORT.md").write_text("\n".join(lines))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    added_rows = score_guard_global_interaction_rows()
    all_rows = read_base_long() + added_rows
    long_rows = compact_long_rows(all_rows)
    write_audit(long_rows, added_rows)
    write_csv(OUT / "compact_ladder_long_metrics.csv", long_rows)

    summaries = {}
    for experiment, meta in COMPACT.items():
        records = build_dataset_rows(experiment, long_rows)
        summary = summarize(records)
        summaries[experiment] = summary
        write_csv(OUT / meta["csv"], records)
        write_csv(OUT / meta["csv"].replace(".csv", "_summary.csv"), summary)
    write_report(summaries)
    print(f"Wrote ladder artifacts to {OUT}")


if __name__ == "__main__":
    main()
