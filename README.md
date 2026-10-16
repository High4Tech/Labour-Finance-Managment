# PLUS POINT

Labour contracting on **Frappe v16, ERPNext v16 and Frappe HRMS v16**. Existing customer, employee, accounting, invoice, payment, authentication and REST functionality comes from upstream. PLUS POINT adds sites, allocations, bulk worker-day attendance, wage snapshots, fixed milestones and operational reporting in native Desk.

This is a **local development application**, not a production SaaS release. See [verification](VERIFICATION_STATUS.md) for actual evidence and gaps, and [architecture](MVP_ARCHITECTURE.md) for the source of truth.

Start with [the user guide](USER_GUIDE.md) for which app to use and the contractor workflow. PLUS POINT's Desk home groups daily work into attendance, workers/sites, client billing and worker payments. **Mark attendance** prepares or reopens a register for review. Setup tools and the six-step guide are available on demand, alongside **How it works**, **Show me around**, and field help. ERPNext's unrelated modules, such as Manufacturing, are optional; they are not part of the usual contractor workflow.

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

Approved work and used allocations are immutable. Use a new dated assignment for new rates. Audited attendance correction workflows remain a production release requirement.

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
