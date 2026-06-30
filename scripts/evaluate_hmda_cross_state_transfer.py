#!/usr/bin/env python3
"""Evaluate final HMDA checkpoints on held-out applicants from other states.

This script reads locally regenerated checkpoints and writes a standalone
transfer audit.
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
import torch

SCRIPT_DIR = Path(__file__).resolve().parent
import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_fairness_interactions as rfi


STATES = ["MD", "OH", "PA", "VA"]

MODEL_VARIANTS = [
    ("erm", "erm"),
    ("blind", "blind"),
    ("reweight", "reweight"),
    ("adv", "adv"),
    ("score_only", "proxy_score_only"),
    ("no_interaction", "no_interaction"),
    ("repair_main0", "direct_spec_boundary"),
    ("repair_main05", "direct_spec_boundary"),
    ("wrong_spec", "direct_spec_boundary_wrong_effect"),
]


def hmda_url(state: str) -> str:
    return f"https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years=2019&states={state.upper()}"


def run_family(root: Path, source_state: str, variant: str) -> Path:
    state = source_state.lower()
    if variant == "repair_main05":
        return root / f"hmda_{state}" / "repair_main05"
    if variant == "no_interaction":
        return root / f"hmda_{state}" / "no_interaction"
    if source_state.upper() == "OH":
        return root / "hmda_oh_ladder"
    return root / f"hmda_{state}" / "main0_with_baselines"


def checkpoint_path(root: Path, source_state: str, seed: int, variant: str, model_name: str) -> Path | None:
    family = run_family(root, source_state, variant)
    path = family / f"seed_{seed}" / "hmda" / f"seed_{seed}" / "selected_artifacts" / f"{model_name}.pt"
    return path if path.exists() else None


def make_data_args(template_args: dict[str, Any], target_state: str, output_dir: Path) -> argparse.Namespace:
    args = argparse.Namespace(**template_args)
    args.dataset = "hmda"
    args.hmda_path = Path(f"data/raw/hmda_2019_{target_state.lower()}.csv")
    args.hmda_url = hmda_url(target_state)
    args.prepared_cache_dir = output_dir / "_prepared_cache"
    args.output_dir = output_dir / "_unused"
    args.device = "cpu"
    args.torch_threads = 2
    return args


def align_data_to_source_columns(data: rfi.PreparedData, source_columns: list[str]) -> rfi.PreparedData:
    """Reorder/fill target design matrix so it matches a source checkpoint."""
    target_map = {name: idx for idx, name in enumerate(data.spec.input_columns)}
    aligned = np.zeros((data.x.shape[0], len(source_columns)), dtype=np.float32)
    missing: list[str] = []
    for dst_idx, name in enumerate(source_columns):
        src_idx = target_map.get(name)
        if src_idx is None:
            missing.append(name)
        else:
            aligned[:, dst_idx] = data.x[:, src_idx]

    # The audit axes refer to continuous z/missing columns whose names are stable
    # across HMDA states. Replacing input_columns is enough for mechanism_metrics
    # to find the aligned column positions.
    source_summary = dict(data.spec.source_summary)
    source_summary["cross_state_alignment_missing_columns"] = missing
    spec = replace(data.spec, input_columns=list(source_columns), source_summary=source_summary)
    return replace(data, x=aligned, spec=spec)


def load_checkpoint_model(path: Path, device: torch.device) -> tuple[torch.nn.Module, dict[str, Any]]:
    ckpt = torch.load(path, map_location="cpu")
    arch = ckpt["architecture"]
    if arch["class"] != "MLP":
        raise ValueError(f"Unsupported checkpoint architecture {arch['class']} in {path}")
    model = rfi.MLP(
        input_dim=int(ckpt["input_dim"]),
        hidden_dim=int(arch["hidden_dim"]),
        depth=int(arch["depth"]),
        dropout=float(arch["dropout"]),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, ckpt


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


def summarize(rows: list[dict[str, Any]], group_keys: list[str], metrics: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(tuple(row[k] for k in group_keys), []).append(row)
    out: list[dict[str, Any]] = []
    for group, items in sorted(grouped.items()):
        base = {key: value for key, value in zip(group_keys, group)}
        base["n"] = len(items)
        for metric in metrics:
            vals = np.asarray([float(item.get(metric, float("nan"))) for item in items], dtype=np.float64)
            vals = vals[np.isfinite(vals)]
            if vals.size:
                base[f"{metric}_mean"] = float(vals.mean())
                base[f"{metric}_std"] = float(vals.std(ddof=1)) if vals.size > 1 else 0.0
            else:
                base[f"{metric}_mean"] = float("nan")
                base[f"{metric}_std"] = float("nan")
        out.append(base)
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float) -> str:
    if not math.isfinite(float(value)):
        return "nan"
    return f"{float(value):.4f}"


def write_report(output_dir: Path, rows: list[dict[str, Any]], summary: list[dict[str, Any]]) -> None:
    cross = [r for r in summary if r["transfer_kind"] == "cross"]
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
    by_model = summarize(
        [r for r in rows if r["transfer_kind"] == "cross"],
        ["model_variant"],
        metrics,
    )
    lines: list[str] = []
    lines.append("# HMDA Cross-State Transfer Audit")
    lines.append("")
    lines.append("Exploratory audit only. This folder is separate from the shipped `results/` files and does not modify the frozen paper artifact.")
    lines.append("")
    lines.append("Protocol: load each 10-seed HMDA checkpoint trained on one source state, evaluate it on the held-out split of each target state, and report both source=target sanity checks and source!=target transfer. Target states use the normal HMDA target-state preprocessing, then columns are aligned to the source checkpoint schema.")
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
    lines.append("")
    lines.append("## Per Source-Target Behavior Summary")
    lines.append("")
    lines.append("| Source | Target | Model | AUC | Acc | AOD | EOD | EOmax | Pair | Proxy effect |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    primary = [r for r in cross if r["model_variant"] in {"erm", "reweight", "adv", "score_only", "repair_main0", "repair_main05", "wrong_spec"}]
    for row in sorted(primary, key=lambda r: (r["source_state"], r["target_state"], r["behavior_aod_gap_mean"])):
        lines.append(
            f"| {row['source_state']} | {row['target_state']} | {row['model_variant']} | "
            f"{fmt(row['behavior_auc_mean'])} | {fmt(row['behavior_accuracy_mean'])} | "
            f"{fmt(row['behavior_aod_gap_mean'])} | {fmt(row['behavior_eod_gap_mean'])} | "
            f"{fmt(row['behavior_eodds_max_gap_mean'])} | {fmt(row['mechanism_pair_abs_mean_mean'])} | "
            f"{fmt(row['mechanism_proxy_effect_gap_mean_mean'])} |"
        )
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `cross_state_raw.csv`: one row per source, target, seed, and model variant.")
    lines.append("- `cross_state_summary_by_pair_model.csv`: mean/std over seeds for each source-target-model.")
    lines.append("- `cross_state_summary_by_model.csv`: mean/std over all cross-state rows for each model.")
    (output_dir / "HMDA_CROSS_STATE_TRANSFER_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=Path("runs/phase3_confirmatory_10seeds_v1"))
    parser.add_argument("--output-dir", type=Path, default=Path("runs/cross_state_target_local_v1"))
    parser.add_argument("--states", nargs="+", default=STATES)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max-mechanism-eval", type=int, default=8192)
    args = parser.parse_args()

    device = torch.device(args.device if args.device != "cuda" or torch.cuda.is_available() else "cpu")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(2)

    rows: list[dict[str, Any]] = []
    data_cache: dict[tuple[str, int, tuple[str, ...]], rfi.PreparedData] = {}
    loaded_target_base: dict[tuple[str, int], rfi.PreparedData] = {}

    # A checkpoint args payload gives us the exact data-loader defaults.
    template_ckpt_path = checkpoint_path(args.artifact_root, args.states[0], args.seeds[0], "erm", "erm")
    if template_ckpt_path is None:
        raise FileNotFoundError("Could not find template HMDA checkpoint")
    template_ckpt = torch.load(template_ckpt_path, map_location="cpu")
    template_args = template_ckpt["args"]

    for target_state in [s.upper() for s in args.states]:
        for seed in args.seeds:
            data_args = make_data_args(template_args, target_state, args.output_dir)
            base_key = (target_state, seed)
            if base_key not in loaded_target_base:
                print(f"[load] target={target_state} seed={seed}", flush=True)
                loaded_target_base[base_key] = rfi.load_data(data_args, seed)
            for source_state in [s.upper() for s in args.states]:
                for variant, model_name in MODEL_VARIANTS:
                    ckpt_path = checkpoint_path(args.artifact_root, source_state, seed, variant, model_name)
                    if ckpt_path is None:
                        print(f"[skip] missing {source_state} seed={seed} {variant}/{model_name}", flush=True)
                        continue
                    model, ckpt = load_checkpoint_model(ckpt_path, device)
                    source_cols = tuple(ckpt["input_columns"])
                    data_key = (target_state, seed, source_cols)
                    if data_key not in data_cache:
                        data_cache[data_key] = align_data_to_source_columns(loaded_target_base[base_key], list(source_cols))
                    eval_args = argparse.Namespace(**ckpt["args"])
                    metrics = eval_one(
                        model=model,
                        ckpt=ckpt,
                        data=data_cache[data_key],
                        device=device,
                        args=eval_args,
                        max_mechanism_eval=args.max_mechanism_eval,
                    )
                    row: dict[str, Any] = {
                        "source_state": source_state,
                        "target_state": target_state,
                        "seed": seed,
                        "transfer_kind": "same_state" if source_state == target_state else "cross",
                        "model_variant": variant,
                        "checkpoint_model": model_name,
                        "checkpoint_path": str(ckpt_path),
                    }
                    row.update(metrics)
                    rows.append(row)
                    print(
                        f"[eval] {source_state}->{target_state} seed={seed} {variant}: "
                        f"AOD={row['behavior_aod_gap']:.4f} EOD={row['behavior_eod_gap']:.4f} "
                        f"pair={row['mechanism_pair_abs_mean']:.4f}",
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
    summary_pair = summarize(rows, ["transfer_kind", "source_state", "target_state", "model_variant"], metrics)
    summary_model = summarize([r for r in rows if r["transfer_kind"] == "cross"], ["model_variant"], metrics)
    write_csv(args.output_dir / "cross_state_raw.csv", rows)
    write_csv(args.output_dir / "cross_state_summary_by_pair_model.csv", summary_pair)
    write_csv(args.output_dir / "cross_state_summary_by_model.csv", summary_model)
    write_report(args.output_dir, rows, summary_pair)
    print(f"Wrote {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
