# OPS-001 dependency admission: `astral-sh/setup-uv`, uv 0.13.0, CPython 3.12.15 in CI — proposed

Reviewer: Claude Code (fresh session) acting in the Codex dependency-admission role under the role swap
recorded in PROGRESS.md (PLAN-001, 2026-10-22 23:4x; Codex out of quota until 2026-10-28 19:41).
Date: 2026-10-22, 23:25–23:45 Asia/Bangkok (+07:00); query times below are UTC.
Snapshot: `413a968c7a0907e63bd26bb744168aceca791a4e`, branch `chore/OPS-001-python-ci`, clean working tree at start.
Contract: [OPS-001-python-ci.md](../contracts/OPS-001-python-ci.md), owner-approved 2026-10-22 23:4x: option (ก)
`astral-sh/setup-uv` pinned by full commit SHA with uv `0.13.0`, option (ข) uv-managed Python 3.12.15.
Procedure: [dependency-admission](../../.agents/skills/dependency-admission/SKILL.md), network read only.
Nothing was installed on this machine; no repository file other than this review, the proposal patch and the
handoff was written. The GitHub REST API was used without a token, one call per 90 s or slower.

## สรุปสำหรับเจ้าของ

เสนอ **ADMIT** ทั้งสามรายการสำหรับ job `python-tests` ใน `ci.yml` เท่านั้น:

1. GitHub Action `astral-sh/setup-uv` ตรึงที่ commit `07a047e608db84b3d8c06cd9a7c7dcc9c355c18e` (release `v10.3.2`,
   2026-10-22, release ล่าสุดและไม่ใช่ prerelease) · repository ทางการของ Astral (องค์กรเดียวกับ uv) · MIT · ไม่พบ security
   advisory ทั้งจาก GitHub และ OSV · ออก release ประมาณ 2–3 ครั้งต่อเดือน
2. uv `0.13.0` (ตรงกับเครื่องเจ้าของ `uv 0.13.0 (4ecd0eff2 2026-10-09)`) · ดาวน์โหลดจาก release ทางการของ `astral-sh/uv`
   ผ่าน mirror ของ Astral แล้วตรวจ SHA-256 ด้วยตารางที่ฝังใน action (ค่า `1468ebd5…` ตรงกับไฟล์ `.sha256` ของ release)
3. CPython `3.12.15` build `20261009` จาก `astral-sh/python-build-standalone` (build ชุดเดียวกับที่ติดตั้งบนเครื่องเจ้าของ)
   ตรวจ SHA-256 ด้วย metadata ที่ฝังใน uv 0.13.0

**ข้อที่เจ้าของต้องรับทราบก่อนอนุมัติ:** uv 0.13.0 มี advisory เปิดอยู่ 1 รายการ
[GHSA-hq85-5cpj-mr62](https://osv.dev/vulnerability/GHSA-hq85-5cpj-mr62) (= PYSEC-2026-4321, เผยแพร่ 2026-10-20, แก้ใน
uv 0.13.4): CA bundle ที่ฝังใน uv ยังเชื่อ root `emSign ECC Root CA - G3` ซึ่งมี intermediate CA ที่กุญแจรั่ว ผู้โจมตีที่ถือกุญแจนั้นอาจ
ปลอม TLS ต่อ uv ได้ ใน job นี้ผลกระทบจำกัดอยู่ที่ "ดาวน์โหลดล้ม → job แดง" เพราะทุกสิ่งที่ uv ดาวน์โหลดถูกตรวจ hash ที่ตรึงไว้แล้ว
(wheels ตาม `uv.lock`, Python ตาม metadata ในตัว uv) ไม่ใช่การรันโค้ดที่ไม่ได้ตรวจ และ uv ตัวเดียวกันบนเครื่องเจ้าของก็มี exposure
เดียวกันอยู่แล้ว ข้อเสนอคือ **คง 0.13.0 ตามที่เจ้าของเลือกเพื่อให้ CI เท่ากับเครื่อง** และเปิดงานติดตามแยก: ยก uv เป็น ≥ 0.13.4
(ล่าสุด 0.13.5, 2026-10-22) **พร้อมกันทั้งเครื่องและ CI** หลังตรวจว่า `uv lock --check`/`--locked` ยังไม่เปลี่ยน lockfile ด้วย uv
รุ่นใหม่ ถ้าเจ้าของต้องการ 0.13.5 ใน CI ตั้งแต่ตอนนี้ แก้ค่า `version:` ใน patch ได้บรรทัดเดียว แต่ CI จะไม่เท่ากับเครื่อง

ไม่ได้ทำในรอบนี้ (ดู Blocks): หลักฐาน AC-03/AC-04 ใน scratch project ถูก permission system ปฏิเสธ จึงเป็น BLOCKED และส่งขั้นตอน
ให้ผู้ทำรันแทนใน `docs/handoff/OPS-001.md`

## Decision proposals

| Item | Exact pin | Proposal | Reason (checks 1–6 below) |
|---|---|---|---|
| GitHub Action `astral-sh/setup-uv` | `astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e # v10.3.2` with `version: "0.13.0"`, `python-version: "3.12.15"`, `enable-cache: false` | **ADMIT** | official Astral org repo, MIT, latest stable release, no advisories, downloads one archive from Astral's own release mirror with a bundled SHA-256 check, node24 runtime, no secrets, token stays `contents: read` |
| uv `0.13.0` (Linux x86_64 archive) | `uv-x86_64-unknown-linux-gnu.tar.gz`, SHA-256 `1468ebd5a5541121837c5a2817b9972ba6090fa6caa3d142620850a47fb75154` | **ADMIT**, owner must accept the open advisory explicitly | same binary family as the dev machine; GHSA-hq85-5cpj-mr62 open (fixed 0.13.4), impact in this job limited to availability because every uv download is hash-pinned; follow-up upgrade recommended for both machine and CI together |
| CPython `3.12.15` build `20261009` | `cpython-3.12.15+20261009-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz`, SHA-256 `ffa8f85f1b56e88b687f08d743d817015524b86a9365fd921243132b80f1a36d` | **ADMIT** | same python-build-standalone release as the interpreter installed locally; hash embedded in uv 0.13.0 |

These proposals cover the `python-tests` job of `.github/workflows/ci.yml` only. They do not admit any Python package
(the seven pins of D-012 are unchanged), a Windows runner, caching, or any other workflow.

## Check 1: exact identity

- Repository `https://github.com/astral-sh/setup-uv`, owner `astral-sh` (type Organization), created 2024-08-23,
  default branch `main`, not a fork, not archived. Spelling matches the uv documentation and the action's own
  `action.yml` (`name: "astral-sh/setup-uv"`, `author: "astral-sh"`). GitHub API `GET /repos/astral-sh/setup-uv`
  at 16:25:28Z.
- Latest release: `v10.3.2`, published 2026-10-22T08:47:11Z, `prerelease: false`, `draft: false`,
  `target_commitish: 07a047e608db84b3d8c06cd9a7c7dcc9c355c18e`, author `github-actions[bot]`, title
  "update known checksums for 0.13.5". GitHub API `GET /repos/astral-sh/setup-uv/releases/latest` at 16:28:34Z.
- Tag dereference: `git ls-remote --tags https://github.com/astral-sh/setup-uv` at 16:25:26Z lists
  `07a047e608db84b3d8c06cd9a7c7dcc9c355c18e refs/tags/v10.3.2` with no peeled `^{}` entry, so `v10.3.2` is a
  lightweight tag pointing directly at that commit (identical to the release's target commit). The moving major
  tags `v1`..`v7` are annotated tags; there is no moving `v8`, `v9` or `v10` tag (the project moved to
  "immutable releases and secure tags" in v8.0.0). The full SHA pin is therefore the only stable reference.
- uv `0.13.0`: PyPI `GET https://pypi.org/pypi/uv/0.13.0/json` at 16:25:30Z: version 0.13.0, author
  "Astral Software Inc.", `license_expression: MIT OR Apache-2.0`, not yanked, released 2026-10-09T19:45Z,
  repository `https://github.com/astral-sh/uv`. Git tag `0.13.0` = `4ecd0eff2a81e3ffdcd7cfee10d08936e4747c17`
  (`git ls-remote --tags https://github.com/astral-sh/uv` at 16:31:34Z), which matches the dev machine:
  `uv 0.13.0 (4ecd0eff2 2026-10-09 x86_64-pc-windows-msvc)`.
- CPython 3.12.15: `uv python list --all-platforms --all-versions --only-downloads --show-urls` (uv 0.13.0, local,
  no network) lists `cpython-3.12.15-linux-x86_64-gnu` at
  `https://releases.astral.sh/github/python-build-standalone/releases/download/20261009/cpython-3.12.15%2B20261009-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz`
  and the Windows build from the same `20261009` release, which is the interpreter installed locally
  (`cpython-3.12.15-windows-x86_64-none` under `%APPDATA%\uv\python`). Tag `20261009` exists in
  `astral-sh/python-build-standalone` (`ccc07c40c2731bfb459c119f2388f65a5a470de6`, `git ls-remote` at 16:31:34Z).

## Check 2: publisher and maintenance

- Publisher: the Astral organization (vendor of uv). The README acknowledges the action was written by Kevin
  Stillhammer (`eifinger`) before moving under the official Astral organization; `package.json` still lists
  `"author": "@eifinger"`. Releases are cut by `github-actions[bot]` (release automation).
- Activity: `pushed_at` 2026-10-22T10:53:28Z; 892 stars, 118 forks, 20 open issues (API, 16:25:28Z).
- Cadence (`GET /repos/astral-sh/setup-uv/releases?per_page=40` at 16:31:36Z): 40 releases between
  2025-06-19 (v6.3.0) and 2026-10-22 (v10.3.2), about 2.5 per month. Majors: v7.0.0 2025-10-07 (node24),
  v8.0.0 2026-03-29 (immutable releases), v9.0.0 2026-07-21 (`prune-cache` default), v10.0.0 2026-08-12
  (automatic cache disabled for sensitive events). Patch releases often only add known checksums for new uv
  versions (v10.3.2 added 0.13.5).
- uv itself released 0.13.1 through 0.13.5 between 2026-10-14 and 2026-10-22 (PyPI release list, 16:28:10Z).

## Check 3: license

- `LICENSE` at the pinned commit: "The MIT License (MIT), Copyright (c) 2024 Kevin Stillhammer"; GitHub reports
  `spdx: MIT`; README "License: MIT". Private use in CI is compatible; nothing is redistributed.
- uv: `MIT OR Apache-2.0` (PyPI). python-build-standalone: builds carry the PSF license of CPython plus the
  project's own MIT/BSD-style licensing (not re-read in this session; the same builds already run locally under
  D-001/D-012).

## Check 4: security

- Advisories for the action: GitHub `GET /repos/astral-sh/setup-uv/security-advisories` at 16:33:18Z returned
  an empty list; OSV `POST /v1/query` (`{"package":{"name":"astral-sh/setup-uv","ecosystem":"GitHub Actions"}}`)
  at 16:28:10Z returned `{}`. No indexed advisory. Absence is not proof of absence.
- Advisory for uv 0.13.0: OSV (`{"package":{"name":"uv","ecosystem":"PyPI"},"version":"0.13.0"}`, 16:28:10Z)
  and PyPI both return **GHSA-hq85-5cpj-mr62 / PYSEC-2026-4321** (published 2026-10-20T19:37Z, modified
  22:11Z): "uv's bundled CA store trusts an emSign root whose intermediate CA keys are compromised", fixed in
  0.13.4. Impact analysis for this job: uv's own TLS bundle is used for (a) the Python build download and
  (b) the wheel downloads; both are verified against pinned SHA-256 values (uv 0.13.0's embedded metadata for
  Python, `uv.lock` for wheels), so a forged server can only make the download fail (availability), not inject
  unverified code. Index metadata fetched by uv is not code. The uv binary itself is downloaded by the action
  with Node's TLS stack (not affected) and checked against the bundled checksum. The same uv 0.13.0 on the dev
  machine carries the same exposure today. Recommended follow-up: a separate decision that upgrades uv to
  ≥ 0.13.4 on the machine and in CI together, after confirming the newer uv leaves `uv.lock` unchanged under
  `--locked`.
- What the action downloads at run time (source read at the pinned commit: `src/download/download-version.ts`,
  `src/download/checksum/checksum.ts`, `src/utils/constants.ts`, `src/setup-uv.ts`):
  1. The version manifest `https://raw.githubusercontent.com/astral-sh/versions/main/v1/uv.ndjson`
     (`VERSIONS_MANIFEST_URL`) to resolve the artifact for the requested version.
  2. The uv archive from the Astral mirror `https://releases.astral.sh/github/uv/releases/download/0.13.0/uv-x86_64-unknown-linux-gnu.tar.gz`
     (`download-from-astral-mirror` defaults to true), falling back to
     `https://github.com/astral-sh/uv/releases/download/0.13.0/…` if the mirror fails.
  3. Checksum: `validateChecksum` uses, in order, the `checksum` input, the bundled `KNOWN_CHECKSUMS` table, then
     the manifest checksum; a mismatch throws and the step fails. Bundled entry
     `"x86_64-unknown-linux-gnu-0.13.0": "1468ebd5a5541121837c5a2817b9972ba6090fa6caa3d142620850a47fb75154"`
     (`src/download/checksum/known-checksums.json` at the pinned commit) equals the release's own
     `uv-x86_64-unknown-linux-gnu.tar.gz.sha256` fetched from GitHub at 16:31:27Z.
  4. The `github-token` input (default `${{ github.token }}`, `contents: read` here) is attached only to
     requests whose origin is `https://github.com` (`githubTokenForUrl`), never to the mirror.
  5. With `enable-cache: false` the action neither restores nor saves the GitHub Actions cache. The post step
     (`dist/save-cache/index.cjs`, `post-if: success()`) is expected to be a no-op; confirm in the first run log.
- Runtime: `runs.using: "node24"`, `main: dist/setup/index.cjs`. The bundled `dist/` is committed; nothing is
  installed with npm at run time. Declared runtime npm dependencies (bundled): `@actions/cache`, `@actions/core`,
  `@actions/exec`, `@actions/glob`, `@actions/io`, `@actions/tool-cache`, `@renovatebot/pep440`, `smol-toml`,
  `undici`. The bundled `dist/` contents were not audited line by line.
- Python download: `uv python install 3.12.15` fetches the build from the Astral mirror of
  `astral-sh/python-build-standalone` (URL above) and verifies it against the SHA-256 embedded in uv 0.13.0
  (`crates/uv-python-managed/download-metadata.json` at tag `0.13.0`, key `cpython-3.12.15-linux-x86_64-gnu`,
  `sha256: ffa8f85f1b56e88b687f08d743d817015524b86a9365fd921243132b80f1a36d`; the GitHub form of the same URL).
  uv also carries `x86_64_v2`…`v4` variants of the same version; the baseline `x86_64` build is selected unless a
  variant is requested.
- Package downloads: `uv sync --locked` installs from the URLs and SHA-256 hashes in `uv.lock` (D-012). On Linux
  six wheels are installed (`colorama` has the marker `sys_platform == 'win32'`): pytest, iniconfig, packaging,
  pluggy, pygments, tzdata.
- Permissions and secrets: workflow `permissions: contents: read` is unchanged; the job adds no secret, no write
  permission, no `curl | sh`, no `continue-on-error`, no `|| true`.

## Check 5: fit

- Target: `ubuntu-24.04` GitHub-hosted runner, x86_64. The action supports node24 runners; `actions/checkout`
  `v7.0.1` already pinned in `ci.yml` runs on the same runtime.
- Inputs needed (action.yml at the pinned commit): `version: "0.13.0"` (exact version; the action otherwise
  reads `required-version` from `uv.toml`/`pyproject.toml` or installs latest), `python-version: "3.12.15"`.
  **`python-version` only exports `UV_PYTHON=3.12.15`** (`setupPython` in `src/setup-uv.ts`); it does not install
  Python. Therefore the job runs an explicit `uv python install 3.12.15` step (exact patch release; `TARGETS`
  honours `UV_PYTHON` too). Without that step `uv sync` would still auto-download the same build
  (`UV_PYTHON_DOWNLOADS` defaults to automatic), but the explicit step makes the download and its result visible
  as its own log section and fails early if the build is missing.
- `enable-cache: false`: the default `auto` would restore and save a GitHub Actions cache keyed on `uv.lock`.
  Six small wheels plus a 30 MB interpreter do not justify the extra moving part for a first job; the owner can
  enable it later in a separate change.
- Lock check: uv 0.13.0 `uv sync --help` and `uv run --help`: `--locked` = "Assert that the `uv.lock` will
  remain unchanged" (fails when the lock does not match `pyproject.toml`); `--frozen` = "Sync/Run without
  updating the `uv.lock` file" (uses the lock as-is, no check). The contract's AC-03 requires failure on a
  mismatch, so the job uses `--locked` on both `uv sync` and `uv run`. (The action's README examples use
  `--frozen`; that is the weaker choice for this contract.)
- Need vs. alternatives: option (2) `pipx install uv==0.13.0` and option (3) `pip install --require-hashes`
  would avoid a new action but either skip hash verification or add steps; the chosen action is published by
  uv's vendor and verifies the archive checksum. No existing project dependency covers installing uv on a runner.
- Python version compatibility: `requires-python = ">=3.12,<3.13"` and `uv.lock` `requires-python = "==3.12.*"`
  accept 3.12.15; it is the interpreter already used for every local test run.

## Check 6: instruction and script files

The action ships no instructions for agents. Files read at the pinned commit: `action.yml`, `README.md`,
`LICENSE`, `package.json`, `src/setup-uv.ts` (first 185 lines plus the Python/env functions),
`src/download/download-version.ts`, `src/download/checksum/checksum.ts`,
`src/download/checksum/known-checksums.json` (0.13.x entries), `src/utils/constants.ts`. Network destinations and
permissions are listed in check 4. Nothing conflicts with AGENTS.md. Not read: `dist/`, the cache modules,
`src/download/manifest.ts`, `src/version/*`.

## Blocks encountered (reported, not routed around)

1. **Permission system (non-interactive session), AC-03/AC-04 scratch evidence — BLOCKED.** The command
   `cd "<scratchpad>/synthetic" && mkdir -p tests && cp "<scratchpad>/variants/test_clean.py" tests/test_case.py && date -u +%H:%M:%SZ && uv lock --offline; echo "lock-exit=$?"; date -u +%H:%M:%SZ; ls`
   was declined with: `This Bash command contains multiple operations. The following parts require approval:
   mkdir -p tests, cp "<scratchpad>/variants/test_clean.py" tests/test_case.py, uv lock --offline,
   echo "lock-exit=$?", ls`. Per CLAUDE.md and the owner's N6 rule the step was stopped, not reshaped. The
   synthetic project files and the exact step script exist in the scratchpad and the procedure is written out in
   `docs/handoff/OPS-001.md` for the implementer (or owner) to run.
2. **guard-bash, a verification command — BLOCKED.** A `node -e` check that compared the `control-plane` job
   bytes of the repository's `ci.yml` with the scratch copy (and would have counted CR bytes and compared the
   test step with the step script) was blocked: `Blocked by .claude/hooks/guard-bash.mjs: inline node code
   references a locked path (.github/). Use the Read tool to read files; locked paths are owner-only.` Not
   redone. This is the `node -e` false-positive class already in the FIX-002 backlog. The same facts follow from
   the patch itself: it contains only added lines, so the existing job and the LF endings are unchanged.

## D-013 ติดตั้ง uv และ Python ใน CI ด้วย `astral-sh/setup-uv` ตรึง SHA, uv 0.13.0, CPython 3.12.15 (OPS-001) — 2026-10-22 — proposed

ข้อความร่างสำหรับ DECISIONS.md; ยังไม่ได้แก้ไฟล์นั้น ผู้ทำเพิ่มหลังเจ้าของอนุมัติ admission นี้

Context: OPS-001 (High, Q6) เพิ่ม job `python-tests` ใน `.github/workflows/ci.yml` ให้ CI รัน pytest บน Linux ทุก PR · ต้องติดตั้ง uv และ
Python บน runner ซึ่งเป็น dependency ใหม่ของ CI (ไม่ใช่ของโปรเจกต์ Python; D-012 ไม่เปลี่ยน) · ผล admission อยู่ใน
`docs/reviews/OPS-001-admission.md` (ตรวจ GitHub/PyPI/OSV 2026-10-22 16:25–16:39 UTC)
Decision: ADMIT สำหรับ job `python-tests` เท่านั้น
- action `astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e` (release `v10.3.2`, 2026-10-22) ด้วย input `version: "0.13.0"`,
  `python-version: "3.12.15"`, `enable-cache: false`
- uv `0.13.0` (archive Linux x86_64 SHA-256 `1468ebd5a5541121837c5a2817b9972ba6090fa6caa3d142620850a47fb75154` ตรวจโดย action)
- CPython `3.12.15` build `20261009` จาก `astral-sh/python-build-standalone` (SHA-256
  `ffa8f85f1b56e88b687f08d743d817015524b86a9365fd921243132b80f1a36d` ตรวจโดย uv) ติดตั้งด้วย `uv python install 3.12.15`
- คำสั่งใน job: `uv sync --locked` และ `uv run --locked pytest tests -q -p no:cacheprovider` (`--locked` ล้มเมื่อ lock ไม่ตรง pyproject;
  `--frozen` ไม่ตรวจ) · job แดงเมื่อ test ล้ม, error หรือถูก skip
Why: ผู้ผลิตเดียวกับ uv, MIT, ไม่มี advisory ของ action, ดาวน์โหลดจาก release ทางการผ่าน mirror ของ Astral พร้อมตรวจ SHA-256, token คง
`contents: read`, ไม่มี secret · uv และ Python รุ่นเดียวกับเครื่องเจ้าของจึงเทียบผล test ได้ตรง
Conditions:
- **ความเสี่ยงที่รับไว้ชั่วคราว:** uv 0.13.0 มี advisory GHSA-hq85-5cpj-mr62 (CA root ที่ intermediate รั่ว, แก้ใน 0.13.4) · ใน job นี้
  ทุกการดาวน์โหลดของ uv ตรวจ hash ที่ตรึงไว้ ผลกระทบจึงจำกัดที่ job แดง · เครื่องเจ้าของมี exposure เดียวกัน
- งานติดตาม: ยก uv เป็น ≥ 0.13.4 ทั้งเครื่องและ CI ในการตัดสินเดียว หลังตรวจว่า `uv.lock` ไม่เปลี่ยนภายใต้ `--locked` ด้วย uv รุ่นใหม่
- เปลี่ยน SHA ของ action, รุ่น uv, รุ่น Python หรือเปิด cache ต้องผ่าน admission และบันทึกที่นี่ · `control-gate.yml` ไม่เปลี่ยน
- ลงทะเบียนใน `docs/tooling/registry.md` (แถวด้านล่าง) และปรับแถว uv เดิมให้บอกว่าใช้ใน CI แล้ว
Review when: advisory ใหม่ของ uv/action, release ใหม่ของ action ที่แก้ความปลอดภัย, เปลี่ยน Python 3.12.x บนเครื่อง, หรือเพิ่ม Windows runner

## Draft row for `docs/tooling/registry.md` (table "Active: runtimes and agents")

| Tool | Version | Config / scope | Permissions and data sent | Last verified |
|---|---|---|---|---|
| GitHub Action `astral-sh/setup-uv` (D-013) | `07a047e608db84b3d8c06cd9a7c7dcc9c355c18e` (`v10.3.2`, 2026-10-22) · uv `0.13.0` · CPython `3.12.15` (python-build-standalone `20261009`) | `ci.yml` job `python-tests` เท่านั้น: `version: "0.13.0"`, `python-version: "3.12.15"` (ตั้ง `UV_PYTHON`), `enable-cache: false` · ตามด้วย `uv python install 3.12.15`, `uv sync --locked`, `uv run --locked pytest …` | ดาวน์โหลด manifest จาก raw.githubusercontent.com (astral-sh/versions) และ uv จาก releases.astral.sh (fallback github.com) ตรวจ SHA-256 จากตารางใน action · uv ดาวน์โหลด Python จาก releases.astral.sh และ wheels จาก files.pythonhosted.org ตรวจ hash จาก metadata/`uv.lock` · `github.token` (`contents: read`) ส่งเฉพาะ github.com · ไม่มี secret · advisory เปิดของ uv 0.13.0: GHSA-hq85-5cpj-mr62 (รับไว้ชั่วคราว, ดู D-013) | admission 2026-10-22 (`docs/reviews/OPS-001-admission.md`) · CI run แรก: UNKNOWN จนกว่า PR ของ OPS-001 จะรัน |

Also change the existing `uv` row's scope text ("ยังไม่ใช้จนกว่า D-001 จะ accepted") to say that uv 0.13.0 is the project
tool since D-012 and the CI tool since D-013.

## Checks run

All times 2026-10-22 UTC (+07:00 = Asia/Bangkok). Commit `413a968` throughout; nothing was committed.

| Command / procedure | Result | Commit | Time (UTC) |
|---|---|---|---|
| `git status --short`; `git log --oneline -3`; `uv --version`; `node --version`; `git --version` | PASS: clean tree, `chore/OPS-001-python-ci`, uv 0.13.0 (4ecd0eff2), node v26.12.0, git 2.46.1 | 413a968 | 16:25 |
| `git ls-remote --tags https://github.com/astral-sh/setup-uv` → scratch file | PASS: `v10.3.2` → `07a047e6…`, lightweight; moving tags only `v1`..`v7` | 413a968 | 16:25:26 |
| `curl -s -o <scratch> https://api.github.com/repos/astral-sh/setup-uv` + `node` parse | PASS: org `astral-sh`, MIT, created 2024-08-23, pushed 2026-10-22 | 413a968 | 16:25:28 |
| `curl -s -o <scratch> https://pypi.org/pypi/uv/0.13.0/json` + `node` parse | PASS: not yanked, MIT OR Apache-2.0, advisory GHSA-hq85-5cpj-mr62 listed | 413a968 | 16:25:30 |
| `uv sync --help`, `uv run --help`, `uv python list --help`, `uv python install --help` → scratch files | PASS: `--locked` asserts the lock unchanged; `--frozen` skips the check | 413a968 | 16:25–16:34 |
| `curl -s -o <scratch>` raw `action.yml`, `README.md`, `package.json`, `LICENSE`, `src/…` at `07a047e6` | PASS: inputs, node24, MIT, download and checksum flow as described | 413a968 | 16:28:03–16:32:13 |
| OSV `POST /v1/query` for `astral-sh/setup-uv` (GitHub Actions) and `uv` 0.13.0 (PyPI) → scratch files | PASS: `{}` for the action; GHSA-hq85-5cpj-mr62 / PYSEC-2026-4321 for uv 0.13.0 | 413a968 | 16:28:10 |
| `curl -s -o <scratch> https://pypi.org/pypi/uv/json` | PASS: latest 0.13.5 (2026-10-22); 0.13.4 (fix) 2026-10-20 | 413a968 | 16:28:10 |
| `uv python list --all-platforms --all-versions --only-downloads --show-urls` → scratch | PASS: 3.12.15 Linux/Windows builds from release `20261009` | 413a968 | 16:28 |
| `curl -s -o <scratch> https://api.github.com/repos/astral-sh/setup-uv/releases/latest` | PASS: `v10.3.2`, not prerelease, target `07a047e6…` | 413a968 | 16:28:34 |
| `curl -s -L -o <scratch>` `uv-x86_64-unknown-linux-gnu.tar.gz.sha256` (release 0.13.0) | PASS: `1468ebd5…` = bundled `KNOWN_CHECKSUMS` entry | 413a968 | 16:31:27 |
| `git ls-remote --tags` for `astral-sh/uv` and `astral-sh/python-build-standalone` | PASS: tag `0.13.0` = `4ecd0eff2…`; tag `20261009` exists | 413a968 | 16:31:34 |
| `curl -s -o <scratch> https://api.github.com/repos/astral-sh/setup-uv/releases?per_page=40` | PASS: cadence above | 413a968 | 16:31:36 |
| `curl -s -o <scratch> https://api.github.com/repos/astral-sh/setup-uv/security-advisories` | PASS: empty list | 413a968 | 16:33:18 |
| `curl -s -o <scratch>` `crates/uv-python/download-metadata.json` at tag 0.13.0; API `contents` listings | FAIL (404, path moved) → found `crates/uv-python-managed/`; metadata fetched 16:38:57 | 413a968 | 16:31:29–16:38:57 |
| `node` parse of uv 0.13.0 `download-metadata.json` | PASS: `cpython-3.12.15-linux-x86_64-gnu` sha256 `ffa8f85f…` | 413a968 | 16:39 |
| synthetic project (`uv lock --offline`, sync, test step) | BLOCKED: permission decline quoted above | 413a968 | 16:28 |
| `node -e` byte comparison of the control-plane job against the scratch copy | BLOCKED: guard-bash message quoted above | 413a968 | 16:34 |

Not tested: the action's bundled `dist/` code; the cache modules (cache disabled); behaviour on the runner
(first CI run is the evidence for AC-01); python-build-standalone licensing files; whether `uv sync --locked`
contacts the package index at all when the lock is complete.

Handoff: the owner accepts or rejects this admission; on ADMIT the implementer adds D-013 to DECISIONS.md and the
registry row, then applies `docs/proposals/OPS-001-ci.patch` under D-006 as described in `docs/handoff/OPS-001.md`.
