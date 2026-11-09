# Frontend/backend verification — 9 November 2026

## Result and scope

Default company screens and the client signing/progress portal now use React/TSX owners connected to the existing Python/Frappe APIs. The remaining event, loans, reports, shell, utilities and portal interfaces from the previous checkpoint have been migrated. This does not mean every installed ERPNext/HRMS or platform-administration screen has been rewritten: explicitly authorized advanced views remain native by design.

Installed runtime at this checkpoint: Frappe 16.51.1, ERPNext 16.51.1, HRMS 16.51.0 and PLUS POINT 0.4.0; frontend dependencies pin React 19.3.1 and TypeScript 7.0.2. Authentication, permissions, DocTypes, native controllers, accounting/stock ledgers and integrations remain intact. See the [ownership ledger](REACT_MIGRATION_2026-11-09.md) and [component contract](REACT_COMPONENT_CONTRACT.md).

CSS still styles React components; JavaScript route adapters still connect Desk routes. Neither implies that the default screen renders a second legacy interface. Runtime ownership and actual consumers were audited, rather than judging migration from filename extensions or visual differences alone.

## Fixes and completed paths

- Saved Jobs & Events links, including saved Draft records and native blocker-record URLs, open the React detail profile. Explicit Edit opens the React editor; projected unsaved drafts resume creation. An unfinished edit draft cannot silently replace the saved profile route.
- Events now share React creation, venue/staff/pay controls, auto-selection review, monthly-profile pay, assignment moves/releases, reservations, calendar, documents and profile sections. Existing backend allocation, budget and commercial-confirmation guards remain enforced.
- Loans/recoveries and both product reports have React owners with company-scoped native read/posting boundaries.
- The shell, search/notification overlays, help, attendance opener, deletion blockers, private uploads, preferences and resumable onboarding use shared React components. A legacy breadcrumb spacing rule was corrected in the shared header and has a regression check.
- Manual wage-payment linking now uses the same metadata-backed FinanceRecord form. Submitted employee-payment checks and amount calculation remain native; posted references use the shared reference dialog.
- Client review/signing/progress uses the same React tabs, fields, feedback and status primitives. Shared owned-root styles prevent public pages from falling back to browser-default controls.
- The event-world canvas remains on demand, pauses correctly, and releases its canvas/listeners/timer when closed. No world assets initialize on ordinary dashboard/app startup.
- Native advanced forms have an explicit return to the company interface. No backend capability was removed to improve presentation.

## Checks performed

| Check | Final result |
| --- | --- |
| Strict TypeScript and production build | Passed |
| Frontend state/validation unit tests | 29 passed |
| Current backend regression run | 187 passed, 0 failures/errors; 418.532 seconds |
| Existing browser suites | Foundation, dashboard, layout, planning, workers, clients, agreements, agreement builder, worker payments, imports, resources and finance passed |
| Event browser suite | 7 passed: saved profile/tabs, worker/pay controls, menus, real lazy scene lifecycle, editor, empty-new-draft behavior and mobile cleanup |
| Migration browser suite | 6 passed: loans, real balance/profile, both reports, navigation snapshot and invalid public token |
| Utility browser suite | 22 passed: shared shell/search, collapse, notification/help dismissal, attendance validation, deletion, native event URL, upload, payment form/reference, all ten onboarding stages and mobile bounds passed |
| Client portal browser suite | 4 passed: review/consent, one acceptance POST, signed state/progress, mobile viewport |

The 187-test backend run covers hierarchy, agreement architecture, consolidated workflows, event controls/start, component validation, full workflow, drafts, planning, payments, dashboard analytics, finance records and new React transport adapters. It includes real QA accounting/ledger posting and permission/cross-company checks. A test harness fix restores the test flag correctly so scheduler work cannot invalidate rollback savepoints; fixture agreement names are unique.

Browser financial mutations, uploads, setup writes and client acceptance were intercepted where needed to protect the main account. The valid-signing browser test verifies the frontend request/state transition, not an actual client signature. Native signature/token expiry/revocation/security and financial posting were exercised separately on QA. Email delivery and external bank/payment-provider integration were not tested by sending a real message/payment.

Detailed ignored artifacts live under `.local/qa/react-*`. Final focused logs include `react-migration-regressions.log`, `react-final-unit.log`, `react-scene-final.log`, `react-migration-browser.log`, `react-utilities-final.log`, `react-portal-browser.log`, `react-payments-final.log`, `react-finance-final.log` and `react-layout-final.log`.

## Performance evidence

Read-only lifecycle measurement across 13 list types and 26 repeat visits:

| Measurement | Result |
| --- | --- |
| Warm list readiness | 125–279 ms; median 184 ms |
| DOM nodes before/after | 13,178 / 13,178 |
| Active screen roots before/after | 1 / 1, plus the persistent shell owner |
| List-update listeners before/after | 1 / 1 |
| Duplicate native list queries | 0 |
| Unhandled browser errors | 0 |
| Collected heap before/after | 22,828,647 / 24,395,053 bytes |
| Initial payment-screen readiness | 3,762 ms |
| Decoded JS/CSS observed in that page/session | 9,438,059 bytes |

These samples show stable measured screen/list ownership and fast warm navigation. The modest heap increase is not proof of no leak. Earlier initial-load samples ranged from about 3.2 to 3.85 seconds, so there is no demonstrated cold-start improvement. The preserved Desk framework still contributes significant initial assets; a lighter isolated company entry remains a separate optimization opportunity. Do not describe all performance work as finished or attribute the original slowdown simply to HTML/CSS.

## Storage and release safety

Source is on `D:\Labour-Managment-Software\Labour-Finance-Managment`. Docker storage is on `D:\DockerDesktop\DockerDesktopWSL\disk\docker_data.vhdx`; the previous C: Docker data disk was verified absent in the storage checkpoint. Database/uploads stay in Docker volumes. Private backups and credentials are ignored by Git. No blanket deletion of native features or tenant financial history was performed.
