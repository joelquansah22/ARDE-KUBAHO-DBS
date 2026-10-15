# Fresh-install test

**Purpose:** prove that someone who did not build the prototype can set it up on a different Windows laptop using
**only the README**, and find every place where the README is unclear. The README is then corrected from the
results (not before).

**Who:** a teammate who has not set up this project before (or has deleted their copy and their Python
environment). **Where:** a Windows laptop that has never had the project on it. **Time:** about 45 minutes.

## Rules for the tester

1. Use **only `README.md`** (the version on GitHub or in the zip you are given). Do not ask the team, do not
   search the code, do not use other docs unless the README sends you there.
2. Start a stopwatch at the start of each step and write the time when it is done.
3. **Every time you hesitate, guess, get an error or have to search the internet, write it down**, with the exact
   error message (a photo of the screen is fine) and what you did to get past it.
4. If you are stuck for more than 10 minutes on one step, write "BLOCKED", ask the team for the smallest hint,
   write the hint down, and carry on.

## Before you start

| Item | Answer |
|---|---|
| Tester (initials) | |
| Date | |
| Laptop (make, Windows version, RAM) | |
| Python already installed? Which version? | |
| Internet speed (fast / slow / very slow) | |
| How you got the project (git clone / zip) | |

## Steps

| # | Step (as the README describes it) | Start | End | Minutes | Got stuck? (yes / no) | What happened, exact errors, how you solved it |
|---|---|---|---|---|---|---|
| 1 | Get the project folder onto the laptop | | | | | |
| 2 | Install Python (if needed), with "Add Python to PATH" | | | | | |
| 3 | Open a command window in the project folder | | | | | |
| 4 | Create the Python environment (`python -m venv .venv`) | | | | | |
| 5 | Activate it and install the packages (`pip install -r requirements.txt`) | | | | | |
| 6 | Start the dashboard (double-click `run_dashboard.bat`): demonstration files are created and the figures prepared on the first run | | | | | |
| 7 | The Executive summary opens in the browser | | | | | |
| 8 | Generate a donor report (Programme overview, PRJ01, FY2025/26 Q4) and open the PDF | | | | | |
| 9 | Run the tests (`python -m pytest`) | | | | | |
| 10 | Find where the secret "salt" file was created, and back it up as the README says | | | | | |

**Total minutes:** ______

## Checks at the end (tick)

- [ ] The synthetic-data banner shows on every page
- [ ] The donor report PDF is one page and opens
- [ ] `python -m pytest` ends with "passed" and no "failed"
- [ ] The salt file exists **outside** the project folder (in your user folder, `.arde_meal`)
- [ ] Nothing in the project folder contains names, phone numbers or ID numbers of real people

## Questions for the tester

1. Which step took longest, and why?
2. Which instruction did you have to read more than once?
3. What would an ARDE/KUBAHO staff member with Excel skills (and no Python) find hardest?
4. Anything the README should say that it does not?

## For the team, after the test

- [ ] Fix every README problem found; note each fix in `docs/decision_log.md` with the tester's step number.
- [ ] If any step was BLOCKED, repeat the test with a second tester after the fix.
- [ ] Copy the total time and the number of stuck points into `docs/evaluation_summary.md` (sustainability).

*Status on 15 October 2026: not yet done. Waiting for a teammate and a second laptop.*
