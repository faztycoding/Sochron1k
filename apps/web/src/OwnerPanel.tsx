import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, parseConfig, parseTelemetry, quoteIsFresh, readJSON, type Telemetry } from "./owner-api";
import { createOwnerAuth, type AuthFactory, type OwnerAuth } from "./owner-auth";
import { ChartPanel } from "./ChartPanel";
import { HistoryPanel } from "./HistoryPanel";
import { ExecutionPanel } from "./ExecutionPanel";

const stateLabels = {
  disabled: "ยังไม่ตั้งค่า MT5 bridge", awaiting_snapshot: "รอข้อมูลจาก MT5",
  connected: "เชื่อมต่อแล้ว", stale: "ข้อมูลเก่า — ห้ามใช้เป็นราคาปัจจุบัน",
  rejected: "ข้อมูลถูกปฏิเสธ — ต้องตรวจสอบ MT5",
};

export function OwnerPanel({ factory = createOwnerAuth, onConnectionChange }: {
  factory?: AuthFactory; onConnectionChange?: (label: string) => void;
}) {
  const [phase, setPhase] = useState<"loading" | "disabled" | "error" | "ready">("loading");
  const [reload, setReload] = useState(0);
  const [token, setToken] = useState<string | null>(null);
  const [view, setView] = useState<{ data: Telemetry; started: number } | null>(null);
  const [now, setNow] = useState(() => performance.now());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [logoutPending, setLogoutPending] = useState(false);
  const [notice, setNotice] = useState("");
  const [readNotice, setReadNotice] = useState("");
  const auth = useRef<OwnerAuth | null>(null);
  const generation = useRef(0);
  const activeToken = useRef<string | null>(null);
  const logoutLatch = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    let instance: OwnerAuth | null = null;
    let unsubscribe: (() => void) | undefined;
    setPhase("loading");
    void (async () => {
      try {
        const config = parseConfig(await readJSON("/api/auth/config", controller.signal));
        if (controller.signal.aborted) return;
        if (!config.enabled) { setPhase("disabled"); return; }
        instance = await factory(config);
        if (controller.signal.aborted) { instance.dispose(); return; }
        auth.current = instance;
        unsubscribe = instance.watch((next) => {
          if (controller.signal.aborted || logoutLatch.current || next === activeToken.current) return;
          activeToken.current = next;
          generation.current++;
          setView(null);
          setReadNotice("");
          setToken(next);
        });
        setPhase("ready");
      } catch { if (!controller.signal.aborted) setPhase("error"); }
    })();
    return () => {
      controller.abort(); generation.current++;
      unsubscribe?.(); instance?.dispose(); auth.current = null;
    };
  }, [factory, reload]);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    const current = generation.current;
    let timer: ReturnType<typeof setTimeout>;
    const tick = setInterval(() => setNow(performance.now()), 1000);
    const poll = async () => {
      const started = performance.now();
      let retry = true;
      try {
        const data = parseTelemetry(await readJSON("/api/owner/telemetry", controller.signal, token));
        if (controller.signal.aborted || current !== generation.current) return;
        setView({ data, started }); setNow(performance.now()); setReadNotice("");
      } catch (error) {
        if (controller.signal.aborted || current !== generation.current) return;
        setView(null);
        if (error instanceof ApiError && [401, 403].includes(error.status)) {
          retry = false;
          setReadNotice(error.status === 403 ? "บัญชีนี้ไม่มีสิทธิ์เจ้าของระบบ" : "Session ใช้งานไม่ได้ กรุณาออกจากระบบแล้วเข้าสู่ระบบใหม่");
        } else setReadNotice("ยืนยันข้อมูลไม่ได้ ข้อมูลบัญชีถูกซ่อนไว้ ระบบจะลองเชื่อมต่อใหม่");
      }
      if (retry && !controller.signal.aborted && current === generation.current) timer = setTimeout(() => void poll(), 1000);
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); clearInterval(tick); };
  }, [token]);

  const elapsed = view ? Math.max(0, (now - view.started) / 1000) : 0;
  const fresh = view ? quoteIsFresh(view.data, elapsed) : false;
  useEffect(() => {
    if (!view || view.data.status.state !== "connected") return;
    const age = Math.max(view.data.status.price_age_seconds ?? 5, view.data.status.heartbeat_age_seconds ?? 5);
    const remaining = Math.max(0, (5 - age) * 1000 - (performance.now() - view.started));
    const timer = setTimeout(() => setNow(performance.now()), remaining + 1);
    return () => clearTimeout(timer);
  }, [view]);
  const data = view?.data;
  const label = data ? (data.status.state === "connected" && !fresh ? stateLabels.stale : stateLabels[data.status.state]) :
    token ? "ยังยืนยันการเชื่อมต่อไม่ได้" : "รอเข้าสู่ระบบเจ้าของ";
  useEffect(() => { onConnectionChange?.(label); }, [label, onConnectionChange]);

  async function signIn(event: FormEvent) {
    event.preventDefault();
    if (!auth.current || busy || logoutPending) return;
    setBusy(true); setNotice(""); logoutLatch.current = false;
    const submitted = password;
    setPassword("");
    try { await auth.current.signIn(email.trim(), submitted); }
    catch { setNotice("เข้าสู่ระบบไม่สำเร็จ ตรวจสอบอีเมล รหัสผ่าน หรือการเชื่อมต่อ"); }
    finally { setBusy(false); }
  }

  async function signOut() {
    if (!auth.current || busy) return;
    logoutLatch.current = true; generation.current++;
    activeToken.current = null;
    setToken(null); setView(null); setReadNotice(""); setPassword(""); setNotice("");
    setLogoutPending(true); setBusy(true);
    try {
      await auth.current.signOut(); setLogoutPending(false); setNotice("ออกจากระบบแล้ว");
    } catch { setNotice("ซ่อนข้อมูลแล้ว แต่ยังยืนยันการออกจากระบบไม่ได้ กรุณาลองอีกครั้ง"); }
    finally { setBusy(false); }
  }

  return <><section className="panel owner-panel" aria-labelledby="owner-title">
    <div className="panel-heading">
      <div><h2 id="owner-title">บัญชี Demo ของคุณ</h2><p className="owner-subtitle">ข้อมูลส่วนตัวสำหรับเจ้าของระบบเท่านั้น</p></div>
      {token || logoutPending ? <button className="quiet-button" disabled={busy} onClick={() => void signOut()}>
        {logoutPending ? "ลองออกจากระบบอีกครั้ง" : "ออกจากระบบ"}
      </button> : <span className="status-chip status-chip--muted">อ่านข้อมูลเท่านั้น</span>}
    </div>
    {phase === "loading" ? <p role="status">กำลังตรวจการตั้งค่าเข้าสู่ระบบ…</p> : null}
    {phase === "disabled" ? <div className="owner-empty"><strong>ยังไม่ตั้งค่าบัญชีเจ้าของ</strong>
      <p>ต้องกำหนด Supabase Auth และเจ้าของบัญชีที่ API ก่อน จึงจะเข้าสู่ระบบและอ่านข้อมูล MT5 ได้</p></div> : null}
    {phase === "error" ? <div className="owner-empty"><p role="alert">โหลดการตั้งค่าเข้าสู่ระบบไม่ได้ ตรวจสอบ API แล้วลองอีกครั้ง</p>
      <button className="quiet-button" onClick={() => setReload(n => n + 1)}>โหลดการตั้งค่าใหม่</button></div> : null}
    {phase === "ready" && !token && !logoutPending ? <form className="owner-login" onSubmit={event => void signIn(event)}>
      <label>อีเมลเจ้าของ<input type="email" autoComplete="username" required maxLength={254} value={email} onChange={event => setEmail(event.target.value)} disabled={busy} /></label>
      <label>รหัสผ่าน<input type="password" autoComplete="current-password" required maxLength={1024} value={password} onChange={event => setPassword(event.target.value)} disabled={busy} /></label>
      <button className="gold-button" type="submit" disabled={busy}>{busy ? "กำลังเข้าสู่ระบบ…" : "เข้าสู่ระบบ"}</button>
      <p className="owner-hint">ไม่บันทึก session ลงเครื่อง เมื่อรีโหลดหน้าต้องเข้าสู่ระบบใหม่ ไม่ใช่รหัสผ่าน MT5</p>
    </form> : null}
    {notice ? <p role="status" className="owner-message">{notice}</p> : null}
    {readNotice ? <p role="alert" className="owner-message">{readNotice}</p> : null}
    {token && !data && !readNotice ? <p role="status">กำลังยืนยันสิทธิ์และอ่านข้อมูลบัญชี…</p> : null}
    {data ? <div className="owner-observation">
      <p className={fresh ? "quote-state is-fresh" : "quote-state"} role="status">{label}</p>
      {data.observation ? <>
        <p className="broker-identity">{data.observation.frame.identity.server} / {data.observation.frame.identity.account_ref} / {data.observation.frame.identity.symbol}</p>
        <dl className="account-values">
          <div><dt>Equity ({data.observation.frame.identity.currency})</dt><dd>{data.observation.frame.equity}</dd></div>
          <div><dt>Balance ({data.observation.frame.identity.currency})</dt><dd>{data.observation.frame.balance}</dd></div>
          <div><dt>Bid{fresh ? "" : " ล่าสุดที่บันทึก"}</dt><dd>{data.observation.frame.bid}</dd></div>
          <div><dt>Ask{fresh ? "" : " ล่าสุดที่บันทึก"}</dt><dd>{data.observation.frame.ask}</dd></div>
        </dl>
        <div className="observation-times">
          <span>อายุราคาอย่างน้อย: {data.status.price_age_seconds === null ? "ไม่ทราบ" : `${(data.status.price_age_seconds + elapsed).toFixed(1)} วินาที`}</span>
          <span>เวลา tick (UTC): {data.observation.event_time_utc}</span>
          <span>API รับข้อมูล (UTC): {data.observation.received_time_utc}</span>
          <span>เวลา tick (กรุงเทพฯ): {new Date(data.observation.event_time_utc).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}</span>
        </div>
        <p className="owner-hint">การเชื่อมต่อข้อมูลไม่ใช่การผ่าน preflight หรือการยืนยัน SL — Auto Trading ยังคงปิด</p>
      </> : <p className="owner-hint">ยังไม่มีข้อมูลบัญชีหรือราคาที่ MT5 ยืนยัน ไม่มีการจำลองยอดเงินหรือราคาในส่วนนี้</p>}
    </div> : null}
  </section><ChartPanel token={data ? token : null} identity={data?.observation?.frame.identity ?? null} />
    <HistoryPanel token={data ? token : null} identity={data?.observation?.frame.identity ?? null} />
    <ExecutionPanel token={token} /></>;
}
