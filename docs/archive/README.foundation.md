# PLUS POINT — SaaS Labour & Finance Management

**Status: foundation starter, not a running application.** This is a prepared overlay for the GitHub repository [`High4Tech/Labour-Finance-Managment`](https://github.com/High4Tech/Labour-Finance-Managment). The source repository initially contained only a README. The actual upstream Frappe/ERPNext/HRMS source and Docker images are downloaded **by the local bootstrap script**; they are intentionally not copied into this repository.

Read **[MVP_ARCHITECTURE.md](./MVP_ARCHITECTURE.md)** before any feature work. The scope includes a High4Tech platform super-admin, monthly SaaS subscriptions, isolated customer workspaces, workers and assignments, dehadi, two billing models (per worker-day and fixed-price), and profitability. None of the custom SaaS/business features are implemented in this starter.

## Requirements
- Git, Docker Desktop + WSL2 (on Windows) or Docker Engine + Compose (Linux/macOS), and Bash (use WSL2 or Git Bash).
- Recommended local machine: 16 GB RAM, several GB of free disk and functioning access to GitHub and Docker registries.
- VS Code recommended. Official Frappe devcontainer is the foundation.

## First-time local setup
```bash
git clone https://github.com/High4Tech/Labour-Finance-Managment.git
cd Labour-Finance-Managment
# Copy this starter's files into the checked-out repository, preserving README replacement.
cp .env.example .env
# EDIT .env and choose a secure PP_ADMIN_PASSWORD.
bash scripts/preflight.sh
bash scripts/bootstrap-local.sh
# In a separate terminal; leave this running to serve the app:
bash scripts/dev.sh start
```

Open **http://demo.localhost:8000** (site hostname in `.env`). If `.localhost` does not resolve on your machine, add the local host mapping or use an appropriate local DNS setup; multi-site tests require distinct hostnames. Login `Administrator` and the password from `.env`. **Never use this development setup, static MariaDB demo password, or plaintext HTTP in production.**

`bootstrap-local.sh` clones the OFFICIAL `frappe/frappe_docker` into ignored `.local/frappe_docker`, starts its development containers, and runs its upstream installer with ERPNext and HRMS `version-16`. First run downloads a large amount and can take substantial time. It does not create the custom PLUS POINT app yet.

## Commands
```bash
bash scripts/dev.sh status
bash scripts/dev.sh version
bash scripts/dev.sh start
bash scripts/dev.sh stop
bash scripts/create-tenant.sh example.localhost  # optional test-tenant site
python3 scripts/api_smoke.py --base-url http://demo.localhost:8000
PP_API_KEY=... PP_API_SECRET=... python3 scripts/api_smoke.py --base-url http://demo.localhost:8000 --crud
python3 scripts/load_test.py --base-url http://demo.localhost:8000 --requests 60 --concurrency 5
python3 -m unittest discover -s tests -v
```

Token authentication is needed for CRUD. To get a local test key and secret: open an appropriately privileged Frappe user, generate API keys in API Access, then place them in ignored `.env` or export them in your shell. **Do not commit or expose keys.** Use local development-only credentials for the destructive ToDo CRUD smoke test.

## Real test status (until someone runs Docker)
- Static source/script checks can run without GitHub/Docker.
- Upstream clone, container start, full API/CRUD checks, cross-site isolation, and performance have NOT been executed in the environment that generated this starter.
- See [TEST_PLAN.md](./TEST_PLAN.md) and [LOCAL_RUNBOOK.md](./LOCAL_RUNBOOK.md) for reproducible verification.

## Production direction
Build custom PLUS POINT apps into immutable official Docker images (as upstream documentation requires); **do not** ship the devcontainer or `pwd.yml` disposable demo. Start with a low-volume single VPS pilot, HTTPS, monitored database, encrypted offsite backups and restore drills. Each subscribing company uses an isolated Frappe site; High4Tech's subscription control plane uses a separate platform site. See architecture for plan enforcement and suspension safeguards.
