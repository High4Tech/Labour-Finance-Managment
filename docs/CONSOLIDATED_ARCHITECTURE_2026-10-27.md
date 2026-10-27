# Consolidated architecture and client portal — 2026-10-27

This is an evolution of the existing Frappe/ERPNext/HRMS app. It creates no replacement accounting, attendance, payroll, loan, warehouse ledger or Job entity. The attached specification was compared with the current implementation; existing financial engines remain authoritative.

## Relationship and workflow map

Client (native Customer/Contact/Address) → optional formal Agreement (Contract + PP Contract Terms) → one or multiple Events (PP Event Plan + Project + event-specific PP Contract Terms) → dated assignments/resources → approved attendance → earnings → native invoices/payments and worker settlements.

A standalone event uses an internal commercial basis without appearing as a formal agreement. An ongoing agreement can omit its end date and fixed quantities. Existing event IDs, signed snapshots, approved rates, invoices and attendance are retained. Event-specific terms are snapshots; editing a root agreement does not reprice completed work. Fixed agreement value is allocated across events, never copied as revenue into each event.

The agreement retains five steps and the previously requested order: Client details → Agreement details → Sites and crew → Pricing and milestones → Review and share. Crew/client rates therefore exist before daily payment estimates. The event retains its four-step information → staffing → resources → staffing schedule flow. Transport and equipment are optional. No recurrence engine or separate small-business app was introduced.

## Changes in this release

- Section headings open their overview; the independent arrow expands/collapses children. Redundant child overview links are removed. Personal section ordering is retained and old group names resolve to the new groups.
- Native search inputs and match buttons share heights, spacing and alignment. Sidebar controls have accessible names and native menu semantics, with contrast-correct dark surfaces. Inputs retain useful width instead of shrinking with native percentage columns. Mobile uses 44px controls.
- An event prepared inside the wizard remains **Draft** until explicitly finished. **Upcoming** applies to finished events whose start date is in the future. A Draft link opens the editor, including older native list links. Saved edits to an unfinished event resume from their associated planning draft without an extra duplicate row.
- Draft attendance marks can be saved. New earnings cannot be approved until the event is finished. Existing approved attendance remains unchanged.
- Created agreement and event headers provide **Copy client link**. It opens the existing online signing portal, now including explicitly refreshed event progress. Agreement links show associated confirmed events; an event link limits progress to that occurrence. Draft events remain internal.
- Repeated Copy reuses a current encrypted grant. The signing grant expires after seven days and can be revoked through existing sharing controls. Copying a link does not send email or generate a PDF. Existing signed evidence is shown rather than asking the client to sign the same version again.
- Equipment booking is item → quantity → warehouse availability for the current dates. When exactly one warehouse has sufficient quantity it is selected. The popup shows on hand, reserved and available quantities. Editing excludes its own reservation during availability checks.
- Vehicle profile assignment selects actual dated events, including standalone events. It no longer incorrectly reserves against a formal agreement project. Available vehicles show registration/model and capacity.
- Server-side reservations require an actual dated event. A framework agreement alone cannot block physical resources. Explicit reservation confirmation still commits planning capacity.
- Full-event resource bookings follow changed event dates and revalidate conflicts. Deliberately partial reservations retain their dates; invalid partial ranges require correction. The whole date edit rolls back on conflict.
- Cancelling a Project/Event releases its future equipment and vehicle reservations. It does not decrement/increment stock, change valuation, create an expense or fabricate a return.

## Sidebar destination map

| Position/group | Destinations |
|---|---|
| Primary | Overview; Attendance |
| Clients and work | Clients; Agreements; Jobs and events |
| Workforce and resources | Workers; Inventory and equipment; Warehouses; Vehicles |
| Finance | Billing and invoices; Worker payments; Worker loans and advances; Receipts and payments; Expenses |
| Reports and analytics | Job and event finances; Worker statement |

Supporting configuration remains available to authorized users through existing contextual tools. High4Tech platform administration is unchanged. Bookmarks using Daily work, Clients and billing, Inventory and transport, Payments and costs, and Business reports remain compatible.

## Exact metadata changes

| Existing DocType | Added field | Purpose |
|---|---|---|
| PP Event Plan | `planning_state` (Draft / Ready, read only, default Ready) | Explicit unfinished/finished planning; date-derived status is separate |
| PP Agreement Share | `portal_event` (hidden read-only Link) | Restrict one bearer grant to one event's progress |
| PP Agreement Share | `access_token` (hidden read-only Password, no copy) | Reuse a current client URL using native encrypted password storage |

The existing `token_hash`, expiry, status, frozen snapshot, digest, proposed amendments and signer evidence are reused. No new DocType or financial amount field is added. Additive installation reloads those existing DocTypes. Blank legacy planning state becomes Ready; existing history is not guessed to be an unfinished draft.

## Reused native functionality and financial reconciliation

- Customer, Contact and Address remain the client source of truth. Selectors use titles and IDs plus dates/context, with server-side company/client checks.
- Employee daily/monthly pay, leave rules and loan eligibility remain on the existing profile. Monthly event pay still supplies amount ÷ 30 for approved attendance; no wages are generated for unworked days.
- PP Assignment → PP Daily Register/PP Register Line → PP Work Entry remains the attendance engine. Present 1, half day 0.5, absent 0, unmarked not approved. Historical rates and duplicate prevention remain.
- PP Worker Loan/PP Loan Recovery and native Payment Entry/Journal Entry remain the loan system. Draft loans are unpaid; disbursement requires matching native posting. Recoveries are capped by earnings, unpaid wages and loan balance, with duplicate monthly recovery protection.
- Wage payments, recoverable advances and non-repayable assistance are distinct purposes. Earned wages use wage settlements; genuine loans use loan/disbursement actions. Non-repayable compensation/expenses must use the appropriate existing payroll/expense record, never a loan created simply because money was given. This release adds no unsupported allowance accounting.
- Outstanding wages remain approved earned wages minus posted wage payments and valid posted recoveries. Outstanding loan remains actual disbursement minus posted recoveries/repayments. Previewing does not post money. Wage payment and loan disbursement/recovery do not duplicate operational wage expenses or revenue.
- Event → agreement → client/company aggregates reuse the existing project financial provider. Contract value, earned revenue, invoiced amount, cash received and outstanding balances remain distinct. No reporting formula was replaced.
- Native Item/Warehouse/Bin, Stock Reconciliation and valuation remain authoritative. Warehouse ownership is the native Owned/Rented type. Inline/bulk quantity changes still require explicit save, stale-value checks and reconciliation.
- Date-based availability uses peak overlapping active reservations, not the sum across unrelated dates. Expiry restores **planning availability** through date filtering, never a scheduled stock increment. Actual consumed/lost stock is not restored. The MVP reserves reusable equipment; native stock transactions govern actual consumption.

## Security, data preservation and bounded updates

The portal reuses the existing bearer signing grant, hashed lookup, native encrypted token storage, expiration and immutable snapshot. Guest output is an allowlist of event title/reference, period, lifecycle, scheduled phases and planned/scheduled crew-day counts. It excludes worker identities/pay, budgets, profit, loans, internal notes, files and company workspace access. Event/client/company relationships are rechecked server side. Invalid, expired and revoked tokens are denied.

Progress is refreshed explicitly, without background polling. Portal output is bounded to 25 recent associated events. Resource choices and list records use existing scoped reads; saving rechecks locks and availability. No new per-keystroke rerender or unbounded observer was added.

Before metadata changes, a Git recovery checkpoint and full working-site database/public/private files backup were created. No customer records were reset or reseeded. Test changes use rollback suites or exact disposable QA fixtures with cleanup guards; no real client email or customer financial posting is used.

## Verification

| Check | Actual result |
|---|---|
| `docker compose exec -T -w /home/frappe/frappe-bench/sites frappe /home/frappe/frappe-bench/env/bin/python /workspace/scripts/audit-workflows.py qa.localhost --architecture-regression` | 296 cases: 294 passed; two outdated test fixtures required correction |
| Same runner with `--consolidated` | 72/72 passed after fixture corrections, including both previously failing cases |
| Latest result per case across those runs | **296 distinct native backend cases passed; no unresolved failure** |
| `node scripts/browser-consolidated.cjs` | 14 checks passed: section navigation, native searches, Draft/Upcoming, copied links, guest signing/privacy, AA/responsiveness; exact fixture restored |
| `node scripts/browser-resource-allocation.cjs` | 7 checks passed: item-first warehouse selection, inline stock/capacity errors, real reservations, own-edit availability, vehicle conflicts, responsive AA; exact fixture restored |
| `node scripts/browser-event-repair-20261027.cjs` | 12 checks passed: real event/date/staffing controls, aligned profiles, responsive crew actions, actionable schedule, payment tables, light/dark and mobile AA; exact fixture restored |
| `python scripts/verify-resource-reservation-race.py` | Two independent sessions requested 8 units each against 12 available; exactly one saved and one was rejected; exact fixture restored |
| Read-only working-account smoke | 5 checks passed; sidebar AA had zero violations in both themes; business record counts unchanged, including all 50 workers |
| Source verification | Changed Python, JavaScript and JSON syntax plus `git diff --check` passed |

The two fixture corrections were: reload a native work-entry object after a deliberately rejected approval before retrying (native timestamp protection remains enabled), and create a dated event before the older fleet-availability test tries to reserve a vehicle. The latter reflects the new architecture requirement that agreements alone cannot allocate real resources. No business validation was relaxed to make these tests pass.

Backend coverage includes one/multiple/ongoing/standalone events; signed amendments and historical rates; attendance, partial wages, monthly loans/recoveries, invoices/receipts and foreign currency; stock reconciliation/valuation, nested/non-overlapping reservations, cancellation and atomic event date changes; native permissions, scoped lookups, guest token denial and source-aware deletion. Race verification uses a synthetic disposable Bin to isolate locking; real Stock Reconciliation and unchanged stock valuation are verified separately by rollback integration tests.

The source recovery point is `backup/pre-consolidated-architecture-20261027` at `3acd83c`. Before changes, the working site backup `20261027_125329-high4tech-events-fd166a217c_localhost-*` completed with database, public files, private files and private configuration. Backup contents and local test evidence stay outside Git. Additive metadata was installed on QA and the working site; assets use `20261027-consolidated-3` and both site caches were refreshed.


## Limits

- Bearer links identify possession of a private link, not independently verified signer identity. They expire after seven days; copy a fresh link when necessary. A shared agreement snapshot remains frozen while event progress is current.
- The client progress list is bounded to the latest 25 events. An individual event link opens that occurrence directly.
- Monthly recovery is retained. No separate per-settlement/final-settlement deduction policy or jurisdiction-specific legal limit was invented; those require an explicit policy and appropriate native payable balances before extension.
- Automated accessibility and workflow checks are evidence for the tested screens, not complete manual usability validation or production security certification.
- Production hosting, SMTP delivery, payment gateways and load testing at commercial scale remain outside this local architecture update.
