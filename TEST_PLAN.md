# Acceptance test plan

Executed evidence and limitations are in VERIFICATION_STATUS.md; source-of-truth design is MVP_ARCHITECTURE.md. Never mark a test passed from the existence of a script or a synthetic fixture.

## Automated regression layers

1. Offline: 11 project/harness tests and 10 arithmetic/register tests. These do not replace ERPNext integration.
2. Real MariaDB: 31 business regressions with rollback, run by plus_point.testing.run_operations. Includes assignment closing/rate replacement, same-site overlaps, report company/date scope, deployment deduplication, fixed-worker revenue, opening/period/closing wage balances, and guest/control-plane rejection.
3. Real HTTP: native login/REST CRUD, anonymous denial, cross-site token/record isolation and 60 authenticated concurrent reads through scripts/verify-live.py.
4. Real HTTP subscription: suspension, expiry, active seat limit, reactivation and cleanup through scripts/verify-subscription.py on the local QA site.
5. Real browser: `browser-product-scope.cjs` checks both curated product homes/sidebars, native support buttons, search filtering, no app/module menu, unrelated-route return and desktop/390px layout. `browser-smoke.cjs` and `browser-navigation.cjs` delegate to it. Old cross-app/HR self-service checks no longer describe the requested interface.
6. Native installer: fresh disposable site/database/user through environment-only credentials, native cleanup limited to that generated test site.
7. Onboarding browser: `scripts/browser-onboarding.cjs` checks the tenant workflow tour (Next/Back/Escape/Finish), two-sided product explanations, collapse preference after reload, field help by first click and keyboard, field tour, return from an unrelated module, a single product workspace, mobile width/tour placement and platform-specific home/field guidance. Guidance tests do not write business documents.
8. Customer workspace browser: `scripts/browser-customer-ux.cjs` checks the default home, collapsed optional content, plain-language sidebar/list labels, comfortable primary target, hidden list ID column and 390px layout. It creates a populated attendance draft on a vacant demo date, reopens that same draft without duplicates or submission, and removes its temporary record. Run against a local tenant only; it refuses a date with an existing register.
9. Contractor reports browser: `scripts/browser-reports.cjs` opens reports from home, Employee and billing terms, verifies project values against the existing financial API, switches financial/deployment and work/assignment views, checks calculation notes, performs a real native XLSX export and verifies a 390px report layout. It uses browser-native login and the seeded local demo data; it writes no business records. Native print controls are available, but final PDF rendering/print pagination is not certified by this check.

10. Platform support: `verify-platform-flow.py` tests actual local HTTP plan edits, platform-only immutable support requests, native RQ/isolated customer execution, username changes, one-time password recovery, old-password rejection, secret masking, suspension/reactivation and cross-site token/database rejection. Test fixtures/settings are restored. Do not run alongside other QA entitlement mutations.
11. Software accounting: `plus_point.testing.run_platform_finance` creates a native monthly plan/subscription, submits its invoice and payment, verifies GL and zero outstanding, and rolls back all fixtures.

## Release gates still required

- Realistic 20/100/1000-worker bulk posting, concurrent write races, deadlocks, latency/CPU/memory/disk profiling.
- Full tenant role matrix, field privacy, site-scoped permissions and privileged direct-SQL endpoint review.
- Approved attendance corrections, invoice credit/rebilling allocation and project closure reconciliation.
- Full native subscription renewal/payment lifecycle and provider signature/idempotency tests.
- Production image/security scanning, individual accounts/MFA, HTTPS, monitoring, encrypted backups and a demonstrated restore.

CI: quality.yml checks source and pure rules. plus-point-integration.yml installs the real pinned stack and tests it; its optional run_saas dispatch input also provisions platform/QA sites and exercises isolation/subscription HTTP. Legacy upstream demo workflow remains only a separate framework smoke, not PLUS POINT acceptance.
