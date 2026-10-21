# CORE-001 project dependency admission — proposed

Reviewer: Codex, dependency-admission role. Date: 2026-10-21, Asia/Bangkok.
Snapshot: `ee33524d55bceb227a11b48619804a848c1aa33f`, branch `feat/CORE-001-timebase`; initially clean working tree.
Target: Windows x64, CPython 3.12; proposed `requires-python = ">=3.12,<3.13"`; no extras.
Procedure: [dependency-admission](../../.agents/skills/dependency-admission/SKILL.md).
Contract: [CORE-001-timebase.md](../contracts/CORE-001-timebase.md), owner-approved v1.

## สรุปสำหรับเจ้าของ

เสนอ **ADMIT ระดับโปรเจกต์ทั้ง 7 pins** ในตารางด้านล่าง: runtime มี `tzdata` ตัวเดียว ส่วน `pytest` และ transitives 5 ตัวอยู่ใน dev/test เท่านั้น ผลนี้เป็น **ข้อเสนอให้เจ้าของตัดสิน D-012** ไม่ใช่การอนุมัติหรือติดตั้ง การอนุมัติ D-010/D-011 เดิมครอบคลุมเฉพาะ SPIKE-001 จึงใช้แทนการอนุมัติ project dependencies และ lockfile แรกไม่ได้

ตรวจ PyPI/OSV ใหม่เวลา **08:02–08:03 +07**: ทั้ง 7 pins ยังเป็น latest ที่ PyPI รายงาน มี universal wheel รองรับ Python 3.12 / Windows x64, ไม่ถูก yank และ hash ตรงหลักฐานเดิม ไม่พบ advisory ที่ตรงกับแต่ละ pin ใน OSV ไม่พบ release artifact ใหม่หรือ advisory ที่มีวัน published/modified หลัง **2026-10-21 02:45 +07** ในผลที่ได้รับ การไม่พบไม่ใช่หลักฐานว่าไม่มีช่องโหว่ที่ยังไม่ถูกเปิดเผย

`hypothesis` **ยังไม่จำเป็นต่อ acceptance ของ CORE-001**: AC-01 ใช้ pytest กับ stdlib สุ่มค่าและตรวจ round-trip ได้ หาก test author เลือกใช้ Hypothesis ตาม skill trial ต้องทำ admission และขออนุมัติแยก ข้อมูลปัจจุบันคือ `hypothesis==6.170.5` และ dependency `sortedcontainers==2.4.0`; OSV ไม่พบ advisory ที่ตรงกับสอง pins นี้ แต่ **ไม่รวมในข้อเสนอ D-012**

ข้อจำกัดที่เปิดเผย: หน้า HTML ของ colorama/Pygments ติด Client Challenge จึงใช้ publisher evidence เดิมร่วมกับ JSON ใหม่; locked-path check **FAIL** เพราะประวัติ branch เทียบ local `main` มี AGENTS.md ที่เปลี่ยนอยู่ก่อนเริ่มงาน รายงานนี้ไม่ได้แก้ไฟล์นั้น และไม่ได้แก้ config/label เพื่อให้ check ผ่าน

## Per-package decision proposals

| Package / exact pin and current PyPI evidence | Scope | Proposal | Reason |
|---|---|---|---|
| [tzdata==2026.5](https://pypi.org/pypi/tzdata/2026.5/json) | Runtime | **ADMIT** | Supplies IANA data to stdlib `zoneinfo` on Windows; required by contract; zero declared runtime dependencies |
| [pytest==9.1.1](https://pypi.org/pypi/pytest/9.1.1/json) | Dev/test direct | **ADMIT** | Contract-prescribed test runner; Python 3.12 compatible; current pin is outside indexed affected ranges |
| [colorama==0.4.6](https://pypi.org/pypi/colorama/0.4.6/json) | Dev/test transitive | **ADMIT** | pytest requires it on Windows; compatible universal wheel; mature but old release, console behavior still untested here |
| [iniconfig==2.3.1](https://pypi.org/pypi/iniconfig/2.3.1/json) | Dev/test transitive | **ADMIT** | Satisfies pytest INI parser requirement; zero further dependencies |
| [packaging==26.3](https://pypi.org/pypi/packaging/26.3/json) | Dev/test transitive | **ADMIT** | Satisfies pytest version/requirement parsing requirement; zero further dependencies |
| [pluggy==1.7.0](https://pypi.org/pypi/pluggy/1.7.0/json) | Dev/test transitive | **ADMIT** | Satisfies pytest hook framework bound `>=1.5,<2`; zero further dependencies |
| [Pygments==2.21.0](https://pypi.org/pypi/Pygments/2.21.0/json) | Dev/test transitive | **ADMIT** | Required syntax highlighting; current pin is outside indexed affected ranges; zero default dependencies |

These proposals cover this exact project dependency set, not unrestricted future versions, extras, build backends, broker access or strategy experiments. No package in this seven-package set requires a separate native-ABI spike on the metadata evidence available; installed behavior remains unverified.

## Evidence method and reuse

Reused [SPIKE-001 admission](SPIKE-001-dependency-admission.md) for prior identity/vendor cross-links, historical license evidence, purpose and runtime-surface descriptions. Rechecked all seven latest and exact PyPI JSON endpoints, artifact names/hashes/sizes/yanked flags, Python/dependency markers, current release history and OSV exact/package-wide queries. The previous review's spike-only admission is not carried forward as authority.

Cutoff: `2026-10-20T19:45:00.000Z` = `2026-10-21 02:45:00 +07`. Latest JSON endpoints are `https://pypi.org/pypi/<name>/json`; exact endpoints are linked in the decision table. Successful registry queries completed `2026-10-21T01:02:57.589Z`–`01:02:57.821Z`; a second comparison against the old report completed `01:03:50.405Z`–`01:03:50.425Z`: all seven filenames/hashes matched and all seven wheels remained non-yanked.

Used existing Node.js `v26.12.0`, built-in `fetch`, JSON parsing and text inspection. GET requests were limited to `pypi.org`; read-only advisory POST queries to `api.osv.dev` (OSV's API host). Redirects were disabled and requests time-limited. No artifact download, package execution, installation, `uv` resolution, environment mutation or TLS setting change occurred. External content was used as evidence, not instructions.

Repository search (`git ls-files 'src/*' 'pyproject.toml' 'uv.lock' '*requirements*'`) returned no tracked implementation or dependency files. The existing spike is a throwaway prototype, not a reusable project dependency environment. Stdlib `datetime`, `zoneinfo`, `random` and AST support cover the remaining CORE-001 needs without new libraries. The approved contract, SPEC J2/J3 and architecture's `timebase` boundary require named-zone conversion through one module.

## Identity, maintenance, licensing and runtime surface

The exact project identities match the official project links recorded in the earlier review and the current JSON. `Pygments` is its display spelling; normalized `pygments` is used for OSV. Current PyPI publisher pages succeeded for the first five projects listed below; the last two publisher refreshes were blocked as recorded later. No new third-party skill/plugin/MCP is admitted, so no tooling-registry draft is needed.

| Project | Publisher evidence | Latest wheel upload UTC; preceding release | Declared license |
|---|---|---|---|
| tzdata | Python Software Foundation; PyPI `belopolsky`, `pganssle`, `stanfromireland` | 2026-10-03; 2026.4 on 2026-09-12 | Apache-2.0; upstream timezone-data notices also apply |
| pytest | pytest-dev; PyPI `anatoly`, `flub`, `hpk`, `nicoddemus`, `pfctdayelise`, `ronny`, `The_Compiler` | 2026-06-19; 9.1.0 on 2026-06-13 | MIT |
| iniconfig | pytest-dev; PyPI `hpk`, `ronny` | 2026-10-06; 2.3.0 on 2025-10-18 | MIT |
| packaging | PyPA; PyPI `brettcannon`, `dstufft`, `pf_moore`, `pradyunsg` | 2026-08-04; 26.2 on 2026-04-24 | Apache-2.0 OR BSD-2-Clause |
| pluggy | pytest-dev / Holger Krekel; PyPI `flub`, `goodboy`, `hpk`, `nicoddemus`, `ronny`, `The_Compiler` | 2026-10-15; 1.6.0 on 2025-05-15 | MIT |
| colorama | Jonathan Hartley / Arnon Yaari; prior PyPI `tartley`, `wiggin15` evidence reused | 2022-10-25; 0.4.5 on 2022-06-16 | BSD-3-Clause from prior review; current JSON classifier says BSD |
| Pygments | Pygments team; current metadata maintainer Matthäus G. Chajdas; prior PyPI `Anteru`, `gbrandl`, `mitsuhiko` evidence reused | 2026-08-17; 2.20.0 on 2026-03-29 | BSD-2-Clause |

Current publisher sources, queried `01:03:11.686Z`–`01:03:12.712Z`: [tzdata](https://pypi.org/project/tzdata/2026.5/), [pytest](https://pypi.org/project/pytest/9.1.1/), [iniconfig](https://pypi.org/project/iniconfig/2.3.1/), [packaging](https://pypi.org/project/packaging/26.3/), [pluggy](https://pypi.org/project/pluggy/1.7.0/). Each successful page reported Trusted Publishing for its artifacts. This is registry evidence, not independent attestation verification. The earlier review reported no Trusted Publishing for Pygments; its current publisher page could not be checked. No current Trusted Publishing claim is made for colorama.

The declared licenses support the intended private project use at this screening level. Redistribution must retain the applicable licenses/notices; archive license files were not extracted. Colorama's old release date is a maintenance limitation, not itself evidence of a vulnerability. Its metadata accepts 3.12, while the older documented tested-version list cited in the previous review ends at 3.10. None of the seven projects had an uploaded artifact after the cutoff in the current release listings. Open security issues outside PyPI/OSV were not searched under the network restriction.

Runtime/security assessment, reusing the earlier documented behavior:

- `tzdata`: compiled TZif data resources for local `zoneinfo` reads, not a second timezone engine. No declared network/broker need. Pinning the distribution does not prove which database `zoneinfo` selects: system TZPATH data can take precedence. Later evidence must identify the data source used for DST/golden tests. This package does not establish the meaning of raw MT5 timestamps.
- `pytest`: executes test modules, `conftest.py` and plugins with the process's permissions; writes caches/temp files and potentially bytecode. Keep it in the dev/test environment. The prior review's isolated-environment and plugin-autoload cautions still apply; no runner setting is changed or mandated by this document.
- `colorama`: console/stdout handling on Windows; `iniconfig`: configuration parsing/file-reading when invoked on a path; `packaging`: requirement/version/marker parsing; `pluggy`: execution of registered hooks; `Pygments`: syntax parsing/highlighting, including regex attack surface. No broker or network integration is required by their stated uses; this is purpose-based assessment, not proof of absence of network/file behavior.
- All seven target wheels are universal. Their tags do not establish that archives contain no unexpected native files, startup hooks, entry points or malicious code. Wheel contents, install hooks and source code were not inspected. Using a wheel avoids invoking an sdist build backend; source-build fallback and additional build dependencies are outside this proposal.

Replacing `tzdata` with hand-maintained DST rules conflicts with the contract. Replacing pytest with stdlib `unittest` changes the prescribed workflow; substituting its five required transitives would require patching the runner. No extra dependency abstraction is justified here.

## Exact Python 3.12 / Windows dependency closure

```text
runtime:
  tzdata==2026.5                             -> no Requires-Dist
dev/test:
  pytest==9.1.1
    colorama>=0.4; sys_platform == "win32"    -> colorama==0.4.6
    iniconfig>=1.0.1                         -> iniconfig==2.3.1
    packaging>=22                           -> packaging==26.3
    pluggy<2,>=1.5                           -> pluggy==1.7.0
    pygments>=2.7.2                          -> Pygments==2.21.0
```

Total: **2 direct + 5 transitive = 7 distributions**, or 1 runtime + 6 dev/test distributions. Windows x64 still has `sys_platform == "win32"`. pytest's `exceptiongroup>=1` and `tomli>=1` apply only below Python 3.11, excluded by `>=3.12,<3.13`. Its `dev` extra is not selected: this project's dev dependency group is not the `pytest[dev]` extra. Thus `hypothesis`, `attrs`, `requests`, `setuptools` and the other extra-only requirements are not pulled in. Pygments' `windows-terminal` extra is also unselected; colorama is already required by pytest. The other five distributions declare no further runtime dependencies.

This is a metadata-derived closure, not an executed resolver result. The future `uv.lock` must preserve these exact pins and applicable markers and be checked for additional distributions. No build backend such as hatchling, setuptools or uv_build has been admitted by this report. Do not assume future build-system requirements belong to this seven-package closure. No `MetaTrader5`, NumPy, pandas, pytz or strategy/research dependency is included.

## Wheel compatibility and registry hashes

Each requested release publishes exactly one universal wheel plus an sdist. All seven wheels were non-yanked. `py2.py3-none-any` expands to `py2-none-any` and `py3-none-any`; its Python 3 component, and each `py3-none-any` wheel, support CPython 3.12 on `win_amd64`. A dedicated cp312 wheel is not needed for these universal distributions.

| Exact wheel filename | Wheel tag | Requires-Python | Compressed bytes |
|---|---|---|---:|
| `tzdata-2026.5-py2.py3-none-any.whl` | `py2.py3-none-any` | `>=2` | 347996 |
| `pytest-9.1.1-py3-none-any.whl` | `py3-none-any` | `>=3.10` | 386536 |
| `colorama-0.4.6-py2.py3-none-any.whl` | `py2.py3-none-any` | `>=2.7`, excluding `3.0.*` through `3.6.*` | 25335 |
| `iniconfig-2.3.1-py3-none-any.whl` | `py3-none-any` | `>=3.10` | 7552 |
| `packaging-26.3-py3-none-any.whl` | `py3-none-any` | `>=3.9` | 129956 |
| `pluggy-1.7.0-py3-none-any.whl` | `py3-none-any` | `>=3.10` | 27082 |
| `pygments-2.21.0-py3-none-any.whl` | `py3-none-any` | `>=3.9` | 1250147 |

Total compressed wheel size **2,174,604 bytes**; excludes Python, uv, extracted files and caches. The following SHA-256 values are registry-reported and matched the previous report; they were not recomputed from downloaded artifacts.

| Distribution | Registry SHA-256 of the wheel above |
|---|---|
| tzdata==2026.5 | `b683bd1b6659ddcd810ff02ad09ba821d4bf1065072805063eb35c49617905ac` |
| pytest==9.1.1 | `37a86b45efb9a47a61a36449063e8e18d0cab3161329fc099eb21783169c4f0c` |
| colorama==0.4.6 | `4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6` |
| iniconfig==2.3.1 | `9121e2c1fdb355232495be3194c8dfe87ccc2d5dee45947b78e68f499790d7a7` |
| packaging==26.3 | `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c` |
| pluggy==1.7.0 | `7dd7b0d8832ba3cb632c306926ded123429211b83641b35dc5c41ad2d34f9bec` |
| Pygments==2.21.0 | `2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9` |

## OSV query evidence and changes since the previous review

Endpoint: [OSV read-only query API](https://api.osv.dev/v1/query), `POST`, `Content-Type: application/json`. Request shape (substitute each table row):

```json
{"package":{"name":"tzdata","ecosystem":"PyPI"},"version":"2026.5"}
```

All times below are **UTC on 2026-10-21**; add seven hours for Asia/Bangkok. Every exact query returned HTTP **200**, body **`{}`**, with no pagination token: **no indexed advisory matched the selected version**. Every exact PyPI JSON also returned `vulnerabilities: []`.

| Query name | Exact version | Query started UTC | Response completed UTC | HTTP / body |
|---|---|---|---|---|
| tzdata | 2026.5 | 01:02:57.488 | 01:02:58.096 | 200 / `{}` |
| pytest | 9.1.1 | 01:02:57.490 | 01:02:57.987 | 200 / `{}` |
| colorama | 0.4.6 | 01:02:57.490 | 01:02:58.032 | 200 / `{}` |
| iniconfig | 2.3.1 | 01:02:57.490 | 01:02:57.986 | 200 / `{}` |
| packaging | 26.3 | 01:02:57.490 | 01:02:57.966 | 200 / `{}` |
| pluggy | 1.7.0 | 01:02:57.491 | 01:02:58.005 | 200 / `{}` |
| pygments | 2.21.0 | 01:02:57.491 | 01:02:57.985 | 200 / `{}` |

Package-wide requests omitted `version`. Every response was HTTP 200 with no next-page token. Returned records' `published` and `modified` fields were compared with `2026-10-20T19:45:00.000Z`.

| Query name | Query started → completed UTC | Records | Published or modified after cutoff |
|---|---|---:|---:|
| tzdata | 01:03:11.817 → 01:03:12.672 | 0 | 0 |
| pytest | 01:03:11.838 → 01:03:13.159 | 2 | 0 |
| colorama | 01:03:11.838 → 01:03:13.139 | 0 | 0 |
| iniconfig | 01:03:11.839 → 01:03:13.153 | 0 | 0 |
| packaging | 01:03:11.839 → 01:03:13.096 | 0 | 0 |
| pluggy | 01:03:11.839 → 01:03:13.152 | 0 | 0 |
| pygments | 01:03:11.839 → 01:03:13.152 | 10 | 0 |

These counts include alias representations and historical affected releases, not currently applicable vulnerabilities. pytest's two records represent CVE-2025-71176, including [GHSA-6w46-j5rx-g56g](https://osv.dev/vulnerability/GHSA-6w46-j5rx-g56g), fixed in **9.0.3**, below proposed 9.1.1. The GHSA record was last modified `2026-09-10T03:50:32.768043789Z`.

Pygments' ten records cover five historical advisory families. The most recent family is CVE-2026-4539 / [GHSA-5239-wwwm-4pmq](https://osv.dev/vulnerability/GHSA-5239-wwwm-4pmq) / PYSEC-2026-2987, fixed in **2.20.0**, below proposed 2.21.0; the GHSA record was last modified `2026-09-10T03:50:59.780634752Z`. The other families are CVE-2015-8557, CVE-2021-20270, CVE-2021-27291 and CVE-2022-40896. The latter has differing historical fixed-version metadata (2.15.0 vs 2.15.1); 2.21.0 is above both, and its exact query is empty.

Thus no newly dated advisory or selected-version match was found since the cutoff. OSV indexing can lag; published/modified timestamps are not ingestion timestamps. This is not an exhaustive new-disclosure search or a guarantee against malicious packages, bundled code vulnerabilities or undisclosed issues.

## Hypothesis — information only for a later decision

CORE-001 AC-01 requires at least 20 reviewer-chosen random round-trip inputs; pytest plus stdlib `random` can meet that criterion with reproducible inputs and explicit boundary cases. Hypothesis would add generated exploration and shrinking, but is not necessary for the present seven ACs. If the author selects Hypothesis-backed tests from the approved `property-based-testing` skill trial, the library becomes necessary for those tests. The contract's plan explicitly requires separate admission; trial approval for a skill is not package/lockfile approval. The [tooling registry](../tooling/registry.md) identifies that trial; this review did not fetch or execute the external skill.

| Informational candidate pin | Current metadata | Target wheel | Required default dependency |
|---|---|---|---|
| [hypothesis==6.170.5](https://pypi.org/pypi/hypothesis/6.170.5/json) | Python `>=3.11`; MPL-2.0; David R. MacIver / Zac Hatfield-Dodds; latest release 2026-10-20 | `hypothesis-6.170.5-cp312-cp312-win_amd64.whl`, 687748 bytes, non-yanked | `sortedcontainers<3.0.0,>=2.1.0` |
| [sortedcontainers==2.4.0](https://pypi.org/pypi/sortedcontainers/2.4.0/json) | No declared Requires-Python bound; Apache 2.0; Grant Jenks; latest release 2021-05-16 | `sortedcontainers-2.4.0-py2.py3-none-any.whl`, 29575 bytes, non-yanked | None |

Hypothesis's current release metadata has **no universal wheel**; the target tag is **`cp312-cp312-win_amd64`** (also a compatible `cp311-abi3-win_amd64` wheel). Do not assume a historical pure-Python characterization still applies. The tag introduces platform/ABI considerations for any later admission; contents and native code were not inspected. Its target wheel was uploaded `2026-10-20T00:53:15.034284Z`, registry SHA-256 `972ca127b57cbd8f0d5e5e454fbfb890b54e96e7dbc897ba1267e51d97a01b6a`. Sorted Containers wheel SHA-256: `a163dcaede0f1c021485e957a39245190e74249897e2ae4b2aa38595db237ee0`. Its old release age and Hypothesis's MPL-2.0 obligations merit attention in a later full admission.

Optional extras are not default dependencies. Hypothesis `[pytest]` adds pytest; `[zoneinfo]` adds `tzdata>=2026.5` on Windows; those versions are already covered by the proposed seven-package set. Neither extra is required merely to generate integer timestamps. `[all]`, CLI, ghostwriter, crosshair and other integration extras enlarge the dependency set and are not proposed. A later assessment must also cover test execution, example-database/cache files and any optional integrations; this is informational screening only.

Latest PyPI reads: Hypothesis `01:02:59.397Z`–`01:02:59.669Z`; Sorted Containers `01:03:00.089Z`–`01:03:00.366Z`; both HTTP 200, empty PyPI vulnerability arrays. Metadata/target wheels were independently re-read at `01:03:50.401Z`–`01:03:51.196Z` with the same versions.

| OSV informational query | Started → completed UTC, 2026-10-21 | HTTP / body |
|---|---|---|
| hypothesis, version 6.170.5 | 01:02:59.669 → 01:03:00.089 | 200 / `{}` |
| sortedcontainers, version 2.4.0 | 01:03:00.366 → 01:03:00.763 | 200 / `{}` |
| hypothesis, package-wide | 01:03:50.673 → 01:03:51.172 | 200 / `{}` |
| sortedcontainers, package-wide | 01:03:51.196 → 01:03:51.534 | 200 / `{}` |

No indexed matches were returned; this is not an ADMIT/REJECT/SPIKE FIRST proposal for these two packages. Neither is included in D-012.

## Blocks and limitations encountered

**BLOCKED — current publisher HTML refresh only:** [colorama 0.4.6](https://pypi.org/project/colorama/0.4.6/) and [Pygments 2.21.0](https://pypi.org/project/Pygments/2.21.0/) returned HTTP 200 with a 3036-character Client Challenge page, confirmed at `2026-10-21T01:03:22.775Z` and `01:03:23.100Z`. Exact visible block text (same on both):

```text
Client Challenge
JavaScript is disabled in your browser. Please enable JavaScript to proceed.
A required part of this site couldn’t load. This may be due to a browser extension, network issues, or browser settings. Please check your connection, disable any ad blockers, or try using a different browser.
```

No challenge code was executed and no browser/security setting changed. Current package JSON and OSV succeeded; prior publisher/license evidence was reused as explicitly marked above. The successful JSON requests do not count as a successful HTML publisher refresh. This is a site response, not an automatic approval rejection.

**Local search tool unavailable:** the read-only helper's `rg` invocation returned `The term 'rg' is not recognized as the name of a cmdlet, function, script file, or operable program.` Git/PowerShell searches supplied the local evidence; nothing was installed.

**FAIL — repository locked-path check:** standalone `node scripts/controls/check-locked-paths.mjs main` exited 1. Exact output:

```text
Locked-path check · base main · head working tree · merge-base 45c1ea5 · 11 changed path(s) · 17 commit(s) checked
!! locked      M  AGENTS.md  (agent instruction file)
Result: FAIL: 1 control change(s) need owner approval (PR label "owner-approved-control-change").
Implementers must not change these paths; if the change is intended, the owner reviews it and applies the label.
```

The working tree was clean when the baseline was checked. The AGENTS.md change is in existing history against local `main`/merge-base `45c1ea58ce2d0e433966a9125e97d55312a1c104`; it was not made by this run. No ref, configuration or label was changed. This local FAIL does not establish the state of remote CI or owner labels. No remote write was attempted.

## D-012 Add project dependencies for CORE-001 — proposed

Date: 2026-10-21. Status: **proposed — รอเจ้าของอนุมัติ**. ข้อความร่างสำหรับ DECISIONS.md; ยังไม่ได้แก้ไฟล์นั้น

Decision: เสนอ ADMIT ชุด project dependencies แรกของ CORE-001 บน Windows x64 / CPython 3.12 (`requires-python = ">=3.12,<3.13"`) โดย pin ครบทุก distribution ดังนี้:

| Group | Exact pin |
|---|---|
| Runtime (`project.dependencies`) | `tzdata==2026.5` |
| Dev/test direct | `pytest==9.1.1` |
| Dev/test transitive, Windows | `colorama==0.4.6` |
| Dev/test transitive | `iniconfig==2.3.1` |
| Dev/test transitive | `packaging==26.3` |
| Dev/test transitive | `pluggy==1.7.0` |
| Dev/test transitive | `Pygments==2.21.0` |

Why: `tzdata` ให้ฐานข้อมูล IANA แก่ stdlib `zoneinfo` ตาม contract บน Windows; pytest เป็น test runner ตาม architecture และ contract พร้อม transitives ที่จำเป็น ทั้งเจ็ด pin มี universal wheel ตรงเป้าหมาย ไม่มีการ yank และไม่พบ OSV advisory ที่ตรงกับเวอร์ชัน ณ เวลา query ในรายงานนี้ จึงเสนอใช้ในโปรเจกต์โดยไม่ต้องทำ native-ABI spike เพิ่มสำหรับชุดนี้

Scope: แทนที่ข้อจำกัดเฉพาะ spike ของ D-010/D-011 **สำหรับชุด CORE-001 นี้เมื่อเจ้าของอนุมัติ D-012 เท่านั้น** จากนั้น Claude จึงสร้าง `pyproject.toml` และ `uv.lock` ฉบับแรกพร้อม dev/test group และติดตั้งภายใต้ authorization ของ contract ที่เจ้าของยืนยัน ตรวจว่า lockfile มี exact pins ครบ ไม่มี extra/build dependency ที่ไม่ผ่าน admission และใช้ wheels ที่รองรับ Python 3.12 / Windows x64

Alternatives: ใช้ stdlib `zoneinfo` พร้อมข้อมูลจากระบบอย่างเดียวไม่เพียงพอบน Windows เป้าหมาย; ไม่เขียนกฎ DST เอง; เปลี่ยนเป็น unittest จะเปลี่ยน workflow ใน contract โดยไม่แก้ความต้องการ timezone data

Consequences: มี runtime dependency 1 ตัวและ dev/test distributions 6 ตัว; ต้องติดตาม timezone-data updates และ advisories พร้อมทำ admission ใหม่ก่อนเปลี่ยน pins; บันทึก data source ที่ `zoneinfo` ใช้จริงและทดสอบ DST ด้วย golden tables; pytest/plugins รันโค้ดด้วยสิทธิ์ process จึงใช้ environment ของงานที่ควบคุม dependency ได้

Exclusions: ไม่อนุมัติ `hypothesis`/`sortedcontainers`, extras, build backends, MetaTrader5/NumPy, broker connection, order execution, research data หรือ strategy experiment ข้อมูล Hypothesis ในรายงานนี้มีไว้ประกอบการตัดสินครั้งถัดไปเท่านั้น

Validation after approval: Claude ตรวจ resolved closure และสร้าง environment; รัน zoneinfo smoke check ตาม contract และ `uv run pytest tests -q` เมื่อมี tests/implementation พร้อมบันทึก commit/เวลา แยกจากผล admission นี้ ไม่ fallback เป็น source build หรือเพิ่ม package โดยอัตโนมัติ

Evidence: [CORE-001 dependency admission](CORE-001-dependency-admission.md), [prior SPIKE-001 admission](SPIKE-001-dependency-admission.md), [approved contract](../contracts/CORE-001-timebase.md), exact PyPI/OSV queries above. Review when: เปลี่ยน pin/Python/platform, เพิ่ม extra/build dependency, พบ advisory, หรือกฎ timezone ที่เกี่ยวข้องเปลี่ยน

## Checks, handoff and session checkpoint

All commands refer to HEAD `ee33524d55bceb227a11b48619804a848c1aa33f`. Times below are **2026-10-21 +07** unless explicitly UTC. This report is the sole permitted file change; no staging, commit or push is authorized in this run.

| Command / procedure | Result | Commit | Time / evidence |
|---|---|---|---|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: clean initial tree, expected branch | `ee33524` | Session start, before queries |
| `git ls-files 'src/*' 'pyproject.toml' 'uv.lock' '*requirements*'` | PASS: no existing tracked implementation/dependency files | `ee33524` | 08:03:11 |
| `node --version` | PASS: existing v26.12.0 | `ee33524` | 08:02:41 |
| `node --input-type=module -` — GET seven latest/exact PyPI JSONs, inspect history/markers/files | PASS: 14 HTTP 200 responses; all requested versions current; no uploads after cutoff | `ee33524` | 08:02:57; URLs/method above |
| `node --input-type=module -` — OSV exact-version and package-wide POST queries | PASS: no exact matches; no returned record published/modified after cutoff | `ee33524` | 08:02:57–08:03:13; exact query times above |
| `node --input-type=module -` — GET seven PyPI publisher pages | PASS for 5; BLOCKED for colorama/Pygments HTML | `ee33524` | 08:03:11–08:03:23; exact block above |
| `node --input-type=module -` — compare current seven wheel names/hashes/non-yanked flags against prior report | PASS: 7/7; total 2174604 bytes | `ee33524` | 08:03:50.405–08:03:50.425 |
| `node --input-type=module -` — Hypothesis/Sorted Containers PyPI and OSV informational queries | PASS: current pins/target tags established; no indexed exact or package-wide matches | `ee33524` | 08:02:59–08:03:51; times above |
| `bash scripts/controls/red-flags.sh main` — baseline | PASS, exit 0, 0 pattern groups; AGENTS.md listed under control paths | `ee33524` | 08:03:22 |
| `node scripts/controls/check-locked-paths.mjs main` — standalone | FAIL, exit 1, one inherited AGENTS.md control change | `ee33524` | 08:03:50; baseline also observed at 08:03:22 |
| `node scripts/controls/test-controls.mjs` | SKIPPED: no control implementation changed | `ee33524` | Document-only task |
| `uv` resolution, install/import, pytest, zoneinfo smoke check | SKIPPED: prohibited by this admission-only request | `ee33524` | No package code executed |

Not tested: actual resolver output or lockfile contents; wheel internals/install hooks/entry points; independent attestations or reproducible builds; installed Python 3.12/Windows console behavior; actual timezone data selection; CORE-001 functional/architecture acceptance; Hypothesis execution/native compatibility; broker or account interaction. These were not run, rather than tested and failed. Open-issue searches outside the allowed domains were out of scope.

Handoff: Claude can review this unstaged report and present the concrete D-012 draft to the owner in a later interactive session. Only after owner approval may the implementer update DECISIONS.md and create/install the project environment. Recheck the actual lock closure before running package code. The checkpoint is here instead of PROGRESS.md because the owner expressly limited this run to one report. There are no pending installs or external writes.

### Completion report

1. **Outcome for the user:** ได้ข้อเสนอ ADMIT ระดับโปรเจกต์ครบ 7 pins พร้อม wheel tags/hashes, OSV query times, ร่าง D-012 และข้อมูล Hypothesis แยกสำหรับการตัดสินภายหลัง
2. **Acceptance status:** การจัดทำ admission ตามคำขอนี้ — PASS ด้าน deliverable/evidence ตามขอบเขตและข้อจำกัดที่ระบุ; ไม่สร้าง AC ใหม่ · CORE-001 **AC-01–AC-06 | SKIPPED** (ไม่รัน package code/tests); **AC-07 | UNKNOWN** (มีเฉพาะ red-flag scan, ยังไม่รัน architecture/pytest และ locked-path check FAIL)
3. **Checks run:** command → result → commit → time ตามตารางด้านบนและ final document checks ด้านล่าง; ไม่ถือ BLOCKED/FAIL/SKIPPED ว่า PASS
4. **Files changed and why:** เพิ่ม `docs/reviews/CORE-001-dependency-admission.md` ไฟล์เดียวเพื่อส่งผล admission และร่าง decision; ไม่แก้ DECISIONS.md, PROGRESS.md, dependency files หรือไฟล์อื่น
5. **Red-flag scan hits and explanations:** baseline 0 pattern groups; AGENTS.md ที่แสดงเป็น control path มาจากประวัติ branch ไม่ใช่การแก้ในงานนี้; scanner ไม่อ่านเนื้อหา untracked report จึงตรวจเนื้อหาเอกสารแยกก่อนส่ง
6. **Not tested:** resolver/install/package runtime, wheel internals, timezone source, Hypothesis native compatibility และ contract acceptance ตามรายการด้านบน
7. **Delivery state:** **implemented** เฉพาะ review document พร้อม metadata/advisory checks; ไม่ใช่ CORE-001 verified, merged หรือ deployed
8. **Remaining risks, follow-ups and next action:** เจ้าของตัดสิน D-012 ภายหลัง; Claude ตรวจ lock closure และทดสอบจริงเมื่อได้รับอนุญาต; publisher HTML 2 หน้าและ locked-path FAIL ยังเปิดเผยเป็นข้อจำกัด รายงานปล่อย unstaged ไม่มี commit/push

### Final document checks

| Command / procedure | Result | Commit | Time, 2026-10-21 +07 |
|---|---|---|---|
| `git status --short`; `git diff --cached --name-only`; `git diff --name-only`; `git rev-parse HEAD` | PASS: only this report untracked; staged and tracked diffs empty; HEAD unchanged | `ee33524` + report | 08:06:02 |
| `bash scripts/controls/red-flags.sh main` after report creation | PASS, exit 0, 0 pattern groups; report explicitly listed as untracked/not scanned | `ee33524` + report | 08:06:02–08:06:03 |
| `node --input-type=module -` — first document structure check | FAIL, exit 1: `missing D-012 draft`; diagnostic-script Unicode transport defect, not a missing heading in the file | `ee33524` + report | 08:06:02.581 |
| `node --input-type=module -` — literal/heading comparison, then ASCII-anchor document check | PASS, exit 0: transmitted dash was `?`, file heading retained U+2014; UTF-8 text, whitespace, final newline, fences, seven draft pins, seven wheel hashes, seven local links checked | `ee33524` + report | 08:06:19.083 |
| `node --input-type=module -` — direct untracked report screen using the scanner's eight Markdown-applicable pattern groups | PASS, exit 0: 0 hits; the two code-only groups do not apply to this Markdown file | `ee33524` + report | 08:06:19.083 |

The first document checker used a literal em dash in a PowerShell here-string piped to Node; that literal arrived as `?`. A direct comparison proved the report itself had the correct heading. The checker used an ASCII-only heading anchor on the next run; no repository configuration or document heading was changed to make the check pass. The supplemental text screen covers the untracked report but does not replace the repository scan after the implementer stages it.
