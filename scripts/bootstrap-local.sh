#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# .env contains only developer-machine settings; ignored by git.
if [[ ! -f "$ROOT/.env" ]]; then
  echo 'Missing .env. Copy .env.example to .env and set PP_ADMIN_PASSWORD.' >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a
: "${FRAPPE_BRANCH:=version-16}"
: "${ERP_HRMS_BRANCH:=version-16}"
: "${LOCAL_SITE:=demo.localhost}"
: "${FRAPPE_PORT:=8000}"
: "${PP_ADMIN_PASSWORD:=}"
[[ "$FRAPPE_BRANCH" == 'version-16' && "$ERP_HRMS_BRANCH" == 'version-16' ]] || { echo 'Use mutually compatible verified Frappe/ERPNext/HRMS branches (starter targets v16).' >&2; exit 1; }
[[ -n "$PP_ADMIN_PASSWORD" && "$PP_ADMIN_PASSWORD" != replace-with-a-random-local-password && "${#PP_ADMIN_PASSWORD}" -ge 12 ]] || { echo 'Set a unique PP_ADMIN_PASSWORD (minimum 12 chars) in .env.' >&2; exit 1; }
[[ "$LOCAL_SITE" =~ ^[a-z0-9][a-z0-9.-]*\.localhost$ ]] || { echo 'LOCAL_SITE must be a safe *.localhost hostname.' >&2; exit 1; }
[[ "$FRAPPE_PORT" =~ ^[0-9]{2,5}$ ]] || { echo 'Invalid FRAPPE_PORT' >&2; exit 1; }
"$ROOT/scripts/preflight.sh"
UPSTREAM="$ROOT/.local/frappe_docker"
if [[ ! -d "$UPSTREAM/.git" ]]; then
  echo 'Cloning official Frappe Docker development environment...'
  mkdir -p "$ROOT/.local"
  git clone --depth 1 https://github.com/frappe/frappe_docker.git "$UPSTREAM"
fi
if [[ ! -d "$UPSTREAM/.devcontainer" ]]; then
  mkdir -p "$UPSTREAM/.devcontainer"
  cp -a "$UPSTREAM/devcontainer-example/." "$UPSTREAM/.devcontainer/"
fi
# Official devcontainer has no published port outside VS Code forwarding.
# Make the port loopback-only; never expose developer services publicly.
cat > "$UPSTREAM/.devcontainer/plus-point.override.yml" <<'YAML'
services:
  frappe:
    ports:
      - "127.0.0.1:${FRAPPE_PORT}:8000"
    volumes:
      - "${PLUS_POINT_ROOT}:/workspace/plus_point_project:cached"
YAML
cat > "$UPSTREAM/development/apps-plus-point.json" <<JSON
[
  {"url":"https://github.com/frappe/erpnext.git", "branch":"$FRAPPE_BRANCH"},
  {"url":"https://github.com/frappe/hrms.git", "branch":"$ERP_HRMS_BRANCH"}
]
JSON
export PLUS_POINT_ROOT="$ROOT" FRAPPE_PORT
COMPOSE=(docker compose -p pluspoint-dev -f "$UPSTREAM/.devcontainer/docker-compose.yml" -f "$UPSTREAM/.devcontainer/plus-point.override.yml")
echo 'Starting official dev dependencies; this may download significant images...'
"${COMPOSE[@]}" up -d
# Installer runs in the official development container. It uses a *hard-coded demo
# MariaDB root password from upstream and is never suitable for production.
if "${COMPOSE[@]}" exec -T frappe bash -lc "test -d /workspace/development/frappe-bench/sites/$LOCAL_SITE"; then
  echo "Existing site $LOCAL_SITE detected; not recreating it."
else
  echo "Installing Frappe + ERPNext + HRMS ($FRAPPE_BRANCH), then creating $LOCAL_SITE ..."
  # Set admin password via container env instead of injecting into a host-side log.
  "${COMPOSE[@]}" exec -T -e PP_ADMIN_PASSWORD="$PP_ADMIN_PASSWORD" frappe \
    bash -lc 'cd /workspace/development && python installer.py --apps-json apps-plus-point.json --frappe-branch "'"$FRAPPE_BRANCH"'" --site-name "'"$LOCAL_SITE"'" --admin-password "$PP_ADMIN_PASSWORD"'
fi
echo 'Installed apps reported by bench:'
"${COMPOSE[@]}" exec -T frappe bash -lc "cd /workspace/development/frappe-bench && bench --site '$LOCAL_SITE' list-apps"
# Require actual installations (not just downloaded apps) before declaring setup done.
APPS="$("${COMPOSE[@]}" exec -T frappe bash -lc "cd /workspace/development/frappe-bench && bench --site '$LOCAL_SITE' list-apps")"
for app in frappe erpnext hrms; do
  if ! printf '%s\n' "$APPS" | grep -Eq "^[[:space:]]*$app([[:space:]]|$)"; then
    echo "ERROR: app '$app' not installed on $LOCAL_SITE. Fix setup; do not call this successful." >&2
    exit 2
  fi
done
echo "Bootstrap installation verified via bench list-apps. Start web with: bash scripts/dev.sh start"
echo 'HTTP and CRUD tests still need to be run against the running web server.'
