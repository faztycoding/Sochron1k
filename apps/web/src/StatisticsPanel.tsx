import { useEffect, useState } from "react";
import { ApiError, readJSON } from "./owner-api";
import { parseResearchStatistics, type EvaluationSplit, type ResearchEvaluation, type ResearchStatisticsView } from "./statistics-api";

const splitLabels: Record<EvaluationSplit, string> = {
  train: "Train · in-sample", validation: "Validation", test: "Test · out-of-sample",
  walk_forward: "Walk-forward", shadow_demo: "Shadow Demo",
};
function bangkok(value: string) {
  return new Date(value).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" });
}
function EvaluationCard({ item }: { item: ResearchEvaluation }) {
  const metric = item.metrics; const cost = item.cost_assumptions;
  return <article className="statistics-card">
    <header><div><span className={`split-badge split-badge--${item.split}`}>{splitLabels[item.split]}</span>
      <strong>{item.strategy.version_id}</strong><small>{item.strategy.status}</small></div>
      <span className="sample-badge">n = {metric.sample_size}</span></header>
    {item.split === "train" ? <p className="statistics-warning">ผลฝึกเป็น in-sample ไม่ใช่หลักฐานยืนยันนอกตัวอย่าง</p> : null}
    <dl className="statistics-values">
      <div><dt>Win rate</dt><dd>{metric.win_rate_pct}%</dd><small>{metric.wins} ชนะ · {metric.losses} แพ้ · {metric.breakeven} เสมอ</small></div>
      <div><dt>Expectancy</dt><dd>{metric.expectancy_r} R</dd><small>95% CI {metric.expectancy_r_ci95_low} ถึง {metric.expectancy_r_ci95_high} R</small></div>
      <div><dt>Net return</dt><dd>{metric.net_return_pct}%</dd><small>หลังต้นทุนตามสมมติฐานนี้</small></div>
      <div><dt>Max drawdown</dt><dd>{metric.max_drawdown_pct}%</dd><small>Profit factor {metric.profit_factor ?? "คำนวณไม่ได้"}</small></div>
    </dl>
    <div className="statistics-costs"><strong>สมมติฐานต้นทุน</strong>
      <span>Spread {cost.spread_points} points</span><span>Slippage {cost.slippage_points} points</span>
      <span>Commission {cost.commission_per_lot} {cost.currency}/lot</span>
      <span>Operating {cost.operating_cost_per_trade} {cost.currency}/trade</span><span>Swap {cost.swap_included ? "รวมแล้ว" : "ยังไม่รวม"}</span>
    </div>
    <div className="statistics-meta">
      <span>Dataset <code title={item.dataset_hash}>{item.dataset_hash.slice(0, 12)}…</code></span>
      <span>Code <code title={item.strategy.code_hash}>{item.strategy.code_hash.slice(0, 12)}…</code></span>
      <span>Data cutoff UTC <strong>{item.data_cutoff_utc}</strong></span><span>กรุงเทพฯ <strong>{bangkok(item.data_cutoff_utc)}</strong></span>
      {item.experiment ? <span>Experiment <strong>{item.experiment.experiment_id} · {item.experiment.status}</strong></span> : <span>ไม่ผูก Experiment</span>}
    </div>
  </article>;
}

export function StatisticsPanel({ token }: { token: string | null }) {
  const [view, setView] = useState<ResearchStatisticsView | null>(null);
  const [error, setError] = useState(""); const [retry, setRetry] = useState(0);
  useEffect(() => {
    setView(null); setError("");
    if (!token) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let repeat = true;
      try {
        const data = parseResearchStatistics(await readJSON("/api/owner/statistics", controller.signal, token, 262_144));
        if (!controller.signal.aborted) { setView(data); setError(""); }
      } catch (reason) {
        if (controller.signal.aborted) return;
        setView(null); if (reason instanceof ApiError && [401, 403].includes(reason.status)) repeat = false;
        setError("อ่านหลักฐานสถิติไม่ได้ ข้อมูลเดิมถูกซ่อนและไม่มีการประมาณค่าทดแทน");
      }
      if (repeat && !controller.signal.aborted) timer = setTimeout(() => void poll(), 10_000);
    };
    void poll(); return () => { controller.abort(); clearTimeout(timer); };
  }, [token, retry]);
  return <section id="research-statistics" className="panel statistics-panel" aria-labelledby="statistics-title">
    <div className="panel-heading statistics-heading"><div><p>Versioned research evidence</p>
      <h2 id="statistics-title">สถิติกลยุทธ์และความไม่แน่นอน</h2>
      <p className="owner-subtitle">ตำแหน่ง API: <code>/api/owner/statistics</code> · อ่านจาก owner RLS เท่านั้น</p></div>
      <span className="status-chip status-chip--muted">ไม่ใช่การรับประกันผลลัพธ์</span></div>
    {!token ? <div className="owner-empty"><strong>เข้าสู่ระบบเจ้าของเพื่ออ่านสถิติ</strong><p>หน้าเว็บไม่คำนวณผลลัพธ์หรือเลือกกลยุทธ์แทน research pipeline</p></div> : null}
    {token && !view && !error ? <p role="status">กำลังอ่าน evaluation ที่บันทึกแล้ว…</p> : null}
    {error ? <div className="owner-empty"><p role="alert">{error}</p><button className="quiet-button" type="button" onClick={() => setRetry(value => value + 1)}>ลองอ่านสถิติอีกครั้ง</button></div> : null}
    {view?.status.state === "awaiting_source" ? <div className="empty-state"><div className="empty-glyph" aria-hidden="true">%</div>
      <strong>API, Tick Replay และตัวประเมินพร้อม · รอข้อมูลย้อนหลัง</strong><p>ต้องจัดเตรียม bars, Bid/Ask ticks และ policy observations แบบ point-in-time ให้ replay สร้าง bundle ก่อนบันทึก evaluation ที่ระบุ dataset, split, sample size, uncertainty และต้นทุนครบ</p></div> : null}
    {view?.status.state === "available" ? <><div className="signal-summary"><span>ล่าสุด {view.status.returned_count} รายการ · จำกัด {view.status.limit}</span>
      <span>อ่านเมื่อ UTC {view.read_at_utc}</span></div><div className="statistics-list">{view.evaluations.map(item =>
        <EvaluationCard key={`${item.strategy.version_id}:${item.dataset_hash}:${item.split}:${item.data_cutoff_utc}`} item={item} />)}</div></> : null}
    <p className="evidence-footnote">Win rate ต้องอ่านคู่กับ n · Expectancy ต้องอ่านคู่กับ 95% CI · ผลย้อนหลังไม่ยืนยันผลอนาคตและไม่อนุมัติ strategy promotion</p>
  </section>;
}
