# Review CORE-008 contract round 6 · v1.4 (scratch) · reviewer fresh-eyes-reviewer subagent (fresh context), narrow re-check of r5 F47

Label: pre-review (Claude subagent). r5 found that PROGRESS.md records no binding switch for CORE-008. I did not re-read PROGRESS.md this round. This round only re-checks r5's F47 and the edits made to close it.

- Contract: `C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/CORE-008-research.md`, v1.4 as edited after r5. ":NN" means line NN of that file.
- Previous round: `CORE-008-contract-r5.md` in the same scratchpad.
- The caller told me to read only these two files, so I did not read the repository working tree. I wrote nothing and ran no commands.
- I used the "Answers to contract reviews" row (:354) only to find the edit.

## Status of r5 findings

| r5 ID | Sev (r5) | Status | Evidence (current v1.4 wording) | Residual |
|---|---|---|---|---|
| F47 | Low | closed | **Rule, :238:** "ทุกส่วนของรายงาน ทั้งตาราง registry, "นับงบ", การตรวจ key และฐานของ Evaluation (F32, F45), บรรทัด setup/จำนวนชุดข้อมูล และ bullet ข้อจำกัด ใช้เฉพาะ record ที่ `hypothesis` ตรงกับ argument (record ของ hypothesis อื่นในไฟล์เดียวกันไม่ถูกอ่าน, F47)".<br>**Negative case, :253:** "registry ที่มี H001 และ H002 ปนกัน (ฐานที่ล็อกของ H001 ผ่าน, ฐานที่เป็น select ของ H002 → `ResearchError`, F47)", the proof of fix r5 asked for.<br>**Each part of render_report now reads only the argument's hypothesis:** the registry table counts (pairing still works because hypothesis is part of the identity, :127, :140); "นับงบ" (:240), matching runner step 5 (:137); the key check (:241) reads no records; the base check (:241) runs on H001 records only, matching runner step 5 (:137–138) — `run_id` hashes the hypothesis (:120), so an H002 select can never share a run_id with an H001 record, and every Evaluation has exactly one outcome; the setup line (:216) finds the base in the filtered set; the dataset-count line (:217) and the limitation bullets (:229–230) are filtered (sorted by the file-wide `seq`, so gaps from other hypotheses do not affect the order).<br>**Result:** both r5 triggers now have one answer. An H002 non-select line placed before H001's first line does not lock H001's base, so H001's locked base is accepted. An Evaluation based on an H002 select raises `ResearchError`. | Cosmetic only, no effect on tests: (1) :241 still says "ใน `records`" twice; :238 overrides it by naming F45, but :241 would read on its own with "ใน record ของ hypothesis นั้น". (2) :238 says "ในไฟล์เดียวกัน", but `records` is a Sequence, not a file. |

## New findings

None.

## AC status

| AC | Status | Why |
|----|--------|-----|
| AC-01–AC-05 | UNKNOWN | No code yet. The F47 edit does not touch them. |
| AC-06 | UNKNOWN | No code yet. The contract now has one reading: each part of render_report reads only the argument's hypothesis, and the mixed H001/H002 case has a stated outcome. |
| AC-07 | UNKNOWN | Nothing to run yet. |

## Checked, nothing found (and how)

- **The edit against runner step 5 (:137–144):** both count and lock per hypothesis. A registry the runner writes cannot contradict the report.
- **The edit against evaluate (:180):** evaluate already requires the same hypothesis on every input record, and it is unchanged. The filter cannot change a verdict, and it cannot show another hypothesis's verdict under "รายงานวิจัย H001". The H001 decision is not weakened.
- **The edit against RunRecord (:88, :96):** any non-empty ASCII hypothesis is still accepted, so a test author can build mixed fixtures with the RunRecord constructor. `render_report` takes a Sequence, so the fixture does not need a file.
- **The negative case "record ของ hypothesis อื่น" (:253):** :238 now defines the outcome (ignored, not an error), so it no longer competes with the new mixed case.
- **Report header (:203):** it uses the argument, not the records, so it is consistent.
- **Status (:4), DoR (:366) and the answers table (:354):** they agree with each other and with r5. Cosmetic: the text was edited after r5 but is still labelled v1.4, so "v1.4" names two texts; git history will separate them once the contract is committed. No test effect.

## Not checked (and why)

- `.agents/skills/cross-agent-review/SKILL.md` and the repository working tree: the caller limited this round to the two files above.
- Sections the F47 edit did not touch, except where read for contradictions with :238 and :253.
- Things that predate v1.4 and that no AC or negative case asks a test author to cover: `render_report` with an empty `hypothesis` argument; whether `render_report` cross-checks `Evaluation.dataset` against the base record; the order used for "บรรทัดแรก" when `records` is not in seq order.
- The normative example bytes and probes: no field, rule or example changed, so r4's results stand.
- `red-flags.sh` and pytest: there is no CORE-008 code or diff yet.

Ready for test authoring: yes
Findings open: 0
