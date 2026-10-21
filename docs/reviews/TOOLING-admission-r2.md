# TOOLING admission r2 — offline source review

## สรุปสำหรับเจ้าของ

**ตรวจ source ครบแล้ว: เสนอ SPIKE FIRST สองตัว และ REJECT หนึ่งตัว ยังไม่มี ADMIT และยังไม่ได้ติดตั้งอะไร**

| Candidate | Version ที่พบ | ข้อเสนอ | เหตุผลหลัก |
|---|---|---|---|
| `property-based-testing` | 1.2.2 | **SPIKE FIRST** | มีประโยชน์ต่อ property tests แต่ต้องพิสูจน์ขอบเขต test-author/reviewer และ dependency approval; upstream รายงานเองว่า eval ยังสร้าง dependency file โดยไม่ควรสร้าง |
| `dimensional-analysis` | 3.1.0 | **SPIKE FIRST** | workflow ปกติแก้ source comments แบบ full-auto จึงใช้ตรง ๆ ใน read-only review ไม่ได้; ต้องทดลองบน synthetic scratch ที่กำหนดขอบเขตและวัดประโยชน์กับ Python/Decimal |
| `supply-chain-risk-auditor` | 2.0.4 | **REJECT ณ pin นี้** | collector อ่าน token ผ่าน `gh auth token` แม้ใช้ `--offline`; ยังอาจเรียก `pip-audit` ที่พบใน PATH ซึ่งไม่ได้ถูกจำกัดด้วย offline flag |

ทุกตัวตรวจที่ repository SHA **`a3131740a39291e42fd15b9eac07e0b393ad71b1`** เท่านั้น อ่านครบ **104 files / 12,797 lines** รวม instruction, references, agents, scripts, tests, fixtures และ metadata พร้อม root LICENSE/README การติด TLS ใน r1 ไม่ขวาง source review รอบนี้แล้ว ข้อเสนอ SPIKE FIRST เป็นงานถัดไปที่ต้องมี scope/approval ของเจ้าของ ไม่ใช่สิทธิ์ให้รัน spike ในรอบนี้

ใช้ license **CC-BY-SA-4.0** ของ upstream และเสนอวิธีติดตั้งผ่าน marketplace เท่านั้นตามคำสั่งเจ้าของ ไม่ copy/vendor เข้า repository; Solidity fixtures แปดไฟล์ของ dimensional-analysis มี MIT SPDX แยกเฉพาะไฟล์นั้น วิธี marketplace ที่ README ให้มายังไม่พิสูจน์การรักษา full SHA pin จึงต้องตรวจ installation revision ก่อนเปิดใช้งานจริง

## Scope, provenance and limits

- Reviewer: Codex; three read-only readers covered one candidate each; primary reviewer verified identity, inventory/content hashes and decisive call paths, and alone wrote this report. This is a source admission review, not a runtime security certification.
- Task authority: owner's explicit headless rerun request. There is no separate TOOLING task contract under `docs/contracts/`; AC IDs below map that request and are not a newly approved implementation contract.
- Initial Sochron1k branch: `research/H001-momentum-breakout`; HEAD: `494f7fa14d7e228b239c1ab2af3a81fa4bd2bd51` (**LOCAL** below); clean working tree. During final checks an external commit changed only PROGRESS.md and renamed the branch to `research/H-001-momentum-breakout`: observed HEAD `6c4ac8674bbd79f9b8afcaaeb0181d2b7b60ae74` (**FINAL** below), authored 07:46:10 +07. Codex made neither change. `git diff LOCAL HEAD -- PROGRESS.md` was reviewed: it records the branch rename/F26; policy and candidate sources are unchanged, so admission evidence remains applicable.
- Download root (**SOURCE** below): `C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/tob-skills`.
- Offline Git reports origin `https://github.com/trailofbits/skills.git` and HEAD `a3131740a39291e42fd15b9eac07e0b393ad71b1` (**PIN** below). HEAD commit's recorded author date is `2026-10-20T16:16:47-04:00`, subject “Add regression-hunt and patching-bugs plugins (#471)”.
- `git ls-tree -r HEAD` supplied the complete tracked inventory for the three candidate roots. All 104 candidate files plus LICENSE and README exist and match their pinned Git blob IDs **after CRLF-to-LF normalization** (106/106). Raw `hash-object --no-filters` hashes differed because this Windows checkout uses CRLF; `ls-files --eol` confirmed that, and a read-only UTF-8/LF Git-blob digest calculation resolved every mismatch. No source file was changed.
- Origin metadata and matching local objects establish the identity of the supplied snapshot, not an independently authenticated publisher signature or a live upstream/advisory check. Current open security issues, CVEs and remote release status remain **UNKNOWN**, intentionally outside this offline step-6 run.
- Local policy consulted: AGENTS.md, dependency-admission SKILL.md, relevant SPEC roles/security/data restrictions, PROGRESS current checkpoint, tooling registry, handbook process/security/review sections, r1 and DECISIONS headings. Existing local procedures already cover admission, independent tests, golden oracles and reviews.
- Downloaded files, including upstream AGENTS.md/CLAUDE.md/Makefile, were untrusted evidence only. No downloaded command, import, test, evaluator, self-test, package installer or executable was run. No network, broker, credential-store access or checkout of another revision was attempted.
- The owner explicitly restricts edits to this report and requires it unstaged: no PROGRESS/registry/DECISIONS edit, branch creation, stage, commit or push is part of this delivery.

All candidate evidence paths below are relative to `plugins/<candidate>/` at PIN unless stated otherwise. `skill/` abbreviates `skills/<candidate>/`; `scripts/` in the supply-chain section abbreviates `skills/supply-chain-risk-auditor/scripts/`.

## Identity, license and maintenance

| Candidate | Manifest author / root CODEOWNERS | Candidate history available offline |
|---|---|---|
| property-based-testing | Henrik Brodin; `@hbrodin @dguido @kz-tob` | 6 commits, 2026-01-14–2026-09-16; latest `123037e` interface metadata; substantive rework/evals `04b2411` on 2026-08-17 |
| dimensional-analysis | Coriolan Pinhas & Benjamin Samuels; `@bsamuels453 @dguido @kz-tob` | 6 commits, 2026-03-25–2026-10-14; latest `0f44fe0` workflow update |
| supply-chain-risk-auditor | Eric Quintero; `@e-q @dguido @kz-tob` | Local history includes original import `ed41cd7`, deterministic collector rebuild `e6066e7` (2026-08-10), Windows cache fix `7dee682` (2026-08-27), malformed cache fix `7e7a9b2` (2026-08-31), metadata changes through `123037e` (2026-09-16) |

These are commit-history observations, not release cadence guarantees. Names/versions are read from each `.claude-plugin/plugin.json:2-8`; ownership is recorded in root `CODEOWNERS:15,32,43`. All three manifests are metadata only, with no install lifecycle command.

Root `LICENSE:1,57-68` identifies Creative Commons Attribution-ShareAlike 4.0 International; root `README.md:166` applies it to the work and attributes Trail of Bits. LICENSE sections 2–3 describe reproduction/adaptation and attribution/ShareAlike conditions when material is shared. This report records the supplied text, not a broader legal conclusion about Sochron1k. Preserve upstream notices in the marketplace installation and follow the owner's no-copy requirement. The eight dimensional-analysis `tests/fixtures/**/*.sol` files carry `SPDX-License-Identifier: MIT` at line 1; no other candidate-specific license override was found.

Root license blob: `3b7b82d0da2db857eda1a798dbd908ea136f07b5` (427 lines). Root README blob: `dc215cd7aed3c6538bbb7a93a13bb4bddc33a96c` (166 lines).

## Permission and destination inventory

Declarations below are requested capabilities, not proof that a particular host grants them. Absence of `allowed-tools` is not a read-only guarantee. Optional examples/eval harnesses are separated from normal operation; none ran here.

### property-based-testing

| Surface | Evidence | Permission / side effect |
|---|---|---|
| Core skill | `skill/SKILL.md:1-4,58-68` | No `allowed-tools` stanza; reads/searches source and tests, generates/reviews tests, triages failures. `effort: low` is also requested. |
| Generation/refactoring | `skill/references/generating.md`; `refactoring.md:8-10,119-120` | Test-file creation and test runs implied. Production refactoring is explicitly left to the author. |
| Ablation evals | `evals/02-neg-cargo-fuzz-coverage/prompt.md:4`; `evals/03-dependency-is-users-call/prompt.md:4`; `README.md:90,95-102` | Respectively `Skill Read` and `Skill Read Write`; README requests `--allow-tools Write` and names `ANTHROPIC_API_KEY` as a prerequisite. No key value is needed for this review. |
| Trigger harness | `evals-extra/run.sh:216-223` | `claude` subprocess with `--permission-mode plan --disallowed-tools Agent`; subprocess/background jobs, temp files, executable stub scripts and persisted raw stdout/stderr. |
| Effectiveness harness | `evals-extra/effectiveness.sh:62-64,80-113,294-300` | Unpinned Hypothesis/pytest via uv; an edit-capable `acceptEdits` Claude session; execute generated tests and temporarily mutate/restore fixture code. Self-test reaches package-dependent grading too. |
| Cleanup / artifacts | `evals-extra/run.sh:103-112,289,311-354,478`; `effectiveness.sh:172-246,288-322` | Create/copy/delete temporary fixtures; results may persist at `ARTIFACT_DIR` or temporary output paths. |

No hook/MCP config, native binary, lifecycle installer, direct broker path, `bypassPermissions` or `--dangerously-skip-permissions` was found. `acceptEdits` is an edit permission mode, not evidence of disabling all host controls.

Destinations, including non-runtime references:

- Marketplace: GitHub `trailofbits/skills` (`README.md:13-17`); attribution `https://github.com/trailofbits` (manifest:7).
- Tutorial `https://secure-contracts.com` (`skill/references/libraries.md:77`); script-comment reference `agentskills.io/skill-creation/optimizing-descriptions` (`evals-extra/run.sh:4`); Go import/search identifier `pgregory.net/rapid` (`libraries.md:26`). These are references, not hard-coded HTTP requests.
- Claude CLI's **configured model service**, hostname unspecified: fixture prompts and files read by eval sessions may leave the machine; both shell evals and `claude plugin eval` spend inference budget. Source does not pin a provider URL.
- uv's **configured index/distribution hosts** for `hypothesis` and `pytest`, and configured **Python download source** if needed. Hosts are not specified in source; do not equate this with a fixed allowlist. `uv run --no-project python3` does not pin 3.12.
- `SMTP_HOST` (with `MAIL_FROM`, `SITE_NAME`) occurs in fenced SMTP/send-message fixture code at `evals/03-dependency-is-users-call/prompt.md:27-28`. It is inert prompt data, not a requested production mail action; no concrete host is supplied.
- `http://www.w3.org/2000/svg` is the bundled icon's XML namespace only. The icon contains no script or external resource fetch.

### dimensional-analysis

| Surface | Evidence | Permission / side effect |
|---|---|---|
| Coordinator | `skill/SKILL.md:4,11,19,28-36,50` | `Read Write Edit Grep Glob Task TodoWrite`; native workers; writes `DIMENSIONAL_SCOPE.json`, `DIMENSIONAL_UNITS.md`, phase state and source comments. Requires an explicitly scoped writable target. |
| Scanner / discoverer / validator | Respective `agents/*.md:4-8` | `Read Grep Glob TodoWrite`. |
| Annotator | `agents/dimension-annotator.md:4-10` | `Read Write Edit Grep Glob TodoWrite`. |
| Propagator | `agents/dimension-propagator.md:4-9` | `Read Edit Grep Glob TodoWrite`. |
| All five eval prompts | Each `evals/*/prompt.md:4` | `Read Write Edit Bash Glob Grep Skill Task`. |
| Eval harnesses | `tests/smoke-test.sh:209-213`; `tests/trigger-test.sh:54-58` | `claude plugin eval`, `CLAUDE_CODE_WALNUT_SPIRE=1`, `--allow-tools Bash Write Edit`; paid model sessions. |
| Test storage / Python | `tests/smoke-test.sh:16-17,27-30,53,64,193-236`; `tests/trigger-test.sh:18-19,39-64` | Copy fixtures, delete work/result directories, write results; run three stdlib Python helpers using `uv run --no-project python3`. |

Core instructions explicitly prioritize host/user policy, preserve existing edits and forbid committing/publishing (`SKILL.md:9,19`). They do not prescribe writing Sochron1k's acceptance/golden tests. This is still a source-editing workflow, not a read-only audit mode.

Destinations:

- Marketplace GitHub `trailofbits/skills`; publisher `https://github.com/trailofbits` (manifest:8).
- Optional `https://github.com/trailofbits/slither-mcp` (`README.md:100`), a link to an additional tool, not an included/admitted MCP server. Excluded from any proposed initial trial.
- `opensource@trailofbits.com` is author contact metadata, not a requested message.
- Claude CLI's configured provider receives eval fixture/source context; host unspecified. uv may obtain an interpreter from its configured download source; no package dependencies are declared by this candidate.
- SVG namespace `http://www.w3.org/2000/svg` only; no network payload.
- No direct HTTP client, curl/wget, package-install command, credential-store read, hook, MCP implementation or native binary was found within the candidate. That does not make the subprocess-based evals offline.

### supply-chain-risk-auditor

Core `skill/SKILL.md:4` requests **Read Write Bash Glob Grep**. `:31-52` asks for manifest/lockfile discovery, `gh auth status`, collector execution and rendering outside the audited repository. `:81-82` optionally refers to `report-writing:writing-style`; that separate skill is neither bundled nor admitted by this review.

The collector reads package.json, pyproject.toml, requirements files, go.mod and supported lockfiles; writes JSON, Markdown and a persistent cache; creates/removes temporary requirement files; can delete malformed cache entries and replace cache files. The renderer reads the artifact and writes a report. Metadata collection also reads target `.git/HEAD` and its contained ref (`collect.py:1323-1346`). Tests launch `sys.executable`; one embedded test driver calls `gh_token()` without a mock (`test_collect.py:873,895`), so running the test suite would not avoid the credential issue. Source-level safeguards include zero-coverage refusal, explicit unassessable results, checks for several non-registry dependency sources (with the private-Python-index gap in F9), and `pip-audit --no-deps --disable-pip`. These are valuable but do not resolve F6/F7 below.

Actual HTTP adapters in `scripts/sources.py`:

| Destination / path template | Method / data sent | Source line |
|---|---|---:|
| `https://api.osv.dev/v1/querybatch` | POST package ecosystem/name/version batches, including resolved transitive packages | 304 |
| `https://registry.npmjs.org/{quoted-package}` | GET package metadata | 353 |
| `https://api.npmjs.org/downloads/point/last-week/{quoted-package}` | GET package download counts | 376 |
| `https://pypi.org/pypi/{name}/json` | GET Python package metadata | 396 |
| `https://proxy.golang.org/{escaped-module}/@latest` | GET Go module version metadata | 440 |
| `https://api.deps.dev/v3alpha/systems/{system}/packages/{quoted}/versions/{version}` | GET package/version project metadata | 461 |
| `https://api.github.com/repos/{owner}/{repo}` | GET upstream metadata, with Bearer token if retrieved | 559 |
| `https://api.github.com/repos/{owner}/{repo}/contents/SECURITY.md`, `.../contents/.github/SECURITY.md`, `.../contents/docs/SECURITY.md` | GET security-policy presence | 581-583,590 |
| `https://api.github.com/repos/{owner}/.github/contents/SECURITY.md`, `.../.github/contents/.github/SECURITY.md` | GET owner-level security-policy fallback | 584-585,590 |
| `https://api.scorecard.dev/projects/{normalized-repo-slug}` | GET OpenSSF report | 614 |

The HTTP client uses a redirect-following urllib opener (`sources.py:82-103,203-210`), with no destination allowlist in that opener. Redirect and environment proxy destinations are not statically bounded to the table. `pip-audit` is an additional subprocess network surface: its installed version/configuration is not pinned or inspected here, so its actual service/index/cache destinations remain **UNKNOWN**. uv's interpreter acquisition is another configured, implicit destination. The requested `gh auth status` also inherits the CLI's configured hosts/behavior; those are not specified by the candidate.

`sources.py:517-534` reads the gh credential using a subprocess, not merely an authentication-status query; the token is passed to GitHub requests (`:556-559`). The script does not intentionally print the token, but reading it already conflicts with AGENTS.md. `sources.py:622-627` checks PATH for `pip-audit`, `osv-scanner`, `npm`, `cargo-audit`, `bundler-audit`; only pip-audit is automatically executed by this collector. Detection of the others is not execution or permission to install them.

Non-production URLs/addresses also present:

- Test inputs include `git+https://x/y.git`, `https://npm.acme.internal/@acme/private/-/private-3.0.0.tgz`, `https://pypi.org/simple`, GitHub sample repositories including `acme/tiny-dep`, `a/b`, `psf/requests`, `https://www.GitHub.com/a/b/`, `https://sr.ht/~someone/project`, `https://example.com/foo`, `https://example.com/x`, `.../gone`, `.../never-fetched`, and `http://evil` (Markdown escaping test). Fixtures also reuse the production API hosts with fake package names. Additional parser-only identifiers include `gitlab.com`, `bitbucket.org`, `example.com/demo`, `example.com/m`, `golang.org/x/text`, Git-over-SSH forms under `github.com/acme/{evil-git-dep,internal-lib,vendored}`, and renderer text `git+ssh://acme/internal`; these are not additional collector fetch endpoints.
- `scripts/test_sources.py:257` uses `http://127.0.0.1:{ephemeral-port}/old` in a real loopback redirect test if the tests are run. It was not run.
- `http://www.w3.org/2000/svg` is only the icon namespace; `http://`, `https://`, `ssh://`, `git://` and registry URL prefixes used in parsers are classification inputs, not a command to fetch arbitrary dependencies.
- No candidate lifecycle installer, native binary, autonomous dependency upgrade, broker/order path or acceptance-test-authoring instruction was found.

## Findings and conditions for reconsideration

### F1 — r1 source-evidence gap resolved for this offline scope

The previous failure to retrieve inventories, instructions, scripts, license and history is resolved by the complete reads and 106 matching normalized blobs. This closes the **source-access portion** of r1 F1. Marketplace pin enforcement remains unproved and is explicitly retained below; r1 is not retrospectively relabeled PASS.

### F2 — High — PBT generation is incompatible with an unscoped implementer/reviewer invocation

**Evidence:** `property-based-testing/skill/SKILL.md:4,58-68` activates on coding/testing requests and directs writing tests when a library exists; `references/interpreting-failures.md:53-56` suggests changing strategies/properties when classifying failures. It contains no local contract or maker/reviewer gate. **Trigger/impact:** Claude implementing an engine could also author its oracle, or a review session could change locked acceptance/golden tests. That violates Sochron1k role separation, read-only review and immutable test contracts.

This is a conditional integration conflict, not an instruction to override local rules. The skill correctly leaves a new dependency to the user (`SKILL.md:64-68`) and production refactoring to the author (`references/refactoring.md:8-10`). **Proof required:** synthetic authorized test-author/reviewer/implementer cases must preserve those distinct roles; changing a failing contract property must be proposed, not applied. Independent golden answers must remain external to the implementation author.

### F3 — High — PBT bundled effectiveness/self-test resolves unapproved packages and runs generated code

**Evidence:** `property-based-testing/evals-extra/effectiveness.sh:62-64` invokes unpinned Hypothesis and pytest through uv; the self-test path reaches the grader (`:159-185,260-262`). `:294-300` launches an edit-capable model, then runs its generated tests. **Impact:** calling an apparently local self-test can install new packages and execute generated code without Sochron1k dependency admission or contract scope. Paid evaluator use also adds model-service access/cost.

**Proof required:** separately approved exact packages/Python, synthetic isolated target, bounded model budget and output paths; no invocation of upstream helpers under this source-review authorization. Core documentation's dependency caution is not an enforcement mechanism. Upstream `README.md:115-118` itself reports unwanted requirements.txt creation in 2/3 with-skill ablation runs; this is upstream evidence, not a test reproduced here.

### F4 — High — dimensional-analysis normally mutates the reviewed source; Medium — parallel writers

**Evidence:** `dimensional-analysis/skill/SKILL.md:28-36,50` requires full-auto annotations and root artifacts, ignores mode arguments by default and does not pause for approvals. `agents/dimension-annotator.md:15,215` and `dimension-propagator.md:14,162` direct edits. `references/step2.md:24` and `step3.md:26` allow parallel writing batches in the same target tree.

**Impact:** a normal “audit” invocation cannot satisfy Sochron1k's read-only reviewer role; disjoint-file parallel writers still violate its one-writer-per-working-tree rule. Scanner exclusions are not a full locked-path policy. **Existing mitigation:** `SKILL.md:9,11,19` gives host/user constraints priority, requires scoped writable access, prevents overlapping writes and forbids commit/publish. This is not proof of malicious bypass. **Proof required:** owner-scoped synthetic scratch only, serialized writes or separate worktrees, protected sentinels unchanged, and explicit refusal/blocked behavior for a read-only target. No normal reviewer installation should be approved on the assumption that “audit” means no edits.

### F5 — High — dimensional-analysis eval cleanup assumes fixed temporary paths belong to the run

**Evidence:** `dimensional-analysis/tests/smoke-test.sh:16-17,27,193` and `tests/trigger-test.sh:18-19,39,48` recursively remove fixed `/tmp/dimensional-analysis-*` work/results paths. **Impact:** pre-existing unrelated artifacts could be deleted; Windows target containment/ownership has not been established. These are optional test-harness actions, not install-time actions. **Proof required:** a separately scoped trial must establish exclusive ownership and resolved absolute deletion boundaries; do not run those bundled scripts unchanged in shared temporary storage. No deletion was attempted here.

### F6 — High — supply-chain collector reads credentials, including in offline mode

**Evidence:** `supply-chain-risk-auditor/scripts/collect.py:1421-1432` calls `sources.gh_token()` whenever discovery finds dependencies, before constructing the offline HTTP client. `sources.py:517-534` executes `gh auth token` and captures stdout. CLI options at `collect.py:1535-1547` contain no opt-out. **Impact:** direct violation of AGENTS.md's “Never read .env or any other credential store”; credentials are then available to the collector for authenticated requests. This is not just a read of public package metadata.

**Proof required before a future revision can be reconsidered:** default and offline paths must make zero credential-store/subprocess-token reads; explicit scope must govern any authenticated mechanism. A mock subprocess sentinel should fail if `gh auth token` is attempted. This report proposes **REJECT as-is**, not a local credential workaround or permission expansion.

### F7 — Medium — supply-chain offline flag does not suppress automatic pip-audit execution

**Evidence:** `supply-chain-risk-auditor/scripts/collect.py:1477` calls `_tooling_notes`; `:1284-1295` invokes a pip-audit cross-check whenever found on PATH and applicable Python pins exist. `sources.py:641-665` executes it without the HTTP client's offline flag. **Impact:** `--offline` is not a whole-process network boundary; ambient tool version/configuration changes behavior and may make external queries. The supplied `--no-deps --disable-pip` flags deliberately avoid pip resolution/build scripts and must be credited; they do not establish zero network or approved-tool identity.

**Proof required:** an offline test must assert no optional external subprocess/network call; online cross-check must require an admitted, pinned executable and approved destinations. Existing optional-tool tests are source evidence only, not validation run here. Severity is Medium for the conditional ambient-tool egress; F6 independently makes the supplied pin unacceptable.

### F8 — Medium — Windows supply-chain cache ownership is not enforced

**Evidence:** `supply-chain-risk-auditor/scripts/sources.py:107-138` documents the trust boundary and explicitly skips ownership verification when `os.getuid` is unavailable, returning a warning. Default cache is a stable path under system temp (`collect.py:1540-1545`); reads trust cached responses and malformed entries can be deleted (`sources.py:148-175`). **Impact:** a cache writable by another actor can affect admission evidence. No claim is made that this machine's temp ACL is insecure; ACL suitability was not inspected.

**Proof required:** a future admitted implementation needs a dedicated private cache whose Windows ACL/ownership is verified, with malicious-cache and cross-user cases. The existing warning and prior Windows crash fix do not prove that boundary.

### F9 — Medium — private Python registry identity is treated as public PyPI

**Evidence:** `supply-chain-risk-auditor/scripts/collect.py:404-422` excludes any truthy `source.registry` from its non-registry map; `:449-450` labels every registry entry as PyPI without checking the registry URL. **Trigger/impact:** a uv.lock entry from a private index can have its name/version sent to public PyPI/OSV and be assessed against a different public package. npm's explicit public-host test at `:129` does not cover this Python path. No private packages were queried here.

**Proof required:** a synthetic private-index lock entry must remain unassessable against public registries and produce zero public lookup requests; public PyPI entries must retain correct coverage. This is a static call-path finding, not a reproduced runtime test.

## Windows, uv, Git Bash and incremental value

| Candidate | Static fit | Evidence still needed |
|---|---|---|
| property-based-testing | Text guidance is portable and useful for round trips, idempotence, Decimal/scaled-integer boundaries and shrinking. No core runtime dependency; Hypothesis is a separate dependency decision. Harnesses use uv but omit interpreter/package pins; Bash arrays/process substitution, GNU timeout, mktemp/cp/rm/chmod/grep/awk/sed/sort/comm/seq and native Claude path handling need Git Bash. | Python 3.12 and Windows paths (including Thai UTF-8), contract/role adherence, no automatic dependency-file writes; incremental defect detection over local write-acceptance-tests/cross-agent-review/break-it-check. Upstream README:121-127 says quality/review/triage effectiveness is not established. |
| dimensional-analysis | Markdown/native-agent core; Python annotations described. Three Python helpers use stdlib; two shell harnesses use uv plus POSIX paths/utilities. No third-party Python dependency or native binary shipped. Some helper text reads omit explicit encoding. | Scoped writes, sequential workers, Windows path/encoding behavior, pinned 3.12, independently computed Python/Decimal unit cases. `tests/summarize_arms.py:107-110` says baseline matched plugin recall/blocking false positives; annotations were the reproducible difference. Solidity fixtures do not prove a benefit for XAU/USD units. |
| supply-chain-risk-auditor | `scripts/pyproject.toml` requires Python >=3.11 and `dependencies=[]`; uv.lock has only the virtual local project, so **zero declared third-party runtime/transitive dependencies**. uv invocation and tomllib fit 3.12; supports uv.lock for exact versions/transitive advisory scope. No Bash-only core requirement. | Credential/offline fixes, Windows cache ownership, approved network/disclosure policy and executable identity. No claim of runtime compatibility: source was not run. Static inspection predicts native-Windows failures in `test_sources.py:154-180`: an unconditional assertion expects POSIX ownership verification, and monkeypatch operations assume `os.getuid` exists. These are **not executed FAIL results**. Optional pip-audit/pytest and interpreter acquisition are separate dependencies/tooling, not covered by the empty runtime dependency list. |

No project dependency is added by this report. PBT and dimensional guidance may help existing local roles, but neither replaces independent golden tests. Supply-chain's deterministic coverage reporting could supplement dependency-admission in a future conforming revision; the local admission process already covers current needs without accepting F6/F7.

A future spike, if the owner chooses one, should use only synthetic non-broker data, a bounded scratch target, approved exact packages if needed, and independent expected outcomes. Do not invoke all upstream Makefile targets: the repository-wide contributor workflow reaches other plugins/tools outside this review. Do not install optional slither-mcp or report-writing integrations through this decision.

## Marketplace method and pin requirement — proposal only

Pinned root `README.md:8-19` and PBT `README.md:10-17` document this Claude marketplace route:

```text
/plugin marketplace add trailofbits/skills
/plugin menu
```

Select only the candidate explicitly approved later: `property-based-testing`, `dimensional-analysis`, or, only after a new review overturns REJECT, `supply-chain-risk-auditor`. Root README:30 uses `<plugin-name>@trailofbits` in its Codex example; this report uses the documented menu for Claude selection and makes no claim that either notation pins a revision.

**These documented commands do not pin the commit.** The required reviewed source is PIN for all three, not merely version 1.2.2/3.1.0/2.0.4 or a moving main branch. Before installation approval, the implementer must establish a supported immutable marketplace reference or an owner-controlled marketplace snapshot outside Sochron1k, verify its complete marketplace manifest and selected plugin bytes at PIN, and ensure update behavior cannot silently substitute a different revision. Verify installed source identity before enabling. The sparse clone lacks the root `.claude-plugin/marketplace.json`; this review did not fetch that missing blob or attempt an installation. It is adequate source-audit input, not a demonstrated installable marketplace snapshot.

Do not invent `@SHA` syntax, copy candidate files into `.agents/` or `.claude/`, edit the downloaded checkout, or treat registration of a floating marketplace as a pin. Marketplace install/update/pin enforcement remains **UNKNOWN**; that is a future admission condition, not an environmental blocker to the completed offline review.

## Draft registry rows — proposed, do not activate

Owner: repository owner. Reviewer/date for every row: Codex, 2026-10-21. Current registry remains unchanged; candidate/rejected states below are proposed dispositions only.

| Candidate | Publisher / license | ช่วยอะไร | Trigger ที่ควรพิจารณา | ข้อควรระวัง |
|---|---|---|---|---|
| `property-based-testing` — candidate; **SPIKE FIRST proposed** | Trail of Bits / Henrik Brodin; CC-BY-SA-4.0; v1.2.2; PIN `a3131740a39291e42fd15b9eac07e0b393ad71b1` | property catalog, generators และ counterexample triage สำหรับ Codex test-author ตาม contract | contract ของ pure risk/time/cost module + synthetic role/dependency-boundary spike ที่เจ้าของอนุมัติ | marketplace `trailofbits/skills` → `property-based-testing`; no copy; core ไม่มี tool allowlist; eval ขอ Write/acceptEdits, model service และ uv packages; ห้าม autorun helpers; F2/F3 และ pin verification ต้องผ่าน |
| `dimensional-analysis` — candidate; **SPIKE FIRST proposed** | Trail of Bits / Coriolan Pinhas & Benjamin Samuels; CC-BY-SA-4.0 (8 Solidity fixtures มี MIT SPDX); v3.1.0; PIN `a3131740a39291e42fd15b9eac07e0b393ad71b1` | ตรวจหน่วย USD/XAU, points, lots, เวลา และ scaling พร้อม annotations | synthetic Python/Decimal scratch contract ที่กำหนดขอบเขตการเขียนและ oracle อิสระ | marketplace `trailofbits/skills` → `dimensional-analysis`; no copy; Read/Write/Edit/Grep/Glob/Task/TodoWrite; eval เพิ่ม Bash/model service; serial writers; ไม่ใช้ตรง ๆ ใน read-only review; ไม่ติด slither-mcp; F4/F5 และ pin verification ต้องผ่าน |
| `supply-chain-risk-auditor` — **REJECT proposed at this pin** | Trail of Bits / Eric Quintero; CC-BY-SA-4.0; v2.0.4; PIN `a3131740a39291e42fd15b9eac07e0b393ad71b1` | deterministic package/advisory evidence เสริม dependency-admission | พิจารณาใหม่เมื่อ upstream revision แก้ credential/offline boundary และผ่าน source review ใหม่ | หากได้รับอนุมัติในอนาคตใช้ marketplace `trailofbits/skills` → `supply-chain-risk-auditor`, no copy; Read/Write/Bash/Glob/Grep, 8 API hosts + redirects + optional pip-audit; F6/F7/F8/F9 ยังเปิด; ห้าม install/run ณ pin นี้ |

**Draft DECISIONS entries:** none: no candidate has an ADMIT proposal. Do not manufacture an accepted/proposed “Add” decision for a rejected or spike-only candidate. An ADMIT reconsideration must include the exact new reviewed pin, permitted role/tools/data/network and an owner-proposed D-0xx entry before installation.

## Complete file-reading inventory

Every listed candidate file was read in full as UTF-8 by its assigned reader; truncated batches were split/reread. Counts are physical lines including blanks, not `Measure-Object -Line` counts. All files are ordinary tracked blobs (100644/100755), not symlinks/submodules. Tables are relative to each candidate root. Listed SVGs and fixtures were also inspected, not executed. Raw Windows checkout sizes are 97,804 / 190,365 / 243,960 bytes respectively (532,129 bytes total).

### property-based-testing — 41 files

| Path | Lines |
|---|---:|
| `.claude-plugin/plugin.json` | 9 |
| `README.md` | 130 |
| `evals-extra/01-roundtrip-codec.md` | 4 |
| `evals-extra/02-normalizer-idempotence.md` | 4 |
| `evals-extra/03-hypothesis-existing.md` | 4 |
| `evals-extra/04-echidna-invariant.md` | 4 |
| `evals-extra/05-review-weak-tests.md` | 4 |
| `evals-extra/07-fuzz-serializer-noname.md` | 4 |
| `evals-extra/08-sort-comparator.md` | 4 |
| `evals-extra/09-neg-libfuzzer-harness.md` | 4 |
| `evals-extra/10-neg-mutation-campaign.md` | 4 |
| `evals-extra/11-neg-flaky-ci.md` | 4 |
| `evals-extra/12-neg-crud-unit-test.md` | 4 |
| `evals-extra/13-neg-slither-scan.md` | 4 |
| `evals-extra/14-neg-benchmark.md` | 4 |
| `evals-extra/15-neg-pytest-setup.md` | 4 |
| `evals-extra/16-neg-e2e-playwright.md` | 4 |
| `evals-extra/effectiveness.sh` | 334 |
| `evals-extra/fixture/contracts/Staking.sol` | 7 |
| `evals-extra/fixture/requirements.txt` | 1 |
| `evals-extra/fixture/src/codec.py` | 19 |
| `evals-extra/fixture/src/money.py` | 9 |
| `evals-extra/fixture/tests/test_parser.py` | 17 |
| `evals-extra/run.sh` | 686 |
| `evals/02-neg-cargo-fuzz-coverage/graders/answers-on-its-own-terms.md` | 31 |
| `evals/02-neg-cargo-fuzz-coverage/graders/does-not-pivot-to-pbt.md` | 28 |
| `evals/02-neg-cargo-fuzz-coverage/graders/no-skill-invocation.md` | 7 |
| `evals/02-neg-cargo-fuzz-coverage/prompt.md` | 11 |
| `evals/03-dependency-is-users-call/graders/dependency-left-to-user.md` | 29 |
| `evals/03-dependency-is-users-call/graders/no-dependency-file-written.md` | 7 |
| `evals/03-dependency-is-users-call/graders/skill-fired.md` | 5 |
| `evals/03-dependency-is-users-call/prompt.md` | 30 |
| `skills/property-based-testing/README.md` | 279 |
| `skills/property-based-testing/SKILL.md` | 68 |
| `skills/property-based-testing/agents/openai.yaml` | 6 |
| `skills/property-based-testing/assets/trail-of-bits-mark.svg` | 1 |
| `skills/property-based-testing/references/generating.md` | 79 |
| `skills/property-based-testing/references/interpreting-failures.md` | 80 |
| `skills/property-based-testing/references/libraries.md` | 77 |
| `skills/property-based-testing/references/refactoring.md` | 120 |
| `skills/property-based-testing/references/reviewing.md` | 78 |

### dimensional-analysis — 43 files

| Path | Lines |
|---|---:|
| `.claude-plugin/plugin.json` | 10 |
| `README.md` | 120 |
| `agents/arithmetic-scanner.md` | 210 |
| `agents/dimension-annotator.md` | 300 |
| `agents/dimension-discoverer.md` | 221 |
| `agents/dimension-propagator.md` | 216 |
| `agents/dimension-validator.md` | 428 |
| `evals/planted-bugs/graders/criteria.md` | 36 |
| `evals/planted-bugs/prompt.md` | 34 |
| `evals/trigger-annotate/graders/criteria.md` | 7 |
| `evals/trigger-annotate/prompt.md` | 9 |
| `evals/trigger-audit/graders/criteria.md` | 7 |
| `evals/trigger-audit/prompt.md` | 9 |
| `evals/trigger-explicit/graders/criteria.md` | 7 |
| `evals/trigger-explicit/prompt.md` | 9 |
| `evals/trigger-oblique/graders/criteria.md` | 7 |
| `evals/trigger-oblique/prompt.md` | 9 |
| `skills/dimensional-analysis/SKILL.md` | 177 |
| `skills/dimensional-analysis/agents/openai.yaml` | 6 |
| `skills/dimensional-analysis/assets/trail-of-bits-mark.svg` | 1 |
| `skills/dimensional-analysis/references/annotate.md` | 321 |
| `skills/dimensional-analysis/references/bug-patterns.md` | 463 |
| `skills/dimensional-analysis/references/common-dimensions.md` | 248 |
| `skills/dimensional-analysis/references/dimension-algebra.md` | 272 |
| `skills/dimensional-analysis/references/step1.md` | 125 |
| `skills/dimensional-analysis/references/step2.md` | 59 |
| `skills/dimensional-analysis/references/step3.md` | 67 |
| `skills/dimensional-analysis/references/step4.md` | 149 |
| `tests/fixtures/ANSWER-KEY.md` | 147 |
| `tests/fixtures/selftest/findings-complete.json` | 49 |
| `tests/fixtures/src/AssetRegistry.sol` | 50 |
| `tests/fixtures/src/InterestIndex.sol` | 50 |
| `tests/fixtures/src/MarginVault.sol` | 140 |
| `tests/fixtures/src/StakingRewards.sol` | 117 |
| `tests/fixtures/src/UniV3Oracle.sol` | 51 |
| `tests/fixtures/src/libraries/FixedPointMath.sol` | 23 |
| `tests/fixtures/src/libraries/PriceLib.sol` | 28 |
| `tests/fixtures/trigger/src/Vault.sol` | 48 |
| `tests/smoke-test.sh` | 236 |
| `tests/summarize_arms.py` | 128 |
| `tests/trigger-test.sh` | 115 |
| `tests/validate_eval_result.py` | 49 |
| `tests/validate_findings.py` | 184 |

### supply-chain-risk-auditor — 20 files

| Path | Lines |
|---|---:|
| `.claude-plugin/plugin.json` | 9 |
| `README.md` | 67 |
| `evals/.gitignore` | 1 |
| `evals/evals.json` | 54 |
| `evals/fixtures/data-service/pyproject.toml` | 9 |
| `evals/fixtures/rusty-svc/Cargo.toml` | 8 |
| `evals/fixtures/shipping-api/package.json` | 13 |
| `skills/supply-chain-risk-auditor/SKILL.md` | 122 |
| `skills/supply-chain-risk-auditor/agents/openai.yaml` | 6 |
| `skills/supply-chain-risk-auditor/assets/trail-of-bits-mark.svg` | 1 |
| `skills/supply-chain-risk-auditor/scripts/collect.py` | 1568 |
| `skills/supply-chain-risk-auditor/scripts/model.py` | 402 |
| `skills/supply-chain-risk-auditor/scripts/pyproject.toml` | 20 |
| `skills/supply-chain-risk-auditor/scripts/render.py` | 809 |
| `skills/supply-chain-risk-auditor/scripts/sources.py` | 683 |
| `skills/supply-chain-risk-auditor/scripts/test_collect.py` | 913 |
| `skills/supply-chain-risk-auditor/scripts/test_model.py` | 274 |
| `skills/supply-chain-risk-auditor/scripts/test_render.py` | 385 |
| `skills/supply-chain-risk-auditor/scripts/test_sources.py` | 291 |
| `skills/supply-chain-risk-auditor/scripts/uv.lock` | 12 |

## Checks and evidence ledger

All timestamps use Asia/Bangkok (+07:00), 2026-10-21. LOCAL and PIN are the full commits defined above. Reading a command string inside candidate content is not counted as running that command.

| Command / procedure actually used | Result and scope | Commit | Time |
|---|---|---|---|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: clean start, existing task branch, LOCAL | LOCAL | 07:41:15 |
| `rg --files ...` / `rg -n ...` initial discovery | BLOCKED for this command only: rg unavailable (command-not-found). Complete discovery used ordinary PowerShell enumeration/search; no installation/config change. The audit itself was not blocked. | LOCAL | Initial batch before 07:41:15 |
| `git -C SOURCE rev-parse HEAD`; `remote get-url origin`; `ls-tree -r HEAD -- plugins/property-based-testing plugins/dimensional-analysis plugins/supply-chain-risk-auditor` | PASS: PIN/origin and complete candidate tree obtained offline | PIN | 07:41:15 |
| `Get-ChildItem -Recurse -Force -File`; numbered/chunked `Get-Content -LiteralPath ... -Encoding UTF8` for each inventory entry | PASS: PBT 41 files/2,208 lines; dimensional 43/4,942; supply-chain 20/5,647; every instruction/script included | PIN | 07:41:05–07:42:19 |
| `git -C SOURCE log --oneline -- plugins/<candidate>`; `log --format='%h %aI %s' -- ...` | PASS: local candidate history; no checkout/fetch | PIN | 07:41:15–07:42:19 |
| `git -C SOURCE hash-object --no-filters -- <path>`; `ls-files --eol -- LICENSE ...` | FAIL for raw-byte identity: CRLF checkout differs from LF Git blobs; identified EOL cause, did not modify files | PIN | 07:41:56–07:42:00 |
| Read-only PowerShell UTF-8 decode, CRLF→LF normalization, SHA-1 of `blob <byte-length>\0` plus LF bytes, compared with `git rev-parse HEAD:<path>` | PASS: 106/106 normalized blob matches (104 candidate files + LICENSE/README), no mismatch | PIN | 07:42:10 |
| Full root LICENSE and README reads; manifest/CODEOWNERS inspection | PASS: pinned license, attribution, per-file MIT fixture notices, versions/authors and documented marketplace method recorded | PIN | 07:41:15–07:43:02 |
| Candidate `Select-String` destination/permission scans plus full control-flow inspection | PASS for static inventory; includes dynamic URLs, redirects, subprocesses and fixture-only destinations; no assertion of bounded runtime egress | PIN | 07:41:57–07:43:11 |
| Focused numbered source reads of supply `collect.py`, `sources.py`, Windows tests and private-registry classification | PASS: F6/F7/F8/F9 evidence confirmed statically; no candidate execution | PIN | 07:42:36–07:45:20 |
| Final report/scope, red-flag and locked-path checks | See exact results below; inherited locked-path FAIL retained | FINAL + unstaged report | 07:46:17–07:46:25 |

The hash calculation above was reviewer-authored file-reading logic, not an import/execution of downloaded code. It normalized only in memory. The first rg discovery attempt produced “The term 'rg' is not recognized”; this was a missing convenience tool with a complete read-only fallback, not a blocked candidate read. No network/TLS attempt was made in r2.

## Final verification

| Command / procedure | Result | Commit / time (+07) |
|---|---|---|
| `bash scripts/controls/red-flags.sh main` | PASS, exit 0: **0 pattern groups** in tracked diff. Lists pre-existing AGENTS.md and the new H001 hypothesis as control-path changes; lists r2 as untracked and explicitly does not scan its content. | FINAL; 2026-10-21 07:46:17 |
| `node scripts/controls/check-locked-paths.mjs main` | **FAIL**, exit 1: `!! locked M AGENTS.md (agent instruction file)`; `Result: FAIL: 1 control change(s) need owner approval (PR label "owner-approved-control-change").` | FINAL; 2026-10-21 07:46:17 |
| `git status --short`; `git diff --name-only`; `git diff --cached --name-only` | PASS: only `?? docs/reviews/TOOLING-admission-r2.md`; tracked/staged working diffs empty. Codex has not staged the report. | FINAL; 2026-10-21 07:46:17 |
| `git log -4 --format='%H %aI %s'`; `git diff --stat LOCAL HEAD`; `git diff LOCAL HEAD -- PROGRESS.md`; `git branch --show-current` | PASS: reconciled the external PROGRESS-only commit and branch rename; no change to reviewed policy or candidate sources. | FINAL; 2026-10-21 07:46:25 |
| `git diff --no-index --check -- /dev/null docs/reviews/TOOLING-admission-r2.md` | Initial output reported a new blank line at EOF; corrected. Final standalone check: no whitespace diagnostics; exit 1 from the no-index comparison with an empty file (content differs), not a claimed exit-0 test. PASS for the narrow no-whitespace-diagnostic observation. | FINAL; initial 2026-10-21 07:46:17; final 07:47:27 |
| Final `git status --short`, tracked/staged diff names, branch/HEAD and UTF-8 report-tail read | PASS: only r2 remains untracked, no staged/tracked working changes, branch/HEAD still FINAL, Thai completion report readable. | FINAL; 2026-10-21 07:47:27 |
| PowerShell `ReadAllText` plus regex/count checks of the report; `git status --short`; `git diff --cached --name-only`; `git rev-parse HEAD` | PASS: 104 inventory rows, 0 trailing-whitespace lines, no extra final blank line or unresolved check placeholders; only r2 untracked and no staged file; HEAD still FINAL. | FINAL; 2026-10-21 07:47:44 |

The locked-path FAIL covers the branch's inherited history against local main at merge-base `45c1ea5` (18 commits / 14 paths), not an AGENTS.md edit by this reviewer. No label, environment override, config change, base substitution or bypass was used to make it pass. The owner/Claude must reconcile the intended PR base and existing approval evidence before delivery gates; this review cannot declare that gate green.

The red-flag script's zero groups are **not a content scan of this unstaged report**. Manual report inspection covers cited command/credential **names**, findings and license/source references only; no credential value or executed destructive action is present. The upstream-risk examples are evidence, not executable task instructions.

## Completion report

1. **Outcome for the user:** ได้ offline source admission review ครบสาม candidate พร้อม evidence, inventory, destinations/permissions, marketplace method และ draft registry rows; เสนอ SPIKE FIRST สำหรับ property-based-testing กับ dimensional-analysis และ REJECT supply-chain-risk-auditor ณ PIN ไม่มี ADMIT จึงไม่มี draft Add decision
2. **Acceptance status** (mapping ของคำขอรอบนี้ ไม่ใช่ contract ใหม่):

   | AC | Status | Evidence |
   |---|---|---|
   | AC-01 ยืนยัน source/pin และ inventory | PASS | PIN + 104-file inventory; 106/106 normalized blob identities รวม LICENSE/README |
   | AC-02 อ่านทุก instruction/script | PASS | Complete file-reading inventory และช่วงเวลาของผู้อ่านทั้งสาม |
   | AC-03 license/history ณ pin | PASS | Root LICENSE/README, MIT fixture notices, manifests/CODEOWNERS และ offline logs; live advisories ไม่ได้อยู่ใน claim นี้ |
   | AC-04 network/permissions/conflicts | PASS | Static inventories และ F2–F9; dynamic destinations ที่ source ไม่กำหนดระบุ UNKNOWN |
   | AC-05 วิเคราะห์ Windows + uv + Git Bash fit | PASS | ตาราง static fit พร้อมข้อจำกัด; runtime compatibility ยังคง UNKNOWN |
   | AC-06 ข้อเสนอ + marketplace method + draft rows/ADMIT decisions | PASS | สอง SPIKE FIRST หนึ่ง REJECT; registry drafts ครบ; ADMIT entry ไม่เกี่ยวข้อง; installation pin enforcement ยัง UNKNOWN |
   | AC-07 Thai owner summary และ Codex แก้ไฟล์เดียว unstaged | PASS | Final verification: r2 เป็น untracked, staged/tracked working diffs ว่าง; external PROGRESS commit แยกระบุไว้ |

3. **Checks run:** command → result → commit → time อยู่ใน evidence ledger และ Final verification; ไม่มี candidate runtime/test/install ถูกอ้างว่าผ่าน
4. **Files changed and why:** เพิ่ม `docs/reviews/TOOLING-admission-r2.md` เท่านั้นเพื่อแทนช่องว่าง evidence ของ r1 และส่งต่อ Claude; ไม่แก้ PROGRESS/registry/DECISIONS ตามขอบเขตคำสั่ง
5. **Red-flag scan hits and explanations:** scan exit 0, pattern groups 0 สำหรับ tracked diff; AGENTS.md/H001 เป็น control-path changes ที่มีอยู่ก่อน run นี้ และ r2 เป็น untracked จึงไม่ถูกสแกนเนื้อหา; locked-path check **FAIL** จาก AGENTS.md เดิมตาม output ด้านบน ไม่ได้แก้หรือ bypass
6. **Not tested:** candidate code/tests/self-tests/evals, installation/uninstallation, immutable marketplace/update behavior, current advisories, native Windows runtime/ACL, Python/Hypothesis/pytest compatibility, network/provider behavior และ broker/market/holdout ทั้งหมดไม่รันตาม scope; control self-test suite ไม่รันเพราะไม่มี control/code change
7. **Delivery state:** **implemented** เฉพาะรายงาน; static evidence ตรวจแล้วแต่ไม่ใช่ CI/owner acceptance, merged หรือ deployed; ปล่อย unstaged ให้ Claude ตรวจและ commit
8. **Remaining risks, follow-ups and next action:** Claude ตรวจ report และ commit ตามคำสั่งเจ้าของ พร้อม reconcile base/approval ของ locked-path FAIL ที่มีอยู่เดิม; เจ้าของเลือกว่าจะอนุมัติ bounded spike สำหรับสอง candidate แรกหรือไม่ ส่วน supply-chain pin นี้ไม่ควรติดตั้ง/รัน ให้พิจารณาใหม่เมื่อแก้ F6–F9 ใน revision ที่ตรวจใหม่; ก่อน installation ใด ๆ ต้องยืนยัน marketplace pin และสิทธิ์ที่อนุมัติ รายงานนี้ไม่มอบ install/run approval
