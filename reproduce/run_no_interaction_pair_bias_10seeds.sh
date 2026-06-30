#!/usr/bin/env bash
set -euo pipefail

# Add the no-interaction scaffold control for the final single-protected
# pair-bias confirmatory experiments. This reuses the concrete Phase-3 configs
# and writes beside the existing 10-seed artifact tree.
#
# Example:
#   DRY_RUN=0 MAX_JOBS=4 bash reproduce/run_no_interaction_pair_bias_10seeds.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
PYTHON="${PYTHON:-python3}"
DEVICE="${DEVICE:-cuda}"
MAX_JOBS="${MAX_JOBS:-4}"
DRY_RUN="${DRY_RUN:-1}"
SEEDS="${SEEDS:-0 1 2 3 4 5 6 7 8 9}"
THREADS="${THREADS:-2}"
OUT_ROOT="${OUT_ROOT:-${ROOT}/runs/no_interaction_pair_bias_10seeds_v1}"
LOG_ROOT="${LOG_ROOT:-${ROOT}/runs/logs/no_interaction_pair_bias_10seeds_v1}"
CACHE_ROOT="${CACHE_ROOT:-${OUT_ROOT}/_prepared_cache}"
RUNNER="${RUNNER:-${ROOT}/scripts/run_fairness_interactions.py}"

SELECTION_MIN_DELTA="${SELECTION_MIN_DELTA:-1e-4}"
HMDA_MIN_AUC="${HMDA_MIN_AUC:-0.84}"
ADULT_MIN_AUC="${ADULT_MIN_AUC:-0.895}"
ACS_AGE_MIN_AUC="${ACS_AGE_MIN_AUC:-0.748}"

COMMON_TRAIN=(
  --device "$DEVICE"
  --torch-threads "$THREADS"
  --epochs 100
  --patience 12
  --batch-size 512
  --anchor-batch-size 512
  --hidden-dim 128
  --depth 3
  --dropout 0.0
  --lr 7e-4
  --weight-decay 1e-4
  --baseline-selection utility
  --repair-selection utility_mechanism
  --utility-selector-metric bce
  --selector-auc-weight 0.0
  --selector-acc-weight 0.0
  --selection-min-delta "$SELECTION_MIN_DELTA"
  --prepared-cache-dir "$CACHE_ROOT"
)

COMMON_FAIR=(
  "${COMMON_TRAIN[@]}"
  --lambda-adv 0.1
  --adv-hidden-dim 64
  --wrong-effect-margin 0.35
)

mkdir -p "$OUT_ROOT" "$LOG_ROOT" "$CACHE_ROOT"

run_limited() {
  local name="$1"
  shift
  local logfile="${LOG_ROOT}/${name}.log"
  local output_dir=""
  local report_name=""
  local args=("$@")
  for ((i = 0; i < ${#args[@]}; i++)); do
    case "${args[$i]}" in
      --output-dir)
        if (( i + 1 < ${#args[@]} )); then
          output_dir="${args[$((i + 1))]}"
        fi
        ;;
      --report-name)
        if (( i + 1 < ${#args[@]} )); then
          report_name="${args[$((i + 1))]}"
        fi
        ;;
    esac
  done

  if [[ -n "$output_dir" && -n "$report_name" && -d "$output_dir" ]]; then
    if find "$output_dir" -name "$report_name" -type f -print -quit | grep -q .; then
      echo "[no-interaction] skip $name (found report $report_name under $output_dir)"
      return 0
    fi
  fi

  echo "[no-interaction] $name"
  printf '  %q' "$@"
  echo
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  "$@" >"$logfile" 2>&1 &
  while (( $(jobs -pr | wc -l) >= MAX_JOBS )); do
    sleep 20
  done
}

hmda_url() {
  local state="$1"
  echo "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years=2019&states=${state^^}"
}

run_hmda_no_interaction_seed() {
  local state="$1"
  local seed="$2"
  local state_upper="${state^^}"
  local state_lower="${state,,}"

  run_limited "hmda_${state_lower}_no_interaction_seed${seed}" \
    "$PYTHON" "$RUNNER" \
      --dataset hmda \
      --hmda-path "${ROOT}/data/raw/hmda_2019_${state_lower}.csv" \
      --hmda-url "$(hmda_url "$state_upper")" \
      --output-dir "${OUT_ROOT}/hmda_${state_lower}/no_interaction/seed_${seed}" \
      --report-name "hmda_${state_lower}_no_interaction_seed${seed}_report.md" \
      --models no_interaction \
      --seeds "$seed" \
      "${COMMON_FAIR[@]}" \
      --lambda-main 0.0 \
      --lambda-pair 1.0 \
      --lambda-proxy-score 0.20 \
      --lambda-proxy-pair 0.40 \
      --lambda-boundary-score 0.20 \
      --lambda-boundary-pair 0.30 \
      --boundary-band 0.10 \
      --selector-mode behavior_proxy \
      --selector-min-auc "$HMDA_MIN_AUC"
}

run_adult_no_interaction_seed() {
  local seed="$1"
  run_limited "adult_gender_no_interaction_seed${seed}" \
    "$PYTHON" "$RUNNER" \
      --dataset adult \
      --adult-axis-preset gender_proxy_no_sparse \
      --output-dir "${OUT_ROOT}/adult_gender/no_interaction/seed_${seed}" \
      --report-name "adult_gender_no_interaction_seed${seed}_report.md" \
      --models no_interaction \
      --seeds "$seed" \
      "${COMMON_FAIR[@]}" \
      --lambda-main 0.0 \
      --lambda-pair 0.35 \
      --lambda-proxy-score 0.20 \
      --lambda-proxy-pair 0.40 \
      --lambda-boundary-score 0.15 \
      --lambda-boundary-pair 0.25 \
      --boundary-band 0.18 \
      --selector-mode behavior_proxy \
      --selector-min-auc "$ADULT_MIN_AUC"
}

run_acs_age_no_interaction_seed() {
  local seed="$1"
  run_limited "acs_age_no_interaction_seed${seed}" \
    "$PYTHON" "$RUNNER" \
      --dataset acs_employment \
      --acs-states MD \
      --output-dir "${OUT_ROOT}/acs_age/no_interaction/seed_${seed}" \
      --report-name "acs_age_no_interaction_seed${seed}_report.md" \
      --models no_interaction \
      --seeds "$seed" \
      "${COMMON_FAIR[@]}" \
      --lambda-main 0.0 \
      --lambda-pair 0.2 \
      --lambda-proxy-score 0.30 \
      --lambda-proxy-pair 0.40 \
      --lambda-boundary-score 0.04 \
      --lambda-boundary-pair 0.06 \
      --boundary-band 0.18 \
      --selector-mode behavior_proxy \
      --selector-min-auc "$ACS_AGE_MIN_AUC"
}

for seed in $SEEDS; do
  for state in md va pa oh; do
    run_hmda_no_interaction_seed "$state" "$seed"
  done
  run_adult_no_interaction_seed "$seed"
  run_acs_age_no_interaction_seed "$seed"
done

if [[ "$DRY_RUN" != "1" ]]; then
  wait
fi

echo "[no-interaction] submitted. OUT_ROOT=$OUT_ROOT LOG_ROOT=$LOG_ROOT DRY_RUN=$DRY_RUN"
