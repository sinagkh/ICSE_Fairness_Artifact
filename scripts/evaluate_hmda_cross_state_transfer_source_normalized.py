#!/usr/bin/env python3
"""Evaluate HMDA cross-state transfer with source-state preprocessing.

This is the stricter companion to `evaluate_hmda_cross_state_transfer.py`.
The target state still supplies the held-out applicants and labels, but the raw
target rows are transformed with the source state's preprocessing statistics and
source checkpoint schema before evaluation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

SCRIPT_DIR = Path(__file__).resolve().parent
import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_fairness_interactions as rfi
from evaluate_hmda_cross_state_transfer import (
    MODEL_VARIANTS,
    STATES,
    checkpoint_path,
    fmt,
    hmda_url,
    load_checkpoint_model,
    run_family,
    summarize,
    write_csv,
)


HMDA_USECOLS = [
    "derived_race",
    "derived_sex",
    "action_taken",
    "loan_type",
    "loan_purpose",
    "lien_status",
    "preapproval",
    "occupancy_type",
    "loan_amount",
    "loan_to_value_ratio",
    "property_value",
    "income",
    "debt_to_income_ratio",
    "applicant_age",
    "tract_minority_population_percent",
    "tract_to_msa_income_percentage",
    "ffiec_msa_md_median_family_income",
]


def make_data_args(template_args: dict[str, Any], state: str, output_dir: Path) -> argparse.Namespace:
    args = argparse.Namespace(**template_args)
    args.dataset = "hmda"
    args.hmda_path = Path(f"data/raw/hmda_2019_{state.lower()}.csv")
    args.hmda_url = hmda_url(state)
    args.prepared_cache_dir = output_dir / "_source_prepared_cache"
    args.output_dir = output_dir / "_unused"
    args.device = "cpu"
    args.torch_threads = 2
    return args


def load_target_raw(args: argparse.Namespace, target_state: str, seed: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    hmda_path = Path(f"data/raw/hmda_2019_{target_state.lower()}.csv")
    rfi.download_hmda(hmda_path, hmda_url(target_state))
    frame = pd.read_csv(hmda_path, usecols=HMDA_USECOLS, low_memory=False)
    frame = frame[
        frame["derived_race"].isin(["White", "Black or African American"])
        & frame["action_taken"].isin([1, 2, 3])
    ].reset_index(drop=True)
    if args.max_rows is not None:
        frame = frame.sample(n=min(args.max_rows, len(frame)), random_state=seed).reset_index(drop=True)
    y = frame["action_taken"].isin([1, 2]).to_numpy(dtype=np.float32)
    s = (frame["derived_race"] == "Black or African American").to_numpy(dtype=np.float32)
    rng = np.random.default_rng(seed)
    train_idx, val_idx, test_idx = rfi.stratified_indices(y, s, rng, args.val_frac, args.test_frac)
    return frame, y, s, train_idx, val_idx, test_idx


def _source_scale(stats: dict[str, Any]) -> float:
    scale = float(stats["q75"]) - float(stats["q25"])
    if scale < 1e-6:
        scale = float(stats["q90"]) - float(stats["q10"])
    if scale < 1e-6:
        scale = float(stats.get("max", 1.0)) - float(stats.get("min", 0.0))
    return max(scale, 1.0)


def transform_target_with_source_spec(
    source_data: rfi.PreparedData,
    target_frame: pd.DataFrame,
    y: np.ndarray,
    s: np.ndarray,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
) -> rfi.PreparedData:
    """Transform target raw rows using source-state preprocessing and schema."""
    source_spec = source_data.spec
    prep = source_spec.source_summary["preprocessing"]
    continuous_stats = prep["continuous"]
    values: dict[str, np.ndarray] = {source_spec.sensitive_column: s.astype(np.float32)}

    for col in source_spec.continuous_columns:
        raw = rfi.parse_dti_series(target_frame[col]) if col == "debt_to_income_ratio" else rfi.as_float_series(target_frame[col])
        stats = continuous_stats[col]
        median = float(stats["median"])
        scale = _source_scale(stats)
        filled = raw.fillna(median)
        values[f"{col}__z"] = ((filled - median) / scale).to_numpy(dtype=np.float32)
        values[f"{col}__missing"] = raw.isna().astype(np.float32).to_numpy()

    if source_spec.categorical_columns:
        cat = target_frame[source_spec.categorical_columns].copy()
        for col in source_spec.categorical_columns:
            cat[col] = cat[col].astype(str).str.strip().replace({"nan": "Missing", "NA": "Missing", "": "Missing"})
        dummies = pd.get_dummies(cat, prefix=source_spec.categorical_columns, dtype=np.float32)
    else:
        dummies = pd.DataFrame(index=target_frame.index)

    x = np.zeros((len(target_frame), len(source_spec.input_columns)), dtype=np.float32)
    missing_columns: list[str] = []
    for idx, name in enumerate(source_spec.input_columns):
        if name in values:
            x[:, idx] = values[name]
        elif name in dummies.columns:
            x[:, idx] = dummies[name].to_numpy(dtype=np.float32)
        else:
            missing_columns.append(name)

    source_summary = dict(source_spec.source_summary)
    source_summary.update(
        {
            "source_normalized_transfer": True,
            "target_rows": int(len(target_frame)),
            "target_sensitive_rate": float(s.mean()),
            "target_label_rate": float(y.mean()),
            "source_schema_missing_target_columns": missing_columns,
        }
    )
    spec = replace(
        source_spec,
        train_idx=train_idx,
        val_idx=val_idx,
        test_idx=test_idx,
        source_summary=source_summary,
    )
    data = rfi.PreparedData(name="hmda", x=x, y=y, s=s, spec=spec)
    data.s_placebo = rfi.label_stratified_placebo_sensitive(data.s, data.y, 12345 + len(data.y))
    return data


def align_preprocessed_data_to_checkpoint(data: rfi.PreparedData, source_columns: list[str]) -> rfi.PreparedData:
    """Reorder/fill already source-normalized data for a particular checkpoint."""
    source_map = {name: idx for idx, name in enumerate(data.spec.input_columns)}
    aligned = np.zeros((data.x.shape[0], len(source_columns)), dtype=np.float32)
    missing: list[str] = []
    for dst_idx, name in enumerate(source_columns):
        src_idx = source_map.get(name)
        if src_idx is None:
            missing.append(name)
        else:
            aligned[:, dst_idx] = data.x[:, src_idx]
    source_summary = dict(data.spec.source_summary)
    source_summary["checkpoint_alignment_missing_columns"] = missing
    spec = replace(data.spec, input_columns=list(source_columns), source_summary=source_summary)
    return replace(data, x=aligned, spec=spec)


def eval_one(
    model: torch.nn.Module,
    ckpt: dict[str, Any],
    data: rfi.PreparedData,
    device: torch.device,
    args: argparse.Namespace,
    max_mechanism_eval: int,
) -> dict[str, float]:
    idx = data.spec.test_idx
    prob = rfi.predict_probs(model, data.x, idx, device)
    behavior = rfi.group_metrics(data.y[idx], data.s[idx], prob)
    thresholds = ckpt.get("group_thresholds_from_val")
    if thresholds:
        thresholds = {int(k): float(v) for k, v in thresholds.items()}
        behavior_thr = rfi.group_metrics(data.y[idx], data.s[idx], prob, thresholds=thresholds)
    else:
        behavior_thr = {}
    mechanism = rfi.mechanism_metrics(model, data, idx, device, max_eval=max_mechanism_eval, args=args)
    mechanism.update(rfi.higher_order_proxy_metrics(model, data, idx, device, max_eval=max_mechanism_eval, args=args))
    out: dict[str, float] = {}
    for key, value in behavior.items():
        out[f"behavior_{key}"] = float(value)
    for key, value in behavior_thr.items():
        out[f"source_threshold_{key}"] = float(value)
    for key, value in mechanism.items():
        if isinstance(value, (int, float, np.floating)) and math.isfinite(float(value)):
            out[f"mechanism_{key}"] = float(value)
        elif isinstance(value, (int, float, np.floating)):
            out[f"mechanism_{key}"] = float("nan")
    return out


def write_report(output_dir: Path, rows: list[dict[str, Any]], summary_pair: list[dict[str, Any]], target_local_dir: Path | None) -> None:
    metrics = [
        "behavior_auc",
        "behavior_accuracy",
        "behavior_aod_gap",
        "behavior_eod_gap",
        "behavior_eodds_max_gap",
        "behavior_dp_gap",
        "mechanism_pair_abs_mean",
        "mechanism_main_abs_logit_mean",
        "mechanism_proxy_score_gap_cond_mean",
        "mechanism_proxy_effect_gap_mean",
    ]
    by_model = summarize([r for r in rows if r["transfer_kind"] == "cross"], ["model_variant"], metrics)
    lines: list[str] = []
    lines.append("# HMDA Source-Normalized Cross-State Transfer Audit")
    lines.append("")
    lines.append("Exploratory audit only. This folder is separate from the shipped `results/` files and does not modify the frozen paper artifact.")
    lines.append("")
    lines.append("Protocol: load each source-state checkpoint and source-state preprocessing specification; transform raw target-state applicants with the source medians/IQR scales, source one-hot schema, and source finite-difference corner values; then evaluate on the target state's held-out split. This is stricter than the target-local transfer audit because preprocessing/scaling is transferred with the model.")
    lines.append("")
    lines.append("## Cross-State Mean Over Source-Target Pairs")
    lines.append("")
    lines.append("| Model | AUC | Acc | AOD | EOD | EOmax | DP | Pair | Main | Proxy score | Proxy effect |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in sorted(by_model, key=lambda r: (r["behavior_aod_gap_mean"], r["behavior_eod_gap_mean"])):
        lines.append(
            f"| {row['model_variant']} | {fmt(row['behavior_auc_mean'])} +/- {fmt(row['behavior_auc_std'])} | "
            f"{fmt(row['behavior_accuracy_mean'])} +/- {fmt(row['behavior_accuracy_std'])} | "
            f"{fmt(row['behavior_aod_gap_mean'])} +/- {fmt(row['behavior_aod_gap_std'])} | "
            f"{fmt(row['behavior_eod_gap_mean'])} +/- {fmt(row['behavior_eod_gap_std'])} | "
            f"{fmt(row['behavior_eodds_max_gap_mean'])} +/- {fmt(row['behavior_eodds_max_gap_std'])} | "
            f"{fmt(row['behavior_dp_gap_mean'])} +/- {fmt(row['behavior_dp_gap_std'])} | "
            f"{fmt(row['mechanism_pair_abs_mean_mean'])} +/- {fmt(row['mechanism_pair_abs_mean_std'])} | "
            f"{fmt(row['mechanism_main_abs_logit_mean_mean'])} +/- {fmt(row['mechanism_main_abs_logit_mean_std'])} | "
            f"{fmt(row['mechanism_proxy_score_gap_cond_mean_mean'])} +/- {fmt(row['mechanism_proxy_score_gap_cond_mean_std'])} | "
            f"{fmt(row['mechanism_proxy_effect_gap_mean_mean'])} +/- {fmt(row['mechanism_proxy_effect_gap_mean_std'])} |"
        )

    if target_local_dir is not None and (target_local_dir / "cross_state_summary_by_model.csv").exists():
        local = pd.read_csv(target_local_dir / "cross_state_summary_by_model.csv")
        src = pd.DataFrame(by_model)
        joined = src.merge(local, on="model_variant", suffixes=("_source_norm", "_target_local"))
        comp_rows = []
        for _, row in joined.iterrows():
            comp_rows.append(
                {
                    "model_variant": row["model_variant"],
                    "auc_delta_source_minus_target": row["behavior_auc_mean_source_norm"] - row["behavior_auc_mean_target_local"],
                    "acc_delta_source_minus_target": row["behavior_accuracy_mean_source_norm"] - row["behavior_accuracy_mean_target_local"],
                    "aod_delta_source_minus_target": row["behavior_aod_gap_mean_source_norm"] - row["behavior_aod_gap_mean_target_local"],
                    "eod_delta_source_minus_target": row["behavior_eod_gap_mean_source_norm"] - row["behavior_eod_gap_mean_target_local"],
                    "pair_delta_source_minus_target": row["mechanism_pair_abs_mean_mean_source_norm"] - row["mechanism_pair_abs_mean_mean_target_local"],
                    "proxy_effect_delta_source_minus_target": row["mechanism_proxy_effect_gap_mean_mean_source_norm"] - row["mechanism_proxy_effect_gap_mean_mean_target_local"],
                }
            )
        write_csv(output_dir / "source_vs_target_local_delta_by_model.csv", comp_rows)
        lines.append("")
        lines.append("## Difference From Target-Local Transfer")
        lines.append("")
        lines.append("See `source_vs_target_local_delta_by_model.csv`. Positive deltas mean source-normalized is larger than target-local; for gaps/residuals this is worse, for AUC/accuracy this is better.")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `cross_state_source_normalized_raw.csv`: one row per source, target, seed, and model variant.")
    lines.append("- `cross_state_source_normalized_summary_by_pair_model.csv`: mean/std over seeds for each source-target-model.")
    lines.append("- `cross_state_source_normalized_summary_by_model.csv`: mean/std over all source!=target rows for each model.")
    lines.append("- `source_vs_target_local_delta_by_model.csv`: optional comparison to target-local transfer if available.")
    (output_dir / "HMDA_SOURCE_NORMALIZED_CROSS_STATE_TRANSFER_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_existing_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append({key: (float("nan") if value == "" else value) for key, value in row.items()})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=Path("runs/phase3_confirmatory_10seeds_v1"))
    parser.add_argument("--output-dir", type=Path, default=Path("runs/cross_state_source_normalized_v1"))
    parser.add_argument("--target-local-dir", type=Path, default=Path("runs/cross_state_target_local_v1"))
    parser.add_argument("--states", nargs="+", default=STATES)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument(
        "--variants",
        nargs="+",
        default=None,
        help="Optional model variants to evaluate. Existing rows for other variants are preserved.",
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max-mechanism-eval", type=int, default=8192)
    args = parser.parse_args()

    device = torch.device(args.device if args.device != "cuda" or torch.cuda.is_available() else "cpu")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(2)
    requested_variants = set(args.variants) if args.variants else None
    selected_variants = [(variant, model_name) for variant, model_name in MODEL_VARIANTS if requested_variants is None or variant in requested_variants]
    if requested_variants is not None:
        known_variants = {variant for variant, _ in MODEL_VARIANTS}
        unknown = sorted(requested_variants - known_variants)
        if unknown:
            raise ValueError(f"Unknown variant(s): {unknown}. Known variants: {sorted(known_variants)}")

    template_ckpt_path = checkpoint_path(args.artifact_root, args.states[0], args.seeds[0], "erm", "erm")
    if template_ckpt_path is None:
        raise FileNotFoundError("Could not find template HMDA checkpoint")
    template_ckpt = torch.load(template_ckpt_path, map_location="cpu")
    template_args = template_ckpt["args"]

    rows: list[dict[str, Any]] = []
    target_raw_cache: dict[tuple[str, int], tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    source_data_cache: dict[tuple[str, int], rfi.PreparedData] = {}
    transformed_cache: dict[tuple[str, str, int], rfi.PreparedData] = {}
    aligned_cache: dict[tuple[str, str, int, tuple[str, ...]], rfi.PreparedData] = {}

    for target_state in [s.upper() for s in args.states]:
        for seed in args.seeds:
            target_key = (target_state, seed)
            if target_key not in target_raw_cache:
                print(f"[raw] target={target_state} seed={seed}", flush=True)
                target_raw_cache[target_key] = load_target_raw(argparse.Namespace(**template_args), target_state, seed)
            target_frame, y, s, train_idx, val_idx, test_idx = target_raw_cache[target_key]
            for source_state in [s_.upper() for s_ in args.states]:
                source_key = (source_state, seed)
                if source_key not in source_data_cache:
                    print(f"[source-prep] source={source_state} seed={seed}", flush=True)
                    source_args = make_data_args(template_args, source_state, args.output_dir)
                    source_data_cache[source_key] = rfi.load_data(source_args, seed)
                transformed_key = (source_state, target_state, seed)
                if transformed_key not in transformed_cache:
                    transformed_cache[transformed_key] = transform_target_with_source_spec(
                        source_data=source_data_cache[source_key],
                        target_frame=target_frame,
                        y=y,
                        s=s,
                        train_idx=train_idx,
                        val_idx=val_idx,
                        test_idx=test_idx,
                    )
                for variant, model_name in selected_variants:
                    ckpt_path = checkpoint_path(args.artifact_root, source_state, seed, variant, model_name)
                    if ckpt_path is None:
                        print(f"[skip] missing {source_state} seed={seed} {variant}/{model_name}", flush=True)
                        continue
                    model, ckpt = load_checkpoint_model(ckpt_path, device)
                    source_cols = tuple(ckpt["input_columns"])
                    aligned_key = (source_state, target_state, seed, source_cols)
                    if aligned_key not in aligned_cache:
                        aligned_cache[aligned_key] = align_preprocessed_data_to_checkpoint(transformed_cache[transformed_key], list(source_cols))
                    eval_args = argparse.Namespace(**ckpt["args"])
                    metrics = eval_one(
                        model=model,
                        ckpt=ckpt,
                        data=aligned_cache[aligned_key],
                        device=device,
                        args=eval_args,
                        max_mechanism_eval=args.max_mechanism_eval,
                    )
                    row: dict[str, Any] = {
                        "source_state": source_state,
                        "target_state": target_state,
                        "seed": seed,
                        "transfer_kind": "same_state" if source_state == target_state else "cross",
                        "preprocessing_mode": "source_normalized",
                        "model_variant": variant,
                        "checkpoint_model": model_name,
                        "checkpoint_path": str(ckpt_path),
                    }
                    row.update(metrics)
                    rows.append(row)
                    print(
                        f"[eval-srcnorm] {source_state}->{target_state} seed={seed} {variant}: "
                        f"AUC={row['behavior_auc']:.4f} AOD={row['behavior_aod_gap']:.4f} "
                        f"EOD={row['behavior_eod_gap']:.4f} pair={row['mechanism_pair_abs_mean']:.4f}",
                        flush=True,
                    )

    metrics = [
        "behavior_auc",
        "behavior_accuracy",
        "behavior_aod_gap",
        "behavior_eod_gap",
        "behavior_eodds_max_gap",
        "behavior_dp_gap",
        "source_threshold_auc",
        "source_threshold_accuracy",
        "source_threshold_aod_gap",
        "source_threshold_eod_gap",
        "source_threshold_eodds_max_gap",
        "source_threshold_dp_gap",
        "mechanism_pair_abs_mean",
        "mechanism_pair_abs_q95",
        "mechanism_main_abs_logit_mean",
        "mechanism_cf_abs_prob_mean",
        "mechanism_cf_flip_rate",
        "mechanism_proxy_score_gap_cond_mean",
        "mechanism_proxy_effect_gap_mean",
        "mechanism_boundary_proxy_score_gap_cond_mean",
        "mechanism_boundary_proxy_effect_gap_mean",
        "mechanism_higher_order_proxy_gap_scope_mean",
        "mechanism_higher_order_boundary_proxy_gap_scope_mean",
    ]
    if requested_variants is not None:
        existing_rows = read_existing_rows(args.output_dir / "cross_state_source_normalized_raw.csv")
        rows = [r for r in existing_rows if r.get("model_variant") not in requested_variants] + rows

    summary_pair = summarize(rows, ["transfer_kind", "source_state", "target_state", "model_variant"], metrics)
    summary_model = summarize([r for r in rows if r["transfer_kind"] == "cross"], ["model_variant"], metrics)
    write_csv(args.output_dir / "cross_state_source_normalized_raw.csv", rows)
    write_csv(args.output_dir / "cross_state_source_normalized_summary_by_pair_model.csv", summary_pair)
    write_csv(args.output_dir / "cross_state_source_normalized_summary_by_model.csv", summary_model)
    write_report(args.output_dir, rows, summary_pair, args.target_local_dir)
    print(f"Wrote {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
