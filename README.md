# PLUS POINT

Event operations, crew and finances on **Frappe v16, ERPNext v16 and Frappe HRMS v16**. Existing customer, employee, accounting, invoice, payment, authentication and REST functionality comes from upstream. PLUS POINT adds sites, allocations, bulk worker-day attendance, wage snapshots, fixed milestones and operational reporting in native Desk.

This is a **local development application**, not a production SaaS release. See [verification](VERIFICATION_STATUS.md) for actual evidence and gaps, and [architecture](MVP_ARCHITECTURE.md) for the source of truth.

Start with [the user guide](USER_GUIDE.md) for which app to use and the event-organizer workflow. PLUS POINT's Desk home opens with a company dashboard: six summary figures, a compact action inbox, selectable work history, revenue/cost comparisons, client activity calendars and project figures. The existing attendance, workers/sites, client billing and payment links stay underneath. **Mark attendance** prepares or reopens a register for review. Business setup is a collapsed sidebar group. **Help** contains workflow guidance and optional guided setup; established businesses see no setup, import or tour prompts on the overview. Only the product workflow appears in navigation and search. Unrelated ERP/HR workspaces and app-switching menus are hidden.

**Arrange sections** in the sidebar menu saves your preferred section order for your login. Section headings open live summaries and work-list counts; charts stay on the main overview. Client and company forms show approved work calendars on their front page.

**Onboarding** now lives inside the dashboard with a sidebar entry and persistent Skip/Resume. One paid workspace has one own-business profile, with clients and events underneath it. Country suggests an editable currency, including SAR. Clients can use another invoice currency, such as USD for a UAE client; new invoices convert approved base amounts at a published or agreed rate. Existing accounting history keeps its original currency. Clients include contact/address details, venues support a map pin, transport fields follow purpose and equipment can record quantities with an optional unit value.

**Display currency** converts overview money figures at the latest published daily exchange rate and shows its source/update time. The app keeps company books and approval limits in their original currency. The overview inherits the existing Desk theme and keeps the animated card/chart presentation.

**Forms and record cleanup:** record choices load fully in A–Z order with centered arrows. Shared input rules accept valid names/numbers/phones and block unsuitable characters. Saved event details and optional client-address reuse reduce repeated typing. Records have Delete actions, and lists support confirmed atomic deletion; approved work, posted history and native dependencies remain protected.

**Business reports** opens native project financial/deployment views and worker statements with assignment history, dated wages/payments and opening/closing balances. See [research alignment](RESEARCH_ALIGNMENT.md) for the October 17 business-context review, corrections and remaining MVP gaps.

**Event operations** adds event plans with per-venue phases and daily crew requirements, exact-date staffing calendars, warehouse availability, equipment reservations and capacity-checked crew/cargo vehicle bookings. **Plan an event** creates the project/agreement/sites/plan together. A new company's saved guide walks through company → client → event/venue → agreement → workers → staffing → transport → equipment → allocation while the background is dimmed and disabled. Existing businesses are not forced through setup. The company menu opens **Guided company setup**. Workers are not software accounts; the customer menu represents the company.

**Import** beside Add downloads templates/reference IDs, then previews CSV/XLSX before saving. It supports employees, finances, clients, venues, vehicles, warehouses, inventory items, counted stock and basic event plans. Google Sheets works through CSV/XLSX export. Read [the event workflow](EVENT_OPERATIONS.md) for setup, calendars, reservations and limits.

High4Tech has its own focused customer, pricing, subscription, account-support and software-finance home. Customer accounts can request native one-time password recovery or a login-ID change through an audited background worker. It does not expose contractor workforce tools. See [support and billing](USER_GUIDE.md#high4tech-customer-support-and-software-finances).

Local demo acquisition: [plans and signup](http://platform.localhost:8000/plans) offers published fixed-rate native plans, contact/business signup, simulated payment and High4Tech approval. Both login screens link to it. Approval now queues a separate empty local company workspace. The owner signs in with the registered email (or optional company login ID), choosing a password through a private one-time setup link shown on the signup page and in High4Tech → Signup approvals → Company login. No charge or email is sent; the local trial lasts 30 days and cannot generate software invoices. High4Tech → Signup approvals reviews requests; Pricing plans controls publication/prices. See [ownership, signup, documents and sidebar ordering](USER_GUIDE.md#local-ownership-signup-and-document-capabilities). Section headers now drag with their child links and save the per-login order; the keyboard up/down alternative remains.

## Run on Windows

With Docker Desktop running in Linux mode, run `START_PLUS_POINT_DEV.cmd`, or:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

This starts persistent MariaDB/Redis, installs pinned upstream apps and the editable PLUS POINT extension, migrates schemas and starts Bench. Ubuntu integration is unnecessary. The first installation downloads several GB and builds assets. Re-running preserves data and refuses unexpected upstream source commits.

Open [PLUS POINT](http://demo.localhost:8000/desk/plus-point). Login as `Administrator`; the generated local password is in ignored `.env` (`PP_ADMIN_PASSWORD`). The launcher never prints credentials. For the separate High4Tech platform site, add `-WithPlatform` to the PowerShell command. See [runbook](LOCAL_RUNBOOK.md).

## Common operations

For event setup and planning, start with [Event operations](EVENT_OPERATIONS.md). The attendance and billing flow remains:

1. Create native Company, Customer, Contract, Project and Employee records.
2. Add `PP Contract Terms` to the contract/project: Daily or Fixed.
3. Add `PP Site` and dated `PP Assignment` records with wage/client rates.
4. Choose **Mark attendance** on Event operations, select a site/date and **Review attendance**. Review units (0, 0.5, 1) and submit the native register. The original site action remains available.
5. Approve `PP Milestone` records for fixed terms; wages remain independent.
6. From terms, select **Prepare client invoice** with a native non-stock service Item. Review and submit the ERPNext Sales Invoice. Use native Payment Entries for receipts.
7. Link submitted employee Payment Entries with `PP Wage Settlement` to distinguish paid wages from earnings.

Approved work and historical allocation identities/rates stay locked. Close the old assignment without excluding any saved work, then use a new dated assignment for changed rates or deployment. Same-site dates cannot overlap. Company administrators can correct an approved attendance register with a required reason. Corrections keep native versions/comments, update wage totals and draft work invoices, and create reviewable debit/credit drafts for already issued work invoices. Issued invoice amounts and historical allocation rates stay unchanged.

A separate project **Spending budget** can warn at 80% and stop new approved wages or posted project expenses above 100%. Enable **Stop spending above budget** on the Project to activate it. Existing projects are not assigned guessed limits. Dashboards/forms provide warning, blocked, success, error/retry and empty/setup states with next actions. See [spending guidance](USER_GUIDE.md#spending-limits-and-next-actions).

## Verification

```powershell
docker compose ps
docker compose exec -T frappe bash -lc 'cd /home/frappe/frappe-bench && bench --site demo.localhost list-apps'
docker compose exec -T frappe bash -lc 'cd /home/frappe/frappe-bench && bench --site demo.localhost execute plus_point.testing.run_operations'
python scripts/verify-live.py
```

Offline checks with Python 3.12+:

```powershell
$env:PYTHONPATH = "$PWD/apps/plus_point"
python -m unittest discover -s tests -v
python -m unittest discover -s apps/plus_point/plus_point/tests -p test_finance.py -v
python -m unittest discover -s apps/plus_point/plus_point/tests -p test_register.py -v
```

The live script tests actual login, authenticated REST CRUD, anonymous rejection, frontend HTML and 60 authenticated concurrent reads. It rotates the local Administrator API token, keeps it only in memory and deletes its temporary ToDo. Database regression fixtures roll back. Synthetic HTTP harness tests are not ERPNext evidence.

After initial setup, Docker starts the app server and platform worker with their container and restarts them after a process failure. The app service reports healthy only when its HTTP endpoint answers. Closing the preview tab does not stop the app; reopen the link above. Stop deliberately with `docker compose stop`; resume with `docker compose up -d --wait` or the launcher. Containers deliberately stopped remain stopped when Docker restarts. Do not delete volumes without backups. Source is in `apps/plus_point`; dependencies and site/database data live in Docker volumes. Original foundation documents are preserved in `docs/archive`. Older Bash/disposable-demo scripts are historical helpers; `compose.yaml` and `scripts/start-local.ps1` are the supported setup.


### Event screens and invoice branding

Client agreements, Event plans and Billing and finances use native Desk lists (filters, sorting, checkboxes and views). Open a record to use its top tabs. Event venue cards combine agreed headcount, assigned names, category wages and coverage. Choose workers shows the current roster and supports creating a worker; Add venue and Add crew category keep event editing in place. Timeline views support Week, Month and Year.

Billing → Invoice branding stores the subscribing company's logo, address, contact and tax details. Invoice preview uses the **PLUS POINT Branded Invoice** print format. Download PDF fetches a JSON response and creates a browser Blob; Print / Save as PDF remains available independently. Outgoing email still requires a configured native Email Account and an explicit Send action.

The shared toolbar contains Appearance, Help and support, a Language placeholder, and company financial totals outside the overview. Required first setup gates navigation; finishing or intentionally skipping setup removes its sidebar entry.

Run `node scripts/browser-experience.cjs` with Playwright and Google Chrome installed for the complete isolated QA flow. It creates an exact temporary company on `qa.localhost`, exercises native lists, tab navigation, date errors, workers, venues, PDF download/print, attendance corrections and mobile dark mode, then restores the previous workspace. Database suites `run_hierarchy`, `run_attendance`, `run_operations`, `run_events`, and `run_currency_billing` roll back business fixtures.

### Agreement revisions and worker benefits

Agreements use Client details, Agreement details, Pricing and milestones, Sites and crew, and Send and sign. Sites contain editable category tables; Fixed pricing hides wage columns. Currency changes preserve accounting value and issued invoices. Worker profiles include activation, Salary and leaves, dated leave, eligibility-checked loans, accounting-backed loan recovery, and worker-specific event assignment with explicit extra crew. See [worker benefits and revision workflow](WORKER_BENEFITS.md). Run `node scripts/browser-worker-flows.cjs` for the new isolated QA flow.
