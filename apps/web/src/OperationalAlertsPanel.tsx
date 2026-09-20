import { useEffect, useRef, useState } from "react";
import { ApiError, postJSON, readJSON } from "./owner-api";
import { alertDefinitions, alertKinds, parseAlertMutationReceipt, parseOperationalAlerts,
  type CoverageRuntime, type LifecycleState, type OperationalAlertInventory } from "./operational-alerts-api";

const runtimeLabels: Record<CoverageRuntime, string> = {
  connected: "อ่าน source ได้", awaiting_configuration: "รอตั้งค่า source",
  awaiting_source: "API พร้อม · รอข้อมูล", degraded: "source ต้องตรวจสอบ",
};
const severityLabels = { critical: "วิกฤต", warning: "เตือน", info: "ข้อมูล" } as const;
const lifecycleLabels: Record<LifecycleState, string> = {
  active: "ยังไม่รับทราบ", acknowledged: "รับทราบแล้ว · เหตุยัง active",
  cleared: "source ยืนยันว่าเหตุหายแล้ว", resolved: "ปิด workflow แล้ว",
  unavailable: "ยืนยัน lifecycle ไม่ได้",
};
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
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState("");
  const retryKeys = useRef(new Map<string, string>());
  const actionController = useRef<AbortController | null>(null);
  useEffect(() => {
    setView(null); setError(""); setActionError(""); setBusy(""); retryKeys.current.clear();
    actionController.current?.abort();
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

  const mutate = async (action: "acknowledge" | "resolve", conditionId: string) => {
    if (!token || busy) return;
    const keyName = `${action}:${conditionId}`;
    const idempotencyKey = retryKeys.current.get(keyName) ?? crypto.randomUUID();
    retryKeys.current.set(keyName, idempotencyKey);
    actionController.current?.abort();
    const controller = new AbortController(); actionController.current = controller;
    setBusy(keyName); setActionError("");
    try {
      const receipt = parseAlertMutationReceipt(await postJSON(
        `/api/owner/alerts/${conditionId}/${action}`, controller.signal, token, idempotencyKey,
      ));
      if (receipt.condition_id !== conditionId || receipt.action !== action) throw new Error("Mismatched receipt");
      const updated = parseOperationalAlerts(await readJSON(
        "/api/owner/alerts", controller.signal, token, 131072,
      ));
      retryKeys.current.delete(keyName); setView(updated);
    } catch (reason) {
      if (controller.signal.aborted) return;
      if (reason instanceof ApiError && reason.status < 500) retryKeys.current.delete(keyName);
      setActionError(action === "acknowledge"
        ? "บันทึกรับทราบไม่สำเร็จ · หากผลไม่ชัดเจน ปุ่มจะใช้ Idempotency-Key เดิมเมื่อลองอีกครั้ง"
        : "ปิด workflow ไม่สำเร็จ · server จะไม่ปิดเหตุที่ยัง active หรือ source ยังยืนยันไม่ได้");
    } finally {
      if (!controller.signal.aborted) setBusy("");
    }
  };

  const coverage = new Map(view?.coverage.map(item => [item.kind, item]));
  return <section id="operational-alerts" className="panel alerts-panel" aria-labelledby="alerts-title">
    <div className="panel-heading alerts-heading"><div><p>Owner operational lifecycle</p>
      <h2 id="alerts-title">ศูนย์แจ้งเตือนและตำแหน่ง API</h2>
      <p className="owner-subtitle">ตำแหน่ง API: <code>/api/owner/alerts</code> · lifecycle ใช้ POST <code>/acknowledge</code> และ <code>/resolve</code> โดยไม่แก้ source</p></div>
      <span className={`alerts-overall alerts-overall--${view?.status ?? "signed-out"}`}>
        {view?.status === "degraded" ? "มี source ต้องตรวจ" : view ? "บางระบบยังไม่ครบ" : "รอยืนยันเจ้าของ"}
      </span></div>
    {error ? <p role="alert" className="owner-message">{error}</p> : null}
    {actionError ? <p role="alert" className="owner-message">{actionError}</p> : null}
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
    {view ? <div className="active-alerts"><div className="active-alerts-heading"><h3>เหตุและประวัติ lifecycle</h3>
      <span>{view.alerts.length} รายการ · journal {view.lifecycle_runtime}{view.truncated ? " · รายการถูกจำกัด" : ""}</span></div>
      {view.alerts.length ? <ul>{view.alerts.map(item => <li className={`active-alert active-alert--${item.severity}`} key={item.id}>
        <div><span className="alert-severity">{severityLabels[item.severity]}</span><strong>{alertDefinitions[item.kind].title}</strong>
          <small>{detailLabels[item.detail_code]} · {sourceLabels[item.source]}</small>
          <span className={`alert-lifecycle alert-lifecycle--${item.lifecycle_state}`}>{lifecycleLabels[item.lifecycle_state]}</span></div>
        <div className="alert-time"><span>พบเหตุ UTC {item.observed_at_utc}</span><span>กรุงเทพฯ {bangkok(item.observed_at_utc)}</span>
          {item.acknowledged_at_utc ? <span>รับทราบ UTC {item.acknowledged_at_utc} · owner</span> : null}
          {item.resolved_at_utc ? <span>ปิด workflow UTC {item.resolved_at_utc}</span> : null}
          <div className="alert-actions">
            {item.acknowledge_allowed ? <button type="button" disabled={Boolean(busy)}
              onClick={() => void mutate("acknowledge", item.condition_id)}>
              {busy === `acknowledge:${item.condition_id}` ? "กำลังบันทึก…" : "รับทราบ"}
            </button> : null}
            {item.resolve_allowed ? <button type="button" disabled={Boolean(busy)}
              onClick={() => void mutate("resolve", item.condition_id)}>
              {busy === `resolve:${item.condition_id}` ? "กำลังปิด…" : "ปิด workflow"}
            </button> : null}
          </div></div>
      </li>)}</ul> : <p className="owner-hint">ยังไม่พบเหตุจาก source ที่เชื่อมอยู่ ข้อความนี้ไม่ครอบคลุม source ที่ยังไม่ได้ตั้งค่า</p>}
    </div> : <div className="owner-empty"><strong>เข้าสู่ระบบเจ้าของเพื่อดูเหตุที่ตรวจพบ</strong>
      <p>รายการ coverage ด้านบนแสดงตำแหน่งเชื่อมต่อได้เสมอ แต่ไม่สร้างเหตุจำลองระหว่างที่ยังไม่ยืนยันสิทธิ์</p></div>}
    <p className="alerts-note">ยังไม่มีการส่งอีเมล/ข้อความ · การรับทราบ/ปิดเหตุเป็น workflow ภายในของ owner ไม่ได้ยืนยันว่า MT5 หรือ source ฟื้นแล้ว · server ไม่อนุญาตให้ปิด safety condition ขณะยัง active · Auto Trading ปิด</p>
  </section>;
}
