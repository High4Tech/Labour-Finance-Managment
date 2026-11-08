# React migration and D: storage checkpoint

The migration is **not complete**. This checkpoint adds React ownership for attendance registers, inventory/equipment, warehouses, vehicles, resource reservations, billing, receipts/payments, supplier invoices and employee reimbursements. The Python/Frappe/ERPNext/HRMS backend remains in place. Native advanced accounting, stock, reports and exports remain accessible.

## Completed owners

| Area | React interface and existing backend boundary |
| --- | --- |
| Attendance | Shared register list, roster, full/half/absent marks, draft, approval, budget preview and correction flow. Native register controllers and payroll rules remain authoritative. The opening event/site/date picker remains a native adapter. |
| Equipment | Shared list, profile, warehouse locations, availability, hire price and reservations. Authorized advanced Item views remain available. |
| Warehouses | Shared list/profile, owned/rented status, editable stock quantities and bulk changes. Reserved quantities are read-only. Native Stock Reconciliation records changes, with server time, expected-quantity checks and reservation protection. |
| Vehicles and reservations | Shared list/profile, availability, vehicle/equipment booking dialog, capacity errors and bulk reservation cancellation. Event/site/date choices use existing scoped APIs. |
| Billing | Agreement billing workspace, real financial summaries, payment schedule, invoice creation/editing/posting, branded PDF preview, email configuration and delivery actions. Browser tests do not send mail. |
| Accounting records | Payment Entry, Sales Invoice, Purchase Invoice and Expense Claim use shared React lists and metadata-backed forms. Native create/save/submit, posting rules, account currencies and document revisions are enforced. Advanced allocations/taxes are explicitly handed to the native view instead of discarded. Unsaved edits survive the round trip. |

Lists preserve contextual event/project filters, company boundaries and native permissions. Each active screen has one owner. Legacy resource/finance list decorators run only in an explicit advanced view; they cannot race React preparation and initialize a second table. These interfaces reuse the existing Button, Field, Select, Dialog, Badge, Panel, DataTable, SummaryCards and DocumentPreview components.

Private PDF previews accept a stored file or a native print request through the same component and revoke object URLs on close/unmount. Native print preview does not create an attachment merely by opening it. File/photo upload controls remain documented native widget adapters.

## Verification

- Strict TypeScript, production build and all 22 frontend state tests passed.
- All 19 new rollback-only backend tests passed on `qa.localhost`: native receipts and invoices/ledger posting, expense claims, schema/company permissions, contextual project filters including expense child rows, stale revisions, protected accounting fields, private print permissions and stock/reservation invariants.
- Resource browser checks passed for all three list/profile/create/edit flows and an event/site/vehicle reservation. A simulated server conflict stays in the dialog and marks the relevant field. Main-site writes were intercepted.
- Accounting browser checks passed for all four shared forms, inline required-field errors, billing/invoice dialogs, advanced-view round trip, mobile/dark dialog bounds, Escape and screen disposal. The idle accounting form made zero requests during the measured 3.5-second interval.
- Worker Payments passed 14 browser checks, including review selection, multi-event bulk consent, optional references, later reference editing, duplicate activation lock and native advanced history. The test's old expectation of zero roots on Item was updated because inventory now has its own React owner.
- The actual attendance QA lifecycle passed after the Docker move: register preparation, marks, draft/approved totals, budget blocking, duplicate prevention, worker earnings, responsive dark layout and fixture cleanup.
- Across 13 migrated list types and 26 repeat visits, warm readiness was 135–406 ms, median 235 ms. DOM nodes stayed at 13,070, active roots at one and list listeners at one; duplicate native list queries and unhandled browser errors were zero. Collected heap rose from 22.65 MB to 23.99 MB. This is bounded-run evidence, not proof of no memory growth.
- The latest standalone cold payment load measured 3,848 ms and 9,426,288 decoded JS/CSS bytes. Earlier checkpoints were faster on cold load; these samples do **not** establish a cold-start improvement or acceptance of the full performance objective. Separating the company entry from unrelated Desk presentation remains required.

Ignored test reports/screenshots are under `.local/qa/react-*`, with focused logs under `.local/`. No main-site financial record was posted by these browser checks.

## Storage move

The source checkout was already physically at `D:\Labour-Managment-Software\Labour-Finance-Managment`. Docker's shared storage was still on C:. After explicit user approval, Docker Desktop's supported disk-image migration moved it to `D:\DockerDesktop\DockerDesktopWSL\disk\docker_data.vhdx`. The main image is at `D:\DockerDesktop\DockerDesktopWSL\main\ext4.vhdx`.

Docker restarted through its migration workflow. The app, MariaDB and both Redis containers are running; the HTTP API responds. Source bind mounts resolve to the D: checkout. The previous C: Docker WSL images are absent. C: had about 39 GB free at final inspection; free space fluctuates with other processes.

A pre-move main-site database/public-file/private-file/config backup is retained at `.local/backups/storage-move-20261108/`. It is ignored by Git, as are tenant data, configuration secrets and Docker disks. Tool installations and unrelated application caches on C: were not relocated.

## Still remaining

Event creation/editing/detail, staffing/pay selection and the shared calendar still use legacy owners. Worker loans/recoveries, product reports, parts of the company shell/search/help/onboarding/preferences and the public client signing/progress portal still need complete React ownership. Native file/photo upload widgets and the attendance opener remain explicit boundaries. The optional scene remains on demand. Do not describe the whole frontend as React until these flows and their regressions are completed.

No framework backend module, DocType, ledger, hook, controller or integration was removed. Only proven unreachable private resource presentation helpers were retired after their consumers moved to React.
