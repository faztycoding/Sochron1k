# Security pre-review OPS-001 round 1 · base main (origin/main `2e3e03d`) · head `b186329` + uncommitted D-006 patch on `.github/workflows/ci.yml` (blob `d940df73`) · reviewer Claude Code security-reviewer subagent (read-only)

Saved verbatim by the implementer from the subagent's final message (2026-10-23 10:2x); only HTML entities from the transport were restored to `<`, `>` and `&`.

The implementer saves this verbatim from the subagent's final message. It is a pre-review only. It does not replace the Codex security review (or the fresh-session review standing in for it under the role swap) that a High-tier task requires.

The reviewer edited, staged and committed nothing. No broker connection was made and no credential store was read. One public-network fetch was attempted and blocked by a hook (see "Not checked"). It was not retried or reshaped. **This review does not show that the job is secure.** It lists what was attacked, what held, and what was out of scope.

**Verdict:** no Critical or High finding.
- **F1, Medium, confirmed by source reading.** A failing or partial suite can turn the job green without touching a locked path. The routes are xfail, deselect, or silently not collecting tests.
- **F2, Low.** The job only fails closed on errors because the implicit default shell is `bash -e`. The handoff claims a second line of defence that does not exist for errors.
- **F3, Low, design limit.** The job's result is computed by the PR's own code (tests, conftest, `pyproject.toml`, `uv.lock`), so it cannot be a tamper-proof gate. This matters if the owner makes `python-tests` a required check (contract option ค).
- **F4, Low, question, pre-existing.** Required-check names can collide. Nothing stops a PR-run workflow from defining a job named `locked-paths`.
- **F5, Low, question, latent.** D-013 accepted GHSA-hq85-5cpj-mr62 on the grounds that the only impact is a red job. That reasoning holds only while no source distribution is built.
- **Write access, secrets, untrusted `${{ }}`, cache poisoning of main:** nothing found in what was checked. The internals of setup-uv (cache post step, checksum precedence, token export) were not re-verified; that fetch was BLOCKED.

## Assets, identities, trust boundary
- **Assets:**
  - the CI signal `ci / python-tests`, which the owner reads before merging
  - the locked acceptance and architecture tests (`rules.mjs:19`)
  - `GITHUB_TOKEN` (`contents: read`)
  - repository contents
  - the GitHub Actions cache (unused)
  - the runner
- **Identities:**
  - the owner (the only merger)
  - Claude (pushes task branches under D-006) and Codex
  - fork contributors, if the repository settings allow fork PRs
  - GitHub Actions
  - Astral: setup-uv, uv, python-build-standalone, the `releases.astral.sh` mirror, and the `astral-sh/versions` manifest on a mutable `main` branch
  - PyPI / files.pythonhosted.org
- **Boundary:**
  - `ci.yml` runs on `pull_request`. It executes the PR's own workflow file, tests, conftest, config and lock.
  - On same-repo branches the PR's YAML also decides its own token scope (pre-existing). Fork PRs get a capped read token.
  - The only trusted judge is `control-gate.yml` (`pull_request_target`, base revision). It judges which paths changed, not test results.

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed (pytest 9.1.1 source read; not executed) | `.github/workflows/ci.yml:70,74`; `scripts/controls/red-flags.sh:50,64`; `scripts/controls/rules.mjs:19` | The step accepts any last line matching `^[0-9]+ passed` that does not contain `skipped`. pytest orders summary parts `failed, passed, skipped, deselected, xfailed, xpassed, warnings, error, subtests …` (`_pytest/terminal.py:63-75,1455-1472`). So `N passed, M xfailed …` and `N passed, M deselected …` pass when the exit code is 0. Silently not collecting tests leaves only `N passed …` | An unlocked `tests/conftest.py` or a `pyproject.toml` `addopts` change: imperative `pytest.xfail(...)` on acceptance items, `--deselect`/`-k`/`-m`, `collect_ignore`, `pytest_ignore_collect` | Failing or excluded locked acceptance tests (50 test defs) and architecture tests (3) show a green `python-tests`. `control-gate` stays green (no locked path changed). red-flags has no pattern hit: `pytest.xfail(` and `collect_ignore` are not in `:50`, and `conftest.py` is not in the `:64` list | One allow-list regex on the whole last line (below). Silent non-collection needs a separate control task (below) | Scratch negative tests below: each must exit non-zero after the fix (today 0); clean and warning-only runs must exit 0 |
| F2 | Low | confirmed (source read) | `.github/workflows/ci.yml:65-68` (no `shell:`); `docs/handoff/OPS-001.md:76-77` | `error` sorts after `passed`, so `783 passed, 1 error in …` matches `^[0-9]+ passed` and contains no `skipped`. Only `bash -e` (GitHub's implicit default for an unspecified shell) plus `pipefail` stops it. The handoff says the checks "still exit 1" without `-e`, which is wrong for errors | A future edit sets `shell: bash {0}`/`sh`, or the step is copied to a shell without `-e` | A fixture setup or teardown error shows green | F1's allow-list rejects `error`. Optionally add an explicit `shell: bash`, which GitHub runs as `bash --noprofile --norc -eo pipefail {0}`. Correct the handoff sentence | `bash step.sh` (no `-e`) on a suite with one teardown error must exit 1 |
| F3 | Low | design limit | `.github/workflows/ci.yml:36-40,68`; contract `OPS-001-python-ci.md:72` (ค) | The job executes the code it judges. A test module or conftest (unlocked) can call `atexit.register(lambda: (sys.stdout.write("784 passed in 3.89s\n"), sys.stdout.flush(), os._exit(0)))`, or set `session.exitstatus = 0` in `pytest_sessionfinish` and print a fake line. `os._exit(0)` in atexit overrides pytest's exit code; `uv run` propagates the child's code | A PR author (an agent under goal pressure or prompt injection, or a fork contributor) adds such code under `tests/` | A green check that does not reflect the suite. If `python-tests` becomes a required check, it must not be read as tamper-proof | No job-level fix exists. Record the limit in D-013 or the job comment. In a follow-up control task, add red-flag patterns `os\._exit\|atexit\|exitstatus\|pytest\.exit\(` | red-flags fixture: a diff adding any of these under `tests/` must produce a hit |
| F4 | Low | question (pre-existing, not introduced here) | `scripts/controls/test-controls.mjs:342`; `.github/workflows/control-gate.yml:17`; `.github/workflows/ci.yml:16,36` | The F1 regression test only forbids the string `check-locked-paths` in `ci.yml`. It does not forbid a PR-run job named `locked-paths`. Branch protection matches required checks by name. Both workflows report as GitHub Actions | A PR edits `ci.yml` (locked, so the real gate goes red) to add `locked-paths: … run: true` | Whether branch protection then counts the passing duplicate is UNKNOWN (GitHub behaviour not verified). The same structure applies to `python-tests` if it becomes required | The owner keeps `control-gate / locked-paths` required and checks the workflow name in the checks list when merging. Optionally have the base-revision verifier flag any non-gate workflow job whose id or `name:` is `locked-paths` (control task) | Verifier fixture: a PR adding a `locked-paths` job in `ci.yml` is reported even with the label |
| F5 | Low | question (latent; not exploitable with today's lock) | `.github/workflows/ci.yml:63,68`; `DECISIONS.md:154`; `uv.lock` | D-013 accepts GHSA-hq85-5cpj-mr62 as "impact = red job" because every uv download is hash-pinned. `uv.lock` has sha256 values for all 7 sdists and wheels (14 hashes), all wheels are `py3-none-any`, and the project is virtual (`package = false`), so nothing is built today. `uv.lock` contains no build-dependency entries | A future lock entry without a compatible wheel | uv would build the sdist and resolve its build requirements (e.g. setuptools) at sync time without lock hashes, over uv's affected CA store. A MITM holding the compromised intermediate could then run code in the job (read token, no secrets) | Add `--no-build` to `uv sync --locked` and `uv run --locked`. uv 0.13.0 help: "Don't build source distributions [env: UV_NO_BUILD=]". Add "any locked package without a compatible wheel" to D-013 "Review when" | Scratch: an sdist-only dependency makes `uv sync --locked --no-build` fail without fetching build deps; the current lock still syncs and the suite still shows `784 passed` |

### F1: abuse path, negative test, minimal fix
- **Abuse path (example a, xfail):**
  - A PR adds `tests/conftest.py` with `def pytest_runtest_setup(item): if item.nodeid.startswith("tests/acceptance/"): pytest.xfail("linux tz")`.
  - pytest exits 0 with a last line like `<n> passed, <m> xfailed in …`. The step passes, `control-gate` passes (no locked path), and red-flags shows no hit.
- **Abuse path (example b, deselect):** `pyproject.toml` `[tool.pytest.ini_options] addopts = "--deselect tests/acceptance/…"` gives `<n> passed, 1 deselected …`, which is green. red-flags only lists `pyproject.toml` under "Control files touched" (informational).
- **Abuse path (example c, silent exclusion):** `collect_ignore = ["acceptance", "architecture"]` in `tests/conftest.py` gives `<n> passed in …` with fewer tests. The summary cannot reveal this.
- **Minimal fix (OPS-001 scope, a new D-006 patch to `ci.yml`):** replace the two `[[ ]]` checks with:
  ```bash
  ok='^[0-9]+ passed(, [0-9]+ warnings?)? in [0-9]+\.[0-9]{2}s( \([0-9:]+\))?$'
  if [[ ! "$summary" =~ $ok ]]; then
    echo "::error::only '<n> passed [, <m> warnings] in <t>s' counts as green (AGENTS.md); got: $summary"
    exit 1
  fi
  ```
  The duration format comes from `format_session_duration`, `_pytest/terminal.py:1647-1653`. This rejects skipped, deselected, xfailed, xpassed, error, failed and `subtests …`, and fixes F2 as well. The current suite has no xfail, skip, deselect or subtests (grep of `tests/`: 0 hits). Its last line is `784 passed in 3.89s`, so the regex does not false-red it.
- **Example c (silent exclusion) needs a follow-up control task.** It is an owner decision outside OPS-001, because `scripts/controls/**` is excluded from this contract. Options:
  - add `conftest.py` (any depth), `pytest.ini`, `tox.ini` and `setup.cfg` to the red-flags "Control files touched" list
  - extend the red-flags skip pattern with `pytest\.xfail\(|collect_ignore|pytest_ignore_collect|pytest_collection_modifyitems|--deselect|--ignore|addopts`
  - or lock `tests/conftest.py`
  - a collected-count floor in `ci.yml` is also possible, but every legitimate test removal would then need a labelled change
- **Negative test (scratch project from the evidence procedure, same step text):**
  1. A conftest imperative xfail on a failing test must exit 1 (today 0).
  2. `addopts = "--deselect tests/test_case.py::test_b"` must exit 1 (today 0).
  3. A failing test marked `@pytest.mark.xfail` must exit 1 (today 0).
  4. A clean run must exit 0. A clean run plus one `warnings.warn` must exit 0.
  5. The AC-04 fail and skip cases must still exit 1.

## AC status (from this reviewer's evidence only)
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | UNKNOWN | No CI run yet. Locally on `b186329` + patch (Windows): `784 passed in 3.89s`, exit 0. CI checks out the PR merge ref, not the head commit |
| AC-02 | PASS (by reading) | Full 40-hex SHA for setup-uv and checkout; exact `version: "0.13.0"` and `python-version: "3.12.15"`; no `curl \| sh`, no `continue-on-error`, no `\|\| true`; no job-level `permissions:`, so workflow `contents: read` applies. That the pin is in the official repo was not re-verified (BLOCKED); it rests on admission evidence from 2026-10-22 |
| AC-03 | UNKNOWN | Not reproduced here. `docs/evidence/OPS-001.md` reports `--locked` exit 1 and `--frozen` exit 0. uv 0.13.0 help confirms the semantics |
| AC-04 | UNKNOWN | Not reproduced here. The evidence covers the two named cases (fail, skip). F1 shows failing tests reported as xfailed, deselected or not collected exit 0 |
| AC-05 | PASS | `test-controls.mjs` 105/105, skipped 0, including both F1 tests, on the patched tree. `control-gate.yml` diff vs `origin/main` is empty |
| AC-06 | PASS | D-013 committed at 09:56:32 +07 (`b186329`, reflog). `ci.yml` was modified at 09:56:38 +07 (file mtime), so admission preceded the apply |

## Threat mapping (OWASP Agentic ASI01–ASI10)
- **ASI01 goal hijack / ASI10 rogue agent:** an implementing agent weakens what runs so CI goes green (F1, F3).
- **ASI09 human-trust exploitation:** the owner reads a green `python-tests` or a duplicate check name as "suite passed" or "gate passed" (F1, F3, F4).
- **ASI04 supply chain:** setup-uv, uv, CPython and wheels (pins and hashes checked; F5 is latent).
- **ASI05 code execution:** PR code runs on the runner, bounded by a read token and PR-scoped cache (F3).
- **ASI03 identity/privilege:** token scope stays `contents: read` (pre-existing caveat below).
- **ASI07 inter-agent communication:** the handoff states an incorrect fail-closed property (F2).
- **ASI02, ASI06, ASI08:** no relevant surface in this diff.
- The OWASP LLM Top 10 does not apply: no AI component in this job.

## Checked, nothing found (and how)
- **Write access, secrets, expressions.**
  - Workflow `permissions: contents: read` (`ci.yml:12-13`). `python-tests` declares no `permissions:`.
  - No `secrets.` reference and no `${{ }}` in the new job. grep finds only `ci.yml:33`, which is pre-existing and passed via `env:`.
  - `persist-credentials: false` (`ci.yml:46`). No `pull_request_target` or `workflow_run` in `ci.yml`.
  - Pre-existing and unchanged: on same-repo branches a PR's own YAML can request wider `permissions:`. `control-gate` flags any `.github/` change (`rules.mjs:18`), but only at merge time.
- **Exit-code swallowing.**
  - No `continue-on-error`, `|| true`, `set +e` or negation around the pipeline.
  - `set -o pipefail` plus the default `bash -e` ends the step with pytest's or uv's code.
  - If `tail` fails, the assignment fails and `-e` stops the step. The `[[ ]]` checks sit correctly inside `if`.
- **tee and summary parsing.**
  - The stats line goes to stdout. It is printed last in `pytest_sessionfinish` (`terminal.py:957-994`).
  - `-q` gives the line without `=` separators (`display_sep = verbosity >= 0`, `:1260`). A second `-q` added through `addopts` suppresses the line (`:1253`), and `--color=yes` adds an ANSI prefix. Both fail closed.
  - A test's own `print` is captured by the default fd capture, so it cannot become the last line.
  - `pytest.exit(returncode=0)` sets exit 0 (`main.py:336-345`), but its banner prints after the summary in `pytest_unconfigure` (`terminal.py:1014-1023`), so the check fails closed.
  - `$summary` is one line inside an `::error::` message, so it cannot start a new workflow command.
  - A committed `pytest-output.txt` symlink can only redirect output, which makes the job red, not green.
- **`-p no:cacheprovider`.**
  - `--lf/--ff/--nf` are registered by the cache provider (`cacheprovider.py:472+`), so with it blocked they are unknown options and pytest exits with a usage error (exit 4).
  - `--sw` asserts `config.cache` (`stepwise.py:63,104`).
  - So a committed `.pytest_cache` plus `--lf` cannot select a subset.
  - It does not disable `conftest.py`, ini `addopts`, `PYTEST_ADDOPTS` or entry-point plugins.
- **Plugins and config today.**
  - The installed packages have no `pytest11` entry points (`entry_points.txt`: console scripts only).
  - The repo has no `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `uv.toml` or `.python-version`.
- **`uv sync --locked`.**
  - uv 0.13.0 help: `--locked` "Assert that the `uv.lock` will remain unchanged"; `--frozen` does not check. Both the sync and run steps use `--locked`.
  - Lock sources are all `https://pypi.org/simple` with sha256 hashes; the project is `virtual`.
  - It does not stop a PR that changes `pyproject.toml` and `uv.lock` together. red-flags lists both as control files (`red-flags.sh:64`), and admission is the process control.
- **Cache poisoning.**
  - `enable-cache: false` (`ci.yml:57`).
  - Independent of the action's code: GitHub limits cache writes from a `pull_request` run to the PR's merge ref, which the base branch never restores. Push-to-main runs merged code.
  - So no PR-to-main poisoning path goes through this job. The no-op post step was not verified (see Not checked).
- **Pins.**
  - setup-uv is pinned to `07a047e608db84b3d8c06cd9a7c7dcc9c355c18e` (40 hex) with a version comment.
  - The checkout pin is identical to `control-plane` and `control-gate`.
  - Python is installed explicitly with `uv python install 3.12.15`.
- **control-gate and F1 separation.**
  - `control-gate.yml` is unchanged.
  - `ci.yml` still has no `check-locked-paths`, and its header still says it is not the gate.
  - The job name `python-tests` does not collide with `locked-paths`. Both F1 tests pass.
- **Patch integrity.** Patch SHA256 `4e7e60f6…`, post-apply SHA256 `e136cae4…` and blob `d940df73…` all equal `docs/handoff/OPS-001.md`.
- **red-flags (`origin/main`).** Exit 0. All 3 groups are prose in `docs/handoff/OPS-001.md`. No secret-pattern hits.
- **Non-security notes:**
  - `ci.yml:51` says "seven small wheels"; six install on Linux (colorama is `win32`-only).
  - Commit `b92c9a0` has the message "หก", without `<type>(<scope>)` or `Refs: OPS-001` (AGENTS.md Git).
  - The evidence table gives the apply time as "09:55", but the file mtime is 09:56:38 +07.

## Not checked (and why)
- **setup-uv source at the pinned SHA: BLOCKED.** This covers whether `enable-cache: false` skips both restore and the post-step save, whether bundled `KNOWN_CHECKSUMS` take precedence over the manifest checksum, whether `github-token` is exported to later steps, and whether workspace config is read when `version` is set.
  - The read-only `curl` into a new scratch folder was refused: `Blocked by .claude/hooks/guard-bash.mjs: mkdir would change $D (a path that cannot be resolved here (variable or unknown directory)). The implementer may not change locked paths; ask the owner.`
  - Per CLAUDE.md it was not retried, reshaped, or replaced by another tool.
  - These items rest only on `docs/reviews/OPS-001-admission.md`, checks 4–6, from a prior session.
  - First-run log checks: `Successfully installed uv version 0.13.0`; a checksum-validation line; no "cache restored" or "cache saved" lines; post step does nothing.
- **Pin provenance and advisories after 2026-10-22: BLOCKED** (same block). This covers tag `v10.3.2` → SHA in `astral-sh/setup-uv`, rather than an impostor commit reachable through a fork, and OSV or GitHub advisories for setup-uv published since then.
- **Repository settings: no access, owner-only.** Branch protection or rulesets, required checks, default workflow permissions, fork-PR policy, repository visibility, Actions secrets.
- **GitHub's handling of duplicate check names in branch protection (F4):** not verified.
- **Execution of the negative tests for F1, F2 and F5:** not run. This role is limited to read-only inspection and existing test commands.
- **Linux runner behaviour (AC-01)** and the AC-03/AC-04 scratch runs: taken from `docs/evidence/OPS-001.md`, not reproduced.
- **Not audited:** uv internals (whether `--locked` contacts the index; `--no-build` with a virtual project), the uv binary, python-build-standalone, and setup-uv's bundled `dist/`.

## Checks run (2026-10-23 UTC; +07 = Asia/Bangkok)
| Command | Result | Commit | Time |
|---|---|---|---|
| `git status`; `git diff .github/workflows/ci.yml`; `git log --oneline -8` | ci.yml modified (additions only), evidence untracked | `b186329` + patch | before 03:06Z |
| `sha256sum` patch and ci.yml; `git hash-object` ci.yml | `4e7e60f6…`, `e136cae4…`, `d940df73…` = handoff | `b186329` + patch | before 03:06Z |
| `curl` setup-uv files @ `07a047e6` into scratch | BLOCKED (guard-bash message above) | – | before 03:06Z |
| `uv run --offline pytest tests -q -p no:cacheprovider` | PASS: `784 passed in 3.89s`, exit 0 | `b186329` + patch | 03:06:41–03:06:45Z |
| `node scripts/controls/test-controls.mjs` | PASS: 105 pass, 0 fail, 0 skipped, exit 0 (both F1 tests ✔) | `b186329` + patch | 03:06:50–03:10:30Z |
| `git diff origin/main -- .github/workflows/control-gate.yml` | empty | `b186329` + patch | ~03:11Z |
| `uv --version`; `uv sync --help`; `uv run --help` (grep) | uv 0.13.0 `4ecd0eff2`; `--locked`, `--frozen`, `--no-build` texts quoted above | – | ~03:14Z |
| `git log`/`git reflog`/`stat` for AC-06 ordering | commit 09:56:32 +07, ci.yml mtime 09:56:38 +07 | `b186329` | ~03:14Z |
| `bash scripts/controls/red-flags.sh origin/main` | exit 0; 3 groups, all prose in the handoff; control file: ci.yml | `b186329` + patch | 03:15:16Z |
| Read-only source reading: `.venv/Lib/site-packages/_pytest/{terminal,main,stepwise,cacheprovider}.py`, `config/__init__.py`, `*/entry_points.txt`; `rules.mjs`; `red-flags.sh`; `uv.lock` | as cited per item | – | 03:0x–03:16Z |
