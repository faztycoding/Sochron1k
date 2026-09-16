import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("Sochron1k safety console", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("keeps Demo and Auto Trading off visible when API is healthy", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ok",
          service: "sochron1k-api",
          version: "0.1.0",
          trading_mode: "demo",
          auto_trading_enabled: false,
          execution_ready: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<App />);

    expect(screen.getByText("DEMO ONLY")).toBeVisible();
    expect(screen.getByText("ยังไม่พร้อมส่งคำสั่งไป MT5")).toBeVisible();
    expect(screen.getByLabelText("ตรวจสอบเฉพาะระบบ local")).toHaveTextContent("LOCAL");
    expect(screen.queryByText("35")).not.toBeInTheDocument();
    for (const unavailableItem of screen.getAllByText("กราฟ")) {
      expect(unavailableItem.closest('[aria-disabled="true"]')).not.toBeNull();
    }
    await waitFor(() => expect(screen.getByText("ออนไลน์ · v0.1.0")).toBeVisible());
    expect(screen.queryByRole("button", { name: /ซื้อ|ขาย|เปิดออเดอร์/ })).not.toBeInTheDocument();
  });

  it("shows a truthful disconnected state and permits a safe health retry", async () => {
    const request = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            status: "ok",
            service: "sochron1k-api",
            version: "0.1.0",
            trading_mode: "demo",
            auto_trading_enabled: false,
            execution_ready: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    render(<App />);
    await waitFor(() => expect(screen.getByText("เชื่อมต่อไม่ได้")).toBeVisible());
    fireEvent.click(screen.getByRole("button", { name: "ตรวจอีกครั้ง" }));
    await waitFor(() => expect(screen.getByText("ออนไลน์ · v0.1.0")).toBeVisible());
    expect(request).toHaveBeenCalledTimes(2);
  });
});
