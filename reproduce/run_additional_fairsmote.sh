#!/usr/bin/env bash
set -euo pipefail

# Fair-SMOTE add-on launcher for the ICSE fairness-debugging paper.
# It writes only new Fair-SMOTE rows and does not modify the frozen Phase 3
# result tree. Use SEEDS="0" for the Phase 1 sanity pass, then SEEDS="0 ... 9".

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PYTHON:-python3}"
DEVICE="${DEVICE:-cuda}"
THREADS="${THREADS:-4}"
SEEDS="${SEEDS:-0}"
MAX_JOBS="${MAX_JOBS:-2}"
DRY_RUN="${DRY_RUN:-1}"
OUT_ROOT="${OUT_ROOT:-${ROOT}/runs/fairsmote/results_full_de_v1}"
LOG_ROOT="${LOG_ROOT:-${ROOT}/runs/logs/fairsmote_full_de_v1}"
CACHE_ROOT="${CACHE_ROOT:-${ROOT}/runs/fairsmote/_prepared_cache_full_de_v1}"
HMDA_MIN_AUC="${HMDA_MIN_AUC:-0.84}"
ADULT_MIN_AUC="${ADULT_MIN_AUC:-0.895}"
ACS_AGE_MIN_AUC="${ACS_AGE_MIN_AUC:-0.748}"

COMMON_FAIR=(
  --device "$DEVICE"
  --torch-threads "$THREADS"
  --epochs 100
  --patience 12
  --batch-size 512
  --anchor-batch-size 512
  --fairsmote-neighbors 5
  --fairsmote-cr 0.8
  --fairsmote-f 0.8
  --fairsmote-situation-testing
  --hidden-dim 128
  --depth 3
  --dropout 0.0
  --lr 7e-4
  --weight-decay 1e-4
  --lambda-adv 0.1
  --adv-hidden-dim 64
  --wrong-effect-margin 0.35
  --baseline-selection utility
  --repair-selection utility_mechanism
  --utility-selector-metric bce
  --selector-auc-weight 0.0
  --selector-acc-weight 0.0
  --selection-min-delta 1e-4
  --prepared-cache-dir "$CACHE_ROOT"
)

mkdir -p "$OUT_ROOT" "$LOG_ROOT" "$CACHE_ROOT"

hmda_url() {
  local state="$1"
  echo "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years=2019&states=${state^^}"
}

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
        output_dir="${args[$((i + 1))]}"
        ;;
      --report-name)
        report_name="${args[$((i + 1))]}"
        ;;
    esac
  done
  if [[ -n "$output_dir" && -n "$report_name" && -d "$output_dir" ]]; then
    if find "$output_dir" -name "$report_name" -type f -print -quit | rg -q .; then
      echo "[fairsmote] skip $name (found report)"
      return 0
    fi
  fi
  echo "[fairsmote] $name"
  printf '  %q' "$@"
  echo
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  "$@" >"$logfile" 2>&1 &
  while (( $(jobs -pr | wc -l) >= MAX_JOBS )); do
    sleep 15
  done
}

run_hmda_seed() {
  local state="$1"
  local seed="$2"
  local state_upper="${state^^}"
  local state_lower="${state,,}"
  run_limited "hmda_${state_lower}_fairsmote_seed${seed}" \
    "$PYTHON" "${ROOT}/scripts/run_fairness_interactions.py" \
      --dataset hmda \
      --hmda-path "${ROOT}/data/raw/hmda_2019_${state_lower}.csv" \
      --hmda-url "$(hmda_url "$state_upper")" \
      --output-dir "${OUT_ROOT}/hmda_${state_lower}/seed_${seed}" \
      --report-name "hmda_${state_lower}_fairsmote_seed${seed}_report.md" \
      --models fairsmote \
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

run_adult_seed() {
  local seed="$1"
  run_limited "adult_gender_fairsmote_seed${seed}" \
    "$PYTHON" "${ROOT}/scripts/run_fairness_interactions.py" \
      --dataset adult \
      --adult-axis-preset gender_proxy_no_sparse \
      --output-dir "${OUT_ROOT}/adult_gender/seed_${seed}" \
      --report-name "adult_gender_fairsmote_seed${seed}_report.md" \
      --models fairsmote \
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

run_acs_age_seed() {
  local seed="$1"
  run_limited "acs_age_fairsmote_seed${seed}" \
    "$PYTHON" "${ROOT}/scripts/run_fairness_interactions.py" \
      --dataset acs_employment \
      --acs-states MD \
      --output-dir "${OUT_ROOT}/acs_age/seed_${seed}" \
      --report-name "acs_age_fairsmote_seed${seed}_report.md" \
      --models fairsmote \
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
    run_hmda_seed "$state" "$seed"
  done
  run_adult_seed "$seed"
  run_acs_age_seed "$seed"
done

wait
echo "[fairsmote] complete"
