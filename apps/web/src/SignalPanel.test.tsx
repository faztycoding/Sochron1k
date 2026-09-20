import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SignalPanel } from "./SignalPanel";

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
function fixture() {
  return { trading_mode: "demo", read_only: true, source: "supabase-signals", read_at_utc: "2026-09-19T12:11:00Z",
    status: { state: "available", returned_count: 1, limit: 50, auto_trading_enabled: false, execution_ready: false },
    signals: [{ signal_id: "signal-pa01-0002", setup_id: "setup-pa01-0002", action: "wait",
      formed_at_utc: "2026-09-19T12:00:00Z", confirmed_at_utc: "2026-09-19T12:10:00Z",
      expires_at_utc: "2026-09-19T12:10:30Z", created_at_utc: "2026-09-19T12:10:01Z",
      evidence_ids: ["feature-m5-1205"], blocked_reason: "รอแท่ง M5 ปิด",
      experiment: { experiment_id: "experiment-pa01-v1", status: "demo", policy_version: "risk-v1.1" },
      strategy: { version_id: "PA01-v1", code_hash: "a".repeat(64), status: "active",
        data_cutoff_utc: "2026-09-19T12:05:00Z" } }] };
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("owner signal panel", () => {
  it("does not read private evidence before login", () => {
    const fetch = vi.spyOn(globalThis, "fetch"); render(<SignalPanel token={null} />);
    expect(screen.getByText("เข้าสู่ระบบเจ้าของเพื่ออ่านสัญญาณ")).toBeVisible();
    expect(fetch).not.toHaveBeenCalled();
  });
  it("renders exact evidence without trade controls", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(fixture()));
    render(<SignalPanel token="owner-token" />);
    expect(await screen.findByText("signal-pa01-0002")).toBeVisible();
    expect(screen.getByText("WAIT")).toBeVisible(); expect(screen.getByText("รอแท่ง M5 ปิด")).toBeVisible();
    expect(screen.getByText("PA01-v1")).toBeVisible(); expect(screen.getByText("experiment-pa01-v1")).toBeVisible();
    expect(screen.getByText("หมดอายุแล้ว")).toBeVisible();
    expect(fetch.mock.calls[0][0]).toBe("/api/owner/signals");
    expect(fetch.mock.calls[0][1]?.headers).toMatchObject({ Authorization: "Bearer owner-token" });
    expect(screen.queryByRole("button", { name: /ซื้อ|ขาย|ส่ง|เปิดออเดอร์/ })).not.toBeInTheDocument();
  });
  it("shows the producer dependency instead of a fabricated signal", async () => {
    const value = fixture(); value.status.state = "awaiting_source"; value.status.returned_count = 0; value.signals = [];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(value)); render(<SignalPanel token="owner-token" />);
    expect(await screen.findByText("API และ PA01 producer พร้อม · รอหลักฐานต้นทาง")).toBeVisible();
    expect(screen.queryByText("WAIT")).not.toBeInTheDocument();
  });
  it("clears malformed evidence and offers a read-only retry", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ secret: "private" })).mockResolvedValue(json(fixture()));
    render(<SignalPanel token="owner-token" />);
    fireEvent.click(await screen.findByRole("button", { name: "ลองอ่านสัญญาณอีกครั้ง" }));
    await waitFor(() => expect(screen.getByText("signal-pa01-0002")).toBeVisible());
    expect(screen.queryByText("private")).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(2);
  });
});
