import { connectionDefinitions, connectionIds, type ConnectionMap as ConnectionData,
  type ConnectionNode, type RuntimeState } from "./connection-api";

export type ConnectionViewState =
  | { kind: "loading" }
  | { kind: "ready"; data: ConnectionData }
  | { kind: "error" };

const runtimeLabels: Record<RuntimeState, string> = {
  connected: "เชื่อมแล้ว",
  configured: "ตั้งค่า API แล้ว",
  awaiting_configuration: "รอตั้งค่า",
  awaiting_source: "API พร้อม · รอแหล่งข้อมูล",
  degraded: "ต้องตรวจสอบ",
  not_applicable: "ยังไม่มี API",
};

function nodeLabel(node: ConnectionNode | null, state: ConnectionViewState["kind"]): string {
  if (state === "loading") return "กำลังตรวจ";
  if (!node) return "ตรวจสถานะไม่ได้";
  if (node.implementation === "partial") return `${runtimeLabels[node.runtime]} · ยังมีส่วนที่ต้องสร้าง`;
  return runtimeLabels[node.runtime];
}

function nodeTone(node: ConnectionNode | null, state: ConnectionViewState["kind"]): string {
  if (state !== "ready" || !node) return "unknown";
  if (node.implementation === "missing") return "missing";
  if (node.implementation === "partial") return "partial";
  if (node.runtime === "connected" || node.runtime === "configured") return "ready";
  if (node.runtime === "degraded") return "degraded";
  return "waiting";
}

export function ConnectionMap({ state, onRetry }: { state: ConnectionViewState; onRetry: () => void }) {
  const nodes = state.kind === "ready" ? new Map(state.data.connections.map(node => [node.id, node])) : null;
  return <section id="api-connections" className="panel connection-panel" aria-labelledby="connection-title">
    <div className="panel-heading connection-heading">
      <div><h2 id="connection-title">แผนที่การเชื่อมต่อ API</h2>
        <p className="owner-subtitle">ตำแหน่งข้อมูลที่ต้องต่อเพื่อให้แต่ละส่วนบน UI แสดงครบ</p></div>
      <div className="connection-heading-actions">
        <span className={`connection-overall connection-overall--${state.kind}`} role="status">
          {state.kind === "ready" ? "อ่านสถานะจาก API" : state.kind === "loading" ? "กำลังอ่านสถานะ" : "อ่านสถานะไม่ได้"}
        </span>
        <button className="quiet-button" type="button" disabled={state.kind === "loading"} onClick={onRetry}>ตรวจการเชื่อมต่อใหม่</button>
      </div>
    </div>
    <div className="connection-key" aria-hidden="true">
      <span>ส่วนบน UI</span><span>Browser API</span><span>แหล่งข้อมูล</span><span>สถานะ</span>
    </div>
    <ol className="connection-rail">
      {connectionIds.map((id, index) => {
        const definition = connectionDefinitions[id];
        const node = nodes?.get(id) ?? null;
        return <li className="connection-row" key={id}>
          <span className="connection-node" aria-hidden="true">{index + 1}</span>
          <div className="connection-surface"><span className="connection-cell-label">ส่วนบน UI</span>
            <strong>{definition.title}</strong><small>{definition.result}</small></div>
          <div className="connection-routes"><span className="connection-cell-label">Browser API</span>
            {definition.routes.map(route => <code key={route}>{route}</code>)}
            {definition.required ? <code className="route-missing">ยังไม่มี {definition.required}</code> : null}</div>
          <div className="connection-source"><span className="connection-cell-label">แหล่งข้อมูล</span>
            <span>{definition.sourceLabel}</span></div>
          <div className="connection-status"><span className="connection-cell-label">สถานะ</span>
            <span className={`connection-state connection-state--${nodeTone(node, state.kind)}`}>
              {nodeLabel(node, state.kind)}
            </span></div>
        </li>;
      })}
    </ol>
    <p className="connection-note">เส้นทางที่ขึ้นว่า “ยังไม่มี” คือ API ที่ต้องสร้างต่อ ไม่ใช่ข้อมูลว่าง · ไม่มี route ใดในรายการนี้เปิดคำสั่งซื้อขายจากหน้าเว็บ</p>
  </section>;
}
