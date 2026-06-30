#!/usr/bin/env python3
"""Create the paper-facing four-panel interaction-localization figure.

The figure merges frozen Phase-4 long metrics with the add-on Fair-SMOTE
results, then plots held-out per-feature direct interaction residuals.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SEEDS = list(range(10))

MODEL_ORDER = ["erm", "fairsmote", "score_only", "no_interaction", "steering"]
MODEL_LABELS = {
    "erm": "ERM",
    "fairsmote": "Fair-SMOTE",
    "score_only": "Score-gap",
    "no_interaction": "No-interaction",
    "steering": "Interaction\nsteering",
}

HMDA_FEATURES = [
    "loan_to_value_ratio",
    "debt_to_income_ratio",
    "loan_amount",
    "property_value",
    "income",
    "tract_minority_population_percent",
    "tract_to_msa_income_percentage",
]

FEATURE_LABELS = {
    "SCHL": "Schooling",
    "age": "Age",
    "any_disability": "Any disability",
    "cognitive_disability": "Cognitive disability",
    "debt_to_income_ratio": "DTI",
    "education_num": "Education",
    "female": "Sex",
    "hours_per_week": "Hours/week",
    "income": "Income",
    "loan_amount": "Loan amt.",
    "loan_to_value_ratio": "LTV",
    "marital_married": "Married",
    "native_us": "Native-born",
    "occupation_exec_prof": "Exec/prof occ.",
    "property_value": "Property value",
    "race_white": "White",
    "recent_mover": "Recent mover",
    "relationship_own_child": "Own child",
    "relationship_spouse": "Spouse",
    "relp_child": "Child in household",
    "relp_householder": "Householder",
    "tract_minority_population_percent": "Tract minority %",
    "tract_to_msa_income_percentage": "Tract/MSA income",
}


@dataclass(frozen=True)
class Panel:
    key: str
    title: str
    experiment: str
    dataset: str
    state: str
    steering_model: str
    fairsmote_root: str
    fairsmote_inner: str
    feature_mode: str
    n_features: int = 7


PANELS = [
    Panel(
        key="hmda_pa",
        title="HMDA-PA Race",
        experiment="hmda_race",
        dataset="hmda",
        state="PA",
        steering_model="repair_main05",
        fairsmote_root="hmda_pa",
        fairsmote_inner="hmda",
        feature_mode="hmda_fixed",
    ),
    Panel(
        key="hmda_oh",
        title="HMDA-OH Race",
        experiment="hmda_race",
        dataset="hmda",
        state="OH",
        steering_model="repair_main05",
        fairsmote_root="hmda_oh",
        fairsmote_inner="hmda",
        feature_mode="hmda_fixed",
    ),
    Panel(
        key="adult_gender",
        title="Adult Gender",
        experiment="adult_gender",
        dataset="adult",
        state="-",
        steering_model="repair_direct",
        fairsmote_root="adult_gender",
        fairsmote_inner="adult",
        feature_mode="top_erm",
    ),
    Panel(
        key="acs_age",
        title="ACS Employment Age",
        experiment="acs_age",
        dataset="acs_employment",
        state="MD",
        steering_model="repair_direct",
        fairsmote_root="acs_age",
        fairsmote_inner="acs_employment_md",
        feature_mode="top_erm",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase4-long",
        default="results/main/confirmatory_long_metrics.csv.gz",
        help="Frozen Phase-4 long metric CSV.",
    )
    parser.add_argument(
        "--fairsmote-root",
        default="runs/fairsmote/results_full_de_v1",
        help="Fair-SMOTE 10-seed result root.",
    )
    parser.add_argument(
        "--output-dir",
        default="runs/localization",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Metric split to plot.",
    )
    parser.add_argument(
        "--metric-prefix",
        default="pair_abs_mean__",
        help="Per-feature mechanism metric prefix.",
    )
    parser.add_argument(
        "--color-cap",
        type=float,
        default=0.0,
        help="Heatmap color cap. Use 0 to set it from the selected ERM maxima.",
    )
    return parser.parse_args()


def feature_label(feature: str) -> str:
    if feature in FEATURE_LABELS:
        return FEATURE_LABELS[feature]
    label = re.sub(r"[_]+", " ", feature).strip()
    return label[:1].upper() + label[1:]


def canonical_phase4_rows(df: pd.DataFrame, panel: Panel, split: str, metric_prefix: str) -> pd.DataFrame:
    models = {
        "erm": "erm",
        "score_only": "score_only",
        "no_interaction": "no_interaction",
        panel.steering_model: "steering",
    }
    sub = df[
        (df["experiment"] == panel.experiment)
        & (df["dataset"] == panel.dataset)
        & (df["state"].astype(str) == panel.state)
        & (df["split"] == split)
        & (df["metric_group"] == "mechanism")
        & (df["metric"].astype(str).str.startswith(metric_prefix))
        & (df["model"].isin(models))
    ].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["model_canonical"] = sub["model"].map(models)
    sub["feature"] = sub["metric"].str.split("__", n=1).str[1]
    sub["value"] = sub["value"].astype(float)
    return sub[
        [
            "experiment",
            "dataset",
            "state",
            "seed",
            "model_canonical",
            "feature",
            "metric",
            "value",
        ]
    ].rename(columns={"model_canonical": "model"})


def fairsmote_rows(
    fairsmote_root: Path,
    panel: Panel,
    metric_prefix: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in SEEDS:
        path = (
            fairsmote_root
            / panel.fairsmote_root
            / f"seed_{seed}"
            / panel.fairsmote_inner
            / f"seed_{seed}"
            / "fairsmote.json"
        )
        if not path.exists():
            raise FileNotFoundError(f"Missing Fair-SMOTE artifact: {path}")
        with path.open() as f:
            data = json.load(f)
        mechanism = data.get("test_mechanism", {})
        for metric, value in mechanism.items():
            if metric.startswith(metric_prefix) and isinstance(value, (int, float)) and math.isfinite(float(value)):
                rows.append(
                    {
                        "experiment": panel.experiment,
                        "dataset": panel.dataset,
                        "state": panel.state,
                        "seed": seed,
                        "model": "fairsmote",
                        "feature": metric.split("__", 1)[1],
                        "metric": metric,
                        "value": float(value),
                    }
                )
    return pd.DataFrame(rows)


def select_features(panel: Panel, rows: pd.DataFrame) -> list[str]:
    if panel.feature_mode == "hmda_fixed":
        return HMDA_FEATURES
    erm = rows[(rows["model"] == "erm")]
    if erm.empty:
        raise ValueError(f"No ERM rows for feature selection in panel {panel.key}")
    ranked = (
        erm.groupby("feature", as_index=False)["value"]
        .mean()
        .sort_values(["value", "feature"], ascending=[False, True])
    )
    return ranked["feature"].head(panel.n_features).tolist()


def summarize_panel(panel: Panel, rows: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    filtered = rows[rows["feature"].isin(features)].copy()
    filtered["panel"] = panel.key
    filtered["panel_title"] = panel.title
    filtered["model_label"] = filtered["model"].map(MODEL_LABELS)
    filtered["feature_label"] = filtered["feature"].map(feature_label)
    filtered["feature_order"] = filtered["feature"].map({f: i for i, f in enumerate(features)})
    filtered["model_order"] = filtered["model"].map({m: i for i, m in enumerate(MODEL_ORDER)})
    filtered = filtered.sort_values(["feature_order", "model_order", "seed"])

    summary = (
        filtered.groupby(
            [
                "panel",
                "panel_title",
                "experiment",
                "dataset",
                "state",
                "model",
                "model_label",
                "model_order",
                "feature",
                "feature_label",
                "feature_order",
            ],
            as_index=False,
        )
        .agg(mean=("value", "mean"), std=("value", "std"), n=("value", "count"))
        .sort_values(["panel", "feature_order", "model_order"])
    )
    return filtered, summary


def draw_panel(ax: plt.Axes, summary: pd.DataFrame, panel: Panel, color_cap: float, cmap: str) -> None:
    table = summary[summary["panel"] == panel.key].copy()
    pivot = (
        table.pivot(index="feature_label", columns="model_label", values="mean")
        .reindex(table.sort_values("feature_order")["feature_label"].drop_duplicates().tolist())
        .reindex([MODEL_LABELS[m] for m in MODEL_ORDER], axis=1)
    )
    data = pivot.to_numpy(dtype=float)
    shown = np.clip(data, 0, color_cap)
    ax.imshow(shown, cmap=cmap, vmin=0, vmax=color_cap, aspect="auto")

    ax.set_title(panel.title, fontsize=10.2, pad=8)
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, rotation=32, ha="right", fontsize=8.2)
    ax.set_yticklabels(pivot.index, fontsize=8.2)
    ax.set_xticks(np.arange(len(pivot.columns) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(pivot.index) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linewidth=0.95)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    cm = plt.get_cmap(cmap)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            if not np.isfinite(value):
                continue
            normed = min(max(value, 0), color_cap) / color_cap if color_cap > 0 else 0
            rgba = cm(normed)
            luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
            text_color = "white" if luminance < 0.46 else "#202020"
            label = f"{value:.3f}" if 0 < value < 0.01 else f"{value:.2f}"
            ax.text(j, i, label, ha="center", va="center", fontsize=6.7, color=text_color)


def write_report(
    output_dir: Path,
    summary: pd.DataFrame,
    feature_rows: list[dict[str, object]],
    color_cap: float,
) -> None:
    lines: list[str] = []
    lines.append("# Four-Panel Feature Localization Report")
    lines.append("")
    lines.append("This artifact plots held-out per-feature direct interaction residuals (`pair_abs_mean__FEATURE`).")
    lines.append("Rows are averaged over ten seeds. Color is clipped at the reported cap; printed values are unclipped.")
    lines.append("Cell labels use three decimals for nonzero values below `0.01` to avoid displaying strong repairs as `0.00`.")
    lines.append("")
    lines.append(f"- Color cap: `{color_cap:.3f}`")
    lines.append("- Model columns: ERM, Fair-SMOTE, Score-gap, No-interaction, Interaction steering.")
    lines.append("- HMDA uses the fixed underwriting feature list; Adult and ACS use the largest ERM residual features, frozen before model comparison.")
    lines.append("")
    lines.append("## Feature Sets")
    lines.append("")
    for row in feature_rows:
        labels = ", ".join(str(x) for x in row["feature_labels"])
        lines.append(f"- **{row['panel_title']}**: {labels}")
    lines.append("")
    lines.append("## Headline Pattern")
    lines.append("")
    for panel in PANELS:
        sub = summary[summary["panel"] == panel.key]
        by_model = sub.groupby(["model", "model_label"], as_index=False)["mean"].mean()
        by_model = by_model.sort_values("mean")
        best = by_model.iloc[0]
        erm = float(by_model[by_model["model"] == "erm"]["mean"].iloc[0])
        fair = float(by_model[by_model["model"] == "fairsmote"]["mean"].iloc[0])
        steering = float(by_model[by_model["model"] == "steering"]["mean"].iloc[0])
        lines.append(
            f"- **{panel.title}**: average selected-feature residual is "
            f"`{steering:.3f}` for interaction steering, `{erm:.3f}` for ERM, "
            f"and `{fair:.3f}` for Fair-SMOTE; lowest row is "
            f"`{str(best['model_label']).replace(chr(10), ' ')}`."
        )
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `localization_four_panel.pdf`")
    lines.append("- `localization_four_panel.png`")
    lines.append("- `localization_four_panel.csv`")
    lines.append("- `localization_four_panel_seed_values.csv`")
    (output_dir / "LOCALIZATION_FOUR_PANEL_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    phase4 = pd.read_csv(args.phase4_long)
    fairsmote_root = Path(args.fairsmote_root)

    seed_tables: list[pd.DataFrame] = []
    summary_tables: list[pd.DataFrame] = []
    feature_rows: list[dict[str, object]] = []

    for panel in PANELS:
        core = canonical_phase4_rows(phase4, panel, args.split, args.metric_prefix)
        fair = fairsmote_rows(fairsmote_root, panel, args.metric_prefix)
        rows = pd.concat([core, fair], ignore_index=True)
        features = select_features(panel, rows)
        missing = sorted(set(MODEL_ORDER) - set(rows["model"].unique()))
        if missing:
            raise ValueError(f"Missing models for {panel.key}: {missing}")
        seed_table, summary = summarize_panel(panel, rows, features)
        seed_tables.append(seed_table)
        summary_tables.append(summary)
        feature_rows.append(
            {
                "panel": panel.key,
                "panel_title": panel.title,
                "features": features,
                "feature_labels": [feature_label(f) for f in features],
            }
        )

    seed_values = pd.concat(seed_tables, ignore_index=True)
    summary = pd.concat(summary_tables, ignore_index=True)

    seed_values.to_csv(output_dir / "localization_four_panel_seed_values.csv", index=False)
    summary.to_csv(output_dir / "localization_four_panel.csv", index=False)

    if args.color_cap > 0:
        color_cap = args.color_cap
    else:
        erm_max = summary[summary["model"] == "erm"]["mean"].max()
        color_cap = float(math.ceil(float(erm_max) * 20) / 20)

    cmap = "YlOrRd"
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 6.65), constrained_layout=True)
    for ax, panel in zip(axes.ravel(), PANELS):
        draw_panel(ax, summary, panel, color_cap, cmap)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=color_cap))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes.ravel().tolist(), fraction=0.024, pad=0.012)
    cbar.set_label(f"Direct interaction residual\ncolor clipped at {color_cap:.2f}", fontsize=8.5)
    cbar.ax.tick_params(labelsize=8)

    fig.suptitle("Per-feature interaction residuals localize fairness bugs", fontsize=12.5, y=1.018)
    fig.savefig(output_dir / "localization_four_panel.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / "localization_four_panel.pdf", bbox_inches="tight")
    plt.close(fig)

    write_report(output_dir, summary, feature_rows, color_cap)

    print(f"Wrote {output_dir / 'localization_four_panel.pdf'}")
    print(f"Wrote {output_dir / 'localization_four_panel.png'}")
    print(f"Wrote {output_dir / 'localization_four_panel.csv'}")
    print(f"Wrote {output_dir / 'LOCALIZATION_FOUR_PANEL_REPORT.md'}")


if __name__ == "__main__":
    main()
