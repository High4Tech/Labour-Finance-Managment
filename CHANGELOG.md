# Development changelog

## 0.4.0 — 2026-10-16

Integrated the discovered v0.3 source into the existing repository without replacing Git history; archived the original foundation documentation. Added pinned Windows Docker Desktop setup, persistent volumes, resumable native app installation and upstream setup defaults.

Reused native ERPNext/HRMS/Frappe business records, Desk, authentication and APIs. Repaired snapshots, historical allocations, pagination and posting concurrency guards. Added native invoice source reservation/posting/cancellation, client receipt summaries, wage settlements against native employee payments, and clear outstanding/profit figures.

Added separate High4Tech workspace/tenant registry backed by native subscriptions/plans, trusted local provisioning/owner accounts, hostname-isolated databases and current host-managed quota/expiry/suspension enforcement. Payment mode stays manual/development. Corrected Bench default-site routing and cached-entitlement enforcement after live tests exposed the defects.

Rotated local credentials following a process diagnostic exposure; provisioning no longer puts passwords in process arguments. Added real database, HTTP, isolation, subscription, browser and disposable-installer checks plus CI definitions. See VERIFICATION_STATUS.md for 45 automated unit/integration tests and separately executed live/browser checks, and explicit unverified production requirements.
Additional concurrency audit: explicitly configured READ COMMITTED for MariaDB 11.8 snapshot behavior, added current locking reads for financial limits/reservations, and verified 10 simultaneous attendance requests (one winner, nine duplicate rejections). Initialized native site encryption keys before web startup to repair fresh-runner first-token authentication. Added the write race to integration CI.
