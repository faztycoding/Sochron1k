# Review BOOT-001 round 1 · base main (951ee98) + uncommitted working tree · reviewer Codex (ChatGPT)

> Provenance: written by the Codex reviewer and pasted into the Claude Code chat by the owner on
> 2026-10-18 at 19:56 (Asia/Bangkok). Saved verbatim below by Claude Code (the implementer), without
> edits, so the response can cite finding IDs. The reviewer re-checks in round 2 (`BOOT-001-r2.md`).

---

1. ผลประเมิน: Claude วางทิศทางได้ดี แต่ BOOT-001 ยังไม่ควรถือว่า verified ครับ จุดดีคือเน้นวิจัยก่อนเทรด ใช้ strategy ชุดเดียว แยกสมมติฐานกับข้อสรุป และมี tests ที่รันผ่านจริง 19/19 อย่างไรก็ตาม พบจุดที่ต้องแก้:
   - F1 — High: CI ตรวจตัวเองด้วยโค้ดจาก PR ที่ [ci.yml (line 38)](/C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/.github/workflows/ci.yml:38) การทดลองในสำเนาแยกพบว่าแก้ตัวตรวจให้คืน exit 0 แล้วผ่านได้โดยไม่มี approval และ tests เดิมยังผ่าน 19/19 ควรใช้ verifier จาก revision ที่เชื่อถือได้และป้องกัน workflow ด้วย พฤติกรรม checkout นี้ตรงกับ GitHub docs
   - F2 — High: สมมติฐานที่ commit แล้ว ยังแก้ย้อนหลังใน branch เดียวกันได้โดย CI ไม่จับ เพราะ [ตัวตรวจ:90 (line 90)](/C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/scripts/controls/check-locked-paths.mjs:90) ดู diff รวมเทียบ main จึงเห็นไฟล์เป็นเพียง “เพิ่มใหม่” ทดลองแล้วคืน exit 0 ต้องตรวจประวัติระหว่าง commits ด้วย
   - F3 — High: shell guard ยังปล่อยการเขียน locked paths เช่น cp /tmp/AGENTS.md . และ cd .claude && echo {} > settings.json ได้ exit 0 จาก [guard-bash.mjs (line 249)](/C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/.claude/hooks/guard-bash.mjs:249) ต้องคำนวณปลายทางจริงและจัดการการเปลี่ยน directory/branch ภายในคำสั่ง ทั้งหมดนี้ทดสอบด้วยข้อความจำลอง ไม่ได้รันคำสั่งอันตรายจริง
   - F4 — Medium: ฟันธงเรื่องเวลา MT5 เกินหลักฐาน [architecture:20 (line 20)](/C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/docs/architecture.md:20) ระบุว่าทั้งหมดเป็น server time ไม่ใช่ UTC แต่ MetaQuotes Python API docs ระบุ tick/bar เป็น UTC ควรแยกตาม API และให้ SPIKE ยืนยันพฤติกรรมจริงก่อนแปลง offset
   - F5 — Medium: งานถัดไปติดเงื่อนไขวนกัน [D-001 (line 13)](/C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/DECISIONS.md:13) ต้องรอผล SPIKE ก่อนรับรอง แต่ [SPIKE-001 (line 4)](/C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/docs/contracts/SPIKE-001-mt5-connectivity-time.md:4) ต้องรอ D-001 accepted ก่อนเริ่ม ต้องกำหนดลำดับอนุมัติใหม่ให้เดินได้จริง
2. Acceptance status
   AC	สถานะ	หลักฐาน
   01–03	UNKNOWN	logic tests ผ่าน แต่ยังไม่ได้ยืนยันครบใน session จริงของทั้งสองเครื่องมือ
   04–05	FAIL	F1–F3
   06	PASS	scan สำเนาไฟล์ข้อความ 56 ไฟล์สำเร็จ
   07	FAIL	scanner จับนิยาม regex ของตัวเอง ดู F6 ด้านล่าง
   08	FAIL	F4
3. Checks ที่รัน — วันที่ 18 ต.ค. 2026 เวลาไทย; ต้นฉบับ HEAD 951ee98 พร้อมไฟล์ใหม่ที่ยังไม่ commit
   Command / การตรวจ	ผล	Revision	เวลา
   node scripts/controls/test-controls.mjs	PASS 19/19	951ee98 + working tree	19:50
   node scripts/controls/check-locked-paths.mjs main	FAIL: พบ 40 control changes ตามคาด	เช่นเดียวกัน	19:50
   node --input-type=module - — hook payload probes	FAIL: คำสั่งที่ควรบล็อกได้ exit 0	เช่นเดียวกัน	19:53
   locked-path checker ใน fixtures	FAIL: ทั้งแก้ hypothesis และปิด verifier หลุดผ่าน	23b6c67, 95b8444	19:54
   bash scripts/controls/red-flags.sh main	BLOCKED: bash ไม่อยู่ใน PATH	ต้นฉบับ	19:50
   คำสั่ง scan เดิมผ่าน Git Bash absolute path	PASS การรัน; พบ 6 กลุ่ม	scratch c49b017 + staged snapshot	19:55
4. ไฟล์ที่เปลี่ยน: ไม่แก้ไฟล์ในโปรเจกต์ ไม่ commit; ใช้สำเนาชั่วคราวแยกสำหรับทดสอบ
5. Red flags: พบ 6 กลุ่มจากเอกสาร นิยามตัวตรวจ และ negative tests โดยมี F6 — Medium: [red-flags.sh (line 55)](/C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/scripts/controls/red-flags.sh:55) จับคำ service_role ใน regex ของตัวเองเป็น Possible secrets ทำให้ AC-07 ไม่ผ่าน ต้องแก้ false positive นี้โดยยังตรวจ secret จริงได้ ไม่พบ credential จริงจาก patterns ที่รัน
6. ยังไม่ได้ทดสอบ: GitHub CI/branch protection จริง, P25 ครบทั้งสองเครื่องมือ, MT5 และเนื้อหา handbook .docx ทั้งเล่ม นอกจากนี้ runtime ของแชทนี้เป็น danger-full-access/never ต่างจากค่าที่โปรเจกต์คาดไว้
7. Delivery state: implemented เท่านั้น ยังไม่ verified, merged หรือ deployed
8. ขั้นถัดไป: ให้ Claude แก้ F1–F6 พร้อม regression evidence แล้วตรวจซ้ำก่อนรับ BOOT-001 โดยเฉพาะ F1–F3 ซึ่งเป็นช่องโหว่ในระบบควบคุมที่งานนี้ตั้งใจสร้างครับ
