import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HistoryPanel } from "./HistoryPanel";
import { disabledHistory, historyFixture, historyIdentity } from "./test/history-fixture";
import type { Timeframe } from "./chart-api";
import { historyQuota } from "./history-api";

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });
function setup() {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async path => {
    const url = new URL(String(path), "http://localhost");
    const timeframe = url.pathname.split("/").at(-1) as Timeframe;
    const after = Number(url.searchParams.get("after_server_s"));
    return json(historyFixture(timeframe, after ? after + 300 : undefined, after ? 1 : 20));
  });
  return { fetch, ...render(<HistoryPanel token="synthetic-token" identity={historyIdentity} />) };
}
describe("SCN-007 owner history workspace", () => {
  it("does not read private data before owner authentication", () => {
    const fetch = vi.spyOn(globalThis, "fetch");
    render(<HistoryPanel token={null} identity={null} />);
    expect(fetch).not.toHaveBeenCalled(); expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it("does not silently advance the snapshot on a timer", async () => {
    const { fetch } = setup(); await screen.findByRole("table");
    vi.useFakeTimers(); await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it.each([0.70, 0.85])("shows storage warning at %s without describing total disk usage", async fraction => {
    const data = historyFixture(); data.database_bytes = Math.ceil(historyQuota * fraction);
    data.storage = fraction === 0.70 ? "warning_70" : "warning_85";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(data));
    render(<HistoryPanel token="synthetic-token" identity={historyIdentity} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(`พื้นที่คลังถึงเกณฑ์ ${fraction * 100}%`);
    expect(screen.getByText(/ไม่รวมไฟล์ข้างเคียงและพื้นที่ระบบ/)).toBeInTheDocument();
  });
  it("reads with no live identity, selects evidence and clears on logout", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(historyFixture()));
    const { rerender } = render(<HistoryPanel token="synthetic-token" identity={null} />);
    await screen.findByRole("table");
    expect(screen.getAllByText("2500.10")).toHaveLength(20);
    const second = historyFixture().bars[1];
    fireEvent.click(screen.getByRole("button", { name: `ดูหลักฐาน ${second.open_time_utc}` }));
    expect(screen.getByText(String(second.confirmed_by_server_s))).toBeVisible();
    rerender(<HistoryPanel token={null} identity={null} />);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(String(second.confirmed_by_server_s))).not.toBeInTheDocument();
  });
  it("pins both directions, bounds rows and only refreshes deliberately", async () => {
    const { fetch, rerender } = setup(); await screen.findByRole("table");
    const last = historyFixture().bars.at(-1)!;
    rerender(<HistoryPanel token="synthetic-token" identity={{ ...historyIdentity }} />);
    expect(fetch).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "หน้าถัดไป" }));
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    await screen.findByRole("table");
    expect(screen.getAllByRole("row")).toHaveLength(2);
    const next = String(fetch.mock.calls.at(-1)![0]);
    expect(next).toContain(`after_server_s=${last.time_server_s}`); expect(next).toContain("through_receipt=42");
    expect(next).toContain(`archive_id=${historyFixture().archive_id}`);
    expect(screen.getByRole("button", { name: "หน้าถัดไป" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "หน้าก่อน" })); await screen.findByRole("table");
    expect(fetch.mock.calls.at(-1)![0]).toContain("after_server_s=0&archive_id=");
    fireEvent.click(screen.getByRole("button", { name: "อ่านชุดล่าสุด" })); await screen.findByRole("table");
    expect(fetch.mock.calls.at(-1)![0]).not.toContain("through_receipt");
  });
  it("handles exact-full-page end and returning from empty page", async () => {
    const { fetch } = setup(); await screen.findByRole("table");
    const empty = historyFixture(); empty.bars = [];
    fetch.mockResolvedValueOnce(json(empty));
    fireEvent.click(screen.getByRole("button", { name: "หน้าถัดไป" }));
    await screen.findByText("สิ้นสุดชุดข้อมูลนี้");
    expect(screen.getByRole("button", { name: "หน้าก่อน" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "หน้าก่อน" })); await screen.findByRole("table");
  });
  it.each(["timeframe", "token", "identity", "logout", "unmount"])("aborts and ignores pending results on %s", async change => {
    let resolve!: (response: Response) => void;
    const { fetch, rerender, unmount } = setup(); await screen.findByRole("table");
    fetch.mockImplementationOnce(() => new Promise(done => { resolve = done; }));
    fireEvent.click(screen.getByRole("button", { name: "หน้าถัดไป" }));
    const signal = fetch.mock.calls.at(-1)![1]?.signal;
    if (change === "timeframe") fireEvent.click(screen.getByRole("button", { name: "M1" }));
    else if (change === "unmount") unmount();
    else rerender(<HistoryPanel token={change === "logout" ? null : change === "token" ? "new-token" : "synthetic-token"}
      identity={change === "identity" ? { ...historyIdentity, account_ref: "new-account" } : historyIdentity} />);
    expect(signal?.aborted).toBe(true);
    const late = historyFixture("M5", historyFixture().bars.at(-1)!.time_server_s + 300, 1);
    Object.assign(late.bars[0], { open: "9999.00", high: "9999.00", low: "9999.00", close: "9999.00" });
    await act(async () => { resolve(json(late)); });
    expect(screen.queryByText("9999.00")).not.toBeInTheDocument();
    if (["logout", "unmount", "identity"].includes(change)) expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it.each([401, 403])("hides values and never automatically retries denied %s", async status => {
    const { fetch } = setup(); await screen.findByRole("table");
    fetch.mockResolvedValue(json({ private: "upstream-secret" }, status));
    fireEvent.click(screen.getByRole("button", { name: "หน้าถัดไป" }));
    await screen.findByRole("alert");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText("upstream-secret")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ลองอ่านหน้าเดิมอีกครั้ง" })).not.toBeInTheDocument();
    vi.useFakeTimers(); await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it.each(["network", "malformed", "oversized"])("hides failed %s reads and retries the same pinned page", async failure => {
    const { fetch } = setup(); await screen.findByRole("table");
    if (failure === "network") fetch.mockRejectedValueOnce(new Error("private-details"));
    else fetch.mockResolvedValueOnce(json(failure === "oversized" ? { payload: "x".repeat(131073) } : {}));
    fireEvent.click(screen.getByRole("button", { name: "หน้าถัดไป" })); await screen.findByRole("alert");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    const failedPath = fetch.mock.calls.at(-1)![0];
    fireEvent.click(screen.getByRole("button", { name: "ลองอ่านหน้าเดิมอีกครั้ง" })); await screen.findByRole("table");
    expect(fetch.mock.calls.at(-1)![0]).toBe(failedPath);
  });
  it("explains disabled history and an empty available archive", async () => {
    const { fetch } = setup(); await screen.findByRole("table");
    fetch.mockResolvedValueOnce(json(disabledHistory()));
    fireEvent.click(screen.getByRole("button", { name: "อ่านชุดล่าสุด" }));
    await screen.findByText(/ยังไม่เปิดการบันทึกประวัติที่ API/);
    const data = historyFixture(); data.bars = [];
    fetch.mockResolvedValueOnce(json(data));
    fireEvent.click(screen.getByRole("button", { name: "อ่านชุดล่าสุด" }));
    await screen.findByText(/ยังไม่มีแท่งปิดที่บันทึกไว้/);
    await waitFor(() => expect(screen.queryByRole("table")).not.toBeInTheDocument());
  });
});
