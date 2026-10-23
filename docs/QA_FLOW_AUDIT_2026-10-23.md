# Full workflow audit — 23 October 2026

**Verdict: the normal operational flow passes, but four exceptional paths remain broken or incomplete. Fix the paid-attendance correction first.** This audit adds repeatable tests and evidence; it does not resolve the application findings below.

## Scope and method

Audited the local PLUS POINT application starting from application commit `11fe875`. This report covers client/worker setup, agreements, staffing, transport and equipment, daily attendance, leave, loans, invoicing, receipts, wage settlements, expenses, reports, updates and deletion.

Financial and stock postings were exercised against actual Frappe/ERPNext/HRMS tables on `qa.localhost`, inside transactions that were rolled back. Browser journeys used exact disposable QA companies and restored their original settings and records afterward. The working customer's business records were not edited or deleted. Report screens on the working site were inspected without changing their business data.

These are local functional results, not production approval, a full security assessment, or a ten-company concurrency benchmark.

## Core results

| Layer | Result | Coverage |
| --- | --- | --- |
| Customer regression tests | 229 passed; no failures or errors | Finance rules 6; register rules 4; operations 48; events/resources 40; attendance 17; currency/billing 9; forms/deletion 22; agreement/worker hierarchy 50; imports 33 |
| Connected lifecycle tests | 2 passed | Three attendance dates through leave, loans, wage settlement, client payments, expenses and reports; resource/deletion availability propagation |
| Signup/activation safeguards | 10 passed | Simulated signup/approval and activation boundaries; no ten-customer production provisioning was attempted |
| Repository/offline tests | 11 passed | App schema/source checks, entitlement rules, local HTTP test harness |
| Current browser journeys | 6 passed after harness maintenance | Agreements, imported deletion, finance hub, resources, daily attendance, worker workflows |
| Business reports | Passed | Project finances and worker statement, all four views, desktop and 390px mobile, horizontal/virtual scrolling and unchanged report data |
| App JavaScript syntax | 28 scripts passed | Customer app scripts |

Total: **252 distinct automated checks passed**, plus the browser/report journeys. Exceptional paths investigated separately are listed below; the passing checks do not cancel out those findings.

### One connected financial example

The test created an agreement and allocated two workers. It approved three dates using Present/Half day/Absent, full and half-day leave, a monthly salary converted to its configured daily rate, and a daily-rate worker. It then recorded an actual employee advance and recovery, a wage payment, an invoice, two partial client receipts and a supplier expense.

| Figure | Verified value in the test company's currency |
| --- | ---: |
| Earned client revenue | 1,050.00 |
| Wages earned | 600.00 |
| Loan disbursed | 500.00 |
| Loan recovered from wages | 75.00 |
| Remaining loan balance | 425.00 |
| Wages paid in cash | 225.00 |
| Wages still outstanding after recovery/payment | 300.00 |
| Client cash received, two receipts | 400.00 + 650.00 |
| Client invoice outstanding | 0.00 |
| Supplier expense | 100.00 |
| Operational profit | 350.00 |

The project summary and worker statement reconciled. Draft attendance did not earn wages, repeated preparation did not duplicate work, and protected historical records remained undeletable.

## Updates and deletion coverage

| Action | Verified result |
| --- | --- |
| Revise agreement requirements | Event requirements update; recorded work/rates keep their historical snapshots |
| Change agreement currency | Entered values retain their numeric amounts; manual agreement exchange-rate input is absent; accounting conversion remains behind the boundary |
| Define vehicle quantities before saving | Requirements persist and appear in the event and signing snapshot without assigning actual vehicles prematurely |
| Change worker status / salary / leave settings | Current worker edit/create screens expose the relevant controls; activation, eligibility and limits are checked |
| Approve attendance | Wages and daily client revenue update; drafts, shortages and budget refusals do not partially post |
| Delete a vehicle reservation | Vehicle availability changes from Assigned to Available |
| Delete an equipment reservation | Reserved stock releases and available stock updates |
| Delete an unused allocation | Worker availability, event allocations and unmarked rosters update |
| Delete an unused event | Planning catalogue removes the event |
| Delete an unused imported event | Real list Delete succeeds; import receipt/hash remains; replay cannot silently recreate it |
| Delete unused equipment with an empty Bin | Native list deletion succeeds and the auxiliary stock row is cleaned up |
| Bulk-delete mixed unused/linked clients | Eligible client is deleted; linked client remains with an explanation |
| Delete stock/accounting history | Refused by the native history/dependency rules; this is expected protection, not a failed deletion |

Whole-company purging and forced deletion of posted financial history were not attempted.

## Confirmed exceptional-path findings

Priority meanings: **P1** = financial correctness needs attention before relying on the affected workflow; **P2** = blocked action or inconsistent lifecycle behavior. All four findings remain **unresolved**.

### QA-02 · P1 · Correcting already-paid attendance leaves inconsistent balances

Reproduction:

1. Approve one worker as Present, earning 200.
2. Submit a wage payment and settlement for 200; outstanding becomes zero.
3. As administrator, correct that attendance to Absent with a reason.
4. Open project finances, the worker profile and the monthly worker balance.

Observed: the correction is accepted, earned wages fall to zero, and the payment stays submitted. Project/profile outstanding becomes **−200**, while monthly outstanding and monthly payable show **0**. There is no explicit overpayment/recovery step that reconciles those views. This does not mean the payment disappears: it means the resulting employee credit/debt is inconsistently represented.

Impact: a legitimate attendance correction after payment can leave the company without a clear, consistent amount to recover or carry forward.

Recommended repair: require a settlement reversal or an explicit overpayment adjustment before completing the correction; expose the same overpaid/recoverable balance in every affected view. Simply hiding negative balances would conceal the problem.

Evidence: `scripts/audit-financial-edges.py`, observation `QA-02`; actual QA Payment Entry remained submitted (`docstatus=1`). Relevant code: `attendance.correct_marks`, `benefits.balances`, `api.project_summary`, `worker_profile.overview`.

### QA-01 · P2 · Sharing an unsigned agreement creates a deletion dead end

Reproduction:

1. Create an unused draft agreement; deletion is initially available.
2. Create its signing link without sending email or signing it.
3. Edit the agreed scope, revoking the old unsigned link.
4. Try Delete and follow Open blocking record.

Observed: both the pending request and the revoked request block agreement deletion through a `PP Agreement Share` dependency. The Delete button is disabled. Open blocking record routes to a record outside the current app navigation scope and redirects to the overview, leaving no usable cleanup action. This is a separate remaining deletion loop from the import-receipt problem fixed in the baseline version.

Impact: unused agreements cannot be removed through the intended UI after sharing, even when nobody signed them.

Recommended repair: provide a scoped cleanup action for unused pending/revoked requests, and route dependency links to usable screens. Keep signed evidence protected; do not broadly ignore all signing records during deletion.

Evidence: `scripts/audit-signing-deletion.cjs`; local JSON `full-audit-signing-deletion-20261023.json` and screenshot `audit-signing-delete-blocked.png`. Confirmed through the actual browser UI, with fixture restoration successful. Relevant code: `record_actions.review`, `forms.js` deletion dialog, `onboarding.js` navigation scope, `signing.invalidate`.

### QA-04 · P2 · Draft invoice preview incorrectly prevents a valid deletion

Reproduction:

1. Approve daily work earning 350 of client revenue.
2. Generate its client invoice and leave it in Draft.
3. Request deletion review for that invoice.

Observed: preview blocks deletion because the approved `PP Work Entry` links to the invoice. However, invoking the application's existing deletion operation in the isolated test succeeds: the native invoice deletion hook releases the source link, the invoice is removed, and earned revenue remains **350 before and after**. The preview evaluates links before accounting for this legitimate cleanup, so the shared UI dialog disables an action the server supports.

Impact: users cannot discard and regenerate an unused draft invoice through the normal Delete dialog. They are told to remove an approved work record that should be retained.

Recommended repair: align draft-invoice preview with its native cleanup hook, ignoring only source links that this specific draft owns and will safely release. Continue protecting submitted invoices and all earned work.

Evidence: `scripts/audit-financial-edges.py`, observation `QA-04`; `actual_removal_succeeded=true`, `source_invoice_after_deletion=null`, earned revenue unchanged. Relevant code: `record_actions.review`, `billing.release_invoice`, Sales Invoice `on_trash` hook.

### QA-03 · P2 · Deleted attendance drafts regenerate, including under closed agreements

Reproduction:

1. Set up an active event and allocation covering today; prepare an unmarked attendance draft.
2. Delete that draft successfully and run the normal today-attendance preparation.
3. Observe its replacement, delete it, close the agreement, and prepare today's attendance again.

Observed: both preparations create a new draft, including after the agreement is Closed, while its project/event/allocation remains active. The old record is actually deleted; a different record replaces it. No work entries or wages are created by this probe.

Impact: deletion appears ineffective, and closing the agreement alone does not stop daily operational generation. Automatic preparation during an active event can be intentional, but the app neither explains this consequence at deletion nor synchronizes closure across these screens.

Recommended repair: define and expose a clear end/pause-event action and synchronize the relevant status rules. Explain when a draft will regenerate; prevent new attendance for stopped work while retaining history.

Evidence: `scripts/audit-financial-edges.py`, observation `QA-03`; original deleted, replacement created, closed-agreement generation `created=1`, work entries `0`. Relevant code: `attendance.ensure_today` selects open projects and dated events/allocations without checking agreement closure.

### Repair order and acceptance checks

1. Resolve QA-02; retest paid-to-Absent and paid-to-Half-day corrections, including loan deductions and existing invoices, across project/profile/monthly statements.
2. Resolve QA-04 and QA-01; retest deletion in both lists and detail screens, mixed bulk selection, source-link cleanup and retained signed/posted history.
3. Resolve QA-03; retest deletion and daily preparation for active, paused, ended and closed work. Re-run the connected lifecycle and current browser journeys after application changes.

## Test harness corrections

Some older browser scripts lagged behind the current UI. The audit updated the crew-capacity button name, selected the installed Edge browser, targeted the custom worker editor, distinguished the wage summary from the loan summary, and waited for the asynchronous return to overview. Those initial selector/timing failures were test-harness problems, not counted as application defects. All six main browser journeys passed after those corrections.

## Evidence and reproducibility

Repeatable runners and journeys added or used for this audit:

- `scripts/audit-workflows.py` — per-case database evidence; customer and platform modes.
- `scripts/audit-workflows.py qa.localhost --journey` — the connected lifecycle tests.
- `scripts/audit-browser-workflows.cjs` — sequential browser journeys with fixture-restoration checks.
- `scripts/audit-financial-edges.py` — exceptional correction/deletion observations in rolled-back fixtures.
- `scripts/audit-signing-deletion.cjs` — unsigned signing-request deletion/navigation probe.
- `apps/plus_point/plus_point/tests/test_full_workflow.py` — connected finance and resource propagation regression cases.

Detailed logs, per-case JSON and screenshots remain local under `.local/qa/full-audit-*` and `.local/qa/audit-*`; they are excluded from Git. Browser stock-edit presentation uses an explicitly simulated stock response, while the connected/database tests separately verify actual stock ledger posting and reservation protection.

## Limits of this audit

- No real bank/payment-provider transfers or customer emails were sent. Accounting entries in QA are not external bank transactions.
- No sustained ten-company load, memory/CPU profiling, concurrent race benchmark or full role/privacy matrix was performed.
- Idle checks found no finance polling and bounded UI work in the inspected resource/navigation flows; this does not establish server capacity under load.
- Production TLS/MFA, backup restoration, hosted deployment, external email delivery and payment-provider integration remain separate acceptance work.
