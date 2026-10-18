# PLUS POINT

Labour contracting on **Frappe v16, ERPNext v16 and Frappe HRMS v16**. Existing customer, employee, accounting, invoice, payment, authentication and REST functionality comes from upstream. PLUS POINT adds sites, allocations, bulk worker-day attendance, wage snapshots, fixed milestones and operational reporting in native Desk.

This is a **local development application**, not a production SaaS release. See [verification](VERIFICATION_STATUS.md) for actual evidence and gaps, and [architecture](MVP_ARCHITECTURE.md) for the source of truth.

Start with [the user guide](USER_GUIDE.md) for which app to use and the contractor workflow. PLUS POINT's Desk home opens with a company dashboard: six summary figures, a compact action inbox, selectable work history, revenue/cost comparisons, client activity calendars and project figures. The existing attendance, workers/sites, client billing and payment links stay underneath. **Mark attendance** prepares or reopens a register for review. Business setup is a collapsed sidebar group. **Help** contains workflow guidance and optional guided setup; established businesses see no setup, import or tour prompts on the overview. Only the product workflow appears in navigation and search. Unrelated ERP/HR workspaces and app-switching menus are hidden.

**Arrange sections** in the sidebar menu saves your preferred section order for your login. Section headings open live summaries and work-list counts; charts stay on the main overview. Client and company forms show approved work calendars on their front page.

**Display currency** converts overview money figures at the latest published daily exchange rate and shows its source/update time. The app keeps company books and approval limits in their original currency. The overview inherits the existing Desk theme and keeps the animated card/chart presentation.

**Business reports** opens native project financial/deployment views and worker statements with assignment history, dated wages/payments and opening/closing balances. See [research alignment](RESEARCH_ALIGNMENT.md) for the October 17 business-context review, corrections and remaining MVP gaps.

**Help → Guided setup** collects one saved step at a time: worker, site/job, billing agreement and assignment after the company prerequisite. It starts automatically only for an unfinished business without assignments; skip and resume are available. **Import** beside Add on supported lists downloads templates/reference IDs and previews CSV/XLSX files before creating/updating employee profiles or posting native historical financial records. Google Sheets files work through CSV/XLSX export. See [setup](USER_GUIDE.md#guided-setup) and [imports](USER_GUIDE.md#import-employees-and-existing-finances).

High4Tech has its own focused customer, pricing, subscription, account-support and software-finance home. Customer accounts can request native one-time password recovery or a login-ID change through an audited background worker. It does not expose contractor workforce tools. See [support and billing](USER_GUIDE.md#high4tech-customer-support-and-software-finances).

## Run on Windows

With Docker Desktop running in Linux mode, run `START_PLUS_POINT_DEV.cmd`, or:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

This starts persistent MariaDB/Redis, installs pinned upstream apps and the editable PLUS POINT extension, migrates schemas and starts Bench. Ubuntu integration is unnecessary. The first installation downloads several GB and builds assets. Re-running preserves data and refuses unexpected upstream source commits.

Open [PLUS POINT](http://demo.localhost:8000/desk/plus-point). Login as `Administrator`; the generated local password is in ignored `.env` (`PP_ADMIN_PASSWORD`). The launcher never prints credentials. For the separate High4Tech platform site, add `-WithPlatform` to the PowerShell command. See [runbook](LOCAL_RUNBOOK.md).

## Common operations

1. Create native Company, Customer, Contract, Project and Employee records.
2. Add `PP Contract Terms` to the contract/project: Daily or Fixed.
3. Add `PP Site` and dated `PP Assignment` records with wage/client rates.
4. Choose **Mark attendance** on Workforce home, select a site/date and **Review attendance**. Review units (0, 0.5, 1) and submit the native register. The original site action remains available.
5. Approve `PP Milestone` records for fixed terms; wages remain independent.
6. From terms, select **Prepare client invoice** with a native non-stock service Item. Review and submit the ERPNext Sales Invoice. Use native Payment Entries for receipts.
7. Link submitted employee Payment Entries with `PP Wage Settlement` to distinguish paid wages from earnings.

Approved work and historical allocation identities/rates stay locked. Close the old assignment without excluding any saved work, then use a new dated assignment for changed rates or deployment. Same-site dates cannot overlap. Audited attendance correction workflows remain a production release requirement.

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

Stop with `docker compose stop`; resume with the launcher. Do not delete volumes without backups. Source is in `apps/plus_point`; dependencies and site/database data live in Docker volumes. Original foundation documents are preserved in `docs/archive`. Older Bash/disposable-demo scripts are historical helpers; `compose.yaml` and `scripts/start-local.ps1` are the supported setup.
