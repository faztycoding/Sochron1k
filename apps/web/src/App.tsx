import { useCallback, useEffect, useRef, useState } from "react";
import { ConnectionMap, type ConnectionViewState } from "./ConnectionMap";
import { parseConnectionMap } from "./connection-api";
import { DemoReadinessPanel, type DemoReadinessViewState } from "./DemoReadinessPanel";
import { parseDemoReadiness } from "./demo-readiness-api";
import { OwnerPanel } from "./OwnerPanel";
import { readJSON } from "./owner-api";

type Health = {
  status: "ok";
  service: string;
  version: string;
  trading_mode: "demo";
  auto_trading_enabled: false;
  execution_ready: false;
};

type ConnectionState =
  | { kind: "loading" }
  | { kind: "ready"; health: Health; checkedAt: Date }
  | { kind: "error"; checkedAt: Date };

const navigation = ["ภาพรวม", "กราฟ", "สัญญาณ", "สถิติ", "เพิ่มเติม"];

const lifecycle = [
  ["Created", "สร้างคำสั่ง"],
  ["Validated", "ผ่านกฎ"],
  ["Queued", "บันทึกแล้ว"],
  ["Sent", "รอ MT5"],
  ["Confirmed", "ยืนยันจากโบรกเกอร์"],
] as const;

function parseHealth(value: unknown): Health {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid health");
  const health = value as Record<string, unknown>;
  if (health.status !== "ok" || health.service !== "sochron1k-api" || typeof health.version !== "string" ||
      !/^\d+\.\d+\.\d+$/.test(health.version) || health.trading_mode !== "demo" ||
      health.auto_trading_enabled !== false || health.execution_ready !== false) throw new Error("Invalid health");
  return health as Health;
}

function LogoMark() {
  return (
    <svg aria-hidden="true" className="logo-mark" viewBox="0 0 36 36">
      <path d="M18 2 32 10v16L18 34 4 26V10L18 2Z" />
      <path d="m18 2 1 16 13-8M18 34l1-16 13 8M4 10l15 8L4 26" />
    </svg>
  );
}

function StateDot({ tone }: { tone: "good" | "warn" | "bad" }) {
  return <span aria-hidden="true" className={`state-dot state-dot--${tone}`} />;
}

export function App() {
  const [ownerConnection, setOwnerConnection] = useState("รอเข้าสู่ระบบเจ้าของ");
  const [connection, setConnection] = useState<ConnectionState>({ kind: "loading" });
  const [connectionMap, setConnectionMap] = useState<ConnectionViewState>({ kind: "loading" });
  const [demoReadiness, setDemoReadiness] = useState<DemoReadinessViewState>({ kind: "loading" });
  const checkGeneration = useRef(0);

  const checkHealth = useCallback(async () => {
    const generation = ++checkGeneration.current;
    setConnection({ kind: "loading" });
    setConnectionMap({ kind: "loading" });
    setDemoReadiness({ kind: "loading" });
    const healthRequest = (async () => {
      const response = await fetch("/api/health", { cache: "no-store", redirect: "error", headers: { Accept: "application/json" } });
      if (!response.ok) {
        throw new Error(`Health request failed: ${response.status}`);
      }
      return parseHealth(await response.json());
    })();
    const mapRequest = readJSON("/api/ui/connections", new AbortController().signal, undefined, 32768)
      .then(parseConnectionMap);
    const readinessRequest = readJSON("/api/ui/demo-readiness", new AbortController().signal, undefined, 32768)
      .then(parseDemoReadiness);
    const [healthResult, mapResult, readinessResult] = await Promise.allSettled([
      healthRequest, mapRequest, readinessRequest,
    ]);
    if (generation !== checkGeneration.current) return;
    const checkedAt = new Date();
    setConnection(healthResult.status === "fulfilled" ?
      { kind: "ready", health: healthResult.value, checkedAt } : { kind: "error", checkedAt });
    setConnectionMap(mapResult.status === "fulfilled" ?
      { kind: "ready", data: mapResult.value } : { kind: "error" });
    setDemoReadiness(readinessResult.status === "fulfilled" ?
      { kind: "ready", data: readinessResult.value } : { kind: "error" });
  }, []);

  useEffect(() => {
    void checkHealth();
    return () => { checkGeneration.current++; };
  }, [checkHealth]);

  const apiOnline = connection.kind === "ready";
  const apiVersion = connection.kind === "ready" ? connection.health.version : null;
  const checkedAt = connection.kind === "loading" ? null : connection.checkedAt;

  return (
    <div className="app-shell">
      <aside className="side-rail" aria-label="เมนูหลัก">
        <a className="brand" href="#overview" aria-label="Sochron1k ภาพรวม">
          <LogoMark />
          <span>Sochron1k</span>
        </a>
        <nav className="rail-nav">
          {navigation.map((item, index) => index === 1 || index === 2 || index === 3 || index === 4 ? (
            <a className="nav-item" href={index === 1 ? "#market-chart" : index === 2 ? "#signal-evidence" : index === 3 ? "#research-statistics" : "#api-connections"} key={item}>
              <span className="nav-index">0{index + 1}</span><span>{index === 4 ? "การเชื่อมต่อ" : item}</span>
            </a>
          ) : (
            <span
              aria-current={index === 0 ? "page" : undefined}
              aria-disabled={index === 0 ? undefined : true}
              className={`nav-item${index === 0 ? " is-active" : " is-disabled"}`}
              key={item}
            >
              <span className="nav-index">0{index + 1}</span>
              <span>{item}</span>
            </span>
          ))}
        </nav>
        <div className="rail-note">
          <span>Runtime</span>
          <strong>Prototype</strong>
          <small>ไม่มีเส้นทางบัญชีจริง</small>
        </div>
      </aside>

      <main id="overview">
        <header className="topbar">
          <div className="mobile-brand">
            <LogoMark />
            <strong>Sochron1k</strong>
          </div>
          <div>
            <p className="page-context">Execution evidence console</p>
            <h1>ศูนย์ควบคุมระบบเดโม่</h1>
          </div>
          <div className="topbar-meta">
            <span className="demo-badge">DEMO ONLY</span>
            <span className="time-readout">
              {checkedAt
                ? `ตรวจล่าสุด ${checkedAt.toLocaleTimeString("th-TH", { timeZone: "Asia/Bangkok" })}`
                : "กำลังตรวจระบบ"}
            </span>
          </div>
        </header>

        <section className="safety-banner" aria-labelledby="safety-title">
          <div className="safety-symbol" aria-hidden="true">!</div>
          <div>
            <h2 id="safety-title">ยังไม่พร้อมส่งคำสั่งไป MT5</h2>
            <p>ระบบควบคุมถูกล็อกไว้จนกว่า preflight, broker identity และ recovery gates จะผ่าน</p>
          </div>
          <div className="lock-state">
            <span>Auto trading</span>
            <strong>ปิด</strong>
          </div>
        </section>

        <ConnectionMap state={connectionMap} onRetry={() => void checkHealth()} />

        <OwnerPanel onConnectionChange={setOwnerConnection} />

        <section className="status-grid" aria-label="สถานะระบบ">
          <article className="panel panel--primary">
            <div className="panel-heading">
              <div>
                <p>สถานะหลัก</p>
                <h2>ความพร้อมของระบบ</h2>
              </div>
              <button className="quiet-button" onClick={() => void checkHealth()} type="button">
                ตรวจอีกครั้ง
              </button>
            </div>
            <div className="readiness-score">
              <div className="score-ring" aria-label="ตรวจสอบเฉพาะระบบ local">
                <span>LOCAL</span>
              </div>
              <div>
                <strong>Local safety core</strong>
                <p>พร้อมทดสอบด้วย simulator เท่านั้น</p>
              </div>
            </div>
            <dl className="status-list">
              <div>
                <dt><StateDot tone={apiOnline ? "good" : connection.kind === "loading" ? "warn" : "bad"} />API</dt>
                <dd>{connection.kind === "loading" ? "กำลังตรวจ" : apiOnline ? `ออนไลน์ · v${apiVersion}` : "เชื่อมต่อไม่ได้"}</dd>
              </div>
              <div>
                <dt><StateDot tone="warn" />MT5 executor</dt>
                <dd>{ownerConnection}</dd>
              </div>
              <div>
                <dt><StateDot tone="warn" />Market feed</dt>
                <dd>ตรวจที่ส่วนบัญชี Demo</dd>
              </div>
              <div>
                <dt><StateDot tone="good" />Execution policy</dt>
                <dd>Demo-only</dd>
              </div>
            </dl>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p>Deterministic controls</p>
                <h2>นโยบายความเสี่ยง</h2>
              </div>
              <span className="policy-version">v1.1</span>
            </div>
            <div className="risk-matrix">
              <div><span>ต่อไม้</span><strong>0.25%</strong><small>ของ Equity ล่าสุด</small></div>
              <div><span>หยุดรายวัน</span><strong>0.75%</strong><small>จากต้นวันไทย</small></div>
              <div><span>หยุดการทดลอง</span><strong>2.00%</strong><small>ไม่รีเซ็ตอัตโนมัติ</small></div>
              <div><span>Exposure สูงสุด</span><strong>1</strong><small>position หรือ pending</small></div>
            </div>
            <p className="policy-note">AI ไม่มีสิทธิ์แก้เพดาน ปลด halt หรือเพิ่มล็อต</p>
          </article>
        </section>

        <section className="panel evidence-panel">
          <div className="panel-heading">
            <div>
              <p>Command lifecycle</p>
              <h2>ทุกคำสั่งต้องมีหลักฐานก่อนส่ง</h2>
            </div>
            <span className="status-chip">ยังไม่เชื่อมประวัติคำสั่ง</span>
          </div>
          <ol className="lifecycle">
            {lifecycle.map(([title, detail], index) => (
              <li key={title}>
                <span>{index + 1}</span>
                <strong>{title}</strong>
                <small>{detail}</small>
              </li>
            ))}
          </ol>
          <p className="evidence-footnote">HTTP สำเร็จไม่เท่ากับ fill · UNKNOWN ต้อง reconcile ก่อน retry · protected เมื่อ MT5 ยืนยัน SL เท่านั้น</p>
        </section>

        <DemoReadinessPanel state={demoReadiness} />

        <section className="broker-proof-section">
          <article className="panel account-panel">
            <div className="panel-heading">
              <div>
                <p>Broker truth</p>
                <h2>หลักฐานการป้องกันสถานะ</h2>
              </div>
              <span className="status-chip status-chip--muted">รอ preflight</span>
            </div>
            <div className="empty-state">
              <div className="empty-glyph" aria-hidden="true">◎</div>
              <strong>ยังไม่ยืนยัน broker-side SL</strong>
              <p>ข้อมูลบัญชีและราคาอยู่ในส่วนบัญชี Demo ด้านบน การอ่านราคาได้ไม่ใช่หลักฐานว่าเปิดสถานะหรือมี SL แล้ว</p>
            </div>
          </article>
        </section>
      </main>

      <nav className="mobile-nav" aria-label="เมนูมือถือ">
        {navigation.slice(0, 4).map((item, index) => index > 0 ? (
          <a className="nav-item" href={index === 1 ? "#market-chart" : index === 2 ? "#signal-evidence" : "#research-statistics"} key={item}>
            <span>{index + 1}</span>{item}
          </a>
        ) : (
          <span
            aria-current={index === 0 ? "page" : undefined}
            aria-disabled={index === 0 ? undefined : true}
            className={`nav-item${index === 0 ? " is-active" : " is-disabled"}`}
            key={item}
          >
            <span>{index + 1}</span>{item}
          </span>
        ))}
      </nav>
    </div>
  );
}
