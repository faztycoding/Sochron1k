import { useEffect, useState } from "react";
import { parseExecutionEvidence, type CommandState, type ExecutionEvidence } from "./execution-api";
import { ApiError, readJSON } from "./owner-api";

const stateLabels: Record<CommandState, string> = {
  created: "สร้างแล้ว", validated: "ผ่านกฎ", queued: "เข้าคิว", sent: "ส่งแล้ว",
  acknowledged: "MT5 รับทราบ", partially_filled: "Fill บางส่วน", filled: "Fill แล้ว",
  protection_failed: "ยืนยัน SL ไม่สำเร็จ", closing: "กำลังปิด", closed: "ปิดแล้ว",
  rejected: "ถูกปฏิเสธ", expired: "หมดอายุ", cancelled: "ยกเลิกแล้ว", unknown: "UNKNOWN · ต้อง reconcile",
};

function bangkok(value: string) {
  return new Date(value).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" });
}

function StateBadge({ state }: { state: CommandState }) {
  const danger = ["unknown", "protection_failed", "rejected"].includes(state);
  return <span className={`execution-state${danger ? " execution-state--danger" : ""}`}>{stateLabels[state]}</span>;
}

function CommandCard({ command }: { command: ExecutionEvidence["commands"][number] }) {
  return <article className="execution-command">
    <header><div><span>{command.side === "buy" ? "BUY" : "SELL"} · {command.symbol}</span>
      <strong>{command.command_id}</strong></div><StateBadge state={command.state} /></header>
    <dl className="execution-values">
      <div><dt>Volume ที่ journal บันทึก</dt><dd>{command.requested_volume}</dd></div>
      <div><dt>Order ticket</dt><dd>{command.order?.order_ticket ?? "ยังไม่มีหลักฐาน"}</dd></div>
      <div><dt>Position ID</dt><dd>{command.order?.position_id ?? "ยังไม่มีหลักฐาน"}</dd></div>
      <div><dt>Broker-side SL</dt><dd className={command.order?.stop_loss_confirmed ? "is-confirmed" : "is-unconfirmed"}>
        {command.order ? command.order.stop_loss_confirmed ? "MT5 ยืนยันแล้ว" : "ยังไม่ยืนยัน" : "ยังไม่มีหลักฐาน"}</dd></div>
    </dl>
    {command.order ? <div className="volume-strip" aria-label="ปริมาณสะสมที่ยืนยันแล้ว">
      <span>Fill <strong>{command.order.filled_volume}</strong></span><span>Pending <strong>{command.order.remaining_volume}</strong></span>
      <span>Cancel <strong>{command.order.cancelled_volume}</strong></span><span>Close <strong>{command.order.closed_volume}</strong></span>
    </div> : <p className="execution-empty">ยังไม่มี Order / Deal / Position ที่ journal ยืนยัน</p>}
    {command.order?.deals.length ? <p className="deal-line">Deal: {command.order.deals.map(item => item.deal_ticket).join(" · ")}</p> : null}
    {command.rejection ? <p className="execution-warning">ยืนยัน no-effect rejection: retcode {command.rejection.retcode} / external {command.rejection.retcode_external}</p> : null}
    {command.management.length ? <ul className="management-list">{command.management.map(item => <li key={item.command_id}>
      <span>{item.operation === "close" ? "Close" : "Cancel"} · {item.command_id}</span><StateBadge state={item.state} />
      <small>{item.outcome ? `ยืนยัน ${item.outcome.completed_volume} · คงเหลือ ${item.outcome.remaining_volume}` : "ยังไม่มี broker outcome"}</small>
    </li>)}</ul> : null}
    <footer><span>UTC {command.updated_at_utc}</span><span>กรุงเทพฯ {bangkok(command.updated_at_utc)}</span></footer>
  </article>;
}

export function ExecutionPanel({ token }: { token: string | null }) {
  const [view, setView] = useState<ExecutionEvidence | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setView(null); setError("");
    if (!token) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let retry = true;
      try {
        const data = parseExecutionEvidence(await readJSON("/api/owner/execution", controller.signal, token, 2_097_152));
        if (!controller.signal.aborted) { setView(data); setError(""); }
      } catch (reason) {
        if (controller.signal.aborted) return;
        setView(null);
        if (reason instanceof ApiError && [401, 403].includes(reason.status)) retry = false;
        setError("อ่านหลักฐานคำสั่งไม่ได้ ข้อมูลเดิมถูกซ่อนและไม่มีการ retry คำสั่งซื้อขาย");
      }
      if (retry && !controller.signal.aborted) timer = setTimeout(() => void poll(), 2000);
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [token]);

  const count = view?.commands.length ?? 0;
  return <section id="execution-evidence" className="panel execution-panel" aria-labelledby="execution-title">
    <div className="panel-heading execution-heading"><div><p>Read-only journal projection</p>
      <h2 id="execution-title">หลักฐานคำสั่งและการป้องกันสถานะ</h2>
      <p className="owner-subtitle">ตำแหน่ง API: <code>/api/owner/execution</code> · ไม่มีปุ่มส่งคำสั่งจากหน้าเว็บ</p></div>
      <span className="status-chip status-chip--muted">Auto Trading ปิด</span></div>
    {!token ? <div className="owner-empty"><strong>เข้าสู่ระบบเจ้าของเพื่ออ่านหลักฐาน</strong>
      <p>ส่วนนี้ไม่ใช้ข้อมูลจำลอง และไม่แสดง account, token หรือ filesystem path</p></div> : null}
    {token && !view && !error ? <p role="status">กำลังอ่าน journal แบบ read-only…</p> : null}
    {error ? <p className="owner-message" role="alert">{error}</p> : null}
    {view?.status.state === "disabled" ? <div className="owner-empty"><strong>API พร้อม · ยังไม่กำหนด execution journal</strong>
      <p>ต้องผูกไฟล์ SQLite ของ ExecutionService ด้วย <code>SOCHRON_EXECUTION_JOURNAL_PATH</code> ที่ฝั่ง API</p></div> : null}
    {view?.status.state === "unavailable" ? <div className="owner-empty"><strong>journal ใช้งานไม่ได้</strong>
      <p>ระบบปฏิเสธ source ที่ถูกสลับ เสียหาย หรือ schema ไม่ตรง และไม่สร้างฐานข้อมูลใหม่แทน</p></div> : null}
    {view?.status.state === "available" ? <>
      <div className="execution-summary"><span>แสดง {count} จาก {view.status.total_commands} คำสั่งล่าสุด</span>
        <span>{view.status.truncated ? "รายการเก่ากว่านี้ไม่อยู่ใน response" : "อ่านครบตาม journal ปัจจุบัน"}</span></div>
      {count ? <div className="execution-list">{view.commands.map(command => <CommandCard command={command} key={command.command_id} />)}</div> :
        <div className="empty-state"><div className="empty-glyph" aria-hidden="true">◎</div><strong>ยังไม่มีคำสั่งใน journal</strong>
          <p>ไม่มีการสร้าง Order / Deal / Position จำลองเพื่อเติมหน้าจอ</p></div>}
    </> : null}
    <p className="evidence-footnote">HTTP สำเร็จไม่ใช่ fill · UNKNOWN ต้อง reconcile · ถือว่า protected เมื่อ MT5 ยืนยัน SL เท่านั้น</p>
  </section>;
}
