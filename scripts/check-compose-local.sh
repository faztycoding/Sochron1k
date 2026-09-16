#!/usr/bin/env bash
set -euo pipefail

expected_node="24.21.0"
observed_node="$(node --version)"
if [[ "$observed_node" != "v${expected_node}" ]]; then
  printf 'FAIL expected Node.js v%s, observed %s\n' "$expected_node" "$observed_node" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  printf 'BLOCKED a running Docker-compatible engine is required for container verification\n' >&2
  exit 2
fi

web_port="${SOCHRON_WEB_PORT:-8080}"

cleanup() {
  docker compose down >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose config --quiet
docker compose build --pull --no-cache
docker compose up --detach --wait --wait-timeout 90

api_container="$(docker compose ps --quiet api)"
web_container="$(docker compose ps --quiet web)"

[[ "$(docker inspect --format '{{.Config.User}}' "$api_container")" == "10001:10001" ]]
[[ "$(docker inspect --format '{{.Config.User}}' "$web_container")" == "101:101" ]]
[[ "$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$api_container")" == "true" ]]
[[ "$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$web_container")" == "true" ]]

curl --fail --silent --show-error "http://127.0.0.1:${web_port}/" >/dev/null
health_json="$(curl --fail --silent --show-error "http://127.0.0.1:${web_port}/api/health")"
HEALTH_JSON="$health_json" .venv/bin/python -c '
import json, os
assert json.loads(os.environ["HEALTH_JSON"]) == {
    "status": "ok",
    "service": "sochron1k-api",
    "version": "0.1.0",
    "trading_mode": "demo",
    "auto_trading_enabled": False,
    "execution_ready": False,
}
'

volume_before="$(docker volume inspect sochron1k_journal_data --format '{{.Name}}')"
docker compose restart api
docker compose up --detach --wait --wait-timeout 90
volume_after="$(docker volume inspect sochron1k_journal_data --format '{{.Name}}')"
[[ "$volume_before" == "$volume_after" ]]

printf 'PASS SCN-003 local build, hardening, health, proxy, and volume checks\n'
