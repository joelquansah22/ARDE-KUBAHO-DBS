# Evaluation protocol

How to collect the human evidence for the evaluation: the **timed reporting task** (manual Excel versus the
prototype) and the **usability test** (tasks plus the System Usability Scale, SUS). The fresh-install test is in
`docs/fresh_install_test.md`. Results are typed into the templates in `evaluation/` and summarised by
`python evaluation/summarise.py`.

> Everything runs on **synthetic data**. Participants must be told that no real ARDE/KUBAHO records are shown.

---

## 1. Consent note (read aloud, then ask for a yes)

> Thank you for helping us test a student prototype. We are testing the **tool, not you**: if something is hard,
> that is a problem with the tool. The session takes about 45 minutes. We will time some tasks, note where you get
> stuck and ask you to fill in a 10-question form. We will not record your name in our results: you will be
> "P1", "P2"... and we only note your role (for example programme manager) and whether you work at ARDE/KUBAHO or
> are a student playing an ARDE/KUBAHO role. We will not record audio or video. The data you will see is invented.
> You can stop at any time without giving a reason, and ask us to delete your results until we hand in the report
> on [date]. Results will appear only as numbers and anonymous comments in our ASU capstone report and in a summary
> for ARDE/KUBAHO. Do you agree to take part?

Record "consent: yes" and the date in the results sheets. **To be confirmed with the university** whether its
human-subjects rules need more (for example a signed form) before testing with ARDE/KUBAHO staff.

---

## 2. Timed reporting task: manual baseline versus the prototype

**The task:** produce the one-page quarterly progress summary for **one project and one quarter**, with exactly
the content of the prototype's donor report:

1. People reached in the quarter (different registered people, not attendance)
2. Activities completed in the quarter
3. Activity spending in the quarter (RWF)
4. Spending to date against the project budget (RWF and %), and whether the project is over budget
5. For each of the project's indicators: target, actual, % achieved and status (on track at 90% or more, at risk
   70 to 89%, off track below 70%)
6. A note on data problems found (for example reports that disagree with the records)

Use the **same project and quarter for both methods**. Suggested: PRJ01 Community Water Access, FY2025/26 Q4 (it
has reported indicators with targets, so item 5 is a real calculation); for a second round, PRJ03 Hygiene Behaviour
Change, FY2025/26 Q4 (it is over budget, which tests item 4, but has no reported indicators). Before the session, run `python evaluation/summarise.py --reference PRJ01
"FY2025/26 Q4"` to write the reference answers (`evaluation/reference_answers_*.csv`), and keep them away from
the participant.

**Order:** to be fair, half the participants do the manual method first and half the prototype first (write the
order in the sheet). Use a different project for the second method only if the participant remembers the first
answers; record it.

### 2a. Manual baseline (Excel, from the raw files)

Give the participant a laptop with Excel and a copy of the **raw messy files** (`data/raw/SYNTHETIC_*.xlsx`), and
a blank Excel or Word page for the summary. No dashboard. They may use any Excel features (filters, pivot tables,
formulas). Start the stopwatch at "go" and record the time at the end of each step:

| Step | What the participant does | Ends when |
|---|---|---|
| M1 Find the files | Opens the activity, register and indicator-report files for the project | All needed files are open |
| M2 Gather the figures | Filters or copies the project's rows for the quarter, from every officer's file | The rows are together |
| M3 Clean | Fixes or leaves out what they judge wrong (dates, district spellings, duplicates, numbers as text) | They say they are done cleaning |
| M4 Calculate | People, activities, spending, spending to date, % achieved, statuses | All figures are filled in |
| M5 Write and check | Writes the one-page summary and checks it | They say the summary is final |

### 2b. Prototype

Start with the laptop on, the dashboard **not** open, and the pipeline already run (the figures prepared).

| Step | What the participant does | Ends when |
|---|---|---|
| P1 Open the dashboard | Double-clicks `run_dashboard.bat` | The Executive summary is on screen |
| P2 Choose | Goes to Programme overview; chooses the project and quarter in "Generate donor report" | Both are chosen |
| P3 Generate | Clicks "Generate donor report" | "Report ready" appears (the machine time is logged automatically in `evaluation/report_generation_log.csv`) |
| P4 Download | Downloads the PDF (and Excel if they wish) | The file is saved |
| P5 Check | Opens the PDF and checks it is right and complete for a donor | They say it is final |

### 2c. What to record (`evaluation/timing_record_sheet.csv`, one line per step)

Participant, role, participant type (ARDE staff / student role-play), method (manual / prototype), order (first /
second), project, quarter, step, start and end clock times (hh:mm:ss), minutes, and notes (where they got stuck,
help given). After both methods, compare each figure with the reference answers and record in the `M5` and `P5`
lines: **figures wrong** (out of the total number of figures) and **figures missing**.

**Rules:** do not help unless the participant is stuck for 3 minutes; then give one hint and write it down. Stop
the manual method at 90 minutes and record "not finished" with the figures done so far.

---

## 3. Usability test

**Participants:** 3 to 5, covering the three roles: executive director, programme manager, MEAL officer. They may
be **ARDE/KUBAHO staff** or **students role-playing ARDE/KUBAHO staff**: record which in every sheet (the results
are reported separately, and student results do not stand in for staff results).

**Set-up:** a laptop at 1366 x 768 if possible, the dashboard open on the Executive summary, all filters at their
defaults, the synthetic data. One facilitator reads the tasks; one note-taker times them and notes problems.
Ask the participant to think aloud.

### 3a. Tasks (read each one aloud; do not show the menu names)

| # | Role | Task | Correct answer (for the note-taker) |
|---|---|---|---|
| T1 | Executive director | "How many indicators are off track this quarter, and which?" | Executive summary, "Off track" tile and list |
| T2 | Executive director | "Is any project over budget? By how much?" | PRJ03, over budget by about RWF 14.7m (10%) |
| T3 | Executive director | "How much funding do we expect from open opportunities, weighted by their chances, and how many deadlines are in the next 90 days?" | Weighted open pipeline tile; deadlines tile |
| T4 | Programme manager | "For the Community Water Access project, how many different people were reached in FY2025/26, and what share were women?" | Programme overview with project and date filters |
| T5 | Programme manager | "Produce the quarterly donor report for the Climate-Smart Farmer Field Schools project, FY2025/26 Q4, as a PDF." | Generate donor report, download the PDF |
| T6 | Programme manager | "Which district reached the most people?" | Geography |
| T7 | MEAL officer | "How many records are quarantined, what is the most common reason, and download the review list for officer FO02." | Data quality, work lists, filter FO02, download |
| T8 | MEAL officer | "Find one month where the water report disagrees with the records, and the row in the Excel file you would check." | Indicators, reconciliation, "Report to check" |

Every participant does every task (whatever their role); the role column says whose question it is. For each
task record in `evaluation/task_results_template.csv`: completed (yes / with help / no), time in seconds, errors
(wrong page, wrong answer), help given, and comments.

### 3b. System Usability Scale (after the tasks)

Hand the participant the ten statements below on paper. Each is answered 1 to 5 (1 = strongly disagree,
5 = strongly agree). Type the answers into `evaluation/sus_results_template.csv`. The standard SUS wording (Brooke,
1996) is used, with "system" meaning the dashboard:

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

**Scoring** (done by `evaluation/summarise.py`): odd items score (answer - 1), even items score (5 - answer);
the sum times 2.5 gives 0 to 100. Around 68 is the commonly quoted average; report the mean, the range and each
participant, and never a SUS score from fewer than 3 participants as if it were general.

### 3c. Close the session

Ask: "What was the most useful thing? What was the most confusing? What is missing for your work?" Write the
answers in the comments column.

---

## 4. After the sessions

1. Run `python evaluation/summarise.py`. It writes `evaluation/evaluation_results.md`: SUS scores (each
   participant, mean, by participant type), task completion and times, manual versus prototype times by step, the
   figures wrong, and the machine time of every generated report.
2. Copy the headline numbers into `docs/evaluation_summary.md` (the "Pending human testing" rows).
3. Do not delete the sheets: they are the evidence. They contain no names.
