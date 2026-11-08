# Frontend/backend verification — 9 November 2026

## Result

The company app has a working React/TSX component layer connected to the existing Python/Frappe APIs, but the whole frontend is **not yet React**. The remaining interfaces below must be migrated before making that claim. This audit verifies the current supported paths; it does not certify every possible record, permission combination or external email/payment integration.

Installed runtime: Frappe 16.51.1, ERPNext 16.51.1, HRMS 16.51.0 and PLUS POINT 0.4.0. React 19.3.1 and TypeScript 7.0.2 are declared in `frontend/package.json`. No backend framework, DocType, permission check, ledger or integration was removed.

## Ownership

| Interface | Current owner |
| --- | --- |
| Dashboard, agreement form/profile, workers, clients | React/TSX with shared components |
| Agreement/event lists, worker payments, notifications, imports | React/TSX with existing scoped APIs |
| Attendance register list and marking/approval | React/TSX; native attendance-opening picker remains an adapter |
| Equipment, warehouse and vehicle lists/profiles/editors/reservations | React/TSX; native stock controllers remain authoritative |
| Billing workspace, Payment Entry, Sales/Purchase Invoice, Expense Claim | React/TSX; native accounting save/submit/posting APIs |
| Event form/profile, staffing/pay pickers and calendar | Legacy PLUS POINT JavaScript/native form ownership; event list is React |
| Worker loans/recoveries, product reports | Legacy ownership remains |
| Parts of shell/search/help/onboarding/preferences, public client signing/progress portal | Legacy ownership remains |
| File/photo upload/pickers and authorized advanced framework views | Documented native adapters/views remain available |

CSS is still used to style React components. Its presence is not evidence that a screen is unmigrated; runtime ownership and source consumers are the checks used here.

## Fixes from this audit

- Saved event names and Open actions now open the event detail profile, including records whose planning state is Draft. A saved record's unfinished edit draft no longer takes over its list link. Projected unsaved drafts still resume their form. Edit event explicitly opens the editor; opening a detail profile does not finalize the event.
- Removed the second event-renderer override that forced saved Draft events into editing, even when the route requested the profile.
- Selected agreement tabs now use the shared accessible brand-text token. The browser audit caught insufficient contrast in both light and dark modes; both pass after the change.
- Corrected obsolete browser assertions that expected no React owner on inventory or agreement creation. The assertions still verify one active owner and cleanup instead of permitting duplicate roots.
- Bumped asset versions and cleared the server asset cache to serve the current route and style code.

## Tests actually run

| Check | Result |
| --- | --- |
| Strict TypeScript and production build | Passed |
| Frontend state/navigation unit tests | 24 passed |
| Architecture/backend workflow suite on QA | 321 passed, 0 failures/errors, 615.48 seconds |
| Accounting/resource backend tests on QA | 19 passed, 0 failures/errors |
| Browser suites | All 12 passed: foundation, dashboard, layout, planning, workers, clients, agreements, agreement builder, worker payments, imports, resources and finance |
| Event navigation regression | Saved Active and saved Draft records open profiles; explicit Edit opens the form; no unhandled JavaScript errors |
| Actual QA attendance lifecycle | Passed roster generation, three attendance states, draft/approval separation, budget stop, exact wages/revenue, duplicate protection, worker summary and mobile/dark fit |
| QA cleanup | Test records removed and original workspace/appearance restored |

The architecture suite covers agreement/event creation, sharing, drafts, planning, crew allocation, attendance, finance, currency rules, deletion and component validation. Browser suites include shared table selection, field validation, error retention, responsive/dark dialogs and screen disposal. Company-site browser financial writes are intercepted; real posting/attendance tests run on the disposable QA site. Email was not sent and no live payment was executed.

The initial browser pass had two failures: an obsolete foundation ownership assertion and the real agreement-tab contrast failure. Focused reruns after correction pass, and the aggregate report records all 12 final results. Detailed ignored artifacts are in `.local/qa/react-audit/`, `.local/qa/event-detail-navigation/` and the associated `.local/react-audit-*.log` files.

## Performance limits

The final read-only lifecycle measurement visited 13 migrated list types, then repeated 26 visits:

- Warm list readiness: **132–239 ms**, median **181 ms**.
- One active React root and one list-update listener before and after.
- DOM count stayed at **13,070**. Duplicate native list queries and unhandled browser errors: **zero**.
- Collected heap increased from **22,687,089** to **24,069,722 bytes**. This bounded run does not prove absence of a memory leak.
- Cold worker-payment readiness: **3,196 ms**, with **9,426,264 decoded JS/CSS bytes** across the measured page/session. This still needs improvement; it is not a claim that the performance objective is complete.

React alone does not prevent stale selection, polling or retained screens. These are lifecycle/cache ownership problems and need direct measurements. Remaining legacy screen migration and a lighter company entry remain necessary.

## Storage

Source is on `D:\Labour-Managment-Software\Labour-Finance-Managment`. Docker's data disk exists at `D:\DockerDesktop\DockerDesktopWSL\disk\docker_data.vhdx`; the prior C: Docker data disk is absent. The database and uploaded files remain in Docker volumes. Backups are private, ignored by Git, and retained under `.local/backups/`.
