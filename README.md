## Quick Start

From the artifact root:

```bash
bash reproduce/check_artifact.sh
python3 reproduce/make_localization_figure_from_csv.py
```

The first command checks that required result files are present. The second command regenerates a dependency-free SVG version of the localization heatmap from the saved localization CSV.

## Contents

- `results/main/`: paired-bias experiment summaries and row-level metric files for the submission tables.
- `results/localization/`: per-feature residuals used for the four-panel localization figure.
- `generated/figures/localization_four_panel2.pdf`: localization figure used in the submission.
- `results/ladder/`: compact component-ablation ladders across HMDA states, Adult, and ACS.
- `results/cross_state/`: source-normalized HMDA cross-state transfer results and ScottKnottESD outputs.
- `results/intersectional/`: ACS age x race intersectional summaries and row-level metrics.
- `results/scott_knott/`: ScottKnottESD groupings, exclusions, and validation reports.
- `scripts/`: experiment runners, aggregation scripts, ScottKnottESD scripts, and figure-generation scripts.
- `reproduce/`: convenience scripts for artifact checks and full/partial reruns.
- `data/README.md`: instructions for obtaining public datasets.

Large row-level metric CSVs are stored as `.csv.gz`. They can be read directly by pandas or expanded with `gzip -dk`.

## Submission Result Mapping

- Paired-bias experiments: `results/main/confirmatory_summary_all_metrics_with_fairsmote.csv` and `results/main/confirmatory_primary_summary_with_fairsmote.csv`.
- Localization figure: `results/localization/localization_four_panel.csv`, `results/localization/localization_four_panel_seed_values.csv`, and `generated/figures/localization_four_panel2.pdf`.
- Component ablation: `results/ladder/*_ladder_10seed_summary.csv`, especially `hmda_va_compact_ladder_10seed_summary.csv`.
- Cross-state transfer: `results/cross_state/cross_state_source_normalized_summary_by_model.csv`.
- Intersectional experiment: `results/intersectional/acs_intersectional_summary_all_metrics.csv`.
- Statistical groupings: `results/scott_knott/*.csv` and `results/cross_state/*scott_knott*.csv`.

## Reproduction Levels

1. **Availability check:** run `bash reproduce/check_artifact.sh`. This does not require GPUs or raw datasets.
2. **Figure regeneration from saved data:** run `python3 reproduce/make_localization_figure_from_csv.py`.
3. **Aggregation/statistics rerun:** use the scripts in `scripts/` on the saved or newly produced result files. ScottKnottESD requires R and the CRAN `ScottKnottESD` package.
4. **Full experiment rerun:** use the shell scripts in `reproduce/` after obtaining the public datasets described in `data/README.md`. Full ten-seed reproduction trains many neural-network models and is GPU-time intensive.

## What Is Not Included

The artifact intentionally excludes trained `.pt`/`.pth` checkpoints, intermediate JSON checkpoint metadata, raw public datasets, and local caches. 
