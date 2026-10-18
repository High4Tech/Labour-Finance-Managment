# Verification status — 2026-10-18

Executed against Docker Desktop Linux engine on this Windows machine. This supersedes the original starter's unexecuted environment claims (preserved in docs/archive).

## Native-theme currency display follow-up

**61 MariaDB regressions passed** with zero failures/errors. Four new currency cases cover Decimal projections and unchanged source accounting, counts/calendar quantities/notification IDs/budget states and warning signs through sub-cent rounding, unavailable-rate fallback, same-currency/invalid/Guest paths without fetching, and stale/future/invalid-rate refusal. Business fixtures roll back; provider snapshots in these tests are controlled examples, not live-rate evidence.

The live provider was reached successfully from the app environment and supplied current PKR rates. The actual browser currency check passed USD/EUR conversion of existing demo figures, disclosure of the real rate/as-of/source, return to original PKR values, app Refresh persistence, read-only failure/retry UI fixture, bold native-theme rendering, unchanged work data/books, reduced motion and 1100/768/390/320px layout. Rates are daily indicative values with a one-hour cache, not streaming or bank settlement rates. Only public quotes leave the app request boundary; no business amount is sent to the provider.

Final currency assets passed the same browser check again. Customer activity/navigation/calendar/notification/personal-order regressions passed with original preferences restored; budget stop/warning/success/retry/empty states passed with the exact demo budget restored and temporary draft removed. High4Tech focused navigation/support/mobile checks passed using its dummy admin account. The retained preview shows USD amounts in the existing native light theme; all final browser flows reported zero application errors. An earlier activity navigation timeout and a harness login attempt with the wrong default username were corrected before these final passes.

## Dashboard presentation follow-up

The customer activity browser flow passed after restyling: six stats before the inbox, chart ranges, actual client/day details, notifications/read acknowledgement, scoped work lists, persisted personal order, native client/company calendars and 390px layout. Original personal preferences were restored. The state browser flow passed existing overrun/red-budget review, pre-submit stop, warning cancellation, approved-work success, load error/retry and empty-company CTA; exact budget/draft fixtures were restored/removed. High4Tech focused navigation, customer-support buttons, accounting reports and mobile checks passed after dismissing its unrelated native update notice; the harness now handles that notice explicitly.

Dedicated read-only browser checks observed moving connector signals, the 91-day control, identical metric text under reduced motion, no running decorative animations with reduced motion, no page overflow at 1100/768/390/320px, and contained date cells. Screenshot review covers desktop and narrow mobile. Financial/backend calculations and workflow endpoints are unchanged; previous 57-case database evidence below is retained, not represented as a new database run for this presentation increment.

## Activity calendar alignment follow-up

Real in-app browser checks verified all seven weekday labels, actual month/year headings, square day cells, weekday/date alignment and no calendar children outside any of the three demo client cards. Checks passed at desktop, 390px and 320px widths; the 320px page has no horizontal overflow. Arrow navigation moved exactly one week and an approved date opened its named work details. The native client front-page calendar also passed geometry/label checks. This is a frontend-only change; financial calculations, record approval and the existing 91-day scope are unchanged. JavaScript syntax and whitespace checks passed; database evidence below remains prior evidence for unchanged backend code.

## Activity dashboards and personal navigation

**57 MariaDB business regressions passed** after the latest activity and budget-aggregation changes. New checks cover approved half-days, future-work exclusion from the 91-day calendar, named daily details, company isolation and Guest denial, validated personal section order, native section counts and notification acknowledgement/change detection. Existing native purchase/claim tests also compare batched totals with individual ledger totals. Business fixtures roll back.

Real Edge as the customer dummy login passed six stats before the action inbox, actual work/finance charts, range switching, day details, client/company front-page calendars, company-scoped native list links, section summaries without charts, saved/reloaded personal ordering, read acknowledgement with unresolved actions retained, and 390px layout. Original personal order/read state were restored. All 11 offline project/harness checks and Python/JavaScript syntax checks passed. Separate High4Tech section-summary/focused-navigation/support/accounting-report browser checks passed with four platform metrics and no workforce UI. Budget warning/stop, existing overrun ticket, approved-work success, injected load failure/retry and empty-company CTA checks passed; exact demo budget/draft fixtures were restored/removed. Screenshots are in ignored `.local/qa`.

Native section Page migrations completed on demo, platform and QA. The local demo intentionally retains its labelled synthetic story (70 added approved work entries, realistic workers/clients and illustrative native invoice/receipt/wage records). The story performs no external transfers and its operator helper is not available over HTTP. Activity is aggregated in SQL before transfer; dashboard budgets use three ledger aggregates rather than three per project. These changes have no production load benchmark. Updates recalculate on open/refresh, with no background push or outgoing email. Calendars describe approved worker-days within 91 days, not verified presence or total lifetime engagement.

## Guided setup and historical imports

Quieter overview follow-up: real Edge confirmed the established demo has no visible setup banner, home import button or tour CTA. Manual Help → Guided setup, skip and reload/resume, saved worker/site/assignment, list-based employee import, duplicate handling and mobile focus all passed. Exact fixtures and the original guide state were restored. Backend eligibility rules and posting behavior are unchanged; the 53-case database result below remains prior evidence.

Follow-up frontend check: real Edge as the customer dummy login verified a populated Workers list and all seven supported employee/finance list headers, Import beside Add, matching default import types, actual CSV template downloads, list reload persistence and 390px layout. Screenshots were reviewed in `.local/qa`. No business records were written. JavaScript syntax and whitespace checks passed; the unchanged backend retains the 53-case evidence below.

**53 actual MariaDB regressions passed**, including the existing 40 plus 13 setup/import cases. Actual native records verify employee creation/update/replay, explicit same-company profile updates, CSV row errors, XLSX formula refusal, approved wage imports, submitted employee payment/settlement GL, source-linked client invoices and partial receipts, project expense costs, fixed milestones/caps, stale spending stops, subscription suspension and whole-file rollback. Setup tests save real worker/site/assignment and new project/agreement records, preserve skip/resume and create no attendance. All business fixtures roll back.

Real Edge browser checks passed setup skip, background inert/focus release, reload/resume, worker → site → agreement → assignment, saved completion and 390px guide layout. Template and reference-ID downloads, read-only employee preview, confirmed employee creation, duplicate skipping, row errors/download CTA and mobile import layout passed. Exact browser fixture records were removed and original setup progress restored; screenshots were visually reviewed in ignored `.local/qa`. An early test run overlapped cache-clearing database fixtures; the final browser pass ran sequentially and its cleanup uses a local saved progress snapshot. No test wages or financial postings remain.

Native target permissions and spending/subscription hooks remain in effect. Imports are bounded snapshots in company currency; no live Sheets connector, bank transfer, complete tax/stock/foreign-currency migration, large-scale batch stress or production role/privacy acceptance is claimed.

## Spending control and state increment

- **40 actual MariaDB regressions passed**. New checks cover the 80% warning boundary, exact-limit approval, rejected over-limit wages, whole-register refusal before any work is created, separation from fixed client milestones, visible existing overruns, zero-cost records and native purchase/expense-claim submission/cancellation. Posted purchases and sanctioned claims are counted once and appear in project financial summaries. Guest/invalid preview calls are rejected. Business fixtures roll back.
- Real browser state checks passed: a temporary demo budget produced red overrun figures and a review CTA; native pre-submit events stopped the proposed register, warning cancellation left it in draft, and an existing approved work record offered the next payment action. No new wages were posted. Original budget settings were restored and the temporary register deleted.
- Browser error injection verified retry/recovery with normal work tools retained. A presentation-only no-company fixture verified the empty-state CTA and 390px width; an actual no-company API response was separately observed on QA. These UI fixtures are not counted as backend validation evidence.
- Focused customer/platform dashboard/navigation checks passed, with a next action for each displayed condition. An existing repeated-redirect race was prevented by allowing only one product redirect per document.

Enforcement is disabled until an administrator sets a positive project budget and enables the stop. Scope is approved wages plus net posted purchases and sanctioned expense lines; it excludes taxes, overhead, stock consumption, timesheets, manual journals and unallocated costs. No concurrent cross-type spending race/stress benchmark or production role audit is claimed by this increment.

## Dashboard increment

Real company dashboards now sit above the existing tools on both overviews. **33 MariaDB regressions passed**, including approved half-day totals, draft exclusion, company scope and unauthorized access rejection. Native platform accounting fixtures verify outstanding balances before/after payment, current-month invoice/receipt totals, chart totals and exclusion of future postings; all fixtures roll back. Real Edge checks passed on both sites for dashboard loading, four summary metrics, two detail panels, refresh, preserved tool navigation and 390px width. Screenshots were visually reviewed in ignored `.local/qa`. Dashboards read saved records on opening/refresh; they do not claim automatic live streaming, forecast revenue or production capacity certification.

## Focused products and support — current increment

- Real Edge browser checks passed as each named dummy account at desktop/390px widths: customer and High4Tech each have one curated native sidebar/home. No extra Apps/Modules menu, HR tools or unrelated workspace navigation. Native command suggestions are filtered; unrelated Desk routes return home. Native accounting/HR dependencies and backend permissions remain installed.
- Registered the existing PLUS POINT demo as a platform trial customer, keeping its actual owner login and business database. No real software purchase or receipt was fabricated.
- Real local HTTP from outside Frappe: pricing-plan create/update/read; Guest and customer-site platform-support denial; queued registered-owner login-ID change while suspended; reactivation; native one-time password completion; new login and old-password rejection; reset result encrypted/masked; two-way cross-site token rejection and no customer User in the platform database. Original QA owner/settings restored and temporary users/requests/plans removed.
- Real native software accounting: a monthly price of 1,250 generated a posted subscription invoice and receivable GL; a posted native receipt created GL and reduced the invoice balance to zero. All financial fixtures rolled back.
- All **31 actual MariaDB business regressions**, **11 offline project/harness checks** and **10 pure finance/register checks** passed. Native customer/onboarding/report browser checks passed, including review-only draft creation/reopening, fixture deletion, project/deployment and worker history views, actual XLSX export and 390px width.
- Live customer HTTP CRUD/anonymous rejection, database/token isolation and 60 reads at concurrency 5 passed with zero errors (p95 98 ms). Ten simultaneous attendance attempts produced one draft and nine rejected duplicates; the draft was removed.

Support is local same-host/.localhost only. Native reset completion needs an active subscription; retrieval of the protected link lasts up to 20 minutes and native expiry also applies. No email is automatically sent. Payment providers, public Internet integrations, production hosting and a full role/privacy audit are not certified by these checks. Current scripts and commands are in LOCAL_RUNBOOK.md and TEST_PLAN.md. Earlier UI navigation evidence below records the historical interface and is superseded by the focused-product checks.

## Earlier runtime evidence

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
