#!/usr/bin/env bash
# Project-scoped local startup; never print the CLI's generated service keys.
set -euo pipefail
cd "$(dirname "$0")/.."
root_dir="$(pwd -P)"
network="sochron1k_supabase_local"
action="${1:-}"
case "$action" in start|stop|guard) ;; *) printf 'Usage: %s start|stop|guard\n' "$0" >&2; exit 1 ;; esac
if [[ -e supabase/.temp/project-ref ]]; then
  printf 'FAIL hosted Supabase project link is outside local setup scope\n' >&2
  exit 1
fi
if ! rg -q '^project_id = "sochron1k"$' supabase/config.toml; then
  printf 'FAIL unexpected local project identity\n' >&2
  exit 1
fi
endpoint="${DOCKER_HOST:-}"
if [[ -z "$endpoint" || -n "${DOCKER_CONTEXT:-}" ]]; then
  endpoint="$(docker context inspect --format '{{.Endpoints.docker.Host}}')"
fi
case "$endpoint" in unix://*) ;; *) printf 'FAIL local Unix Docker socket required\n' >&2; exit 1 ;; esac
docker info >/dev/null
if docker container inspect supabase_db_sochron1k >/dev/null 2>&1; then
  actual_root="$(docker inspect supabase_db_sochron1k --format '{{index .Config.Labels "com.supabase.cli.workdir"}}')"
  [[ "$actual_root" == "$root_dir" ]] || { printf 'FAIL database belongs to another workdir\n' >&2; exit 1; }
fi
if [[ "$action" == guard ]]; then exit 0; fi
if [[ "$(node --version)" != v24.21.0 || "$(npm exec supabase -- --version)" != 2.117.0 ]]; then
  printf 'FAIL use pinned Node 24.21.0 and Supabase CLI 2.117.0\n' >&2
  exit 1
fi
if [[ "$action" == stop ]]; then
  exec npm exec supabase -- stop --project-id sochron1k --agent no
fi
if ! docker network inspect "$network" >/dev/null 2>&1; then
  docker network create --driver bridge \
    --label com.sochron.scope=local-db \
    --opt com.docker.network.bridge.host_binding_ipv4=127.0.0.1 "$network" >/dev/null
fi
network_config="$(docker network inspect "$network" --format '{{.Driver}} {{index .Options "com.docker.network.bridge.host_binding_ipv4"}} {{index .Labels "com.sochron.scope"}}')"
[[ "$network_config" == 'bridge 127.0.0.1 local-db' ]] || { printf 'FAIL unsafe local database network\n' >&2; exit 1; }
npm exec supabase -- start --network-id "$network" --agent no >/dev/null
if ! "${SOCHRON_PYTHON:-.venv/bin/python}" - <<'PY'
import json
import subprocess

ids = subprocess.check_output(
    ['docker', 'ps', '-q', '--filter', 'label=com.supabase.cli.project=sochron1k'],
    text=True,
).split()
if not ids:
    raise SystemExit('FAIL no local Supabase containers')
for container in ids:
    ports = json.loads(subprocess.check_output(
        ['docker', 'inspect', container, '--format', '{{json .NetworkSettings.Ports}}'],
        text=True,
    ))
    for bindings in ports.values():
        if any(binding['HostIp'] != '127.0.0.1' for binding in (bindings or [])):
            raise SystemExit('FAIL non-loopback Supabase publication')
print('PASS effective local Supabase bindings are loopback-only')
PY
then
  npm exec supabase -- stop --project-id sochron1k --agent no
  exit 1
fi
printf 'Local Supabase started; credential-bearing status output suppressed.\n'
