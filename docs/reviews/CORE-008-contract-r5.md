# Review CORE-008 contract round 5 · v1.4 (scratch) · reviewer fresh-eyes-reviewer subagent (fresh context), narrow re-check of r4 F43-F46

Label: pre-review (Claude subagent). PROGRESS.md records no binding switch for CORE-008. This is a contract re-check done before any tests exist, limited to r4's F43–F46 and to anything the v1.4 edits touch.

- Contract: `C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/CORE-008-research.md`, v1.4. ":NN" means line NN of that file.
- Previous round: `CORE-008-contract-r4.md` in the same scratchpad.
- Repository: `feat/CORE-007-backtest` at `8e24be4`, working tree clean. I wrote nothing in the repository and needed no scratch files.
- I read no implementer reasoning. I used the "Answers to contract reviews" rows (:350–353) only as a map.

## Status of r4 findings

| r4 ID | Sev (r4) | Status | Evidence (v1.4 wording) | Residual |
|---|---|---|---|---|
| F43 | Low | closed | **Runner, :144:** "ผลรวมต่อ variant ของจำนวน params select ที่ต่างกัน (คีย์ = variant + params: ค่าตั้งต้นของ A, B และ C จึงนับเป็น 3 ชุด, F43) + บรรทัด started ของ robustness + บรรทัด started ของ stress ≤ 63".<br>**Report, :240:** "นับงบ" uses the same per-variant sum.<br>**Consistency:** :141 counts distinct params per variant. The per-row "งบ" cell for select (:239) is per variant, so the three select cells add up to the select part of :240. H001 §4 says "3 โครงสร้าง × ไม่เกิน 6 ชุดต่อโครงสร้าง", which matches 18 + 30 + 3 = 51 in D10 (:289). AC-02 and AC-06 now have one reading. | D10 (:289) still says only "select (ชุด)". The normative text at :144 governs, so this is cosmetic. |
| F44 | Low (q) | closed as recorded | **(ก), :297** requires the rule to name the validation Dataset; a select on any other Dataset is not an eligible base. **(ง), :301** proposes one select per variant in the holdout file, with frozen params and the screen file's setup, enforced in the acquisition-host contract. Both sit under :296 as the owner's own decisions before SLICE-R1. :296 and :351 say they do not block this task. No CORE-008 behaviour changed, so a test author has nothing to encode. | Not enforced in code until the owner decides (ก) and the acquisition-host contract adopts (ง). Expected. |
| F45 | Low | closed, with a new gap (F47) | **New rule, :241:** `Evaluation.base_run_id` must be the run_id of an ok select line of that variant in `records`, and if `records` has a non-select started line of that variant, it must equal the base that first line fixed (runner step 5), else `ResearchError`. **Negative case, :253.** Consistent with runner step 5 (:138): both key on the first non-select started line of the variant. r4's trigger is now refused. If the variant has only select lines, any ok select is accepted, but evaluate can then give only stop or insufficient, so go cannot be produced by choosing the base. | The rule does not say which hypothesis's records it reads (F47). AC-06 does not name render_report's `ResearchError` cases; this predates v1.4 and :253 lists them, so no finding. |
| F46 | Low | closed | **List, :88:** "sizer_label เป็น str ASCII ไม่ว่าง (F46) และ error เป็น ASCII", matching the table (:107). **Negative case, :253.** By :87 an empty sizer_label is a value error (`ResearchError`), and `read_records` of such a line raises `ResearchError` with the line number (:128). | Cosmetic: the case sits in the render_report group of :253. |

## New findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F47 | Low | confirmed | v1.4:241 vs :238, :137, :88, :253 | The new F45 rule reads all of `records` ("ใน `records`" twice, no hypothesis filter), while :238 limits only counting to the argument's hypothesis. Runner step 5, cited in :241, is per hypothesis (:137). RunRecord accepts any non-empty ASCII hypothesis (:88) and :253 lists "record ของ hypothesis อื่น" as a render_report negative case, so a mixed-hypothesis file is an expected fixture, buildable through `append_record`. | A registry where an H002 robustness started line for B (on H002's ok select Z) precedes H001's first robustness line for B on base X; `render_report(records, {"B": eval_X}, hypothesis="H001")`. Reverse: H001 has no non-select line for B and the Evaluation's base is H002's ok select of B. | Whole-file reading: the correct H001 report raises `ResearchError`, and the reverse case is accepted showing H002's verdict. Per-hypothesis reading: the opposite. Both faithful to the text, so a test locks in a guess. H001 itself is not at risk (`run_variant` writes "H001"). | At :238 (or :241): "ทุกส่วนของรายงาน รวมการตรวจฐานของ Evaluation (F45) ใช้เฉพาะ record ที่ hypothesis ตรงกับ argument". This also settles the limitation bullets (:229–230). | A render_report negative case with a mixed H001/H002 registry: the H001 Evaluation on H001's locked base is accepted; an Evaluation whose base is an H002 select ok raises `ResearchError`. |

## AC status
| AC | Status | Why |
|----|--------|-----|
| AC-01 | UNKNOWN | No code yet. The `__post_init__` list now matches the table for sizer_label. |
| AC-02 | UNKNOWN | No code yet. The 63 cap has one reading. |
| AC-03 | UNKNOWN | Not touched by v1.4. |
| AC-04 | UNKNOWN | Not touched by v1.4. |
| AC-05 | UNKNOWN | Not touched by v1.4. |
| AC-06 | UNKNOWN | Settled: the "รวมที่นับงบ" golden (3/63 at the A, B and C defaults) and the locked-base check. Open: whether the base check reads one hypothesis or the whole file (F47). |
| AC-07 | UNKNOWN | Standard command; nothing to run yet. |

## Checked, nothing found (and how)
- **F43 arithmetic:** 18 select + 30 robustness (10/8/12) + 3 stress = 51 ≤ 63, matching D10, Plan 5 (ค) and H001 §4. A select re-run cannot raise a distinct-params count.
- **F45 against the runner:** the first non-select started line fixes the base in both :138 and :241; failed or interrupted lines also fix it. A runner-made file can never hold two bases for one variant. The key check and the base check both raise `ResearchError`, so their order does not matter.
- **F45 against evaluate:** evaluate is unchanged; the restriction lives only in render_report. Withholding inputs for the locked base can turn go into stop, never stop into insufficient.
- **F46:** list, table and negative case agree.
- **F44 has no code effect.**
- **Cosmetic, no test effect:** the Status line (:4) and the DoR line (:365) did not mention r4 or v1.4.

## Not checked (and why)
- Sections that v1.4 did not edit, beyond reading them for contradictions with the four edits.
- The normative example bytes and probes: v1.4 changed no field, rule or example, so r4's results stand.
- `red-flags.sh` and pytest: no CORE-008 code or diff yet.
- The owner's future content for (ก) and (ง).

Ready for test authoring: no
Findings open: 1

F47 needs a one-phrase edit at :238 or :241, and a re-check can be limited to F47.
