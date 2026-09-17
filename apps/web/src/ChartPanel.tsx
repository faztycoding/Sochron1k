import { useEffect, useMemo, useState } from "react";
import { ApiError, readJSON } from "./owner-api";
import { CandleCanvas } from "./CandleCanvas";
import { canvasCanPreservePrices, chartIsFresh, parseChart, periods, type AccountIdentity, type ChartView, type Timeframe } from "./chart-api";

const labels = {
  disabled: "ยังไม่ตั้งค่าช่องข้อมูลกราฟและช่วงเวลาของโบรกเกอร์",
  awaiting_snapshot: "รอแท่งเทียนจาก MT5 — ยังไม่มีข้อมูล",
  ready: "ข้อมูลล่าสุดจากช่อง MT5",
  stale: "ข้อมูลเก่า — ไม่ใช่ราคาปัจจุบัน",
  rejected: "ข้อมูลกราฟถูกปฏิเสธ — ห้ามใช้อ้างอิงการซื้อขาย",
};
export function ChartPanel({ token, identity }: { token: string | null; identity: AccountIdentity | null }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("M5");
  const [view, setView] = useState<{ data: ChartView; started: number; token: string; timeframe: Timeframe; identityKey: string } | null>(null);
  const [notice, setNotice] = useState("");
  const [now, setNow] = useState(() => performance.now());
  const [selectedTime, setSelectedTime] = useState("");
  // Identity is a primitive dependency; telemetry polling must not restart chart reads.
  const identityKey = identity ? JSON.stringify(identity) : "";
  useEffect(() => {
    setView(null); setNotice(""); setSelectedTime("");
    if (!token || !identityKey) return;
    const expectedIdentity = JSON.parse(identityKey) as AccountIdentity;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const clock = setInterval(() => setNow(performance.now()), 250);
    const poll = async () => {
      const started = performance.now();
      let retry = true;
      try {
        const data = parseChart(await readJSON(`/api/owner/chart/${timeframe}`, controller.signal, token, 262144), timeframe, expectedIdentity);
        if (controller.signal.aborted) return;
        setView({ data, started, token, timeframe, identityKey }); setNow(performance.now()); setNotice("");
      } catch (error) {
        if (controller.signal.aborted) return;
        setView(null);
        if (error instanceof ApiError && [401, 403].includes(error.status)) {
          retry = false; setNotice("ไม่มีสิทธิ์อ่านกราฟ กรุณาออกจากระบบแล้วเข้าสู่ระบบใหม่");
        } else setNotice("อ่านกราฟไม่ได้ ซ่อนข้อมูลแล้ว กำลังลองเชื่อมต่อใหม่");
      }
      if (retry && !controller.signal.aborted) timer = setTimeout(() => void poll(), 1000);
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); clearInterval(clock); };
  }, [token, identityKey, timeframe]);
  const current = view && view.token === token && view.timeframe === timeframe && view.identityKey === identityKey ? view : null;
  const elapsed = current ? Math.max(0, (now - current.started) / 1000) : 0;
  const data = current?.data;
  const fresh = data ? chartIsFresh(data, elapsed) : false;
  useEffect(() => {
    if (!current || current.data.state !== "ready" || !current.data.observation) return;
    const value = current.data;
    const remaining = Math.min(15 - (value.snapshot_age_seconds ?? 15),
      periods[current.data.observation.timeframe] - (value.latest_bar_age_seconds ?? Infinity),
      5 - (value.feed_status.price_age_seconds ?? 5), 5 - (value.feed_status.heartbeat_age_seconds ?? 5));
    const timer = setTimeout(() => setNow(performance.now()), Math.max(0, remaining * 1000 - (performance.now() - current.started)) + 1);
    return () => clearTimeout(timer);
  }, [current]);
  // A rejection is not a usable history view. The API may retain it for diagnostics.
  const observation = data && data.state !== "rejected" ? data.observation : null;
  const numericSafe = useMemo(() => observation ? canvasCanPreservePrices(observation) : false, [observation]);
  const bar = observation?.bars.find(item => item.open_time_utc === selectedTime) ?? observation?.bars.at(-1);
  return <section id="market-chart" className="panel chart-panel" aria-labelledby="chart-title">
    <div className="panel-heading chart-heading">
      <div><h2 id="chart-title">กราฟราคา {observation?.identity.symbol ?? "Demo"}</h2><p className="owner-subtitle">แท่งเทียนจาก MT5 · ไม่มีการเติมราคาที่หายไป</p></div>
      <div className="timeframe-controls" role="group" aria-label="ช่วงเวลาแท่งเทียน">
        {(Object.keys(periods) as Timeframe[]).map(item => <button key={item} type="button" aria-pressed={timeframe === item}
          onClick={() => setTimeframe(item)}>{item}</button>)}
      </div>
    </div>
    {!token || !identity ? <div className="chart-empty"><strong>รอยืนยันบัญชีเจ้าของและข้อมูล MT5</strong>
      <p>เข้าสู่ระบบในส่วนบัญชี Demo ก่อน กราฟจะปรากฏเมื่อได้รับแท่งเทียนที่ตรวจสอบแล้ว</p></div> :
      notice ? <p role="alert" className="chart-empty">{notice}</p> : !data ? <p role="status" className="chart-empty">กำลังอ่านกราฟ {timeframe}…</p> :
        <p role="status" className={fresh ? "quote-state is-fresh" : "quote-state"}>{data.state === "ready" && !fresh ? labels.stale : labels[data.state]}</p>}
    {observation && bar ? <>
      <div className={fresh ? "chart-plot" : "chart-plot chart-plot--stale"}>
        {numericSafe ? <CandleCanvas key={`${timeframe}:${observation.digits}:${observation.tick_size}`} observation={observation} /> :
          <p className="chart-empty">ความละเอียดราคาเกินขีดจำกัดของกราฟ อ่านค่าทศนิยมเต็มในตารางด้านล่าง</p>}
      </div>
      <p className="chart-legend">เขียว: ขึ้น · แดง: ลง · ทอง: ยังไม่ยืนยันปิด · แกนเวลา UTC</p>
      {observation.gaps.length ? <div className="chart-gap" role="note"><strong>มีช่วงข้อมูลขาด {observation.gaps.length} ช่วง — ยังไม่ทราบสาเหตุ</strong>
        <p>ช่องว่างบนกราฟเป็นเครื่องหมาย ไม่ใช่สัดส่วนระยะเวลา และไม่ใช่หลักฐานว่าตลาดปิด</p>
        <details><summary>ดูช่วงที่ขาด</summary><ul>{observation.gaps.map(gap => <li key={gap.after_open_time_utc}>
          {gap.after_open_time_utc} ถึง {gap.before_open_time_utc}: ขาด {gap.missing_intervals} แท่ง
        </li>)}</ul></details></div> : null}
      <label className="bar-selector">ตรวจค่าแท่งเทียน (UTC)
        <select value={bar.open_time_utc} onChange={event => setSelectedTime(event.target.value)}>
          {observation.bars.map(item => <option key={item.open_time_utc} value={item.open_time_utc}>
            {item.open_time_utc} · {item.closed ? "ปิดแล้ว" : "ยังไม่ยืนยันปิด"}
          </option>)}
        </select>
      </label>
      <p className="bar-state">{bar.closed ? "แท่งปิดแล้ว — มีแท่งถัดไปยืนยัน" : "ยังไม่ยืนยันปิด — ค่านี้ยังเปลี่ยนได้"}</p>
      <dl className="chart-values">{(["open", "high", "low", "close"] as const).map((key, index) => <div key={key}>
        <dt>{["เปิด (O)", "สูงสุด (H)", "ต่ำสุด (L)", "ปิดล่าสุด (C)"][index]}</dt><dd>{bar[key]}</dd>
      </div>)}</dl>
      <div className="observation-times">
        <span>Tick volume: {bar.tick_volume} · Spread: {bar.spread_points} points (ไม่ใช่ปริมาณซื้อขายจริง)</span>
        <span>เปิดแท่ง (กรุงเทพฯ): {new Date(bar.open_time_utc).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}</span>
        <span>แหล่งข้อมูล: {observation.source} · ฐานราคา: {observation.price_basis === "bid" ? "Bid" : "Last"}</span>
        <span>MT5 อ่านข้อมูล (UTC): {observation.observed_at}</span><span>API รับข้อมูล (UTC): {observation.received_time_utc}</span>
        <span>อายุ snapshot อย่างน้อย: {data?.snapshot_age_seconds === null ? "ไม่ทราบ" : `${((data?.snapshot_age_seconds ?? 0) + elapsed).toFixed(1)} วินาที`}</span>
      </div>
    </> : null}
    <p className="owner-hint">กราฟสำหรับติดตามข้อมูล ไม่ยืนยันความพร้อมส่งคำสั่ง · Auto Trading ปิด</p>
    <p className="chart-attribution"><a href="#bar-history">ดูประวัติแท่งปิดที่บันทึกไว้</a></p>
    <p className="chart-attribution">กราฟโดย <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView Lightweight Charts™</a> · <a href="/chart-notice.txt">ลิขสิทธิ์และใบอนุญาต</a></p>
  </section>;
}
