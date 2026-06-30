#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[check] artifact root: $ROOT"

required=(
  "README.md"
  "requirements.txt"
  "data/README.md"
  "results/main/confirmatory_summary_all_metrics_with_fairsmote.csv"
  "results/main/confirmatory_primary_summary_with_fairsmote.csv"
  "results/main/confirmatory_long_metrics_with_fairsmote.csv.gz"
  "results/localization/localization_four_panel.csv"
  "generated/figures/localization_four_panel2.pdf"
  "results/ladder/hmda_va_compact_ladder_10seed_summary.csv"
  "results/cross_state/cross_state_source_normalized_summary_by_model.csv"
  "results/intersectional/acs_intersectional_summary_all_metrics.csv"
  "results/scott_knott/scott_knott_esd_groups.csv"
)

for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "[error] missing required file: $path" >&2
    exit 1
  fi
done
echo "[check] required files present"

if find . -type f \( -name '.DS_Store' -o -path '*/__pycache__/*' -o -name '*.pt' -o -name '*.pth' -o -name '*.ckpt' -o -name '*.pkl' -o -name '*.pickle' -o -name '*.npy' -o -name '*.npz' -o -name '*.json' -o -name '*.pyc' \) | grep -q .; then
  echo "[error] artifact contains checkpoint-like or bulky intermediate files:" >&2
  find . -type f \( -name '.DS_Store' -o -path '*/__pycache__/*' -o -name '*.pt' -o -name '*.pth' -o -name '*.ckpt' -o -name '*.pkl' -o -name '*.pickle' -o -name '*.npy' -o -name '*.npz' -o -name '*.json' -o -name '*.pyc' \) >&2
  exit 1
fi
echo "[check] no checkpoint-like binary/intermediate files found"

python3 - <<'PY'
from pathlib import Path

forbidden = [
    "fairness_" + "interaction_debugging",
    "paper_" + "artifact_final",
    "/Use" + "rs/",
    "codex_" + "project",
]
skip_suffixes = {".gz", ".pdf", ".png"}
hits = []
for path in Path(".").rglob("*"):
    if not path.is_file() or path.name == "SHA256SUMS" or path.suffix in skip_suffixes:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for token in forbidden:
        if token in text:
            hits.append((str(path), token))
if hits:
    detail = "\n".join(f"{p}: {token}" for p, token in hits[:20])
    raise SystemExit(f"internal path/name markers found:\n{detail}")
print("[check] no internal workspace path markers found")
PY

python3 - <<'PY'
import csv
import gzip
from collections import defaultdict
from pathlib import Path

root = Path(".")
summary = root / "results/main/confirmatory_summary_all_metrics_with_fairsmote.csv"
with summary.open(newline="") as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit("summary CSV is empty")
print(f"[check] main summary rows: {len(rows)}")

needed_experiments = {
    "hmda_race",
    "adult_gender",
    "acs_age",
    "acs_intersectional_age_race",
}
present = {r["experiment"] for r in rows}
missing = sorted(needed_experiments - present)
if missing:
    raise SystemExit(f"missing experiments in main summary: {missing}")

long_path = root / "results/main/confirmatory_long_metrics_with_fairsmote.csv.gz"
metrics = {"aod_age", "aod_race", "sAOD", "aod_excess"}
by_seed = defaultdict(dict)
with gzip.open(long_path, "rt", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if (
            row["experiment"] == "acs_intersectional_age_race"
            and row["split"] == "test"
            and row["metric"] in metrics
        ):
            key = (row["model"], int(row["seed"]))
            by_seed[key][row["metric"]] = float(row["value"])

checked = 0
for key, vals in by_seed.items():
    if metrics <= vals.keys():
        calc = vals["sAOD"] - max(vals["aod_age"], vals["aod_race"])
        if abs(calc - vals["aod_excess"]) > 1e-10:
            raise SystemExit(f"aod_excess mismatch for {key}: {vals['aod_excess']} vs {calc}")
        checked += 1
if checked == 0:
    raise SystemExit("no complete intersectional seed rows found")
print(f"[check] verified per-seed AOD-excess formula for {checked} model/seed rows")
PY

echo
echo "Paper mapping:"
echo "  main paired-bias table: results/main/confirmatory_summary_all_metrics_with_fairsmote.csv"
echo "  localization figure:    generated/figures/localization_four_panel2.pdf"
echo "  ladder table:           results/ladder/hmda_va_compact_ladder_10seed_summary.csv"
echo "  cross-state transfer:   results/cross_state/cross_state_source_normalized_summary_by_model.csv"
echo "  intersectional table:   results/intersectional/acs_intersectional_summary_all_metrics.csv"
echo "  ScottKnottESD groups:   results/scott_knott/ and results/cross_state/"
echo
echo "[check] OK"
