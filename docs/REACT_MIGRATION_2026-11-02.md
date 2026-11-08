# React migration — company application

Latest checkpoint: [November 9 resource, attendance, accounting and D: storage ledger](REACT_MIGRATION_2026-11-09.md). Its completed owners supersede the historical classifications below; the whole migration is still incomplete.

This is an ongoing migration, not a completed rewrite. Frappe, ERPNext and HRMS remain the Python backend, authentication, permission, document, accounting and stock engines. The platform operator console and authorized advanced native views remain available. No database records are migrated into browser state.

## Ownership contract

- `frontend/src/components.tsx` is authoritative for React buttons, fields, selects, feedback, dialogs, badges, panels, tables, selection and pagination. Existing orange visual tokens and shared list geometry remain authoritative. A financial card, notification card and dashboard chart are documented variants rather than unrelated UI systems.
- A mounted screen owns its whole presentation subtree. Legacy DOM enhancement, field-label and feedback scanners skip `[data-pp-react-root]`. No HTML-string renderer is embedded into a React component to claim conversion.
- Native route hosts are temporary compatibility adapters. Each active screen has one React root. Route departure unmounts it and releases listeners, timers, charts, observers and native host overrides. Advanced native routes have explicit, reversible session preferences.
- Real data comes through authenticated same-origin APIs and existing server permissions, validation, company scoping and ledger safeguards. No direct database access, token in local storage, duplicate accounting implementation or financial-result cache.
- Read requests reject stale responses. Search is debounced; changed filters reset pagination/selection. Mutation confirmations retain their stable request identity and disable duplicate submission.
- Updates are event-driven and coalesced, not an interval that reloads the screen every few seconds. Chart instances update their data and dispose on departure. Unchanged cards/inputs remain mounted.
- Native advanced filtering, exports, accounting, stock and HR features are preserved. Product release notices are company-hidden; platform operators retain native release notices and update capabilities.

## Screen checklist

“React” below means that screen's markup/state are owned by React. A linked legacy dialog is explicitly listed as pending.

| Area | Current ownership | Remaining work |
| --- | --- | --- |
| Overview dashboard: three metrics, events, milestones, activity, attendance, workers, footer scenes | React, real existing APIs | Recheck cross-screen live changes as subsequent owners migrate |
| Overview date range and chart-data dialogs | React | Preserve field-level validation and keyboard tests |
| Notifications and company activity | React | Header notification overlay and shell remain native |
| Worker payment balances/history, bulk confirmation, references and timing dialogs | React | Manual native partial-payment form remains an advanced workflow |
| Agreement and event lists, inline drafts, search/status/sort, pagination/selection | React | Import and deletion-review dialogs remain legacy owners |
| Scoped search and quick worker/client creation | React; editors reused by profiles | Resource creation shortcuts remain legacy until their owners migrate |
| Company header, sidebar, global search, notification overlay, help | Native shared shell | Port without changing layout, keyboard shortcuts or authorized navigation |
| Saved agreement profile, overview/detail tabs, section editors, crew/site/vehicle staging, rate-card edits, milestones, share/approval and private PDF/document previews | React on direct and contextual agreement routes; native Quill and file uploader are isolated documented widget boundaries | Imports and deletion review remain native boundaries |
| Agreement creation/full document editing and draft recovery | React, same backend save/proposal/signing/draft APIs | Continue cross-module regression as event and import owners migrate |
| Events/jobs: create/edit, independent/linked terms, venues, crew picker/pay, auto-selection, resources, schedule, detail/documents | Legacy shared owners | Port each complete workflow; preserve booking conflicts/payroll and lazy scene |
| Workers: list, profile/create/edit, assignment, salary/leave/loan actions | React, real existing APIs | Photo uploader and native right comment/activity sidebar remain native boundaries |
| Clients: list, create/edit/detail, linked work | React, native Customer/Contact/Address APIs | Deletion review and native right comment/activity sidebar remain native boundaries |
| Inventory/equipment, warehouses/balances, vehicles/bookings | Legacy simplified/native owners | React ownership; preserve native stock engine behind advanced view |
| Attendance lists/registers, date selection, marks/approval/correction | Legacy shared owners | React ownership; retain approved-work and correction transaction rules |
| Billing/invoices, loans/recoveries, receipts/payments, expenses/reimbursements | Legacy finance/native owners | React owners using the existing posting APIs |
| Event finances and worker statements | Native reports with shared presentation | React product report views; retain native exports/report infrastructure |
| Imports: template/download/upload/preview/approval/result | React shared dialog, original transactional APIs | Native advanced Data Import stays available |
| Client online agreement/progress/signing/update approval portal | Legacy public portal | React public entry with existing private-token/CSRF/version safeguards |
| Onboarding and account/preferences | Legacy/native owners | Port customer controls; platform admin stays native |

All rows must be verified before describing the whole company frontend as React. The existing Desk assets still contribute substantially to cold startup. React alone does not remove that cost. Route assets must be deferred as their consumers migrate, followed by a standalone company shell that does not initialize unrelated Desk presentation.

## Verification evidence so far

- Latest wider architecture regression: 320 backend tests passed with zero failures/errors (699.4s), including the agreement proposal and signing/document regression. The latest focused regression passed 78 tests with zero failures/errors, including payments, worker/client form saves and version conflicts, dashboard data, drafts and permissions. These run on an isolated rollback-only QA site.
- Strict TypeScript, production build and 22 frontend state tests pass. Production React is pinned to 19.3.1 and locally bundled with route splitting. Scoped search defers worker/client editor chunks until creation is requested. Production dependency audit reported zero vulnerabilities.
- Browser suites: dashboard 17, planning 15, payments 14, notifications/foundation 13, workers 17, clients 12 and saved agreements 23 checks passed. These include real API reads, controlled selection, no idle interval refresh, keyboard dismissal, field errors, existing native advanced-view access, responsive light/dark automated AA and root cleanup. Financial writes are intercepted on the main-site UI tests; actual posting is tested on rollback-only QA.
- The main company already had paid wages. Explicit browser-only unpaid fixtures cover multi-event bulk consent/reference states without inventing live debt or changing financial records.
- Offline CI checks: 11 harness tests, 6 pure finance tests, 4 register tests, Python compilation and JavaScript syntax checks. The harness's local HTTP fixture needs socket access in this environment.
- Repeated-route performance test: after warming five migrated list types, 20 further route visits had a median readiness of 125ms (118–155ms in that run). DOM nodes stayed 12,969; realtime list listeners stayed 1; active React roots stayed 1. Collected heap increased from ~20.2MB to ~22.0MB, so this is not a claim of zero memory growth. There were zero duplicate native record-list queries and zero unhandled browser errors.

Browser evidence lives under ignored `.local/qa/react-*`. These are scoped automated checks, not a complete manual accessibility certification or a completed full-app migration. Older browser scripts that inspect native field groups need owner-specific React assertions; they are not evidence that unmigrated screens are complete.

## Rollback and measured performance

Before work: `backup/pre-react-interface-20261102` points to `dc204d16443c7914ac7ad643aa7ff654ce9eec1d`; main-site database, public/private files and config were backed up. No financial record was changed by the browser audits.

Early isolated payment samples: legacy readiness 2,921 ms; first React implementation 4,286 ms; route-prepared React 3,905 ms. Assets ~9.15 MB legacy versus ~9.39 MB React. Thus cold loading is **not yet a demonstrated improvement**. React reduces the destructive interaction behavior and enables owned state; removing duplicate native presentation cost is still required. The latest isolated cold payment sample was 3,324ms with ~9.4MB decoded JS/CSS, so first loading is still not a demonstrated improvement. Warm React list transitions are measured separately above. A standalone company shell and remaining workflow migrations are still required.

## Next migration gates

1. Agreements: full creation/editing, partial drafts, contextual links and saved profiles are React. Imports and deletion reviews remain native boundaries; preserve those workflows while their owners migrate.
2. Events: complete create/edit/profile, staffing/pay/auto-selection, resources and shared calendar, then booking/payroll/attendance regression.
3. Resources, attendance, remaining finance, reports and imports, one complete owner at a time.
4. Company shell and public portal; remove unrelated Desk presentation from the company entry only when workflow coverage allows it. Native authorized advanced views remain separate and available.

The shared visual/interaction contract and dependency audit are in `REACT_COMPONENT_CONTRACT.md`. No backend module, DocType, ledger, controller, permission hook or integration was removed. The old worker presentation was retired only after its remaining consumers were checked and the React/native-advanced worker checks passed.

## 2026-11-03 agreement checkpoint

The saved agreement route now lazy-loads its own React owner before initializing the old form catalogue, profile renderer or activity rail. Shared components own the section tabs, summary facts, tables, selection/bulk editing, cards, modal fields, CC rows, approval dialogs and private document previews. The supplied file-type SVGs and local Tabler sprite remain in use. Formatted scope uses the installed native Quill engine as an isolated mounted widget; read-only document formatting strips active imported markup.

Browser checks found and fixed actual migration failures before acceptance: an editor could open without the saved scope; the native editor's 300ms value debounce could omit text entered just before saving; a newly staged site could submit a temporary browser ID to the backend; and a new object dependency could repeatedly request category capacity. The replacement handlers keep the editor mounted, synchronize text immediately, resolve new sites by name and stabilize capacity dependencies. Tests cover all four failures, including an idle request-count assertion.

New site/crew/vehicle edits remain staged until the existing approval API accepts them. A rollback-only backend regression verifies that a proposed site does not appear in live terms until the client accepts, and does not create assignments, payroll, invoices or ledger entries. Existing event snapshots retain their rates. The category selector now reads a small permission-scoped choice endpoint instead of fetching every agreement, event and client. Category-aware worker creation reuses the same worker editor and returns to the requirement; custom category creation remains available inside that workflow.

The agreement browser suite passed 23 checks: saved text and rapid save, date errors, separate CC fields, approval/attestation payloads, site reuse, temporary-ID rejection, missing-worker category, category-specific capacity without idle polling, rate-card validation, safe formatted read-only scope, private PDF URL cleanup, fixed/daily milestones, real-data reads, mobile/dark automated AA and repeated root disposal. Main-site browser writes are intercepted. Backend tests run on the isolated rollback-only QA site.

Latest isolated performance evidence: cold payment readiness 2,959ms with ~9.4MB decoded JS/CSS; after warming five list types, 20 more route visits had median readiness 138ms. DOM nodes stayed 12,969, realtime list listeners stayed 1, active screen roots stayed 1 and duplicate native list queries stayed 0. Collected heap grew from ~20.2MB to ~22.1MB. This verifies bounded screen lifecycle in that run, not zero memory growth or a proven cold-start improvement. Unrelated native Desk assets still need to be separated from the eventual company entry point.

The final foundation harness passed 13 checks, including authorized non-administrator-labelled list ownership and late-response cleanup. Across the seven current browser suites, 111 checks passed with zero failures or unhandled browser errors. Native Desk canonical URL redirects can replace the document load event, so the harness waits for navigation commit and the actual owned screen's ready state.

## 2026-11-03 full agreement form checkpoint

The three-step agreement form is now a lazy React owner using the same shared fields, rich editor, panels, resource editors, tables, dialogs and full-width footer as the saved profile. New agreements, existing document edits, resumed drafts and contextual project/client links enter that owner directly, without first rendering and transforming a native FieldGroup or downloading the whole planning catalogue. Existing active terms still go through immutable update proposals and client signature or explicit company attestation; editing never silently overwrites the live agreement.

The form preserves partial legacy draft payloads, including unfinished site/crew/vehicle popups. A serialized autosave queue retains the latest change during an in-flight write, propagates the server revision, keeps bounded local recovery, refuses empty default-only drafts and does not automatically replay conflicting revisions. It flushes on page visibility/navigation without a polling interval. Formatted text synchronizes immediately. Client details use abortable, stale-safe requests; long client choices fetch another page only at the end of the list.

Daily schedules are regenerated when the agreement dates change, while invoiced periods remain protected. Fixed milestones support local individual/bulk editing and reject totals above the contract value. Rate cards remain authoritative for category prices, and resource dates inherit the agreement period. No staged new site ID is sent as an existing database record. Creation uses the original save, delivery preflight, signing link, private A4 PDF and follow-up event-draft APIs. New metadata and contextual lookup endpoints enforce the same company/document permissions; no schema migration is required.

The broad backend suite passed 320 tests, followed by 14 focused permission/sharing/contextual lookup tests. Frontend state tests passed 22 cases. The browser form suite passed 22 checks and covers empty drafts, field errors, real clients, stable typing/autosave, inherited resource dates, schedule rebasing, fixed/bulk milestones, separate CC fields, intercepted final creation, partial popup recovery, active-document proposals, keyboard/root cleanup and mobile/desktop light/dark automated AA. The updated planning suite expects the React creator and verifies that it releases ownership on departure. Browser financial/agreement writes stay intercepted; backend posting tests use the rollback-only QA site.

This checkpoint does not complete the event, resource, attendance, remaining finance/report/import, company-shell or public-portal migration. The earlier isolated cold/warm measurements above remain the performance evidence; this checkpoint does not claim a new cold-start improvement. Remaining native infrastructure and advanced views are preserved.

Across the eight current browser suites, 133 checks passed with zero failed checks or unhandled browser errors. This is scoped coverage of the migrated owners, not an acceptance claim for the still-native modules.

## 2026-11-03 shared loading, geometry, payments and import checkpoint

The five migrated list routes now mark their owned native host before asynchronous preparation. Their unused native sidebar no longer reserves a left column, including the first ready frame. Agreement create/edit uses the full main container and the same full-width footer. All React roots share one mount/dispose implementation instead of separate equivalent implementations per screen.

React owns company dashboard loading directly. The superseded company skeleton/data loader is bypassed, and a shared skeleton uses the final dashboard grid. The platform renderer remains separate and intact. Relevant local-save, currency and realtime notices now enter one visibility-aware, throttled update queue; there is no interval refresh. Resource loading reports a changed request scope as busy immediately rather than briefly advertising an idle state before its effect starts.

Worker payment rows remain selectable for review even when the balance is already paid or there is no approved work. Posting still requires permission, positive approved outstanding and explicit actual-payment consent. Selected zero/unapproved balances are excluded with an explanation. References remain optional and can be entered later. Shared Checkbox uses the existing Figma styling and square 20px dimensions across tables and forms; closed selects no longer swallow a dialog's Escape key.

Tables inside React forms/dialogs contain more than six rows within a measured six-row viewport (maximum 500px), with sticky headings and retained horizontal scrolling/sticky actions. A local ResizeObserver tracks only that active table and is disconnected on cleanup. Payment names retain a readable minimum width and show agreement name/reference. Daily periods show their date once and the optional agreed working hours; unset historical hours are explicitly labelled. Hours live in the existing schedule JSON, validate complete/different HH:MM values, support overnight shifts and survive schedule rebasing. No schema migration is needed.

All 15 product imports now share the React dialog, upload, select, feedback, preview table, consent and result components. Original template/help content, external-ID idempotency, final permission/linked-record/budget checks, transactional rollback, reference downloads, error CSV formula protection, onboarding refresh and contextual agreement editing are retained. Preview approval is invalidated on file/type/company changes or a failed apply; posting is never retried automatically. Files are session-local, reads are bounded and disposed, and the engine's short-lived user-bound approval token remains server controlled. Native Data Import remains available in authorized advanced views.

This extends the migration; it does not complete the remaining event, resource, attendance, finance/report, company-shell or public-portal owners. See REACT_INTERFACE_AUDIT_2026-11-03.md for current acceptance evidence and the explicit remaining scope.
