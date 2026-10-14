# Decision log

Every assumption and design decision, with the date and the reason. Newest phase at the bottom.
Anything about the real ARDE/KUBAHO organisation is marked **to be confirmed with partner**.

## Phase 1: Scaffold and synthetic data (2026-10-14)

### Set-up and tooling

| # | Decision | Reason |
|---|---|---|
| D01 | Build in the project root folder (`Applied Project/`) rather than an `arde-meal-prototype/` subfolder. The brief is copied to `CLAUDE.md`. | Team instruction. The project was moved out of OneDrive first. |
| D02 | Use Python 3.12 in a local virtual environment (`.venv/`). All versions are pinned in `requirements.txt`. | 3.12 is installed on the team laptop and meets the "3.11+" rule. Pinning keeps every laptop identical. Note: pandas is 3.0, which is stricter about data types than older guides online. |
| D03 | Approved extra libraries: **PyYAML 6.0.3** (reads config files), **pyarrow 25.0.1** (Parquet export for Power BI), **rapidfuzz 3.14.6** (fuzzy duplicate matching), **fpdf2 2.8.9** (PDF donor report). | Approved by the team on 2026-10-14. All free and open source. |
| D04 | **kaleido is not used.** If the PDF report needs charts, they will be drawn with matplotlib (to be added to `requirements.txt` only when needed, in Phase 5). | Team instruction. matplotlib is not yet a requirement. |
| D05 | Git repository started. One commit at the end of each phase. | Team instruction. |
| D06 | Everything under `data/` is excluded from git, including the synthetic files. They can be rebuilt with `python src/generate_synthetic.py`, and the same seed always gives the same files. | Keeps real data out of git by default, so no one has to remember to. Teammates regenerate locally (about 6 seconds). |
| D07 | The pseudonymisation salt will live at `~/.arde_meal/pseudonymisation_salt.txt` (outside the repository). The path is set in `config/settings.yaml`. The file is created in Phase 2. | Brief Section 2 and team instruction: the salt must never be shared or committed. |

### Data model additions (approved 2026-10-14)

| # | Decision | Reason |
|---|---|---|
| D08 | All fact tables carry `source_file` and `source_row` (the Excel row number as seen in Excel). | Approved. Any number on the dashboard can be traced to its original row. |
| D09 | `fact_activity` gains `planned_date`, `entry_date` and `status` (planned, completed, delayed, cancelled). | Approved. Needed for the timeliness rule and the "% completed on time" indicator. |
| D10 | **Configurable default, to be confirmed with partner.** Status definitions used in the synthetic data: **completed** = done within 7 days of the planned date; **delayed** = done more than 7 days late, or still not done when the reporting window closed; **cancelled** = not done and no longer planned; **planned** = scheduled after the reporting window. The 7-day tolerance is `on_time_tolerance_days` in settings. | A clear rule was needed to generate data. **To be confirmed with partner** how they define "on time". |
| D11 | **Configurable default, to be confirmed with partner.** A late entry is one typed in more than 30 days after the activity (`late_entry_days`). An activity is on time if done within 7 days of its planned date (`on_time_tolerance_days`). | Placeholder thresholds, both in `config/settings.yaml`. The team confirmed on 2026-10-14 to keep them as defaults. |

### Privacy and recoding (approved 2026-10-14)

| # | Decision | Reason |
|---|---|---|
| D12 | Duplicate beneficiaries are found by fuzzy matching inside `ingest.py`, **before** hashing. Only a hashed cluster ID is stored. The matching threshold (`duplicate_matching.name_similarity_threshold`, starting value 88) is in settings so it can be tuned. | Approved. Names cannot be compared after they are hashed. |
| D13 | Individual donors are shown as "Individual donor #NNN". Organisations keep their names. | Approved. Individuals' names are personal data. |
| D14 | Sex coded as `1` is **not mapped**. It is flagged for review. The mapping is in `sex_mapping` in settings; Kinyarwanda `Gore` = female and `Gabo` = male are included. | Approved. Officers use `1` inconsistently, so guessing would introduce errors. |
| D15 | Donor contact names, emails and phone numbers are in the synthetic tracker so the pipeline can prove it drops them. Emails use the reserved `example.org` domain. | Privacy by design needs something to test against. |

### Synthetic world (assumptions accepted 2026-10-14)

| # | Decision | Reason |
|---|---|---|
| D16 | Reporting window: fiscal years FY2023/24 to FY2025/26 (1 July 2023 to 30 June 2026). Rwanda's fiscal year runs July to June. | Accepted assumption; gives the "3 years of monthly records" in the brief. |
| D17 | `as_of_date` is fixed at 2026-06-30 while on synthetic data, so deadlines and overdue actions look sensible whatever day the demo is run. Set it to `null` for real data. | Otherwise every synthetic deadline would be in the past by the time of the demo. |
| D18 | Two fictional programmes (WASH; Climate-Resilient Agriculture), five projects, 15 activity types, 8 real districts (Nyagatare, Kayonza, Bugesera, Kirehe, Nyamagabe, Huye, Rulindo, Karongi). All defined in `config/synthetic.yaml`. | Brief Section 6. The district choice is arbitrary. **To be confirmed with partner** where ARDE/KUBAHO actually works. |
| D19 | The 5 provinces and 30 districts are Rwanda's real ones (`config/reference/rwanda_admin.yaml`). Sector, cell and village names are invented from syllables and may coincide with real places by chance. | Brief Section 5 allows synthetic names below district. |
| D20 | Field staff are identified by codes only (FO01 to FO04, data-entry clerk DE01, owners ED01, PM01, PM02, MEAL01, FIN01). | Staff names are personal data too. |
| D21 | Donor names are fictional; countries are real, for realism. Six of the 25 donors are individuals. | Accepted assumption. |
| D22 | Beneficiary names combine common Rwandan given names and surnames at random. National IDs follow the real 16-digit pattern (1 + birth year + 7/8 for sex + digits) and phone numbers the 07X pattern, but every number is random. | Realism for the cleaning rules. No real person is described. |
| D23 | Each field officer has a different file layout (A to D) plus a "digitised paper records" file. Layout C uses Kinyarwanda headers (Akarere, Umurenge, Akagari, Umudugudu, Amazina, Igitsina, Imyaka, Indangamuntu, Ubumuga, Abagore, Abagabo, Bose, Igiteranyo) and values (Gore/Gabo, Yego/Oya). | Brief Section 6 asks for inconsistent layouts. **A Kinyarwanda speaker should check these terms.** |
| D24 | Activity records and monthly indicator reports are generated as separate sources, so their figures do not reconcile exactly. | This is realistic (two different forms filled in by different people). It is also a useful consistency check later. |
| D25 | A monthly indicator report is "expected" for each project, district and month in which at least one of that project's indicators is due (monthly, quarterly or semi-annual). Indicator targets are set once per fiscal year. | Needed to define reporting completeness (CC-04). **To be confirmed with partner** how reporting is actually scheduled. |
| D26 | The digitised paper file has no "planned date" column, so on-time completion cannot be worked out for paper-only activities. | Realistic: paper attendance sheets do not record the plan. |
| D27 | The indicator catalogue is a Phase 1 stub (codes, names, level, unit, frequency, disaggregation). Full definitions follow in Phase 4. | Accepted assumption. |
| D28 | Templates in `templates/` are generated from `config/templates.yaml`, with dropdown lists, date checks and text formatting for phone and ID columns. The donor template is a draft until Phase 6. | Staff can change a template without touching code. |

### The injected-error log and answer key

| # | Decision | Reason |
|---|---|---|
| D29 | The answer key goes in `data/ground_truth/`, separate from `data/raw/`. The pipeline must never read it. It holds the true values, where each record was written (file, sheet, row), and one log line per injected problem. | Lets Phase 2 measure exactly what was fixed, flagged or missed. |
| D30 | Every cell that differs from the standard template is logged, including an officer's habits (for example "F" instead of "Female", Excel serial dates). So the log has about 15,000 lines, most of them simple format fixes. | A habit is still a cleaning task the pipeline has to get right. |
| D31 | Each logged problem has an expected handling: **fix** (pipeline should correct it), **flag** (pipeline should send it for review), **fix_or_flag** (either is acceptable), or **undetectable** (cannot be caught without the paper form, e.g. a misspelt name). | Gives a fair target for the Phase 2 "95% fixed or flagged" check. |
| D32 | Error rates are set in `config/synthetic.yaml`. Rare problems on small groups (percentages over 100, percentages typed as fractions, amounts in USD) are injected at exact counts so they are never zero. | Coin-flips on about 50 rows sometimes gave zero, which would leave a rule untested. |

## Phase 2: Ingestion, cleaning and pseudonymisation (2026-10-14)

### Team decisions on the Phase 1 questions

| # | Decision | Reason |
|---|---|---|
| D33 | **Lineage is `source_file`, `source_sheet`, `source_row`** on every fact table (data model change, approved). | Several workbooks have more than one sheet (FO04's yearly sheets, the paper file), so file + row alone is ambiguous. |
| D34 | Phase 2 is scored without a single headline percentage: fixed/flagged/missed by error type; officer habits and genuine errors totalled separately; false corrections counted over every cleaned cell; duplicate precision and recall at several thresholds. The 95% target applies to genuine errors on their own; any type under 90% is marked. | Team instruction. One combined figure would be dominated by easy format fixes (about 92% of logged problems are habits). |
| D35 | `data/` stays out of git. A content fingerprint (SHA-256) is printed by the generator, stored in `config/synthetic.yaml` and `docs/synthetic_data.md`, and checked by `python src/generate_synthetic.py --verify` and by a test. | Team instruction. Excel stores the save time inside each file, so a plain file checksum would change on every run; the fingerprint covers cell contents only. |

### How ingestion works

| # | Decision | Reason |
|---|---|---|
| D36 | Column names are mapped in `config/source_mappings.yaml` (every spelling seen, including Kinyarwanda). The header row is found automatically: the row among the first 15 with the most known column names. Unrecognised columns are listed in `data/staging/sheet_inventory.csv`. | Real files can be added by editing one config file. Unrecognised columns are reported, never silently dropped. |
| D37 | A header that can mean two things (e.g. "ID": registration number in FO04, national ID in the paper file) takes whichever field is not already claimed by another column in that sheet. | Avoids a separate mapping per file. |
| D38 | Rows above the header, blank rows, and totals rows (a label such as TOTAL or IGITERANYO, or any `=SUM` formula) are removed and logged. | Brief Section 6 layouts. |
| D39 | All raw cells are staged as text first; converting them to dates and numbers happens in `clean.py`. | Nothing is lost or silently converted before cleaning. |
| D40 | Hashing uses HMAC-SHA256 with the salt in `~/.arde_meal/pseudonymisation_salt.txt` (created on first run; the pipeline refuses a salt inside the project folder). Keys: `BEN-...` per person, `REG-...` per registration row, `DON-...` per donor. | Salted, one-way and stable. **Back up the salt**: without it, new keys will not match old ones. |
| D41 | Names, phone numbers, national IDs, dates of birth, registration numbers and donor contact details are used in memory for matching, then dropped. Date of birth is first turned into age at registration. | Privacy by design (brief Section 2). The issue log records *that* a phone was fixed, never the phone itself. |

### Duplicate matching (approach approved in D12)

| # | Decision | Reason |
|---|---|---|
| D42 | Two registrations are one person if (1) their national IDs match on the first 15 digits, or (2) their names score at least 88 with rapidfuzz `token_sort_ratio` (word order ignored), they are in the same district and of the same sex, **and** nothing clearly disagrees: phones differing in more than 1 digit, different IDs, or ages more than 2 years apart. All limits are under `duplicate_matching` in settings. | 15 digits because Excel drops the 16th when an ID is stored as a number. Phones are not used on their own because family members often share one. |
| D43 | Threshold 88 kept. On the synthetic data the vetoes, not the threshold, give the precision: names alone at 88 give precision 0.51 (different people share common names); with vetoes, precision is 1.0 at every threshold from 80 to 92, and recall is 0.97 (0.985 at 80) before the ID rule, 1.0 with it. The synthetic data cannot separate 80 to 88. | 88 is the more cautious choice (fewer wrong merges if real records have near-identical names and missing phones). **To be re-checked on a hand-labelled sample of real registrations.** |
| D44 | The beneficiary key is the hash of the earliest registration's identity (its ID if it has one, else name + phone + district). | Stable when later duplicates are added. A new, *earlier* record joining a cluster would change the key; acceptable for a prototype, noted for Phase 8. |

### Cleaning rules

| # | Decision | Reason |
|---|---|---|
| D45 | Dates: day first (`12/03/2024` = 12 March). Whole numbers 20,000 to 80,000 in a date column are Excel serial numbers. `March 2024` is stored as 1 March and **flagged** "day unknown"; such rows are left out of on-time calculations. | Rwandan practice; a month-only date cannot be made exact. |
| D46 | Districts: words like "District" and "Akarere ka" are removed, then exact match, then the closest name if it scores 80 or more and clearly beats the second best. Otherwise flagged. If the district is missing or unrecognised but the village exists in only one district, the district is filled from the village (the original problem stays flagged). | Typos like `Nyagatre` are fixed; `Hyue` (score 75) is not guessed but is resolved through its village. |
| D47 | Villages are matched within the stated district (and sector, if it matches), accepting the closest spelling at 85 or more. | Fixes paper transcription slips without crossing districts. |
| D48 | Numbers: thousands separators, `RWF`/`Frw`, `people`, `ha` and `%` are removed; `O` becomes 0 and `l` becomes 1 only when the result is a number; `USD` amounts are converted at `usd_to_rwf` (1,450). Percentage indicators typed between 0 and 1 are read as fractions (0.72 = 72%). | Brief Section 6. The exchange rate is still to be confirmed (open item). |
| D49 | Sex `1`, probability words (`High`), and unknown districts, villages, projects and activities are **flagged and left empty**, never guessed. | Approved for sex (D14); the same principle is applied to every code list. |
| D50 | Row checks run now and flag (never delete): missing required values, negatives, female > total, female + male not equal to total, dates outside the project window (31-day grace), entry before activity, late entry (or "possibly late" when only the month is known), "completed" but late, "on time cannot be verified" (month-only dates), missing target, % over 100, actual > 3 x target, impossible age or household size, missing monthly reports. | Needed so Phase 2 can be scored on genuine errors. Phase 3 turns these flags into the formal `dq_results` rules, scores and quarantine. |
| D51 | Exact duplicate activity rows (identical in every cell within one sheet) are removed; the first copy is kept. | Brief Section 8 (uniqueness). |
| D52 | Late entry is measured only for activities that took place (a cancelled activity has no activity date). | Brief Section 8 defines timeliness from the activity date. The generator was corrected to match (D55). |

### Changes to the synthetic generator in Phase 2

| # | Decision | Reason |
|---|---|---|
| D53 | The error log gained a `field` column (the standard field name). | Lets the scorer compare each logged cell with the cleaned table. |
| D54 | 14 "completed but late" problems in the **paper file** are now marked `undetectable`, because the paper form has no planned date. Together with the 5 misspelt names, **19 problems are excluded** (not 5, as in Phase 1). | Honest denominator: nothing in the file can reveal them. The 3 similar cases in officer files, where both dates are month-only and in the same month, are still counted, and are missed. |
| D55 | The generator no longer blanks a value that another injected problem depends on (e.g. the activity date of a late entry), nor the date or total of a cancelled activity. | Those double injections hid the first problem, and a cancelled activity legitimately has no date or participants. |

## Phase 2 follow-up: checks requested before Phase 3 (2026-10-14)

### Were the generator fixes D52 to D55 really bug fixes?

Checked by rebuilding the generator as it was before D52, D54 and D55, generating that dataset, and running
the **current, unchanged** cleaner on it. Every difference between the two error logs was traced to its cause.
On the pre-fix data the same cleaner scored 97.5% on genuine errors (31 missed); on the fixed data, 99.8% (3 missed).

| Fix | What changed in the error log | Kind of generator bug | Had the cleaner been catching these? |
|---|---|---|---|
| D52 | 9 `late_entry` entries removed (7 cancelled activities, 2 delayed activities not yet done) | **Logged but not present**: none of the 9 activities has an activity date, and the brief measures timeliness from the activity date | No: all 9 were missed |
| D53 | No data change (a `field` column was added to the log) | Not applicable | Not applicable |
| D54 | 14 `status_completed_but_late` entries in the paper file relabelled `undetectable` | **Not a bug fix; a relabelling.** The errors are real, but the paper file has no planned date, so nothing in it can reveal them | No: all 14 were missed |
| D55 (part 1) | 1 `missing_required` removed (blank total on a cancelled activity) | **Logged but not present**: a cancelled activity legitimately has no participants | No: missed |
| D55 (part 2) | 4 `late_entry` entries kept, but their activity date is no longer blanked by a second injection | **Present but hidden**: the late entries were real, but the evidence (the activity date) had been removed | No before (missed), yes after (all 4 flagged) |
| D55 (side effect) | Changing which cells get blanked shifted the random choices for later cells: 11 entries moved and 12 appeared elsewhere (same kinds of error) | Not applicable | Caught in both versions (none missed) |

**Conclusion, stated plainly:** D52 and D55 part 1 removed errors that were logged but did not exist.
**The requested confirmation does not hold for D54 and D55 part 2.** D54 took 14 real errors that the cleaner
was missing out of the denominator (accepted by the team as undetectable). D55 part 2 changed the data so that
4 real errors the cleaner had been missing became detectable; the cleaner was not changed and now flags them.
The 3 misses that remain are real and still counted.

### Recommendations and rules agreed

| # | Decision | Reason |
|---|---|---|
| D56 | **Recommendation for the partner: the paper activity form should gain a "planned date" field.** | Without it, an activity written as "completed" that was actually late cannot be detected (14 cases in the main set, 10 in the held-out set), and on-time completion (indicator CC-02) cannot be calculated for paper-only activities. |
| D57 | **Template recommendation: ID and phone columns must be formatted as text.** `build_templates.py` already does this (number format `@` on every text column). An ID typed into a column formatted as a number keeps only 15 digits; **the 16th digit is lost and cannot be recovered** by the pipeline. Such IDs are flagged (info level), matched on their first 15 digits, and counted in the measure "National IDs typed as text" (81.9% in the main set). | Excel stores numbers with 15 significant digits. |
| D58 | **Three flag levels** (`flag_severity` in settings): **critical** = row quarantined (impossible values, missing required fields, codes that cannot be mapped, including districts and villages); **warning** = review queue (suspected duplicates, actual > 3x target, sum mismatches, district/province mismatch, "completed" but late); **info** = counted only (day unknown, ID stored as number, on-time not verifiable, late entry, missing monthly report). A flag not listed is treated as a warning, so nothing new is silently ignored. A district that is unrecognised but resolved from its village is downgraded from critical to warning. | Team instruction. `missing_target` is classed as critical (a required field), which quarantines indicator rows without a target; the team may prefer warning, since the actual value is still usable. |
| D59 | Duplicates have two levels: **certain** (every record in the group shares a national ID, or a phone number with names scoring 95 or more) are merged without review (logged, no flag); all other matches are **suspected** and go to the review queue. In the main set: 43 groups certain (86 rows), 23 suspected (46 rows). | Only the uncertain cases need a person's judgement. |
| D60 | Review-queue size is planned at 2 minutes a row (`review_minutes_per_row`; to be checked with the MEAL officer), against a budget of 60 minutes a month. **Main set: 240 rows over 36 months, 6.7 a month on average (about 13 minutes), busiest month 15; no month over budget. Held-out set: 9.4 a month, busiest 22; no month over budget.** Biggest drivers: sum mismatches (2.8 a month) and "completed" but late (2.0 a month). Quarantine: 286 rows (7.8 a month), mostly missing required values. | Team instruction (about one hour a month). |
| D61 | Info-level flags become dashboard measures: timeliness (88.8% of activity records entered within 30 days), dates with a known day (90.3%), on-time status checkable (74.1%), IDs typed as text (81.9%), reporting completeness (96.2%). Written to `clean_dq_info_metrics.parquet`. | Team instruction: measures, not rows to review. |
| D62 | The Excel templates are rebuilt only when `templates.yaml` or the values behind its dropdown lists change (a content stamp is kept in `templates/.build_stamp`). `python src/build_templates.py --force` always rebuilds. | Rebuilding every run gave the files a new save time, so git always showed them as changed. |

### Held-out test set

| # | Decision | Reason |
|---|---|---|
| D63 | A held-out set is generated with a different seed (7919) by `config/synthetic_holdout.yaml` into `data/holdout/`. It adds mess the cleaner was not designed for: a fifth officer (FO05) with unseen column names, dates such as `12 Mar 24`, `12 March 2024` and `12.03.2024`, unseen district spellings (r/l and k/g swaps, two slips, abbreviations, `Dist.` prefix, old names Butare, Gikongoro, Kibuye), harder duplicates (names swapped between columns, two letters missing, nicknames, half with no phone, most with no ID) and 61 **namesakes**: different people sharing a name, district and sex (half within 2 years of age, half without phone or ID). All of it is switched on only by that config: the main set's fingerprint is unchanged. | Team instruction: test on data the cleaner was not tuned on. |
| D64 | **Rule: the cleaner is not changed because of the held-out results until the team has reviewed them.** If the pipeline crashes on the held-out set, the scorer records the crash, sets aside the files whose header row could not be recognised, and re-runs; every record in those files counts as missed and their duplicate pairs stay in the recall denominator (conservative). Any later fix must be re-scored on the main set and on a **new** held-out seed, since this one will then have been seen. | Keeps the held-out result honest. |
| D65 | `data/holdout/manual/` holds hand-made messy files from teammates, with an `answer_key.csv` (template provided). The scorer picks them up automatically. Only the README and the template are committed. | Team instruction: mess that nobody on the cleaning side imagined. |

### Held-out findings (recorded, NOT yet fixed; awaiting team review)

1. **The unchanged pipeline crashes.** The FO05 activity file has no recognisable column names, so every field is empty, and `clean.py` fails on an empty officer code (`'NoneType' object has no attribute 'upper'`).
2. **Header detection can pick a data row.** In the FO05 register, a "No" answer in the disability column matches the alias "No" (registration number), so a data row was taken as the header.
3. **Unseen column names are reported but not mapped**, so the whole FO05 layout is lost (all 536 FO05 records missed: 163 activities, 92 registrations, 281 services). The fix for real data is a mapping entry in `source_mappings.yaml`, not code.
4. **New date styles are not read:** `12 Mar 24` and `12 March 2024` are flagged as unreadable (critical, so the row is quarantined) instead of being converted; `12.03.2024` works. An unreadable date also hides the row's late-entry and on-time checks.
5. **Silent wrong ages (the only false corrections, 5 cells):** when the registration date cannot be read, the age is worked out from the date of birth at the as-of date instead, making people 2 to 3 years too old with no flag.
6. **Namesakes:** 13 of 56 readable namesake pairs were wrongly merged (duplicate precision 0.83 at threshold 88, against 1.0 on the main set). They have no phone or ID and similar ages, so no veto applies.
7. **Harder duplicates:** recall 0.885 at 88 (0.92 at 80). Nicknames (`Jado` for Jean de Dieu) score below every threshold tried.
8. New district spellings (including old names and abbreviations) were all fixed or flagged outside FO05: 100%.
9. Pipeline run time was 145 seconds on 2026-10-14 (96 of them in scoring, which runs only on synthetic data). The cleaning hot spot is the village lookup, which filters a table once per row. A speed-up that leaves the output unchanged is proposed for Phase 3, verified against the scorecard.

## Held-out fixes and re-scoring (2026-10-14)

### Freezing the "before" figures

| # | Decision | Reason |
|---|---|---|
| D66 | The scorecard as it stood at commit `5087cad` is frozen as `docs/phase2_scorecard_v1_holdout1.md` (SHA-256 of its content, line endings normalised: `d5ebed8311873ba8272a19d4eae4a68ee47a5bd6e3a59f75debb594113e5af35`). A test fails if it changes. The live scorecard (`docs/phase2_cleaning_scorecard.md`) is now version 2. | Team instruction: these are the "before" figures for the report. |

### General fixes (not tailored to the held-out file)

| # | Decision | Reason |
|---|---|---|
| D67 | **Unrecognised layout (fix a):** a sheet whose header row cannot be found is **skipped, never guessed**. The pipeline prints `SKIPPED <file> / <sheet>: layout not recognised ... Column headers found: ... Add them to config/source_mappings.yaml`, carries on with the other files, writes the list to `data/staging/skipped_sheets.csv`, and logs a sheet-level critical issue (`sheet_skipped_unrecognised_layout`). The Phase 3 data-quality report will list skipped files. | A maintainer can fix it in config from the message alone; a guessed mapping could silently put numbers in the wrong columns. |
| D68 | **Header detection (fix b):** a row counts as the header only if at least 3 of its cells are known column names (`cleaning.header_min_matches`). | A single "No" in a data row matched the alias "No" (registration number) and was taken as the header. Every real layout so far has 5 or more matches. |
| D69 | **Dates with month names (fix c):** day-month-year text such as `12 Mar 24`, `12 March 2024`, `12-Mar-2024`, `12th March 2024` is read using the list `cleaning.date_text_formats` in settings (plus `ordinal_suffixes`). A 2-digit year up to `two_digit_year_pivot` (30) is 20xx, above it 19xx (`5 Jan 57` = 1957). Month-first styles (`Mar 12, 2024`) are deliberately **not** in the list. | Team instruction: rules in config. Month-first dates are a different convention; adding them is a decision for the partner. |
| D70 | **Ages (fix d):** age at registration is worked out from the date of birth only when **both** the date of birth and the registration date can be read. Otherwise the age is left empty and flagged `age_not_computable` (info level). There is no fallback to the as-of date. | The fallback made 5 people 2 to 3 years too old with no flag (the only false corrections in held-out 1). |
| D71 | **Duplicates (fix e):** similar names are merged only when a phone number (within 1 digit) or a national ID confirms the match (`duplicate_matching.merge_requires_phone_or_id`). A name-only match is **never merged**; both registrations get a `possible_duplicate_person` warning and keep separate keys until a person confirms them. Nicknames remain a known limitation; there is no nickname list. | Team instruction. Different people who share a name, with no phone or ID, were being merged (13 of 56 namesake pairs in held-out 1). Cost: some true duplicates are no longer merged automatically and wait in the review queue instead. |
| D72 | **Old district names (fix f):** `config/district_legacy_map.yaml`, marked **"To be confirmed with partner"**. No old name was found to be a clear one-to-one case: names such as Butare, Kibuye or Gikongoro meant both a town (now in one district) and a former province (now split over several), so the `one_to_one` list is empty. Ambiguous names are flagged for review (warning), never guessed; the pipeline uses a candidate district only when the row's village exists in exactly one of the candidates, and still sends the row for review. The candidate lists come from general knowledge and must be checked. | Team instruction. Guessing "Butare = Huye" would be wrong for any record from the other districts of the former province. |
| D73 | **Totals rows (fix g):** the 1 missed totals row in held-out 1 (12.5%, 1 of 8) was the `Sum` row inside the FO05 file, which the pipeline had set aside; all 7 totals rows in readable files were removed. The rule itself was therefore not at fault, but it was made more general anyway: the first filled cell may be a totals word followed by more text (`Total (RWF)`, `Totals:`, `Sub-total`), provided every other filled cell in the row is a number. A row with other text (e.g. a project called "Total Sanitation Campaign") is never dropped. | Team instruction to find the cause and fix the general rule. |
| D74 | **Missing target** is now a warning, not critical: the row is kept, and the indicator will show "no target set" instead of a % achieved (Phase 4). | Team decision. |
| D75 | **Robustness:** a column missing from a sheet now reaches the cleaner as empty (None), never as NaN; a missing officer code no longer crashes the cleaner. | Root cause of the held-out-1 crash. |

### Speed and separation of scoring

| # | Decision | Reason |
|---|---|---|
| D76 | Village and district-from-village lookups use precomputed dictionaries. All 22 staging tables were compared with the previous output: **identical** (commit `8224522`). Cleaning time fell from about 30 s to about 5 s. | Team instruction: speed up and prove the output is unchanged. |
| D77 | `python src/pipeline.py` now runs **production steps only** (ingest, clean, then validate, model and indicators as they are built). Synthetic generation, template building and scoring have their own commands; `python src/pipeline.py --score` runs scoring after the production run. | Team instruction: scoring is a test tool, not part of production. |

### Scoring corrections (the scorer, not the cleaner)

| # | Decision | Reason |
|---|---|---|
| D78 | When a sheet gives a date of birth, the cleaned age is now compared with the age worked out from the true date of birth and the true date **of that registration**. | The answer key's `age` for a second registration copies the first registration's age with a random +/-1. For one held-out-1 duplicate registered later, the cleaner's age (29) was right and the key (27) was wrong. The old comparison allowed +/-1, which hid this inconsistency on the main set. |

### Test sets

| # | Decision | Reason |
|---|---|---|
| D79 | Held-out 1 is scored twice: **as is** (FO05 skipped gracefully) and **with `config/mapping_overlays/holdout1_fo05.yaml`**, the column names a maintainer would add to `source_mappings.yaml` after reading the SKIPPED message. The overlay is not used in production. | Shows what a quick config fix (no code) achieves. |
| D80 | **Held-out 2** (`config/synthetic_holdout2.yaml`, seed 4243) was written after the fixes were designed and generated only after the code was final. Its mess is a different batch: a sixth officer (FO06) whose layout is only partly recognisable, unseen date styles (`Mar 12, 2024`, `12/Mar/2024`, `2024.03.12`, `12th March 2024`; `12/Mar/2024` and `12th March 2024` turned out to be covered by the general D69 rule, `Mar 12, 2024` and `2024.03.12` are not), unseen district spellings (`Nyaga tare`, `Huye, Southern Province`, vowel changes, `Akarere ka Kireh`, old names Umutara and Kibungo), and duplicates written with initials, hyphens or an extra given name. **It is the headline figure and must never be used to tune the cleaner**; any later fix needs a new seed. | Team instruction. |

### Results (scorecard v2, code at commit `2754c99`; held-out 2 generated afterwards)

| Measure | Main set | Held-out 1 as is | Held-out 1 + FO05 mapping | **Held-out 2 (headline)** |
|---|---|---|---|---|
| Genuine errors fixed or flagged | 99.8% | 95.2% (v1: 93.6%) | 98.9% | **92.9%** (96.1% without the FO06 file) |
| Officer habits | 100% | 92.8% (v1: 92.7%) | 100% | **87.5%** (100% without FO06) |
| Namesakes kept apart | n/a | 91.8% (v1: 70.5%) | 100% | **100%** |
| Error types below 90% | 0 | 5 | 1 | **6** |
| Clean values wrongly changed | 0 | 0 (v1: 5) | 0 | **0** (7 more cells left empty as a knock-on, see D82) |
| Duplicate precision / recall merged / merged or reviewed | 1.0 / 0.864 / 1.0 | 1.0 / 0.59 / 0.885 | 1.0 / 0.59 / 0.897 | **1.0 / 0.53 / 0.687** |
| Review queue per month (average / busiest) | 7.9 / 16 | 11.5 / 24 | 12.1 / 25 | **8.2 / 13** |
| Months over the one-hour budget | 0 | 0 | 0 | 0 |
| Rows quarantined (36 months) | 240 | 269 | 275 | **1,093** |
| Pipeline crashed | no | no (v1: yes) | no | no |

Production pipeline: 11.6 s (ingest 5.5 s, clean 4.4 s). Scoring all four sets: about 6 minutes, separate from production.

### Held-out 2 findings (recorded, NOT fixed; awaiting team review)

| # | Finding |
|---|---|
| D81 | **A partly recognised layout passes silently.** FO06's activity sheet has 5 known column names (District, Sector, Cell, Village, Total), so it is read rather than skipped, but the activity date, activity, project, female/male, cost and status columns are unknown. Result: 364 activity rows quarantined for missing required values, and no message beyond `sheet_inventory.csv`. FO06's register is read, but its registration number is unknown, so its Services sheet (also skipped) cannot be linked. This file alone pulls genuine errors from 96.1% to 92.9% and habits from 100% to 87.5%. Possible general rule: print the same loud message for a sheet whose required fields are unmapped (and perhaps skip it). |
| D82 | **Month-first and year-first dotted dates are not read** (`Mar 12, 2024`, `2024.03.12`): 496 rows quarantined as unreadable. Month-first was left out on purpose (D69); `2024.03.12` is unambiguous and could be added to `date_text_formats`. `12/Mar/2024` and `12th March 2024` were read correctly by the new config rule. Knock-on: on 7 FO02 registrations the registration date was unreadable, so age was correctly left empty and flagged (D70); the scorer counts these 7 as knock-ons, not wrong changes (D83). |
| D83 | Scoring correction: an age worked out from the date of birth depends on the registration date, so a blank age on a row whose registration date carries an injected problem is classed as a knock-on. All 7 cases were checked by hand: every one had an unreadable registration date. |
| D84 | **Duplicates written with initials or an extra given name** (`J. C. Uwimana`) are mostly not found: recall merged-or-reviewed 0.687 (26 pairs missed). Precision stays 1.0 and every namesake pair was kept apart. Like nicknames, initials are a known limitation unless the team wants an initials rule. |
| D85 | Late entries 83% and sum mismatches 89.5% are knock-ons of D81 and D82 (the dates or female/male columns could not be read, so the checks could not run). |
| D86 | The monthly review queue stays within one hour on every set (busiest month 25 rows, about 50 minutes). Quarantine on held-out 2 averages about 30 rows a month, driven by D81 and D82. |

## Round 4: last changes to the cleaner on synthetic data (2026-10-14)

**Team decision: the cleaner is not tuned on synthetic data after this round.** The next changes to it should come from real partner files or from the final held-out round in Phase 7 (D94).

| # | Decision | Reason |
|---|---|---|
| D87 | **No partial reads.** Each kind of sheet has required fields (`required_fields` in `config/source_mappings.yaml`, e.g. an activity sheet needs date, activity, district, village, status and total). If any is unmapped, the whole sheet is **skipped** with the same SKIPPED message as an unreadable layout, naming the missing required fields and the unrecognised headers. Skipped sheets are listed in `skipped_sheets.csv` and at the top of the data-quality report. Main set: no change (every sheet has its required fields). Held-out 2: FO06's activity sheet and register are now skipped instead of read partly. | Team instruction (finding D81). A sheet read without its dates or activity names produced 364 quarantined rows and hid injected problems. |
| D88 | **`2024.03.12` (year.month.day)** added to `cleaning.date_text_formats`. Month-first dates (`Mar 12, 2024`) stay out and are now a question for the partner. | Team instruction (finding D82). Year-first with a 4-digit year is unambiguous; month-first is not the Rwandan convention and could be confused with day-first. |
| D89 | **Initials rule:** a name with initials (`J. C. Uwimana`) is compared with full names in the same district (`Jean Claude Uwimana`). It becomes a review candidate (`possible_duplicate_initials`, warning) when every full word (the surname) scores at least 90, the initials match the first letters of the other given names, both ages are known and within 2 years, and sex, phone and ID do not disagree. **Never merged.** Settings: `duplicate_matching.initials_rule`, `initials_surname_min_score`. **Main-set review queue: no change** (287 review rows before and after, 7.9 a month on average, busiest month 16), because the main set contains no initials; all cleaned tables were identical before and after this round. On held-out 2 (seen data) recall of true duplicate pairs, merged or sent to review, rose from 0.687 to 0.855. | Team instruction (finding D84). |

### Scorer corrections: both were found AFTER seeing results

Neither changed the cleaner. Both changed only how the scorer judges a cell, and both make the score more lenient in one specific, checked situation, so they are recorded with their evidence.

| # | Correction | Evidence | Effect |
|---|---|---|---|
| D90 | (Also D78.) **Age from a date of birth is compared with the age worked out from the true date of birth and the true date of that registration**, instead of the answer key's `age` column with a tolerance of +/-1. Found while reviewing the held-out-1 results after the round-3 fixes. | Held-out 1, `SYNTHETIC_beneficiary_register_FO02.xlsx`, Register row 279 (registration FO02-0275, person PER00321, a second registration). Date of birth 1996-02-08, registered 2025-06-12: true age at that registration 29. The cleaner gave 29. The answer key said 27, because the generator copies the first registration's age (28) and adds a random -1. The generator's age for second registrations is therefore not a reliable answer when a sheet gives a date of birth. The cleaner was right. | Held-out 1 false corrections 1 to 0. Main set: no change. |
| D91 | (Also D83.) **A blank age is classed as a knock-on when the registration date on the same row carries an injected problem**, because an age at registration cannot be worked out without that date (rule D70). Found after seeing the held-out-2 results (before scorecard v2 was written, so v2 already includes it). | Held-out 2, `SYNTHETIC_beneficiary_register_FO02.xlsx`, Register rows 16, 26, 33, 78, 134, 144 and 170. Every one has an injected registration date in an unreadable style (`2023.09.17`, `Nov 11, 2023`, `Dec 8, 2023`, `Jul 30, 2024`, `2025.07.14`, `2025.09.18`, `Jan 19, 2026`). The cleaner left the age empty and flagged `age_not_computable`, as designed. Checked row by row by hand. | Held-out 2 "clean values wrongly changed" 7 to 0; the 7 cells are still shown in the scorecard as knock-ons. The 92.9% headline is not affected (false corrections are reported separately). |

### Reporting

| # | Decision | Reason |
|---|---|---|
| D92 | Scorecard v2 is frozen as `docs/phase2_scorecard_v2_holdout2.md` (from commit `95c2b03`; content SHA-256 `5ec05b29821f786303b0e6be049dce3030483d8118266b4c883be2baa87ac3d4`, guarded by a test). **The headline stays held-out 2 as first scored: genuine errors 92.9%.** The live scorecard (v3) copies that column from v2, re-scores the main set, and adds two clearly labelled recovery runs on held-out 2, which is now seen data: after this round's fixes alone, genuine errors **87.5%** (lower, because FO06's sheets are now skipped and all their records count as missed; quarantined rows fall from 1,093 to 449); and with the FO06 column names added in config (`config/mapping_overlays/holdout2_fo06.yaml`, no code), **96.6%**, officer habits 100%. | Team instruction: do not replace the headline; show what fix 1 plus a config mapping recovers. |
| D93 | `python src/score_cleaning.py` now re-scores only the main set and the held-out-2 recovery runs; `--all` re-scores every set. | Team instruction: no new held-out round now. |
| D94 | **Planned for Phase 7: one final held-out round.** A new config (`synthetic_holdout3.yaml`, new seed), written and committed before it is generated, plus every hand-made file in `data/holdout/manual/` with its answer key. Scored once with `python src/score_cleaning.py --all` on the code as it stands then, and reported next to v1, v2 and v3 without further tuning. | Team instruction. |

## Phase 3: Validation and data model (2026-10-14)

### Data-quality rules and quarantine

| # | Decision | Reason |
|---|---|---|
| D95 | The checks run where the data is read and cleaned (`ingest.py`, `clean.py`), each raising a flag with a severity. `validate.py` groups the flags into 14 rules in `config/dq_rules.yaml`, covering the six dimensions of brief Section 8, and scores them: **rule score** = % of the records it applies to that do not break it; **dimension score** = average of its rules; **overall** = average of the six dimensions. | Checking each value once, at the moment it is cleaned, avoids two copies of every rule drifting apart. The grouping and the formula are in config and in the report, so the MEAL officer can see how a score is made. |
| D96 | Plain pandas checks are used rather than pandera. | The brief allows either. The rules already run inside the cleaner; a second schema layer would duplicate them, and pandas checks are easier for a maintainer to read. |
| D97 | **Quarantine** = every row with at least one critical flag. Quarantined rows are **not** in the fact tables; they are kept in the `quarantine` table with their reasons and details. Rows with warnings only are used in results and listed in `review_queue`. A test confirms that every cleaned row is either in a fact table or in quarantine (nothing silently dropped). | Brief Section 8; severity levels agreed in D58. |
| D98 | Skipped sheets are the **first section** of `docs/data_quality_report.md`, are a completeness rule (COM-01), and are stored in the `skipped_sheets` table. | Team instruction: show skipped sheets prominently. A skipped sheet removes every one of its records from the results. |
| D99 | Data quality by field officer covers activity records (officer column) and indicator reports (`entered_by`). Registers and service lists have no officer column, so they are scored by source file only. | No invented officer link. **To be confirmed with partner** whether registers can carry an officer code. |

### Star schema

| # | Decision | Reason |
|---|---|---|
| D100 | The fact tables have exactly the columns in brief Section 5 plus the approved additions (`planned_date`, `entry_date`, `status` on `fact_activity`; `source_sheet` on every fact). **Not added** (would change the data model, so not done without asking): a quality flag or field-officer column on `fact_activity`. The data-quality tables hold that information and can be joined on the lineage columns. | Brief Section 11: ask before changing the data model. |
| D101 | `dim_location` holds one row per village **plus one row per district** (`DIST-<district>`, with no sector, cell or village), because monthly indicator reports are at district level. These are extra rows, not extra columns. | `fact_indicator_result` needs a location_id; the reports do not name a village. |
| D102 | `dim_programme.funder_id` holds the funder's `donor_key`, so it links to `dim_donor` (the donor ID itself is not carried into the warehouse). `dim_indicator.indicator_id` is a number given in catalogue order; `owner` and `data_source` stay mostly empty until the full catalogue in Phase 4. | Keeps every link inside the warehouse. |
| D103 | `dim_beneficiary` takes each person's details from their earliest registration that was **not** quarantined. A person whose only registrations were quarantined still gets a row (key only, details empty), so that service records link. | Avoids using details from a row that failed a critical check, without breaking links. |
| D104 | `fact_indicator_result.quality_flag` is `ok`, or the row's warnings in words (e.g. `no target set`, `actual more than 3 x target`). A missing target keeps the row (D74). | Lets the Indicators page show "no target set" instead of a % achieved. |
| D105 | Before saving, `model.py` checks that keys are unique, every link points to an existing row, no personal-data column exists, and every fact row has its lineage. If any check fails it stops with a list of problems and **saves nothing** (it builds a temporary file and only replaces the warehouse when all checks pass). | A broken model must never reach the dashboard. |

### Exports, data dictionary, pipeline

| # | Decision | Reason |
|---|---|---|
| D106 | Every warehouse table is exported to `data/exports/` as CSV (UTF-8 with a byte-order mark, so Excel shows accented characters correctly) and Parquet (for Power BI), plus `model_relationships.csv` listing every link (many-to-one) for setting up the Power BI model. | Brief Section 2: Power BI compatibility. The Power BI guide follows in Phase 7. |
| D107 | `docs/data_dictionary.md` is generated from the real warehouse schema (column types, row counts) and the descriptions in `config/data_dictionary.yaml`. The build fails if a table has a column that is not described, or a described column is missing. | The dictionary cannot fall out of date. |
| D108 | `python src/pipeline.py` runs ingest, clean, validate and model in one command: **15.5 seconds** on the main set (target under 60). | Brief Phase 3. |
| D109 | Main-set results: overall data-quality score **96.1%** (completeness 96.8, validity 99.5, consistency 96.9, uniqueness 97.6, timeliness 86.5, accuracy 99.2); **240 rows quarantined** (167 activities, 64 registrations, 5 indicator results, 4 opportunities); **287 rows in the review queue**; no sheets skipped. Warehouse: 2,727 activity facts, 4,475 service facts, 586 indicator results, 26 opportunities, 1,509 people. | Recorded for the report. |

## Open items to confirm with ARDE/KUBAHO and supervisors (brief Section 15)

These do not block the prototype.

- [ ] Which programme is the pilot (`pilot.programme_ids` in settings)
- [ ] Actual data sources, formats and record counts
- [ ] Data access authorisation and confidentiality terms
- [ ] Preferred dashboard tool (Streamlit, Power BI, or both)
- [ ] Whether the donor module is part of the assessed scope
- [ ] Where the prototype will be hosted after handover, and who maintains it
- [ ] Obligations under Rwanda's Law No. 058/2021 on personal data protection (with the partner and the university)
- [ ] Districts where ARDE/KUBAHO works (D18)
- [ ] Definitions of "on time" (7 days) and "late entry" (30 days), kept as configurable defaults (D10, D11)
- [ ] Duplicate-matching threshold, checked on a hand-labelled sample of real registrations (D43)
- [ ] Kinyarwanda column names and values used in the mappings (D23, D36)
- [ ] Add a planned-date field to the paper activity form (D56)
- [ ] Old district names and their candidate districts (D72, config/district_legacy_map.yaml)
- [ ] **Partner question:** do staff ever write dates month first ("Mar 12, 2024")? They are not read until confirmed (D69, D82, D88)
- [ ] Minutes per review-queue row, checked with the MEAL officer (D60)
- [ ] Whether beneficiary registers can carry a field-officer code (D99)
- [ ] Reporting schedule for indicator reports (D25)
- [ ] USD to RWF exchange rate to use in reports (`currency.usd_to_rwf`, now 1,450)
