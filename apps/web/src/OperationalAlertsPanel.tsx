import { useEffect, useState } from "react";
import { ApiError, readJSON } from "./owner-api";
import { alertDefinitions, alertKinds, parseOperationalAlerts, type CoverageRuntime,
  type OperationalAlertInventory } from "./operational-alerts-api";

const runtimeLabels: Record<CoverageRuntime, string> = {
  connected: "อ่าน source ได้", awaiting_configuration: "รอตั้งค่า source",
  awaiting_source: "API พร้อม · รอข้อมูล", degraded: "source ต้องตรวจสอบ",
};
const severityLabels = { critical: "วิกฤต", warning: "เตือน", info: "ข้อมูล" } as const;
const sourceLabels = {
  telemetry_bridge: "Telemetry bridge", execution_bridge: "Execution bridge",
  execution_journal: "Execution journal", policy_writer: "Policy writer",
  bar_history: "Bar history", api_budget: "API budget",
} as const;
const detailLabels: Record<string, string> = {
  entry_rejected: "คำสั่งเปิดถูกปฏิเสธ", management_rejected: "คำสั่งจัดการถูกปฏิเสธ",
  entry_unknown: "ผลคำสั่งเปิดยังไม่ทราบ", management_unknown: "ผลคำสั่งจัดการยังไม่ทราบ",
  open_volume_without_confirmed_sl: "มีปริมาณเปิดแต่ MT5 ยังไม่ยืนยัน SL",
  daily_halt: "หยุดตามเพดานรายวัน", total_halt: "หยุดตามเพดานการทดลอง",
  daily_and_total_halt: "หยุดทั้งรายวันและการทดลอง", price_or_heartbeat_stale: "ราคา/heartbeat เกินอายุ",
  telemetry_stale: "Telemetry เกินอายุ", telemetry_rejected: "Telemetry ถูกปฏิเสธ",
  execution_stale: "Execution inventory เกินอายุ", execution_rejected: "Execution inventory ถูกปฏิเสธ",
  policy_writer_degraded: "Policy writer ผิดปกติ", execution_journal_unavailable: "Execution journal อ่านไม่ได้",
  bar_history_unavailable: "คลังแท่งปิดอ่านไม่ได้", warning_70: "พื้นที่คลังถึง 70%",
  warning_85: "พื้นที่คลังถึง 85%",
};

function bangkok(value: string) {
  return new Date(value).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" });
}

export function OperationalAlertsPanel({ token }: { token: string | null }) {
  const [view, setView] = useState<OperationalAlertInventory | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setView(null); setError("");
    if (!token) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let retry = true;
      try {
        const data = parseOperationalAlerts(await readJSON("/api/owner/alerts", controller.signal, token, 131072));
        if (!controller.signal.aborted) { setView(data); setError(""); }
      } catch (reason) {
        if (controller.signal.aborted) return;
        setView(null);
        if (reason instanceof ApiError && [401, 403].includes(reason.status)) retry = false;
        setError("อ่านศูนย์แจ้งเตือนไม่ได้ ข้อมูลเหตุเดิมถูกซ่อน");
      }
      if (retry && !controller.signal.aborted) timer = setTimeout(() => void poll(), 5000);
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [token]);

  const coverage = new Map(view?.coverage.map(item => [item.kind, item]));
  return <section id="operational-alerts" className="panel alerts-panel" aria-labelledby="alerts-title">
    <div className="panel-heading alerts-heading"><div><p>Read-only operational inventory</p>
      <h2 id="alerts-title">ศูนย์แจ้งเตือนและตำแหน่ง API</h2>
      <p className="owner-subtitle">ตำแหน่ง API: <code>/api/owner/alerts</code> · รวมสถานะสำคัญโดยไม่ส่งคำสั่งหรือแก้ source</p></div>
      <span className={`alerts-overall alerts-overall--${view?.status ?? "signed-out"}`}>
        {view?.status === "degraded" ? "มี source ต้องตรวจ" : view ? "บางระบบยังไม่ครบ" : "รอยืนยันเจ้าของ"}
      </span></div>
    {error ? <p role="alert" className="owner-message">{error}</p> : null}
    {token && !view && !error ? <p role="status">กำลังรวมสถานะจาก source แบบ read-only…</p> : null}
    <div className="alert-coverage-key" aria-hidden="true"><span>เหตุที่ต้องเฝ้าระวัง</span><span>สถานะ source</span><span>API / แหล่งข้อมูล</span></div>
    <ol className="alert-coverage-list">{alertKinds.map((kind, index) => {
      const definition = alertDefinitions[kind]; const item = coverage.get(kind);
      return <li className="alert-coverage-row" key={kind}>
        <div className="alert-coverage-name"><span>{String(index + 1).padStart(2, "0")}</span><div>
          <strong>{definition.title}</strong><small>{kind}</small></div></div>
        <div><span className="alert-cell-label">สถานะ source</span>
          <span className={`alert-runtime alert-runtime--${item?.runtime ?? "signed-out"}`}>
            {definition.implementation === "missing" ? "ยังไม่มี cost source" : item ? runtimeLabels[item.runtime] : "เข้าสู่ระบบเพื่ออ่าน runtime"}
          </span></div>
        <div className="alert-location"><span className="alert-cell-label">API / แหล่งข้อมูล</span>
          {definition.routes.map(route => <code key={route}>{route}</code>)}<small>{definition.sourceLabel}</small></div>
      </li>;
    })}</ol>
    {view ? <div className="active-alerts"><div className="active-alerts-heading"><h3>เหตุที่ตรวจพบ</h3>
      <span>{view.alerts.length} รายการ{view.truncated ? " · รายการถูกจำกัด" : ""}</span></div>
      {view.alerts.length ? <ul>{view.alerts.map(item => <li className={`active-alert active-alert--${item.severity}`} key={item.id}>
        <div><span className="alert-severity">{severityLabels[item.severity]}</span><strong>{alertDefinitions[item.kind].title}</strong>
          <small>{detailLabels[item.detail_code]} · {sourceLabels[item.source]}</small></div>
        <div className="alert-time"><span>UTC {item.observed_at_utc}</span><span>กรุงเทพฯ {bangkok(item.observed_at_utc)}</span></div>
      </li>)}</ul> : <p className="owner-hint">ยังไม่พบเหตุจาก source ที่เชื่อมอยู่ ข้อความนี้ไม่ครอบคลุม source ที่ยังไม่ได้ตั้งค่า</p>}
    </div> : <div className="owner-empty"><strong>เข้าสู่ระบบเจ้าของเพื่อดูเหตุที่ตรวจพบ</strong>
      <p>รายการ coverage ด้านบนแสดงตำแหน่งเชื่อมต่อได้เสมอ แต่ไม่สร้างเหตุจำลองระหว่างที่ยังไม่ยืนยันสิทธิ์</p></div>}
    <p className="alerts-note">ยังไม่มีการส่งอีเมล/ข้อความ และยังไม่มีระบบบันทึกผู้รับทราบหรือเวลาปิดเหตุ · ฟิลด์ acknowledged_by / resolved_at จึงว่างตามจริง · Auto Trading ปิด</p>
  </section>;
}
