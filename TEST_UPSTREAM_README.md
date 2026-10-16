# PLUS POINT: first real upstream verification

**This is a framework smoke-test stage, NOT the SaaS MVP and NOT an HRMS integration test.**

This verification uses the official `frappe/frappe_docker` **disposable ERPNext demo**. It downloads actual upstream containers, initializes a MariaDB-backed site, and checks the live HTTP and authenticated Company APIs plus a database read. The Windows runner collects 20 sequential response times. This is **not** production configuration and **not** a substitute for testing the `plus_point` custom app or HRMS.

## On Windows: no Ubuntu commands

Simplest option: **double-click `RUN_ERPNext_TEST.cmd`** in your project folder. It runs the tests using Windows Docker Desktop and cleans up the disposable containers afterward.

Alternatively, open **Windows PowerShell** inside `D:\Labour-Managment-Software\Labour-Finance-Managment` (not Ubuntu), with Docker Desktop running in Linux containers mode, then:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-erpnext-windows.ps1 -StopAfterTest
```

The script fetches the official compose file from GitHub and runs it as a disposable test stack, exposing HTTP **only on 127.0.0.1:8080**. It downloads large Docker images, may need 5–15 minutes and a few GB free. The `-StopAfterTest` switch removes test containers and volumes (not your project files); omit it if you want to inspect the temporary demo. You must not enter actual PLUS POINT customer data in this stack; the default demo credentials are `Administrator/admin`.

This script does **not** execute the `bootstrap-local.sh` custom development setup; that remains the next stage once baseline checks succeed. It does not require WSL Ubuntu integration because `docker` is invoked by Windows PowerShell, where the user's Docker CLI already works.

## GitHub Actions integration test

`.github/workflows/upstream-integration.yml` starts the same official disposable Docker example on a hosted Linux runner and executes:

1. Real HTTP ping and Frappe/ERPNext installed-app checks.
2. A real MariaDB-backed DocType read through Frappe bench.
3. Generate a disposable API token on the throwaway site.
4. Authenticated HTTP ToDo create/read/update/delete (cleaned up).
5. Light 60-request, five-concurrent-worker response measurement.

The workflow runs automatically when pushed/PR'd and can also be started manually from GitHub Actions. **A green workflow only verifies upstream ERPNext**, not HRMS, custom business APIs, tenant billing, super-admin functions, security hardening or production load. Those need subsequent implementation and tests.

## Scope boundaries

- Frappe Docker's `pwd.yml` is officially documented as **disposable, not suitable for adding custom apps**.
- Final PLUS POINT must use the custom-app development setup, then build an immutable production image with the custom app installed.
- Never reuse disposable Docker demo passwords, volumes or exposed endpoints for production.
- Both per-worker-day and fixed milestone billing, tenant isolation and central subscription controls remain part of `MVP_ARCHITECTURE.md`.

## Known restrictions

- Network access and Docker Engine are necessary for **real** upstream tests.
- Demo Compose is fetched from upstream `main`, but the ERPNext container tag is normalized to `v16.51.1`. Pin a Compose source commit and image digest before relying on CI reproducibility.
- Test credentials are ephemeral, not a production secret strategy.
- If token generation fails due to a Frappe version change, that is a valid CI failure requiring adaptation, not proof the application is broken.

### Upstream dependency constraints actually inspected

At inspection on 2026-10-16, the `version-16` `pyproject.toml` files specify: **Frappe Python >=3.14,<3.15**, **ERPNext Python >=3.14** and **ERPNext Frappe >=16.50,<17**; HRMS requires **Frappe >=16.50,<17 and ERPNext >=16.50,<17**. Local host Python is irrelevant to the disposable Docker smoke test, but the later full development bench must satisfy the requirements. These dependency constraints were read from upstream repository sources, **not runtime-tested**.
