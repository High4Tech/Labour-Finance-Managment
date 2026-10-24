# Component validation and workflow repairs — 24 October 2026

This follow-up repairs the four findings in the 23 October workflow audit and adds direct component checks. It covers the company application, with financial/stock regression tests isolated in rolled-back QA transactions and browser changes restricted to disposable QA companies. Existing customer business records were not changed or deleted.

## Repaired workflow findings

| Baseline finding | Current behavior | Verification |
| --- | --- | --- |
| QA-02: correcting paid attendance made balances inconsistent | Reducing approved earnings below settled wages plus loan recoveries is refused atomically. The message explains that linked settlements/recoveries must be reversed first. Increasing earnings and unpaid corrections remain available. | Present-to-Absent and Present-to-Half-day after payment; recovery-backed wages; unchanged attendance/balance on refusal; correction after reversal; full connected financial journey |
| QA-01: unsigned signing requests blocked agreement deletion | Deleting an otherwise unused agreement removes its pending/revoked links through native permission checks. Signed snapshots remain protected. The UI does not offer dependency links outside the app's navigation scope. | Actual browser deletion after sharing/revocation; signed evidence refused with no inaccessible blocker link; backend signed-history safeguard |
| QA-04: a valid draft invoice could not be deleted | The preview recognizes only the source links that the draft invoice's native deletion hook will release. Approved work and earned revenue remain intact. Submitted invoices and unrelated dependencies stay protected. | Preview permits deletion; invoice removed; source released; earned revenue unchanged; existing accounting-history regressions |
| QA-03: closed agreements kept generating attendance drafts | Automatic preparation and new attendance require an open project and active dated agreement. Existing attendance history can still be viewed. Delete explains that active events regenerate today's unmarked draft and that agreement closure stops new generation. | Closed agreement creates zero new drafts; new preparation refused; historical register readable; normal active-event generation remains idempotent |

## Component rules now checked

| Component / state | Behavior |
| --- | --- |
| Upcoming planning dates | The calendar disables past days. Clicking a disabled past day cannot change the selected start. Saving a newly backdated agreement is also rejected on the server. |
| Historical records | **Record past work** is an explicit option. Existing historical agreements open in that mode; old records are not made unusable by a blanket ban on past dates. |
| Date order | Through/end cannot precede From/start. The field shows the corrective boundary underneath it and no save request is sent for the invalid range. |
| Crew and vehicle date bounds | Calendars and inline validation honor the agreement interval. Child dates outside it are rejected by the existing server rules. |
| Date text | Malformed date text gets a format hint. The date picker normalizes bounds to the Date objects required by the installed control. |
| Birth and loan dates | Future birth dates are blocked. Loan disbursement date has the existing server's today-or-earlier limit in its calendar. |
| Required fields | Missing agreement fields have a specific inline instruction. A missing client contact method points to both email and phone; entering either clears that combined error. |
| Email | Email input/keyboard/autocomplete, syntax feedback with an example, and server validation. Correcting the value clears its error. |
| Phone | Phone input/keyboard; formatted international/local numbers with 7–15 digits; optional leading +, spaces, parentheses and hyphens. Letters and too-short/long values are rejected. |
| Numeric fields | Letters are blocked in numeric controls. Integer counts reject fractional paste. Server checks reject text, nonfinite amounts and fractional integer values in worker finance fields. |
| Semantic numeric limits | Crew count 1–500; nonnegative salary/waiting period; leave allowance 0–31; worker loan percentage 0–100; actual loan deduction greater than zero and at most 100; vehicle requirement 1–100. Daily wage/client charges and fixed contract values use their positive-value rule. |
| Warehouse quantities | Negative quantities, exponent text and reductions below today's reserved quantity have guidance directly beneath the edited input. Letters are blocked; correcting the quantity clears the error. Invalid rows block saving, reservations remain read-only, and bulk editing still works. The server retains stock-history and future reservation protection. |
| Hidden worker tabs | Saving reveals the tab containing the invalid field. Tab/panel associations and error descriptions are linked for assistive technology. |
| Error layout | Field errors grow beneath their own control rather than sitting in an overlapping absolute box. Common input/date errors share the same feedback component. |
| Operational tables | Agreement and resource tables use one renderer, header scopes, mobile cell labels, shared spacing and wrapping action containers. Native top-level lists and financial report grids retain their framework components and capabilities. |
| Mobile action layout | Crew table actions were checked at 390px and desktop widths with no intersecting button rectangles. Existing resource/report responsive checks are retained. |

The 7–15 digit phone rule checks format, not ownership or deliverability. Email checks similarly validate syntax. These are functional checks of the listed component states, not an exhaustive claim about every possible field value, role, browser or locale.

## Verification results

| Layer | Result |
| --- | --- |
| Customer regression, including connected lifecycle and new boundary tests | **242 distinct cases passed**, zero failures/errors |
| Platform signup/activation safeguards | **10 passed** |
| Repository/local HTTP harness | **11 passed** |
| Automated total | **263 passed** |
| Focused browser components | **26 checks passed**, no page errors; fixture restored |
| Browser journeys | **8 distinct journeys passed**: components, signing deletion, agreements, imported deletion, finance, resources, attendance, workers; all fixtures restored |
| Extra final browser checks | Signing/history protection and warehouse quantity states passed again after their final changes |
| Business report layouts | **Passed** on the working site after cache refresh: both reports, all four views, desktop/mobile, full rows, horizontal and 60-row virtual scrolling, unchanged data, separated filters and bounded idle/route cleanup |

The full three-day financial example still reconciles revenue 1,050, wages 600, loan recovery 75, wage cash 225, other expenses 100 and operational profit 350. This verifies the repair did not alter the normal accounting flow. Future attendance approval, insufficient stock, duplicate records and protected posted-history checks remain in the regression suite.

The first report-layout attempt timed out during Desk boot with no page script error. The follow-up uses the refreshed working-site app cache and waits for report readiness. Its final result is recorded above.

## Repeatable checks and evidence

- `scripts/audit-workflows.py qa.localhost` runs the full 242-case customer suite; `--components` runs the 11 new boundary cases; `--journey` runs the connected lifecycle cases.
- `scripts/audit-financial-edges.py` now invokes the repaired-boundary regression suite; historical failure observations remain in the original audit report and local logs.
- `scripts/browser-components.cjs` checks actual calendar clicks, typing/paste, field feedback, hidden tabs and responsive table actions.
- `scripts/audit-signing-deletion.cjs` checks actual deletion plus signed-history protection.
- `scripts/browser-resources.cjs` includes inline stock validation and bulk-edit checks. Its stock-posting response is explicitly simulated; actual ledger posting/reservation rules are verified separately by the database tests.
- `.local/qa/final-validation-20261024.json` summarizes counts and the latest result for each browser journey. Detailed case evidence, logs and screenshots remain local and excluded from Git.

No bank transfers or customer emails were sent. Ten-company sustained load and a full security/role audit remain outside this functional test run.

## Calendar click regression and repair

The user subsequently reported that calendar arrows and date cells did not respond. This was reproduced with a normal pointer click on the agreement end calendar. The earlier component checks covered a disabled past-day click and programmatic date changes, but missed normal enabled-day and navigation clicks.

The shared date validation was unconditionally updating the date picker's bounds on input blur. That rebuilt its calendar between pointer down and click, discarding the interaction. Bounds now update only when their normalized date changes. Date order, agreement boundaries, past-date restrictions and corrective inline messages remain enforced.

Fresh verification after this repair:

- **10 calendar checks passed** using normal clicks: agreement start/end navigation and selection, forward/back navigation, vehicle dialog selection, dark mobile navigation/selection, worker past birth-date selection, year/month/day selection, and no page errors.
- **26 component checks passed again**, including disabled past dates, invalid date order, agreement interval boundaries and future birth-date rejection.
- Both disposable QA fixtures were restored. No customer records were changed by these tests.

`scripts/browser-calendar.cjs` is now included in the default browser audit. Evidence is saved locally in `.local/qa/calendar-interactions-20261024.json` and `.local/qa/component-browser-20261024.json`. The shared asset version is refreshed so existing sites receive the repair.
