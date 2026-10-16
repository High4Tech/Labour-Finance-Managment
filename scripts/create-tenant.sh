#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] || { echo 'Missing local .env' >&2; exit 1; }
set -a; source "$ROOT/.env"; set +a
SITE="${1:-}"
[[ "$SITE" =~ ^[a-z0-9][a-z0-9.-]*\.localhost$ ]] || { echo 'Usage: create-tenant.sh tenant-name.localhost' >&2; exit 2; }
[[ "$SITE" != "${LOCAL_SITE:-demo.localhost}" ]] || { echo 'Use a different name from the main demo site.' >&2; exit 2; }
[[ "${PP_ADMIN_PASSWORD:-}" != '' ]] || { echo 'Set PP_ADMIN_PASSWORD in .env' >&2; exit 1; }
UPSTREAM="$ROOT/.local/frappe_docker"
export PLUS_POINT_ROOT="$ROOT" FRAPPE_PORT="${FRAPPE_PORT:-8000}"
COMPOSE=(docker compose -p pluspoint-dev -f "$UPSTREAM/.devcontainer/docker-compose.yml" -f "$UPSTREAM/.devcontainer/plus-point.override.yml")
"${COMPOSE[@]}" exec -T -e PP_ADMIN_PASSWORD="$PP_ADMIN_PASSWORD" -e NEW_SITE="$SITE" frappe bash -lc '
  set -e
  cd /workspace/development/frappe-bench
  test ! -d "sites/$NEW_SITE" || { echo "Site already exists"; exit 1; }
  bench new-site "$NEW_SITE" --db-host mariadb --db-root-username root --db-root-password 123 --admin-password "$PP_ADMIN_PASSWORD" --mariadb-user-host-login-scope "%"
  bench --site "$NEW_SITE" install-app erpnext
  bench --site "$NEW_SITE" install-app hrms
  bench --site "$NEW_SITE" list-apps
'
echo "Second isolated development tenant created: http://$SITE:$FRAPPE_PORT"
