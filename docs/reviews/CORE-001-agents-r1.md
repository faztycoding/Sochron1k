# Review CORE-001-agents round 1 · base b2eb69c · head working tree · reviewer Claude Code (Fable 5.1, fresh headless session)

Date: 2026-10-21 (+07). Branch: `chore/CORE-001-post-merge` (equal to `origin/main`).
HEAD: `b2eb69c07a553b30f293689edeaed55526c41c5d` (merge of PR #8, 2026-10-21 19:32:38 +07).
Reviewed artifact: the uncommitted `AGENTS.md` and `CLAUDE.md` after the implementer session applied
`docs/proposals/AGENTS-core001-phase.patch` (Codex proposal, D-006) with one standalone `git apply`.
Oracle: `docs/handoff/CORE-001.md:406-537` ("Post-merge proposal: AGENTS.md and CLAUDE.md phase text").

**Verdict: Ready to commit: yes. No findings.**
This verdict covers the two applied files and the appended handoff section only. It does not approve a
merge or the control-change label; `check-locked-paths` correctly stays FAIL until the owner labels the PR.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|

No confirmed findings and no unresolved questions; no severity assigned.

## AC status

The AC numbers map to the five checks in the review request, not to the CORE-001 module acceptance.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 tracked changes are exactly AGENTS.md, CLAUDE.md, docs/handoff/CORE-001.md | PASS | `git status --porcelain=v1 --untracked-files=all` lists only those three as ` M`; `git diff --stat`: AGENTS.md 19 (+14/-5), CLAUDE.md 3 (+1/-2), docs/handoff/CORE-001.md 132 (+132/-0). No untracked file (docs/proposals/ is ignored by `.gitignore:10`). Hunks of the two locked files are reproduced below. |
| AC-02 hashes match the handoff | PASS | All four post-apply values and the patch SHA256 equal `docs/handoff/CORE-001.md:417,424-425` (table below). HEAD blobs and the index are unchanged. |
| AC-03 `git apply -R --check` passes standalone | PASS | Exit 0, no output, 19:56:38 +07, run as one standalone command. Working tree = HEAD + patch, byte for byte. |
| AC-04 content is correct, no rule weakened, no authority widened | PASS | Every changed sentence traced to a source (table below). The verified Python command was rerun: 24 passed, 0 skipped, exit 0 at 19:56:44 +07. The removed CLAUDE.md sentence described the one-time live push completed 2026-10-20 21:24 +07 (`docs/handoff/BOOT-001.md:1520-1541`). |
| AC-05 nothing else changed in the two files | PASS | Line counts: AGENTS.md 166 -> 175 (= +14 -5), CLAUDE.md 30 -> 29 (= +1 -2). `git diff --word-diff=plain -U0` shows changed words only inside the six described edits. `git diff --check` exit 0. |

## Checked, nothing found (and how)

### Identity and scope

| Artifact | Expected (handoff) | Observed | Match |
|----------|--------------------|----------|-------|
| `AGENTS.md` SHA256 | `80d15603c78d6fcca2ce04cea090a52d89963337306aff04c091118829f1f538` | same (`sha256sum`, 19:56:15) | yes |
| `AGENTS.md` Git blob | `b6b321e14e9533e8e38037d38ffeb723838500d8` | same (`git hash-object AGENTS.md`, no `-w`) | yes |
| `CLAUDE.md` SHA256 | `ef1edf750c22876cab5a260a31c0e73dbb33bf82b4411a91c69939b76945e1eb` | same (`sha256sum`) | yes |
| `CLAUDE.md` Git blob | `2786fa48746ba2fe2ba07faf731ea68b3e1b8dea` | same (`git hash-object CLAUDE.md`) | yes |
| Patch SHA256 | `d1979d269bc960d7f48f423a3e9e7c9ef9ab3b4f3f40858075644531b3d573f7` | same (`sha256sum docs/proposals/AGENTS-core001-phase.patch`, 4500 bytes, regular file `-rw-r--r--`) | yes |
| Pre-apply `AGENTS.md` SHA256 (handoff line 420) | `d5fe0d89…c775f` | `git show HEAD:AGENTS.md \| sha256sum` = `d5fe0d89952075438a51d6fe72570267c1e7a9ab225c91d701276f8a9acc775f` | yes |
| Pre-apply `CLAUDE.md` SHA256 (handoff line 420) | `b47c048e…1632` | `git show HEAD:CLAUDE.md \| sha256sum` = `b47c048e2a8b6c1013a37ff5490a461d7cf1e69c3646a61bfc9773450c311632` | yes |

- Index and HEAD untouched: `git ls-files -s` and `git ls-tree HEAD` both give `100644 0764f4bf…` for AGENTS.md
  and `100644 dd08b545…` for CLAUDE.md; nothing is staged. The patch `index` lines name exactly these
  before-blobs and the observed after-blobs.
- Encoding of both targets: no CR byte (ripgrep count of `\r` = 0 in both files), no BOM (first bytes
  `23 20 41` and `40 41 47`), exactly one trailing LF (last bytes `6e 0a` and `2e 0a`).
- The patch file's hunks equal `git diff -- AGENTS.md CLAUDE.md` (same two files, same `index` lines,
  same +/- lines); the standalone reverse check proves byte equality rather than only hunk equality.

### Hunks of the two locked files (`git diff -- AGENTS.md CLAUDE.md`, 19:55)

AGENTS.md, hunk 1 (`@@ -11,8 +11,11 @@`), the Phase bullet:

```diff
-- Phase: architecture accepted. D-001 was accepted on 2026-10-21 (scope in DECISIONS.md D-001);
-  there is no application code yet. Write code only under an approved task contract, and add a
+- Phase: building the pure modules before ENV-1. D-001 was accepted on 2026-10-21
+  (scope in DECISIONS.md D-001); the first module, `sochron.timebase` (CORE-001), merged on
+  2026-10-21 with the project's first environment (D-012). Application code lives under
+  `src/sochron/`; tests under `tests/`.
+  Write code only under an approved task contract, and add a
```

AGENTS.md, hunk 2 (`@@ -22,19 +25,25 @@`), Stack and Verified commands:

```diff
-  `MetaTrader5` package (Windows-only wheels, cp310 to cp314), pytest, SQLite, Parquet. None is a
-  project dependency yet: each enters through the `dependency-admission` review and owner approval.
+  `MetaTrader5` package (Windows-only wheels, cp310 to cp314), pytest, SQLite, Parquet.
+  Project dependencies so far (D-012, 2026-10-21): `tzdata==2026.5` (runtime) and
+  `pytest==9.1.1` with its five transitives (dev), pinned in `pyproject.toml` and `uv.lock`.
+  `MetaTrader5`, SQLite and Parquet libraries are not project dependencies yet; each enters
+  through the `dependency-admission` review and owner approval.
 ...
-Only commands that ran successfully in this repository. Python commands are added once they exist and pass.
+Only commands that ran successfully in this repository.
 ...
+- Python tests:   uv run --offline pytest tests -q -p no:cacheprovider   (24 passed, 0 skipped on 2026-10-21; run from the repo root in Git Bash)
+- Patch checks:   git apply --check docs/proposals/<file>.patch   and   git apply -R --check docs/proposals/<file>.patch, each as one standalone command (F21)
 If a command fails for environment reasons, report BLOCKED with the output. Never change config to make it pass.
+The `bash …` commands assume Git Bash; from PowerShell call `C:/Program Files/Git/bin/bash.exe` explicitly (N2).
```

CLAUDE.md, the only hunk (`@@ -8,8 +8,7 @@`):

```diff
-  the owner. After the initial r9 owner application and fresh-session review, run the live push
-  in the owner's session and record the result and CI for that exact pushed head; no prompt is expected.
+  the owner.
```

### Content fact check, sentence by sentence

| Changed text | Source checked | Result |
|--------------|----------------|--------|
| "Phase: building the pure modules before ENV-1." | `docs/contracts/CORE-001-timebase.md:36,119` (every function pure; `CORE-` prefix is for the pure part: timebase, costs, risk); `docs/architecture.md:248-249` (ENV-1 is row 1c, SLICE-R1 starts only after ENV-1); PROGRESS.md next action names ENV-1 or CORE-002 as the next contract | Correct. The ENV-1 restrictions that follow the bullet are unchanged. |
| "the first module, `sochron.timebase` (CORE-001), merged on 2026-10-21" | `git log -1 --date=iso b2eb69c`: "Merge pull request #8 from faztycoding/feat/CORE-001-timebase", 2026-10-21 19:32:38 +0700; `git diff --name-only b2eb69c^1 b2eb69c` lists `src/sochron/timebase/*.py`; `src/sochron/core/__init__.py` is a docstring-only package ("CORE-001 needs none beyond the stdlib") | Correct: timebase is the only module with code. |
| "with the project's first environment (D-012)" | `DECISIONS.md:132-143` D-012 "dependency ชุดแรก … `pyproject.toml`/`uv.lock` ฉบับแรก", accepted 2026-10-21; commit `3da18d1` "chore(core-001): create the project environment per D-012" is inside PR #8 (`pyproject.toml`, `uv.lock` in the merge diff) | Correct. |
| "Application code lives under `src/sochron/`; tests under `tests/`." | `ls -R src tests`: `src/sochron/{__init__.py,core/,timebase/}`; `tests/{acceptance/CORE-001,architecture,golden/CORE-001,unit/timebase}`; `pyproject.toml:25-27` `testpaths = ["tests"]`, `pythonpath = ["src"]` | Correct. |
| "Project dependencies so far (D-012, 2026-10-21): `tzdata==2026.5` (runtime) and `pytest==9.1.1` with its five transitives (dev), pinned in `pyproject.toml` and `uv.lock`." | `pyproject.toml:7-19`: `dependencies = ["tzdata==2026.5"]`; dev group `pytest==9.1.1`, `colorama==0.4.6`, `iniconfig==2.3.1`, `packaging==26.3`, `pluggy==1.7.0`, `pygments==2.21.0` (five transitives); `uv.lock:6-99` carries the same seven versions; D-012 lists the same seven pins | Correct. |
| "`MetaTrader5`, SQLite and Parquet libraries are not project dependencies yet; each enters through the `dependency-admission` review and owner approval." | `pyproject.toml` has no other dependency; D-012 condition "เพิ่ม, ลบ หรือเปลี่ยน pin ใดๆ … ต้องผ่าน admission" | Correct; same claim as the replaced sentence, now with the admitted pins carved out. |
| "Only commands that ran successfully in this repository." (sentence "Python commands are added once they exist and pass." removed) | A Python command is now listed, so the placeholder sentence is spent | Consistent; the "only commands that ran successfully" rule is kept. |
| "Python tests: `uv run --offline pytest tests -q -p no:cacheprovider` (24 passed, 0 skipped on 2026-10-21; run from the repo root in Git Bash)" | Rerun by this reviewer from the repo root in Git Bash: `24 passed in 0.07s`, exit 0, 19:56:44-19:56:45 +07; `-q` output shows no skipped count, so 0 skipped; earlier record `docs/reviews/CORE-001-r3.md:200` on `bf0d504` | Correct. |
| "Patch checks: `git apply --check …` and `git apply -R --check …`, each as one standalone command (F21)" | `docs/reviews/BOOT-001-r9.md:55` F21 Low: combined inspection forms block; "Minimal fix is documentation: list `git apply -R --check <patch>` and `git apply --check <patch>` as standalone commands in AGENTS.md Verified commands"; this session: `-R --check` standalone passed 19:56:38, the chained form (`…; echo; date`) was blocked by guard-bash exactly as F21 describes; forward `--check` ran standalone in the repo per handoff line 480 (19:46:41) | Correct; the line is F21's own minimal fix. |
| "The `bash …` commands assume Git Bash; from PowerShell call `C:/Program Files/Git/bin/bash.exe` explicitly (N2)." | `docs/handoff/BOOT-001.md:57` N2 (bash not on PATH in Codex's PowerShell); `ls -la "/c/Program Files/Git/bin/bash.exe"` exists; handoff lines 521-522 show `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` ran PASS from PowerShell at 19:50:34 and 19:51:16 | Correct path and fact. See observation (a) below. |
| CLAUDE.md: removed "After the initial r9 owner application and fresh-session review, run the live push in the owner's session and record the result and CI for that exact pushed head; no prompt is expected." | `docs/handoff/BOOT-001.md:1520-1541`: the live push `git push origin HEAD:refs/heads/chore/BOOT-001-project-bootstrap` ran 2026-10-20 21:24 +07, no block or prompt, pushed head `2f2b6ca…`, CI `control-plane` success 21:25:34 +07 | Correct: a one-time step, completed and recorded. The preceding sentence "Labels and all other external writes stay with the owner." and the rest of the bullet are intact. |

### Authority and rule strength

- No sentence grants a new permission. The two new verified-command lines are a test run and two
  read-only inspection forms of `git apply`; D-006 already covers standalone `git apply` of
  `docs/proposals/` patches and the guard already requires inspection forms to be standalone (F21).
- Nothing in Authority, Never, Agent roles, Locked paths, Trading and research invariants, Security
  baseline, Tests and evidence, Conventions or Git changed (word diff is confined to the hunks above).
- The restrictions before ENV-1 (no holdout cut, no research ingestion, no strategy experiments) and
  the contract and dependency-admission requirements are preserved verbatim.
- The CLAUDE.md edit removes an instruction, not a restriction: "Labels and all other external writes
  stay with the owner", the force/deletion/multi-ref/main blocks and the named-remote form all remain.

### Checks run

All checks refer to HEAD `b2eb69c07a553b30f293689edeaed55526c41c5d` plus the uncommitted working tree.
Times are 2026-10-21, Asia/Bangkok (+07). Runtime: Windows 11; Git 2.46.1.windows.1; Git Bash 5.2.32;
Node.js v26.12.0; uv 0.13.0.

| Command / procedure | Result | Commit / artifact | Time (+07) |
|---------------------|--------|-------------------|------------|
| `git status --porcelain=v1 --untracked-files=all`, `git diff --stat`, `git rev-parse HEAD`, `git branch --show-current` | PASS: three ` M` paths, no untracked; 147(+)/7(-) over 3 files; HEAD `b2eb69c`; branch `chore/CORE-001-post-merge` | working tree | 19:55:04 |
| `git diff -- AGENTS.md CLAUDE.md` | PASS: two hunks in AGENTS.md, one in CLAUDE.md, as reproduced above | working tree | 19:55 |
| `sha256sum AGENTS.md CLAUDE.md docs/proposals/AGENTS-core001-phase.patch`; `git hash-object AGENTS.md`; `git hash-object CLAUDE.md`; `git ls-files -s`; `git ls-tree HEAD`; `git check-ignore -v` | PASS: all five hashes equal the handoff; index and HEAD blobs unchanged; patch ignored by `.gitignore:10` | working tree | 19:56:15 |
| `git apply -R --check docs/proposals/AGENTS-core001-phase.patch` (standalone) | PASS: exit 0, no output | working tree | 19:56:38 |
| `git show HEAD:AGENTS.md \| wc -l` vs `wc -l AGENTS.md` (and CLAUDE.md); `git diff --numstat`; `git diff --check`; `git diff --word-diff=plain --word-diff-regex='[^[:space:]]+' -U0 -- AGENTS.md CLAUDE.md` | PASS: 166->175 and 30->29; numstat 14/5, 1/2, 132/0; `--check` exit 0; word changes only inside the described edits | working tree | 19:56:38 |
| `uv run --offline pytest tests -q -p no:cacheprovider` (repo root, Git Bash) | PASS: `24 passed in 0.07s`, exit 0 | working tree | 19:56:44-19:56:45 |
| `git log -1 --date=iso b2eb69c`; `git diff --name-only b2eb69c^1 b2eb69c`; `git log origin/main -- pyproject.toml uv.lock`; `ls -R src tests` | PASS: facts in the table above | `b2eb69c` | 19:57 |
| `head -c 3 \| od`, `tail -c 2 \| od` on both targets; ripgrep count of `\r` | PASS: no BOM, no CR, one trailing LF | working tree | 19:57 |
| `bash scripts/controls/red-flags.sh main` | PASS execution, exit 0; one pre-existing pattern group (`type: ignore` x4 in the already-merged `tests/unit/timebase/test_timebase_unit.py`, explained in `docs/reviews/CORE-001-r3.md`); control files listed include the merged pyproject/lockfile/tests because local `main` (`20b7c64`) is behind `origin/main` | working tree | 19:58:52-19:58:53 |
| `node scripts/controls/check-locked-paths.mjs main` | **FAIL** (expected), exit 1: 5 control changes need the owner label; three are the already-merged Codex test files, two are AGENTS.md and CLAUDE.md | working tree | 19:58:55 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS, exit 0: zero pattern groups; changed files AGENTS.md, CLAUDE.md, docs/handoff/CORE-001.md; control files AGENTS.md, CLAUDE.md | working tree | 19:59:14 |
| `node scripts/controls/check-locked-paths.mjs origin/main` | **FAIL** (expected), exit 1: 2 control changes (AGENTS.md, CLAUDE.md) need the owner label `owner-approved-control-change` | working tree | 19:59:15 |
| `git show HEAD:AGENTS.md \| sha256sum`; `git show HEAD:CLAUDE.md \| sha256sum` | PASS: equal the handoff's pre-apply values (line 420) | `b2eb69c` | 19:58:55 |

### Hook events during this review (recorded, none hidden)

1. PostToolUse `check-locked-after.mjs` on the first (read-only) command reported "protected files
   changed since the previous check: uncommitted M AGENTS.md, M CLAUDE.md". The report contains
   exactly the two target files of the proposal patch just applied, which is the one case CLAUDE.md
   allows to continue after verifying every expected SHA256 and Git blob against the handoff. All
   matched (table above), so the review continued. No later report appeared.
2. PreToolUse `guard-bash.mjs` blocked the hashing command in its `node -e` form: "inline node code
   references a locked path (agents.md). Use the Read tool to read files; locked paths are
   owner-only." The review request listed `sha256sum` as the alternative method in advance, so the
   hashes were taken with `sha256sum` and `git hash-object`. This is reported here for the owner,
   because the standing N6 rule has no listed exception for this exact block; if the owner does not
   accept the request's pre-listed alternative as authorization, treat it as a process deviation to
   record, not as a defect in the patch (the result is identical to the handoff either way).
3. PreToolUse `guard-bash.mjs` blocked `git apply -R --check …; echo "exit=$?"; date …`: "git apply
   must be one standalone literal command." Rerun alone under the owner-granted standalone-rerun
   exception (2026-10-20, F21); passed. This block is itself evidence for the new "Patch checks" line.

### Observations (not findings, no change requested)

- (a) The N2 line names the bash path but not the PowerShell call form; the invocation that actually
  ran in PowerShell is `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main`
  (quotes and `&` are needed because the path contains a space). The sentence is not wrong; a future
  proposal could add the `&` form if PowerShell users trip on it.
- (b) "24 passed, 0 skipped on 2026-10-21" is a dated count; it will need a new proposal when the next
  module adds tests. That is the same convention the handoff and PROGRESS use.
- (c) Local `main` is at `20b7c64`, behind `origin/main` (`b2eb69c`), so the two verified `… main` scans
  include the merged CORE-001 files. Running them against `origin/main` shows only this change.
  Fast-forwarding local `main` is the owner's call; nothing in this review depends on it.

## Not checked (and why)

- `node scripts/controls/test-controls.mjs`: not requested, no hook, settings, control script or test
  changed by this patch, and the suite takes about three minutes. The guard behaviour that matters
  here (F21 standalone rule) was exercised live instead.
- CI, the PR label and the merge: owner gates; the locked-path FAIL above is a tested result.
- The implementer's own `git apply` command and the patch bytes before it ran: this session sees the
  post-apply state only. The patch file's current SHA256 equals the handoff, and the standalone
  reverse check proves working tree = HEAD + patch, which makes the pre-apply state derivable.
- The handoff's temporary-copy procedure (`--git-dir`/`--work-tree` apply) was not reproduced; it is
  superseded by the in-repository reverse check.
- The forward `git apply --check` was not rerun: it necessarily fails once the patch is applied. Its
  standalone PASS at 19:46:41 is recorded in the handoff (line 480).
- No dependency, broker, MT5 or research action: none is in scope and none was performed.

Only `docs/reviews/CORE-001-agents-r1.md` was written by this reviewer. Nothing was staged, committed,
pushed or edited elsewhere. Next step for the implementer session: commit `AGENTS.md`, `CLAUDE.md`,
`docs/handoff/CORE-001.md` and this review under the D-006 flow; the owner labels the PR after CI.

Ready to commit: yes
