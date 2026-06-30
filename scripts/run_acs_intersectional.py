from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from torch import nn

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_fairness_interactions import (  # noqa: E402
    AxisSpec,
    MLP,
    as_float_series,
    iter_minibatches,
    prepare_tabular_frame,
    sigmoid_np,
    weighted_bce_loss,
)


MODEL_LABELS = {
    "erm": "ERM",
    "blind": "Blind: age+race removed",
    "reweight": "Reweighted ERM",
    "adv": "Adversarial debiasing",
    "r1_joint_marginal": "R1 joint-marginal repair",
    "r3_intersectional": "R3 intersectional-only repair",
    "r4_full": "R4 full intersectional repair",
    "r4_full_guarded": "R4 full + marginal guards",
    "r4_r1plus": "R4 R1 + intersectional repair",
    "no_effect": "No-interaction control",
    "wrong_d3": "Wrong-D3 control",
}

REPAIR_MODELS = {
    "r1_joint_marginal",
    "r3_intersectional",
    "r4_full",
    "r4_full_guarded",
    "r4_r1plus",
    "no_effect",
    "wrong_d3",
}
WRONG_CONTROL_MODELS = {"wrong_d3"}


@dataclass
class ACSIntersectionalData:
    state: str
    x: np.ndarray
    y: np.ndarray
    age40: np.ndarray
    black: np.ndarray
    subgroup: np.ndarray
    input_columns: list[str]
    axes: list[AxisSpec]
    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray
    source_summary: dict[str, object]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACS Employment age-by-race intersectional interaction experiment.")
    parser.add_argument("--states", nargs="+", default=["MD"])
    parser.add_argument("--acs-root", type=Path, default=Path("data/raw/acs"))
    parser.add_argument("--acs-year", default="2018")
    parser.add_argument("--acs-horizon", choices=["1-Year", "5-Year"], default="1-Year")
    parser.add_argument("--acs-density", type=float, default=1.0)
    parser.add_argument(
        "--prepared-cache-dir",
        type=Path,
        default=None,
        help="Optional cache for preprocessed ACS arrays/splits keyed by state, seed, and data config.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("runs/acs_intersectional_age_race_seed0_v1"))
    parser.add_argument("--report-path", type=Path, default=Path("runs/reports/ACS_INTERSECTIONAL_AGE_RACE_REPORT.md"))
    parser.add_argument("--models", nargs="+", choices=list(MODEL_LABELS), default=["erm", "r1_joint_marginal", "r4_full", "no_effect", "wrong_d3"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--torch-threads", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--anchor-batch-size", type=int, default=512)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--dropout", type=float, default=0.0)
    parser.add_argument("--lr", type=float, default=7e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--test-frac", type=float, default=0.20)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--warmup-epochs", type=int, default=5)
    parser.add_argument("--lambda-d2", type=float, default=0.30)
    parser.add_argument("--lambda-d3", type=float, default=0.45)
    parser.add_argument("--lambda-ar", type=float, default=0.10)
    parser.add_argument("--lambda-score", type=float, default=0.06)
    parser.add_argument("--lambda-boundary", type=float, default=0.06)
    parser.add_argument("--lambda-marginal-behavior", type=float, default=0.08)
    parser.add_argument("--lambda-marginal-dp", type=float, default=0.02)
    parser.add_argument("--lambda-marginal-threshold", type=float, default=0.20)
    parser.add_argument("--marginal-threshold-temp", type=float, default=0.06)
    parser.add_argument("--lambda-adv", type=float, default=0.10)
    parser.add_argument("--adv-hidden-dim", type=int, default=64)
    parser.add_argument("--wrong-margin", type=float, default=0.25)
    parser.add_argument("--boundary-band", type=float, default=0.18)
    parser.add_argument("--selector-min-auc", type=float, default=0.73)
    parser.add_argument("--selector-min-acc", type=float, default=0.69)
    parser.add_argument("--selector-mech-weight", type=float, default=0.02)
    parser.add_argument("--selector-marginal-weight", type=float, default=0.40)
    parser.add_argument("--selector-auc-weight", type=float, default=0.05)
    parser.add_argument("--selector-acc-weight", type=float, default=0.02)
    parser.add_argument(
        "--selection-min-delta",
        type=float,
        default=0.0,
        help="Minimum validation-score improvement required to reset patience.",
    )
    parser.add_argument(
        "--baseline-selection",
        choices=["endpoint_fairness", "utility"],
        default="utility",
        help=(
            "Checkpoint policy for ERM/baseline/control rows. endpoint_fairness preserves legacy "
            "sAOD/excess-based selection; utility selects by validation task utility only."
        ),
    )
    parser.add_argument(
        "--repair-selection",
        choices=["endpoint_fairness_mechanism", "utility_mechanism"],
        default="utility_mechanism",
        help="Checkpoint policy for correct repair rows.",
    )
    parser.add_argument("--utility-selector-metric", choices=["bce", "auc", "accuracy"], default="bce")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--save-artifacts", action="store_true", default=True)
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def to_jsonable(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stratified_indices(labels: np.ndarray, rng: np.random.Generator, val_frac: float, test_frac: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train: list[int] = []
    val: list[int] = []
    test: list[int] = []
    for label in sorted(np.unique(labels).tolist()):
        idx = np.flatnonzero(labels == label)
        rng.shuffle(idx)
        n = len(idx)
        n_test = max(1, int(round(n * test_frac)))
        n_val = max(1, int(round(n * val_frac)))
        n_test = min(n_test, max(0, n - 2))
        n_val = min(n_val, max(0, n - n_test - 1))
        test.extend(idx[:n_test].tolist())
        val.extend(idx[n_test : n_test + n_val].tolist())
        train.extend(idx[n_test + n_val :].tolist())
    out = tuple(np.asarray(split, dtype=np.int64) for split in (train, val, test))
    for arr in out:
        rng.shuffle(arr)
    return out


def load_acs_age_race(args: argparse.Namespace, state: str, seed: int) -> ACSIntersectionalData:
    try:
        from folktables import ACSDataSource
    except ImportError as exc:
        raise RuntimeError("ACS experiments require `folktables`.") from exc

    states = [state.upper()]
    source = ACSDataSource(
        survey_year=str(args.acs_year),
        horizon=str(args.acs_horizon),
        survey="person",
        root_dir=str(args.acs_root),
    )
    frame = source.get_data(states=states, density=float(args.acs_density), random_seed=seed, download=True).reset_index(drop=True)
    frame = frame[(pd.to_numeric(frame["AGEP"], errors="coerce") > 16) & (pd.to_numeric(frame["AGEP"], errors="coerce") < 90)]
    if "PWGTP" in frame.columns:
        frame = frame[pd.to_numeric(frame["PWGTP"], errors="coerce") >= 1]
    frame = frame[pd.to_numeric(frame["RAC1P"], errors="coerce").isin([1, 2])].reset_index(drop=True)
    if args.max_rows is not None:
        frame = frame.sample(n=min(args.max_rows, len(frame)), random_state=seed).reset_index(drop=True)

    def num(col: str) -> pd.Series:
        return pd.to_numeric(frame[col], errors="coerce")

    age = num("AGEP")
    y = (num("ESR") == 1).to_numpy(dtype=np.float32)
    age40 = (age >= 40).to_numpy(dtype=np.float32)
    black = (num("RAC1P") == 2).to_numpy(dtype=np.float32)
    subgroup = (age40.astype(np.int64) * 2 + black.astype(np.int64)).astype(np.int64)
    split_labels = subgroup * 2 + y.astype(np.int64)
    rng = np.random.default_rng(seed)
    train_idx, val_idx, test_idx = stratified_indices(split_labels, rng, args.val_frac, args.test_frac)

    frame["female"] = (num("SEX") == 2).astype(np.float32)
    frame["married"] = (num("MAR") == 1).astype(np.float32)
    frame["never_married"] = (num("MAR") == 5).astype(np.float32)
    frame["divorced_or_separated"] = num("MAR").isin([3, 4]).astype(np.float32)
    frame["widowed"] = (num("MAR") == 2).astype(np.float32)
    frame["relp_householder"] = (num("RELP") == 0).astype(np.float32)
    frame["relp_spouse"] = (num("RELP") == 1).astype(np.float32)
    frame["relp_child"] = num("RELP").isin([2, 3, 4]).astype(np.float32)
    frame["relp_other"] = (~num("RELP").isin([0, 1, 2, 3, 4])).astype(np.float32)
    frame["native_us"] = (num("NATIVITY") == 1).astype(np.float32)
    frame["citizen"] = num("CIT").isin([1, 2, 3, 4]).astype(np.float32)
    frame["recent_mover"] = num("MIG").isin([2, 3]).astype(np.float32)
    frame["military_service"] = num("MIL").isin([1, 2, 3, 4]).astype(np.float32)
    frame["any_disability"] = (num("DIS") == 1).astype(np.float32)
    frame["hearing_disability"] = (num("DEAR") == 1).astype(np.float32)
    frame["vision_disability"] = (num("DEYE") == 1).astype(np.float32)
    frame["cognitive_disability"] = (num("DREM") == 1).astype(np.float32)
    frame["ancestry_reported"] = num("ANC").isin([1, 2]).astype(np.float32)

    binary_features = [
        "female",
        "married",
        "never_married",
        "divorced_or_separated",
        "widowed",
        "relp_householder",
        "relp_spouse",
        "relp_child",
        "relp_other",
        "native_us",
        "citizen",
        "recent_mover",
        "military_service",
        "any_disability",
        "hearing_disability",
        "vision_disability",
        "cognitive_disability",
        "ancestry_reported",
    ]
    continuous = ["SCHL", *binary_features]
    axis_features = ["SCHL", *binary_features]
    x_single, input_single, axes, prep_summary = prepare_tabular_frame(
        frame=frame,
        y=y,
        s=age40,
        sensitive_column="S_age40plus",
        continuous=continuous,
        categorical=[],
        axis_features=axis_features,
        train_idx=train_idx,
        binary_axis_features=binary_features,
    )
    x = np.concatenate([x_single[:, :1], black[:, None].astype(np.float32), x_single[:, 1:]], axis=1).astype(np.float32)
    input_columns = ["S_age40plus", "S_black", *input_single[1:]]
    adjusted_axes = []
    for axis in axes:
        adjusted_axes.append(
            AxisSpec(
                name=axis.name,
                feature=axis.feature,
                column=axis.column,
                low=axis.low,
                high=axis.high,
                low_raw=axis.low_raw,
                high_raw=axis.high_raw,
                missing_column=axis.missing_column,
            )
        )

    return ACSIntersectionalData(
        state=state.upper(),
        x=x,
        y=y,
        age40=age40,
        black=black,
        subgroup=subgroup,
        input_columns=input_columns,
        axes=adjusted_axes,
        train_idx=train_idx,
        val_idx=val_idx,
        test_idx=test_idx,
        source_summary={
            "rows": int(len(frame)),
            "states": states,
            "task": "ACS Employment, filtered to Black/White workers.",
            "protected_pair": "age>=40 x Black",
            "subgroup_names": {"0": "young_white", "1": "young_black", "2": "older_white", "3": "older_black"},
            "preprocessing": prep_summary,
        },
    )


def prepared_cache_key(args: argparse.Namespace, state: str, seed: int) -> str:
    payload = {
        "version": 1,
        "state": state.upper(),
        "seed": int(seed),
        "acs_root": str(args.acs_root),
        "acs_year": str(args.acs_year),
        "acs_horizon": str(args.acs_horizon),
        "acs_density": float(args.acs_density),
        "max_rows": args.max_rows,
        "val_frac": float(args.val_frac),
        "test_frac": float(args.test_frac),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]


def load_acs_age_race_cached(args: argparse.Namespace, state: str, seed: int) -> ACSIntersectionalData:
    if args.prepared_cache_dir is None:
        return load_acs_age_race(args, state, seed)
    cache_dir = args.prepared_cache_dir / "acs_intersectional_age_race"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{prepared_cache_key(args, state, seed)}.pkl"
    if cache_path.exists():
        with cache_path.open("rb") as handle:
            return pickle.load(handle)
    data = load_acs_age_race(args, state, seed)
    tmp_path = cache_path.with_name(f"{cache_path.name}.{os.getpid()}.tmp")
    with tmp_path.open("wb") as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp_path, cache_path)
    return data


def make_model(input_dim: int, args: argparse.Namespace, device: torch.device) -> MLP:
    return MLP(input_dim=input_dim, hidden_dim=args.hidden_dim, depth=args.depth, dropout=args.dropout).to(device)


class IntersectionalAdversary(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_groups: int = 4) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_groups),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class GradientReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx: object, x: torch.Tensor, scale: float) -> torch.Tensor:
        ctx.scale = scale
        return x.view_as(x)

    @staticmethod
    def backward(ctx: object, grad_output: torch.Tensor) -> tuple[torch.Tensor, None]:
        return -ctx.scale * grad_output, None


def gradient_reverse(x: torch.Tensor, scale: float) -> torch.Tensor:
    return GradientReverse.apply(x, scale)


def make_adversary(args: argparse.Namespace, device: torch.device) -> IntersectionalAdversary:
    # Label-conditioned four-way adversary: young/older x White/Black subgroup.
    return IntersectionalAdversary(input_dim=args.hidden_dim + 1, hidden_dim=args.adv_hidden_dim).to(device)


def tensor_slice(array: np.ndarray, idx: np.ndarray, device: torch.device) -> torch.Tensor:
    return torch.as_tensor(array[idx], dtype=torch.float32, device=device)


def clone_set(x: torch.Tensor, col: int, value: float) -> torch.Tensor:
    out = x.clone()
    out[:, col] = value
    return out


def clone_axis(x: torch.Tensor, axis: AxisSpec, col_to_idx: dict[str, int], value: float) -> torch.Tensor:
    out = x.clone()
    out[:, col_to_idx[axis.column]] = value
    if axis.missing_column is not None and axis.missing_column in col_to_idx:
        out[:, col_to_idx[axis.missing_column]] = 0.0
    return out


def subgroup_score(model: nn.Module, x: torch.Tensor, age_col: int, race_col: int, age: int, black: int) -> torch.Tensor:
    return model(clone_set(clone_set(x, age_col, float(age)), race_col, float(black)))


def feature_effect(model: nn.Module, x: torch.Tensor, axis: AxisSpec, col_to_idx: dict[str, int], age_col: int, race_col: int, age: int, black: int) -> torch.Tensor:
    base = clone_set(clone_set(x, age_col, float(age)), race_col, float(black))
    low = clone_axis(base, axis, col_to_idx, axis.low)
    high = clone_axis(base, axis, col_to_idx, axis.high)
    return model(high) - model(low)


def interaction_terms(model: nn.Module, x: torch.Tensor, axes: list[AxisSpec], col_to_idx: dict[str, int]) -> dict[str, torch.Tensor]:
    age_col = col_to_idx["S_age40plus"]
    race_col = col_to_idx["S_black"]
    d2age: list[torch.Tensor] = []
    d2race: list[torch.Tensor] = []
    d3: list[torch.Tensor] = []
    gsub: list[torch.Tensor] = []
    for axis in axes:
        e_yw = feature_effect(model, x, axis, col_to_idx, age_col, race_col, 0, 0)
        e_yb = feature_effect(model, x, axis, col_to_idx, age_col, race_col, 0, 1)
        e_ow = feature_effect(model, x, axis, col_to_idx, age_col, race_col, 1, 0)
        e_ob = feature_effect(model, x, axis, col_to_idx, age_col, race_col, 1, 1)
        d2age.append(0.5 * ((e_ow - e_yw) + (e_ob - e_yb)))
        d2race.append(0.5 * ((e_yb - e_yw) + (e_ob - e_ow)))
        d3.append((e_ob - e_yb) - (e_ow - e_yw))
        stacked = torch.stack([e_yw, e_yb, e_ow, e_ob], dim=0)
        pairs = [(stacked[i] - stacked[j]).abs() for i in range(4) for j in range(i + 1, 4)]
        gsub.append(torch.stack(pairs, dim=0).max(dim=0).values)
    s_yw = subgroup_score(model, x, age_col, race_col, 0, 0)
    s_yb = subgroup_score(model, x, age_col, race_col, 0, 1)
    s_ow = subgroup_score(model, x, age_col, race_col, 1, 0)
    s_ob = subgroup_score(model, x, age_col, race_col, 1, 1)
    d2ar = (s_ob - s_yb) - (s_ow - s_yw)
    return {
        "D2age": torch.stack(d2age, dim=0),
        "D2race": torch.stack(d2race, dim=0),
        "D3": torch.stack(d3, dim=0),
        "Gsub": torch.stack(gsub, dim=0),
        "D2ar": d2ar,
    }


def topk_square(values: torch.Tensor, frac: float = 0.35) -> torch.Tensor:
    if values.numel() == 0:
        return values.new_tensor(0.0)
    k = max(1, int(math.ceil(values.numel() * frac)))
    return torch.topk(values.square().flatten(), k=k, largest=True).values.mean()


def soft_binary_gap_loss(prob: torch.Tensor, y: torch.Tensor, group: torch.Tensor, min_cell_size: int = 8) -> tuple[torch.Tensor, torch.Tensor]:
    label_losses: list[torch.Tensor] = []
    for label in [0, 1]:
        m0 = (group == 0) & ((y > 0.5) == bool(label))
        m1 = (group == 1) & ((y > 0.5) == bool(label))
        if int(m0.sum().detach().cpu()) >= min_cell_size and int(m1.sum().detach().cpu()) >= min_cell_size:
            label_losses.append((prob[m1].mean() - prob[m0].mean()).square())
    if label_losses:
        aod_like = torch.stack(label_losses).mean()
    else:
        aod_like = prob.new_tensor(0.0)
    m0 = group == 0
    m1 = group == 1
    if int(m0.sum().detach().cpu()) >= min_cell_size and int(m1.sum().detach().cpu()) >= min_cell_size:
        dp_like = (prob[m1].mean() - prob[m0].mean()).square()
    else:
        dp_like = prob.new_tensor(0.0)
    return aod_like, dp_like


def marginal_behavior_guard_loss(prob: torch.Tensor, y: torch.Tensor, subgroup: torch.Tensor, args: argparse.Namespace) -> torch.Tensor:
    age = (subgroup >= 2).long()
    race = (subgroup % 2).long()
    age_aod, age_dp = soft_binary_gap_loss(prob, y, age)
    race_aod, race_dp = soft_binary_gap_loss(prob, y, race)
    threshold_temp = max(float(args.marginal_threshold_temp), 1e-4)
    soft_pred = torch.sigmoid((prob - 0.5) / threshold_temp)
    age_thresh_aod, age_thresh_dp = soft_binary_gap_loss(soft_pred, y, age)
    race_thresh_aod, race_thresh_dp = soft_binary_gap_loss(soft_pred, y, race)
    return (
        args.lambda_marginal_behavior * (age_aod + race_aod)
        + args.lambda_marginal_dp * (age_dp + race_dp)
        + args.lambda_marginal_threshold * (age_thresh_aod + race_thresh_aod + 0.5 * age_thresh_dp + 0.5 * race_thresh_dp)
    )


def label_score_guard_loss(logits: torch.Tensor, y: torch.Tensor, group: torch.Tensor, args: argparse.Namespace) -> torch.Tensor:
    loss = logits.new_tensor(0.0)
    prob = torch.sigmoid(logits)
    for group_value in sorted(torch.unique(group).detach().cpu().tolist()):
        for label in [0, 1]:
            mask = (group == int(group_value)) & ((y > 0.5) == bool(label))
            if int(mask.sum().detach().cpu()) >= 8:
                target = y[mask].mean()
                loss = loss + args.lambda_score * (prob[mask].mean() - target).square()
    return loss


def repair_loss(model_name: str, model: nn.Module, x: torch.Tensor, y: torch.Tensor, subgroup: torch.Tensor, data: ACSIntersectionalData, args: argparse.Namespace) -> torch.Tensor:
    col_to_idx = {name: i for i, name in enumerate(data.input_columns)}
    terms = interaction_terms(model, x, data.axes, col_to_idx)
    loss = x.new_tensor(0.0)
    if model_name in {"r1_joint_marginal", "r4_full", "r4_full_guarded", "r4_r1plus"}:
        loss = loss + args.lambda_d2 * (terms["D2age"].square().mean() + terms["D2race"].square().mean())
        loss = loss + args.lambda_d2 * 0.5 * (topk_square(terms["D2age"]) + topk_square(terms["D2race"]))
    if model_name in {"r3_intersectional", "r4_full", "r4_full_guarded", "r4_r1plus"}:
        loss = loss + args.lambda_d3 * terms["D3"].square().mean()
        loss = loss + args.lambda_d3 * topk_square(terms["D3"])
        loss = loss + args.lambda_ar * terms["D2ar"].square().mean()
    if model_name == "wrong_d3":
        wrong = torch.relu(terms["D3"].new_tensor(float(args.wrong_margin)) - terms["D3"].abs())
        loss = loss + args.lambda_d3 * (wrong.square().mean() + topk_square(wrong))
    if model_name == "no_effect":
        # Same anchor/budget path, but no interaction constraint.
        loss = loss + args.lambda_score * x.new_tensor(0.0)

    if model_name in {"r1_joint_marginal", "r4_r1plus"}:
        logits = model(x)
        prob = torch.sigmoid(logits)
        age = (subgroup >= 2).long()
        race = (subgroup % 2).long()
        loss = loss + label_score_guard_loss(logits, y, age, args)
        loss = loss + label_score_guard_loss(logits, y, race, args)
        boundary = (prob - 0.5).abs() <= args.boundary_band
        if int(boundary.sum().detach().cpu()) >= 16:
            b_terms = interaction_terms(model, x[boundary], data.axes, col_to_idx)
            loss = loss + args.lambda_boundary * (b_terms["D2age"].abs().mean() + b_terms["D2race"].abs().mean())
        loss = loss + marginal_behavior_guard_loss(prob, y, subgroup, args)

    if model_name in {"r3_intersectional", "r4_full", "r4_full_guarded", "r4_r1plus", "wrong_d3", "no_effect"}:
        # Guard: preserve subgroup-conditioned mean logits around labels, so the
        # model cannot win by simply flattening all outputs.
        logits = model(x)
        loss = loss + label_score_guard_loss(logits, y, subgroup, args)
        prob = torch.sigmoid(logits)
        boundary = (prob - 0.5).abs() <= args.boundary_band
        if int(boundary.sum().detach().cpu()) >= 16:
            b_terms = interaction_terms(model, x[boundary], data.axes, col_to_idx)
            if model_name == "r4_full":
                loss = loss + args.lambda_boundary * b_terms["D3"].abs().mean()
            if model_name in {"r4_full_guarded", "r4_r1plus"}:
                loss = loss + args.lambda_boundary * b_terms["D3"].abs().mean()
        if model_name == "r4_full_guarded":
            loss = loss + marginal_behavior_guard_loss(prob, y, subgroup, args)
    return loss


def train_weights(data: ACSIntersectionalData) -> np.ndarray:
    weights = np.ones(len(data.y), dtype=np.float32)
    labels_train = data.subgroup[data.train_idx].astype(np.int64) * 2 + data.y[data.train_idx].astype(np.int64)
    all_labels = data.subgroup.astype(np.int64) * 2 + data.y.astype(np.int64)
    total = float(len(labels_train))
    for label in np.unique(labels_train):
        count = int((labels_train == label).sum())
        weights[all_labels == label] = total / max(1.0, float(len(np.unique(labels_train)) * count))
    return weights


def sample_anchor_indices(data: ACSIntersectionalData, rng: np.random.Generator, count: int) -> np.ndarray:
    labels = data.subgroup[data.train_idx].astype(np.int64) * 2 + data.y[data.train_idx].astype(np.int64)
    per_cell = max(1, count // max(1, len(np.unique(labels))))
    out: list[int] = []
    for label in sorted(np.unique(labels).tolist()):
        pool = data.train_idx[labels == label]
        out.extend(rng.choice(pool, size=per_cell, replace=len(pool) < per_cell).tolist())
    if len(out) < count:
        out.extend(rng.choice(data.train_idx, size=count - len(out), replace=len(data.train_idx) < count).tolist())
    rng.shuffle(out)
    return np.asarray(out[:count], dtype=np.int64)


def predict_probs(model: nn.Module, x: np.ndarray, indices: np.ndarray, device: torch.device) -> np.ndarray:
    model.eval()
    out: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(indices), 8192):
            idx = indices[start : start + 8192]
            xb = torch.as_tensor(x[idx], dtype=torch.float32, device=device)
            out.append(torch.sigmoid(model(xb)).detach().cpu().numpy())
    return np.concatenate(out).astype(np.float32)


def safe_auc(y: np.ndarray, prob: np.ndarray) -> float:
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, prob))


def binary_aod(y: np.ndarray, pred: np.ndarray, group: np.ndarray) -> tuple[float, float, float, float]:
    stats: dict[int, tuple[float, float, float]] = {}
    for g in [0, 1]:
        mask = group.astype(np.int64) == g
        pos = mask & (y > 0.5)
        neg = mask & (y <= 0.5)
        tpr = float(pred[pos].mean()) if pos.any() else float("nan")
        fpr = float(pred[neg].mean()) if neg.any() else float("nan")
        dp = float(pred[mask].mean()) if mask.any() else float("nan")
        stats[g] = (tpr, fpr, dp)
    eod = abs(stats[1][0] - stats[0][0])
    fpr_gap = abs(stats[1][1] - stats[0][1])
    dp = abs(stats[1][2] - stats[0][2])
    return 0.5 * (eod + fpr_gap), eod, fpr_gap, dp


def subgroup_behavior(y: np.ndarray, pred: np.ndarray, subgroup: np.ndarray) -> tuple[float, float, float, float]:
    tpr: dict[int, float] = {}
    fpr: dict[int, float] = {}
    pr: dict[int, float] = {}
    for g in range(4):
        mask = subgroup.astype(np.int64) == g
        pos = mask & (y > 0.5)
        neg = mask & (y <= 0.5)
        tpr[g] = float(pred[pos].mean()) if pos.any() else float("nan")
        fpr[g] = float(pred[neg].mean()) if neg.any() else float("nan")
        pr[g] = float(pred[mask].mean()) if mask.any() else float("nan")
    aods: list[float] = []
    eods: list[float] = []
    fprs: list[float] = []
    dps: list[float] = []
    for a in range(4):
        for b in range(a + 1, 4):
            if all(math.isfinite(v) for v in [tpr[a], tpr[b], fpr[a], fpr[b]]):
                aods.append(0.5 * (abs(tpr[a] - tpr[b]) + abs(fpr[a] - fpr[b])))
                eods.append(abs(tpr[a] - tpr[b]))
                fprs.append(abs(fpr[a] - fpr[b]))
            if math.isfinite(pr[a]) and math.isfinite(pr[b]):
                dps.append(abs(pr[a] - pr[b]))
    return float(max(aods)), float(max(eods)), float(max(fprs)), float(max(dps))


def behavior_metrics(data: ACSIntersectionalData, indices: np.ndarray, prob: np.ndarray) -> dict[str, float]:
    y = data.y[indices]
    pred = (prob >= 0.5).astype(np.int64)
    aod_age, eod_age, fpr_age, dp_age = binary_aod(y, pred, data.age40[indices])
    aod_race, eod_race, fpr_race, dp_race = binary_aod(y, pred, data.black[indices])
    s_aod, s_eod, s_fpr, s_dp = subgroup_behavior(y, pred, data.subgroup[indices])
    max_aod = max(aod_age, aod_race)
    max_eod = max(eod_age, eod_race)
    return {
        "auc": safe_auc(y, prob),
        "accuracy": float(accuracy_score(y, pred)),
        "bce": float(log_loss(y, np.clip(prob, 1e-6, 1 - 1e-6), labels=[0, 1])),
        "aod_age": float(aod_age),
        "eod_age": float(eod_age),
        "fpr_age": float(fpr_age),
        "eodds_max_age": float(max(eod_age, fpr_age)),
        "dp_age": float(dp_age),
        "aod_race": float(aod_race),
        "eod_race": float(eod_race),
        "fpr_race": float(fpr_race),
        "eodds_max_race": float(max(eod_race, fpr_race)),
        "dp_race": float(dp_race),
        "sAOD": float(s_aod),
        "sEOD": float(s_eod),
        "sFPR": float(s_fpr),
        "sEOdds_max": float(max(s_eod, s_fpr)),
        "sDP": float(s_dp),
        "aod_excess": float(s_aod - max_aod),
        "eod_excess": float(s_eod - max_eod),
    }


def mechanism_metrics(model: nn.Module, data: ACSIntersectionalData, indices: np.ndarray, device: torch.device, max_eval: int = 8192) -> dict[str, float]:
    rng = np.random.default_rng(40403 + len(indices))
    eval_idx = indices
    if len(eval_idx) > max_eval:
        eval_idx = rng.choice(eval_idx, size=max_eval, replace=False)
    x = torch.as_tensor(data.x[eval_idx], dtype=torch.float32, device=device)
    model.eval()
    terms = interaction_terms(model, x, data.axes, {name: i for i, name in enumerate(data.input_columns)})
    return {
        "D2age": float(terms["D2age"].abs().mean().detach().cpu()),
        "D2race": float(terms["D2race"].abs().mean().detach().cpu()),
        "D3": float(terms["D3"].abs().mean().detach().cpu()),
        "D2ar": float(terms["D2ar"].abs().mean().detach().cpu()),
        "Gsub": float(terms["Gsub"].abs().mean().detach().cpu()),
    }


def selection_score(model_name: str, behavior: dict[str, float], mech: dict[str, float], args: argparse.Namespace) -> float:
    penalty = 0.0
    if behavior["auc"] < args.selector_min_auc:
        penalty += 10.0 * (args.selector_min_auc - behavior["auc"])
    if behavior["accuracy"] < args.selector_min_acc:
        penalty += 10.0 * (args.selector_min_acc - behavior["accuracy"])
    utility = utility_selection_score(behavior, args, penalty)
    endpoint_fairness = (
        behavior["sAOD"]
        + 0.5 * behavior["sEOD"]
        + 0.75 * max(0.0, behavior["aod_excess"])
        + 0.5 * max(0.0, behavior["eod_excess"])
        + args.selector_auc_weight * (1.0 - behavior["auc"])
        + args.selector_acc_weight * (1.0 - behavior["accuracy"])
        + penalty
    )
    correct_repair = {"r1_joint_marginal", "r3_intersectional", "r4_full", "r4_full_guarded", "r4_r1plus"}
    if model_name in WRONG_CONTROL_MODELS and args.baseline_selection == "utility":
        wrong_residual = max(0.0, float(args.wrong_margin) - finite_float(mech.get("D3")))
        if penalty > 0.0:
            return float(utility + wrong_residual)
        return float(wrong_residual + 1e-3 * utility)
    if model_name not in correct_repair and args.baseline_selection == "utility":
        return float(utility)
    score = utility if args.repair_selection == "utility_mechanism" and model_name in correct_repair else endpoint_fairness
    mechanism_residual = 0.0
    if model_name == "r1_joint_marginal":
        mechanism_residual = mech["D2age"] + mech["D2race"]
    elif model_name in {"r4_full", "r4_full_guarded", "r4_r1plus"}:
        mechanism_residual = mech["D2age"] + mech["D2race"] + mech["D3"] + 0.25 * mech["D2ar"]
        if model_name == "r4_full_guarded" and args.repair_selection != "utility_mechanism":
            score += args.selector_marginal_weight * (
                max(behavior["aod_age"], behavior["aod_race"])
                + 0.5 * max(behavior["eod_age"], behavior["eod_race"])
                + 0.25 * max(behavior["dp_age"], behavior["dp_race"])
            )
    elif model_name in {"r3_intersectional", "wrong_d3"}:
        mechanism_residual = mech["D3"]
    if args.repair_selection == "utility_mechanism" and model_name in correct_repair:
        if penalty > 0.0:
            return float(utility + mechanism_residual)
        if model_name in {"r1_joint_marginal", "r4_r1plus"}:
            marginal_behavior = (
                max(behavior["aod_age"], behavior["aod_race"])
                + 0.5 * max(behavior["eod_age"], behavior["eod_race"])
                + 0.25 * max(behavior["dp_age"], behavior["dp_race"])
            )
            return float(mechanism_residual + args.selector_marginal_weight * marginal_behavior + 1e-3 * utility)
        return float(mechanism_residual + 1e-3 * utility)
    score += args.selector_mech_weight * mechanism_residual
    return float(score)


def utility_selection_score(behavior: dict[str, float], args: argparse.Namespace, penalty: float = 0.0) -> float:
    if args.utility_selector_metric == "auc":
        score = 1.0 - behavior["auc"]
    elif args.utility_selector_metric == "accuracy":
        score = 1.0 - behavior["accuracy"]
    else:
        score = behavior["bce"]
    if args.utility_selector_metric != "auc":
        score += args.selector_auc_weight * (1.0 - behavior["auc"])
    if args.utility_selector_metric != "accuracy":
        score += args.selector_acc_weight * (1.0 - behavior["accuracy"])
    return float(score + penalty)


def finite_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(out):
        return default
    return out


def effective_selector_policy(model_name: str, args: argparse.Namespace) -> str:
    correct_repair = {"r1_joint_marginal", "r3_intersectional", "r4_full", "r4_full_guarded", "r4_r1plus"}
    if model_name in correct_repair:
        if args.repair_selection == "utility_mechanism":
            if model_name in {"r1_joint_marginal", "r4_r1plus"}:
                return "utility_guard_plus_marginal_mechanism"
            return "utility_guard_plus_mechanism"
        return "endpoint_fairness_plus_mechanism"
    if model_name in WRONG_CONTROL_MODELS and args.baseline_selection == "utility":
        return "utility_guard_plus_wrong_spec"
    if args.baseline_selection == "utility":
        return "utility_only"
    return "endpoint_fairness_only"


def train_one(model_name: str, data: ACSIntersectionalData, seed: int, args: argparse.Namespace, device: torch.device, run_dir: Path) -> dict[str, object]:
    set_seed(seed)
    rng = np.random.default_rng(seed + 3307)
    model = make_model(data.x.shape[1], args, device)
    adversary = make_adversary(args, device) if model_name == "adv" else None
    opt_params = list(model.parameters())
    if adversary is not None:
        opt_params.extend(adversary.parameters())
    opt = torch.optim.AdamW(opt_params, lr=args.lr, weight_decay=args.weight_decay)
    weights = train_weights(data) if model_name == "reweight" else np.ones(len(data.y), dtype=np.float32)
    blind_cols = [data.input_columns.index("S_age40plus"), data.input_columns.index("S_black")] if model_name == "blind" else []
    best_state: dict[str, torch.Tensor] | None = None
    best_adv_state: dict[str, torch.Tensor] | None = None
    best: dict[str, object] | None = None
    best_score = float("inf")
    stale = 0
    history: list[dict[str, object]] = []
    epochs = min(args.epochs, 12) if args.quick else args.epochs
    start = time.time()
    print(f"[{data.state} seed {seed}] training {model_name} for up to {epochs} epochs", flush=True)
    for epoch in range(epochs):
        model.train()
        losses: list[float] = []
        for batch_idx in iter_minibatches(data.train_idx, args.batch_size, rng):
            xb = tensor_slice(data.x, batch_idx, device)
            yb = tensor_slice(data.y, batch_idx, device)
            wb = tensor_slice(weights, batch_idx, device)
            if blind_cols:
                xb = xb.clone()
                xb[:, blind_cols] = 0.0
            opt.zero_grad(set_to_none=True)
            loss = weighted_bce_loss(model(xb), yb, wb)
            if adversary is not None:
                warmup = min(1.0, float(epoch + 1) / max(1, args.warmup_epochs))
                features = model.features(xb)
                adv_features = gradient_reverse(features, warmup * args.lambda_adv)
                adv_input = torch.cat([adv_features, yb.unsqueeze(1)], dim=1)
                adv_logits = adversary(adv_input)
                adv_target = torch.as_tensor(data.subgroup[batch_idx], dtype=torch.long, device=device)
                loss = loss + nn.functional.cross_entropy(adv_logits, adv_target)
            if model_name in REPAIR_MODELS:
                anchor_idx = sample_anchor_indices(data, rng, args.anchor_batch_size)
                xa = tensor_slice(data.x, anchor_idx, device)
                ya = tensor_slice(data.y, anchor_idx, device)
                ga = torch.as_tensor(data.subgroup[anchor_idx], dtype=torch.long, device=device)
                warmup = min(1.0, float(epoch + 1) / max(1, args.warmup_epochs))
                loss = loss + warmup * repair_loss(model_name, model, xa, ya, ga, data, args)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            losses.append(float(loss.detach().cpu()))

        val_prob = predict_probs(model, data.x, data.val_idx, device)
        val_behavior = behavior_metrics(data, data.val_idx, val_prob)
        val_mech = mechanism_metrics(model, data, data.val_idx, device, max_eval=4096)
        score = selection_score(model_name, val_behavior, val_mech, args)
        history.append({"epoch": epoch + 1, "train_loss": float(np.mean(losses)), "val_behavior": val_behavior, "val_mechanism": val_mech, "selection_score": score})
        if score < best_score - float(args.selection_min_delta):
            stale = 0
            best_score = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            best_adv_state = (
                {k: v.detach().cpu().clone() for k, v in adversary.state_dict().items()}
                if adversary is not None
                else None
            )
            best = history[-1]
        else:
            stale += 1
            if stale >= args.patience:
                print(f"[{data.state} seed {seed}] {model_name} early stop at epoch {epoch + 1}", flush=True)
                break
        print(
            f"[{data.state} seed {seed}] {model_name} epoch {epoch+1}: "
            f"auc={val_behavior['auc']:.4f} acc={val_behavior['accuracy']:.4f} "
            f"sAOD={val_behavior['sAOD']:.4f} excess={val_behavior['aod_excess']:.4f} "
            f"D2a={val_mech['D2age']:.4f} D2r={val_mech['D2race']:.4f} D3={val_mech['D3']:.4f}",
            flush=True,
        )

    assert best_state is not None and best is not None
    model.load_state_dict(best_state)
    if adversary is not None and best_adv_state is not None:
        adversary.load_state_dict(best_adv_state)
    test_prob = predict_probs(model, data.x, data.test_idx, device)
    test_behavior = behavior_metrics(data, data.test_idx, test_prob)
    test_mech = mechanism_metrics(model, data, data.test_idx, device)
    artifacts: dict[str, str] = {}
    if args.save_artifacts:
        artifact_dir = run_dir / f"seed_{seed}" / "selected_artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        ckpt = artifact_dir / f"{model_name}.pt"
        manifest = artifact_dir / f"{model_name}.artifact.json"
        payload = {
            "model": model_name,
            "label": MODEL_LABELS[model_name],
            "state": data.state,
            "seed": seed,
            "effective_selector": effective_selector_policy(model_name, args),
            "input_columns": data.input_columns,
            "axes": [asdict(axis) for axis in data.axes],
            "best": best,
            "test_behavior": test_behavior,
            "test_mechanism": test_mech,
            "args": vars(args),
            "model_state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
            "adversary_state_dict": (
                {k: v.detach().cpu() for k, v in adversary.state_dict().items()} if adversary is not None else None
            ),
        }
        torch.save(payload, ckpt)
        manifest_payload = {k: v for k, v in payload.items() if k not in {"model_state_dict", "adversary_state_dict"}}
        manifest_payload["checkpoint_path"] = str(ckpt)
        write_json(manifest, manifest_payload)
        artifacts = {"checkpoint": str(ckpt), "manifest": str(manifest)}
    result = {
        "state": data.state,
        "seed": seed,
        "model": model_name,
        "label": MODEL_LABELS[model_name],
        "effective_selector": effective_selector_policy(model_name, args),
        "best": best,
        "history": history,
        "test_behavior": test_behavior,
        "test_mechanism": test_mech,
        "artifacts": artifacts,
        "train_seconds": float(time.time() - start),
    }
    print(
        f"[{data.state} seed {seed}] finished {model_name}: "
        f"auc={test_behavior['auc']:.4f} acc={test_behavior['accuracy']:.4f} "
        f"sAOD={test_behavior['sAOD']:.4f} excess={test_behavior['aod_excess']:.4f} "
        f"D3={test_mech['D3']:.4f}",
        flush=True,
    )
    return result


def cell_counts(data: ACSIntersectionalData, indices: np.ndarray) -> dict[str, object]:
    sg = data.subgroup[indices].astype(np.int64)
    y = data.y[indices].astype(np.int64)
    names = {0: "young_white", 1: "young_black", 2: "older_white", 3: "older_black"}
    return {
        "n": int(len(indices)),
        "cells": {f"{names[g]}_y{label}": int(((sg == g) & (y == label)).sum()) for g in range(4) for label in [0, 1]},
    }


def fmt(value: object) -> str:
    try:
        f = float(value)  # type: ignore[arg-type]
    except Exception:
        return str(value)
    if not math.isfinite(f):
        return "nan"
    return f"{f:.4f}"


def write_report(path: Path, data: ACSIntersectionalData, results: list[dict[str, object]], args: argparse.Namespace) -> None:
    lines: list[str] = []
    lines.append("# ACS Employment Age x Race Intersectional Direct-Interaction Experiment")
    lines.append("")
    lines.append("Protected attributes are both present in the model: `age>=40` and `Black` among Black/White ACS Employment workers.")
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append(f"- Rows: {len(data.y)}")
    lines.append(f"- Train/val/test: {len(data.train_idx)} / {len(data.val_idx)} / {len(data.test_idx)}")
    lines.append(f"- Axes: {', '.join(axis.feature for axis in data.axes)}")
    lines.append("")
    lines.append("## Cell Counts")
    lines.append("")
    for split, idx in [("train", data.train_idx), ("val", data.val_idx), ("test", data.test_idx)]:
        lines.append(f"- `{split}`: `{cell_counts(data, idx)['cells']}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Model | AUC | Acc | AOD age | AOD race | sAOD | AOD excess | sEOD | sFPR | sEOdds max | EOD excess | D2age | D2race | D3 | D2ar | Gsub |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for result in results:
        b = result["test_behavior"]
        m = result["test_mechanism"]
        lines.append(
            f"| {result['label']} | {fmt(b['auc'])} | {fmt(b['accuracy'])} | {fmt(b['aod_age'])} | {fmt(b['aod_race'])} | "
            f"{fmt(b['sAOD'])} | {fmt(b['aod_excess'])} | {fmt(b['sEOD'])} | {fmt(b['sFPR'])} | {fmt(b['sEOdds_max'])} | "
            f"{fmt(b['eod_excess'])} | {fmt(m['D2age'])} | {fmt(m['D2race'])} | {fmt(m['D3'])} | {fmt(m['D2ar'])} | {fmt(m['Gsub'])} |"
        )
    lines.append("")
    lines.append("## Run Configuration")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(to_jsonable(vars(args)), indent=2, sort_keys=True))
    lines.append("```")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.torch_threads:
        torch.set_num_threads(args.torch_threads)
    device = torch.device(args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, object]] = []
    last_data: ACSIntersectionalData | None = None
    for state in [s.upper() for s in args.states]:
        for seed in args.seeds:
            data = load_acs_age_race_cached(args, state, seed)
            last_data = data
            run_dir = args.output_dir / state.lower()
            write_json(
                run_dir / f"seed_{seed}" / "data_manifest.json",
                {
                    "state": state,
                    "seed": seed,
                    "input_columns": data.input_columns,
                    "axes": [asdict(axis) for axis in data.axes],
                    "summary": data.source_summary,
                    "splits": {
                        "train": cell_counts(data, data.train_idx),
                        "val": cell_counts(data, data.val_idx),
                        "test": cell_counts(data, data.test_idx),
                    },
                },
            )
            for model_name in args.models:
                all_results.append(train_one(model_name, data, seed, args, device, run_dir))
                write_json(run_dir / f"seed_{seed}" / "results_so_far.json", all_results)
    write_json(args.output_dir / "results.json", all_results)
    if last_data is not None:
        write_report(args.report_path, last_data, all_results, args)


if __name__ == "__main__":
    main()
