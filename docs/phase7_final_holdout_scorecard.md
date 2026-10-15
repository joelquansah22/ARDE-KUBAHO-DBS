# Phase 7 final held-out scorecard (synthetic data) - FROZEN

*Generated once by `python src/score_cleaning.py --final` on 15 October 2026, with the pipeline and configuration exactly as committed before the data was generated (decision log D169). No fixes were made after seeing these results; weaknesses are listed as limitations. Do not edit or regenerate.*

The final set was generated from `config/synthetic_final.yaml`: the production officers and layouts, a fresh seed (6151), held-out 2's harder mess (new date styles, district variants, initials, hyphens and extra names in duplicates, namesakes) and the reconciliation scenario switched on. No hand-made files were provided in `data/holdout/manual/raw/`.

## Cleaning and duplicates, next to the earlier rounds

Held-out 1 and held-out 2 are copied from the frozen v2 scorecard (first scores on unseen data). The main set has been seen many times; it is shown for reference only.

| measure | Main set (seed 2023) | Held-out 1, as first scored with the v2 code (seed 7919) | Held-out 2 HEADLINE (v2, seed 4243) | FINAL held-out round (seed 6151, Phase 7) |
|---|---|---|---|---|
| genuine errors % | 99.8 | 95.2 | 92.9 | 98.1 |
| officer habits % | 100.0 | 92.8 | 87.5 | 100.0 |
| namesakes kept apart % | n/a | 91.8 | 100.0 | 100.0 |
| privacy % | 100.0 | 100.0 | 100.0 | 100.0 |
| types below 90% | 0 | 5 | 6 | 1 |
| false corrections | 0 of 58,329 | 0 of 57,845 | 0 of 54,280 | 0 of 60,332 |
| rows missing | 0 | 536 | 596 | 0 |
| duplicate precision | 1.0 | 1.0 | 1.0 | 1.0 |
| duplicate recall (merged) | 0.864 | 0.59 | 0.53 | 0.443 |
| duplicate recall (merged or reviewed) | 1.0 | 0.885 | 0.687 | 0.869 |
| review queue per month (avg / busiest) | 7.6 / 15 | 11.5 / 24 | 8.2 / 13 | 10.2 / 22 |
| months over 1 hour | 0 | 0 | 0 | 0 |
| rows quarantined | 235 | 269 | 1093 | 521 |
| sheets skipped | 0 | 3 | 1 | 0 |
| crashed | no | no | no | no |

## Reconciliation

Held-out 1 and 2 had no reconciliation scenario, so only the main set can be compared.

| measure | Main set | Final held-out |
|---|---|---|
| Comparisons scored | 140.0 | 138.0 |
| With a planted discrepancy | 47.0 | 52.0 |
| Planted discrepancies caught | 22.0 | 34.0 |
| Catch rate % | 46.8 | 65.4 |
| Planted discrepancies at least the minimum apart | 20.0 | 30.0 |
| ... of which caught | 19.0 | 29.0 |
| Catch rate (at least the minimum) % | 95.0 | 96.7 |
| Flags raised | 27.0 | 40.0 |
| Flags: planted discrepancies caught | 22.0 | 34.0 |
| Flags: genuine data errors caught | 5.0 | 6.0 |
| Flags: unexplained false alarms | 0.0 | 0.0 |
| Planted report rows too small to detect on their own | 46.0 | 39.0 |

## Final held-out: results by error type

- Genuine errors fixed or flagged: **98.1%** (1,364 of 1,390). Target 95%: **met**.
- Error types below 90%: **1** (duplicate_beneficiary).
- False corrections: **0** clean values wrongly changed, out of 60,332 clean cells compared (0.000%); 7 more were wrong only as a knock-on from an injected error on the same row.
- Rows in the answer key missing from the cleaned tables: 0. Rows that should not be there: 0.

### (b) Totals by group

| group | fixed | flagged | missed | total | fixed_or_flagged_% |
|---|---|---|---|---|---|
| genuine_errors | 553 | 811 | 26 | 1390 | 98.1 |
| matching_traps | 64 | 0 | 0 | 64 | 100.0 |
| officer_habits | 14170 | 1142 | 0 | 15312 | 100.0 |
| privacy | 31 | 0 | 0 | 31 | 100.0 |

### (a) Fixed, flagged and missed by error type

| group | error_type | fixed | flagged | missed | total | fixed_or_flagged_% | below_90% |
|---|---|---|---|---|---|---|---|
| genuine_errors | duplicate_beneficiary | 27 | 26 | 8 | 61 | 86.9 | YES |
| genuine_errors | status_completed_but_late | 0 | 84 | 7 | 91 | 92.3 |  |
| genuine_errors | female_exceeds_total | 0 | 28 | 1 | 29 | 96.6 |  |
| genuine_errors | transcription_error | 20 | 12 | 1 | 33 | 97.0 |  |
| genuine_errors | late_entry | 0 | 312 | 7 | 319 | 97.8 |  |
| genuine_errors | missing_required | 41 | 111 | 2 | 154 | 98.7 |  |
| genuine_errors | accuracy_outlier | 0 | 9 | 0 | 9 | 100.0 |  |
| genuine_errors | date_out_of_window | 0 | 9 | 0 | 9 | 100.0 |  |
| genuine_errors | district_typo | 427 | 0 | 0 | 427 | 100.0 |  |
| genuine_errors | district_wrong_province | 0 | 23 | 0 | 23 | 100.0 |  |
| genuine_errors | duplicate_activity_row | 38 | 0 | 0 | 38 | 100.0 |  |
| genuine_errors | impossible_age | 0 | 7 | 0 | 7 | 100.0 |  |
| genuine_errors | impossible_household_size | 0 | 6 | 0 | 6 | 100.0 |  |
| genuine_errors | missing_monthly_report | 0 | 30 | 0 | 30 | 100.0 |  |
| genuine_errors | missing_target | 0 | 37 | 0 | 37 | 100.0 |  |
| genuine_errors | negative_value | 0 | 28 | 0 | 28 | 100.0 |  |
| genuine_errors | percent_over_100 | 0 | 4 | 0 | 4 | 100.0 |  |
| genuine_errors | sex_ambiguous_code_1 | 0 | 14 | 0 | 14 | 100.0 |  |
| genuine_errors | sum_mismatch | 0 | 71 | 0 | 71 | 100.0 |  |
| matching_traps | namesake_different_person | 64 | 0 | 0 | 64 | 100.0 |  |
| officer_habits | amount_in_usd | 3 | 0 | 0 | 3 | 100.0 |  |
| officer_habits | blank_row | 78 | 0 | 0 | 78 | 100.0 |  |
| officer_habits | date_dmy_text | 3769 | 0 | 0 | 3769 | 100.0 |  |
| officer_habits | date_excel_serial | 2270 | 0 | 0 | 2270 | 100.0 |  |
| officer_habits | date_month_year_text | 18 | 542 | 0 | 560 | 100.0 |  |
| officer_habits | date_new_format | 904 | 312 | 0 | 1216 | 100.0 |  |
| officer_habits | disability_variant | 952 | 0 | 0 | 952 | 100.0 |  |
| officer_habits | district_old_name | 23 | 1 | 0 | 24 | 100.0 |  |
| officer_habits | district_variant | 791 | 7 | 0 | 798 | 100.0 |  |
| officer_habits | donor_name_variant | 7 | 0 | 0 | 7 | 100.0 |  |
| officer_habits | donor_type_variant | 3 | 0 | 0 | 3 | 100.0 |  |
| officer_habits | id_stored_as_number | 0 | 253 | 0 | 253 | 100.0 |  |
| officer_habits | merged_header_row | 1 | 0 | 0 | 1 | 100.0 |  |
| officer_habits | number_as_text | 1867 | 23 | 0 | 1890 | 100.0 |  |
| officer_habits | percent_as_fraction | 5 | 0 | 0 | 5 | 100.0 |  |
| officer_habits | phone_leading_zero_lost | 256 | 0 | 0 | 256 | 100.0 |  |
| officer_habits | probability_format | 8 | 4 | 0 | 12 | 100.0 |  |
| officer_habits | province_variant | 1203 | 0 | 0 | 1203 | 100.0 |  |
| officer_habits | sex_variant | 1055 | 0 | 0 | 1055 | 100.0 |  |
| officer_habits | stage_variant | 13 | 0 | 0 | 13 | 100.0 |  |
| officer_habits | status_variant | 923 | 0 | 0 | 923 | 100.0 |  |
| officer_habits | title_row | 14 | 0 | 0 | 14 | 100.0 |  |
| officer_habits | totals_row | 7 | 0 | 0 | 7 | 100.0 |  |
| privacy | personal_data_contact | 25 | 0 | 0 | 25 | 100.0 |  |
| privacy | personal_data_individual_donor | 6 | 0 | 0 | 6 | 100.0 |  |

### (c) False corrections

Every cleaned cell that had no injected problem was compared with its true value.

| kind | entity | field | cells |
|---|---|---|---|
| knock-on from an injected error on the same row | registration | dob | 7 |

Examples:

| entity | field | source_file | source_row | raw_value | clean_value | true_value | kind |
|---|---|---|---|---|---|---|---|
| registration | dob | SYNTHETIC_beneficiary_register_FO02.xlsx | 89 | None |  | 30 | knock-on from an injected error on the same row |
| registration | dob | SYNTHETIC_beneficiary_register_FO02.xlsx | 132 | None |  | 39 | knock-on from an injected error on the same row |
| registration | dob | SYNTHETIC_beneficiary_register_FO02.xlsx | 187 | None |  | 43 | knock-on from an injected error on the same row |
| registration | dob | SYNTHETIC_beneficiary_register_FO02.xlsx | 206 | None |  | 52 | knock-on from an injected error on the same row |
| registration | dob | SYNTHETIC_beneficiary_register_FO02.xlsx | 240 | None |  | 42 | knock-on from an injected error on the same row |
| registration | dob | SYNTHETIC_beneficiary_register_FO02.xlsx | 350 | None |  | 63 | knock-on from an injected error on the same row |
| registration | dob | SYNTHETIC_beneficiary_register_FO02.xlsx | 353 | None |  | 46 | knock-on from an injected error on the same row |

Flags on rows with no injected problem at all (for information; a flag does not change a value):

| issue_code | rows |
|---|---|
| accuracy_outlier | 1 |

### (d) Duplicate beneficiaries: matching threshold

Pairs of registrations of the same person. Precision = share of matched pairs that are right; recall = share of true pairs found. Same national ID = always matched; otherwise names must score at least the threshold, in the same district and of the same sex, and are kept apart if phones differ by more than 1 digit, IDs differ, or ages differ by more than 2 years. The two lower variants switch rules off only to show what each rule contributes.

| rules | threshold | configured | true_pairs | pairs_found | correct_pairs | wrong_pairs | missed_pairs | precision | recall | clusters_mixing_different_people | pairs_sent_to_review | true_pairs_in_review | recall_merged_or_reviewed | namesake_pairs_merged | namesake_pairs_reviewed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full rules (as used by the pipeline) | 80 |  | 61 | 30 | 30 | 0 | 31 | 1.0 | 0.492 | 0 | 38 | 29 | 0.967 | 0 of 64 | 8 |
| full rules (as used by the pipeline) | 85 |  | 61 | 28 | 28 | 0 | 33 | 1.0 | 0.459 | 0 | 36 | 28 | 0.918 | 0 of 64 | 8 |
| full rules (as used by the pipeline) | 88 | yes | 61 | 27 | 27 | 0 | 34 | 1.0 | 0.443 | 0 | 34 | 26 | 0.869 | 0 of 64 | 8 |
| full rules (as used by the pipeline) | 92 |  | 61 | 23 | 23 | 0 | 38 | 1.0 | 0.377 | 0 | 34 | 26 | 0.803 | 0 of 64 | 8 |
| names + vetoes, no ID rule | 80 |  | 61 | 27 | 27 | 0 | 34 | 1.0 | 0.443 | 0 | 41 | 32 | 0.967 | 0 of 64 | 8 |
| names + vetoes, no ID rule | 85 |  | 61 | 24 | 24 | 0 | 37 | 1.0 | 0.393 | 0 | 40 | 32 | 0.918 | 0 of 64 | 8 |
| names + vetoes, no ID rule | 88 | yes | 61 | 20 | 20 | 0 | 41 | 1.0 | 0.328 | 0 | 39 | 31 | 0.836 | 0 of 64 | 8 |
| names + vetoes, no ID rule | 92 |  | 61 | 14 | 14 | 0 | 47 | 1.0 | 0.23 | 0 | 39 | 31 | 0.738 | 0 of 64 | 8 |
| names only, no vetoes, no ID rule | 80 |  | 61 | 639 | 44 | 595 | 17 | 0.069 | 0.721 | 199 | 0 | 0 | 0.721 | 64 of 64 | 0 |
| names only, no vetoes, no ID rule | 85 |  | 61 | 252 | 39 | 213 | 22 | 0.155 | 0.639 | 127 | 0 | 0 | 0.639 | 64 of 64 | 0 |
| names only, no vetoes, no ID rule | 88 | yes | 61 | 159 | 32 | 127 | 29 | 0.201 | 0.525 | 98 | 0 | 0 | 0.525 | 64 of 64 | 0 |
| names only, no vetoes, no ID rule | 92 |  | 61 | 127 | 25 | 102 | 36 | 0.197 | 0.41 | 88 | 0 | 0 | 0.41 | 64 of 64 | 0 |

Name scores of the 61 true duplicate pairs read by the pipeline: lowest 64, 17 below 80, 22 below 85, 29 below 88, 36 below 92.

### Missed problems

| error_type | outcome_note | count |
|---|---|---|
| duplicate_beneficiary | not matched to first registration | 8 |
| status_completed_but_late | wrong value: completed (true delayed) | 7 |
| missing_required |  | 2 |
| female_exceeds_total | wrong value: 25.0 (true 9.0) | 1 |
| late_entry | wrong value: 2024-05-31 (true 2024-05-31) | 1 |
| late_entry | wrong value: 2024-01-31 (true 2024-01-31) | 1 |
| late_entry | wrong value: 2024-08-02 (true 2024-08-02) | 1 |
| late_entry | wrong value: 2025-10-09 (true 2025-10-09) | 1 |
| late_entry | wrong value: 2026-06-04 (true 2026-06-04) | 1 |
| late_entry | wrong value: 2026-03-12 (true 2026-03-12) | 1 |
| late_entry | wrong value: 2026-07-10 (true 2026-07-10) | 1 |
| transcription_error |  | 1 |

| error_type | source_file | source_sheet | source_row | field | true_value | messy_value | outcome_note |
|---|---|---|---|---|---|---|---|
| missing_required | SYNTHETIC_activity_monitoring_FO01.xlsx | Activities | 294.0 | total | 35 |  |  |
| status_completed_but_late | SYNTHETIC_activity_monitoring_FO01.xlsx | Activities | 795.0 | status | delayed | Completed | wrong value: completed (true delayed) |
| status_completed_but_late | SYNTHETIC_activity_monitoring_FO01.xlsx | Activities | 819.0 | status | delayed | Completed | wrong value: completed (true delayed) |
| status_completed_but_late | SYNTHETIC_activity_monitoring_FO02.xlsx | Activities | 583.0 | status | delayed | completed | wrong value: completed (true delayed) |
| late_entry | SYNTHETIC_activity_monitoring_FO02.xlsx | Activities | 722.0 | entry_date | 34 | 2026.03.12 | wrong value: 2026-03-12 (true 2026-03-12) |
| status_completed_but_late | SYNTHETIC_activity_monitoring_FO02.xlsx | Activities | 782.0 | status | delayed | completed | wrong value: completed (true delayed) |
| status_completed_but_late | SYNTHETIC_activity_monitoring_FO02.xlsx | Activities | 811.0 | status | delayed | completed | wrong value: completed (true delayed) |
| missing_required | SYNTHETIC_activity_monitoring_FO03.xlsx | Activities | 292.0 | total | 12 |  |  |
| status_completed_but_late | SYNTHETIC_activity_monitoring_FO04.xlsx | FY2023-24 | 158.0 | status | delayed | Complete | wrong value: completed (true delayed) |
| status_completed_but_late | SYNTHETIC_activity_monitoring_FO04.xlsx | FY2025-26 | 177.0 | status | delayed | Completed | wrong value: completed (true delayed) |
| late_entry | SYNTHETIC_digitised_paper_records.xlsx | Activities | 41.0 | entry_date | 44 | 2024-01-31 00:00:00 | wrong value: 2024-01-31 (true 2024-01-31) |
| late_entry | SYNTHETIC_digitised_paper_records.xlsx | Activities | 84.0 | entry_date | 33 | 2024-05-31 00:00:00 | wrong value: 2024-05-31 (true 2024-05-31) |
| late_entry | SYNTHETIC_digitised_paper_records.xlsx | Activities | 102.0 | entry_date | 37 | 02/Aug/2024 | wrong value: 2024-08-02 (true 2024-08-02) |
| late_entry | SYNTHETIC_digitised_paper_records.xlsx | Activities | 243.0 | entry_date | 45 | 2025-10-09 00:00:00 | wrong value: 2025-10-09 (true 2025-10-09) |
| female_exceeds_total | SYNTHETIC_digitised_paper_records.xlsx | Activities | 303.0 | female | 9 | 25 | wrong value: 25.0 (true 9.0) |
| late_entry | SYNTHETIC_digitised_paper_records.xlsx | Activities | 353.0 | entry_date | 31 | 2026-06-04 00:00:00 | wrong value: 2026-06-04 (true 2026-06-04) |
| late_entry | SYNTHETIC_digitised_paper_records.xlsx | Activities | 367.0 | entry_date | 39 | 10/07/2026 | wrong value: 2026-07-10 (true 2026-07-10) |
| duplicate_beneficiary | SYNTHETIC_beneficiary_register_FO01.xlsx | Register | 410.0 | name | PER00488 | Niyitegeka Anastase Bosco Pierre | not matched to first registration |
| duplicate_beneficiary | SYNTHETIC_beneficiary_register_FO01.xlsx | Register | 416.0 | name | PER00179 | Twizeyimana Valens-Baptiste | not matched to first registration |
| duplicate_beneficiary | SYNTHETIC_beneficiary_register_FO02.xlsx | Register | 141.0 | surname | PER01379 | Uwamahoro | not matched to first registration |
| duplicate_beneficiary | SYNTHETIC_beneficiary_register_FO02.xlsx | Register | 256.0 | surname | PER01551 | Sibomana | not matched to first registration |
| duplicate_beneficiary | SYNTHETIC_beneficiary_register_FO04.xlsx | Register | 61.0 | name | PER00778 | Fabrice Patrick Nkurunziza | not matched to first registration |
| duplicate_beneficiary | SYNTHETIC_digitised_paper_records.xlsx | Registrations | 71.0 | name | PER00945 | BYIRINGIRO F. | not matched to first registration |
| duplicate_beneficiary | SYNTHETIC_digitised_paper_records.xlsx | Registrations | 113.0 | name | PER00615 | HARERIMANA JOSIANE MARIE | not matched to first registration |
| duplicate_beneficiary | SYNTHETIC_digitised_paper_records.xlsx | Registrations | 115.0 | name | PER01536 | Emmanuel-Damascene Mukeshimana | not matched to first registration |

... 1 more in score_injected_errors.csv.

## Final held-out: review queue and quarantine

Each flag has one of three levels (`flag_severity` in config/settings.yaml): **critical** = row quarantined until the source file is corrected; **warning** = row used, but goes to the MEAL officer's review queue; **info** = counted as a data-quality measure, no one acts on a row. A row with any critical flag is quarantined and not also counted in the review queue.

Flags by level: critical 562, warning 441, info 1,479.

### Review queue (warnings) per month

At 2 minutes a row (an assumption to check with the MEAL officer), the budget of 60 minutes a month allows 30 rows.

- Rows to review over 36 months: **368**; per month: average **10.2**, median 10, busiest month 22 (2024-12), about 20 minutes a month on average.
- Months over the one-hour budget: **0**.
- Rows with no month (e.g. donor records): 0.

What drives the review queue (a row can have more than one reason):

| code | rows | per_month |
|---|---|---|
| status_completed_but_late | 72 | 2.0 |
| sum_mismatch | 67 | 1.9 |
| district_unrecognised | 67 | 1.9 |
| possible_duplicate_person | 46 | 1.3 |
| missing_target | 36 | 1.0 |
| possible_duplicate_initials | 28 | 0.8 |
| district_legacy_name_ambiguous | 23 | 0.6 |
| district_province_mismatch | 23 | 0.6 |
| accuracy_outlier | 11 | 0.3 |

Rows to review by month:

| month | rows to review | minutes | quarantined |
|---|---|---|---|
| 2023-07 | 5 | 10 | 8 |
| 2023-08 | 4 | 8 | 6 |
| 2023-09 | 8 | 16 | 2 |
| 2023-10 | 5 | 10 | 4 |
| 2023-11 | 9 | 18 | 11 |
| 2023-12 | 6 | 12 | 8 |
| 2024-01 | 10 | 20 | 13 |
| 2024-02 | 5 | 10 | 21 |
| 2024-03 | 6 | 12 | 12 |
| 2024-04 | 12 | 24 | 17 |
| 2024-05 | 9 | 18 | 10 |
| 2024-06 | 15 | 30 | 7 |
| 2024-07 | 9 | 18 | 13 |
| 2024-08 | 9 | 18 | 13 |
| 2024-09 | 12 | 24 | 8 |
| 2024-10 | 14 | 28 | 5 |
| 2024-11 | 8 | 16 | 10 |
| 2024-12 | 22 | 44 | 11 |
| 2025-01 | 15 | 30 | 8 |
| 2025-02 | 10 | 20 | 10 |
| 2025-03 | 8 | 16 | 3 |
| 2025-04 | 5 | 10 | 12 |
| 2025-05 | 12 | 24 | 9 |
| 2025-06 | 9 | 18 | 8 |
| 2025-07 | 15 | 30 | 12 |
| 2025-08 | 11 | 22 | 15 |
| 2025-09 | 10 | 20 | 12 |
| 2025-10 | 13 | 26 | 17 |
| 2025-11 | 15 | 30 | 11 |
| 2025-12 | 15 | 30 | 16 |
| 2026-01 | 9 | 18 | 9 |
| 2026-02 | 11 | 22 | 8 |
| 2026-03 | 13 | 26 | 12 |
| 2026-04 | 10 | 20 | 15 |
| 2026-05 | 7 | 14 | 13 |
| 2026-06 | 12 | 24 | 15 |

### Quarantined rows (critical)

- Rows quarantined: **521** (per month: average 10.7, busiest 21). These are fixed in the source Excel file, not in the queue.

| code | rows |
|---|---|
| date_unreadable | 296 |
| missing_required | 132 |
| female_exceeds_total | 34 |
| negative_value | 28 |
| sex_unmapped | 14 |
| date_outside_project_window | 9 |
| entry_before_activity | 9 |
| district_unrecognised | 7 |
| impossible_age | 7 |
| impossible_household_size | 6 |
| probability_word | 4 |
| percent_over_100 | 4 |
| number_unreadable | 1 |
| village_unrecognised | 1 |

### Info-level measures (for the dashboard, not for review)

| metric | percent | numerator | denominator | note |
|---|---|---|---|---|
| Timeliness: activity records entered within the allowed days | 89.8 | 2309 | 2572 | Activities that took place, with a known day and an entry date; entered within late_entry_days (settings). Activities whose day is unknown cannot be judged and are left out. |
| Reporting completeness: expected monthly reports received | 92.1 | 384 | 417 | Every project, district and month for which an indicator report was due (indicator CC-04). |
| Activity dates with a known day | 91.0 | 2624 | 2884 | Activities with a date; the rest were typed as a month only. |
| Activities whose on-time status can be checked | 74.0 | 2278 | 3078 | Needs exact activity and planned dates (coverage of indicator CC-02). |
| National IDs typed as text (all 16 digits kept) | 83.7 | 1295 | 1548 | An ID stored as a number in Excel loses its last digit, which cannot be recovered. |
| People with no duplicate check pending | 95.6 | 1527 | 1598 | People (unique beneficiary keys) whose records are not waiting for a duplicate review. The people count on the dashboard includes the others, so it may be slightly too high until the review is done. |

## Reconciliation scoring (final held-out round)

The WASH-01 and AGR-01 reports are worked out from the same true data as the activity and register files, with discrepancies planted at known rates (decision log D132): two officers over-report 15 to 30% of the time, some months are under-reported by 20 to 50%, and a few figures have 1 to 5% rounding differences that should stay within the tolerance.

Scored at each indicator's comparison level (catalogue `derived.reconcile`, D162): WASH-01 by month (total), AGR-01 by quarter (total), by project and district. A gap needs more than the % tolerance AND at least 5 apart.

- Comparisons scored: 138; with a planted discrepancy: **52**; flagged: **34 (65.4%)**.
- Of these, **30** have a planted difference of at least 5; flagged: **29 (96.7%)**.

**Every flag raised (40), by what it caught:**

| What the flag caught | Flags |
|---|---|
| Planted discrepancies (over- or under-reporting) caught | 34 |
| Genuine data errors caught (an injected problem in the report or the records, e.g. an extra zero, quarantined or duplicate records) | 6 |
| Unexplained false alarms | 0 |

- Comparisons with only a planted rounding difference that stayed within the tolerance: 2 of 2.

| indicator_code | kind | outcome | comparisons |
|---|---|---|---|
| AGR-01 | none | correctly within tolerance | 20 |
| AGR-01 | none | flag explained: report-side data error | 2 |
| AGR-01 | planted | caught | 5 |
| AGR-01 | planted | missed | 1 |
| AGR-01 | planted | missed (smaller than the minimum) | 8 |
| WASH-01 | none | correctly within tolerance | 58 |
| WASH-01 | none | flag explained: records-side data issue | 4 |
| WASH-01 | planted | caught | 29 |
| WASH-01 | planted | missed (smaller than the minimum) | 9 |
| WASH-01 | rounding | correctly within tolerance | 2 |

### Known limitation: planted discrepancies too small to detect

Of 68 planted report rows (the grain the officer reports: project, district, month and, for AGR-01, sex), **39** differ from the truth by less than 5 on their own (AGR-01: 30, WASH-01: 9). On its own, none of these can be detected at any level; 13 of them sit in a comparison that was flagged because it adds up with other planted differences. Full list: `data/staging/score_reconciliation_too_small.csv`.

| indicator_code | project_id | district | period | sex | kind | true_value | actual_value | size | its comparison unit |
|---|---|---|---|---|---|---|---|---|---|
| WASH-01 | PRJ01 | Nyagatare | 2023-07-01 |  | over_report | 8.0 | 10.0 | 2.0 | missed (smaller than the minimum) |
| WASH-01 | PRJ01 | Nyagatare | 2023-10-01 |  | over_report | 15.0 | 18.0 | 3.0 | missed (smaller than the minimum) |
| WASH-01 | PRJ01 | Nyagatare | 2025-03-01 |  | over_report | 8.0 | 11.0 | 3.0 | missed (smaller than the minimum) |
| WASH-01 | PRJ01 | Kayonza | 2023-09-01 |  | over_report | 21.0 | 25.0 | 4.0 | missed (smaller than the minimum) |
| WASH-01 | PRJ01 | Kayonza | 2023-11-01 |  | over_report | 11.0 | 13.0 | 2.0 | missed (smaller than the minimum) |
| WASH-01 | PRJ01 | Kayonza | 2024-10-01 |  | over_report | 13.0 | 16.0 | 3.0 | missed (smaller than the minimum) |
| WASH-01 | PRJ01 | Kayonza | 2025-05-01 |  | over_report | 22.0 | 26.0 | 4.0 | missed (smaller than the minimum) |
| WASH-01 | PRJ01 | Kayonza | 2025-07-01 |  | over_report | 9.0 | 11.0 | 2.0 | missed (smaller than the minimum) |
| WASH-01 | PRJ01 | Kayonza | 2025-12-01 |  | over_report | 8.0 | 10.0 | 2.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Bugesera | 2024-05-01 | Female | under_report | 1.0 | 0.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Kirehe | 2023-10-01 | Female | under_report | 2.0 | 1.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Kirehe | 2025-04-01 | Male | under_report | 2.0 | 1.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Kirehe | 2026-04-01 | Female | under_report | 2.0 | 1.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2023-12-01 | Female | over_report | 1.0 | 2.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2023-12-01 | Male | over_report | 1.0 | 2.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2024-01-01 | Female | over_report | 3.0 | 4.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2024-01-01 | Male | over_report | 1.0 | 2.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2024-02-01 | Male | under_report | 2.0 | 1.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2024-04-01 | Female | over_report | 2.0 | 3.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2024-06-01 | Male | over_report | 2.0 | 3.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2024-10-01 | Female | over_report | 2.0 | 3.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2024-12-01 | Male | over_report | 3.0 | 4.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2025-03-01 | Female | over_report | 3.0 | 4.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2025-03-01 | Male | over_report | 3.0 | 4.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2025-04-01 | Female | over_report | 3.0 | 4.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2025-05-01 | Female | over_report | 1.0 | 2.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2025-05-01 | Male | over_report | 4.0 | 5.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2025-06-01 | Female | over_report | 3.0 | 4.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2025-08-01 | Male | over_report | 2.0 | 3.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2025-09-01 | Female | over_report | 3.0 | 4.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2025-10-01 | Female | over_report | 3.0 | 4.0 | 1.0 | missed |
| AGR-01 | PRJ04 | Rulindo | 2025-10-01 | Male | over_report | 3.0 | 4.0 | 1.0 | missed |
| AGR-01 | PRJ04 | Rulindo | 2025-11-01 | Female | over_report | 2.0 | 3.0 | 1.0 | missed |
| AGR-01 | PRJ04 | Rulindo | 2025-12-01 | Female | over_report | 4.0 | 6.0 | 2.0 | missed |
| AGR-01 | PRJ04 | Rulindo | 2026-02-01 | Female | over_report | 1.0 | 2.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2026-03-01 | Male | over_report | 3.0 | 4.0 | 1.0 | missed (smaller than the minimum) |
| AGR-01 | PRJ04 | Rulindo | 2026-04-01 | Female | over_report | 4.0 | 5.0 | 1.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2026-04-01 | Male | over_report | 4.0 | 6.0 | 2.0 | caught |
| AGR-01 | PRJ04 | Rulindo | 2026-06-01 | Female | over_report | 5.0 | 6.0 | 1.0 | caught |

## Changes made after seeing results

Every answer-key correction or scoring change made after results were seen, one line each. Details and evidence are in `docs/decision_log.md`. The frozen scorecards v1 and v2 were not rescored.

| Decision | What changed | Change |
|---|---|---|
| D54 | Answer key | 14 'completed but late' problems in the paper file relabelled undetectable (the paper form has no planned date); with 5 misspelt names, 19 problems left out of the genuine-error denominator. |
| D78 / D90 | Scorer | An age worked out from a date of birth is compared with the age from the TRUE date of birth and the true date of that registration (the key copied the first registration's age with +/-1). |
| D83 / D91 | Scorer | A blank age is a knock-on, not a miss, when the registration date on the same row carries an injected problem (all 7 cases checked by hand). |
| D136 | Scorer | A USD amount is judged against the amount the officer wrote, converted at the configured rate (the generator had rounded the USD figure before writing it). |
| D153 | Scoring rule | Reconciliation catch rate also reported for planted discrepancies at least the minimum difference (5) apart, after the minimum cut the raw catch rate to 30.3%; the raw figure is still reported. |
| D162 | Comparison level | Reconciliation compared at a level set per indicator (WASH-01 by month, AGR-01 by quarter, totals only), after AGR-01's monthly district figures proved mostly under the minimum. |

