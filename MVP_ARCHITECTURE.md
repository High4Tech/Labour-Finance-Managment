# PLUS POINT — source-of-truth architecture

Updated 2026-10-17. Local development scope; production acceptance is separate. Actual test evidence is in VERIFICATION_STATUS.md. The original blueprint is preserved under docs/archive. RESEARCH_ALIGNMENT.md maps the owner's October 17 research handoff to the implementation and remaining gaps.

## Scope and non-goals

Customer setup is a small native Dialog flow with per-user server-stored progress (`pp_guided_setup_v1` user default). It creates normal Company/Employee/Project/Customer/Contract/PP Site/PP Contract Terms/PP Assignment records with native insert permissions and validations. Skip persists progress and only releases UI focus; it never changes staff permissions. The High4Tech site cannot call these endpoints.

`imports.py` supports bounded UTF-8 CSV and single-sheet XLSX snapshots, with schema-specific templates and reference-ID downloads. Parsing rejects formulas and oversized files/workbooks. A read-only row preview is cached for 20 minutes under a random token bound to its authenticated user, company and import type. Applying a preview rechecks permissions, data, ordered project locks and native posting rules inside one transaction. An internal immutable PP Import Record stores the company/type/source-ID hash and saved record reference. Company serialization plus its deterministic primary key prevents concurrent import replay. Repeated financial rows skip; changed posted rows reject; employees use explicit IDs and a restricted profile field set. Standard target document permissions, budget/tenancy hooks and GL submission are preserved. No bank API, external Sheets OAuth or invented opening balances are introduced. Cross-type concurrency stress and production role/privacy acceptance remain separate release work.

PLUS POINT supports labour contractors: client contracts, projects/sites, worker allocations, contractor attendance/dehadi, daily and fixed price billing, wages paid and operational profitability. High4Tech operates SaaS accounts. Reuse ERPNext/HRMS rather than rebuilding an ERP, payroll, authentication server, REST framework or payment gateway. Native mobile apps, biometrics and statutory payroll customization are outside this increment.

## Selected upstreams and versions

Exact repositories, release refs and commits are in upstream.lock.json. Frappe v16.51.1, ERPNext v16.51.1, HRMS v16.51.0, and frappe_docker commit 8242235e56dd80e15842cb4820b5b612805cf7fd. Official Bench (Python 3.14/Node 24), MariaDB 11.8 and Redis 7.4 images are pinned by digest in compose.yaml. Bootstrap verifies source commits and refuses implicit upgrades. Transitive dependencies follow upstream metadata/lockfiles; production requires an immutable scanned image.

## Reused features versus custom extensions

| Requirement | Owner |
| --- | --- |
| Client companies, agreements, projects | ERPNext Customer, Contract, Project |
| Employee records, standard HR and payroll | ERPNext Employee and HRMS |
| Invoices, payments, accounts, subscription billing | ERPNext Sales Invoice, Payment Entry, Subscription, Subscription Plan |
| Authentication, REST, roles, Desk, audit versions and schema migrations | Frappe |
| Site hierarchy, dated allocations, contractor attendance | PP Site, PP Assignment, PP Daily Register, PP Register Line, PP Work Entry |
| Billing policies and fixed earned revenue | PP Contract Terms, PP Milestone |
| Allocation of real employee payments to earned wages | PP Wage Settlement |
| Hosting directory and operational entitlements | PP Tenant and trusted local worker |
| Audited customer account assistance | PP Support Request, native RQ and native User security |

PP Work Entry records contractor economics; it does not recreate Employee/payroll. It does not automatically synchronize HRMS Attendance or override native leave/shift rules.

## Database relationships and validation

Tenant site/database -> native Customers/Contracts/Projects/Employees. Project links Company and Customer. PP Contract Terms links one Contract/Project pair. PP Site belongs to Project with optional same-project parent. PP Assignment links Employee, site/project/terms, dates and rates. PP Work Entry snapshots those references and rates. Submitted registers create approved work entries in one transaction. PP Milestone links fixed terms. Native Sales Invoice Item custom fields reference work/milestone sources. PP Wage Settlement links Employee, Project and a unique submitted native Payment Entry.

Historical rate snapshots are immutable; used assignment identities/rates/start dates and economic contract terms cannot be rewritten. A used assignment may close earlier only if all saved work remains within its dates; it cannot reopen or extend. Same-worker/same-site assignments cannot overlap (inclusive dates). Assignment then employee locks follow work insertion's order; the employee lock serializes overlap checks under the tested READ COMMITTED deployment. Different-site assignments can overlap for split days; work-entry validation enforces the aggregate day cap. Employee row locks also serialize settlement limits; terms locks serialize milestone caps and invoice reservations. No commits inside posting hooks. Queries used for totals disable default pagination. Native Version records retain changes. Production requires realistic large-volume profiling and audited attendance correction/reversal workflows.

## Daily wage and contract billing rules

Both required models are explicit: per worker-day billing and fixed price milestone billing.

Daily: earned wage = agreed snapshot wage rate × attendance units; client earned revenue = client rate × units. Units are 0, 0.5 or 1. Each employee may total at most one worker-day across sites on a date; employee/site/date cannot duplicate. Fixed: daily wages remain independent; worker-day client revenue is zero. Approved milestones recognize revenue; their combined value cannot exceed fixed contract value. Decimal arithmetic uses two currency decimals and half-up rounding. Custom terms and settlements use company currency only.

Always distinguish contract value, earned revenue, invoiced net/gross, receivable balances settled, outstanding balances, wages earned/paid/outstanding, other costs and operational profit. Settled invoices may include credit notes/write-offs; they are not automatically cash collected. Other costs use native Project purchase/expense-claim totals, excluding taxes, overhead and unallocated costs. Do not book the same contractor wage again as a project purchase/expense. Reports are operational contribution, not statutory net profit.

Invoice creation creates a native Draft for review and reserves sources. Draft deletion/cancellation releases them; submission marks milestones Invoiced. Duplicate sources, amount changes, returns, incorrect customer/project/company/currency and source removal are rejected. Native credit notes exist; partial source credits/rebilling need a dedicated adjustment workflow before commercial release. Wage settlements allocate full submitted employee Payment Entries and cannot exceed approved unpaid earnings. Native employee advances remain distinct. Operational earnings do not create payroll accrual journals automatically.

## Backend API architecture and UI

Native /api/resource/<DocType> supplies permission-checked CRUD. Authenticated custom methods: plus_point.api.prepare_daily_register (POST), worker_statement, project_summary; plus_point.billing.create_invoice (POST); plus_point.tenancy.account_status. The native Desk workspace links reused modules; site and terms forms add attendance/invoice/finance actions. No separate backend or frontend.

Two standard native Script Reports expose contractor results without a new reporting UI. PLUS POINT Project Finances reuses project_summary and offers lifetime financial or deployment views by legal company/client/project/status, including completed projects. PLUS POINT Worker Statement reads approved work, dated submitted native employee payments and their settlements for running opening/period/closing balances, plus an assignment-history view. Both require System Manager and normal document permissions, reject control-plane execution, and keep one company/currency per report. Native report permissions, table controls, printing and export are reused. Project/site/date profitability is not fabricated where native cost and milestone data cannot support that attribution.

Initial tenant operations use native System Manager. Dedicated supervisor/finance roles, wage field privacy and site-scoped User Permission regression tests remain production requirements.

Desk onboarding is an app-owned JavaScript/CSS extension loaded through native hooks, using Frappe's existing Dialog, Driver tour and Bootstrap tooltip facilities. It explains app boundaries and the contractor workflow, adds a context-aware route home, and reads native DocField descriptions for field tips. Tenant home presents common tasks first, with setup records and the six-step guide collapsed initially. Mark attendance uses permission-checked native queries to reopen a saved site/date register, or calls the existing prepare_daily_register method to create a draft; submission remains an explicit native form action. A small boot hook distinguishes the control-plane site from tenant sites. The quick-start preference is optional, browser-local and keyed by hostname plus logged-in user; it is not an authorization or business-state flag.

Tenant migration installs a native site-level Custom Sidebar only when no operator layout exists, preserves per-user sidebar choices, and supplies default link-title Property Setters for Employee/Project only if none exist. An empty site default_app becomes plus_point; explicit preferences are preserved. Tenant custom lists show familiar labels and omit the internal name column/filter, while backend names and references remain intact. The native sidebar still filters entries by document permissions. Platform navigation is excluded from these tenant changes. USER_GUIDE.md describes the workflow; UX_DESIGN.md records the design reasoning and limits.

The boot extension sets native `on_apps_screen=False` on engine app entries, leaving their route/dock metadata intact. Customer sites show one PLUS POINT product entry; the control-plane site shows one High4Tech admin entry. This is presentation, not access control. Shared HR/account/user tools remain native and are linked within the customer workspace, subject to existing permissions. Guides distinguish the two product sides and present platform-specific steps on the control plane.

## Tenant isolation and permissions

Native Frappe site per tenant with distinct MariaDB database/user. Validated Host selects the site; browser tenant IDs never select another database. The separate platform.localhost site requires pp_control_plane=true and High4Tech Platform Admin for registry mutations. A role on a tenant site grants no platform access or automatic cross-site support login. Development Administrator is a bootstrap identity; production needs named users and MFA.

## Subscription lifecycle

Reuse ERPNext subscriptions/plans, invoices and manual Payment Entry confirmation. PP Tenant records organization/contact, subscription, suspension and active-user/worker/site limits. A trusted same-host operator worker runs outside HTTP, creates native sites and installs pinned apps. Every 60 seconds it synchronizes Active/Trialing/Grace Period eligibility and explicit period expiry to protected tenant site_config. Expired/suspended/unpaid/cancelled sites reject document writes while retaining read-only access. Limits include reactivation and use row locks. No configured entitlement means uncontrolled Development mode; all commercial tenants must use provisioning. Missing expiry on a configured entitlement fails closed.

Tenant web users cannot edit site_config. Hooks cover standard insert/save/submit/cancel/delete and allow audit/auth infrastructure records. Audit privileged upstream methods that write SQL directly before commercial release; hooks are not proof of universal enforcement. Same-host configuration avoids premature remote signing infrastructure; multi-host deployment needs authenticated agents and signed short-lived entitlements. Suspension propagation takes up to one worker interval. The worker never deletes sites. Production needs observable job state, unique onboarding credentials and recovery tooling.

Controlled development billing uses native manual workflows with no external money movement. Production must use an ERPNext-supported Payment Gateway Account adapter, verified webhooks and idempotency; never build a card processor.

## Press evaluation and decision

Press already supports sites, hosting operations, billing and backups. Its official architecture includes Agent, Docker and Ansible, expanding operating/maintenance scope beyond this single-host pilot. Defer adoption; revisit before multi-host self-service hosting instead of rebuilding general hosting infrastructure. No recurring hosting price is asserted. Press is AGPL-3.0; modified network-served versions carry corresponding-source obligations under its terms. Preserve notices and review final deployment/distribution obligations before commercial use. Frappe is MIT; ERPNext/HRMS are GPL-3.0. Our MIT app does not relicense upstream code.

Sources: https://github.com/frappe/press ; https://github.com/frappe/press/blob/master/license.txt ; https://docs.frappe.io/erpnext/subscription ; https://docs.frappe.io/framework/user/en/basics/sites .

## Local deployment and security

Windows Docker Desktop Linux engine; loopback web/socket ports; private database/Redis network; persistent named bench/database volumes; editable app bind mount. Ubuntu integration is unnecessary. Fresh local secrets are generated into ignored .env and never printed/committed. Do not expose developer containers or reuse local credentials commercially. Back up using native bench backup --with-files and copy backups to private off-host storage. Volumes are not backups; backups/site configs never enter Git.

## Production direction and cost

Build an immutable custom image with the pinned official frappe_docker layered build. Shared web/workers/scheduler/socket/frontend services with many isolated sites can start on one appropriately sized Linux host; separate servers per tenant are unnecessary. Add TLS, protected admin network, monitored queues/errors/disk, persistent MariaDB/sites, private Redis, encrypted offsite backups, retention and tested restores. Size capacity from measured workload. Production manifests, restore drills, monitoring and independent security review remain incomplete. Never deploy the disposable pwd.yml demo or this developer image commercially.

## Acceptance criteria and technical decisions

Phase 1: healthy services, pinned installed apps, real DB/login/REST CRUD/frontend. Phase 2: relationships, allocations, bulk attendance and historical snapshots verified in MariaDB. Phase 3: daily/fixed revenue, invoice reservation/posting/cancellation, worker payments and labelled operational profit verified. Phase 4: separate tenant/platform DBs, native subscriptions, provisioning, quota/expiry/suspension/reactivation and cross-site access rejection verified. Phase 5: browser workflow checks, concurrency, permission/privacy, correction workflows and backup/restore pass.

Do not mark whole phases complete because scaffolding, synthetic HTTP tests or offline arithmetic pass. Record evidence and gaps in VERIFICATION_STATUS.md. Preserve Git history; use a tested review branch with descriptive commits and no force push. Existing foundation files remain archived. Architecture choices favor maintained upstream software and a small extension surface.

Client cash reporting separately sums submitted native Payment Entry allocations to company-currency project invoices, net of refunds; unallocated and FX receipts are explicitly excluded. The High4Tech workspace links the native tenant/subscription/plan/user/accounting screens. Local owner accounts reuse native roles and development credentials; production invitations remain a release gate.

## Transaction isolation refinement

The pinned MariaDB 11.8 image enables InnoDB snapshot isolation. Simultaneous worker-day writes exposed error 1020 under REPEATABLE READ. compose.yaml therefore explicitly selects READ COMMITTED, and financial duplicate/cap checks use current locking reads with employee/contract serialization. This setting is part of the tested deployment contract; preserve it in production. Ten simultaneous draft attendance requests produced one creation and nine validation rejections, with all temporary drafts deleted. Larger mixed-workload/deadlock testing remains required. Native site encryption keys are initialized before web startup to avoid stale configuration during first API-key generation.

Reference: https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-system-variables#innodb_snapshot_isolation .


## Focused products and account support — October 17

Boot context supplies one curated native module sidebar per site. PLUS POINT contains contractor operations and related setup. High4Tech contains software customers, pricing/subscriptions, support and software-business accounting. Native command suggestions are filtered; unrelated Desk routes return to the product home. Presentation does not replace native permissions. Broad development manager roles remain a production review item.

PP Support Request requires a control-plane site and High4Tech Platform Admin. Creation binds target site/email from PP Tenant rather than request-supplied identities. Requests are immutable after creation. Native RQ processes an isolated customer-site Bench subprocess after rechecking the registry. The child helper is not whitelisted and refuses web/control-plane execution and built-in accounts. Login-ID changes use native User validation and its unique index for an identity-only update; suspended business writes remain blocked. Reset uses native User generation and session invalidation, with no email. Completion uses the unchanged native password-reset endpoint, including strength, expiry, hashing and single-use checks. Reactivate suspended subscriptions before completing the native reset form.

Reset URLs are encrypted in native __Auth, masked in DocType REST data and retrieved only by authorized platform admins for 20 minutes. Hourly cleanup removes expired encrypted results. Child stdout stays in memory and errors are redacted before logging. No plaintext old passwords, keys in process arguments, new credential store or independent authentication implementation is introduced. This local same-host bridge supports registered .localhost customer owners. Remote-host support, verified support identity procedures and email delivery remain production work.

Native software Subscription Plan → Subscription → Sales Invoice → Payment Entry → GL is tested with rollback. Native profit/loss and receivable reports expose High4Tech finances. Local external HTTP tests cover independent databases and the support bridge; public SaaS, email and payment-provider connections are not claimed.


## Company dashboards

`plus_point.dashboard.overview` is a read-only native RPC. Customer access requires System Manager; platform access requires the control-plane flag and High4Tech Platform Admin. Companies and all source records use native permission-checked lists. Unknown/inaccessible company selection is rejected. Customer figures reuse the existing project financial report, not a second accounting formula. Counts/attendance cover the selected company and its contractor projects. The last seven days include approved work only, with fractional worker-days preserved.

Platform figures use native posted Sales Invoices and customer Payment Entries in company currency. Monthly invoicing includes taxes and credit notes, cash includes unallocated receipts net of refunds, and future posting dates are excluded from the current-month/six-month series. Outstanding invoices are positive base-currency outstanding balances across posted invoices. Customer access status follows the same subscription period/suspension calculation as provisioning. No MRR, profit or paid-customer status is inferred from trials. Company access is authoritative, not browser-supplied currency or role values.

The existing home tools remain below summary metrics, a native-theme chart and a project/customer table. The company selector and Refresh figures read saved data; revisiting home reloads it. Loading, permission/error/retry and empty-company states keep the existing tools usable. No new dependencies, background polling or business writes are introduced.


## Operational spending control and state feedback

The owner clarified that a separate spending budget is required, rather than a client billing limit. Reuse native Project.estimated_costing, labelled Spending budget on customer sites, with an explicit native Custom Field pp_enforce_spending_budget. It starts disabled; System Manager controls budget/stop changes through native Project saves and their history. Fixed client values and approved milestone caps remain unchanged.

plus_point.budget sums approved PP Work Entry wages, submitted Purchase Invoice Item base_net_amount and approved/submitted Expense Claim Detail base_sanctioned_amount, using row project or parent fallback. Rejected/cancelled claims and draft/cancelled invoices are excluded; tax, overhead, timesheet, stock and unallocated costs are outside this operational measure. Existing project_summary now reads these posted expense sources directly so report spending is not dependent on cached Project update frequency. No worker payment is counted a second time.

Project row locks serialize cost increases. New draft-work snapshots lock Project before Assignment/Employee; approval and whole-register checks take that same project lock before comparing totals. Purchase/claim submission and allowed post-submit updates lock affected projects in sorted order and exclude their existing contributions before evaluating replacement costs. The register checks its whole proposed amount before creating work entries. Server validation rejects increases above the enabled limit, even through REST; cost reductions and zero-cost records remain allowed during an existing overrun. Changing a budget below existing costs retains those costs and shows an overrun rather than rewriting history.

The read-only, manager-only budget preview validates the supported document type and project/document permissions. Native client before-submit/approval events stop over-budget actions and require explicit acknowledgement between 80% and 100%. Preview is guidance; it does not authorize or bypass server validation. Native accounting budgets and other upstream validations remain in place. Form results and dashboard conditions each include a next action, with text and colour for warning/error/success/empty states. Error retry does not remove normal work tools.
