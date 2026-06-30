#!/usr/bin/env Rscript

# Run ScottKnottESD on HMDA cross-state transfer metrics.
#
# Input: cross_state_raw.csv from evaluate_hmda_cross_state_transfer.py.
# Output:
#   - cross_state_scott_knott_esd_groups.csv: one ScottKnottESD grouping per metric
#     over all source != target rows (n=120 per complete model).
#   - cross_state_pair_scott_knott_esd_groups.csv: same grouping per source-target
#     pair and metric (n=10 per complete model).
#   - cross_state_scott_knott_esd_exclusions.csv: intentionally excluded blind rows
#     for direct protected-attribute mechanism metrics.
#   - CROSS_STATE_SCOTT_KNOTT_ESD_REPORT.md: run summary.

root <- getwd()
local_lib <- file.path(root, ".r_sk_libs")
.libPaths(c(local_lib, "/usr/lib/R/site-library", "/usr/lib/R/library"))

suppressPackageStartupMessages(library(ScottKnottESD))

args <- commandArgs(trailingOnly = TRUE)
input_csv <- if (length(args) >= 1) args[[1]] else
  "results/cross_state/cross_state_source_normalized_raw.csv"
output_dir <- if (length(args) >= 2) args[[2]] else
  "results/cross_state"

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

higher_is_better <- function(metric) {
  grepl("(auc|accuracy)$", metric)
}

descriptive_higher <- function(metric) {
  grepl(
    "positive_rate|_tpr_|_fpr_|boundary_fraction|pair_count|scope_count",
    metric
  )
}

direction_for_metric <- function(metric) {
  if (higher_is_better(metric)) {
    "higher"
  } else if (descriptive_higher(metric)) {
    "descriptive_higher"
  } else {
    "lower"
  }
}

is_degenerate_blind_direct_metric <- function(model, metric) {
  model == "blind" & grepl("^mechanism_(main_|cf_|pair_abs_)", metric)
}

metric_group_for <- function(metric) {
  if (startsWith(metric, "behavior_")) {
    "behavior"
  } else if (startsWith(metric, "source_threshold_")) {
    "source_threshold_behavior"
  } else if (startsWith(metric, "mechanism_")) {
    "mechanism"
  } else {
    "other"
  }
}

make_wide <- function(part, metric, obs_cols) {
  part$obs_id <- do.call(paste, c(part[obs_cols], sep = "\r"))
  obs <- sort(unique(part$obs_id))
  models <- sort(unique(part$model_variant))
  wide <- matrix(NA_real_, nrow = length(obs), ncol = length(models))
  colnames(wide) <- models
  rownames(wide) <- obs
  for (i in seq_len(nrow(part))) {
    wide[part$obs_id[[i]], part$model_variant[[i]]] <- part[[metric]][[i]]
  }
  wide
}

run_one <- function(raw, metric, obs_cols, source_state = "ALL", target_state = "ALL") {
  part <- raw[, c(obs_cols, "model_variant", metric), drop = FALSE]
  part <- part[is.finite(part[[metric]]), , drop = FALSE]
  if (nrow(part) == 0) {
    return(list(groups = data.frame(), error = data.frame(
      source_state = source_state,
      target_state = target_state,
      metric = metric,
      status = "skipped",
      error = "No finite values",
      stringsAsFactors = FALSE
    )))
  }

  wide <- make_wide(part, metric, obs_cols)
  complete_models <- colnames(wide)[colSums(is.na(wide)) == 0]
  wide <- wide[, complete_models, drop = FALSE]
  if (ncol(wide) < 2 || nrow(wide) < 2) {
    return(list(groups = data.frame(), error = data.frame(
      source_state = source_state,
      target_state = target_state,
      metric = metric,
      status = "skipped",
      error = "Need at least two complete models and two observations",
      stringsAsFactors = FALSE
    )))
  }

  direction <- direction_for_metric(metric)
  sk_input <- if (direction == "lower") -wide else wide
  fit <- tryCatch(
    ScottKnottESD::sk_esd(as.data.frame(sk_input, check.names = FALSE)),
    error = function(e) e
  )
  if (inherits(fit, "error")) {
    return(list(groups = data.frame(), error = data.frame(
      source_state = source_state,
      target_state = target_state,
      metric = metric,
      status = "error",
      error = conditionMessage(fit),
      stringsAsFactors = FALSE
    )))
  }

  group_vec <- fit$groups
  rows <- list()
  idx <- 1
  for (model in names(group_vec)) {
    vals <- wide[, model]
    rows[[idx]] <- data.frame(
      source_state = source_state,
      target_state = target_state,
      metric_group = metric_group_for(metric),
      metric = metric,
      direction = direction,
      model = model,
      n = length(vals),
      mean = mean(vals),
      std = if (length(vals) > 1) sd(vals) else 0,
      sk_esd_group = as.integer(group_vec[[model]]),
      package = "ScottKnottESD",
      package_version = as.character(packageVersion("ScottKnottESD")),
      stringsAsFactors = FALSE
    )
    idx <- idx + 1
  }
  list(groups = do.call(rbind, rows), error = data.frame())
}

run_many <- function(raw, metric_cols, pair_level = FALSE) {
  group_rows <- list()
  error_rows <- list()
  gi <- 1
  ei <- 1

  if (pair_level) {
    for (source_state in sort(unique(raw$source_state))) {
      for (target_state in sort(unique(raw$target_state))) {
        part_pair <- raw[raw$source_state == source_state & raw$target_state == target_state, ]
        for (metric in metric_cols) {
          res <- run_one(part_pair, metric, obs_cols = c("seed"), source_state = source_state, target_state = target_state)
          if (nrow(res$groups) > 0) {
            group_rows[[gi]] <- res$groups
            gi <- gi + 1
          }
          if (nrow(res$error) > 0) {
            error_rows[[ei]] <- res$error
            ei <- ei + 1
          }
        }
      }
    }
  } else {
    for (metric in metric_cols) {
      res <- run_one(raw, metric, obs_cols = c("source_state", "target_state", "seed"))
      if (nrow(res$groups) > 0) {
        group_rows[[gi]] <- res$groups
        gi <- gi + 1
      }
      if (nrow(res$error) > 0) {
        error_rows[[ei]] <- res$error
        ei <- ei + 1
      }
    }
  }

  groups <- if (length(group_rows)) do.call(rbind, group_rows) else data.frame()
  errors <- if (length(error_rows)) do.call(rbind, error_rows) else data.frame()
  list(groups = groups, errors = errors)
}

raw_all <- read.csv(input_csv, stringsAsFactors = FALSE, check.names = FALSE)
raw <- raw_all[raw_all$transfer_kind == "cross", ]

metric_cols <- names(raw)[vapply(raw, is.numeric, logical(1))]
metric_cols <- setdiff(metric_cols, "seed")
metric_cols <- metric_cols[grepl("^(behavior|source_threshold|mechanism)_", metric_cols)]

excluded_rows <- list()
ex_idx <- 1
for (metric in metric_cols) {
  mask <- is_degenerate_blind_direct_metric(raw$model_variant, metric)
  if (any(mask, na.rm = TRUE)) {
    excluded_rows[[ex_idx]] <- data.frame(
      source_state = raw$source_state[mask],
      target_state = raw$target_state[mask],
      seed = raw$seed[mask],
      model = raw$model_variant[mask],
      metric = metric,
      value = raw[[metric]][mask],
      exclusion_reason = paste(
        "blind removes the protected attribute; direct protected-main/pair",
        "mechanism residual is zero by construction"
      ),
      stringsAsFactors = FALSE
    )
    ex_idx <- ex_idx + 1
  }
}
excluded <- if (length(excluded_rows)) do.call(rbind, excluded_rows) else data.frame()

for (metric in metric_cols) {
  raw[[metric]][is_degenerate_blind_direct_metric(raw$model_variant, metric)] <- NA_real_
}

aggregate <- run_many(raw, metric_cols, pair_level = FALSE)
pair <- run_many(raw, metric_cols, pair_level = TRUE)

groups_csv <- file.path(output_dir, "cross_state_scott_knott_esd_groups.csv")
pair_groups_csv <- file.path(output_dir, "cross_state_pair_scott_knott_esd_groups.csv")
errors_csv <- file.path(output_dir, "cross_state_scott_knott_esd_errors.csv")
pair_errors_csv <- file.path(output_dir, "cross_state_pair_scott_knott_esd_errors.csv")
exclusions_csv <- file.path(output_dir, "cross_state_scott_knott_esd_exclusions.csv")

write.csv(aggregate$groups, groups_csv, row.names = FALSE)
write.csv(pair$groups, pair_groups_csv, row.names = FALSE)
write.csv(aggregate$errors, errors_csv, row.names = FALSE)
write.csv(pair$errors, pair_errors_csv, row.names = FALSE)
write.csv(excluded, exclusions_csv, row.names = FALSE)

primary_metrics <- c(
  "behavior_auc", "behavior_accuracy", "behavior_aod_gap",
  "behavior_eod_gap", "behavior_eodds_max_gap", "behavior_dp_gap",
  "mechanism_pair_abs_mean", "mechanism_main_abs_logit_mean",
  "mechanism_proxy_score_gap_cond_mean", "mechanism_proxy_effect_gap_mean"
)
primary <- aggregate$groups[aggregate$groups$metric %in% primary_metrics, ]
primary <- primary[order(primary$metric, primary$sk_esd_group, primary$mean), ]

report_path <- file.path(output_dir, "CROSS_STATE_SCOTT_KNOTT_ESD_REPORT.md")
con <- file(report_path, open = "w")
writeLines("# Cross-State ScottKnottESD Report\n", con)
writeLines("## Implementation\n", con)
writeLines(sprintf("- R version: `%s`", R.version.string), con)
writeLines(sprintf("- Package: `ScottKnottESD` `%s`", as.character(packageVersion("ScottKnottESD"))), con)
writeLines(sprintf("- Input: `%s`", input_csv), con)
writeLines("- Filter: `transfer_kind == cross`.", con)
writeLines("- Aggregate grouping: one ScottKnottESD test per metric over all cross-state source-target-seed values.", con)
writeLines("- Pair grouping: one ScottKnottESD test per source-target pair and metric.", con)
writeLines("- Direction: group 1 is best for `higher`/`lower` objective metrics. For `descriptive_higher` metrics, group 1 means the highest value, not necessarily best.\n", con)
writeLines("## Outputs\n", con)
writeLines("- `cross_state_scott_knott_esd_groups.csv`: aggregate cross-state groups.", con)
writeLines("- `cross_state_pair_scott_knott_esd_groups.csv`: per source-target groups.", con)
writeLines("- `cross_state_scott_knott_esd_errors.csv`: aggregate skipped/error metrics.", con)
writeLines("- `cross_state_pair_scott_knott_esd_errors.csv`: pair-level skipped/error metrics.", con)
writeLines("- `cross_state_scott_knott_esd_exclusions.csv`: rows intentionally excluded from direct mechanism metrics.\n", con)
writeLines("## Summary\n", con)
writeLines(sprintf("- Numeric metrics considered: `%d`.", length(metric_cols)), con)
writeLines(sprintf("- Aggregate group rows: `%d`.", nrow(aggregate$groups)), con)
writeLines(sprintf("- Aggregate skipped/error metrics: `%d`.", nrow(aggregate$errors)), con)
writeLines(sprintf("- Pair-level group rows: `%d`.", nrow(pair$groups)), con)
writeLines(sprintf("- Pair-level skipped/error metric cases: `%d`.", nrow(pair$errors)), con)
writeLines(sprintf("- Excluded blind direct-mechanism seed-level cells: `%d`.", nrow(excluded)), con)
writeLines("- Exclusion rule: `blind` is omitted for `mechanism_main_*`, `mechanism_cf_*`, and `mechanism_pair_abs_*`, because the protected attribute is removed and those residuals are zero by construction.\n", con)
writeLines("## Primary Aggregate Groups\n", con)
writeLines("| Metric | Direction | Group | Model | Mean | Std | n |", con)
writeLines("|---|---|---:|---|---:|---:|---:|", con)
if (nrow(primary) > 0) {
  for (i in seq_len(nrow(primary))) {
    writeLines(sprintf(
      "| `%s` | %s | %d | `%s` | %.6f | %.6f | %d |",
      primary$metric[[i]], primary$direction[[i]], primary$sk_esd_group[[i]],
      primary$model[[i]], primary$mean[[i]], primary$std[[i]], primary$n[[i]]
    ), con)
  }
}
close(con)

cat(sprintf("Wrote %s\n", groups_csv))
cat(sprintf("Wrote %s\n", pair_groups_csv))
cat(sprintf("Wrote %s\n", report_path))
