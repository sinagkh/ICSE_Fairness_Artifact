# Four-Panel Feature Localization Report

This artifact plots held-out per-feature direct interaction residuals (`pair_abs_mean__FEATURE`).
Rows are averaged over ten seeds. Color is clipped at the reported cap; printed values are unclipped.
Cell labels use three decimals for nonzero values below `0.01` to avoid displaying strong repairs as `0.00`.

- Color cap: `0.700`
- Model columns: ERM, Fair-SMOTE, Score-gap, No-interaction, Interaction steering.
- HMDA uses the fixed underwriting feature list; Adult and ACS use the largest ERM residual features, frozen before model comparison.

## Feature Sets

- **HMDA-PA Race**: LTV, DTI, Loan amt., Property value, Income, Tract minority %, Tract/MSA income
- **HMDA-OH Race**: LTV, DTI, Loan amt., Property value, Income, Tract minority %, Tract/MSA income
- **Adult Gender**: Hours/week, Married, Spouse, Age, Education, Own child, Exec/prof occ.
- **ACS Employment Age**: Schooling, Any disability, Cognitive disability, Native-born, Child in household, Householder, Sex

## Headline Pattern

- **HMDA-PA Race**: average selected-feature residual is `0.003` for interaction steering, `0.371` for ERM, and `0.492` for Fair-SMOTE; lowest row is `Interaction steering`.
- **HMDA-OH Race**: average selected-feature residual is `0.004` for interaction steering, `0.284` for ERM, and `0.590` for Fair-SMOTE; lowest row is `Interaction steering`.
- **Adult Gender**: average selected-feature residual is `0.033` for interaction steering, `0.327` for ERM, and `0.752` for Fair-SMOTE; lowest row is `Interaction steering`.
- **ACS Employment Age**: average selected-feature residual is `0.045` for interaction steering, `0.463` for ERM, and `0.436` for Fair-SMOTE; lowest row is `Interaction steering`.

## Files

- `localization_four_panel.pdf`
- `localization_four_panel.png`
- `localization_four_panel.csv`
- `localization_four_panel_seed_values.csv`
