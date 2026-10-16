# PLUS POINT Frappe extension — v0.4

Extends native Frappe Desk, ERPNext and HRMS v16. Upstream owns Customer, Contract, Project, Employee, payroll, accounting, invoices, payments, authentication, permissions and REST.

Custom DocTypes: PP Site, PP Contract Terms, PP Assignment, PP Daily Register / PP Register Line, PP Work Entry, PP Milestone, PP Wage Settlement and PP Tenant. Source approval, historical wage/billing snapshots, native invoice reservation and same-host tenant entitlements are validated server-side. There is no replacement ERP or payment gateway.

Use the repository's compose.yaml and scripts/start-local.ps1 to install the pinned sources and this editable app. See the root README, MVP_ARCHITECTURE.md, LOCAL_RUNBOOK.md and VERIFICATION_STATUS.md. Source from the original v0.3 package was integrated and repaired; upstream repositories are not vendored here.

Tests in plus_point/tests include pure calculation rules and real MariaDB-backed ERPNext/HRMS regressions. Run real tests through plus_point.testing.run_operations on a local test-enabled site. Production security, role privacy, corrections and deployment acceptance remain separate.