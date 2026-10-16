#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] && { set -a; source "$ROOT/.env"; set +a; }
: "${LOCAL_SITE:=demo.localhost}"
: "${FRAPPE_PORT:=8000}"
export FRAPPE_PORT PLUS_POINT_ROOT="$ROOT"
UPSTREAM="$ROOT/.local/frappe_docker"
[[ -f "$UPSTREAM/.devcontainer/plus-point.override.yml" ]] || { echo 'First run: bash scripts/bootstrap-local.sh' >&2; exit 1; }
COMPOSE=(docker compose -p pluspoint-dev -f "$UPSTREAM/.devcontainer/docker-compose.yml" -f "$UPSTREAM/.devcontainer/plus-point.override.yml")
case "${1:-}" in
  start)
    "${COMPOSE[@]}" up -d
    echo "Starting bench on http://$LOCAL_SITE:$FRAPPE_PORT (Ctrl+C stops bench, not data containers)"
    "${COMPOSE[@]}" exec -T frappe bash -lc 'cd /workspace/development/frappe-bench && bench start'
    ;;
  stop) "${COMPOSE[@]}" stop ;;
  status) "${COMPOSE[@]}" ps ;;
  version)
    "${COMPOSE[@]}" exec -T frappe bash -lc "cd /workspace/development/frappe-bench && bench version && bench --site '$LOCAL_SITE' list-apps"
    ;;
  logs) "${COMPOSE[@]}" logs --tail 100 ;;
  *) echo 'Usage: bash scripts/dev.sh {start|stop|status|version|logs}' >&2; exit 2 ;;
esac
