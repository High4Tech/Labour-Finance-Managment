# PLUS POINT — MVP Architecture & Product Boundaries

**Status:** Architecture decision record / implementation blueprint, 2026-10-16.
**Canonical target repository:** `High4Tech/Labour-Finance-Managment`
**Current implementation state:** Foundation/bootstrap and test harness; SaaS and workforce modules **not yet implemented**. Do not describe this repository as production-ready.

## 1. Mission and boundaries

PLUS POINT is a multi-tenant subscription SaaS for companies managing contracted labour, client companies, projects/sites, worker assignments, daily wages (`dehadi`), client billing, payments, and profit. Platform operations belong to **High4Tech**; a customer's operational records belong to that customer alone.

### Day-one MVP business capabilities (IN scope)
1. Tenant onboarding by platform admin; subscription plans, billing cycle, trial/grace/suspended status, seat/worker/site limits, platform user/tenant administration, and tenant-level admin accounts.
2. Client companies and contacts; contracts under clients; multiple projects and sites per contract (site types include Main Site, Compound, Warehouse).
3. Worker roster, skills/categories, date-effective wages, dated site/project assignments.
4. Bulk daily attendance for a site and date (present/absent/half-day, reversible corrections with audit). Labour cost is calculated from approved work, not a payroll summary manually entered afterward.
5. Client billing models: **(a) per worker-day** by category/rate agreement, **(b) fixed price** by explicitly approved contract milestones. Each contract declares its model; do not silently change it after billing.
6. Wage earned vs wage paid/outstanding; billable earned vs invoiced vs cash collected; project expenses; project/site/client/worker reports and closure statements.
7. Roles: platform super admin; tenant owner/admin; dispatcher/supervisor; finance/accounting viewer/editor (least privilege).
8. Import/export CSV, immutable history of approved financial postings, documented backup/restore.

### NOT in MVP
Native apps, facial recognition, GPS/QR, transport, accommodation, advanced payroll taxes and statutory compliance, recruitment, supplier procurement, AI features, public client portals, complicated timesheet scheduling, auto bank integrations, production payment gateway, multi-currency accounting. These require a separately approved extension/phase.

## 2. Technology decisions

| Layer | Choice | Rationale |
|---|---|---|
| Framework | Frappe Framework v16 (`version-16`), Python | App lifecycle, DocTypes, permissions, jobs, migrations, REST APIs |
| Business modules | ERPNext v16 + Frappe HRMS v16 | Clients, project accounting, invoices, payment entries, employees and attendance |
| Data | MariaDB (site/database per tenant) | Native Frappe tenancy; better isolation than inventing row-level tenancy inside ERPNext |
| Queue/cache | Redis | Native framework dependency |
| UI | Frappe Desk first; Vue/Frappe UI for high-frequency attendance/custom SaaS pages later | Fast validation, avoid two independent backends |
| Local environment | Official `frappe/frappe_docker` **devcontainer**, not `pwd.yml` demo | Editable dev setup |
| Production | Custom app baked into official Frappe Docker image, persistent MariaDB/sites, offsite backup, reverse proxy+TLS | Reproducible cheapest viable VPS start |
| API | Frappe native REST/resource and authenticated methods | Do not create redundant Express/Supabase data server |

No ERPNext fork unless a hard requirement demonstrably cannot be met by app hooks/DocTypes. Pin tested upstream commits/releases before first deployed tenant; avoid unchecked auto-upgrades.

## 3. Multi-tenant SaaS and subscription control

### Isolation / topology
```
Internet -> TLS Reverse Proxy -> one shared Frappe bench (web/workers/cache)
                                 |-- platform.pluspoint.example (Frappe control-plane site; own DB)
                                 |-- alpha.pluspoint.example    (ERPNext+HRMS+PLUS POINT tenant; own DB)
                                 `-- beta.pluspoint.example     (ERPNext+HRMS+PLUS POINT tenant; own DB)
                                MariaDB: one distinct database + db user per Frappe site
```
A **platform site** is deliberately separate from all client sites, with isolated databases per subscriber. Platform super admins are not global tenant administrators. Their platform rights do not automatically confer permission to inspect a tenant's worker/financial details. Support access must be separately approved, time-limited and audited.

Do not model multi-tenancy by just adding `tenant_id` fields to existing ERPNext tables; doing so would create serious access-control and reporting risks. No cross-tenant SQL queries. Resolve customer by validated site host, not a client-supplied `tenant_id`. Site creation/deletion/restore are administrative workflows performed by a protected internal provisioning worker, never by arbitrary web requests.

### Control-plane DocTypes (new custom Frappe app; to implement)
- **PP Tenant**: ID, hostname, tenant site ID, provisioning state, owner contact, plan, status, timestamps, isolation metadata.
- **PP Plan**: ID, version, currency, monthly charge, limits (active users/workers/sites), included features, active/retired.
- **PP Subscription**: tenant, plan_version snapshot, start/renewal dates, billing period, trial/grace days, status (trialing/active/past_due/grace/suspended/cancelled), cancellation timing.
- **PP Platform Invoice**: subscription period, amount, taxes/discounts, invoice status, reference.
- **PP Platform Payment**: invoice, amount, external bank/reference, evidence, verified_by, timestamp; **manual confirmation for MVP**. Never let a tenant self-confirm a subscription payment.
- **PP Provisioning Job**: requested site/hostname, idempotency key, state, attempts, logs (redacted), rollback strategy.
- **PP Admin Audit**: actor, action, subject, before/after metadata, timestamp, reason; immutable or append-only.
- **PP Tenant User Directory**: identity mapping and seat counts. Per-tenant Frappe Users remain authoritative for actual app logins/permissions.

### Subscription enforcement
- Hosted SaaS only: tenant-level admin cannot disable subscription enforcement by editing code or configuration.
- Platform is authoritative for plan/version/status. Tenant may cache a **signed, short-lived entitlement** (e.g. <=24h) to survive brief control-plane outages. Signatures use asymmetric keys, public verification key in tenant; server-to-server transport authenticated/mTLS or scoped service token. No ordinary browser-trusted flags.
- The tenant backend checks entitlements **server-side** at sensitive workflows (write APIs, imports, batch jobs, user creation, provisioning and relevant background tasks), not only by hiding UI menus. Protect bulk endpoints too.
- Expiration: 3–7 day configurable grace; afterward **read-only access to existing records and billing/renewal area**. Do not delete customer data automatically. Suspension, support override and reinstatement audited. Review legal/access obligations before production policy.
- Limits: enforce active users/workers/sites before creating/re-activating records; race-safe transactions; permitted downgrades can't silently delete data.
- Billing: manual bank transfer confirmation for first release; gateways are adapters added later and callbacks must use verified webhook signatures and idempotency keys.
- Admin login: MFA required in production, per-role access, rate limits, secure session policy. Do not share site Administrator credentials.

## 4. Tenant business records and mappings

| Business concept | Source / custom model | Required notes |
|---|---|---|
| Customer company | ERPNext `Customer` | Tenant's external clients, not SaaS subscribing tenant |
| Customer contract | ERPNext `Contract` extended by `PP Contract Terms` | Billing strategy, currency, date-effective terms |
| Project | ERPNext `Project` | Contract link and budget/status |
| Site | custom `PP Site` | project, optional parent, site type/address |
| Employee/worker | HRMS `Employee` | Normalized identifier, trade/skill and eligibility |
| Worker wage history | custom `PP Worker Rate` | amount, unit, effective_from/to, approval |
| Client bill rate history | custom `PP Client Rate` | contract/category/worker override, effective dates |
| Worker assignment | custom `PP Assignment` | employee, site/project, start/end, status; overlapping allocations validated |
| Approved attendance | custom `PP Work Entry` | employee/date/site, units (0/0.5/1), snapshot of wage + billing rate, status; immutable once posted |
| Fixed milestone | custom `PP Milestone` | fixed contract, amount, completion/approval, invoice references |
| Labour settlement | custom `PP Wage Settlement` | earned, paid, outstanding; integrate ERPNext accounting; no duplicate expense booking |
| Project expenses | ERPNext accounting entries, plus custom mapping as required | project/site allocation and audit |
| Client invoice | ERPNext `Sales Invoice` | references approved work or fixed milestone |
| Client receipts | ERPNext `Payment Entry` | allocated to invoices, separate from invoice amount |

Cardinality: tenant site -> Customers -> Contracts -> Projects -> Sites; Employees -> Assignments -> Work Entries; Work Entries -> Wages and (daily contracts) billable values; Milestones -> fixed billable values. All records live **inside one tenant DB** except SaaS plans/subscriptions/tenant directory, which live at the control-plane site.

Unique/idempotent posting identifiers should prevent duplicate attendance/wage/invoice runs. Use approval/cancellation rather than delete/rewrite for posted records. Currency amounts use `Decimal`/ERPNext precision policy, never binary floating-point. Effective-dated rates are captured on each approved work entry.

## 5. Financial policies — immutable rules

**Daily contracts**: earned billable revenue = sum of approved eligible work units × effective client billing rate, adjusted by approved corrections/credit notes. Employee wage liability = sum of approved paid work units × snapshotted daily wage + approved overtime/allowance. Half-day and overtime policies are contract-configurable; never assume half-day client billing equals half-day wage without rules.

**Fixed contracts**: contract value = base fixed amount + approved variations. Earned/billable revenue is based on **approved milestones**, not worker-days. Labour attendance is still cost, not incremental billed revenue. Revisions require explicit authorized change orders. At completion, projected profitability should not be confused with earned revenue to date.

**Always separate**: contract value, earned revenue, issued invoices, received cash, wages accrued, worker payments, and other project costs. Dashboards label all explicitly. Gross contribution = earned revenue − wages accrued − attributable costs, subject to documented allocation policy. Receivables and payables are not revenue/cost proxies.

For fixed projects, employee-specific revenue is a **management allocation** (if enabled) with stated methodology, NOT direct client-billed revenue. Never double-count across daily registers and milestones.

## 6. MVP interfaces, roles and API

Tenant UI: Dashboard; Customers & Contracts; Projects & Sites; Workforce; Daily Operations (bulk attendance/assignments); Billing & Wage Settlements; Reports. Platform UI: Tenant Directory, Plans, Subscriptions, Platform Invoices/Payments, Provisioning, Audit/Support.

Permissions: tenant admins control their own site; supervisors limited to allowed sites; finance roles control invoices/payments; platform roles only on control-plane site. Central `Administrator` is a local development bootstrap identity only.

Use standard Frappe REST API, authenticated server methods, webhooks only when justified. Version external/custom API paths and implement request validation, pagination, idempotency and RBAC in the backend.

## 7. Cheapest safe deployment path

1. **Local**: Windows Docker Desktop with WSL2 or Linux/macOS Docker; official devcontainer stack. Two demo sites to exercise site isolation once basic functionality is healthy.
2. **Pilot**: one appropriately sized VPS with a production-specific image containing `erpnext`, `hrms`, `plus_point`, and `plus_point_control`. Separate tenant sites share the bench processes, but not databases. Reverse proxy with HTTPS, automated encrypted OFFSITE backup, tested restores, monitoring, security updates, and firewall. Do **not** expose MariaDB/Redis or the developer stack.
3. **Scale**: split control plane/tenant benches or tenants across VPSs when verified concurrency, queue delay, DB storage and resource use demand it. Do not imply one tiny VPS can host unlimited ERPNext sites.

Capacity/cost cannot be promised before load tests. Initial resource-sizing hypothesis for a low-concurrency pilot is >=4GB RAM, with 8GB+ often preferable for production ERPNext+HRMS+workers; measure actual memory and CPU. Application subscription charges are **not** the hosting bill.

## 8. Testing gates and evidence

- **Bootstrap:** `bench version` confirms compatible v16 branches, and `bench --site demo.localhost list-apps` shows ERPNext and HRMS.
- **API authentication:** Frappe `/api/method/ping` responds, invalid token denied; authenticated `/api/resource/ToDo` POST/GET/PUT/DELETE works (temporary development test user and cleanup).
- **Data isolation:** two sites have separate DBs. Test authenticated record created in site A is not visible in site B with B's own credentials. Verify host/subdomain can't override permissions.
- **Business tests later:** 2 contracts under one company, daily and fixed, two sites and 20 workers; transfers; no duplicate worker-day; historical rate change; partial wages/receipts; profit correctness; fixed milestones not double-counted.
- **Subscription tests later:** create/upgrade/downgrade/cancel, trial expiry, grace, payment verification, suspend, read-only access, resume, limits and concurrency/race, tenant provisioning idempotence, audit, payment idempotence.
- **Performance:** warm up and record p50/p95/p99 latency, throughput, error rate on realistic data, and DB/CPU/RAM/worker metrics; test 5/10/25 concurrent active users and bulk attendance entries. Targets must be based on expected workload and hardware. A healthy ping alone is not an optimization test.
- **Release gate:** security/RBAC review, dependency scan, backups/restores, migrations on a copy, UAT with real historical figures, and no unverified claims of production readiness.

## 9. Delivery phases

- **Phase 0 (NOW):** framework selection; local reproducible official devcontainer bootstrap; version/API/CRUD/basic load smoke script; architecture and runbook. Foundation NOT yet verified until Docker runs.
- **Phase 1:** create separate `plus_point_control` custom Frappe app/site, tenant registry, basic plan/subscription CRUD, manual payment verification, managed provisioning (no gateway).
- **Phase 2:** `plus_point` tenant custom app/site, companies/contracts/projects/sites, worker wage rates, assignments and attendance.
- **Phase 3:** daily and fixed contract billing, wage settlement, invoice reconciliation, dashboards/reports and immutable audit.
- **Phase 4:** tenant automation, full security/load/UAT, encrypted backups, deploy pilot to budget VPS and monitor.

### Decision change control

Do not add features from the 19-module roadmap without recording: user need, business rule, DocType/API impact, permission impact, cost/complexity, tests and approval. Changes to tenancy and financial semantics require an explicit architecture decision record. All commits should reference the accepted MVP scope.

## 10. Primary upstream documentation

- https://github.com/frappe/frappe_docker
- https://github.com/frappe/erpnext
- https://github.com/frappe/hrms
- https://docs.frappe.io/framework/user/en/basics/sites
- https://docs.frappe.io/framework-git/rest-api/authentication
- https://frappe.github.io/frappe_docker/01-getting-started/01-choosing-a-deployment-method.html

Note on licenses: Frappe is MIT; ERPNext and HRMS are GPL-3.0. Verify distribution, modification, and SaaS obligations with counsel before distributing derivative deployments; do not copy GPL code into a closed-source repository without review.
