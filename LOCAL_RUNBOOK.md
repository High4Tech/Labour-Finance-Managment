# Local operator runbook

The supported setup is Windows PowerShell + Docker Desktop Linux engine, compose.yaml and scripts/start-local.ps1. No Ubuntu terminal is needed. Source and Git history remain in this checkout. Original foundation guidance is archived.

## Start and stop

Run START_PLUS_POINT_DEV.cmd. The launcher generates missing strong local credentials in ignored .env, creates persistent named volumes, installs pinned releases, migrates schemas and starts Bench. Initial setup needs network access to official GitHub repositories, PyPI, npm and Docker Hub. Re-running preserves existing databases and refuses source commit drift. Use docker compose stop to stop; run the launcher to resume. Do not delete volumes as a troubleshooting step.

Local app: http://demo.localhost:8000/desk/plus-point . Login Administrator with PP_ADMIN_PASSWORD in .env. Never paste or print credentials in issue reports. Local ports bind only to 127.0.0.1. Other devices cannot access this developer setup.

If .localhost DNS is unavailable, use http://127.0.0.1:8000 and configure a Host header of demo.localhost in diagnostic requests. Native bench site routing uses hostnames. Multiple tenants must use their own hostname.

## Real verification

```powershell
docker compose ps
docker compose exec -T frappe bash -lc 'cd /home/frappe/frappe-bench && bench --site demo.localhost list-apps'
docker compose exec -T frappe bash -lc 'cd /home/frappe/frappe-bench && bench --site demo.localhost execute plus_point.testing.run_operations'
python scripts/verify-live.py
```

Database regressions use temporary fixtures with transaction rollback. The HTTP test rotates the local Administrator API token, retains it only in memory and deletes its temporary ToDo. It uses fresh local login credentials and checks 60 authenticated requests at concurrency 5. This is a light baseline, not capacity certification.

Optional labelled local demo data:

```powershell
docker compose exec -T frappe bash -lc 'cd /home/frappe/frappe-bench && bench --site demo.localhost execute plus_point.testing.seed_demo'
```

This creates a PLUS POINT Demo company/customer/project/worker, one approved daily entry and a fixed milestone; reruns preserve existing demo records. It intentionally marks the local setup wizard complete. Do not run seed helpers on production.

The seed also completes Frappe's native post-setup transition, so All apps opens the desktop rather than reloading the completed wizard. With Playwright and Chromium installed, run `node scripts/browser-navigation.cjs` to check the actual app switcher, HR, Home dashboard, Users and return to PLUS POINT. Set `PP_BROWSER_CHANNEL=msedge` to use installed Edge. Optional `PP_BROWSER_USER` and `PP_BROWSER_PASSWORD` select a local account instead of Administrator; credentials are never logged. Set `PP_BROWSER_EMPLOYEE_APP=1` to include HR employee self-service and browser Back. That check requires the login to be linked to an active Employee using its native User ID field. Screenshots stay in ignored `.local/qa`.

`node scripts/browser-onboarding.cjs` checks the six-step tour, app explanations, collapse preference, keyboard/click field help, field tour, way back from Manufacturing and a 390px mobile layout. It uses the same browser credential variables. The tenant check needs seeded sample allocations; the platform check (`PP_BROWSER_SITE=platform.localhost`) needs a seeded tenant. It changes browser-local preferences only. Native field descriptions are synchronized with `bench --site <site> migrate`; Desk guidance assets are served directly from the app's public files. Refresh Desk after updating them. See USER_GUIDE.md for end-user instructions.

`node scripts/browser-customer-ux.cjs` verifies the simpler tenant home, grouped navigation, list labels, collapsed optional content and mobile layout. It uses the same credential variables and seeded demo site/allocations. The test requires a vacant demo attendance date (today plus two days), creates and reopens a reviewable draft, then deletes that temporary draft. It refuses to modify an existing register. Tenant migration adds the grouped native sidebar only if no site-level customization exists; per-user choices and an explicit starting app are preserved.

## Separate High4Tech platform

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1 -WithPlatform
```

Open http://platform.localhost:8000/desk/high4tech . This site has its own database and pp_control_plane=true. Administrator has the development bootstrap privileges; production must use individual High4Tech Platform Admin accounts plus appropriate native ERPNext accounting roles.

Configure a native High4Tech Company, service Item, Customer for the subscriber, monthly Subscription Plan and Subscription (trial or active, with explicit period end). Add a PP Tenant with a distinct .localhost hostname, owner email, subscription and limits. Do not use demo.localhost or platform.localhost for a new tenant. The operator worker checks the registry every minute, provisions missing sites using bench and synchronizes host-controlled entitlements. Native invoices and manually confirmed Payment Entries handle development billing. No real payment gateway is enabled.

Suspend/reactivate in PP Tenant; renewal/trial eligibility comes from native Subscription. Worker failures require operator investigation; its output is deliberately redacted. It never deletes sites. Local tenants share the local development Administrator password; unique invitation/credentials and secure provider integration remain production requirements. Existing demo.localhost without an entitlement is explicitly uncontrolled Development mode.

To synchronize a specific registered tenant immediately:

```powershell
docker compose exec -T frappe python /workspace/scripts/provision.py --tenant example.localhost
```

## Diagnose safely

```powershell
docker compose exec -T frappe tail -n 80 /home/frappe/frappe-bench/logs/bench-start.log
docker compose logs --tail 50 mariadb
```

Docker access errors from an automation sandbox are different from a broken daemon: retry using the approved host Docker permission. Do not reset WSL, Docker volumes or the database. Dependency download timeouts can be retried; existing pinned sources/sites are retained. Never post site_config, .env, API keys or complete environment dumps.

## Backups and upgrades

Native bench --site <site> backup --with-files writes private site backups inside the persistent bench volume. Copy them to protected off-host storage. Verify a restore into a new isolated test site before trusting backups. No restore drill has been certified by this increment. Protect .env separately. Do not commit site backups or database artifacts.

Update upstream.lock.json and image digests deliberately in a branch, back up every tenant, build/migrate in staging, and execute the full regression/isolation suite before a production rollout. Never use bench update against unreviewed floating branches. Build custom apps into a pinned official production image; the local sleep-infinity/bench-start developer container is not a production deployment.
Credential maintenance: scripts/rotate-local.py rotates local Administrator passwords/API keys/sessions and database root credentials without printing values, then updates ignored .env. Restart with the launcher afterward. This is a local operator tool, not a tenant API.
