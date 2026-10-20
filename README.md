# Sochron1k

ระบบวิจัยและเทรดอัตโนมัติ XAU/USD บน MetaTrader 5 แบบ **Demo-only**
ผลลัพธ์ที่ต้องการคือหลักฐานว่ากลยุทธ์มีความได้เปรียบหลังหักต้นทุน ไม่ใช่จำนวนฟีเจอร์ (Handbook v5 บท 34)

**สถานะ: Bootstrap (BOOT-001)** · ยังไม่มีโค้ดแอป · สถาปัตยกรรม *proposed* (D-001) · SPEC ร่าง 0.1 รอเจ้าของรับรอง

## อ่านอะไรก่อน

| ไฟล์ | ใช้ทำอะไร | ใครอ่าน |
|---|---|---|
| [SPEC.md](SPEC.md) | โจทย์ ขอบเขต risk tier และคำถามที่ต้องตอบ | เจ้าของ (ทุกบรรทัด) |
| [docs/architecture.md](docs/architecture.md) | ทางเลือกสถาปัตยกรรม ข้อเสนอ module map และลำดับงาน | เจ้าของ, agents |
| [DECISIONS.md](DECISIONS.md) | การตัดสินใจ D-001 ถึง D-005 | เจ้าของ |
| [PROGRESS.md](PROGRESS.md) | สถานะล่าสุดและสิ่งที่ต้องทำต่อ | ทุกคน ทุก session |
| [AGENTS.md](AGENTS.md) | กติกาของ agent ทุกตัว (single source of truth) | agents, เจ้าของ |
| [docs/HANDBOOK-CORE.md](docs/HANDBOOK-CORE.md) | กฎแกนของ Handbook v5 ฉบับย่อ | agents |
| [docs/tooling/registry.md](docs/tooling/registry.md) | เครื่องมือ, skills, agents และ candidates | เจ้าของ |

## วงรอบงานหนึ่ง task (ทีม 2 agent)

| ขั้น | ใคร | คำสั่ง |
|---|---|---|
| 1. ร่าง contract + แผน แล้วเจ้าของอนุมัติ acceptance | Claude Code → คุณ | `/task-contract <งาน>` |
| 2. เขียน acceptance tests ที่ต้อง fail ก่อน | Codex (chat ใหม่) | `$write-acceptance-tests <ID>` |
| 3. ลงมือ + completion report + demo script + handoff | Claude Code | `/implement-task <ID>` |
| 4. Review เทียบ main | Codex (chat ใหม่, read-only) | `/review` แล้ว `$cross-agent-review <ID>` |
| 5. แก้ตาม finding ID แล้วให้ Codex ตรวจซ้ำเฉพาะ ID นั้น | Claude Code → Codex | `/fix-findings <ID>` |
| 6. CI ผ่าน, คุณทำ demo เอง, push และ merge | คุณ | – |
| 7. Checkpoint ก่อนจบ session | ผู้ทำ session | `/checkpoint` |

งานวิจัย: `/register-hypothesis` **ก่อน** backtest ทุกครั้ง, `$leakage-audit` ก่อนเชื่อตัวเลข
ติดปัญหา: `/debug-with-evidence` (ครบ 3 รอบโดยไม่มีหลักฐานใหม่ จะส่งต่อ second opinion อัตโนมัติ)
ไม่อ่านโค้ดก็ตรวจได้: `/explain-back` และ red-flag scan

## คำสั่งที่ตรวจแล้ว

```bash
bash scripts/controls/red-flags.sh main          # สัญญาณอันตรายใน diff (ทุก hit ต้องมีคำอธิบาย)
node scripts/controls/check-locked-paths.mjs main # locked / append-only paths
node scripts/controls/test-controls.mjs           # self-tests ของ hooks และกฎล็อก
```

คำสั่ง Python จะเพิ่มเมื่อ D-001 ได้รับการยอมรับและมีโค้ดจริงที่รันผ่าน

## โครงไฟล์ปัจจุบัน

```text
AGENTS.md, CLAUDE.md          กติกาของ agent (locked)
SPEC.md, DECISIONS.md, PROGRESS.md
docs/architecture.md          สถาปัตยกรรม (proposed)
docs/HANDBOOK-CORE.md         กฎแกน (locked)
docs/contracts/               BOOT-001, SPIKE-001, template
docs/handoff/ docs/reviews/   ส่งต่องานระหว่าง agent (templates)
docs/hypotheses/ docs/failures/ docs/tooling/
.claude/                      settings, hooks, skills (11), agents (4)  (locked)
.agents/skills/               Codex skills (10)  (locked)
.codex/config.toml            Codex sandbox/approval ของโปรเจกต์ (locked)
.github/                      CI (ci: self-tests; control-gate: locked-path gate from the base revision) + PR template (locked)
scripts/controls/             red-flags, locked-path check, self-tests (locked)
```

## แหล่งที่มา
- *Agentic Software Engineering Handbook* v5.0 (18 ต.ค. 2026): `Agentic_Software_Engineering_Handbook_v5.docx` ที่ root (ฉบับย่อสำหรับ agent: `docs/HANDBOOK-CORE.md`)
- งานรอบก่อนอยู่ใน git history ที่ `a3b3fbf` เป็นข้อมูลอ้างอิงเท่านั้น (D-003)
- คู่มือนี้และระบบนี้ไม่ใช่คำแนะนำการลงทุน
