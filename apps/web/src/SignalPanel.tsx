import { useEffect, useState } from "react";
import { ApiError, readJSON } from "./owner-api";
import { parseSignalEvidence, type SignalAction, type SignalEvidence, type SignalEvidenceView } from "./signal-api";

const actionLabels: Record<SignalAction, string> = { buy: "BUY", sell: "SELL", wait: "WAIT", block: "BLOCK" };
function bangkok(value: string) {
  return new Date(value).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" });
}
function SignalCard({ signal, now }: { signal: SignalEvidence; now: number }) {
  const expired = Date.parse(signal.expires_at_utc) <= now;
  return <article className="signal-card">
    <header><div><span className={`signal-action signal-action--${signal.action}`}>{actionLabels[signal.action]}</span>
      <strong>{signal.signal_id}</strong><small>{signal.setup_id}</small></div>
      <span className={`signal-validity${expired ? " signal-validity--expired" : ""}`}>{expired ? "หมดอายุแล้ว" : "ยังอยู่ในอายุสัญญาณ"}</span></header>
    <dl className="signal-values">
      <div><dt>Strategy</dt><dd>{signal.strategy.version_id}</dd><small>{signal.strategy.status}</small></div>
      <div><dt>Experiment</dt><dd>{signal.experiment.experiment_id}</dd><small>{signal.experiment.status}</small></div>
      <div><dt>Policy</dt><dd>{signal.experiment.policy_version}</dd></div>
      <div><dt>Code hash</dt><dd title={signal.strategy.code_hash}>{signal.strategy.code_hash.slice(0, 12)}…</dd></div>
    </dl>
    {signal.blocked_reason ? <p className="signal-reason"><strong>เหตุผล:</strong> {signal.blocked_reason}</p> :
      signal.action === "wait" ? <p className="signal-reason">WAIT นี้ไม่มีเหตุผลเพิ่มเติมที่ source บันทึกไว้</p> : null}
    <div className="signal-times">
      <span>ยืนยัน UTC <strong>{signal.confirmed_at_utc}</strong></span><span>กรุงเทพฯ <strong>{bangkok(signal.confirmed_at_utc)}</strong></span>
      <span>หมดอายุ UTC <strong>{signal.expires_at_utc}</strong></span><span>Data cutoff <strong>{signal.strategy.data_cutoff_utc}</strong></span>
    </div>
    <footer><span>หลักฐาน {signal.evidence_ids.length} รายการ</span>
      <span>{signal.evidence_ids.length ? signal.evidence_ids.join(" · ") : "source ไม่ได้แนบ evidence ID"}</span></footer>
  </article>;
}

export function SignalPanel({ token }: { token: string | null }) {
  const [view, setView] = useState<SignalEvidenceView | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    setView(null); setError("");
    if (!token) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let repeat = true;
      try {
        const data = parseSignalEvidence(await readJSON("/api/owner/signals", controller.signal, token, 262_144));
        if (!controller.signal.aborted) { setView(data); setError(""); setNow(Date.now()); }
      } catch (reason) {
        if (controller.signal.aborted) return;
        setView(null);
        if (reason instanceof ApiError && [401, 403].includes(reason.status)) repeat = false;
        setError("อ่านหลักฐานสัญญาณไม่ได้ ข้อมูลเดิมถูกซ่อนและไม่มีการสร้างสัญญาณทดแทน");
      }
      if (repeat && !controller.signal.aborted) timer = setTimeout(() => void poll(), 5000);
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [token, retry]);
  useEffect(() => {
    if (!view?.signals.length) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [view]);

  return <section id="signal-evidence" className="panel signal-panel" aria-labelledby="signal-title">
    <div className="panel-heading signal-heading"><div><p>Versioned decision evidence</p>
      <h2 id="signal-title">สัญญาณและเหตุผลที่ยืนยันแล้ว</h2>
      <p className="owner-subtitle">ตำแหน่ง API: <code>/api/owner/signals</code> · อ่านจาก owner RLS เท่านั้น</p></div>
      <span className="status-chip status-chip--muted">ไม่ใช่คำสั่งซื้อขาย</span></div>
    {!token ? <div className="owner-empty"><strong>เข้าสู่ระบบเจ้าของเพื่ออ่านสัญญาณ</strong>
      <p>หน้าเว็บไม่สร้าง BUY/SELL/WAIT เอง และไม่มีสิทธิ์ส่งคำสั่งไป MT5</p></div> : null}
    {token && !view && !error ? <p role="status">กำลังอ่านสัญญาณที่ยืนยันแล้ว…</p> : null}
    {error ? <div className="owner-empty"><p role="alert">{error}</p>
      <button className="quiet-button" type="button" onClick={() => setRetry(value => value + 1)}>ลองอ่านสัญญาณอีกครั้ง</button></div> : null}
    {view?.status.state === "awaiting_source" ? <div className="empty-state"><div className="empty-glyph" aria-hidden="true">↔</div>
      <strong>API พร้อม · รอ Strategy producer</strong><p>ต้องมีบริการคำนวณ PA01 จากแท่งปิดและเขียนหลักฐานลง Supabase ก่อน ส่วนนี้จึงจะแสดงรายการจริง</p></div> : null}
    {view?.status.state === "available" ? <><div className="signal-summary"><span>ล่าสุด {view.status.returned_count} รายการ · จำกัด {view.status.limit}</span>
      <span>อ่านเมื่อ UTC {view.read_at_utc}</span></div><div className="signal-list">
        {view.signals.map(signal => <SignalCard key={signal.signal_id} signal={signal} now={now} />)}
      </div></> : null}
    <p className="evidence-footnote">Signal ไม่ใช่ Order · ไม่ยืนยันกำไร · ต้องผ่าน risk, journal, executor และ MT5 แยกกันทุกครั้ง</p>
  </section>;
}
