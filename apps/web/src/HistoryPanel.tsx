import { useEffect, useState } from "react";
import { periods, type AccountIdentity, type Timeframe } from "./chart-api";
import { historyPageSize, historyPath, parseHistory, type HistoryCursor, type HistoryPin, type HistoryRequest, type HistoryView } from "./history-api";
import { ApiError, readJSON } from "./owner-api";

const bangkok = (value: string) => new Date(value).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" });
type Query = { request: HistoryRequest; earlier: HistoryCursor[] };
export function HistoryPanel({ token, identity }: { token: string | null; identity: AccountIdentity | null }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("M5");
  const identityKey = identity ? JSON.stringify(identity) : "";
  return <section id="bar-history" className="panel history-panel" aria-labelledby="history-title">
    <div className="panel-heading chart-heading">
      <div><h2 id="history-title">ประวัติแท่งปิด</h2><p className="owner-subtitle">ข้อมูลที่บันทึกไว้ ไม่ใช่ราคาปัจจุบัน</p></div>
      <div className="timeframe-controls" role="group" aria-label="ช่วงเวลาประวัติ">
        {(Object.keys(periods) as Timeframe[]).map(item => <button key={item} type="button" aria-pressed={timeframe === item}
          onClick={() => setTimeframe(item)}>{item}</button>)}
      </div>
    </div>
    {token ? <HistoryWorkspace key={JSON.stringify([token, identityKey, timeframe])} token={token} identityKey={identityKey} timeframe={timeframe} /> :
      <p className="owner-hint">เข้าสู่ระบบและยืนยันสิทธิ์เจ้าของก่อนอ่านประวัติ</p>}
  </section>;
}

// Keyed scope destroys private rows, selection and cursors synchronously on account/session/TF changes.
function HistoryWorkspace({ token, identityKey, timeframe }: { token: string; identityKey: string; timeframe: Timeframe }) {
  const initial = (): Query => ({ request: { timeframe, identity: identityKey ? JSON.parse(identityKey) : null, after: 0 }, earlier: [] });
  const [query, setQuery] = useState<Query>(initial);
  const [result, setResult] = useState<{ query: Query; data?: HistoryView; error?: "denied" | "failed" } | null>(null);
  const [selection, setSelection] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const data = parseHistory(await readJSON(historyPath(query.request), controller.signal, token, 131072), query.request);
        if (!controller.signal.aborted) setResult({ query, data });
      } catch (error) {
        if (!controller.signal.aborted) setResult({ query, error: error instanceof ApiError && [401, 403].includes(error.status) ? "denied" : "failed" });
      }
    })();
    return () => controller.abort();
  }, [query, token]);
  const current = result?.query === query ? result : null;
  const data = current?.data;
  const bar = data?.bars.find(item => item.time_server_s === selection) ?? data?.bars[0];
  function navigate(direction: "next" | "previous") {
    if (!data?.archive_id || !data.identity) return;
    const pin: HistoryPin = query.request.pin ?? { archive: data.archive_id, receipt: data.through_receipt,
      identity: data.identity, offset: data.bars[0]?.broker_utc_offset_seconds };
    const last = data.bars.at(-1);
    const cursor = direction === "next" && last ? { after: last.time_server_s, previousUTC: last.open_time_utc } : query.earlier.at(-1);
    if (!cursor) return;
    setSelection(0); setResult(null);
    setQuery({ request: { ...query.request, ...cursor, pin }, earlier: direction === "next" ?
      [...query.earlier, { after: query.request.after, previousUTC: query.request.previousUTC }] : query.earlier.slice(0, -1) });
  }
  return <div className="history-workspace">
    <div className="history-toolbar">
      <p>หน้า {query.earlier.length + 1} · เก่าไปใหม่ · สูงสุด {historyPageSize} แท่งต่อหน้า</p>
      <div className="history-actions">
        <button className="quiet-button" disabled={!data || !query.earlier.length} onClick={() => navigate("previous")}>หน้าก่อน</button>
        <button className="quiet-button" disabled={!data || data.bars.length !== historyPageSize} onClick={() => navigate("next")}>หน้าถัดไป</button>
        <button className="quiet-button" disabled={!current || current.error === "denied"} onClick={() => { setResult(null); setSelection(0); setQuery(initial()); }}>อ่านชุดล่าสุด</button>
      </div>
    </div>
    {!current ? <p role="status">กำลังอ่านประวัติ {timeframe}…</p> : current.error ? <div>
      <p role="alert">{current.error === "denied" ? "ไม่มีสิทธิ์อ่านประวัติ กรุณาออกจากระบบแล้วเข้าสู่ระบบใหม่" :
        "อ่านประวัติไม่ได้ ซ่อนข้อมูลแล้ว ตรวจการเชื่อมต่อหรืออ่านชุดล่าสุดหากคลังเปลี่ยน"}</p>
      {current.error === "failed" ? <button className="quiet-button" onClick={() => { setResult(null); setQuery({ ...query }); }}>ลองอ่านหน้าเดิมอีกครั้ง</button> : null}
    </div> : null}
    {data?.state === "disabled" ? <p role="status">ยังไม่เปิดการบันทึกประวัติที่ API ต้องตั้งค่าคลังส่วนตัวก่อน</p> : null}
    {data?.state === "available" ? <>
      <p className="broker-identity">{data.identity?.server} / {data.identity?.account_ref} / {data.identity?.symbol}</p>
      <details className="history-snapshot"><summary>ชุดข้อมูลถึง receipt {data.through_receipt} · ไม่มีการเพิ่มแท่งใหม่ระหว่างเปลี่ยนหน้า</summary>
        <p>คลัง: {data.archive_id}</p><p>SQLite: {(data.database_bytes / 1048576).toFixed(2)} / {data.quota_bytes / 1048576} MiB — ไม่รวมไฟล์ข้างเคียงและพื้นที่ระบบ</p>
      </details>
      {data.storage !== "normal" ? <p role="alert" className="owner-message">พื้นที่คลังถึงเกณฑ์ {data.storage === "warning_85" ? "85%" : "70%"} ต้องตรวจพื้นที่และสำรองข้อมูล ไม่มีการลบประวัติอัตโนมัติ</p> : null}
      {!data.bars.length ? <p role="status">{query.request.after ? "สิ้นสุดชุดข้อมูลนี้" : "ยังไม่มีแท่งปิดที่บันทึกไว้ในช่วงเวลานี้"}</p> : <>
        <p className="owner-hint">เลื่อนตารางเพื่อดูค่าครบ กดเวลาเพื่อดูหลักฐานของแท่งนั้น</p>
        <div className="history-table-scroll" tabIndex={0} role="region" aria-label="ตารางประวัติแท่งปิด">
          <table className="history-table"><caption className="history-caption">แท่งปิด {timeframe} · เวลาเปิดกรุงเทพฯ</caption>
            <thead><tr><th scope="col">เปิดแท่ง (กรุงเทพฯ)</th><th scope="col">เปิด (O)</th><th scope="col">สูงสุด (H)</th><th scope="col">ต่ำสุด (L)</th><th scope="col">ปิด (C)</th><th scope="col">Tick volume</th></tr></thead>
            <tbody>{data.bars.map(item => <tr key={item.time_server_s} className={bar === item ? "is-selected" : undefined}>
              <th scope="row"><button type="button" aria-pressed={bar === item} aria-label={`ดูหลักฐาน ${item.open_time_utc}`} onClick={() => setSelection(item.time_server_s)}>{bangkok(item.open_time_utc)}</button></th>
              <td>{item.open}</td><td>{item.high}</td><td>{item.low}</td><td>{item.close}</td><td>{item.tick_volume}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </>}
      {data.gaps.length ? <div className="chart-gap"><strong>ข้อมูลขาด {data.gaps.length} ช่วง — ยังไม่ทราบสาเหตุ</strong><ul>{data.gaps.map(gap =>
        <li key={gap.after_open_time_utc}>{gap.after_open_time_utc} ถึง {gap.before_open_time_utc}: ขาด {gap.missing_intervals} แท่ง</li>)}</ul></div> : null}
      {bar ? <div className="history-provenance" aria-label="หลักฐานแท่งที่เลือก">
        <h3>หลักฐานแท่งที่เลือก</h3><dl>
          <div><dt>เปิดแท่ง (UTC)</dt><dd>{bar.open_time_utc}</dd></div>
          <div><dt>แท่งถัดไปยืนยันปิด (เวลา server ดิบ)</dt><dd>{bar.confirmed_by_server_s}</dd></div>
          <div><dt>MT5 อ่านข้อมูล (UTC)</dt><dd>{bar.source_observed_at}</dd></div>
          <div><dt>API รับครั้งแรก (UTC)</dt><dd>{bar.first_received_at}</dd></div>
          <div><dt>API รับครั้งแรก (กรุงเทพฯ)</dt><dd>{bangkok(bar.first_received_at)}</dd></div>
          <div><dt>Receipt แรก / MT5 build</dt><dd>{bar.first_receipt} / {bar.terminal_build}</dd></div>
          <div><dt>แหล่งข้อมูล / ฐานราคา</dt><dd>{data.source} / {bar.price_basis}</dd></div>
          <div><dt>Tick size / Spread (points)</dt><dd>{bar.tick_size} / {bar.spread_points}</dd></div>
          <div><dt>Server offset จาก UTC (วินาที)</dt><dd>{bar.broker_utc_offset_seconds}</dd></div>
        </dl>
      </div> : null}
      <p className="owner-hint">เวลาเปิดแท่งไม่ใช่เวลาที่ระบบได้รับข้อมูล · Tick volume ไม่ใช่ปริมาณซื้อขายจริง · ประวัตินี้ไม่ใช่หลักฐานการส่งคำสั่งหรือผลกลยุทธ์</p>
    </> : null}
  </div>;
}
