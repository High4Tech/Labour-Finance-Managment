# Local operator runbook

The supported setup is Windows PowerShell + Docker Desktop Linux engine, compose.yaml and scripts/start-local.ps1. No Ubuntu terminal is needed. Source and Git history remain in this checkout. Original foundation guidance is archived.

## Start and stop

The customer home includes Guided setup and Import employees or finances. Both are customer System Manager flows; High4Tech is excluded. Run a normal site migration to install PP Import Record before using imports. Templates and reference-ID files download from the signed-in customer site; uploads are CSV/XLSX snapshots without external Sheets credentials. See USER_GUIDE.md for field formats, supported record types and posting order.

Run `scripts/browser-setup-imports.cjs` with the same bundled Node/Playwright/Edge environment as the other browser checks. It uses local test-enabled demo records, restores the original setup progress, and removes only its generated worker/site/assignment/import receipt. Its operator-only helper is not whitelisted. Do not run it alongside the database suite or other guide/import mutations. An interrupted run retains its original progress snapshot in the site's private backups directory; use `plus_point.testing.setup_browser_fixture` with the exact logged run ID and action `end` to finish cleanup. Never delete or reset site volumes to clean up tests.

Run START_PLUS_POINT_DEV.cmd. The launcher generates missing strong local credentials in ignored .env, creates persistent named volumes, installs pinned releases, migrates schemas and starts Bench. Initial setup needs network access to official GitHub repositories, PyPI, npm and Docker Hub. Re-running preserves existing databases and refuses source commit drift. Use docker compose stop to stop; run `docker compose up -d --wait` or the launcher to resume. Do not delete volumes as a troubleshooting step.

The container runs scripts/run-local.py as its supervised startup command. It waits for sites/.plus-point-ready, written only after successful bootstrap, then owns Bench (without the asset watcher) and the platform worker. If either exits, both process groups stop and Docker's unless-stopped policy restarts the app container. MariaDB and Redis also use unless-stopped. The app health check requests the configured site's /api/method/ping endpoint; a running container alone is not evidence of a reachable app. Logs remain in the persistent bench logs directory. No initial setup, migration or dependency download runs on an ordinary container restart. For older installations, run the launcher once after pulling this startup change so bootstrap can create the readiness marker.

Turning Docker back on resumes containers that were running when Docker stopped. A deliberate Compose Stop requires an explicit Compose Start/Up or the launcher. A closed browser preview can be reopened at the local app URL independently of these services.

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

The seed completes native setup. `node scripts/browser-product-scope.cjs` checks each focused product overview/sidebar, filtered search suggestions, staff/customer record navigation, support buttons on High4Tech, unrelated-route return and a 390px layout. `browser-navigation.cjs` and `browser-smoke.cjs` are compatibility entry points for that check; the earlier HR/app-switching routes were intentionally removed. Set `PP_BROWSER_CHANNEL=msedge` for installed Edge, `PP_BROWSER_SITE` for the local site and optionally `PP_BROWSER_USER` / `PP_BROWSER_PASSWORD` for its named account. Credentials are not logged; screenshots stay in ignored `.local/qa`.

`node scripts/browser-onboarding.cjs` checks the six-step tour, app explanations, collapse preference, keyboard/click field help, field tour, return from an unrelated route and a 390px mobile layout. It uses the same browser credential variables. The tenant check needs seeded sample allocations; the platform check (`PP_BROWSER_SITE=platform.localhost`) needs a seeded tenant. It changes browser-local preferences only. Native field descriptions are synchronized with `bench --site <site> migrate`; Desk guidance assets are served directly from the app's public files. Refresh Desk after updating them. See USER_GUIDE.md for end-user instructions.

`node scripts/browser-customer-ux.cjs` verifies the simpler tenant home, grouped navigation, list labels, collapsed optional content and mobile layout. It uses the same credential variables and seeded demo site/allocations. The test requires a vacant demo attendance date (today plus two days), creates and reopens a reviewable draft, then deletes that temporary draft. It refuses to modify an existing register. Tenant migration adds the grouped native sidebar only if no site-level customization exists; per-user choices and an explicit starting app are preserved.

`node scripts/browser-reports.cjs` verifies native project financial/deployment views, the worker statement and assignment-history view, home/form shortcuts, calculation notes, actual XLSX export and 390px report width. It uses the same credential variables, browser-native login and the labelled demo worker/company. Migrate the tenant after pulling these report definitions; no new frontend build or reporting service is needed. The report company is your legal business; Client company narrows its customer projects. Reports use native permissions and are unavailable on the control-plane site.

## Separate High4Tech platform

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1 -WithPlatform
```

Open http://platform.localhost:8000/desk/high4tech . This site has its own database and pp_control_plane=true. Administrator has the development bootstrap privileges; production must use individual High4Tech Platform Admin accounts plus appropriate native ERPNext accounting roles.

Configure a native High4Tech Company, service Item, Customer for the subscriber, monthly Subscription Plan and Subscription (trial or active, with explicit period end). Add a PP Tenant with a distinct .localhost hostname, owner email, subscription and limits. Never use the platform hostname as a customer. The existing demo.localhost can be registered without replacing its database; `plus_point.testing.seed_platform_customer_demo` registers it as a labelled local trial without fabricated sales. The operator worker checks the registry every minute, provisions missing sites using bench and synchronizes host-controlled entitlements. Native invoices and manually confirmed Payment Entries handle development billing. No real payment gateway is enabled.

Suspend/reactivate in PP Tenant; renewal/trial eligibility comes from native Subscription. Worker failures require operator investigation; its output is deliberately redacted. It never deletes sites. Local tenants share the local development Administrator password; unique invitation/credentials and secure provider integration remain production requirements. The existing demo.localhost is now registered as a trial software customer and receives the same subscription enforcement.

To synchronize a specific registered tenant immediately:

```powershell
docker compose exec -T frappe python /workspace/scripts/provision.py --tenant example.localhost
```

## Customer support and software finance checks

On a registered customer account use Reset customer password or Change customer login ID, then View support result on the native request. Native short-queue workers must be running. Only the registered owner is supported; the customer's existing password is never revealed. Reactivate a suspended subscription before native reset completion. No automatic email is sent. Link retrieval is restricted to the platform admin and 20 minutes; native reset expiry also applies. Hourly native scheduler cleanup removes expired encrypted results. Never put reset links in logs, issues or source control.

Run `python scripts/verify-platform-flow.py` for real local HTTP pricing changes, platform-role/Guest rejection, queued login-ID/password support, native single-use password completion, old-password rejection, encrypted/masked results, suspension/reactivation and database/token isolation. It uses a temporary QA owner, restores its registry/settings, and deletes its users/requests/plan. Do not run it concurrently with another QA entitlement-changing test. An optional named platform login uses `PP_PLATFORM_SUPPORT_USER` and `PP_PLATFORM_SUPPORT_PASSWORD`; defaults come from the ignored local environment. `plus_point.testing.cleanup_support_test_fixtures` recovers only strictly named completed/failed support fixtures and unreferenced test plans after interruption.

Run `bench --site platform.localhost execute plus_point.testing.run_platform_finance` from the container bench directory for native plan/subscription billing, posted invoice and receipt GL, and zero outstanding balance. All its financial fixtures roll back. This does not charge a bank/card or deliver email. Public payment webhooks, remote-host provisioning and outgoing email are unconfigured.

## Spending controls and state UX

Migrate customer/platform/QA sites after pulling this change to add the Project spending-stop Custom Field. Project.estimated_costing remains the native field and is labelled Spending budget on customer sites. Existing projects stay unenforced until an administrator chooses a positive limit and enables Stop spending above budget. Never assign artificial budgets merely to make the dashboard show a state.

Run the actual operations suite for budget guards, purchases/claims and rollback. Run `node scripts/browser-conditions.cjs` on the seeded local demo for red overruns, native pre-submit stop/warning/cancel, success CTA, retry/recovery and empty/mobile presentation. It uses the local bootstrap credential in memory, creates a vacant-date draft, temporarily sets a demo budget, then restores/deletes its own fixtures. It refuses an already enabled demo budget. Do not run alongside manual budget edits or attendance tests using the same date. State examples saved in ignored `.local/qa` are test evidence, not persistent business budgets.

## Diagnose safely

```powershell
docker compose exec -T frappe tail -n 80 /home/frappe/frappe-bench/logs/bench-start.log
docker compose logs --tail 50 mariadb
```

Docker access errors from an automation sandbox are different from a broken daemon: retry using the approved host Docker permission. Do not reset WSL, Docker volumes or the database. Dependency download timeouts can be retried; existing pinned sources/sites are retained. Never post site_config, .env, API keys or complete environment dumps.

## Backups and upgrades

Native bench --site <site> backup --with-files writes private site backups inside the persistent bench volume. Copy them to protected off-host storage. Verify a restore into a new isolated test site before trusting backups. No restore drill has been certified by this increment. Protect .env separately. Do not commit site backups or database artifacts.

Update upstream.lock.json and image digests deliberately in a branch, back up every tenant, build/migrate in staging, and execute the full regression/isolation suite before a production rollout. Never use bench update against unreviewed floating branches. Build custom apps into a pinned official production image; this supervised Bench developer container is not a production deployment.
Credential maintenance: scripts/rotate-local.py rotates local Administrator passwords/API keys/sessions and database root credentials without printing values, then updates ignored .env. Restart with the launcher afterward. This is a local operator tool, not a tenant API.

## Approved local signup workspaces

Use High4Tech → Signup approvals → Approve & create workspace after a simulated payment. Existing approved requests use Create company workspace. The container-owned platform worker creates a separate local site/database and native owner; setup takes a few minutes. Do not copy demo business data or set the owner to a shared Administrator password. The owner uses the registered email (optional company login ID), chooses a password through Company login → Set your password, then starts fresh company onboarding. The signup tab offers the same private link. No email is sent. If its private one-time link expires, Refresh password setup link before the first login; later password recovery uses Customer support. Retry workspace setup retains the bound site and data after a failure.

Workspace hostnames are server-derived .localhost addresses served on port 8000. Keep Docker running. These trial subscriptions last 30 days and block software invoice generation. Payment remains simulated. Protected site configuration, each site's encryption key and database/uploads need native backups alongside the code; Git is not a customer-data backup. The provisioner refuses an unrelated existing site and does not delete sites or volumes.
