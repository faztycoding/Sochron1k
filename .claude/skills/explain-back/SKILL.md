---
name: explain-back
description: Explains a Sochron1k change, branch or PR to the owner in plain Thai, without needing to read code. Covers what changes for the user, the step-by-step flow, where data and orders go, who can see or change what, what happens on network loss, duplicate actions or broker failure, what is not done or tested, and how to undo it. Use when the owner asks "อธิบายให้ฟัง", "สรุปให้เข้าใจง่าย", "explain back", "เปลี่ยนอะไรไปบ้าง", or before the owner approves a merge.
argument-hint: "[branch, PR or TASK-ID]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P13; ch.15 technique 7"
---

# Explain back for the owner

The owner checks quality through outcomes, not code. A plain explanation that contradicts the
contract is a finding. If an answer cannot be read from the real code or evidence, write
"ไม่ทราบ" instead of guessing.

## Answer in Thai, minimal jargon, in this order
1. **What changes for you**: what you can now see or do differently (1–3 lines).
2. **The flow, step by step**: you do X → the system does Y → data or orders go to Z. For trading
   paths, say when an order is sent, which checks run first (Demo-only, risk gate), and what MT5 confirms.
3. **Who can see or change what**, and what stops everyone else.
4. **When things go wrong**: internet drops; the same action happens twice; MT5 or the broker
   does not answer; prices are stale; the computer restarts mid-way.
5. **Not done, or not tested yet**: kept separate from "tested and failed".
6. **How to undo it**: revert the branch, turn off a flag, restore data. Note anything that cannot be undone.

Cite file paths or test names for each claim so the owner or a reviewer can check it.
