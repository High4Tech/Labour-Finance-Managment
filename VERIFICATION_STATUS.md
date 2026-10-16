# Verification status — 2026-10-16

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
