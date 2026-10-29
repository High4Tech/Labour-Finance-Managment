# Table, filter and milestone controls

## Result

- Delete review now presents separate blocker cards with short reasons and expandable details. Existing linked-record routing, permissions and financial-history protections remain intact.
- Filters show one status selection, sort/order radios and Reset. Advanced native criteria remain accessible in a disclosure.
- Resource commitment sits inside Billing setup, using horizontal radios on desktop and a dropdown on mobile.
- The final agreement/event footer invokes the existing create/save handler. It cannot address an undefined next step.
- Shared tables support selection and copying. Editable crew requirements, vehicle requirements, milestones, event reservations, role pay settings and worker daily-rate previews expose contextual bulk actions. Existing worker-pay bulk actions and native list controls remain available. Saved agreement edits retain their client-approval gate; invoiced history remains protected.
- Monthly auto-selection displays profile salary without daily-only columns. Daily selection fetches each worker's profile rate into an editable field. Changes are validated against the server-selected workers; profile/availability changes still require a new review, and over-budget confirmation remains enforced.
- Upcoming milestone information is a table with View milestone in its action column. Long standalone facts span the panel. Signed-document dates omit microseconds; the signature fingerprint is labelled as verification evidence rather than an unexplained agreement version.

## Early invoices

Generate invoice is available before approved attendance exists. In that case it previews a private **Pro forma invoice**, marked Estimated, and saves it in Documents. The PDF records when it was generated and whether that was before, during or after its billing period. It uses agreed quantities/client rates and explicitly states that attendance is not finalized.

An estimate does not create a Sales Invoice, consume work entries, close the payment period, record a receivable or recognize revenue. Once the period ends and approved attendance exists, the normal invoice uses actual unbilled work. Repeated actual-invoice requests return the existing invoice. The recurring billing process is unchanged.

## Verification

- 179 distinct backend cases covered across the broad regression run and focused reruns. The final focused suite passed 100/100. The bulk-total failure found during testing was fixed by validating the whole fixed-contract total before applying the batch.
- 12 browser scenarios passed on disposable company data: filter/reset/sort, blocker routing, daily overrides, monthly salary, event bulk edits, both final wizard actions, real estimate PDF generation/document retention, resource-control responsiveness and milestone bulk editing. No browser runtime errors.
- New blocker/pay dialogs and agreement creation were scanned against WCAG A/AA tags in light/dark mode at 1600px and 390px. Dialog overflow checks passed. These are scoped checks, not a certification of the entire application.
- Seven read-only company-screen checks passed; before/after record counts were unchanged. QA fixtures were removed after browser tests.
- Dashboard comparison against `e184ccf`: two runs per version, 72 asset requests each. Ready times before: 4095/3332ms; after: 3155/3377ms. Period-change times before: 300/282ms; after: 273/233ms. Measured transferred assets increased by 13,624 bytes; DOM elements increased by 112 for table selection. No new package, global observer or polling loop was added. This small local sample showed no meaningful regression; it is not a production capacity benchmark.

## Restore point

Code tag: `backup/pre-table-controls-20261029` at `e184ccf`.

A complete private company backup (database, configuration and public/private files) was taken before the changes, with timestamp prefix `20261029_122819`. No company business records were edited by the tests.
