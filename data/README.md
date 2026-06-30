# Data Access

Raw datasets are not redistributed in this artifact. The scripts download or load the public sources below.

## HMDA 2019

Use the FFIEC/CFPB 2019 Modified Loan/Application Register files for Maryland, Virginia, Pennsylvania, and Ohio. The experiment restricts to White/Black applicants and predicts loan approval/origination (`action_taken` in `{1,2}`).

Expected raw data location for full reruns is configurable through `scripts/run_fairness_interactions.py`; see its `--hmda-root` argument.

## UCI Adult

The Adult data files are downloaded from the UCI repository by `scripts/run_fairness_interactions.py` when needed:

- `adult.data`
- `adult.test`

The experiment predicts income over 50K with sex as the protected attribute.

## ACS Employment

ACS Employment uses the `folktables` package to obtain ACS Public Use Microdata. The paired-bias experiment uses age as the protected attribute; the intersectional experiment uses age and race.

Install `folktables` from `requirements.txt` and configure the ACS cache/root with the corresponding script arguments.

## Splits and Seeds

All reported runs use seeds `0` through `9`, validation fraction `0.15`, test fraction `0.20`, maximum `100` epochs, and patience `12`, as described in `configs/CONFIRMATORY_RERUN_INSTRUCTIONS.md`.

