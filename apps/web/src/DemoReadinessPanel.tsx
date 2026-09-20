import { readinessGateDefinitions, readinessGateIds, type DemoReadiness,
  type ReadinessGateState } from "./demo-readiness-api";

export type DemoReadinessViewState =
  | { kind: "loading" }
  | { kind: "ready"; data: DemoReadiness }
  | { kind: "error" };

const stateLabels: Record<ReadinessGateState, string> = {
  missing: "ยังขาดข้อมูล",
  recorded: "บันทึกแล้ว",
  configured: "ตั้งค่าแล้ว",
  awaiting_source: "รอแหล่งข้อมูล",
  connected: "เชื่อมแล้ว",
  degraded: "ต้องตรวจสอบ",
  not_run: "ยังไม่ทดสอบ",
  not_authorized: "ยังไม่ได้อนุญาต",
  evidence_admitted: "รับหลักฐานแล้ว",
  evidence_failed: "หลักฐานไม่ผ่าน",
};

const overallLabels: Record<DemoReadiness["state"], string> = {
  awaiting_owner_inputs: "รอข้อมูลจากเจ้าของ",
  awaiting_runtime: "รอเชื่อม runtime",
  awaiting_target_evidence: "รอหลักฐานเครื่องเป้าหมาย",
  awaiting_operational_authorization: "รออนุญาตใช้งาน Demo",
  degraded: "พบสถานะที่ต้องตรวจสอบ",
};

function tone(state: ReadinessGateState | null): string {
  if (state === "connected" || state === "configured" || state === "recorded" ||
      state === "evidence_admitted") return "ready";
  if (state === "degraded" || state === "evidence_failed") return "degraded";
  if (state === "missing") return "missing";
  return "waiting";
}

export function DemoReadinessPanel({ state }: { state: DemoReadinessViewState }) {
  const gates = state.kind === "ready" ? new Map(state.data.gates.map(gate => [gate.id, gate])) : null;
  const remaining = state.kind === "ready" ? state.data.gates.filter(gate =>
    !["connected", "configured", "recorded", "evidence_admitted"].includes(gate.state)).length : readinessGateIds.length;
  const overall = state.kind === "ready" ? overallLabels[state.data.state] :
    state.kind === "loading" ? "กำลังอ่านสถานะ" : "ตรวจสถานะไม่ได้";

  return <section id="demo-readiness" className="panel readiness-panel" aria-labelledby="readiness-title">
    <div className="panel-heading readiness-heading">
      <div>
        <p>Demo admission ledger</p>
        <h2 id="readiness-title">สิ่งที่ต้องครบก่อนใช้งานเดโม่</h2>
        <p className="owner-subtitle">แยกข้อมูลที่ตั้งค่าแล้ว การเชื่อมต่อจริง และหลักฐานบนเครื่องเป้าหมาย</p>
      </div>
      <div className="readiness-overall" role="status">
        <strong>{overall}</strong>
        <span>{remaining} gate ยังไม่ครบ · Auto Trading ปิด</span>
      </div>
    </div>
    <div className="readiness-key" aria-hidden="true">
      <span>Gate</span><span>สถานะ</span><span>ตำแหน่ง API / แหล่งข้อมูล</span><span>สิ่งที่ต้องทำต่อ</span>
    </div>
    <ol className="readiness-list">
      {readinessGateIds.map((id, index) => {
        const definition = readinessGateDefinitions[id];
        const gate = gates?.get(id) ?? null;
        const label = state.kind === "loading" ? "กำลังตรวจ" : gate ? stateLabels[gate.state] : "ตรวจสถานะไม่ได้";
        return <li className="readiness-row" key={id}>
          <div className="readiness-name">
            <span className="readiness-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            <div><strong>{definition.title}</strong><small>{definition.detail}</small></div>
          </div>
          <div><span className="readiness-cell-label">สถานะ</span>
            <span className={`readiness-state readiness-state--${tone(gate?.state ?? null)}`}>{label}</span></div>
          <div className="readiness-location"><span className="readiness-cell-label">ตำแหน่ง API / แหล่งข้อมูล</span>
            {definition.routes.map(route => <code key={route}>{route}</code>)}
            <small>{definition.sourceLabel}</small>
          </div>
          <div className="readiness-action"><span className="readiness-cell-label">สิ่งที่ต้องทำต่อ</span>
            {definition.nextAction}</div>
        </li>;
      })}
    </ol>
    <p className="readiness-note">สถานะ “รับหลักฐานแล้ว” หมายถึงไฟล์ normalized ถูกตรวจและผูก revision ครบ ไม่ใช่การอนุมัติ release · หน้านี้ไม่มีคำสั่งซื้อขาย และ Auto Trading ยังปิด</p>
  </section>;
}
