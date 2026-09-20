#!/usr/bin/env bash
set -euo pipefail

expected_node="24.21.0"
observed_node="$(node --version)"
if [[ "$observed_node" != "v${expected_node}" ]]; then
  printf 'FAIL expected Node.js v%s, observed %s\n' "$expected_node" "$observed_node" >&2
  exit 1
fi

ruby -ryaml -e '
  config = YAML.safe_load(File.read("compose.yaml"), aliases: false)
  services = config.fetch("services")
  raise "expected only api and web services" unless services.keys.sort == %w[api web]
  api = services.fetch("api")
  web = services.fetch("web")
  [api, web].each do |service|
    raise "container must be read-only" unless service.fetch("read_only") == true
    raise "container must drop all capabilities" unless service.fetch("cap_drop") == ["ALL"]
    raise "container must deny privilege escalation" unless service.fetch("security_opt") == ["no-new-privileges:true"]
  end
  raise "api must not publish a host port" if api.key?("ports")
  raise "web must bind to loopback" unless web.fetch("ports") == ["127.0.0.1:${SOCHRON_WEB_PORT:-8080}:8080"]
  raise "trading mode must be demo" unless api.fetch("environment").fetch("TRADING_MODE") == "demo"
  raise "auto trading must be false" unless api.fetch("environment").fetch("AUTO_TRADING_ENABLED") == "false"
  raise "application network must be internal" unless config.fetch("networks").fetch("app_internal").fetch("internal") == true
  raise "api must join only internal network" unless api.fetch("networks") == ["app_internal"]
  raise "web must join internal and ingress networks" unless web.fetch("networks").sort == %w[app_internal web_ingress]
  raise "ingress must permit port publishing" unless config.fetch("networks").fetch("web_ingress").fetch("driver") == "bridge" && !config.fetch("networks").fetch("web_ingress")["internal"]
  raise "journal volume must be explicit" unless config.fetch("volumes").fetch("journal_data").fetch("name") == "${SOCHRON_JOURNAL_VOLUME:-sochron1k_journal_data}"
  puts "PASS Compose YAML structure and safety assertions"
'

for image in \
  'python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f' \
  'node:24.21.0-bookworm-slim@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553' \
  'nginx:1.30.5-alpine3.24@sha256:25820c39dba41369486df729ad6697de2fab631ca809e0503e1d1e0c73d9a232'; do
  if ! rg --fixed-strings --quiet "$image" services/api/Dockerfile apps/web/Dockerfile; then
    printf 'FAIL missing admitted image identity: %s\n' "$image" >&2
    exit 1
  fi
done

if rg --ignore-case --quiet 'TRADING_MODE: live|AUTO_TRADING_ENABLED: "?true|0\.0\.0\.0:.*:8000' compose.yaml; then
  printf 'FAIL Compose configuration exposes a live, auto-enabled, or host API path\n' >&2
  exit 1
fi

python3 - <<'PY'
from pathlib import Path

nginx = Path("apps/web/nginx.conf").read_text()
deny = "location ^~ /api/internal/"
proxy = "location /api/"
if deny not in nginx or "return 404;" not in nginx[nginx.index(deny):nginx.index(proxy)]:
    raise SystemExit("FAIL browser ingress does not deny the private alert source")
print("PASS private alert source denied at browser ingress")
PY

python3 scripts/check-no-secrets.py
printf 'PASS SCN-003 static container topology on Node.js %s\n' "$expected_node"
