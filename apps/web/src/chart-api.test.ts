import { describe, expect, it, vi } from "vitest";
import { canvasCanPreservePrices, chartIsFresh, parseChart, periods, priceUnits, type ChartView, type Timeframe } from "./chart-api";
import { candlePoints } from "./CandleCanvas";
import { readJSON } from "./owner-api";

import { chartFixture, identity } from "./test/chart-fixture";

describe("native chart browser contract", () => {
  it.each(Object.keys(periods) as Timeframe[])("preserves exact OHLC, time mapping and forming %s", timeframe => {
    const value = chartFixture(timeframe);
    expect(parseChart(value, timeframe, identity)).toEqual(value);
    expect(value.observation?.bars.at(-1)?.closed).toBe(false);
  });
  it("keeps scientific notation exact and declines unsafe canvas conversion", () => {
    expect(priceUnits("1E-10")).toBe(1n);
    expect(priceUnits("99999999999999.9999999999")).toBe(999999999999999999999999n);
    const value = chartFixture().observation!;
    value.digits = 10; value.tick_size = "1E-10";
    for (const bar of value.bars) for (const field of ["open", "high", "low", "close"] as const) bar[field] = "99999999999999.9999999999";
    expect(canvasCanPreservePrices(value)).toBe(false);
  });
  it.each(["0", "-1", "NaN", "Infinity", "1e100", "1e-11", "100000000000000", 2500, null])("rejects invalid decimal %s", value => {
    expect(() => priceUnits(value)).toThrow();
  });
  const mutations: Array<[string, (value: ChartView) => void]> = [
    ["wrong timeframe", v => { v.observation!.timeframe = "M1"; }],
    ["other account", v => { v.observation!.identity = { ...identity, account_ref: "other" }; }],
    ["unsafe execution", v => { Object.assign(v, { execution_ready: true }); }],
    ["auto trading", v => { Object.assign(v.feed_status, { auto_trading_enabled: true }); }],
    ["NaN age", v => { v.snapshot_age_seconds = NaN; }],
    ["missing age", v => { v.latest_bar_age_seconds = null; }],
    ["no observation", v => { v.observation = null; }],
    ["disabled with bars", v => { v.state = "disabled"; }],
    ["invalid UTC", v => { v.observation!.observed_at = "2026-09-17T00:00:01"; }],
    ["wrong source", v => { Object.assign(v.observation!, { source: "synthetic" }); }],
    ["wrong time mapping", v => { v.observation!.broker_utc_offset_seconds = 0; }],
    ["closed final bar", v => { v.observation!.bars[1].closed = true; }],
    ["forming historical bar", v => { v.observation!.bars[0].closed = false; }],
    ["out of order", v => { v.observation!.bars.reverse(); }],
    ["invalid OHLC", v => { v.observation!.bars[0].low = "2501.00"; }],
    ["tick violation", v => { v.observation!.tick_size = "0.25"; }],
    ["bad digits", v => { v.observation!.digits = 0; }],
    ["unsafe volume", v => { v.observation!.bars[0].tick_volume = Number.MAX_SAFE_INTEGER + 1; }],
    ["empty bars", v => { v.observation!.bars = []; }],
    ["oversized window", v => { v.observation!.bars = Array(241).fill(v.observation!.bars[0]); }],
    ["future bar", v => { v.observation!.observed_at = v.observation!.bars[0].open_time_utc; }],
  ];
  it.each(mutations)("rejects %s", (_name, mutate) => {
    const value = chartFixture(); mutate(value); expect(() => parseChart(value, "M5", identity)).toThrow();
  });
  it("validates gap metadata and inserts only a whitespace marker", () => {
    const value = chartFixture("M5", true);
    expect(parseChart(value, "M5", identity)).toEqual(value);
    const points = candlePoints(value.observation!);
    expect(points).toHaveLength(3); expect(Object.keys(points[1])).toEqual(["time"]);
    expect(points[2]).toMatchObject({ color: "#d6b46a" });
    value.observation!.gaps = [];
    expect(() => parseChart(value, "M5", identity)).toThrow();
  });
  it("expires snapshot, quote and current-bar ages independently", () => {
    const value = chartFixture();
    expect(chartIsFresh(value, 4.9)).toBe(true); expect(chartIsFresh(value, 5.01)).toBe(false);
    value.snapshot_age_seconds = 14;
    expect(chartIsFresh(value, 1.01)).toBe(false);
    value.snapshot_age_seconds = 0; value.latest_bar_age_seconds = 299;
    expect(chartIsFresh(value, 1)).toBe(false);
    value.state = "rejected"; expect(chartIsFresh(value, 0)).toBe(false);
  });
  it("preserves the default response bound and gives charts a separate bounded allowance", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ padding: "x".repeat(70000) })));
    try {
      await expect(readJSON("/api/owner/telemetry", new AbortController().signal)).rejects.toThrow("Response too large");
      await expect(readJSON("/api/owner/chart/M5", new AbortController().signal, "fixture", 262144)).resolves.toHaveProperty("padding");
      fetch.mockImplementation(async () => new Response("x".repeat(262145)));
      await expect(readJSON("/api/owner/chart/M5", new AbortController().signal, "fixture", 262144)).rejects.toThrow("Response too large");
    } finally { fetch.mockRestore(); }
  });
});
