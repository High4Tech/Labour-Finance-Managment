# Acceptance test plan

Executed evidence and limitations are in VERIFICATION_STATUS.md; source-of-truth design is MVP_ARCHITECTURE.md. Never mark a test passed from the existence of a script or a synthetic fixture.

## Automated regression layers

1. Offline: 11 project/harness tests and 10 arithmetic/register tests. These do not replace ERPNext integration.
2. Real MariaDB: 61 business regressions with rollback, run by plus_point.testing.run_operations. Includes assignment closing/rate replacement, same-site overlaps, report company/date scope, deployment deduplication, fixed-worker revenue, opening/period/closing wage balances, spending limits, guided setup and historical imports.
3. Real HTTP: native login/REST CRUD, anonymous denial, cross-site token/record isolation and 60 authenticated concurrent reads through scripts/verify-live.py.
4. Real HTTP subscription: suspension, expiry, active seat limit, reactivation and cleanup through scripts/verify-subscription.py on the local QA site.
5. Real browser: `browser-product-scope.cjs` checks both curated product homes/sidebars, native support buttons, search filtering, no app/module menu, unrelated-route return and desktop/390px layout. `browser-smoke.cjs` and `browser-navigation.cjs` delegate to it. Old cross-app/HR self-service checks no longer describe the requested interface.
6. Native installer: fresh disposable site/database/user through environment-only credentials, native cleanup limited to that generated test site.
7. Onboarding browser: `scripts/browser-onboarding.cjs` checks the tenant workflow tour (Next/Back/Escape/Finish), two-sided product explanations, collapse preference after reload, field help by first click and keyboard, field tour, return from an unrelated module, a single product workspace, mobile width/tour placement and platform-specific home/field guidance. Guidance tests do not write business documents.
8. Customer workspace browser: `scripts/browser-customer-ux.cjs` checks the default home, collapsed optional content, plain-language sidebar/list labels, comfortable primary target, hidden list ID column and 390px layout. It creates a populated attendance draft on a vacant demo date, reopens that same draft without duplicates or submission, and removes its temporary record. Run against a local tenant only; it refuses a date with an existing register.
9. Contractor reports browser: `scripts/browser-reports.cjs` opens reports from home, Employee and billing terms, verifies project values against the existing financial API, switches financial/deployment and work/assignment views, checks calculation notes, performs a real native XLSX export and verifies a 390px report layout. It uses browser-native login and the seeded local demo data; it writes no business records. Native print controls are available, but final PDF rendering/print pagination is not certified by this check.

10. Platform support: `verify-platform-flow.py` tests actual local HTTP plan edits, platform-only immutable support requests, native RQ/isolated customer execution, username changes, one-time password recovery, old-password rejection, secret masking, suspension/reactivation and cross-site token/database rejection. Test fixtures/settings are restored. Do not run alongside other QA entitlement mutations.
11. Software accounting: `plus_point.testing.run_platform_finance` creates a native monthly plan/subscription, submits its invoice and payment, verifies GL and zero outstanding, and rolls back all fixtures.

12. Dashboard checks: customer database fixtures verify company scope, approved half-days, exclusion of drafts and guest/inaccessible-company rejection. Native platform finance fixtures verify dashboard invoice balance before/after payment, current-month posted sales/receipts and exclusion of future postings. The focused browser check verifies four metrics, two panels, refresh, dashboard-before-tools ordering and 390px width on both sites.

13. Spending rules: real database tests cover 80% and exact/over-limit boundaries, no wage creation for blocked registers, separate client billing, lowered-budget overruns, zero-cost entries, native purchases and expense claims with cancellation, and preview permissions.
14. `browser-conditions.cjs` temporarily changes only the local demo budget, verifies actual overrun figures and native pre-submit blocked/warning/cancel states, observes existing approved-work success, injects an error/empty response for presentation coverage, and restores the original budget plus removes its draft. It refuses to replace an already enabled demo budget.

15. Setup/import acceptance: real database checks cover resume/skip, new job/agreement creation, real worker/site assignments without attendance, employee create/update/explicit same-company IDs, CSV errors, XLSX values/formula refusal, actual work and employee payment GL, linked native invoice/partial receipt, fixed milestones/caps, expenses/budgets, stale limits, suspension, replay/conflict rules, wrong-user/guest/platform denial and atomic whole-file rollback. `scripts/browser-setup-imports.cjs` walks through the real setup, tests background focus blocking and release, reload/resume, template/reference downloads, no-write preview, real employee import, duplicate skip, row error download action and 390px layouts. Its exact temporary workers/sites/assignments/import receipt and original guide state are cleaned up in finally. Run it sequentially with database fixtures; native user creation clears global cache and may invalidate pending previews.

The read-only `scripts/browser-list-imports.cjs` checks persistent header Import actions beside Add on all seven supported customer lists, including a populated Employee list, matching template downloads and mobile/reload behavior. Set `PP_BROWSER_PASSWORD` (and optionally `PP_BROWSER_USER`) for the local customer account; credentials are not stored in the script.

## Release gates still required

- Realistic 20/100/1000-worker bulk posting, concurrent write races, deadlocks, latency/CPU/memory/disk profiling.
- Full tenant role matrix, field privacy, site-scoped permissions and privileged direct-SQL endpoint review.
- Approved attendance corrections, invoice credit/rebilling allocation and project closure reconciliation.
- Full native subscription renewal/payment lifecycle and provider signature/idempotency tests.
- Production image/security scanning, individual accounts/MFA, HTTPS, monitoring, encrypted backups and a demonstrated restore.

CI: quality.yml checks source and pure rules. plus-point-integration.yml installs the real pinned stack and tests it; its optional run_saas dispatch input also provisions platform/QA sites and exercises isolation/subscription HTTP. Legacy upstream demo workflow remains only a separate framework smoke, not PLUS POINT acceptance.

## Activity dashboards

Run `scripts/browser-activity-overview.cjs` with the customer test password supplied in `PP_BROWSER_PASSWORD` and optional `PP_BROWSER_CHANNEL=msedge`. It snapshots/restores the dummy login's exact section order/read preferences through a non-HTTP operator helper. Check six stats before the inbox; range-based approved work; actual financial amounts; date details; front-page client/company calendars; section counts and company-scoped list navigation; save/reload ordering; read acknowledgement without resolving records; 390px width and browser errors. Review `activity-overview.png`, `activity-calendars.png`, `client-billing-hub.png` and `client-front-activity.png` in ignored `.local/qa`.

Run database tests sequentially with browser mutation fixtures to avoid unrelated native cache-clearing races. `plus_point.testing.run_operations` now covers activity, scope, preferences and acknowledgements alongside all existing posting/import/budget rules. `browser-conditions.cjs` verifies budget and load/empty states; `browser-product-scope.cjs` verifies the separate platform UI.

## Display currencies

`browser-currency-display.cjs` checks actual current USD/EUR conversion, bold native-theme figures, rate/source disclosure, native-currency restoration and app Refresh persistence. A clearly isolated response fixture checks unavailable-rate fallback and retry; it is not represented as a real provider outage. It verifies unchanged worker quantities/source figures, reduced motion and 1100/768/390/320px widths without posting business records. Run with the local customer password in `PP_BROWSER_PASSWORD`.

The database suite adds four cases for Decimal projections and original-record preservation, unchanged non-money fields/notification IDs/budget states, rate failure retaining source amounts, currency/Guest denial before fetching, and stale/future/non-finite/zero-rate rejection. It mocks rate snapshots so suite correctness does not depend on Internet access or today's market. Live provider access is verified separately through the browser check.
