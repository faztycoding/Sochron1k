import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChartPanel } from "./ChartPanel";
import { chartFixture, identity } from "./test/chart-fixture";

const canvas = vi.hoisted(() => ({ setData: vi.fn(), fitContent: vi.fn(), remove: vi.fn(), create: vi.fn() }));
vi.mock("lightweight-charts", () => ({ ColorType: { Solid: "solid" }, CandlestickSeries: "Candlestick",
  createChart: (...args: unknown[]) => { canvas.create(...args); return { addSeries: () => ({ setData: canvas.setData }), timeScale: () => ({ fitContent: canvas.fitContent }), remove: canvas.remove }; },
}));
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.clearAllMocks(); vi.useRealTimers(); });
function setup() {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async path => json(chartFixture(String(path).endsWith("M1") ? "M1" : "M5")));
  const result = render(<ChartPanel token="synthetic-token" identity={identity} />);
  return { fetch, ...result };
}
describe("owner native chart UI", () => {
  it("never reads or loads a chart without an authenticated account", () => {
    const fetch = vi.spyOn(globalThis, "fetch");
    render(<ChartPanel token={null} identity={null} />);
    expect(screen.getByText("รอยืนยันบัญชีเจ้าของและข้อมูล MT5")).toBeVisible();
    expect(fetch).not.toHaveBeenCalled(); expect(canvas.create).not.toHaveBeenCalled();
  });
  it("renders exact values, selects closed bars, and disposes the canvas on logout", async () => {
    const { rerender } = setup();
    await screen.findByText("2500.10");
    await waitFor(() => expect(canvas.setData).toHaveBeenCalled());
    expect(canvas.fitContent).toHaveBeenCalledTimes(1);
    expect(screen.getByText("ยังไม่ยืนยันปิด — ค่านี้ยังเปลี่ยนได้")).toBeVisible();
    fireEvent.change(screen.getByLabelText("ตรวจค่าแท่งเทียน (UTC)"), { target: { value: chartFixture().observation!.bars[0].open_time_utc } });
    expect(screen.getByText("แท่งปิดแล้ว — มีแท่งถัดไปยืนยัน")).toBeVisible();
    rerender(<ChartPanel token={null} identity={null} />);
    expect(screen.queryByText("2500.10")).not.toBeInTheDocument(); expect(canvas.remove).toHaveBeenCalledTimes(1);
  });
  it("aborts and discards an old timeframe response", async () => {
    let resolve!: (value: Response) => void;
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(path => String(path).endsWith("M5") ? new Promise(done => { resolve = done; }) : Promise.resolve(json(chartFixture("M1"))));
    render(<ChartPanel token="synthetic-token" identity={identity} />);
    fireEvent.click(screen.getByRole("button", { name: "M1" }));
    await screen.findByText("2500.10");
    expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(true);
    const old = chartFixture(); old.observation!.bars[0].open = "9999.00";
    await act(async () => { resolve(json(old)); });
    expect(screen.queryByText("9999.00")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "M1" })).toHaveAttribute("aria-pressed", "true");
  });
  it("clears old-token data immediately and ignores its pending response", async () => {
    let resolve!: (value: Response) => void;
    const { fetch, rerender } = setup(); await screen.findByText("2500.10");
    fetch.mockImplementation(() => new Promise(done => { resolve = done; }));
    rerender(<ChartPanel token="refreshed-token" identity={identity} />);
    expect(screen.queryByText("2500.10")).not.toBeInTheDocument();
    rerender(<ChartPanel token={null} identity={null} />);
    await act(async () => { resolve(json(chartFixture())); });
    expect(screen.queryByText("2500.10")).not.toBeInTheDocument();
  });
  it.each([401, 403])("denies without retrying or exposing an upstream body: %s", async status => {
    vi.useFakeTimers();
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ error: "private-body" }, status));
    await act(async () => { render(<ChartPanel token="synthetic-token" identity={identity} />); });
    expect(screen.getByRole("alert")).toHaveTextContent("ไม่มีสิทธิ์อ่านกราฟ");
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(fetch).toHaveBeenCalledTimes(1); expect(screen.queryByText("private-body")).not.toBeInTheDocument();
  });
  it("clears on network failure and recovers with a new valid response", async () => {
    const { fetch } = setup(); await screen.findByText("2500.10");
    fetch.mockRejectedValueOnce(new Error("private-network-details"));
    await screen.findByRole("alert", {}, { timeout: 1800 });
    expect(screen.queryByText("2500.10")).not.toBeInTheDocument();
    expect(await screen.findByText("2500.10", {}, { timeout: 1800 })).toBeVisible();
  });
  it("marks a quote stale even while its next chart request hangs", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date", "performance"] });
    let monotonic = 0;
    vi.spyOn(performance, "now").mockImplementation(() => monotonic);
    const value = chartFixture(); value.feed_status.price_age_seconds = 4.99;
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json(value)).mockImplementation(() => new Promise(() => {}));
    await act(async () => { render(<ChartPanel token="synthetic-token" identity={identity} />); });
    expect(screen.getByText("ข้อมูลล่าสุดจากช่อง MT5")).toBeVisible();
    monotonic = 20;
    await act(async () => { await vi.advanceTimersByTimeAsync(20); });
    expect(screen.getByText("ข้อมูลเก่า — ไม่ใช่ราคาปัจจุบัน")).toBeVisible();
  });
  it("hides a retained rejected observation and explains the rejection", async () => {
    const value = chartFixture(); value.state = "rejected";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(value));
    render(<ChartPanel token="synthetic-token" identity={identity} />);
    expect(await screen.findByText(/ข้อมูลกราฟถูกปฏิเสธ/)).toBeVisible();
    expect(screen.queryByText("2500.10")).not.toBeInTheDocument(); expect(canvas.create).not.toHaveBeenCalled();
  });
});
