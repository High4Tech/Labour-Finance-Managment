# Acceptance test plan

Executed evidence and limitations are in VERIFICATION_STATUS.md; source-of-truth design is MVP_ARCHITECTURE.md. Never mark a test passed from the existence of a script or a synthetic fixture.

## Automated regression layers

1. Offline: 11 project/harness tests and 10 arithmetic/register tests. These do not replace ERPNext integration.
2. Real MariaDB: 24 business regressions with rollback, run by plus_point.testing.run_operations.
3. Real HTTP: native login/REST CRUD, anonymous denial, cross-site token/record isolation and 60 authenticated concurrent reads through scripts/verify-live.py.
4. Real HTTP subscription: suspension, expiry, active seat limit, reactivation and cleanup through scripts/verify-subscription.py on the local QA site.
5. Real browser: tenant/High4Tech workspaces and native list navigation using scripts/browser-smoke.cjs; app-switcher/HR/Home/Users round trip using scripts/browser-navigation.cjs, optionally as a named local account with linked employee self-service; screenshots in private .local/qa.
6. Native installer: fresh disposable site/database/user through environment-only credentials, native cleanup limited to that generated test site.
7. Onboarding browser: `scripts/browser-onboarding.cjs` checks the tenant workflow tour (Next/Back/Escape/Finish), app-role explanations, collapse preference after reload, field help by first click and keyboard, field tour, return from an optional module, app captions, mobile width/tour placement and platform-specific home/tile/field guidance. Guidance tests do not write business documents.
8. Customer workspace browser: `scripts/browser-customer-ux.cjs` checks the default home, collapsed optional content, plain-language sidebar/list labels, comfortable primary target, hidden list ID column and 390px layout. It creates a populated attendance draft on a vacant demo date, reopens that same draft without duplicates or submission, and removes its temporary record. Run against a local tenant only; it refuses a date with an existing register.

## Release gates still required

- Realistic 20/100/1000-worker bulk posting, concurrent write races, deadlocks, latency/CPU/memory/disk profiling.
- Full tenant role matrix, field privacy, site-scoped permissions and privileged direct-SQL endpoint review.
- Approved attendance corrections, invoice credit/rebilling allocation and project closure reconciliation.
- Full native subscription renewal/payment lifecycle and provider signature/idempotency tests.
- Production image/security scanning, individual accounts/MFA, HTTPS, monitoring, encrypted backups and a demonstrated restore.

CI: quality.yml checks source and pure rules. plus-point-integration.yml installs the real pinned stack and tests it; its optional run_saas dispatch input also provisions platform/QA sites and exercises isolation/subscription HTTP. Legacy upstream demo workflow remains only a separate framework smoke, not PLUS POINT acceptance.
