import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OwnerPanel } from "./OwnerPanel";
import type { OwnerAuth } from "./owner-auth";
import { parseConfig, parseTelemetry, quoteIsFresh } from "./owner-api";
import { disabledHistory, historyFixture } from "./test/history-fixture";
import { alertDefinitions, alertKinds } from "./operational-alerts-api";

const config = { enabled: true, supabase_url: "https://auth.fixture.invalid", public_key: "sb_publishable_" + "fixture".repeat(4) };
const fixture = () => ({
  status: { state: "connected", price_fresh: true, heartbeat_fresh: true, price_age_seconds: 0,
    heartbeat_age_seconds: 0, auto_trading_enabled: false, execution_ready: false },
  observation: { event_time_utc: "2026-09-17T00:00:00Z", received_time_utc: "2026-09-17T00:00:00Z",
    frame: { trade_mode: "demo", equity: "1000.00", balance: "1001.00", free_margin: "900.00", bid: "2500.10", ask: "2500.30",
      identity: { account_ref: "synthetic-account", server: "Synthetic-Demo", currency: "USD", symbol: "XAUUSD.fixture" } } },
});
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
const disabledExecution = () => ({ trading_mode: "demo", read_only: true, source: "local-execution-journal",
  status: { state: "disabled", reason: "not_configured", total_commands: 0, truncated: false,
    auto_trading_enabled: false, execution_ready: false }, commands: [] });
const emptySignals = () => ({ trading_mode: "demo", read_only: true, source: "supabase-signals",
  read_at_utc: "2026-09-17T00:00:00Z", status: { state: "awaiting_source", returned_count: 0, limit: 50,
    auto_trading_enabled: false, execution_ready: false }, signals: [] });
const emptyStatistics = () => ({ trading_mode: "demo", read_only: true, source: "supabase-evaluations",
  read_at_utc: "2026-09-17T00:00:00Z", status: { state: "awaiting_source", returned_count: 0, limit: 30,
    auto_trading_enabled: false, execution_ready: false, promotion_decided: false }, evaluations: [] });
const emptyAlerts = () => ({ protocol: "sochron.operational-alerts.v1", trading_mode: "demo", read_only: true,
  auto_trading_enabled: false, execution_ready: false, delivery_configured: false, status: "partial",
  generated_at_utc: "2026-09-17T00:00:00Z", truncated: false, alerts: [],
  coverage: alertKinds.map(kind => ({ kind, implementation: alertDefinitions[kind].implementation,
    runtime: "awaiting_configuration", api_routes: alertDefinitions[kind].routes,
    sources: alertDefinitions[kind].sources })) });
function setup(privateResponse: () => Promise<Response> = async () => json(fixture()),
  historyResponse: () => Promise<Response> = async () => json(disabledHistory())) {
  let callback: (token: string | null) => void = () => {};
  const unsubscribe = vi.fn();
  const auth: OwnerAuth = {
    signIn: vi.fn(async () => { callback("synthetic-user-token"); }),
    signOut: vi.fn(async () => { callback(null); }),
    watch: vi.fn(fn => { callback = fn; return unsubscribe; }), dispose: vi.fn(),
  };
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (path) =>
    String(path) === "/api/auth/config" ? json(config) : String(path).startsWith("/api/owner/chart/") ?
      json({ state: "disabled", feed_status: fixture().status, observation: null,
        snapshot_age_seconds: null, latest_bar_age_seconds: null, execution_ready: false }) :
      String(path).startsWith("/api/owner/history/") ? historyResponse() :
      String(path) === "/api/owner/execution" ? json(disabledExecution()) :
      String(path) === "/api/owner/alerts" ? json(emptyAlerts()) :
      String(path) === "/api/owner/signals" ? json(emptySignals()) :
      String(path) === "/api/owner/statistics" ? json(emptyStatistics()) : privateResponse());
  const factory = vi.fn(async () => auth);
  const result = render(<OwnerPanel factory={factory} />);
  return { auth, fetch, factory, unsubscribe, emit: (value: string | null) => callback(value), ...result };
}
async function login() {
  fireEvent.change(await screen.findByLabelText("อีเมลเจ้าของ"), { target: { value: "owner@sochron.test" } });
  fireEvent.change(screen.getByLabelText("รหัสผ่าน"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "เข้าสู่ระบบ" }));
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });

describe("SCN-005 owner UI", () => {
  it("shows archived bars without telemetry and clears them when live authorization fails", async () => {
    let authorized = true;
    setup(async () => authorized ? json({ status: { ...fixture().status, state: "awaiting_snapshot", price_fresh: false,
      heartbeat_fresh: false, price_age_seconds: null, heartbeat_age_seconds: null }, observation: null }) : json({}, 401),
      async () => json(historyFixture()));
    await login(); await screen.findByRole("table");
    expect(screen.queryByText("1000.00")).not.toBeInTheDocument();
    authorized = false;
    await screen.findByRole("alert", {}, { timeout: 1800 });
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText("2500.10")).not.toBeInTheDocument();
  });
  it("does not offer login when server configuration is disabled", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ enabled: false }));
    const factory = vi.fn(); render(<OwnerPanel factory={factory} />);
    expect(await screen.findByText("ยังไม่ตั้งค่าบัญชีเจ้าของ")).toBeVisible();
    expect(screen.queryByLabelText("รหัสผ่าน")).not.toBeInTheDocument();
    expect(factory).not.toHaveBeenCalled();
  });
  it("offers a config retry without collecting a password on failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("private-error"))
      .mockResolvedValueOnce(json({ enabled: false }));
    render(<OwnerPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "โหลดการตั้งค่าใหม่" }));
    expect(await screen.findByText("ยังไม่ตั้งค่าบัญชีเจ้าของ")).toBeVisible();
    expect(screen.queryByText("private-error")).not.toBeInTheDocument();
  });
  it("signs in and displays only validated owner telemetry", async () => {
    const { auth, fetch } = setup(); await login();
    expect(await screen.findByText("1000.00")).toBeVisible();
    expect(screen.getByText("2500.10")).toBeVisible();
    expect(screen.getByText(/เวลา tick \(UTC\)/)).toHaveTextContent("2026-09-17T00:00:00Z");
    expect(auth.signIn).toHaveBeenCalledWith("owner@sochron.test", "synthetic-password");
    const request = fetch.mock.calls.find(([path]) => path === "/api/owner/telemetry");
    expect(request?.[1]?.headers).toMatchObject({ Authorization: "Bearer synthetic-user-token" });
    expect(request?.[1]?.cache).toBe("no-store");
    expect(screen.queryByRole("button", { name: /เปิดออเดอร์/ })).not.toBeInTheDocument();
  });
  it("clears password and redacts a failed sign-in error", async () => {
    const { auth } = setup(); vi.mocked(auth.signIn).mockRejectedValue(new Error("private-credential"));
    await login(); expect(await screen.findByText(/เข้าสู่ระบบไม่สำเร็จ/)).toBeVisible();
    expect(screen.getByLabelText("รหัสผ่าน")).toHaveValue("");
    expect(screen.queryByText("private-credential")).not.toBeInTheDocument();
  });
  it.each([401, 403, 503])("hides account values when API denies access: %s", async status => {
    setup(async () => json({ detail: "sensitive-upstream-body" }, status)); await login();
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(screen.queryByText("1000.00")).not.toBeInTheDocument();
    expect(screen.queryByText("sensitive-upstream-body")).not.toBeInTheDocument();
  });
  it("rejects malformed private data", async () => {
    setup(async () => json({ status: { state: "connected" } })); await login();
    expect(await screen.findByRole("alert")).toHaveTextContent("ยืนยันข้อมูลไม่ได้");
  });
  it("never calls a stale quote current", async () => {
    const data = fixture(); data.status.state = "stale"; data.status.price_fresh = false;
    setup(async () => json(data)); await login();
    expect(await screen.findByText("Bid ล่าสุดที่บันทึก")).toBeVisible();
    expect(screen.getByText(/ข้อมูลเก่า/)).toBeVisible();
  });
  it("discards a private response arriving after logout", async () => {
    let resolve!: (value: Response) => void;
    setup(() => new Promise(done => { resolve = done; })); await login();
    await screen.findByRole("button", { name: "ออกจากระบบ" });
    await waitFor(() => expect(resolve).toBeTypeOf("function"));
    fireEvent.click(screen.getByRole("button", { name: "ออกจากระบบ" }));
    await act(async () => { resolve(json(fixture())); });
    expect(await screen.findByText("ออกจากระบบแล้ว")).toBeVisible();
    expect(screen.queryByText("1000.00")).not.toBeInTheDocument();
  });
  it("masks values and allows retry when remote logout fails", async () => {
    const { auth, emit } = setup(); await login(); await screen.findByText("1000.00");
    vi.mocked(auth.signOut).mockRejectedValueOnce(new Error("offline"));
    fireEvent.click(screen.getByRole("button", { name: "ออกจากระบบ" }));
    expect(await screen.findByText(/ยังยืนยันการออกจากระบบไม่ได้/)).toBeVisible();
    act(() => emit("late-refresh-token"));
    expect(screen.queryByText("1000.00")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "ลองออกจากระบบอีกครั้ง" }));
    expect(await screen.findByText("ออกจากระบบแล้ว")).toBeVisible();
  });
  it("unsubscribes and disposes the Auth client on unmount", async () => {
    const { auth, unsubscribe, unmount } = setup(); await screen.findByLabelText("รหัสผ่าน"); unmount();
    expect(auth.dispose).toHaveBeenCalledOnce(); expect(unsubscribe).toHaveBeenCalledOnce();
  });
  it("does not stop polling on duplicate SIGNED_IN events", async () => {
    const { emit, fetch } = setup(); await login(); await screen.findByText("1000.00");
    act(() => emit("synthetic-user-token"));
    await waitFor(() => expect(fetch.mock.calls.filter(([path]) => path === "/api/owner/telemetry").length).toBeGreaterThan(1), { timeout: 1800 });
    expect(screen.getByText("1000.00")).toBeVisible();
  });
  it("discards the old-token response after token refresh", async () => {
    let resolve!: (value: Response) => void;
    let count = 0;
    const { emit } = setup(() => ++count === 1 ? new Promise(done => { resolve = done; }) : Promise.resolve(json(fixture())));
    await login(); await waitFor(() => expect(resolve).toBeTypeOf("function"));
    act(() => emit("refreshed-user-token"));
    expect(await screen.findByText("1000.00")).toBeVisible();
    const old = fixture(); old.observation.frame.equity = "999999.00";
    await act(async () => { resolve(json(old)); });
    expect(screen.queryByText("999999.00")).not.toBeInTheDocument();
  });
  it("hides previously visible values after a polling network failure", async () => {
    let count = 0;
    setup(async () => { if (++count > 1) throw new Error("offline"); return json(fixture()); });
    await login(); await screen.findByText("1000.00");
    await waitFor(() => expect(screen.queryByText("1000.00")).not.toBeInTheDocument(), { timeout: 1800 });
    expect(screen.getByRole("alert")).toHaveTextContent("ยืนยันข้อมูลไม่ได้");
  });
  it("expires the displayed quote even while the next request hangs", async () => {
    vi.useFakeTimers();
    let count = 0;
    await act(async () => { setup(() => ++count === 1 ? Promise.resolve(json(fixture())) : new Promise(() => {})); });
    await act(async () => {
      fireEvent.change(screen.getByLabelText("อีเมลเจ้าของ"), { target: { value: "owner@sochron.test" } });
      fireEvent.change(screen.getByLabelText("รหัสผ่าน"), { target: { value: "synthetic-password" } });
      fireEvent.click(screen.getByRole("button", { name: "เข้าสู่ระบบ" }));
    });
    expect(screen.getByText("Bid")).toBeVisible();
    await act(async () => { await vi.advanceTimersByTimeAsync(5100); });
    expect(screen.getByText("Bid ล่าสุดที่บันทึก")).toBeVisible();
    expect(screen.getByText(/ข้อมูลเก่า/)).toBeVisible();
  });
});

describe("runtime validation", () => {
  it.each(["sb_secret_fixture", "invalid"])("rejects non-public keys: %s", public_key => {
    expect(() => parseConfig({ ...config, public_key })).toThrow();
  });
  it("rejects non-loopback plain HTTP Auth", () => {
    expect(() => parseConfig({ ...config, supabase_url: "http://external.invalid" })).toThrow();
  });
  it("accepts a valid configuration", () => { expect(parseConfig(config)).toEqual(config); });
  it("ages quotes independently of another API response", () => {
    const data = parseTelemetry(fixture());
    expect(quoteIsFresh(data, 4.9)).toBe(true);
    expect(quoteIsFresh(data, 5.01)).toBe(false);
  });
  it("rejects live mode and unsafe execution flags", () => {
    const data = fixture(); data.observation.frame.trade_mode = "real";
    expect(() => parseTelemetry(data)).toThrow();
    const enabled = fixture(); enabled.status.auto_trading_enabled = true;
    expect(() => parseTelemetry(enabled)).toThrow();
  });
  it("rejects impossible quotes and invalid timestamps", () => {
    const data = fixture(); data.observation.frame.ask = "-1";
    expect(() => parseTelemetry(data)).toThrow();
    const time = fixture(); time.observation.event_time_utc = "not-time";
    expect(() => parseTelemetry(time)).toThrow();
  });
});
