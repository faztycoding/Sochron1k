# TASK BOOT-001 — Project bootstrap: process rules, controls, skills, initial architecture

Version v1 · Owner: เจ้าของ repository · Parent: Handbook v5 "เริ่มโปรเจกต์ใหม่ใน 1 หน้า" ขั้น 1–4 · Tier **High** · Branch `chore/BOOT-001-project-bootstrap`
Status: draft (เขียนระหว่างทำงาน ตามคำขอของเจ้าของ "วาง architecture, ตั้ง project rule ตาม handbook, หา skill/agent") — **รอเจ้าของรับรอง**
Review r1 (Codex, `docs/reviews/BOOT-001-r1.md`): ยอมรับ F1–F6 ทั้งหมด คำตอบและหลักฐานอยู่ใน `docs/handoff/BOOT-001.md` · apply patch แล้ว (`cca98c7`, ตามคำสั่งเจ้าของ 2026-10-19) · รอ Codex review round 2

## Risk tier (Q1–Q6)
- Q1 no · Q2 no · Q3 no · Q4 no · Q5 no
- Q6 **yes**: ตั้ง hooks, permissions, CI checks และสิทธิ์ของ agent ทั้งหมด → High และเป็น task แยกของตัวเอง

## Goal / user outcome
เจ้าของได้ repository ที่พร้อมทำงานตาม Handbook v5 กับทีม 2 agent ประกอบด้วย กติกาที่ทั้ง Claude Code และ Codex โหลด, ตัวบังคับที่ agent แก้เองไม่ได้, skills/agents สำหรับวงรอบงานมาตรฐาน, SPEC และสถาปัตยกรรมฉบับร่างที่ติดป้ายสิ่งที่ยังไม่รู้ชัดเจน และ task ถัดไปที่ลงมือได้ทันทีเมื่อเจ้าของตัดสิน

## Current behavior and evidence
`main` @ `951ee98`: repository ว่าง (เหลือแค่ Handbook v5 .docx ที่ยังไม่ track)

## Scope
- In scope: Starter Kit ชุด Lite/Standard (ภาคผนวก A), AGENTS.md (B) + Agent roles (O), CLAUDE.md, `.claude/settings.json` + hooks, `.codex/config.toml`, CI control-plane job, red-flag scan, templates (D, E, G, H, I), SPEC ร่าง, architecture ร่าง (P04), ADRs, skills/agents, tool registry, contract ถัดไป (SPIKE-001)
- Exclusions: โค้ดแอป, การติดตั้ง dependency, การเชื่อม MT5, การ push, branch protection บน GitHub
- Allowed files: ทุกไฟล์ใหม่ใน repository นี้ (ไม่มีไฟล์เดิมให้แก้)

## Acceptance
- AC-01 Given เปิด repo ใน Claude Code และ Codex, When รัน P25 (`/verify-agent-setup`, `$verify-agent-setup`), Then ทั้งสองยกกฎจาก Agent roles ได้ตรงตัวอักษร และรายงานบทบาทตัวเองถูก
- AC-02 Given Claude Code ใช้ project settings, When พยายามเขียน locked path (เช่น `tests/acceptance/x`, `AGENTS.md`, `.claude/settings.json`), Then ถูกบล็อกด้วย deny rule หรือ hook
- AC-03 Given worktree ใต้ `.claude/worktrees/<name>`, When แก้ไฟล์ทั่วไปในนั้น, Then ทำได้ แต่ locked paths ใน worktree ยังถูกบล็อก
- AC-04 Given คำสั่ง shell ที่ push, reset --hard, clean -f, ข้าม hook, เขียน locked path, อ่าน .env, ลบแบบ recursive นอกโปรเจกต์ หรือ commit บน main, When Claude รัน, Then guard บล็อกและบอกเหตุผล ส่วนคำสั่งพัฒนาปกติผ่าน
- AC-05 Given PR ที่แก้ locked path หรือแก้ไฟล์ append-only, When CI รันโดยไม่มี label `owner-approved-control-change`, Then check ล้ม และเมื่อมี label ก็ผ่าน
- AC-06 Given diff ของ branch, When รัน `bash scripts/controls/red-flags.sh main`, Then แสดงทุกกลุ่มที่พบ และไม่ fail งาน
- AC-07 ไม่มี secret ในไฟล์ใดของ branch (red-flag กลุ่ม Possible secrets และ Secret-like value assigned ต้องว่าง)
- AC-08 SPEC.md และ docs/architecture.md ติดป้ายสมมติฐาน [A] / TBD ครบ ไม่มีค่าทางธุรกิจที่ agent เดาเอง และ ADR ทุกตัวที่ต้องให้เจ้าของตัดสินยังเป็น proposed

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01 | เจ้าของ + ทั้งสองเครื่องมือ | P25 ใน session ใหม่ของแต่ละเครื่องมือ → `docs/tooling/compatibility.md` | L4 |
| 02–04 | สคริปต์ + live test | `node scripts/controls/test-controls.mjs` (logic) + ลองเขียน locked path ใน session จริง | L2 (ในเครื่อง), L3 เมื่อ CI รัน |
| 05 | CI + สคริปต์ | `control-gate.yml` (pull_request_target, ตัวตรวจจาก base revision) ตั้งแต่ PR ถัดจาก BOOT-001 (PR ที่เพิ่ม gate นี้ถูกตัดสินโดยเจ้าของ); ในเครื่อง: tests F1/F2 ใน `test-controls.mjs` | L3 (CI) / L2 (ในเครื่อง) |
| 06–07 | สคริปต์ | `bash scripts/controls/red-flags.sh <base>` ใน scratch clone | L2 |
| 08 | เจ้าของ + Codex | อ่าน SPEC/architecture; `$adversarial-design-review` | L5 |

## Risk, data and external side effects
ไม่มี action ภายนอก (ไม่ push, ไม่เชื่อมโบรกเกอร์) ความเสี่ยงหลักคือ hook บล็อกงานปกติ (false positive) หรือมีช่องให้เลี่ยง ซึ่งรับมือด้วย test suite, CI และ D-004

## Authorization
เจ้าของขอให้ตั้งโปรเจกต์ (แชท 2026-10-18) การรับรองว่า controls ใช้ได้, การ merge และการเปิด branch protection เป็นของเจ้าของ

## Budget
1 session · ไม่มีค่าใช้จ่ายเพิ่ม

## Recovery
ทุกอย่างอยู่บน branch แยก ทิ้งได้ทั้งก้อน (`git switch main` แล้วลบ branch) หรือปิด hooks ชั่วคราวได้โดยเจ้าของ (แก้ `.claude/settings.json` เอง)

## Done scope
implementation (พร้อมตรวจ) → เจ้าของรับรอง + Codex review → merge โดยเจ้าของ
