# Company frontend migration — 9 November 2026

The default company app and public client agreement/progress portal now have React/TSX screen owners. The remaining company flows from the previous checkpoint have been migrated. Python/Frappe/ERPNext/HRMS still own authentication, permissions, document validation, payroll, accounting, stock and existing APIs.

This is a company-interface migration, not a rewrite of every installed framework screen. Authorized advanced accounting/stock/report views and platform administration intentionally remain native, as requested. Native route hosts, CSS, Jinja entry documents and isolated rendering engines are not duplicate company screen owners.

## Screen ownership

| Area | React owner and backend boundary |
| --- | --- |
| Dashboard, notifications and shared shell | Dashboard, charts, skeleton, tables, activity, header/sidebar portals, anchored search, currency/theme/account menus and notification preview. Existing dashboard and preference APIs. |
| Agreements and clients | Lists, client profiles/editors, agreement creation/editing/profile, requirements, milestones, approval proposals, sharing, documents and imports. Existing agreement, billing, draft and client APIs. |
| Jobs & Events | List, new/edit three-step form, saved profile, venue requirements, worker/pay selection, auto-selection, bulk pay changes, transport, documents, shared staffing calendar and review. Existing event controls and native allocation/transfer validation. Saved list links open the profile; Edit explicitly opens the editor. |
| Workers | List/profile/editor, salary/leave/loan controls, assignments and photo upload entry. Existing Employee, attendance, assignment and loan controllers. |
| Attendance | Register list, opening picker, roster, marks, draft/approval, budget previews and corrections. Native payroll/attendance rules remain authoritative. |
| Equipment, warehouses and vehicles | Shared lists, profiles, editors, quantity/bulk stock changes, availability, reservations and conflicts. Reserved quantities remain read-only; native stock reconciliation and capacity checks enforce writes. |
| Billing and accounting | Billing workspace; Payment Entry, Sales Invoice, Purchase Invoice and Expense Claim lists/forms; branded PDF preview. Native save/submit, ledger posting, account currency and revision checks. Advanced tax/allocation controls use an explicit native handoff. |
| Worker payments and loans | Bulk confirmation, optional/later references, payment timing, manual wage-payment link, loan list/profile/create and recovery history. Shared FinanceRecord also handles PP Wage Settlement; native submitted Payment Entry validation computes settlement amount. |
| Reports | Project finances and worker statement filters, summaries, tables and export. A narrow adapter calls the installed native report engine with company scope. |
| Utilities | Deletion/blocker cards, assignment moves, help, private upload, section preferences and both resumable onboarding entry points. Existing authorized APIs/controllers remain in place. |
| Client portal | Agreement review, signer fields/consent, signing and confirmed event progress in shared React components. Existing token, expiry, revocation, signature and guest-access checks. |

## Component and lifecycle ownership

Recurring controls reuse Button, Field, Input, Select, RadioGroup, Checkbox, Panel, DataTable, Badge, Dialog, Feedback, SummaryCards and DocumentPreview. Rich text owns an isolated Quill instance; the optional event-world canvas and setup map initialize only in their relevant owner and dispose on close/departure. The event-world test verifies real on-demand loading, pause and cleanup.

There is one active screen root and one persistent shell root; temporary dialog roots/portals belong to their opener and dispose on dismissal. Relevant realtime messages are coalesced; there is no recurring full-page polling. Read requests reject stale responses and abort on departure. Current financial reads and all posting decisions remain server checked. Empty new defaults do not create a draft.

Only proven unreachable private PLUS POINT presentation helpers were retired. Native DocTypes, hooks, controllers, reports, permissions, stock/accounting infrastructure and integrations were preserved. Old local hashed chunks remain on disk for already-open tabs; the release manifest publishes only the current dependency graph.

## Verification and practical limits

Strict TypeScript, production build, 29 frontend unit tests and 187 backend regression tests passed. Sixteen browser suites cover the company screens, shared utilities and client portal; focused checks include native event-URL redirects, profile versus editor routing, payment selection/consent, inline errors, mobile/dark bounds and lifecycle cleanup. See [the verification report](REACT_VERIFICATION_2026-11-09.md) for evidence and limitations.

Across 26 repeat list visits, measured warm readiness was 125–279 ms (median 184 ms), without growth in DOM count, active screen roots or list listeners, and without duplicate native list queries. Initial readiness still measured 3.762 seconds. This completes the remaining default-screen ownership migration, but does not establish that every cold-start performance objective is achieved. React alone does not eliminate lifecycle or loading problems.

## Storage move

The source checkout was already physically at `D:\Labour-Managment-Software\Labour-Finance-Managment`. Docker's shared storage was still on C:. After explicit user approval, Docker Desktop's supported disk-image migration moved it to `D:\DockerDesktop\DockerDesktopWSL\disk\docker_data.vhdx`. The main image is at `D:\DockerDesktop\DockerDesktopWSL\main\ext4.vhdx`.

Docker restarted through its migration workflow. The app, MariaDB and both Redis containers are running; the HTTP API responds. Source bind mounts resolve to the D: checkout. The previous C: Docker WSL images are absent. C: had about 39 GB free at final inspection; free space fluctuates with other processes.

A pre-move main-site database/public-file/private-file/config backup is retained at `.local/backups/storage-move-20261108/`. It is ignored by Git, as are tenant data, configuration secrets and Docker disks. Tool installations and unrelated application caches on C: were not relocated.

## Release boundary

Source and generated production chunks are versioned together. Browser financial writes and email delivery were intercepted; actual native posting/security regressions ran on the separate QA site. No real client email or main-account payment was sent by these checks. Test artifacts, credentials, tenant data and backups remain ignored by Git.
