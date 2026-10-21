# Tool registry — Sochron1k

Handbook v5 บท 9 และภาคผนวก I: ทุก tool, skill, plugin และ MCP server ที่ใช้งานต้องอยู่ที่นี่พร้อมเจ้าของ สิทธิ์ และวันตรวจล่าสุด
สถานะ: **active** (ใช้อยู่) · **candidate** (ยังไม่ติดตั้ง รอ trigger + admission) · **rejected** · **disabled**
ตรวจล่าสุด: 2026-10-18 โดย Claude Code (BOOT-001) · เจ้าของ: เจ้าของ repository

## Active: runtimes and agents

| Tool | Version | Config / scope | Permissions and data sent | Last verified |
|---|---|---|---|---|
| Claude Code (VS Code extension) | 2.1.301 (`anthropic.claude-code-2.1.301-win32-x64`) | `CLAUDE.md` → `@AGENTS.md`; `.claude/settings.json` (deny/ask, hooks, `worktree.baseRef=head`); skills; agents | ส่ง code context ไป Anthropic · deny rules บังคับทุกโหมดรวม bypassPermissions · ask rules ไม่ถามในโหมด bypass | hooks: logic test PASS 2026-10-18 · runtime: ดู compatibility.md |
| Codex (VS Code extension) | `openai.chatgpt-26.1007.21434` | อ่าน `AGENTS.md` เอง; skills จาก `.agents/skills/`; `.codex/config.toml` (มีผลเมื่อ trust โปรเจกต์) | ส่ง code context ไป OpenAI · global `~/.codex/config.toml` ของเจ้าของ: model `gpt-6-astra`, reasoning `ultra`, `[windows] sandbox = "elevated"` | UNKNOWN: รอเจ้าของรัน P25 |
| GitHub Actions | `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1) | `ci.yml` (pull_request: self-tests และ red-flags ของโค้ดใน PR เป็นข้อมูลประกอบ) · `control-gate.yml` (pull_request_target: ตัวตรวจจาก base revision, PR เป็นแค่ข้อมูล, เป็น required check ที่เจ้าของต้องตั้ง) · ทั้งสองใช้ `contents: read` และไม่มี secrets | – | UNKNOWN: ยังไม่เคยรัน (ยังไม่มี push); control-gate มีผลตั้งแต่ PR ถัดจากที่เพิ่มมัน |
| Node.js | v26.12.0 (local) / ค่าเริ่มต้นของ runner `ubuntu-24.04` | สคริปต์ `scripts/controls/*.mjs` และ hooks | ไม่มี network | 2026-10-18 |
| Git / Git Bash | git 2.46.1, bash 5.2.32 | hooks รันผ่าน Git Bash บน Windows | – | 2026-10-18 |
| uv | 0.13.0 (มี CPython 3.12.15, 3.15.0) | ยังไม่ใช้จนกว่า D-001 จะ accepted | ดาวน์โหลดแพ็กเกจจาก PyPI เมื่อใช้ | 2026-10-18 |

## Active: project hooks (`.claude/hooks/`, rules in `scripts/controls/rules.mjs`)

| Hook | Event / matcher | Blocks | Failure mode |
|---|---|---|---|
| `protect-paths.mjs` | PreToolUse `Edit\|Write\|MultiEdit\|NotebookEdit` | locked paths, append-only registry, hypotheses ที่ commit แล้ว (รวมใน worktree) | fail closed (`onFailure: block`) |
| `guard-bash.mjs` | PreToolUse `Bash\|PowerShell\|Monitor` | push, reset --hard, clean, ข้าม hook, commit บน main, เขียน locked path, อ่าน credential, ลบ recursive นอกโปรเจกต์, DROP/TRUNCATE, pipe-to-shell · ตีความปลายทางจริง (ตั้งแต่ patch r1) (cd/pushd/subshell, copy เข้าโฟลเดอร์, redirect, output flags, การแตกไฟล์, เป้าหมายใน patch, nested shell, xargs) และ branch switch ภายในคำสั่ง | fail closed |
| `session-context.mjs` | SessionStart | – (พิมพ์ branch, HEAD, checkpoint ล่าสุด) | ไม่บล็อก |
| `check-locked-after.mjs` | PostToolUse + PostToolUseFailure `Bash\|PowerShell\|Monitor`; PreToolUse `--baseline` | ไม่บล็อกก่อน (ตรวจหลังรัน): รายงานการเปลี่ยน locked/append-only paths ที่ใหม่กว่าการตรวจครั้งก่อนใน session รวม commit ใหม่และไฟล์ locked ที่ git ignore (`settings.local.json`) แล้วสั่ง Claude หยุดแจ้งเจ้าของ · ย้อนการแก้ไม่ได้ | input อ่านไม่ได้หรือตรวจไม่สำเร็จ → รายงานให้เจ้าของรู้; โหมด `--baseline` ไม่บล็อกคำสั่ง |

Evidence: `node scripts/controls/test-controls.mjs` (28 tests, PASS 2026-10-19 ที่ `cca98c7` และ `5216ff4`) · `check-locked-after.mjs`: live ใน Claude Code 2.1.301 (ดู compatibility.md) แต่ยังไม่มี regression tests ถาวร ข้อจำกัด: เป็น heuristic จากข้อความคำสั่ง จึงมองไม่เห็นโปรแกรมที่เปิดไฟล์เอง (เช่น `python x.py`) ชั้นที่บังคับจริงคือ CI control-gate + การรับรองของเจ้าของ

## Active: project skills and agents (v1.0.0, owner: เจ้าของ repository, source: Handbook v5 Prompt Library)

| Name | Tool | Role | Handbook | Invoke |
|---|---|---|---|---|
| spec-interview | Claude Code | planner | P03, P01 | `/spec-interview` |
| architecture-options | Claude Code | planner | P04 | `/architecture-options` |
| task-contract | Claude Code | planner | P05, P06 | `/task-contract` |
| implement-task | Claude Code | implementer | P07, P14, P13, P30 | `/implement-task` |
| fix-findings | Claude Code | implementer | P28 | `/fix-findings` |
| debug-with-evidence | Claude Code | implementer | P08, P29 | `/debug-with-evidence` |
| checkpoint | Claude Code (ใช้ได้ทั้งสองฝั่ง) | session owner | P15, P16 | `/checkpoint save\|resume` |
| explain-back | Claude Code | implementer | P13 | `/explain-back` |
| register-hypothesis | Claude Code | planner (quant) | P31 | `/register-hypothesis` |
| failure-to-control | Claude Code | learning loop | P23 | `/failure-to-control` |
| verify-agent-setup | Claude Code | setup check | P25 | `/verify-agent-setup` (เรียกเองเท่านั้น) |
| write-acceptance-tests | Codex | test author | P26, P09 | `$write-acceptance-tests` |
| cross-agent-review | Codex | reviewer | P27, P10 | `/review` แล้ว `$cross-agent-review` |
| security-review | Codex | reviewer | P11 | `$security-review` |
| break-it-check | Codex | reviewer | P12 | `$break-it-check` |
| leakage-audit | Codex | reviewer (quant) | P32 | `$leakage-audit` |
| dependency-admission | Codex | reviewer | P17 | `$dependency-admission` |
| second-opinion | Codex | second opinion | P29 | `$second-opinion` |
| adversarial-design-review | Codex | reviewer | บท 2, 5, 6 | `$adversarial-design-review` |
| rules-review | Codex | weekly review | P24 | `$rules-review` |
| verify-agent-setup | Codex | setup check | P25 | `$verify-agent-setup` |
| fresh-eyes-reviewer | Claude subagent | pre-review | ใช้ `cross-agent-review` | Claude เรียกเอง หรือ "use the fresh-eyes-reviewer agent" |
| quant-auditor | Claude subagent | pre-review (quant) | ใช้ `leakage-audit` | เช่นเดียวกัน |
| security-reviewer | Claude subagent | pre-review | ใช้ `security-review` | เช่นเดียวกัน |
| second-opinion | Claude subagent (worktree) | second opinion | ใช้ `second-opinion` | ถูกเรียกจาก `debug-with-evidence` |

Evaluation: ยังไม่ได้ทำ trigger/behavior evals ของ skills (**SKIPPED**: ไม่มี eval harness และ Python บนเครื่อง) จะตรวจจาก P25, การใช้งานจริงใน task แรก และ `$rules-review` รายสัปดาห์

## MCP servers
ไม่มีสำหรับโปรเจกต์นี้ (ไม่มี `.mcp.json`) connectors ระดับผู้ใช้ใน Claude (เช่น Claude Docs, Gmail, Drive) ไม่ใช่ส่วนของโปรเจกต์ และห้ามใช้กับข้อมูลของโปรเจกต์โดยไม่เพิ่มรายการที่นี่และได้รับอนุมัติ

## Candidates (ยังไม่ติดตั้ง)
อ่านเฉพาะคำอธิบายจาก README หรือ marketplace แล้ว ยังไม่ได้อ่านทุกไฟล์ จึงต้องผ่าน `$dependency-admission` ก่อนติดตั้งตาม trigger

| Candidate | Publisher / license | ช่วยอะไร | Trigger ที่ควรพิจารณา | ข้อควรระวัง |
|---|---|---|---|---|
| `pyright-lsp` (claude-plugins-official) | Anthropic / Apache-2.0 (marketplace) | ให้ Claude เห็น type error ทันที จับ F04/F05 | D-001 accepted และเริ่มเขียน Python | ต้องติดตั้ง pyright |
| `astral` plugin: uv, ruff, ty + ty LSP | Astral (`astral-sh/claude-code-plugins`) / Apache-2.0 หรือ MIT | ความรู้ uv/ruff/ty ที่ตรงรุ่น + LSP | เช่นเดียวกัน | LSP เรียก `uvx` (ใช้ network) |
| `property-based-testing` v1.2.2 — **SPIKE FIRST อนุมัติโดยเจ้าของ 2026-10-21** | Trail of Bits (`trailofbits/skills`, pin `a3131740a39291e42fd15b9eac07e0b393ad71b1`) / CC-BY-SA-4.0 | property tests (Hypothesis) สำหรับ risk sizing และ invariants · review: `docs/reviews/TOOLING-admission-r2.md` (อ่านครบทุกไฟล์) | ทดลองแบบจำกัดเมื่อเริ่ม contract แรกของ timebase/costs/risk: ใช้โดย Codex ในบทบาท test author เท่านั้น · ไลบรารี Hypothesis ต้องผ่าน dependency admission แยก | ติดตั้งผ่าน marketplace จาก pin ไม่ copy เข้า repo (license SA) · ยังไม่ติดตั้ง · ผลทดลองตัดสิน ADMIT/REJECT |
| `mutation-testing` | Trail of Bits / CC-BY-SA-4.0 | ทำ break-it check (P12) ให้เป็นอัตโนมัติ | มี golden/acceptance tests ชุดแรก | – |
| `supply-chain-risk-auditor` v2.0.4 — candidate (Codex r2 เสนอ REJECT ที่ pin นี้; เจ้าของยังไม่ตัดสิน) | Trail of Bits / CC-BY-SA-4.0 (pin `a313174…`) | ตรวจความเสี่ยงของแพ็กเกจ PyPI (เสริม P17) | การรับ dependency ครั้งแรก | ใช้ network · review r2 พบว่า collector อ่าน token ผ่าน `gh auth token` แม้ใช้ `--offline` และอาจเรียก `pip-audit` ที่พบใน PATH · `$dependency-admission` ของ Codex ครอบคลุม PyPI อยู่แล้ว |
| `dimensional-analysis` v3.1.0 — candidate (Codex r2 เสนอ SPIKE FIRST; เจ้าของยังไม่ตัดสิน) | Trail of Bits / CC-BY-SA-4.0 (pin `a313174…`; fixture Solidity 8 ไฟล์เป็น MIT) | จับหน่วยปนกัน (ราคา, points, lots, สกุลเงินบัญชี) | งาน risk sizing / cost model | workflow ปกติแก้ comment ใน source แบบอัตโนมัติ จึงใช้ตรงๆ ใน review แบบ read-only ไม่ได้ ต้องทดลองบน synthetic code ก่อน |
| `agentic-actions-auditor` | Trail of Bits / CC-BY-SA-4.0 | ตรวจ GitHub Actions หาความเสี่ยงจาก AI agent | เมื่อ CI มีมากกว่า control-plane job | – |
| `security-guidance` (claude-plugins-official) | Anthropic | เตือนรูปแบบเสี่ยงขณะแก้โค้ด | ถ้า security finding เกิดซ้ำ | ซ้ำกับ red-flag scan บางส่วน |
| context7 MCP | Upstash (external) | ดึงเอกสารไลบรารีตามรุ่น | ถ้า F05 (ใช้ API ผิดรุ่น) เกิดซ้ำ | ส่ง query ออกภายนอก ต้องผ่าน MCP admission |
| OpenAI curated: `security-threat-model`, `gh-fix-ci`, `jupyter-notebook` | OpenAI (`openai/skills`) | threat model, แก้ CI, notebook สำรวจข้อมูล | งาน High / CI ล้ม / สำรวจข้อมูลใน R1 | เคยใช้ในรอบก่อน |

## Rejected

| Item | เหตุผล |
|---|---|
| `obra/superpowers` | workflow TDD ให้ implementer เขียน test เอง ซึ่งขัดกับ binding (Codex เขียน test, ล็อก test) |
| `DonCoyoteS/claude-mt5-trader` | เป็นระบบเทรดทั้งชุด รวม autonomous live trading ขัดกับ Demo-only และไม่ใช่ skill |
| Generic backtesting skills (`wshobson/agents` backtesting-frameworks, `jeremylongshore` backtesting-trading-strategies) | กว้างหรือผูกกับ yfinance เสี่ยงขัดกับ controls บท 34 (variant registry, holdout, random-entry) และยังไม่ได้ตรวจคุณภาพ |
