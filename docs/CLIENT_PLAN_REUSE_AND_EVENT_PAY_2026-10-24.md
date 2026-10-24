# Client plans, event pay and agreement actions — 24 October 2026

## Final behavior

- Agreement headers group Save agreement, Save draft and Import agreement. A draft may omit crew and scope; its client, name, dates and billing model are still required. Financially used agreements cannot become drafts.
- Add site lists up to 20 previous site plans for the chosen client, ordered by the source agreement's latest update. Choose whether to copy crew or use only the site name. Copying retains categories, counts, location and relative dates, maps prices to the target agreement's currency, and creates editable rows without copying worker assignments or payroll. Duplicate sites and plans exceeding the new date interval have corrective messages.
- Daily agreements show only client rates. Fixed agreements show no per-worker prices. Worker pay belongs to the event, with independently stored Daily and Monthly amounts and a chosen basis for each allocation. Monthly amount / 30, rounded to two decimals, is the full-day attendance rate; half days earn half. This retains the existing attendance-based payroll policy, rather than posting a salary for unworked days.
- Choose workers shows pay controls only for selected new workers, alongside client pricing. Missing or nonpositive pay has inline feedback. Edit pay changes unused allocations; saved attendance locks pay basis, amount and daily rate. Profile defaults are preserved when an event uses another amount.
- Daily pay above the client rate needs explicit confirmation. Fixed pricing compares the inclusive dated cost of all allocations against the fixed agreement value. These projections do not post wages or change actual revenue/profit. The server checks again under the project lock, including bulk/automatic allocations and native assignment saves.
- An unused event can remove its agreement or choose another active agreement for the same client/company. A replacement supplies its own sites, crew and dates. Unlinked events display Agreement required and are excluded from project finances. Operational, payroll, reservation and financial history blocks detachment/reassignment. Deletion review explains the financial exclusion and directs the user to the event's agreement controls.
- Agreement imports use client prices and include conditions separated by `|`. Event templates use category and agreement currency instead of wages. Worker templates include both pay rates and leave/loan settings. Warehouse templates include Owned/Rented and status. Current stock count templates use automatic timestamps and retained unit values; older dated/value templates remain supported. Import guidance uses an info button and keeps preview/confirmation before posting.

## Data preservation

The schema adds Employee daily/monthly default rates and assignment pay basis/amount/confirmation fields. The installer copies an existing legacy salary only into its matching empty default-rate field once. Existing wages, attendance, invoices, payments and loans are retained. Legacy agreement wages remain internal for old records/API compatibility; editing client requirements does not replace event worker pay.

Pre-update source: `89f2226`. The working site's database, configuration and public/private files were backed up at `20261024_144937` under its private backups directory before the final installer runs. Backups remain private and are not committed to Git.

## Verification

Evidence is recorded in `.local/qa/planning-full-regression.log`, `.local/qa/planning-browser-20261024.json`, and the component/calendar/worker browser logs. All database cases use rollback-only QA transactions; browser fixtures use disposable QA companies and require restoration. No customer business records, posted financial transactions or outgoing messages are used as tests.


Final results: **258 distinct database regression cases passed** across the full run and affected-suite reruns. The initial full run's 11 errors were outdated test writers using retired template headers; preserving their original headers verified old-file compatibility. The paused-event test was corrected to inspect its own project rather than count unrelated fixture attendance. Latest results for every case are retained in `.local/qa/planning-final-validation-20261024.json`.

Browser verification passed: **13 new planning checks**, **10 calendar checks**, **26 input/component checks**, and the worker salary/activation/leave/loan/event-assignment journey. Every disposable fixture was restored. A missing accessible label in the Edit pay dialog was repaired during this verification. Worker-browser startup/screenshot stalls were bounded; the successful final run completes login fully, retries interrupted Desk boot once, and blocks unused audio downloads. This is functional verification, not a sustained load or full security audit.
