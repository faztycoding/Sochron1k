# SCN-008 AC-07 internal Python artifact

2026-09-17. Base `b1832afbd45fc8dfdbc8eb2f7976f0543839b63b`, dirty candidate;
verified at `2026-09-17T06:32:52.661773+00:00` on macOS 26.6.2 arm64.
Python 3.14.7, uv 0.12.15, pytest 9.1.1, Ruff 0.16.8.

## Outcome and limits

An internal wheel installs both existing Python packages and exposes `sochron-sync`
without source-relative PYTHONPATH. Installed console/module invocations preserve
disabled defaults, private init/status, redacted failures and interruption/recovery
semantics. This completes the installable-artifact detail of AC-07, not all operator
delivery. Target Linux/container packaging, backup/restore and full Demo gates are
still incomplete. Hosted services, Supabase, MT5 and owner UI/API processes were
not started or modified by this verifier. No package was published or daemon enabled.

The only production-code change is a shared `cli()` signal wrapper. Console scripts
call a function rather than executing a module's `__main__` guard, so both entry
paths now install the SIGTERM handler and restore the previous handler on return
or SystemExit. Core source, transport, journal, risk and API behavior is unchanged.
Runtime dependencies retain all previous locked versions. Build-only additions are
Hatchling 1.32.0, pathspec 1.1.1, tomlkit 0.15.1 and trove-classifiers 2026.6.1.19;
existing packaging 26.3 and pluggy 1.6.0 satisfy the remaining backend requirements.

## Independent checks

The verifier checks installed build versions against `uv.lock`, builds an sdist
and wheel with fixed SOURCE_DATE_EPOCH, and rebuilds the wheel directly. Both wheel
files have identical bytes. It verifies the complete wheel member set: 22 source
modules plus four dist-info files, and every module's bytes against the checkout.
The sdist includes those source files, pyproject, uv.lock, PKG-INFO and Hatch's
required .gitignore metadata (whose bytes are also checked). No runtime data,
fixture, secret, frontend or development helper is shipped in the wheel.

A fresh virtual environment outside the checkout installs production requirements
with hash enforcement and binary-only dependency selection, then the wheel with
no index or dependency resolution. The entire installed distribution/version set
matches the platform-active exported requirements plus sochron1k 0.1.0. Module
locations are inside that environment, with no pytest or Hatchling installed.
The actual worker child has no PYTHONPATH and runs outside the repository.

The installed console and module default to DISABLED. Help works; an intentionally
invalid generated key-like argument returns a redacted error without echoing it.
Private init/status work with no service-key file and no network effects; a second
init is denied. A synthetic loopback receiver accepts a real worker HTTP request
and withholds its response. SIGTERM produces STOPPED/exit 130 with no traceback or
key. Independent SQLite inspection finds UNKNOWN, attempt 1, cursor 0. A new
installed process reads back the fixture destination, reaches VERIFIED, then IDLE;
local status has receipt 1 and no pending batch. The receiver observed one store.

This receiver is synthetic and in-memory; the separate AC-06 report supplies real
local PostgREST evidence for its recorded revision. Neither test establishes TLS,
hosted authentication, power-loss durability, target recovery or broker truth.

## Exact commands and results

On this workstation uv was invoked at `/tmp/sochron-uv.dALxxk/venv/bin/uv` after
verifying it reports 0.12.15; that temporary tool path is not a deployment requirement.

- `uv lock`: PASS; only build-group additions, no runtime upgrades.
- `uv sync --frozen --all-groups`: PASS. The project is intentionally dependency-only
  in the developer environment; the console-script-not-installed warning is expected.
- `.venv/bin/ruff check scripts/check-worker-package.py services/worker/src/sochron_worker/__main__.py tests/test_sync_transport.py`: PASS.
- `.venv/bin/pytest -q tests/test_sync_transport.py`: **69 PASS**.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv .venv/bin/python scripts/check-worker-package.py`:
  PASS, all four artifact/install/CLI/recovery groups.
- `bash scripts/check-scn-001-local.sh`: **427 PASS**, Ruff and secret scan PASS.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`
  and `git diff --check`: PASS.

Initial formatting checks found long lines, corrected before verification. The
first artifact verifier rejected Hatch's automatically included .gitignore. The
official sdist contract and pinned backend source establish this required metadata;
the verifier now requires that exact file and its exact bytes, not a wildcard
allowlist. No secret/fixture exclusion or recovery assertion was removed.

Frontend, database and target-container checks were not rerun: no UI, migration,
Compose or Dockerfile changed. Existing dependency-only container sync is retained;
an actual target build remains a separate gate.

## Artifact identity

Retained locally under `output/worker-package/0a927fe6611149cab04d380ddf554816/`:

| Artifact | SHA-256 |
| --- | --- |
| `sochron1k-0.1.0-py3-none-any.whl` | `a5ef5a1d31325904aa5e01546f57742ea8a7d7e1f1900ffb084cc1d41bbec60c` |
| `sochron1k-0.1.0.tar.gz` | `5b50f6d56d96df205cb9d238ee96e48196c79ffadfafd7a6cdb804b1ece0d3e2` |
| `requirements.txt` | `4b1ac33c8d278e015c3aba2250cd65f20891f3705c61867fd831ca35950b5289` |

`result.json` records all module, lock, build config, fixture and verifier hashes.
Verifier SHA-256: `5716363dae8a749146517f75b5abf570354e1fe3c5a639dd772aa8b106085f13`.
The commit containing this report identifies the final candidate; no source or
build input changed after the successful artifact run. Temporary fixture key,
source, journal and installation were removed; no operator state was deleted.
Artifacts are ignored local outputs, reproducible from the committed source and
locked build environment. Version 0.1.0 alone is not sufficient evidence identity.

The [operations skill](../../tooling/skills/sochron-vps-operations/SKILL.md) guided
artifact/config identity and explicit activation; the
[risk/recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md) guided
UNKNOWN preservation and restart oracles. Blueprint sections 05, 13-16 and 19-23
were visually checked without modifying the PDF. See [ADR-010](../decisions/ADR-010-python-delivery-artifact.md)
for official build documentation and [operator instructions](../operations/native-m1-sync.md).
