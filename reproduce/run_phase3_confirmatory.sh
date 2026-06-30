#!/usr/bin/env bash
set -euo pipefail

# Ten-seed confirmatory sweep launcher.
#
# Default behavior is a dry run. Use DRY_RUN=0 to execute.
# Example:
#   DRY_RUN=0 MAX_JOBS=3 bash reproduce/run_phase3_confirmatory.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
if [[ ! -f "${DEFAULT_ROOT}/scripts/run_fairness_interactions.py" && -f "${DEFAULT_ROOT}/../scripts/run_fairness_interactions.py" ]]; then
  DEFAULT_ROOT="$(cd "${DEFAULT_ROOT}/.." && pwd)"
fi

ROOT="${ROOT:-${DEFAULT_ROOT}}"
OUT_ROOT="${OUT_ROOT:-${ROOT}/runs/phase3_confirmatory_9seeds_v1}"
LOG_ROOT="${LOG_ROOT:-${ROOT}/runs/logs/phase3_confirmatory_9seeds_v1}"
PYTHON="${PYTHON:-python3}"
DEVICE="${DEVICE:-cuda}"
MAX_JOBS="${MAX_JOBS:-3}"
DRY_RUN="${DRY_RUN:-1}"
SEEDS="${SEEDS:-1 2 3 4 5 6 7 8 9}"
THREADS="${THREADS:-2}"
SELECTION_MIN_DELTA="${SELECTION_MIN_DELTA:-1e-4}"
CACHE_ROOT="${CACHE_ROOT:-${OUT_ROOT}/_prepared_cache}"
HMDA_MIN_AUC="${HMDA_MIN_AUC:-0.84}"
ADULT_MIN_AUC="${ADULT_MIN_AUC:-0.895}"
ACS_AGE_MIN_AUC="${ACS_AGE_MIN_AUC:-0.748}"
ACS_INTERSECTIONAL_MIN_AUC="${ACS_INTERSECTIONAL_MIN_AUC:-0.73}"
ACS_INTERSECTIONAL_MIN_ACC="${ACS_INTERSECTIONAL_MIN_ACC:-0.69}"

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

COMMON_INTERSECTIONAL=(
  "${COMMON_TRAIN[@]}"
  --lambda-adv 0.1
  --adv-hidden-dim 64
  --boundary-band 0.18
  --selector-min-auc "$ACS_INTERSECTIONAL_MIN_AUC"
  --selector-min-acc "$ACS_INTERSECTIONAL_MIN_ACC"
  --wrong-margin 0.25
)

mkdir -p "$OUT_ROOT" "$LOG_ROOT" "$CACHE_ROOT"

run_limited() {
  local name="$1"
  shift
  local logfile="${LOG_ROOT}/${name}.log"
  local output_dir=""
  local report_name=""
  local report_path=""
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
      --report-path)
        if (( i + 1 < ${#args[@]} )); then
          report_path="${args[$((i + 1))]}"
        fi
        ;;
    esac
  done

  if [[ -n "$report_path" && -f "$report_path" ]]; then
    echo "[phase3] skip $name (found report $report_path)"
    return 0
  fi
  if [[ -n "$output_dir" && -n "$report_name" && -d "$output_dir" ]]; then
    if find "$output_dir" -name "$report_name" -type f -print -quit | grep -q .; then
      echo "[phase3] skip $name (found report $report_name under $output_dir)"
      return 0
    fi
  fi

  echo "[phase3] $name"
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

run_hmda_main0_with_baselines_seed() {
  local state="$1"
  local seed="$2"
  local state_upper="${state^^}"
  local state_lower="${state,,}"

  # Baselines, score/wrong controls, and the main0 direct-boundary repair share
  # the same lambda_main=0.0 configuration and one prepared-data cache.
  run_limited "hmda_${state_lower}_main0_with_baselines_seed${seed}" \
    "$PYTHON" "${ROOT}/scripts/run_fairness_interactions.py" \
      --dataset hmda \
      --hmda-path "${ROOT}/data/raw/hmda_2019_${state_lower}.csv" \
      --hmda-url "$(hmda_url "$state_upper")" \
      --output-dir "${OUT_ROOT}/hmda_${state_lower}/main0_with_baselines/seed_${seed}" \
      --report-name "hmda_${state_lower}_main0_with_baselines_seed${seed}_report.md" \
      --models erm blind reweight adv proxy_score_only direct_spec_boundary direct_spec_boundary_wrong_effect \
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

run_hmda_repair_main05_seed() {
  local state="$1"
  local seed="$2"
  local state_upper="${state^^}"
  local state_lower="${state,,}"

  # Main-effect variant. Keep boundary_band matched to main0 so lambda_main is
  # the only policy difference in the cross-state comparison.
  run_limited "hmda_${state_lower}_repair_main05_seed${seed}" \
    "$PYTHON" "${ROOT}/scripts/run_fairness_interactions.py" \
      --dataset hmda \
      --hmda-path "${ROOT}/data/raw/hmda_2019_${state_lower}.csv" \
      --hmda-url "$(hmda_url "$state_upper")" \
      --output-dir "${OUT_ROOT}/hmda_${state_lower}/repair_main05/seed_${seed}" \
      --report-name "hmda_${state_lower}_repair_main05_seed${seed}_report.md" \
      --models direct_spec_boundary \
      --seeds "$seed" \
      "${COMMON_FAIR[@]}" \
      --lambda-main 0.50 \
      --lambda-pair 1.0 \
      --lambda-proxy-score 0.20 \
      --lambda-proxy-pair 0.40 \
      --lambda-boundary-score 0.20 \
      --lambda-boundary-pair 0.30 \
      --boundary-band 0.10 \
      --selector-mode behavior_proxy \
      --selector-min-auc "$HMDA_MIN_AUC"
}

run_hmda_oh_ladder_seed() {
  local seed="$1"
  # Ohio ladder is the OH main0 superset: it includes shared baselines, controls,
  # direct boundary repair, and full ladder rows, so we do not launch a duplicate
  # OH main0/baseline job.
  run_limited "hmda_oh_ladder_seed${seed}" \
  "$PYTHON" "${ROOT}/scripts/run_fairness_interactions.py" \
    --dataset hmda \
    --hmda-path "${ROOT}/data/raw/hmda_2019_oh.csv" \
    --hmda-url "$(hmda_url OH)" \
    --output-dir "${OUT_ROOT}/hmda_oh_ladder/seed_${seed}" \
    --report-name "hmda_oh_ladder_seed${seed}_phase3_report.md" \
    --models erm blind reweight adv proxy_score_only proxy_effect proxy_exhaustive direct_spec_boundary direct_spec_full direct_spec_boundary_wrong_effect \
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

run_adult_gender_seed() {
  local seed="$1"
  run_limited "adult_gender_seed${seed}" \
  "$PYTHON" "${ROOT}/scripts/run_fairness_interactions.py" \
    --dataset adult \
    --adult-axis-preset gender_proxy_no_sparse \
    --output-dir "${OUT_ROOT}/adult_gender/seed_${seed}" \
    --report-name "adult_gender_seed${seed}_phase3_report.md" \
    --models erm blind reweight adv proxy_score_only direct_spec_boundary direct_spec_boundary_wrong_effect \
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
  run_limited "acs_age_seed${seed}" \
  "$PYTHON" "${ROOT}/scripts/run_fairness_interactions.py" \
    --dataset acs_employment \
    --acs-states MD \
    --output-dir "${OUT_ROOT}/acs_age/seed_${seed}" \
    --report-name "acs_age_seed${seed}_phase3_report.md" \
    --models erm blind reweight adv proxy_score_only proxy_exhaustive direct_spec_boundary direct_spec_boundary_wrong_effect \
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

run_acs_intersectional_seed() {
  local seed="$1"
  run_limited "acs_intersectional_age_race_seed${seed}" \
  "$PYTHON" "${ROOT}/scripts/run_acs_intersectional.py" \
    --states MD \
    --output-dir "${OUT_ROOT}/acs_intersectional_age_race/seed_${seed}" \
    --report-path "${OUT_ROOT}/acs_intersectional_age_race/seed_${seed}/ACS_INTERSECTIONAL_PHASE3_REPORT.md" \
    --models erm blind reweight adv r1_joint_marginal r3_intersectional r4_r1plus no_effect wrong_d3 \
    --seeds "$seed" \
    "${COMMON_INTERSECTIONAL[@]}"
}

for seed in $SEEDS; do
  for state in md va pa; do
    run_hmda_main0_with_baselines_seed "$state" "$seed"
    run_hmda_repair_main05_seed "$state" "$seed"
  done
  run_hmda_oh_ladder_seed "$seed"
  run_hmda_repair_main05_seed oh "$seed"
  run_adult_gender_seed "$seed"
  run_acs_age_seed "$seed"
  run_acs_intersectional_seed "$seed"
done

if [[ "$DRY_RUN" != "1" ]]; then
  wait
fi

echo "[phase3] submitted. OUT_ROOT=$OUT_ROOT LOG_ROOT=$LOG_ROOT DRY_RUN=$DRY_RUN"
