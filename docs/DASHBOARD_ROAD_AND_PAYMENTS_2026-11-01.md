# Dashboard road, navigation and wage confirmations

## Delivered

- Open, wider perimeter road with roofless client office, worker house, warehouse and event site. Two workers and a vehicle follow scroll progress; loading/work poses run only while visible. Removed the bottom workflow panel from the dashboard, keeping its shared component available elsewhere.
- A single local 119,373-byte sprite atlas supplies the decorative world. No Three.js, WebGL renderer, model downloads or scene polling on the dashboard. The larger interactive event scene remains lazy-loaded on demand. Reduced motion and page visibility stop decorative motion; route changes release listeners and observers. Roads are shown on wide screens (1600px+) so smaller screens retain usable data space.
- Active events and upcoming milestones show up to three actual records and hug the rows. Attendance register and attendance chart panels share a height; missing register rows stay blank. Workers search has no action-column shadow bleed.
- Fifteen navigation SVGs exported from the supplied Figma file are shared by navigation, dashboard activity and notifications. Currency selector retains the compact currency-code-and-chevron design. Collapsed native navigation occupies 64px and the main content reflows.
- Outside-click dismissal covers native dialogs, native global search and menu overlays, including a click during the opening backdrop animation. Static confirmation dialogs and busy forms stay protected. Dragging from inside a dialog does not dismiss it.
- Notifications & activity is a dedicated company screen, reached from both activity View all and the notification overlay footer. Only the current user's personal notifications may be marked read. Company activity and record links retain native permission checks. Lists paginate in bounded pages.
- Scoped centered searches: Ctrl/Cmd+A agreements; Ctrl/Cmd+E events; Alt+L workers; Alt+I inventory; Alt+W warehouses; Alt+V vehicles. They do not override typing, text selection, rich-text editing, or another active form. Ctrl/Cmd+K retains native global search. The global search divider no longer crosses the input.
- Pending native report requests are cancelled when changing reports, preventing previous results from rendering against the next report's metadata. Native filtering, masking, exports and report capabilities remain intact.

## Worker payments

Worker payments now opens with approved wages, recorded payments, posted loan deductions and outstanding balances, followed by worker/event rows and Paid / Partly paid / Unpaid states. Workers without approved attendance are labelled No approved wages. Assigned and accrued amounts are not confused with actual payment.

An event's payment confirmation timing can be Manual, Daily or Monthly, in creation/editing, event actions, or the Worker payments screen. Daily becomes due through yesterday; monthly through the last completed month, or through the end of a completed event. These settings prepare confirmations: they do not transfer money, invent attendance, or mark a worker paid.

Recording a full outstanding payment requires an account, actual payment date, reference and explicit confirmation. The existing accounting workflow rechecks balances with locks, submits native Payment Entry and wage settlements atomically, and prevents duplicate retry posting. Existing/partial manual payments remain available through the native payment-history and linking workflow. Loan deductions count only after posting. Amounts in this screen use the company's accounting currency.

No existing business records were deleted or paid during the browser audit. Financial posting tests ran on the test site and rolled back.

## Verification

- 76 rollback-only backend tests passed (65 payment/workflow/dashboard/draft checks plus 11 component/financial validation checks): wage balances, partial/final payment status, retry idempotency, loan treatment, permissions, confirmation timing, searches, drafts, booking and dashboard calculations.
- 34 dashboard follow-up browser checks passed, including opening-transition dismissal, protected static dialogs, all six search shortcuts, payment field errors and navigation cleanup.
- 36 shared-shell browser checks passed across primary routes, report navigation, keyboard, mobile navigation, light/dark layouts and accessibility.
- 19 interactive event-world lifecycle checks passed: cold/warm opening, pause/resume, unavailable WebGL fallback, interrupted-download retry and graphics disposal.
- 23 earlier dashboard-polish checks passed with the intentionally removed footer animation assertion updated.
- Light/dark checks at 390, 768, 1440 and 1920px; shell checks also at 320 and 1024px. Automated WCAG AA checks on tested regions reported zero violations. This is not a claim of a full manual accessibility certification.
- Syntax checks passed for all modified/new JavaScript and Python sources; whitespace checks passed.

Evidence is stored locally under `.local/qa/dashboard-followup`, `.local/qa/app-shell`, the event-scene audit output and `.local/road-payment-tests.log` (ignored from Git).

## Performance comparison

Two local browser runs per version compared baseline `75a4299` against the update at 1440px using equivalent asset delivery. Mean dashboard readiness: 4,107ms to 3,525ms; filter interaction: 424ms to 295ms. These small local samples are diagnostic, not production guarantees.

Dashboard API requests stayed at two; chart instances stayed at four and dropped to zero after navigation. Mean DOM nodes: 12,724 to 12,685. Mean measured heap: 26.38MB to 27.58MB. JS/CSS transfer measured about 9.67MB to 9.69MB, mostly the retained native framework. No idle network requests or repeating header mutations were detected. The decorative atlas is one additional lazy request on wide screens. New payment and company-tools screens load only when requested.

## Backup and installation

Both test and main sites migrated successfully. Database snapshot before installation:

`sites/high4tech-events-fd166a217c.localhost/private/backups/20261101_163120-high4tech-events-fd166a217c_localhost-database.sql.gz`

Git rollback point: tag `backup/pre-road-payments-20261101` at `75a4299`. Frappe/ERPNext/HRMS modules, DocTypes, stock/accounting systems and advanced native views remain preserved.
