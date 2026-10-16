#!/usr/bin/env bash
set -euo pipefail
need() { if ! command -v "$1" >/dev/null 2>&1; then echo "MISSING: $1" >&2; return 1; else echo "OK: $1"; fi; }
failed=0
for binary in bash git docker python3; do need "$binary" || failed=1; done
if command -v docker >/dev/null 2>&1; then
  docker compose version || failed=1
  docker info >/dev/null 2>&1 || { echo "Docker daemon is not accessible" >&2; failed=1; }
fi
if [[ "$failed" != 0 ]]; then echo 'Install missing prerequisites before bootstrap.' >&2; exit 1; fi
echo 'Preflight passed. This does not prove ERPNext/HRMS are installed or running.'
