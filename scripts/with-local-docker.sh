#!/usr/bin/env bash
# Use the dedicated development engine without changing the user's shell or Docker context.
set -euo pipefail
runtime_dir="${SOCHRON_RUNTIME_DIR:-${HOME}/.local/share/sochron-runtime}"
export PATH="${runtime_dir}/bin:${PATH}"
export DOCKER_CONFIG="${runtime_dir}/docker"
export DOCKER_HOST="unix://${HOME}/.colima/sochron1k/docker.sock"
unset DOCKER_CONTEXT DOCKER_TLS_VERIFY DOCKER_CERT_PATH
if [[ $# -eq 0 ]]; then
  printf 'Usage: bash scripts/with-local-docker.sh COMMAND [ARGS...]\n' >&2
  exit 1
fi
exec "$@"
