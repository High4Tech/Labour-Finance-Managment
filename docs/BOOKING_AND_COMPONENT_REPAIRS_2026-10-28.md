# Booking controls and shared component repairs — 28 October 2026

## Delivered behavior

- Untouched agreement/event forms no longer create empty drafts. Actual partial business details still autosave; recovery preserves meaningful work.
- Search suggestions keep native keyboard selection and permissions. More results appears at the bottom after scrolling, hides again above the bottom, and appends results without submitting the form.
- Same-client recent sites return from an existing client or an unambiguous existing client name. Selecting a suggestion clears the site error immediately. Site-only records work; imported crew uses the new agreement dates.
- Workers contains both worker profiles and work assignments, with All, Available, Assigned, Scheduled and Inactive views. Booking checks apply across sites and events, including native assignment saves. Dates are inclusive whole-day slots because the current assignment model has no time-of-day fields.
- Event deletion offers a focused crew/finance review. Selected unused bookings can be released, then the unused event can be deleted. Recorded attendance and posted financial history remain protected; cancellation releases safe future capacity and retains the history and outstanding earnings.
- The payment dialog records payments the administrator confirms were actually made. Only approved, earned outstanding wages qualify. Native Payment Entry and wage settlements enforce permissions, account/currency rules and posting validation. Project/employee locks, reviewed-balance checks and reference-based retry handling prevent stale or duplicate recording. This does not transfer money through a bank.
- The event crew-pay popup uses a selectable table with select all, bulk daily/monthly changes, individual editing and safe unassignment. Monthly pay comes from each worker profile. Attendance locks and over-budget confirmation still apply.
- Equipment opens a focused availability, warehouse/location, event reservation and daily per-unit hire-rate profile. Prices use native Item Price and a currency-specific event hire Price List. Stock valuation is unchanged. The hire rate is a reference/default price, not automatic invoice posting.

## Shared component ownership

The shared component/selector owners now define consistent rounded filled status badges, record summary label/value/note slots, icon actions, separate help and number/link controls, compact help popovers, and aligned CC email rows. Agreement/event modules consume these styles; competing local status overrides were removed. Existing compact native informational alerts are scoped to the company shell. No new global observer or polling loop was added.

The normal equipment view hides irrelevant sales/manufacturing controls. Authorized **Advanced ERPNext controls** still opens the full native Item form. No Frappe, ERPNext or HRMS capability, controller, DocType, accounting integration or native validation was removed.

## Verification

- **325 distinct backend cases have passing results.** The broad 314-case run initially exposed one older dashboard fixture that attempted a now-forbidden overlapping booking. The fixture was corrected to simulate legacy data inside a rollback-only test. The relevant 68-case dashboard suite and final 99-case workflow/draft/planning/operations suite then passed. The merged case report contains no failed/error cases; this is combined evidence, not a claim that all 325 ran in one invocation.
- **44 browser scenario checks passed:** 14 repair scenarios, 11 native-control scenarios, 12 responsive workflow scenarios, and 7 read-only company smoke checks. Fixture cleanup was separately verified.
- Checks cover meaningful/empty drafts, previous sites, paging and keyboard behavior, CC/help geometry, worker availability, bulk profile pay, event release/deletion, ongoing-event payment review/cancellation, equipment routing, imports and calendars. Responsive light/dark and automated WCAG A/AA checks ran on affected worker/event controls and profile tabs. Automated accessibility checks do not replace a full manual accessibility audit.
- Changed Python sources parsed, changed JavaScript/browser scripts passed syntax checks, and whitespace checks passed.
- The final customer-account smoke test loaded release asset version `20261028-booking-controls-2` with no browser runtime errors. Before/after counts were unchanged: 9 agreements, 4 events, 50 workers, 1 sales invoice, 1 worker loan, 5 agreement shares and 0 planning drafts. Browser mutations used a disposable QA company; backend finance tests rolled back. No real email or payment was sent.

### Performance sample

Two isolated dashboard runs before/after baseline `9aff9e2`:

| Measure | Before | After |
| --- | --- | --- |
| Route ready, milliseconds | 4702 / 3600 | 3068 / 3037 |
| Period interaction, milliseconds | 478 / 253 | 369 / 337 |
| Measured JS/CSS resources | 72 / 72 | 72 / 72 |
| Encoded asset bytes | 9,519,968 / 9,535,488 | 9,544,459 / 9,544,459 |
| DOM nodes | 13,104 / 13,104 | 13,104 / 13,104 |
| Used JS heap, MB | 24.65 / 28.18 | 24.73 / 24.73 |

Two chart instances were active on the dashboard and disposed on route departure. This small sample shows no observed readiness/resource-count regression; it is not a statistical performance guarantee. The asset increase includes the new focused controls. Equipment stock/reservation aggregation is batched rather than querying each warehouse individually.

## Backup and release

- Pre-change Git snapshot: `backup/pre-booking-controls-20261028`, pointing to `9aff9e2`.
- Fresh private company database/config/public/private-file backup prefix: `/home/frappe/frappe-bench/sites/high4tech-events-fd166a217c.localhost/private/backups/20261028_221319-high4tech-events-fd166a217c_localhost-`.
- Assets were versioned and company/QA caches refreshed. No schema migration or company-data reset was required.

Local evidence is under `.local/qa/`: `workflow-verified-unit.json`, `workflow-repairs-browser.json`, `refinement-native-controls.json`, `workflow-refinement-browser.json`, `dashboard-after.json`, and `workflow-performance`. Evidence may contain company data and is intentionally not published to GitHub.
