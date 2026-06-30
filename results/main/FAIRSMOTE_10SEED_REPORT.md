# Fair-SMOTE 10-Seed Report

This report adds the faithful Fair-SMOTE preprocessing baseline to the confirmatory paired-bias table and reruns standard CRAN `ScottKnottESD` on the full primary metric set.

## Artifact Paths

- Fair-SMOTE-inclusive Phase 4 root: `results/main`
- Standard ScottKnottESD groups: `results/main/scott_knott_esd_groups.csv`
- Full long metric ledger: `results/main/confirmatory_long_metrics.csv`

## ScottKnottESD Audit

- Group rows written: `1410`.
- Error/skipped metric cases: `0`.
- Intentional excluded seed-level rows: `360` (`blind` direct protected-attribute mechanism metrics).
- Group `1` is best; lower-is-better metrics were negated before `sk_esd()`.

## Fair-SMOTE vs Interaction Steering

Values are mean +/- standard deviation over ten seeds. `SK` is the ScottKnottESD group for the same metric/dataset; lower group is better.

### HMDA-MD race

| Metric | Fair-SMOTE | SK | Interaction steering | SK |
|---|---:|---:|---:|---:|
| AUC | 0.8472 +/- 0.0042 | 7 | 0.8499 +/- 0.0022 | 6 |
| Acc. | 0.8332 +/- 0.0066 | 7 | 0.8616 +/- 0.0025 | 5 |
| AOD | 0.0132 +/- 0.0062 | 2 | 0.0081 +/- 0.0044 | 1 |
| EOD | 0.0114 +/- 0.0081 | 4 | 0.0039 +/- 0.0026 | 1 |
| EOdds | 0.0186 +/- 0.0098 | 3 | 0.0124 +/- 0.0087 | 2 |
| DP | 0.0717 +/- 0.0139 | 3 | 0.0586 +/- 0.0068 | 1 |
| Direct int. | 0.6233 +/- 0.1718 | 7 | 0.0040 +/- 0.0015 | 1 |
| Proxy effect | 0.6420 +/- 0.0920 | 9 | 0.0171 +/- 0.0027 | 2 |
| Proxy score | 0.2421 +/- 0.1035 | 3 | 0.0618 +/- 0.0336 | 1 |

### HMDA-VA race

| Metric | Fair-SMOTE | SK | Interaction steering | SK |
|---|---:|---:|---:|---:|
| AUC | 0.8502 +/- 0.0031 | 8 | 0.8583 +/- 0.0029 | 7 |
| Acc. | 0.8386 +/- 0.0073 | 8 | 0.8765 +/- 0.0025 | 5 |
| AOD | 0.0211 +/- 0.0115 | 4 | 0.0078 +/- 0.0061 | 1 |
| EOD | 0.0146 +/- 0.0071 | 6 | 0.0025 +/- 0.0019 | 1 |
| EOdds | 0.0281 +/- 0.0171 | 5 | 0.0131 +/- 0.0109 | 2 |
| DP | 0.0506 +/- 0.0111 | 1 | 0.0538 +/- 0.0064 | 2 |
| Direct int. | 0.6582 +/- 0.2341 | 8 | 0.0039 +/- 0.0017 | 1 |
| Proxy effect | 0.5670 +/- 0.0823 | 8 | 0.0183 +/- 0.0055 | 1 |
| Proxy score | 0.2748 +/- 0.1239 | 4 | 0.0813 +/- 0.0499 | 1 |

### HMDA-PA race

| Metric | Fair-SMOTE | SK | Interaction steering | SK |
|---|---:|---:|---:|---:|
| AUC | 0.8351 +/- 0.0032 | 8 | 0.8447 +/- 0.0036 | 6 |
| Acc. | 0.7987 +/- 0.0220 | 9 | 0.8546 +/- 0.0020 | 6 |
| AOD | 0.0153 +/- 0.0127 | 4 | 0.0070 +/- 0.0062 | 1 |
| EOD | 0.0152 +/- 0.0158 | 4 | 0.0021 +/- 0.0019 | 1 |
| EOdds | 0.0195 +/- 0.0138 | 3 | 0.0119 +/- 0.0118 | 1 |
| DP | 0.0925 +/- 0.0201 | 4 | 0.0810 +/- 0.0043 | 2 |
| Direct int. | 0.4924 +/- 0.0883 | 7 | 0.0033 +/- 0.0008 | 1 |
| Proxy effect | 0.4762 +/- 0.0738 | 7 | 0.0245 +/- 0.0053 | 1 |
| Proxy score | 0.2751 +/- 0.1159 | 4 | 0.0706 +/- 0.0430 | 1 |

### HMDA-OH race

| Metric | Fair-SMOTE | SK | Interaction steering | SK |
|---|---:|---:|---:|---:|
| AUC | 0.8413 +/- 0.0031 | 10 | 0.8519 +/- 0.0029 | 6 |
| Acc. | 0.8065 +/- 0.0189 | 10 | 0.8697 +/- 0.0020 | 6 |
| AOD | 0.0258 +/- 0.0203 | 6 | 0.0048 +/- 0.0030 | 2 |
| EOD | 0.0255 +/- 0.0208 | 7 | 0.0016 +/- 0.0011 | 1 |
| EOdds | 0.0302 +/- 0.0219 | 5 | 0.0082 +/- 0.0057 | 2 |
| DP | 0.0660 +/- 0.0303 | 4 | 0.0563 +/- 0.0033 | 2 |
| Direct int. | 0.5899 +/- 0.1911 | 10 | 0.0036 +/- 0.0014 | 1 |
| Proxy effect | 0.4834 +/- 0.0591 | 11 | 0.0214 +/- 0.0053 | 2 |
| Proxy score | 0.2542 +/- 0.1358 | 6 | 0.0908 +/- 0.0476 | 2 |

### Adult gender

| Metric | Fair-SMOTE | SK | Interaction steering | SK |
|---|---:|---:|---:|---:|
| AUC | 0.8889 +/- 0.0027 | 8 | 0.9013 +/- 0.0034 | 7 |
| Acc. | 0.8337 +/- 0.0041 | 7 | 0.8466 +/- 0.0028 | 6 |
| AOD | 0.1248 +/- 0.0282 | 7 | 0.0353 +/- 0.0136 | 1 |
| EOD | 0.1626 +/- 0.0415 | 6 | 0.0349 +/- 0.0289 | 1 |
| EOdds | 0.1626 +/- 0.0415 | 7 | 0.0467 +/- 0.0234 | 1 |
| DP | 0.1996 +/- 0.0205 | 8 | 0.1248 +/- 0.0151 | 1 |
| Direct int. | 0.7244 +/- 0.1318 | 6 | 0.0317 +/- 0.0020 | 1 |
| Proxy effect | 0.4483 +/- 0.0707 | 7 | 0.0186 +/- 0.0038 | 1 |
| Proxy score | 0.7487 +/- 0.1316 | 3 | 0.0888 +/- 0.0577 | 1 |

### ACS Employment age

| Metric | Fair-SMOTE | SK | Interaction steering | SK |
|---|---:|---:|---:|---:|
| AUC | 0.7497 +/- 0.0035 | 3 | 0.7420 +/- 0.0049 | 7 |
| Acc. | 0.7090 +/- 0.0039 | 5 | 0.7122 +/- 0.0047 | 3 |
| AOD | 0.1301 +/- 0.0223 | 8 | 0.0201 +/- 0.0110 | 1 |
| EOD | 0.0690 +/- 0.0147 | 6 | 0.0190 +/- 0.0099 | 1 |
| EOdds | 0.1911 +/- 0.0328 | 8 | 0.0272 +/- 0.0136 | 1 |
| DP | 0.1509 +/- 0.0192 | 6 | 0.0334 +/- 0.0190 | 3 |
| Direct int. | 0.3616 +/- 0.0838 | 6 | 0.0383 +/- 0.0026 | 1 |
| Proxy effect | 0.2730 +/- 0.0573 | 8 | 0.0293 +/- 0.0019 | 1 |
| Proxy score | 0.7192 +/- 0.0619 | 7 | 0.0389 +/- 0.0198 | 1 |

## Summary

- **HMDA-MD race**: Fair-SMOTE pair residual `0.623` vs steering `0.004`; AOD `0.013` vs steering `0.008`.
- **HMDA-VA race**: Fair-SMOTE pair residual `0.658` vs steering `0.004`; AOD `0.021` vs steering `0.008`.
- **HMDA-PA race**: Fair-SMOTE pair residual `0.492` vs steering `0.003`; AOD `0.015` vs steering `0.007`.
- **HMDA-OH race**: Fair-SMOTE pair residual `0.590` vs steering `0.004`; AOD `0.026` vs steering `0.005`.
- **Adult gender**: Fair-SMOTE pair residual `0.724` vs steering `0.032`; AOD `0.125` vs steering `0.035`.
- **ACS Employment age**: Fair-SMOTE pair residual `0.362` vs steering `0.038`; AOD `0.130` vs steering `0.020`.

Fair-SMOTE is a useful SE fairness baseline because it sometimes improves endpoint fairness through data preprocessing, but it does not repair the audited direct interaction mechanism. Interaction steering remains the only row that consistently reaches the best mechanism group across the paired-bias datasets.
