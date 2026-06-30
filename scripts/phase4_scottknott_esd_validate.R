#!/usr/bin/env Rscript

# Validate model groupings with the standard CRAN ScottKnottESD package.
# The input is the confirmatory long-metrics CSV produced by
# phase4_confirmatory_aggregate.py. For lower-is-better metrics, values are
# negated before calling sk_esd(), so group 1 always denotes the best group.

root <- getwd()
local_lib <- file.path(root, ".r_sk_libs")
.libPaths(c(local_lib, "/usr/lib/R/site-library", "/usr/lib/R/library"))

suppressPackageStartupMessages(library(ScottKnottESD))

args <- commandArgs(trailingOnly = TRUE)
input_csv <- if (length(args) >= 1) args[[1]] else
  "results/main/confirmatory_long_metrics.csv.gz"
output_dir <- if (length(args) >= 2) args[[2]] else
  "results/scott_knott"

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

primary_single_behavior <- c(
  "auc", "accuracy", "aod_gap", "eod_gap", "eodds_max_gap", "fpr_gap", "dp_gap"
)
primary_intersectional_behavior <- c(
  "auc", "accuracy", "aod_age", "aod_race", "sAOD", "aod_excess",
  "eod_age", "eod_race", "sEOD", "eod_excess", "sEOdds_max"
)
primary_single_mechanism <- c(
  "pair_abs_mean", "pair_abs_q95", "pair_abs_max", "main_abs_logit_mean",
  "cf_flip_rate", "cf_abs_prob_mean", "proxy_effect_gap_mean",
  "proxy_effect_gap_max", "proxy_score_gap_cond_mean",
  "boundary_proxy_effect_gap_mean",
  "boundary_proxy_effect_gap_max", "boundary_proxy_score_gap_cond_mean",
  "higher_order_boundary_proxy_gap_scope_mean",
  "higher_order_boundary_proxy_gap_scope_max"
)
primary_intersectional_mechanism <- c("D2age", "D2race", "D3", "D2ar", "Gsub")

primary_metrics <- unique(c(
  primary_single_behavior, primary_intersectional_behavior,
  primary_single_mechanism, primary_intersectional_mechanism
))
higher_is_better <- c("auc", "accuracy")

is_degenerate_blind_direct_metric <- function(experiment, model, metric) {
  model == "blind" &&
    experiment != "acs_intersectional_age_race" &&
    (grepl("^main_", metric) || grepl("^cf_", metric) || grepl("^pair_abs_", metric))
}

raw <- read.csv(input_csv, stringsAsFactors = FALSE, check.names = FALSE)
raw <- raw[raw$split == "test" & raw$metric %in% primary_metrics, ]
raw$value <- as.numeric(raw$value)

excluded <- raw[
  mapply(is_degenerate_blind_direct_metric, raw$experiment, raw$model, raw$metric),
]
if (nrow(excluded) > 0) {
  excluded$exclusion_reason <- paste(
    "blind removes the protected attribute; direct protected-main/pair",
    "mechanism residual is zero by construction"
  )
}
raw <- raw[
  !mapply(is_degenerate_blind_direct_metric, raw$experiment, raw$model, raw$metric),
]

make_key <- function(df) {
  paste(df$experiment, df$dataset, df$state, df$metric, sep = "\r")
}
raw$key <- make_key(raw)

results <- list()
errors <- list()
idx <- 1
err_idx <- 1

for (key in sort(unique(raw$key))) {
  part <- raw[raw$key == key, ]
  bits <- strsplit(key, "\r", fixed = TRUE)[[1]]
  experiment <- bits[[1]]
  dataset <- bits[[2]]
  state <- bits[[3]]
  metric <- bits[[4]]
  direction <- if (metric %in% higher_is_better) "higher" else "lower"

  models <- sort(unique(part$model))
  seeds <- sort(unique(part$seed))
  wide <- matrix(NA_real_, nrow = length(seeds), ncol = length(models))
  colnames(wide) <- models
  rownames(wide) <- seeds
  for (i in seq_len(nrow(part))) {
    wide[as.character(part$seed[[i]]), part$model[[i]]] <- part$value[[i]]
  }

  complete_models <- colnames(wide)[colSums(is.na(wide)) == 0]
  wide <- wide[, complete_models, drop = FALSE]
  if (ncol(wide) < 2 || nrow(wide) < 2) {
    errors[[err_idx]] <- data.frame(
      experiment = experiment, dataset = dataset, state = state, metric = metric,
      status = "skipped", error = "Need at least two complete models and two seeds",
      stringsAsFactors = FALSE
    )
    err_idx <- err_idx + 1
    next
  }

  original_wide <- wide
  sk_input <- if (direction == "higher") wide else -wide
  sk_df <- as.data.frame(sk_input, check.names = FALSE)

  fit <- tryCatch(
    ScottKnottESD::sk_esd(sk_df),
    error = function(e) e
  )

  if (inherits(fit, "error")) {
    errors[[err_idx]] <- data.frame(
      experiment = experiment, dataset = dataset, state = state, metric = metric,
      status = "error", error = conditionMessage(fit),
      stringsAsFactors = FALSE
    )
    err_idx <- err_idx + 1
    next
  }

  group_vec <- fit$groups
  for (model in names(group_vec)) {
    vals <- original_wide[, model]
    results[[idx]] <- data.frame(
      experiment = experiment,
      dataset = dataset,
      state = state,
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
}

out <- if (length(results)) do.call(rbind, results) else data.frame()
err <- if (length(errors)) do.call(rbind, errors) else data.frame()

groups_csv <- file.path(output_dir, "scott_knott_esd_groups.csv")
errors_csv <- file.path(output_dir, "scott_knott_esd_errors.csv")
exclusions_csv <- file.path(output_dir, "scott_knott_esd_exclusions.csv")
write.csv(out, groups_csv, row.names = FALSE)
write.csv(err, errors_csv, row.names = FALSE)
write.csv(excluded, exclusions_csv, row.names = FALSE)

comparison_csv <- file.path(output_dir, "scott_knott_esd_comparison.csv")
light_csv <- file.path(output_dir, "scott_knott_groups.csv")
if (file.exists(light_csv) && nrow(out) > 0) {
  light <- read.csv(light_csv, stringsAsFactors = FALSE, check.names = FALSE)
  cmp <- merge(
    out,
    light[, c("experiment", "dataset", "state", "metric", "model", "sk_group")],
    by = c("experiment", "dataset", "state", "metric", "model"),
    all.x = TRUE
  )
  cmp$group_match <- cmp$sk_esd_group == cmp$sk_group
  write.csv(cmp, comparison_csv, row.names = FALSE)
} else {
  cmp <- data.frame()
}

report_path <- file.path(output_dir, "SCOTT_KNOTT_ESD_VALIDATION_REPORT.md")
con <- file(report_path, open = "w")
writeLines("# ScottKnottESD Validation Report\n", con)
writeLines("## Implementation\n", con)
writeLines(sprintf("- R version: `%s`", R.version.string), con)
writeLines(sprintf("- Package: `ScottKnottESD` `%s`", as.character(packageVersion("ScottKnottESD"))), con)
writeLines(sprintf("- Input: `%s`", input_csv), con)
writeLines("- Rule: group 1 is best; lower-is-better metrics are negated before `sk_esd()`.\n", con)
writeLines("## Outputs\n", con)
writeLines("- `scott_knott_esd_groups.csv`: standard ScottKnottESD groups.", con)
writeLines("- `scott_knott_esd_errors.csv`: metrics skipped or errored by the package.", con)
writeLines("- `scott_knott_esd_exclusions.csv`: rows intentionally excluded from grouping.", con)
writeLines("- `scott_knott_esd_comparison.csv`: comparison with the lightweight in-repo grouping.\n", con)
writeLines("## Summary\n", con)
writeLines(sprintf("- Group rows written: `%d`.", nrow(out)), con)
writeLines(sprintf("- Error/skipped metric cases: `%d`.", nrow(err)), con)
writeLines(sprintf("- Excluded seed-level metric rows: `%d`.", nrow(excluded)), con)
writeLines(
  "- Exclusion rule: `blind` is omitted for non-intersectional direct protected-attribute mechanism metrics matching `main_*`, `cf_*`, or `pair_abs_*`, because the protected attribute is removed and these residuals are zero by construction.",
  con
)
if (exists("cmp") && nrow(cmp) > 0) {
  matches <- sum(cmp$group_match, na.rm = TRUE)
  total <- sum(!is.na(cmp$sk_group))
  writeLines(sprintf("- Lightweight-vs-ScottKnottESD exact group matches: `%d/%d`.", matches, total), con)
  mismatches <- cmp[!is.na(cmp$sk_group) & !cmp$group_match, ]
  writeLines(sprintf("- Exact group mismatches: `%d`.", nrow(mismatches)), con)
}
if (nrow(err) > 0) {
  writeLines("\n## Errors/Skipped Cases\n", con)
  for (i in seq_len(min(20, nrow(err)))) {
    writeLines(sprintf(
      "- `%s %s %s %s`: `%s`",
      err$experiment[[i]], err$state[[i]], err$metric[[i]], err$status[[i]], err$error[[i]]
    ), con)
  }
}
close(con)

cat(sprintf("Wrote %s\n", groups_csv))
cat(sprintf("Wrote %s\n", report_path))
