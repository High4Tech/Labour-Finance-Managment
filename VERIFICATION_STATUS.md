# Verification status — 2026-10-17

Executed against Docker Desktop Linux engine on this Windows machine. This supersedes the original starter's unexecuted environment claims (preserved in docs/archive).

## Passing actual runtime checks

- Official Bench image, MariaDB 11.8 and two Redis services running; MariaDB health check passes. Web/socket ports bind only to 127.0.0.1. Persistent bench/database volumes survive restart.
- Frappe 16.51.1, ERPNext 16.51.1, HRMS 16.51.0 and PLUS POINT 0.4 installed. Source commits and image digests pinned and verified.
- Three independent sites: demo.localhost, platform.localhost and qa.localhost. Native platform Subscription/Subscription Plan and PP Tenant created; trusted worker provisioned QA site and native owner account.
- Fresh environment-only installer wrapper created a disposable Frappe site/database/user successfully, verified actual records and removed only that generated test DB/user using native cleanup. Native site archive retained inside the private bench volume.
- Actual Administrator login using rotated credentials; authenticated native ERPNext/HRMS/custom REST reads; ToDo create/read/update/delete, persisted update and anonymous rejection. Temporary HTTP records cleaned.
- Actual cross-site token rejection in both directions and a first-site record returning 404 under the second site's own credentials. Bench default-site override was removed: Host routing is required for these checks.
- Actual HTTP suspension and expiry reject writes while preserving reads; native User REST API rejects a seat beyond the configured limit; reactivation restores writes. Original QA entitlement restored, temporary Users/ToDos removed.
- **24 real MariaDB-backed business regressions passed**: daily/half-day rates, fixed milestones and cap, independent fixed wages, snapshot immutability, bulk register posting, duplicate/cross-site day limits, source reservations, invoice posting/cancellation and GL entries, client cash receipts vs invoice/earned revenue, wage settlements against native employee payments, outstanding balances, permissions, quotas and 25-row reporting. Fixtures rolled back.
- **11 offline project/harness checks + 10 pure finance/register tests passed**. Synthetic HTTP harness tests are not counted as live ERPNext evidence.
- Real Edge browser: authenticated tenant workspace, site/attendance/terms lists; separate High4Tech workspace and tenant/plan/subscription lists. Zero JavaScript page errors. Screenshots retained in ignored .local/qa.
- Latest light authenticated list test: **60 requests, concurrency 5, 0 errors; median 62.8 ms, p95 82.3 ms, maximum 96.1 ms**. Small local dataset; no warm-up or throughput/capacity certification.

## Defects found and fixed

- Docker permissions were sandbox restrictions; Windows Docker Desktop works without Ubuntu integration.
- Empty Docker volume directory required Bench's ignore-existing initialization option.
- Native setup defaults (warehouse types, genders, price lists, fiscal year) must come from upstream setup routines.
- Bench configuration parsing expects Python literals, not JSON booleans.
- Original app version metadata was inconsistent; normalized to 0.4.0.
- Integer zero vs database decimal zero incorrectly rejected fixed-rate work approval.
- Original summaries could silently omit records because of default pagination.
- Added employee/terms row locks for attendance, settlement, milestone and invoice races; used allocations and economic terms cannot rewrite historical work.
- Bench's fixed default site defeated hostname tenancy; removed default_site selection and enabled hostname routing.
- Cached site configuration delayed suspension; write hooks now read current host-controlled entitlements for web/background operations.
- Local credentials appeared in a process diagnostic. All affected local Administrator passwords/API keys/sessions and database root credentials were rotated. New provisioning reads passwords from the environment, not process arguments. No .env/site data/secrets are tracked.

## Not run / not claimed complete

- Broad upstream ERPNext/HRMS test suites, statutory payroll validation and complete upstream vulnerability/license audits.
- Large datasets, simultaneous attendance write stress/deadlock profiling and multi-host capacity.
- Dedicated supervisor/finance roles, wage field privacy, comprehensive site-scoped User Permission matrix.
- Audited attendance adjustment/reversal and partial source credit/rebilling workflows.
- Automatic payroll accrual journals; custom work economics remain separate from native payroll.
- All privileged upstream direct-SQL methods audited for subscription enforcement.
- Native monthly renewals over actual elapsed calendar periods; native scheduler is enabled and billing is reused, not reimplemented.
- Live payment-provider credentials/webhooks; development billing remains manual/mock with no external money movement.
- Production deployment, HTTPS/MFA, unique onboarding invitations, encrypted offsite backup/restore drills and monitoring.
- GitHub-hosted CI execution is separate from local passes. The new workflow includes actual app/database/HTTP regressions and optional full SaaS provisioning.

## Reproduce

Use README.md and LOCAL_RUNBOOK.md. Business suite: plus_point.testing.run_operations. Live HTTP: scripts/verify-live.py --other-site qa.localhost. Subscription HTTP: scripts/verify-subscription.py. Browser: scripts/browser-smoke.cjs (Playwright/Chromium or installed Edge channel). Installer test: scripts/verify-installer.py inside the Bench virtualenv. Database/site contents and browser outputs are private ignored runtime artifacts.
## Final concurrent-write refinement

Verified MariaDB's actual isolation settings, reproduced error 1020 during concurrent writes, selected READ COMMITTED in Compose and tightened financial current-row locking reads. The 24 business tests pass again. Ten simultaneous HTTP attendance writes now give exactly one created draft and nine duplicate validation rejections; drafts are cleaned. Full mixed-write load/deadlock profiling remains unrun.

GitHub static checks passed. The first fresh-runner integration installed the real stack and passed all 24 database tests, then exposed first-token authentication failure from a missing encryption key in cached web configuration. Bootstrap now initializes the native encryption key before web starts; the updated integration workflow reruns this fresh and includes the attendance write race. See the PR checks for final remote status.

Browser workflow check also clicked Prepare daily attendance on the demo site, set a work date through the native dialog, verified a populated reviewable draft register and deleted that temporary draft successfully. No page JavaScript errors occurred.

## HR and user navigation correction

Reproduced a Purchase Order permission error on the native Home dashboard, rejection of the unlinked demo login by employee self-service, and a repeated setup-page reload from All apps. PLUS POINT now declares its canonical `/desk/plus-point` route; the demo seed executes the native post-setup transition that removes the old setup-wizard home default. Local tenant owners include the native Purchase Manager role needed by the Home dashboard. The requested local dummy accounts were corrected in their respective site databases; the tenant login was linked to the clearly labelled sample employee without adding restrictive worker-only User Permissions.

Real Edge verification as the non-Administrator tenant dummy account passed the actual All apps → PLUS POINT → Frappe HR → All apps → Framework flow, Home dashboard cards, Users list and return to PLUS POINT. Linked HR employee self-service and browser Back also passed. No HTTP errors or JavaScript page errors were observed. The 11 offline project/harness checks passed again. Reproduce with `scripts/browser-navigation.cjs`; local screenshots remain ignored.

## Product onboarding and contextual help

Added native Desk guidance for the contractor workflow, the roles of PLUS POINT/ERPNext/HR/Framework/High4Tech, optional ERP modules, and a context-aware route home. The tenant workspace has a collapsible six-step guide and an opt-in tour using Frappe's existing Driver. Native field descriptions explain 42 fields across nine PLUS POINT document types; field tips work by mouse, keyboard or click, and Explain this screen offers a native Dialog and field tour. The platform's app tile is labelled High4Tech admin and opens its subscriber workspace. No upstream source was modified and guidance does not change document permissions.

Applied metadata migrations on demo.localhost and platform.localhost. Actual Edge checks as each site's named dummy account passed tenant tour controls and dismissal, app explanations, collapse persistence after reload, keyboard/first-click field tips, field tour, optional Manufacturing guidance and route home, four app captions, and a 390px layout/tour. Platform checks passed its own app entry, platform-home link and customer-organization field tip. These checks changed only browser-local guide preferences and observed zero JavaScript or HTTP errors. Screenshots are in ignored `.local/qa`.

The existing real browser navigation/self-service round trip passed again. The attendance browser check also passed again: a populated draft was created through the site action and removed. All 11 offline project/harness checks and Python/JavaScript syntax checks pass. Broad upstream suites and production role/privacy acceptance were not rerun or claimed by this UI increment.

## Simpler customer workspace

Tenant migration adds a native grouped sidebar only where no site-level customization exists, preserves explicit starting-app preferences, and makes PLUS POINT the default for an unconfigured customer site. The home prioritizes attendance and three related task groups; setup records and the six-step guide begin collapsed. Custom lists use familiar titles/actions and omit their internal ID column/filter. Native title metadata improves link labels. Field help stays available on focus, through the question buttons and screen explanations. The separate platform is excluded from tenant navigation changes.

Actual Edge verification as the named tenant dummy account passed the default home route, collapsed optional content, plain-language sidebar, milestone list, primary target size, creation of a populated attendance draft, reopening that same draft with no duplicate or automatic submission, and the home/dialog at 390px. The temporary draft was removed using a separate local Administrator session because the ordinary tenant role correctly has no attendance delete permission. The browser observed zero JavaScript or HTTP errors in the successful run. Tenant onboarding passed all tour controls, remembered guide state, keyboard/click field tips, field tour, optional-module return and mobile layout again; platform onboarding passed separately with zero JavaScript/HTTP errors.

The actual All apps → PLUS POINT → HR → Framework → Home → Users → PLUS POINT round trip and linked employee self-service/browser Back passed again with zero browser/server errors. The original site action also created a populated attendance draft and removed it; tenant and platform list smoke checks passed. Browser smoke URLs now use the canonical `/desk` routes. A legacy `/app` navigation stalled during verification before this test correction; the native app-switcher flow and current routes passed afterward.

Database inspection confirmed the workspace setup is idempotent on the demo site, retains the existing sidebar, uses native link-title metadata and does not create a tenant sidebar on the control-plane site. All 11 offline project/harness checks and Python/JavaScript syntax checks passed again. Existing financial/database results above are prior evidence; this UI increment did not rerun the broad business suite or production role/privacy acceptance. Customer usability sessions and comprehensive accessibility acceptance remain unrun.

During resumption Docker Desktop failed on a stale Windows runtime socket. Its two runtime directories were renamed and retained, then recreated; the existing persistent app/database volumes were reused. After the development watcher rebuilt styles, stale process-local asset references caused CSS failures. Refreshing the shared asset manifest and triggering the native web reload restored current assets; the successful final browser checks ran after this recovery. No upstream source contents or stored customer records were changed for recovery. Screenshots remain in ignored `.local/qa`.

## Research-context alignment — October 17

Compared the supplied full research handoff with the repository, running sites and business rules. RESEARCH_ALIGNMENT.md records the requirements mapping, corrections and remaining gaps. The historical handoff's claims of unverified installation/Git state are superseded by the actual runtime and commit evidence above.

Added two standard native Script Reports: Project Finances (lifetime financial results and deployment overview) and Worker Statement (dated approved work/settled payments with opening/closing balances, plus assignment history). Home, Employee, Project and billing terms expose shortcuts; financial calculation detail is collapsed on demand. Reports reuse native permissions, tables and export; they require one selected legal company and do not invent worker-level fixed revenue, period project profit or site allocation of cumulative costs. Both providers reject the actual control-plane site's configuration. Native reports were synchronized successfully on demo.localhost and platform.localhost; the platform's separate navigation remains intact.

Corrected used assignments so a safe end date permits a subsequent rate/assignment without changing historical snapshots. Saved work, including drafts, cannot fall beyond the new end date; used allocations cannot reopen or extend. Same-worker/same-site overlap is rejected under employee serialization, while split-site days remain possible under the existing aggregate day limit.

**31 actual MariaDB business regressions passed**, including seven new cases for safe closure/new rates, draft preservation, overlap rejection, dated opening/period/closing balances, deployment deduplication, company/date scope and report guest/control-plane denial. Existing tests additionally exercise reporting beyond 20 rows, fixed-worker zero revenue and native receipt/invoice distinction. Fixtures rolled back. **11 offline project/harness checks and 10 pure finance/register checks passed** (52 automated cases combined). Python/JavaScript syntax and whitespace checks pass.

Actual Edge checks as the tenant dummy account passed home → financial/deployment report, values compared with the existing financial API, collapsed calculation notes and their disclosure, Employee → Worker Statement, work/assignment view switching, a real native **XLSX export** (200 response with ZIP workbook bytes), billing terms → filtered Project Finances, and a 390px report layout. The final run observed zero JavaScript/HTTP errors and wrote no business records. One intermediate run encountered a transient Socket.IO polling 400; the unchanged error assertions passed on the subsequent run. Screenshots remain in ignored `.local/qa`.

Native print controls are reused; final PDF rendering and pagination were not exercised. New report performance at commercial scale, concurrent assignment-write stress, full role/field privacy acceptance and dedicated contract/site/closure report formats remain unrun or incomplete. Earlier broad SaaS isolation and subscription results remain prior evidence; this increment did not rerun every upstream or production acceptance check.

## Two product sides and launcher correction — October 17

The extra launcher entries were upstream engine apps, not additional tenant/platform sides. The boot hook now uses native `on_apps_screen` flags to show one PLUS POINT entry on a customer site and one High4Tech admin entry on the separate control-plane site. Full native route/dock metadata remains present, and no document permissions or accounting behavior changed. Shared staff accounts, accounts and permitted HR tools are linked inside the customer's More tools and setup. The customer guide explains the two sides; the platform guide covers subscribers, plans, billing and access instead of contractor job steps.

Actual Edge checks as the named tenant dummy account confirmed one launcher entry, All apps return, internal HR tools, staff accounts/Users, native Home dashboard, linked HR employee self-service and browser Back. Platform checks as its dummy account confirmed one High4Tech admin entry, platform-specific guidance and native field help. The tenant tour/help/mobile regression passed with one product caption. The project/worker reports and real XLSX export also passed again under the simplified launcher. Successful runs observed zero JavaScript or HTTP errors and changed no business records. Python/JavaScript syntax and whitespace checks pass. This presentation change did not rerun the financial/database suite; its prior 31-case pass remains recorded above.
