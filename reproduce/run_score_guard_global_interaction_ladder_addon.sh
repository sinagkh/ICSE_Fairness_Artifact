#!/usr/bin/env bash
set -euo pipefail

# Run the missing compact-ladder rung:
# BCE + global label-conditioned score-gap + boundary-local score-gap
# + global direct/proxy feature-effect interaction, without boundary pair loss.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
OUT_ROOT="${OUT_ROOT:-${ROOT}/runs/score_guard_global_interaction_ladder_v1}"
LOG_ROOT="${LOG_ROOT:-${ROOT}/runs/logs/score_guard_global_interaction_ladder_v1}"
PYTHON="${PYTHON:-python3}"
DEVICE="${DEVICE:-cuda}"
THREADS="${THREADS:-2}"
SEEDS="${SEEDS:-1 2 3 4 5 6 7 8 9}"
MAX_JOBS="${MAX_JOBS:-3}"
CACHE_ROOT="${CACHE_ROOT:-${OUT_ROOT}/_prepared_cache}"

mkdir -p "$LOG_ROOT" "$OUT_ROOT"

COMMON=(
  --models score_guard_global_interaction
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
  --selection-min-delta 1e-4
  --prepared-cache-dir "$CACHE_ROOT"
  --lambda-adv 0.1
  --adv-hidden-dim 64
  --wrong-effect-margin 0.35
  --selector-mode behavior_proxy
)

run_one() {
  local dataset="$1"
  local seed="$2"
  case "$dataset" in
    hmda_oh)
      "$PYTHON" "$ROOT/scripts/run_fairness_interactions.py" \
        --dataset hmda \
        --hmda-path "$ROOT/data/raw/hmda_2019_oh.csv" \
        --hmda-url "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years=2019&states=OH" \
        --output-dir "$OUT_ROOT/hmda_oh/seed_${seed}" \
        --report-name "hmda_oh_score_guard_global_interaction_seed${seed}_report.md" \
        --seeds "$seed" \
        "${COMMON[@]}" \
        --lambda-main 0.0 \
        --lambda-pair 1.0 \
        --lambda-proxy-score 0.20 \
        --lambda-proxy-pair 0.40 \
        --lambda-boundary-score 0.20 \
        --lambda-boundary-pair 0.30 \
        --boundary-band 0.10 \
        --selector-min-auc 0.84
      ;;
    adult_gender)
      "$PYTHON" "$ROOT/scripts/run_fairness_interactions.py" \
        --dataset adult \
        --adult-axis-preset gender_proxy_no_sparse \
        --output-dir "$OUT_ROOT/adult_gender/seed_${seed}" \
        --report-name "adult_score_guard_global_interaction_seed${seed}_report.md" \
        --seeds "$seed" \
        "${COMMON[@]}" \
        --lambda-main 0.0 \
        --lambda-pair 0.35 \
        --lambda-proxy-score 0.20 \
        --lambda-proxy-pair 0.40 \
        --lambda-boundary-score 0.15 \
        --lambda-boundary-pair 0.25 \
        --boundary-band 0.18 \
        --selector-min-auc 0.895
      ;;
    acs_age)
      "$PYTHON" "$ROOT/scripts/run_fairness_interactions.py" \
        --dataset acs_employment \
        --acs-states MD \
        --output-dir "$OUT_ROOT/acs_age/seed_${seed}" \
        --report-name "acs_age_score_guard_global_interaction_seed${seed}_report.md" \
        --seeds "$seed" \
        "${COMMON[@]}" \
        --lambda-main 0.0 \
        --lambda-pair 0.2 \
        --lambda-proxy-score 0.30 \
        --lambda-proxy-pair 0.40 \
        --lambda-boundary-score 0.04 \
        --lambda-boundary-pair 0.06 \
        --boundary-band 0.18 \
        --selector-min-auc 0.748
      ;;
    *)
      echo "Unknown dataset: $dataset" >&2
      return 2
      ;;
  esac
}

for seed in $SEEDS; do
  for dataset in hmda_oh adult_gender acs_age; do
    log="$LOG_ROOT/${dataset}_score_guard_global_interaction_seed${seed}.log"
    (
      run_one "$dataset" "$seed"
    ) > "$log" 2>&1 &
    while (( $(jobs -pr | wc -l) >= MAX_JOBS )); do
      wait -n
    done
  done
done

wait
